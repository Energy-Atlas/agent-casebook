# Evaluation instances

Cases describe behavior. Some cases also have **evaluation instances**:
concrete, runnable versions of the situation that an agent can attempt and that
can be graded. They are optional. A case without one is complete, and most
cases will never have one.

!!! note "Pilot"
    The current instances use synthetic inputs and serve as **public
    development references** for building and checking the evaluation
    mechanics. They are not a hidden benchmark, and a score on them says
    nothing about performance on real GIS workflows.

## Three separate things

| | What it is | Where it lives |
| --- | --- | --- |
| **Case** | The general situation, the expected and undesirable behavior, and why | `docs/cases/<stage>/<case>.md` |
| **Evaluation instance** | Concrete inputs, the task the agent receives, what it may use and must return, the reference, the acceptance rules, and a grader | `evals/instances/<instance-id>/`, outside the published site |
| **Run result** | What one agent configuration actually produced on one instance, and how it was graded | Outside the repository by default (`runs/`, ignored by Git) |

An instance names the case ids it exercises. The case page lists linked
instances, but the case file does not change. Being evaluable is unrelated to
the `validation` stage: an instance can exercise a case from any stage.

## What the evaluated agent receives

Only the files the instance lists as agent-facing: a task description and the
inputs. Never the case text, the reference, the acceptance rules, or other
instances. Faulty and control variants share the same task text, so the task
does not reveal which one the agent has.

Assembling such a bundle is not the same as isolating the agent. The tooling
copies the right files into a clean directory outside the repository; it does
not block network access or restrict the filesystem. An actual evaluated agent
must start in a fresh session, without the conversation in which the instance
was written and without access to the repository or references. The run record
states how that was done.

## What grading can claim

Results keep criterion kinds apart instead of merging them into one score:

- **Correctness:** outputs against the reference, with tolerances and accepted
  alternatives rather than exact file equality.
- **Behavioral evidence:** behavior the outputs actually establish, for example
  whether a written layer's coordinates were transformed or only relabeled.
  Self-reported decisions are marked as self-reported.
- **Integrity:** whether the report is consistent with the artifacts, and
  whether cited sources exist among the inputs. A cited source that exists is
  not proof that it supports the claim.

Each instance also lists what its outputs cannot establish, such as whether the
agent examined the evidence it cites or would have asked the user. Those need a
transcript or expert review.

Grading distinguishes a failed agent from a failed evaluation: `invalid-output`
(the submission cannot be read), `env-error` (the evaluator's environment or
files are broken), and `grader-error` (the grader crashed) are reported
separately from `fail`.

## Current instances

| Instance | Case | Variant |
| --- | --- | --- |
| `crs-declaration-mislabeled` | [UBEM-004](../cases/preprocessing/crs-declaration-check.md) | Footprint layer declares a geographic CRS but holds projected coordinates |
| `crs-declaration-control` | [UBEM-004](../cases/preprocessing/crs-declaration-check.md) | Same inputs with a correct declaration |

How to check, prepare, and grade instances is described in `evals/README.md`
in the repository.
