# AGENTS.md

Instructions for coding agents (and humans) working in this repository.

## What this repository is

A public casebook of expected agent behavior in urban building energy modeling
(UBEM) workflows. Each case is one Markdown file describing a situation, the
behavior a competent agent should show, the behavior it should avoid, and the
reasoning behind the distinction. The site is built with MkDocs Material.

The casebook records **behavior**, not software. Cases should stay valid
regardless of which simulation engine, UBEM framework, or agent tooling is used.

## Layout

| Path | Purpose |
| --- | --- |
| `docs/cases/<category>/<case-name>.md` | One case record |
| `docs/cases/<category>/index.md` | Category overview; its case table is generated |
| `docs/cases/index.md` | Catalog of all cases; its table is generated |
| `docs/guide/case-format.md` | Human-readable case schema |
| `templates/case.md` | Template for new cases |
| `scripts/casebook.py` | Schema, validator, CLI, and MkDocs hook |
| `skills/ubem-casebook-add/SKILL.md` | Installable agent skill that adds a case via branch and PR |
| `skills/ubem-casebook-eval/SKILL.md` | Agent skill for checking, preparing, and grading evaluation instances |
| `evals/` | Optional evaluation instances and their tooling (`evals/README.md`) |
| `docs/guide/evaluations.md` | Concepts: case, evaluation instance, run result |
| `mkdocs.yml` | Site configuration |

Categories, in workflow order: `preprocessing`, `model-config`, `simulation`,
`validation`, `calibration`, `results`, `scenarios`. Do not add a category
without being asked; if one is needed, add it to `CATEGORIES` in
`scripts/casebook.py`, create `docs/cases/<category>/index.md`, and update
`docs/guide/case-format.md`.

## Adding a case

1. Pick the category that matches the workflow stage where the behavior occurs.
2. Pick a short kebab-case file name that names the behavior or situation,
   e.g. `area-benchmarking.md`. Search existing cases first; extend a related
   case rather than duplicating it.
3. Get the next free id:
   ```bash
   python scripts/casebook.py next-id
   ```
4. Copy `templates/case.md` to `docs/cases/<category>/<case-name>.md` and fill
   it in. Delete the prompt text under each heading.
5. Validate and build:
   ```bash
   python scripts/casebook.py check
   ```
   ```bash
   mkdocs build --strict
   ```
6. Commit the case on its own (see Commits).

You do not need to edit `mkdocs.yml`, the catalog, or the category index pages:
navigation and case tables are generated from the files and their front matter.

The `ubem-casebook-add` skill automates these steps on a separate branch and
opens a pull request. When you change the case rules, the template, or the
CLI, check that `skills/ubem-casebook-add/SKILL.md` still matches.

## Case rules

The validator enforces these; `docs/guide/case-format.md` explains them.

- Front matter fields: `id`, `title`, `date`, `origin`, `stage`, `tags`,
  `data_availability`, `eval_readiness`. No other fields.
- `id` is `UBEM-` plus a zero-padded number, unique, never reused or renumbered.
- `stage` equals the category folder the file is in.
- `eval_readiness: automated` requires an evaluation instance in
  `evals/instances/` that links to the case id. Otherwise choose
  `conceptual`, `specified`, or `mockable`.
- `date` is the date the case was recorded (`YYYY-MM-DD`).
- `tags` are kebab-case. Reuse existing tags where they fit (see the Tags page
  or `grep -h "^tags:" -r docs/cases`).
- Body sections are H2 headings in this order: `Situation`,
  `Expected behavior`, `Undesirable behavior`, `Rationale`, then optionally
  `Observation`, `Evaluation potential`, `References`. Drop the `(optional)`
  suffix from the template; delete optional sections you do not use.
- No H1 in the body. The page title comes from `title`.

## Writing guidance

- Write the situation concretely enough that two readers would picture the
  same scenario: what data and tools are available, what the agent has just
  observed.
- State expected and undesirable behavior as observable actions and decisions,
  including what the agent should communicate to the user and when it should
  stop and ask.
- Name conditions. "Avoid X" is weaker than "avoid X when Y, because Z".
- Put domain knowledge in Rationale: modeling assumptions, typical error
  sources, consequences downstream.
- Describe tools by function ("a benchmark query tool", "an evidence retrieval
  tool"), not by product, unless the product matters to the behavior.
- Link related cases with relative links, e.g. `[UBEM-001](area-benchmarking.md)`.
- Cite only references you can verify. Do not invent citations, URLs, or data.

## Evaluation instances (optional)

A case is complete without evaluation material. Adding a case never requires
an instance, and recording a case never runs an evaluation.

When asked to add or change an evaluation instance:

- Put it in `evals/instances/<instance-id>/`, never under `docs/` (anything
  there is published and treated as a case). Link it to existing case ids in
  `instance.yaml`; the case file does not change except `eval_readiness`.
- Keep `agent/` (what the evaluated agent receives) free of case text, case
  or instance ids, and reference answers. Give faulty and control variants the
  same task text and file names.
- Describe instances as public development references, not hidden
  benchmarks. List what the outputs cannot establish under `not_assessed`.
- Include a correct sample submission and targeted incorrect ones with the
  exact criteria each must fail.
- Run `python evals/evalkit.py check` as well as the case checks.
- Keep run results out of Git (`runs/` is ignored) and out of case and
  instance folders.
- Use only newly constructed synthetic data until the licensing decisions in
  `evals/README.md` are made for third-party data and code.

An agent being evaluated must start in a fresh session from a bundle made by
`python evals/evalkit.py prepare`, without the authoring conversation or this
repository. `prepare` assembles a clean bundle; it does not enforce isolation.

## Confidentiality

This repository is public. `data_availability: private` or `restricted` means
the data behind a case is not shared, so the case must not contain it.

- No real addresses, owner names, account numbers, meter ids, or
  building-identifying details of private data.
- No excerpts of private datasets, internal reports, or client deliverables.
- Point to restricted material only with a non-identifying description,
  e.g. "internal calibration notes, 2026 campus project".

If a request would put such material in a case, stop and ask.

## License

The repository is licensed under CC BY 4.0 (`LICENSE`), so everything added
must be licensable under it. Write cases in your own words; do not copy
figures, tables, or passages from papers, standards, or other copyrighted
sources. Cite them under References instead.

## Commits

- Default branch: `main`.
- Conventional Commits with a scope: `type(scope): subject`, imperative,
  lower case, no trailing period.
- Types: `feat` (new case or site feature), `fix` (correction), `docs`
  (guide, README, agent docs), `chore`, `ci`, `refactor`.
- Scope is the case category for case changes, otherwise the area touched
  (`site`, `template`, `schema`, `agents`, `skills`, `evals`).

Examples:

```text
feat(calibration): add area-benchmarking case
fix(calibration): correct benchmark units in UBEM-001
feat(site): add generated case catalog
docs(agents): clarify tag reuse
```

Do not push or open pull requests unless asked.
