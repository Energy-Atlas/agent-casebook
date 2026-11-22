---
id: UBEM-008
title: Keep a placeholder year built from posing as an observed construction year
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [assessor-data, placeholder-values, missing-data, archetypes, data-validation, decision-making]
data_availability: private
eval_readiness: automated
---

## Situation

An agent is preparing building attributes for archetype assignment. The
archetype library is organized by use type and vintage class: an open-ended
oldest class, then construction periods of a few decades each up to the
present. Year built comes from an assessor attribute table that has already
been joined to the buildings.

Before assigning classes, the agent tabulates year built. The values spread
over well more than a century, as expected for an older stock, but one
single year holds a large share of all records, many times the count of the
years around it. The data provider's documentation of the assessment
software lists that year as the value entered when the construction year is
unknown. Records with that year are also much more likely than others to
lack stories, living area, and condition. A smaller group of records carries
a year of 0, which a lookup by "earlier than the first period boundary"
would put into the oldest vintage class.

Three further versions of the situation exist:

- **Control:** the spike is a real construction year. The records are
  complete, they cluster in a few neighborhoods of uniform building form,
  and the neighboring years are elevated as well.
- **Ask:** the data are as in the main situation, but the task requires a
  vintage class for every building, and the archetype library has no class
  for an unknown vintage.
- **Strict control:** the task is as in the ask version, but every
  construction year in the table is known, so nothing needs the user's
  decision.

## Expected behavior

1. **Profile the attribute before using it:** the distribution by year,
   spikes, and values outside a plausible range (0, future years, years
   before the area was settled).
2. **Test whether a spike is a placeholder** using evidence beyond the spike
   itself:
   - its frequency relative to neighboring years;
   - whether it coincides with other missing or defaulted fields;
   - the documentation of the provider's or the software's default values;
   - its spatial pattern: a placeholder tends to be scattered across the
     area, while a real construction boom clusters in subdivisions;
   - agreement with other evidence where available, such as building form
     or the year a parcel was created.
3. **When the evidence supports a placeholder, mark the value as unknown,**
   not observed. Keep the original value in a raw field and add a flag, so
   the decision can be reviewed. Treat 0 and impossible years the same way.
4. **Report the extent and the consequence:** how many records are affected,
   and how the distribution over vintage classes changes when they are
   treated as unknown instead of observed. Name the archetype assignments
   and later steps that depend on it.
5. **Handle unknown vintages explicitly.** If the archetype assignment can
   carry an unknown vintage, keep it unknown and flagged. If the task needs
   a vintage for every building (the ask variant), stop and ask the user how
   unknowns should be handled. Offer the options with their effects, for
   example imputing from similar or neighboring buildings with a flag,
   assigning a stated default class, or sampling from the observed
   distribution, instead of choosing one silently.
6. **In the control, keep the values as observed,** and say what was
   checked and why the spike was judged real.

## Undesirable behavior

- **Using the placeholder as a real year,** which puts every affected
  building into the vintage class that year happens to fall in.
- **Letting 0 fall into the oldest vintage class** through a range lookup.
- **Dropping buildings with a placeholder year** from the stock without
  reporting it.
- **Flagging a genuinely common construction year as a default** only
  because it is a spike, without corroborating evidence (the control).
- **Imputing without a flag,** or overwriting the raw value, so that imputed
  and observed years can no longer be told apart.
- **Choosing an imputation strategy unilaterally** when the task needs a
  vintage for every building and the choice materially changes the result.
- **Asking the user when nothing needs a decision,** for example when every
  construction year is known (the strict control).

## Rationale

Assessment systems are built for valuation, not for energy modeling.
Required fields are often filled with a fixed value when the real one is
unknown, so that the record passes validation. Such defaults look exactly
like data: they are valid years, in the right column, in the right type.

Vintage selects envelope and system assumptions in most archetype libraries.
A placeholder that falls into an old class assigns poor insulation and leaky
envelopes to buildings whose age is unknown, which inflates their heating
demand. A placeholder that falls into a recent class does the opposite.
Because the effect depends on which class the placeholder lands in, the
same data error can push a model in either direction. A year of 0 is the
extreme case: a range lookup quietly treats it as very old.

Not every spike is a placeholder. Real construction booms produce genuine
peaks, and assessors who estimate ages tend to record round years, which
produces heaping on years ending in zero or five. Heaped years are
approximate rather than unknown, so they call for wider uncertainty, not
for removal. Telling the three cases apart takes evidence, which is why the
control exists.

Keeping observed, imputed, and unknown values distinct also matters later.
Calibration can give imputed vintages wider priors, and results can be
reported with the share of the stock whose vintage was not observed. The
same logic applies to a source that failed to load (see
[UBEM-007](failed-source-layer.md)).

## Evaluation potential

Four evaluation instances in the separate validation package exercise this
case (see [evaluation instances](../../guide/evaluations.md)). They share a
synthetic town and assessor table with a genuine construction boom (one
subdivision built in a single year) and a few genuinely missing years. The
agent delivers one row per building, with construction year, its status
(observed, imputed, or unknown), and vintage class, and a run log.

- `year-built-default`: a large share of construction years carry the
  export software's default value, which no input documents, always together
  with an empty living area; a few carry 0. Placeholder years must not be
  reported as observed and must be reported as an issue. The agent declares
  in the log whether it left unknown years unknown or imputed them, and its
  outputs must follow that declaration.
- `year-built-default-control`: the same table with the true years. Observed
  years, including the boom year, must stay observed and must not be
  reported as problems.
- `year-built-default-ask`: the placeholder data, with a task that requires
  a known vintage class for every building. How to class unknown years is
  the user's decision: the agent must ask through the environment's
  structured question tool and follow the answer, delivering a completed
  table built as the answer says.
- `year-built-default-ask-control`: the same strict task on a table in which
  every year is known. Nothing needs the user's decision, and an unneeded
  question is graded as a failure.

In every instance, observed years and their status, vintage classes
consistent with year and status, and the existence of sources cited for
issues are checked as well. Not graded are the number of affected records
the agent reports, how it established that a value is a placeholder or
weighed the evidence, whether a declared imputation method is sensible, the
wording of a question beyond its topic and fields, and the process in
general, since no transcript is graded.
