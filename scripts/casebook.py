"""Casebook schema, validator, CLI, and MkDocs hook.

Used two ways:

- As an MkDocs hook (see ``hooks`` in mkdocs.yml): validates every case and
  logs problems as warnings, so ``mkdocs build --strict`` fails on them; adds a
  metadata table to case pages; fills ``<!-- casebook:index -->`` markers with
  case tables; orders case categories in workflow order in the navigation.
- As a CLI::

      python scripts/casebook.py check          # validate all cases, run the release scan
      python scripts/casebook.py check --evals-dir PATH  # also cross-check evaluation instances
      python scripts/casebook.py next-id        # print the next free case id
      python scripts/casebook.py scan PATH ...  # release scan of given files or directories

The release scan looks for secrets and identifying details that must not be
published (see docs/guide/data-release.md).

Evaluation instances live in a separate validation package, not in this
repository. Each is ``instances/<instance-id>/instance.yaml`` in the package
and names the case ids it exercises in a ``cases:`` list. When ``check`` is
given the package location (``--evals-dir`` or the ``UBEM_EVALS_DIR``
environment variable), it verifies that linked case ids exist and that every
case marked ``eval_readiness: automated`` has a linked instance. Without a
location the cross-check is skipped with a note. The MkDocs hook never reads
the package.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import posixpath
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

# Workflow order; also the allowed values of `stage` and the case folders.
CATEGORIES = [
    "preprocessing",
    "model-config",
    "simulation",
    "validation",
    "calibration",
    "results",
    "scenarios",
]
ORIGINS = ["expert-practice", "observed", "literature", "synthetic"]
DATA_AVAILABILITY = ["public", "restricted", "private", "synthetic"]
EVAL_READINESS = ["conceptual", "specified", "mockable", "automated"]

FIELDS = [
    "id",
    "title",
    "date",
    "origin",
    "stage",
    "tags",
    "data_availability",
    "eval_readiness",
]
REQUIRED_SECTIONS = ["Situation", "Expected behavior", "Undesirable behavior", "Rationale"]
SECTIONS = REQUIRED_SECTIONS + ["Observation", "Evaluation potential", "References"]

ID_PREFIX = "UBEM-"
ID_RE = re.compile(r"^UBEM-(\d{3,})$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
FENCE_RE = re.compile(r"^(```|~~~)")
MARKER_RE = re.compile(r"<!--\s*casebook:index(?:\s+stage=([a-z0-9-]+))?\s*-->")

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
EVALS_DIR_ENV = "UBEM_EVALS_DIR"  # location of the separate validation package
INSTANCES_SUBDIR = "instances"  # relative to the validation package root

log = logging.getLogger("mkdocs.hooks.casebook")


@dataclass
class Case:
    path: str  # relative to docs/, POSIX style, e.g. "cases/calibration/x.md"
    meta: dict
    body: str
    error: str | None = None  # set when the file cannot be parsed

    @property
    def stage_dir(self) -> str:
        return self.path.split("/")[1] if self.path.count("/") >= 2 else ""

    @property
    def slug(self) -> str:
        return posixpath.splitext(posixpath.basename(self.path))[0]


def parse_case(path: str, text: str) -> Case:
    match = FRONT_MATTER_RE.match(text.replace("\r\n", "\n"))
    if not match:
        return Case(path, {}, text, "missing YAML front matter")
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        return Case(path, {}, text, f"invalid YAML front matter: {exc}")
    if not isinstance(meta, dict):
        return Case(path, {}, text, "front matter is not a mapping")
    return Case(path, meta, text[match.end():])


def load_cases(docs_dir: Path = DOCS_DIR) -> list[Case]:
    cases = []
    for file in sorted((docs_dir / "cases").rglob("*.md")):
        if file.name == "index.md":
            continue
        rel = file.relative_to(docs_dir).as_posix()
        cases.append(parse_case(rel, file.read_text(encoding="utf-8")))
    return cases


@dataclass
class Instance:
    path: str  # relative to the validation package root, POSIX style
    id: str
    cases: list
    error: str | None = None


def load_instances(evals_dir: Path) -> list[Instance]:
    """Read the id and linked case ids of each instance in the validation package."""
    root = evals_dir / INSTANCES_SUBDIR
    instances = []
    for file in sorted(root.glob("*/instance.yaml")):
        rel = f"{INSTANCES_SUBDIR}/{file.parent.name}/{file.name}"
        try:
            spec = yaml.safe_load(file.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            instances.append(Instance(rel, file.parent.name, [], f"invalid YAML: {exc}"))
            continue
        if not isinstance(spec, dict):
            instances.append(Instance(rel, file.parent.name, [], "not a mapping"))
            continue
        instances.append(Instance(rel, str(spec.get("id")), spec.get("cases"), None))
    return instances


def instance_links(instances: list[Instance]) -> dict[str, list[str]]:
    """Map case id -> ids of instances that link to it."""
    links: dict[str, list[str]] = {}
    for inst in instances:
        if not inst.error and isinstance(inst.cases, list):
            for case_id in inst.cases:
                links.setdefault(str(case_id), []).append(inst.id)
    return links


def validate_links(cases: list[Case], instances: list[Instance]) -> list[tuple[str, str]]:
    """Cross-check cases against the instances of the validation package."""
    problems = []
    case_ids = {str(c.meta.get("id")) for c in cases if not c.error}
    for inst in instances:
        folder = inst.path.split("/")[-2]
        label = f"<validation package>/{inst.path}"
        if inst.error:
            problems.append((label, inst.error))
            continue
        if inst.id != folder:
            problems.append((label, f"id '{inst.id}' does not match folder '{folder}'"))
        if not (isinstance(inst.cases, list) and inst.cases):
            problems.append((label, "cases must be a non-empty list of case ids"))
            continue
        for case_id in inst.cases:
            if str(case_id) not in case_ids:
                problems.append((label, f"links to unknown case id '{case_id}'"))
    links = instance_links(instances)
    for case in cases:
        if case.meta.get("eval_readiness") == "automated" and str(case.meta.get("id")) not in links:
            problems.append((
                case.path,
                "eval_readiness is automated but no instance in the validation package links to it",
            ))
    return problems


def headings(body: str) -> tuple[list[str], list[str]]:
    """Return (H1 titles, H2 titles) outside fenced code blocks."""
    h1, h2, in_fence = [], [], False
    for line in body.splitlines():
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
        elif not in_fence and line.startswith("# "):
            h1.append(line[2:].strip())
        elif not in_fence and line.startswith("## "):
            h2.append(line[3:].strip())
    return h1, h2


def validate_case(case: Case) -> list[str]:
    if case.error:
        return [case.error]
    errors = []
    meta = case.meta

    if case.path.count("/") != 2:
        errors.append("cases must live at cases/<category>/<case-name>.md")
    if not SLUG_RE.match(case.slug):
        errors.append(f"file name '{case.slug}' is not kebab-case")

    missing = [f for f in FIELDS if f not in meta]
    unknown = [f for f in meta if f not in FIELDS]
    if missing:
        errors.append(f"missing front matter fields: {', '.join(missing)}")
    if unknown:
        errors.append(f"unknown front matter fields: {', '.join(unknown)}")

    if "id" in meta and not ID_RE.match(str(meta["id"])):
        errors.append(f"id '{meta['id']}' does not match {ID_PREFIX}NNN")
    if "title" in meta and not (isinstance(meta["title"], str) and meta["title"].strip()):
        errors.append("title must be a non-empty string")
    if "date" in meta and not isinstance(meta["date"], dt.date):
        errors.append(f"date '{meta['date']}' is not a YYYY-MM-DD date")

    for name, allowed in [
        ("stage", CATEGORIES),
        ("origin", ORIGINS),
        ("data_availability", DATA_AVAILABILITY),
        ("eval_readiness", EVAL_READINESS),
    ]:
        if name in meta and meta[name] not in allowed:
            errors.append(f"{name} '{meta[name]}' not in: {', '.join(allowed)}")
    if meta.get("stage") in CATEGORIES and meta["stage"] != case.stage_dir:
        errors.append(f"stage '{meta['stage']}' does not match folder '{case.stage_dir}'")

    if "tags" in meta:
        tags = meta["tags"]
        if not isinstance(tags, list) or not tags:
            errors.append("tags must be a non-empty list")
        else:
            bad = [str(t) for t in tags if not (isinstance(t, str) and SLUG_RE.match(t))]
            if bad:
                errors.append(f"tags are not kebab-case: {', '.join(bad)}")
            if len(set(tags)) != len(tags):
                errors.append("tags contain duplicates")

    h1, h2 = headings(case.body)
    if h1:
        errors.append("body must not contain an H1; the title comes from front matter")
    unknown_sections = [h for h in h2 if h not in SECTIONS]
    if unknown_sections:
        errors.append(
            f"unknown sections: {', '.join(unknown_sections)} "
            f"(allowed: {', '.join(SECTIONS)}; drop any '(optional)' suffix)"
        )
    missing_sections = [s for s in REQUIRED_SECTIONS if s not in h2]
    if missing_sections:
        errors.append(f"missing sections: {', '.join(missing_sections)}")
    known = [h for h in h2 if h in SECTIONS]
    if known != sorted(known, key=SECTIONS.index) or len(set(known)) != len(known):
        errors.append(f"sections must appear once each, in order: {', '.join(SECTIONS)}")
    return errors


def validate(cases: list[Case], instances: list[Instance] | None = None) -> list[tuple[str, str]]:
    """Validate cases; cross-check instances only when they are given."""
    problems = [(c.path, e) for c in cases for e in validate_case(c)]
    if instances is not None:
        problems += validate_links(cases, instances)
    seen: dict[str, str] = {}
    for case in cases:
        case_id = case.meta.get("id")
        if case_id in seen:
            problems.append((case.path, f"duplicate id {case_id} (also in {seen[case_id]})"))
        elif case_id:
            seen[case_id] = case.path
    return problems


def next_id(cases: list[Case]) -> str:
    numbers = [int(m.group(1)) for c in cases if (m := ID_RE.match(str(c.meta.get("id", ""))))]
    return f"{ID_PREFIX}{max(numbers, default=0) + 1:03d}"


def _sort_key(case: Case) -> tuple:
    match = ID_RE.match(str(case.meta.get("id", "")))
    return (int(match.group(1)) if match else sys.maxsize, case.path)


# --- MkDocs hook -------------------------------------------------------------

_cases: dict[str, Case] = {}


def on_files(files, config):
    docs_dir = Path(config["docs_dir"])
    cases = load_cases(docs_dir)
    # The site build does not read the validation package; `check` does.
    problems = validate(cases)
    for path, message in problems:
        log.warning(f"{path}: {message}")
    # Only cases without problems get a metadata table and a row in case
    # tables; rendering an invalid case would fail on missing fields.
    invalid = {path for path, _ in problems}
    _cases.clear()
    _cases.update({c.path: c for c in cases if c.path not in invalid})
    return files


def on_nav(nav, config, files):
    # Home first, then sections (Cases, Guide), then loose pages such as Tags.
    nav.items.sort(key=lambda i: 0 if _first_src(i) == "index.md" else 2 if i.is_page else 1)
    for item in nav.items:
        if item.is_section and _first_src(item).startswith("cases/"):
            item.children.sort(key=_category_rank)
    # Previous/next links are computed before this event; recompute them.
    pages = list(_iter_pages(nav.items))
    nav.pages = pages
    for prev, page in zip([None] + pages[:-1], pages):
        page.previous_page = prev
        if prev is not None:
            prev.next_page = page
    if pages:
        pages[-1].next_page = None
    return nav


def on_page_markdown(markdown, page, config, files):
    src = page.file.src_uri
    case = _cases.get(src)
    if case:
        markdown = _meta_table(case) + "\n\n" + markdown
    return MARKER_RE.sub(lambda m: _case_table(src, m.group(1)), markdown)


def _iter_pages(items):
    for item in items:
        if item.is_page:
            yield item
        elif item.is_section:
            yield from _iter_pages(item.children)


def _first_src(item) -> str:
    if item.is_page:
        return item.file.src_uri
    if item.is_section:
        for child in item.children:
            if src := _first_src(child):
                return src
    return ""


def _category_rank(item) -> int:
    if not item.is_section:
        return -1
    parts = _first_src(item).split("/")
    category = parts[1] if len(parts) > 2 else ""
    return CATEGORIES.index(category) if category in CATEGORIES else len(CATEGORIES)


def _meta_table(case: Case) -> str:
    m = case.meta
    lines = [
        "| ID | Stage | Origin | Recorded | Data availability | Eval readiness |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| `{m['id']}` | [{m['stage']}](index.md) | {m['origin']} | {m['date']} "
        f"| {m['data_availability']} | {m['eval_readiness']} |",
    ]
    return "\n".join(lines)


def _case_table(page_src: str, stage: str | None) -> str:
    if stage and stage not in CATEGORIES:
        log.warning(f"{page_src}: unknown stage '{stage}' in casebook:index marker")
    cases = sorted(
        (c for c in _cases.values() if stage is None or c.meta.get("stage") == stage),
        key=_sort_key,
    )
    if not cases:
        return "_No cases yet._"
    base = posixpath.dirname(page_src)
    header = ["ID", "Case"] + ([] if stage else ["Stage"]) + ["Origin", "Eval readiness"]
    rows = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for c in cases:
        link = f"[{c.meta.get('title', c.slug)}]({posixpath.relpath(c.path, base)})"
        cells = [f"`{c.meta.get('id')}`", link]
        if not stage:
            cells.append(str(c.meta.get("stage")))
        cells += [str(c.meta.get("origin")), str(c.meta.get("eval_readiness"))]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


# --- release scan --------------------------------------------------------------
#
# Catches accidental publication of secrets and identifying details in a public
# repository (see docs/guide/data-release.md). It finds accidents, not
# deliberate re-identification: real geometry, attribute combinations, and
# identifying prose need a human reviewer.

REPO_ROOT = DOCS_DIR.parent
SCAN_ALLOW = "release-scan: allow"
SCAN_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".woff", ".woff2"}
_OLC = "[23456789CFGHJMPQRVWX]"
SCAN_PATTERNS = [
    ("secret", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),  # Google API key
    ("secret", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),  # AWS access key id
    ("secret", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),  # GitHub token
    ("secret", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,}")),  # API keys with sk- prefix
    ("secret", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),  # Slack token
    ("secret", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("secret", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*['\"][^'\"\s]{12,}['\"]")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("local-path", re.compile(r"(?i)\b[A-Z]:[\\/]{1,2}Users[\\/]{1,2}(?!public\b|default\b)[A-Za-z0-9._\-]+")),
    ("local-path", re.compile(r"(?<![A-Za-z0-9_.])/(?:Users|home)/(?!runner\b)[a-z][a-z0-9._\-]*/")),
    ("street-address", re.compile(
        r"\b\d{1,5}\s+(?:[NSEW]\.?\s+)?(?:[A-Z][a-z]+\s+){1,3}"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Place|Pl|Terrace|Ter|Parkway|Pkwy)\b")),
    ("parcel-id", re.compile(r"(?<![\w.\-])\d{1,3}\.\d{1,2}-\d{1,2}-\d{1,3}(?:\.\d{1,3})?(?![\w\-])")),
    ("building-id", re.compile(rf"\b{_OLC}{{4,8}}\+{_OLC}{{2,}}-\d+-\d+-\d+-\d+\b")),
]
# File names that suggest credentials; a bare key inside them has no telltale format.
SCAN_SECRET_FILE = re.compile(
    r"(?i)(?:^|[._\-])(?:api[_\-]?keys?|secrets?|credentials?|passwords?)(?:\.[A-Za-z0-9]+)?$"
    r"|^\.env(?:\..*)?$|\.(?:pem|key|p12|pfx)$|^id_(?:rsa|ed25519|ecdsa)$")
SCAN_EMAIL_ALLOW = re.compile(r"(?i)@(?:example\.(?:com|org|net)|anthropic\.com|users\.noreply\.github\.com)$")


def _mask(text: str) -> str:
    return text[:4] + "*" * max(len(text) - 4, 3) if len(text) > 4 else "*" * len(text)


def scan_text(text: str) -> list[tuple[int, str, str]]:
    """Return (line number, finding kind, masked match) for each finding."""
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        if SCAN_ALLOW in line:
            continue
        for kind, pattern in SCAN_PATTERNS:
            for match in pattern.finditer(line):
                if kind == "email" and SCAN_EMAIL_ALLOW.search(match.group(0)):
                    continue
                findings.append((number, kind, _mask(match.group(0))))
    return findings


def repository_files(root: Path = REPO_ROOT) -> list[Path]:
    """Tracked and new, non-ignored files; every file if Git is unavailable."""
    import subprocess

    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, check=True,
        ).stdout.decode("utf-8")
        return sorted(root / p for p in out.split("\0") if p and (root / p).is_file())
    except (OSError, subprocess.CalledProcessError):
        return sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts)


def release_scan(paths: list[Path], root: Path = REPO_ROOT) -> list[tuple[str, str]]:
    problems = []
    files = []
    for path in paths:
        files.extend(sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path])
    for file in files:
        try:
            label = file.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            label = str(file)
        if SCAN_SECRET_FILE.search(file.name):
            problems.append((label, "release scan: file name suggests credentials (secret-file)"))
        if file.suffix.lower() in SCAN_SKIP_SUFFIXES:
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, kind, masked in scan_text(text):
            problems.append((f"{label}:{number}", f"release scan: possible {kind} ({masked})"))
    return problems


# --- CLI ---------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--docs-dir", type=Path, default=DOCS_DIR)
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check", help="validate all cases and run the release scan")
    p_check.add_argument(
        "--evals-dir", type=Path, default=None,
        help=f"validation package to cross-check eval_readiness against (default: ${EVALS_DIR_ENV})",
    )
    sub.add_parser("next-id", help="print the next free case id")
    p_scan = sub.add_parser("scan", help="run the release scan on given files or directories")
    p_scan.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)

    if args.command == "scan":
        findings = release_scan(args.paths)
        for path, message in findings:
            print(f"{path}: {message}", file=sys.stderr)
        print(f"release scan: {len(findings)} finding(s)")
        return 1 if findings else 0

    cases = load_cases(args.docs_dir)
    if args.command == "next-id":
        print(next_id(cases))
        return 0

    evals_dir = args.evals_dir or (Path(os.environ[EVALS_DIR_ENV]) if os.environ.get(EVALS_DIR_ENV) else None)
    instances = None
    problems = []
    if evals_dir is None:
        print(
            f"note: validation package not given (--evals-dir or {EVALS_DIR_ENV}); "
            "eval_readiness: automated not cross-checked"
        )
    elif not (evals_dir / INSTANCES_SUBDIR).is_dir():
        problems.append((str(evals_dir), f"validation package has no {INSTANCES_SUBDIR}/ folder"))
    else:
        instances = load_instances(evals_dir)
    problems += validate(cases, instances)
    findings = release_scan(repository_files(args.docs_dir.parent))
    for path, message in problems + findings:
        print(f"{path}: {message}", file=sys.stderr)
    checked = f"{len(cases)} case(s)"
    if instances is not None:
        checked += f" and {len(instances)} evaluation instance(s)"
    print(f"{checked} checked, {len(problems)} problem(s); release scan: {len(findings)} finding(s)")
    return 1 if problems or findings else 0


if __name__ == "__main__":
    sys.exit(main())
