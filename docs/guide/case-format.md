# Case format

Each case is one Markdown file at `docs/cases/<category>/<case-name>.md`,
starting from `templates/case.md` in the repository root. `scripts/casebook.py` enforces this format; `mkdocs build --strict` fails
when a case breaks it.

## Front matter

```yaml
---
id: UBEM-001
title: Verify data integrity before calibration
date: 2026-10-27
origin: expert-practice
stage: calibration
tags: [data-validation, decision-making, restraint]
data_availability: private
eval_readiness: conceptual
---
```

| Field | Meaning | Values |
| --- | --- | --- |
| `id` | Permanent identifier; never reused or renumbered | `UBEM-` + zero-padded number |
| `title` | Short statement of the expected behavior; used as the page title | text |
| `date` | Date the case was recorded | `YYYY-MM-DD` |
| `origin` | Where the case comes from | see below |
| `stage` | Workflow stage; must equal the category folder | see below |
| `tags` | Topics for cross-cutting browsing | list of kebab-case strings |
| `data_availability` | Whether the data behind the case can be shared | see below |
| `eval_readiness` | How close the case is to an evaluation | see below |

### `origin`

| Value | Meaning |
| --- | --- |
| `expert-practice` | Distilled from practitioner experience |
| `observed` | Seen in an actual agent run; describe it under Observation |
| `literature` | Drawn from published work; cite it under References |
| `synthetic` | Constructed to probe a behavior |

### `stage`

`preprocessing`, `model-config`, `simulation`, `validation`, `calibration`,
`results`, `scenarios`. See the [home page](../index.md#categories) for what
each covers.

### `data_availability`

| Value | Meaning |
| --- | --- |
| `public` | The data behind the case is publicly available |
| `restricted` | Available under agreement or on request |
| `private` | Not shareable; the case describes it without reproducing it |
| `synthetic` | The case relies only on constructed data |

The repository is public. Whatever the value, a case never contains private
data or identifying details.

### `eval_readiness`

| Value | Meaning |
| --- | --- |
| `conceptual` | The behavior is described; no assessment is designed yet |
| `specified` | Pass/fail criteria or a rubric are written down |
| `mockable` | A synthetic or mocked scenario that reproduces the situation is described |
| `automated` | An executable evaluation exists |

## Body

H2 sections, in this order. The first four are required.

1. `Situation`
2. `Expected behavior`
3. `Undesirable behavior`
4. `Rationale`
5. `Observation` (optional)
6. `Evaluation potential` (optional)
7. `References` (optional)

Rules:

- No H1 in the body; the title comes from `title`.
- No other H2 sections. Use H3 inside a section if needed.
- Remove the `(optional)` suffix from the template headings, and delete
  optional sections you do not use.

A metadata table is added to the top of each case page when the site is built,
and case tables on the catalog and category pages are generated from front
matter. Neither needs editing by hand.
