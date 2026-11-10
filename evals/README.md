# Evaluation instances

Optional, runnable companions to casebook cases. A case never needs one; a
case without evaluation material is complete. The concepts are described in
`docs/guide/evaluations.md` (published as *Evaluation instances* on the site).

**Status: pilot.** The fixtures and references here are **public development
references**, used to develop and check the evaluation mechanics. They are not
a hidden benchmark: anyone, including a model in training, can read them. A
score on them does not establish performance on real GIS workflows.

## Layout

```text
evals/
  evalkit.py                         check, prepare, grade
  requirements.txt                   PyYAML only; separate from the docs build
  families/<family>/                 shared task text, generator, grader
  instances/<instance-id>/
    instance.yaml                    specification (below)
    agent/                           the only files an agent receives
    reference/                       expected values; never given to the agent
    submissions/<name>/              sample submissions for the grader self-test
runs/                                default result location (repo root, ignored by Git)
```

Everything here is outside `docs/`, so none of it is published on the site or
treated as a case. `scripts/casebook.py check` only verifies that linked case
ids exist and that a case marked `eval_readiness: automated` has an instance.

## Specification (`instance.yaml`)

```yaml
id: crs-declaration-mislabeled    # equals the folder name; kebab-case; never reused
version: 1                        # bump when inputs, reference, or acceptance change
status: development               # public development reference (only value for now)
cases: [UBEM-004]                 # case ids this instance exercises
family: crs-declaration           # shared generator, grader, and task text
summary: >-                       # for maintainers; never shown to the agent
  ...
inputs:
  origin: synthetic               # synthetic | open-data | mixed
  generator: evals/families/crs-declaration/generate.py
  license: ...                    # license of the fixtures
  sources: []                     # third-party sources: name, version, URL, license, checksum
agent:
  files: [task.md, ...]           # copied into the bundle, relative to agent/; nothing else is
  returns: [report.json, ...]     # files the agent writes under output/
  environment: {...}              # what the agent may use; describes, does not enforce
reference: reference/expected.json
grader: evals/families/crs-declaration/grade.py
acceptance: {...}                 # accepted answers and tolerances, passed to the grader
not_assessed: [...]               # behaviors these outputs cannot establish
self_test:                        # sample submissions and the outcome each must get
  - {submission: submissions/correct, status: pass}
  - {submission: submissions/reprojected, status: fail, failed: [crs_action, parcel_join]}
```

Paths starting with `evals/` are relative to the repository root; others are
relative to the instance folder.

## Commands

Install `evals/requirements.txt` (PyYAML) in any environment; the project
`.venv` already has it.

```bash
python evals/evalkit.py check
```

Validates every specification, regenerates the fixtures in a temporary
directory and compares them byte for byte with the committed files, scans
agent-facing files for instance and case ids, and grades every sample
submission against its expected status and failed criteria.

```bash
python evals/evalkit.py prepare crs-declaration-mislabeled --out <empty dir outside the repo>
```

Copies only `agent.files` into the bundle and writes a receipt (instance id,
version, commit, checksums) next to the bundle, not inside it. It refuses a
directory inside the repository, because an agent started there could read the
cases, references, and repository instructions.

```bash
python evals/evalkit.py grade crs-declaration-mislabeled --submission <bundle>/output --run-meta run.json
```

Writes `runs/<timestamp>-<instance>/result.json` unless `--out` is given. Exit
codes: 0 pass, 1 fail, 2 invalid-output, 3 env-error, 4 grader-error.

## What `prepare` does and does not do

`prepare` assembles a clean bundle. It does **not** enforce isolation: it does
not block network access, restrict the filesystem, or control what context an
agent harness loads. For an actual evaluation, whoever launches the agent must:

- start the agent in a **fresh session**, without the authoring conversation,
  the casebook checkout, the case text, or references;
- use the bundle as its working directory, outside any repository whose
  instructions it would load;
- record how the agent was isolated (in `--run-meta`), since the result cannot
  establish it.

## Result record

`result.json` (schema `ubem-casebook-eval-result/0.1`):

| Field | Content |
| --- | --- |
| `status` | `pass`, `fail`, `invalid-output` (schema failed), `env-error` (evaluator environment or instance files broken), `grader-error` (grader crashed) |
| `summary` | Per criterion kind: counts and outcome. Kinds are kept apart, never merged into one score |
| `criteria` | One entry per criterion: `id`, `kind`, `outcome` (`pass`, `fail`, `not-evaluated`), `detail`, `diagnostics` |
| `not_assessed` | Behaviors the outputs cannot establish, copied from the specification |
| `instance` | id, version, linked cases, and checksums of the specification, reference, and agent files |
| `grader`, `casebook` | grader path and checksum; casebook commit and whether the tree was dirty |
| `submission` | path and file checksums |
| `run` | caller-supplied metadata: agent harness, model, settings, isolation, fresh context |
| `diagnostics` | evaluator-side messages, e.g. tracebacks for env-error or grader-error |

Criterion kinds:

- `schema`: the submission can be read at all. A failure makes the status
  `invalid-output`, and the other criteria are not evaluated.
- `correctness`: the outputs match the reference within tolerance.
- `behavior-evidence`: behavior that the outputs establish, from the written
  artifacts or from what the agent reports. Self-reported items are labeled as
  such in `detail`.
- `integrity`: internal consistency and reference integrity, such as whether
  cited sources exist among the inputs. A cited source that exists is **not**
  evidence that it supports the claim.

Results are run artifacts. Keep them out of the case and instance folders and
out of Git. Bring findings back as new or revised cases through the normal
contribution workflow.

## Adding an instance

Follow the pilot family (`families/crs-declaration/`):

1. Link it to an existing case id. Write the qualitative case first if needed.
2. Construct inputs with a deterministic generator. For third-party data,
   record the decisions listed under *Licensing* first.
3. Write the agent-facing task so that it does not reveal the variant: control
   and faulty variants share the same task text and file names.
4. Write the reference and acceptance rules, including accepted alternatives
   and tolerances, and the list of what the outputs cannot establish.
5. Add a correct sample submission and targeted incorrect ones, each with the
   exact criteria it must fail.
6. Run `python evals/evalkit.py check` and `python scripts/casebook.py check`.

## Licensing

The pilot fixtures are newly constructed synthetic data and fall under the
repository license (CC BY 4.0), like everything else here for now. Decisions
needed before going further:

- **Code license.** CC BY 4.0 is not designed for software. Decide whether
  `evals/` and `scripts/` code should get a software license (e.g. MIT or
  Apache-2.0) before distributing the tooling as a separate package.
- **Third-party data.** Before adding open-data-derived fixtures, check each
  source's license. Share-alike database licenses (OpenStreetMap's ODbL, for
  example) cannot be relicensed under CC BY 4.0. Prefer downloading at prepare
  time with a pinned version and checksum over committing extracts, and
  record source, version, license, and attribution in `inputs.sources`.
- **Confidentiality.** The repository's confidentiality rules apply to
  fixtures and references as much as to case text: no private data or
  identifying details.
