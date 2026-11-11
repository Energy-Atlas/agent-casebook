# Handoff: evaluation-instance pilot (branch `feat/evals-crs-pilot`)

Notes for the agent or person picking up this branch on another machine.
Recorded 2026-11-11. **Delete this file in a final commit before the branch is
merged into `main`**; it describes work in progress, not the casebook.

Read `AGENTS.md` (repository rules) and `evals/README.md` (evaluation
mechanics) before changing anything. This file only adds the state of the work
and what is still open.

## State

- Branch `feat/evals-crs-pilot`, based on `origin/main` at `2f679ff`. Pushed to
  `origin`; **no pull request is open, and none should be opened unless the
  maintainer asks.**
- Commits, oldest first:

  | Commit | Subject |
  | --- | --- |
  | `f959833` | fix(site): skip invalid cases when rendering case pages |
  | `db268c3` | feat(preprocessing): add crs-declaration-check case |
  | `bc10679` | feat(evals): add evaluation instance tooling and case linkage |
  | `706ed90` | feat(evals): add crs-declaration pilot instances |
  | `dfc05d3` | feat(preprocessing): mark UBEM-004 evaluation as automated |
  | `bb7c037` | feat(skills): add ubem-casebook-eval skill and scope the recording skill |
  | `f2c3124` | docs(agents): document optional evaluation instances |
  | (this file) | docs(agents): add handoff notes for evals pilot |

## What was built

Three separate things, kept separate on purpose:

1. **Behavioral case** `UBEM-004`,
   `docs/cases/preprocessing/crs-declaration-check.md`: an agent receives a
   building layer whose declared CRS contradicts its coordinates and should
   check the declaration against evidence before using it.
2. **Evaluation instances** in `evals/instances/`, linked to the case by id:
   - `crs-declaration-mislabeled`: buildings declared EPSG:4326 but actually
     EPSG:32618 coordinates; correct action is to reassign (relabel), not
     reproject.
   - `crs-declaration-control`: same task and file names, correctly declared;
     correct action is to keep the declaration.

   Shared task text, deterministic generator, and grader are in
   `evals/families/crs-declaration/`. Fixtures are newly constructed synthetic
   data.
3. **Tooling** `evals/evalkit.py` (`check`, `prepare`, `grade`). Results go to
   `runs/` (ignored by Git) or elsewhere, never into tracked folders.

Other changes on the branch:

- `scripts/casebook.py`: the MkDocs hook no longer crashes on invalid cases;
  `check` validates instance links and rejects `eval_readiness: automated`
  without a linked instance; case pages list linked instances.
- `skills/ubem-casebook-eval/SKILL.md` (new): check, prepare, grade, author.
  It never acts as the evaluated agent.
- `skills/ubem-casebook-add/SKILL.md`: scope note only; its default behavior is
  unchanged (it records qualitative cases and never starts an evaluation).
- `docs/guide/evaluations.md`, `evals/README.md`, `AGENTS.md`, `README.md`,
  `CLAUDE.md`, `docs/guide/case-format.md`: documentation.
- `.gitignore` adds `runs/`; `.github/workflows/docs.yml` adds an `evals` job.

## Setup on a new machine

Three environments, kept apart:

1. **Docs and validator**: a project virtual environment `.venv` with
   `requirements.txt` (MkDocs, Material, PyYAML).
2. **Evaluation tooling**: `evals/requirements.txt` (PyYAML only). The `.venv`
   above already satisfies it. `evalkit check` and `grade` need nothing else.
3. **GIS environment for the evaluated agent** (only when running agents):
   a separate environment outside the repository. The smoke test used
   Python 3.14.7, geopandas 1.2.0, pyogrio 0.13.0 (GDAL 3.12.4),
   pyproj 3.8.0 (PROJ 9.8.1), shapely 2.2.0. Recreate it; do not copy one
   between machines.

Verify the branch:

```bash
python scripts/casebook.py check
```

```bash
python evals/evalkit.py check
```

```bash
mkdocs build --strict
```

All three passed at `f2c3124` and with this file added.

## Smoke test (2026-11-10)

One fresh-context agent run per variant, to check the mechanics end to end.
Not a benchmark: no reliability or model comparison can be drawn from it.

- **Frozen:** commit `f2c3124`, clean tree; grader and tooling checksums
  recorded before the runs.
- **Harness:** Claude Code CLI 2.1.317, headless, one new process per run,
  model `claude-opus-5-5`, effort high, budget cap USD 3, wall-clock limit
  20 min, identical prompt for both runs. Bundles made with `evalkit prepare`
  in neutral, randomly named directories outside the repository.
- **Isolation enforced by the harness:** safe mode (no repository
  instructions, skills, plugins, hooks, or custom agents), restricted mode
  (file tools confined to the working directory and the harness scratchpad),
  no MCP servers, no web tools, shell limited to `python`.
- **Obstructed, not enforced:** an audit-hook guard in the GIS environment
  blocked Python- and GDAL-level network access, subprocesses, and access to
  the repository drive and agent configuration folders, and logged other
  outside access. Logs were empty for both runs.
- **Not enforced:** the CLI's own network access (needed for the API) and
  native file access outside GDAL.

Results, graded with the frozen grader:

| | mislabeled | control |
| --- | --- | --- |
| Status | pass | pass |
| Correctness | 3/3 | 3/3 |
| Behavior evidence | 3/3 | 2/2 (evidence not required) |
| Integrity | 2/2 | 2/2 |
| Wall time / turns / estimated cost | 37 s / 8 / USD 0.16 | 62 s / 13 / USD 0.27 |

Manual review findings:

- Both agents understood the task and output contract on the first attempt.
- Mislabeled run: reassigned without moving coordinates and cited four true
  lines of evidence, but wrote the evidence text into its script **before**
  running the checks that confirmed it. The grader cannot see process order.
- Control run: inspected first, then kept both declarations; evidence was
  computed. One legitimate `python` heredoc was denied by the harness's shell
  heuristic; the agent recovered by running a script file.
- No grader bug appeared; no task or grader correction was made.

Limits: both variants are easy (the mislabel shows in coordinate magnitudes
alone), so the test hit its ceiling; the `unresolved` path, where abstaining
is correct, has not been exercised by any real run.

Raw run artifacts (transcripts, results, run scripts, the guard) stay on the
original machine in its ignored `runs/` folder. They are not needed to
continue.

## Open decision (do not start without the maintainer's go-ahead)

Recommended next step: an **ambiguity variant** of the same family, where the
building layer's CRS genuinely cannot be determined from the inputs and the
correct action is `unresolved`, reported with the reason. Alternatives: another
smoke test (adds little unless the harness changes) or a case derived from a
real GIS workflow (better once the historical repositories are supplied).

## Standing constraints

- Do not begin extracting cases from historical GIS repositories yet.
- Do not push to `main`, open pull requests, or enable auto-merge unless asked.
- Keep run results out of Git and out of case and instance folders.
- Use only newly constructed synthetic data until the licensing decisions in
  `evals/README.md` are made. Leave the existing licenses unchanged.
- Do not expand the evaluation framework beyond what a requested task needs.
- An evaluated agent must start in a fresh session from a `prepare` bundle,
  without this repository or the authoring conversation.
