# UBEM Agent Casebook

A casebook of expected agent behavior in urban building energy modeling (UBEM)
workflows: setup, simulation, calibration, and result interpretation.

Each case is a short Markdown record of a situation an agent may face, what a
competent agent should investigate, decide, communicate, or execute, what it
should avoid, and why. Cases come from expert practice, observed agent runs,
and the literature. Over time they are meant to seed evaluation scenarios.

The casebook is published as a static site with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

## Layout

```text
docs/
  index.md                     site home
  cases/<category>/<case>.md   case records
  cases/<category>/index.md    category overview (case table is generated)
  guide/                       case format and contribution guide
templates/case.md              template for new cases
scripts/casebook.py            schema, validator, and MkDocs hook
AGENTS.md                      instructions for coding agents
```

Case categories follow the workflow: `preprocessing`, `model-config`,
`simulation`, `validation`, `calibration`, `results`, `scenarios`.

## Contributing

Most cases are expected to be written with coding agents such as Claude Code.
Agents and humans follow the same rules in [AGENTS.md](AGENTS.md); the case
format is documented in [docs/guide/case-format.md](docs/guide/case-format.md).

Commits use [Conventional Commits](https://www.conventionalcommits.org/) with a
scope, e.g. `feat(calibration): add area-benchmarking case`.

## Local preview

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# .venv/bin/python -m pip install -r requirements.txt     # macOS/Linux
```

```bash
python scripts/casebook.py check
```

```bash
mkdocs serve
```

`mkdocs build --strict` fails on any case that breaks the schema, so the
check also runs as part of every build.

## Deployment

`.github/workflows/docs.yml` validates and builds the site on every push and
pull request, and deploys `main` to GitHub Pages. In the repository settings,
set **Pages → Build and deployment → Source** to **GitHub Actions**.
