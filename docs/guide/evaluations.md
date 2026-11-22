# Evaluation instances

Cases describe behavior. Some cases also have **evaluation instances**:
concrete, runnable versions of the situation that an agent can attempt and that
can be graded. They are optional. A case without one is complete, and most
cases will never have one.

## Three separate things

| | What it is | Where it lives |
| --- | --- | --- |
| **Case** | The general situation, the expected and undesirable behavior, and why | This casebook: `docs/cases/<stage>/<case>.md` |
| **Evaluation instance** | Concrete inputs, the task the agent receives, what it may use and must return, the reference, the acceptance rules, and a grader | A separate validation package, together with the environments and graders |
| **Run result** | What one agent configuration actually produced on one instance, and how it was graded | Outside the casebook; never committed with cases |

The validation package is a separate repository,
`Energy-Atlas/ubem-agent-evals`. It is private for now, so its instances
cannot yet be inspected from this site.
Private held-out material, such as instances built on non-public data or kept
back from public development, is kept outside both the casebook and the
package.

An instance names the case ids it exercises. A case that has instances names
them by instance id in its *Evaluation potential* section and is marked
`eval_readiness: automated`; nothing else in the case changes. Being evaluable
is unrelated to the `validation` stage: an instance can exercise a case from
any stage.

The casebook check can confirm that every case marked `automated` has an
instance in a local copy of the package:

```bash
python scripts/casebook.py check --evals-dir <path-to-validation-package>
```

Without the package location (`--evals-dir` or the `UBEM_EVALS_DIR`
environment variable), the check skips this cross-check and prints a note.

## What the evaluated agent receives

Only the files the instance lists as agent-facing: a task description and the
inputs. Never the case text, the reference, the acceptance rules, or other
instances. Faulty and control variants share the same task text, so the task
does not reveal which one the agent has.

Assembling such a bundle is not the same as isolating the agent. An evaluated
agent must start in a fresh session, without the conversation in which the
instance was written and without access to the casebook, the package, or the
references. The run record states how that was done.

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

Grading distinguishes a failed agent from a failed evaluation: an unreadable
submission, a broken evaluation environment, and a crashed grader are reported
separately from a failed criterion.

Public instances are development references for the evaluation mechanics, not
a hidden benchmark. A score on them says nothing about performance on real
GIS workflows.
