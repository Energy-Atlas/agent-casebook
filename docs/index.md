# UBEM Agent Casebook

A casebook of expected agent behavior in urban building energy modeling (UBEM)
workflows.

Agents that set up, run, calibrate, and interpret urban-scale energy models
make many judgment calls that never show up as errors: which data to trust,
which parameter to adjust, when to stop and ask. This casebook records those
calls as short cases. Each describes a situation, what a competent agent
should do, what it should avoid, and why.

## How to read a case

Every case has the same parts:

| Section | Answers |
| --- | --- |
| **Situation** | What is happening, and what data and tools are available? |
| **Expected behavior** | What should a competent agent investigate, decide, communicate, or execute? |
| **Undesirable behavior** | What should it avoid, and under what conditions? |
| **Rationale** | Why does the distinction matter? Which domain knowledge applies? |
| Observation | What actually happened, for observed cases. |
| Evaluation potential | How the behavior could be assessed, and whether a mocked scenario could reproduce it. |
| References | Literature and pointers to supporting material. |

Front matter fields such as origin, data availability, and evaluation
readiness are described in the [case format](guide/case-format.md).

## Categories

Cases are grouped by the workflow stage where the behavior occurs:

| Stage | Covers |
| --- | --- |
| [Preprocessing](cases/preprocessing/index.md) | Acquiring and cleaning geometry, attributes, meter, and weather data |
| [Model config](cases/model-config/index.md) | Archetypes, templates, constructions, schedules, systems, zoning |
| [Simulation](cases/simulation/index.md) | Running and monitoring simulations, handling failures and warnings |
| [Validation](cases/validation/index.md) | Checking outputs against measured or reference data without tuning |
| [Calibration](cases/calibration/index.md) | Choosing and adjusting uncertain inputs to match measurements |
| [Results](cases/results/index.md) | Aggregating, interpreting, and communicating results and uncertainty |
| [Scenarios](cases/scenarios/index.md) | Retrofit, electrification, climate, and policy scenarios |

See the [full catalog](cases/index.md) or browse by [tag](tags.md).

## Contributing

Cases are mostly written with coding agents. See
[contributing](guide/contributing.md).
