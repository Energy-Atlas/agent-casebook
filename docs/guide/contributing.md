# Contributing

Cases are mostly added through coding agents such as Claude Code. The
repository's `AGENTS.md` holds the rules both agents and people follow; this
page summarizes them.

## Add a case

1. Choose the workflow stage where the behavior occurs; that is the folder.
2. Choose a short kebab-case file name that names the behavior.
3. Get the next id with `python scripts/casebook.py next-id`.
4. Copy `templates/case.md` into `docs/cases/<stage>/` and fill it in.
5. Run `python scripts/casebook.py check` and `mkdocs build --strict`.
6. Commit the case on its own, e.g. `feat(calibration): add area-benchmarking case`.

Navigation and case tables are generated, so no other file needs editing.

## Prompting an agent

A useful request gives the agent the stage, the situation, what the competent
behavior is, and what the tempting mistake is. For example:

> Add a calibration case: the agent finds simulated EUIs match benchmarks but
> total consumption and floor-area share are far above typical, and should
> question conditioned floor area before tuning intensity parameters.

The agent drafts the full record; review it for domain accuracy and for
anything that should not be public.

## What makes a good case

- A concrete situation, with the data and tools available stated.
- Behavior written as observable actions, decisions, and communication.
- Conditions on each "avoid", and the domain reasoning behind it.
- No private data, identifying details, or unverifiable citations.

See the [case format](case-format.md) for the schema.
