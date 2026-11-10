---
name: ubem-casebook-eval
description: >-
  Check, prepare, grade, or author optional evaluation instances in the UBEM
  Agent Casebook (pilot). Use only when the user explicitly asks to check
  evaluation instances, prepare a task bundle for an agent, grade a
  submission, or add or revise an evaluation instance. Never use it to record
  a case (that is ubem-casebook-add), and never start an evaluation because a
  case was recorded.
argument-hint: "check [instance] | prepare <instance> <out-dir> | grade <instance> <submission-dir> | author <instance-id>"
---

# ubem-casebook-eval

Operate the casebook's optional evaluation instances with
`evals/evalkit.py`. Recording cases, running evaluations, and publishing are
separate: this skill never records cases, never pushes, and never opens pull
requests unless the user asks.

The instances are **public development references**, not a hidden benchmark.
Say so whenever you report results, and do not present a score as evidence of
performance on real workflows.

## 1. Locate the casebook

Find the repository as `ubem-casebook-add` does (step 2 of that skill): the
git top level of the working or session project directory, then
`UBEM_CASEBOOK_DIR`. In addition, the directory must contain
`evals/evalkit.py`. Do not search the disk or clone. Call it `REPO`.

Read `REPO/AGENTS.md` (section *Evaluation instances*) and
`REPO/evals/README.md`. They are authoritative where they differ from this
skill.

Python: `REPO/.venv` if present, otherwise any interpreter with PyYAML. The
tooling needs only `evals/requirements.txt`. Never install packages globally.
If PyYAML is missing, ask before installing it into a temporary virtual
environment.

## 2. Operations

Run commands from `REPO`. Do only the operation the user asked for.

### check

```bash
<python> evals/evalkit.py check [instance-id ...]
```

Report the result line and every problem. Problems are about the instance
(specification, fixtures that no longer match the generator, leaked ids,
sample submissions graded differently than expected), not about any agent.

### prepare a bundle for an evaluated agent

```bash
<python> evals/evalkit.py prepare <instance-id> --out <new empty dir>
```

- Choose a new, empty directory **outside** the casebook and outside any
  repository whose instructions an agent harness would load (for example, a
  fresh temporary directory). `prepare` refuses directories inside the
  casebook.
- Give the user the bundle path and the receipt path. The receipt identifies
  the instance; keep it away from the evaluated agent.
- Explain that `prepare` assembles a clean bundle but does **not** enforce
  isolation: no network or filesystem restrictions.
- In this pilot, do not launch the evaluated agent yourself, and never act as
  the evaluated agent: you have seen the instance, its references, and this
  conversation. The user starts a separate agent in a **fresh session** with
  the bundle as its working directory, no access to the casebook or
  references, and the bundle's `task.md` as its only instructions. The agent
  writes its outputs to `output/` inside the bundle.
- Do not paste case text, references, or hints into the evaluated agent's
  prompt.

### grade a submission

1. Write a run-metadata JSON file **outside the repository** with what the
   user tells you: agent harness and version, model, settings, date, whether
   the session was fresh, and how isolation was handled (network, filesystem).
   Record unknown values as `"unknown"`; do not guess.
2. Grade:

   ```bash
   <python> evals/evalkit.py grade <instance-id> --submission <bundle>/output --run-meta <file>
   ```

   The result goes to `REPO/runs/` (ignored by Git) unless `--out` is given.
3. Report from the result file:
   - the `status`, and the outcome for each criterion kind (`correctness`,
     `behavior-evidence`, `integrity`), kept separate, not merged into one
     score;
   - each failed criterion with its diagnostics;
   - the `not_assessed` list, as things this result does not establish;
   - for `env-error`, `grader-error`, or `invalid-output`, say that the
     problem lies with the evaluator, the grader, or an unreadable submission,
     not a judged agent failure, and quote the diagnostic.
4. Claim only what the criteria establish. Self-reported items are only what
   the agent said. A cited source that exists among the inputs is not
   evidence that it supports the claim.
5. Never commit results, and never copy them into case or instance folders.
   If a run reveals a behavior worth recording, offer to record it as a case
   with `ubem-casebook-add`. That is a separate request the user must approve.

### author or revise an instance

Only on an explicit request.

1. The instance must link to an existing case id. If the case does not exist
   yet, record it first with `ubem-casebook-add`, as its own commit.
2. Work on a new branch, not `main`, for example `evals/<instance-id>`. Use a
   separate worktree if the user's checkout has other work, as in
   `ubem-casebook-add` step 3.
3. Follow *Adding an instance* in `evals/README.md` and the pilot family in
   `evals/families/crs-declaration/`:
   - a deterministic generator;
   - newly constructed synthetic data only, until the licensing decisions in
     `evals/README.md` are made;
   - identical task text and file names across faulty and control variants;
   - acceptance rules with accepted alternatives and tolerances;
   - a `not_assessed` list;
   - a correct sample submission and targeted incorrect ones with the exact
     criteria each must fail.
4. Apply the confidentiality rules in `AGENTS.md` to fixtures and references
   as well as text.
5. Run `<python> evals/evalkit.py check`, `<python> scripts/casebook.py check`,
   and `<python> -m mkdocs build --strict --site-dir <tmpdir>/site`. Fix
   problems until all pass. Treat a missing MkDocs as an environment
   problem, as `ubem-casebook-add` does.
6. Commit with `feat(evals): add <instance-id> instance` (or `fix(evals): ...`),
   plus your usual trailers. Change a case's `eval_readiness` to `automated`
   in a separate `feat(<category>): ...` commit.
7. Show the user the branch, commits, and check results. Push and open a pull
   request only if asked, following `ubem-casebook-add` step 7.
