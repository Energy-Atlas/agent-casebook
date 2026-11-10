"""Evaluation instance tooling for the UBEM Agent Casebook (pilot).

Evaluation instances are optional, runnable companions to qualitative cases.
Each lives in ``evals/instances/<instance-id>/`` and links to one or more case
ids. The fixtures and references are public development references, not a
hidden benchmark.

Commands::

    python evals/evalkit.py check [INSTANCE ...]
    python evals/evalkit.py prepare INSTANCE --out DIR [--receipt FILE]
    python evals/evalkit.py grade INSTANCE --submission DIR [--out FILE]
                                  [--run-meta FILE] [--label TEXT]

- ``check`` validates instance specifications, confirms that the generator
  reproduces the committed fixtures byte for byte, scans agent-facing files for
  leaked identifiers, and grades every sample submission against its expected
  outcome (grader self-test).
- ``prepare`` copies only the agent-facing files into an empty directory
  outside the repository and writes a receipt next to it (not inside it). It
  assembles a clean bundle; it does not restrict what an agent can read or
  reach. Isolation is the job of whoever launches the agent.
- ``grade`` scores a submission directory and writes a machine-readable result
  (default: ``runs/<timestamp>-<instance>/result.json``, which Git ignores).

Exit codes for ``grade``: 0 pass, 1 fail, 2 invalid-output, 3 env-error,
4 grader-error.

Only the Python standard library and PyYAML are required (see
``evals/requirements.txt``). This is separate from the documentation build.
"""

from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

try:
    import yaml
except ImportError:  # reported as an environment error by the commands
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = ROOT / "evals"
INSTANCES_DIR = EVALS_DIR / "instances"
RUNS_DIR = ROOT / "runs"

RESULT_SCHEMA = "ubem-casebook-eval-result/0.1"
STATUSES = ["pass", "fail", "invalid-output", "env-error", "grader-error"]
EXIT_CODES = {"pass": 0, "fail": 1, "invalid-output": 2, "env-error": 3, "grader-error": 4}
CRITERION_KINDS = ["schema", "correctness", "behavior-evidence", "integrity"]
OUTCOMES = ["pass", "fail", "not-evaluated"]

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CASE_ID_RE = re.compile(r"^UBEM-\d{3,}$")
INPUT_ORIGINS = ["synthetic", "open-data", "mixed"]
INSTANCE_STATUSES = ["development"]

REQUIRED = {
    "id": str,
    "version": int,
    "status": str,
    "cases": list,
    "family": str,
    "summary": str,
    "inputs": dict,
    "agent": dict,
    "reference": str,
    "grader": str,
    "acceptance": dict,
    "not_assessed": list,
    "self_test": list,
}


class EnvError(Exception):
    """The evaluator's environment or instance files are broken, not the submission."""


# --- loading and specification checks ------------------------------------------


def require_yaml() -> None:
    if yaml is None:
        raise EnvError("PyYAML is not installed; install evals/requirements.txt")


def instance_dir(instance_id: str) -> Path:
    return INSTANCES_DIR / instance_id


def load_spec(instance_id: str) -> dict:
    require_yaml()
    path = instance_dir(instance_id) / "instance.yaml"
    if not path.is_file():
        raise EnvError(f"no instance specification at {path.relative_to(ROOT).as_posix()}")
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise EnvError(f"{path.name} is not a mapping")
    return spec


def spec_problems(instance_id: str, spec: dict) -> list[str]:
    problems = []
    for key, kind in REQUIRED.items():
        if key not in spec:
            problems.append(f"missing field: {key}")
        elif not isinstance(spec[key], kind) or isinstance(spec[key], bool):
            problems.append(f"{key} must be a {kind.__name__}")
    if problems:
        return problems
    if spec["id"] != instance_id or not ID_RE.match(instance_id):
        problems.append(f"id '{spec['id']}' must be kebab-case and equal the folder name")
    if spec["version"] < 1:
        problems.append("version must be a positive integer")
    if spec["status"] not in INSTANCE_STATUSES:
        problems.append(f"status must be one of: {', '.join(INSTANCE_STATUSES)}")
    if not spec["cases"] or not all(isinstance(c, str) and CASE_ID_RE.match(c) for c in spec["cases"]):
        problems.append("cases must be a non-empty list of case ids (UBEM-NNN)")
    inputs = spec["inputs"]
    if inputs.get("origin") not in INPUT_ORIGINS:
        problems.append(f"inputs.origin must be one of: {', '.join(INPUT_ORIGINS)}")
    if not isinstance(inputs.get("license"), str):
        problems.append("inputs.license is required")
    agent = spec["agent"]
    if not (isinstance(agent.get("files"), list) and agent["files"]):
        problems.append("agent.files must list the agent-facing files")
    if not (isinstance(agent.get("returns"), list) and agent["returns"]):
        problems.append("agent.returns must list the files the agent writes")
    if not isinstance(agent.get("environment"), dict):
        problems.append("agent.environment must describe what the agent can use")
    for entry in spec["self_test"]:
        if not (isinstance(entry, dict) and "submission" in entry and entry.get("status") in STATUSES):
            problems.append(f"self_test entry needs 'submission' and a valid 'status': {entry}")
    if not spec["self_test"]:
        problems.append("self_test must include at least one sample submission")
    return problems


