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
skills/ubem-casebook-add/      agent skill for adding a case via a PR
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

### Agent skill: `ubem-casebook-add`

[`skills/ubem-casebook-add`](skills/ubem-casebook-add/SKILL.md) lets a coding
agent add a case end to end. It drafts and validates the case, commits it on a
local `case/<category>/<case-name>` branch, shows a preview, and on approval
pushes the branch and opens a pull request.

```text
ubem-casebook-add [case name] [case category] [context] [fetch-context=false] [skip-approval=false]
```

- Case name and category are inferred when omitted.
- By default only the text passed to the skill is used. With
  `fetch-context=true` the agent also draws on the conversation and session
  context.
- With `skip-approval=true` the preview is skipped and the agent goes straight
  to the pull request. Validation and the confidentiality check still run.
- If pushing fails (no remote, no write access, GitHub auth problems), the
  branch stays local and the agent says why.

Install with [`npx skills`](https://github.com/vercel-labs/skills), from GitHub
or from a local checkout:

```bash
npx skills add <owner>/<repo> --skill ubem-casebook-add -g
```

```bash
npx skills add ./ --skill ubem-casebook-add -g
```

The skill works on a local checkout of this repository. Run your agent from
inside the checkout, or set `UBEM_CASEBOOK_DIR` to its path.

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

## License

This repository is licensed under the
[Creative Commons Attribution 4.0 International License (CC BY 4.0)](LICENSE).
You may share and adapt the cases for any purpose, including commercially, as
long as you give appropriate credit, link to the license, and indicate if
changes were made.

## Deployment

`.github/workflows/docs.yml` validates and builds the site on every push and
pull request, and deploys `main` to GitHub Pages. In the repository settings,
set **Pages → Build and deployment → Source** to **GitHub Actions**.
