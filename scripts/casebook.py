"""Casebook schema, validator, CLI, and MkDocs hook.

Used two ways:

- As an MkDocs hook (see ``hooks`` in mkdocs.yml): validates every case and
  logs problems as warnings, so ``mkdocs build --strict`` fails on them; adds a
  metadata table to case pages; fills ``<!-- casebook:index -->`` markers with
  case tables; orders case categories in workflow order in the navigation.
- As a CLI::

      python scripts/casebook.py check     # validate all cases
      python scripts/casebook.py next-id   # print the next free case id
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
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


def validate(cases: list[Case]) -> list[tuple[str, str]]:
    problems = [(c.path, e) for c in cases for e in validate_case(c)]
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
    cases = load_cases(Path(config["docs_dir"]))
    for path, message in validate(cases):
        log.warning(f"{path}: {message}")
    _cases.clear()
    _cases.update({c.path: c for c in cases if not c.error})
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
    return "\n".join([
        "| ID | Stage | Origin | Recorded | Data availability | Eval readiness |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| `{m['id']}` | [{m['stage']}](index.md) | {m['origin']} | {m['date']} "
        f"| {m['data_availability']} | {m['eval_readiness']} |",
    ])


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


# --- CLI ---------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--docs-dir", type=Path, default=DOCS_DIR)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="validate all cases")
    sub.add_parser("next-id", help="print the next free case id")
    args = parser.parse_args(argv)

    cases = load_cases(args.docs_dir)
    if args.command == "next-id":
        print(next_id(cases))
        return 0

    problems = validate(cases)
    for path, message in problems:
        print(f"{path}: {message}", file=sys.stderr)
    print(f"{len(cases)} case(s) checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