def file_problems(instance_id: str, spec: dict) -> list[str]:
    base = instance_dir(instance_id)
    problems = []
    agent_dir = base / "agent"
    listed = set(spec["agent"]["files"])
    present = {p.relative_to(agent_dir).as_posix() for p in agent_dir.rglob("*") if p.is_file()} if agent_dir.is_dir() else set()
    for name in sorted(listed - present):
        problems.append(f"agent file listed but missing: agent/{name}")
    for name in sorted(present - listed):
        problems.append(f"file in agent/ not listed in agent.files (would not reach the agent): agent/{name}")
    for key in ["reference", "grader"]:
        if not resolve(base, spec[key]).is_file():
            problems.append(f"{key} file not found: {spec[key]}")
    reference = resolve(base, spec["reference"])
    if reference.is_file() and agent_dir in reference.parents:
        problems.append("reference must not live inside agent/")
    generator = spec["inputs"].get("generator")
    if generator and not resolve(base, generator).is_file():
        problems.append(f"generator not found: {generator}")
    for entry in spec["self_test"]:
        if not resolve(base, entry["submission"]).is_dir():
            problems.append(f"sample submission not found: {entry['submission']}")
    return problems


def resolve(base: Path, path: str) -> Path:
    """Paths in a spec are relative to the instance folder, or to the repo root if they start with evals/."""
    return ROOT / path if path.startswith("evals/") else base / path


def leak_problems(files: list[Path], markers: list[str]) -> list[str]:
    problems = []
    for file in files:
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in markers:
            if marker and marker in text:
                problems.append(f"agent-facing file {file.name} contains '{marker}'")
    return problems


def leak_markers(spec: dict) -> list[str]:
    """Strings that must not reach the agent: instance ids and case ids."""
    ids = [p.name for p in INSTANCES_DIR.iterdir() if p.is_dir()] if INSTANCES_DIR.is_dir() else []
    return sorted(set(ids) | set(spec["cases"]))


def reproduction_problems(instance_id: str, spec: dict) -> list[str]:
    generator = spec["inputs"].get("generator")
    if not generator:
        return []
    base = instance_dir(instance_id)
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [sys.executable, str(resolve(base, generator)), "--out-root", tmp]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return [f"generator failed: {proc.stderr.strip()[-500:]}"]
        generated = Path(tmp) / instance_id
        if not generated.is_dir():
            return [f"generator did not produce {instance_id}/"]
        problems = []
        produced = {p.relative_to(generated).as_posix() for p in generated.rglob("*") if p.is_file()}
        for top in sorted({p.split("/")[0] for p in produced}):
            committed = {
                p.relative_to(base).as_posix() for p in (base / top).rglob("*") if p.is_file()
            } if (base / top).is_dir() else set()
            for rel in sorted(committed - produced):
                problems.append(f"committed file not produced by the generator: {rel}")
        for rel in sorted(produced):
            if not (base / rel).is_file():
                problems.append(f"generated file not committed: {rel}")
            elif not filecmp.cmp(generated / rel, base / rel, shallow=False):
                problems.append(f"committed file differs from generator output: {rel}")
        return problems


# --- grading ----------------------------------------------------------------------


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(directory: Path) -> dict[str, str]:
    if not directory.is_dir():
        return {}
    return {
        p.relative_to(directory).as_posix(): sha256(p)
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def git_state() -> dict:
    def run(*args):
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()

    try:
        return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def load_grader(path: Path):
    spec = importlib.util.spec_from_file_location(f"grader_{abs(hash(path))}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "grade"):
        raise EnvError(f"grader {path.name} has no grade() function")
    return module


def grade_submission(instance_id: str, submission: Path) -> dict:
    """Grade a submission directory; return the result record (never raises)."""
    started = dt.datetime.now(dt.timezone.utc)
    result = {
        "schema": RESULT_SCHEMA,
        "instance": {"id": instance_id},
        "casebook": git_state(),
        "submission": {"path": str(submission)},
        "graded_at": started.isoformat(timespec="seconds"),
        "status": None,
        "summary": {},
        "criteria": [],
        "not_assessed": [],
        "diagnostics": [],
    }
    try:
        spec = load_spec(instance_id)
        problems = spec_problems(instance_id, spec)
        if problems:
            raise EnvError("invalid instance specification: " + "; ".join(problems))
        base = instance_dir(instance_id)
        agent_dir = base / "agent"
        reference_path = resolve(base, spec["reference"])
        grader_path = resolve(base, spec["grader"])
        for path in [reference_path, grader_path]:
            if not path.is_file():
                raise EnvError(f"missing instance file: {path.relative_to(ROOT).as_posix()}")
        result["instance"].update({
            "version": spec["version"],
            "status": spec["status"],
            "cases": spec["cases"],
            "spec_sha256": sha256(base / "instance.yaml"),
            "reference_sha256": sha256(reference_path),
            "agent_files_sha256": tree_hashes(agent_dir),
        })
        result["grader"] = {"path": grader_path.relative_to(ROOT).as_posix(), "sha256": sha256(grader_path)}
        result["not_assessed"] = spec["not_assessed"]
        if not submission.is_dir():
            result["status"] = "invalid-output"
            result["diagnostics"].append(f"submission directory not found: {submission}")
            return result
        result["submission"]["files_sha256"] = tree_hashes(submission)
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        grader = load_grader(grader_path)
    except EnvError as exc:
        result["status"] = "env-error"
        result["diagnostics"].append(str(exc))
        return result
    except Exception:  # noqa: BLE001 - anything here is the evaluator's fault
        result["status"] = "env-error"
        result["diagnostics"].append(traceback.format_exc())
        return result

    try:
        criteria = grader.grade(
            submission_dir=submission,
            agent_dir=agent_dir,
            reference=reference,
            acceptance=spec["acceptance"],
        )
        _check_criteria(criteria)
    except Exception:  # noqa: BLE001 - a crash in the grader is not the agent's failure
        result["status"] = "grader-error"
        result["diagnostics"].append(traceback.format_exc())
        return result

    result["criteria"] = criteria
    result["summary"] = {
        kind: _kind_summary([c for c in criteria if c["kind"] == kind])
        for kind in CRITERION_KINDS
        if any(c["kind"] == kind for c in criteria)
    }
    if any(c["kind"] == "schema" and c["outcome"] == "fail" for c in criteria):
        result["status"] = "invalid-output"
    elif any(c["outcome"] == "fail" for c in criteria):
        result["status"] = "fail"
    else:
        result["status"] = "pass"
    return result


def _check_criteria(criteria) -> None:
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("grader must return a non-empty list of criteria")
    seen = set()
    for c in criteria:
        for key in ["id", "kind", "outcome", "detail"]:
            if key not in c:
                raise ValueError(f"criterion missing '{key}': {c}")
        if c["kind"] not in CRITERION_KINDS or c["outcome"] not in OUTCOMES:
            raise ValueError(f"criterion has invalid kind or outcome: {c}")
        if c["id"] in seen:
            raise ValueError(f"duplicate criterion id: {c['id']}")
        seen.add(c["id"])


def _kind_summary(criteria: list[dict]) -> dict:
    counts = {o: sum(c["outcome"] == o for c in criteria) for o in OUTCOMES}
    counts["outcome"] = "fail" if counts["fail"] else "pass" if counts["pass"] else "not-evaluated"
    return counts


def failed_ids(result: dict) -> list[str]:
    return sorted(c["id"] for c in result["criteria"] if c["outcome"] == "fail")


# --- commands ---------------------------------------------------------------------


def all_instances() -> list[str]:
    if not INSTANCES_DIR.is_dir():
        return []
    return sorted(p.name for p in INSTANCES_DIR.iterdir() if (p / "instance.yaml").is_file())


def cmd_check(ids: list[str]) -> int:
    require_yaml()
    ids = ids or all_instances()
    total = 0
    for instance_id in ids:
        problems = []
        try:
            spec = load_spec(instance_id)
        except EnvError as exc:
            problems = [str(exc)]
            spec = None
        if spec is not None:
            problems = spec_problems(instance_id, spec)
            if not problems:
                problems += file_problems(instance_id, spec)
            if not problems:
                agent_files = [instance_dir(instance_id) / "agent" / f for f in spec["agent"]["files"]]
                problems += leak_problems(agent_files, leak_markers(spec))
                problems += reproduction_problems(instance_id, spec)
                for entry in spec["self_test"]:
                    result = grade_submission(instance_id, resolve(instance_dir(instance_id), entry["submission"]))
                    expected_failed = sorted(entry.get("failed", []))
                    if result["status"] != entry["status"] or (
                        result["status"] in ("fail", "invalid-output") and failed_ids(result) != expected_failed
                    ):
                        problems.append(
                            f"self-test {entry['submission']}: expected {entry['status']} {expected_failed}, "
                            f"got {result['status']} {failed_ids(result)} {result['diagnostics'][-1:] or ''}"
                        )
        for problem in problems:
            print(f"evals/instances/{instance_id}: {problem}", file=sys.stderr)
        total += len(problems)
    print(f"{len(ids)} instance(s) checked, {total} problem(s)")
    return 1 if total else 0


def cmd_prepare(instance_id: str, out: Path, receipt: Path | None) -> int:
    spec = load_spec(instance_id)
    problems = spec_problems(instance_id, spec) or file_problems(instance_id, spec)
    if problems:
        for problem in problems:
            print(f"evals/instances/{instance_id}: {problem}", file=sys.stderr)
        return 1
    out = out.resolve()
    if out == ROOT or ROOT in out.parents:
        print(
            "refusing to prepare a bundle inside the casebook repository: an agent started there "
            "could read the cases, references, and repository instructions. Choose a directory "
            "outside it.",
            file=sys.stderr,
        )
        return 1
    if out.exists() and any(out.iterdir()):
        print(f"refusing to write into a non-empty directory: {out}", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    agent_dir = instance_dir(instance_id) / "agent"
    for name in spec["agent"]["files"]:
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(agent_dir / name, target)
    copied = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    leaks = leak_problems([out / f for f in copied], leak_markers(spec))
    if copied != sorted(spec["agent"]["files"]) or leaks:
        print("bundle check failed: " + "; ".join(leaks or ["unexpected files in bundle"]), file=sys.stderr)
        return 1
    receipt = receipt or out.parent / f"{out.name}.receipt.json"
    record = {
        "schema": "ubem-casebook-eval-bundle/0.1",
        "instance": {"id": instance_id, "version": spec["version"], "cases": spec["cases"]},
        "casebook": git_state(),
        "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "bundle_dir": str(out),
        "files_sha256": tree_hashes(out),
        "agent_returns": spec["agent"]["returns"],
        "environment": spec["agent"]["environment"],
        "isolation": (
            "Not enforced. The bundle holds only agent-facing files, but evalkit does not restrict "
            "filesystem or network access. Start the evaluated agent in a fresh session with the "
            "bundle as its working directory and without the authoring conversation, the casebook "
            "checkout, or references."
        ),
    }
    receipt.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"bundle: {out}")
    print(f"receipt (keep it away from the agent): {receipt}")
    print(f"the agent writes {', '.join(spec['agent']['returns'])} under {out / 'output'}")
    return 0


def cmd_grade(instance_id: str, submission: Path, out: Path | None, run_meta: Path | None, label: str | None) -> int:
    result = grade_submission(instance_id, submission.resolve())
    if run_meta:
        try:
            result["run"] = json.loads(run_meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            result["run"] = {}
            result["diagnostics"].append(f"could not read run metadata {run_meta}: {exc}")
    else:
        result["run"] = {}
    if out is None:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = RUNS_DIR / "-".join(filter(None, [stamp, instance_id, label])) / "result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"status: {result['status']}")
    for kind, summary in result["summary"].items():
        print(f"  {kind}: {summary['outcome']} ({summary['pass']} pass, {summary['fail']} fail)")
    for c in result["criteria"]:
        if c["outcome"] == "fail":
            print(f"  FAIL {c['id']}: {c['detail']}")
    for d in result["diagnostics"]:
        print(f"  diagnostic: {d.strip().splitlines()[-1]}")
    print(f"result: {out}")
    return EXIT_CODES[result["status"]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check", help="validate instances and run grader self-tests")
    p_check.add_argument("instances", nargs="*")
    p_prep = sub.add_parser("prepare", help="assemble the agent-facing bundle")
    p_prep.add_argument("instance")
    p_prep.add_argument("--out", type=Path, required=True)
    p_prep.add_argument("--receipt", type=Path)
    p_grade = sub.add_parser("grade", help="grade a submission and write a result")
    p_grade.add_argument("instance")
    p_grade.add_argument("--submission", type=Path, required=True)
    p_grade.add_argument("--out", type=Path)
    p_grade.add_argument("--run-meta", type=Path)
    p_grade.add_argument("--label")
    args = parser.parse_args(argv)

    try:
        if args.command == "check":
            return cmd_check(args.instances)
        if args.command == "prepare":
            return cmd_prepare(args.instance, args.out, args.receipt)
        return cmd_grade(args.instance, args.submission, args.out, args.run_meta, args.label)
    except EnvError as exc:
        print(f"environment error: {exc}", file=sys.stderr)
        return EXIT_CODES["env-error"]


if __name__ == "__main__":
    sys.exit(main())
