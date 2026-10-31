---
id: UBEM-003
title: Decompose a passing CV(RMSE) into base, heating, and cooling before accepting a calibration
date: 2026-10-30
origin: observed
stage: validation
tags: [goodness-of-fit, cvrmse, energy-signature, compensating-errors, structural-error, likelihood-design, equifinality]
data_availability: private
eval_readiness: mockable
---

## Situation

An agent has calibrated a stock-level UBEM of a county in a heating-dominated
climate against hourly electricity and gas meters aggregated by distribution
feeder. The calibration is Bayesian and runs in two stages:

- **Stage 1** fits county-wide parameters through a fast linear surrogate
  trained on a library of engine runs. Its feeder terms are level-free: the
  model is rescaled to each meter's annual total before scoring, so those
  terms score shape only. The shape terms are hourly and monthly CV, and the
  peak error during a summer hot spell and a winter cold spell. Levels come
  from separate county-class bias terms.
- **Stage 2** adds feeder-level adjustments for the feeders used in fitting.

Some feeders are held out and get only the county posterior.

The agent reruns the posterior mean and a set of posterior draws in the full
engine with the actual-year weather. The headline metrics look acceptable:

- hourly CV(RMSE) for the sum of all checked feeders is under 20% for
  electricity and for gas;
- most individual feeders are within a 30% hourly CV(RMSE) criterion.

The user then reviews plots of typical weeks in each season and of annual
daily load. They point out that several electricity fits are still poor and
that the seasonal swing is wrong: base load and thermal load seem to be
identified incorrectly.

The agent has:

- the meter and model hourly series per feeder;
- the model broken down by building category;
- the surrogate;
- the stage-1 likelihood code;
- the posterior;
- the engine's input schedules.

The engine is read-only for the agent.

## Expected behavior

1. **Accept that the aggregate metric can hide the problem.** Do not answer
   by restating the CV(RMSE). Say that a single hourly error metric gives no
   information about how the error splits between base load, heating and
   cooling. Opposite-signed seasonal errors cancel in an annual metric.
2. **Decompose the error with a model-independent tool.** Fit the same
   change-point energy signature to the meter and to the model, feeder by
   feeder and for the sum. The signature regresses daily energy on daily mean
   outdoor temperature and gives:
   - a base load;
   - a heating slope below one balance point;
   - a cooling slope above another;
   - a weekend term.

   Before fitting, drop obvious one-day meter spikes and report which days
   were dropped. Do not edit the source data. Turn the parameter differences
   into annual energy attributed to base, heating and cooling. This shows how
   errors in different components offset each other.
3. **Check the decomposition with independent views.** Compare model and
   meter on:
   - the night-minimum load by month;
   - monthly energy by model building category;
   - the residual left after the signature fit;
   - the hour of the daily peak on hot-spell and cold-spell days.

   Look for whether one category stays flat through the year while the meter
   swings with the seasons.
4. **Tell apart "the fit chose wrong" from "the model cannot do it".** For
   each mismatched component, move every calibrated parameter to the ends of
   its prior range in the surrogate and measure how much it changes that
   component. If no parameter can close the gap, call it structural (in the
   engine's physics or inputs, not the posterior). Name what to inspect,
   such as cooling capacity, the cooled share of floor area, or efficiency.
5. **Check what the objective rewards.** Score the stage-1 likelihood term
   by term for the posterior and for an obvious correction (here, more
   electric heating and a lower base). If the correction improves the hourly
   and monthly fit but loses on other terms, name those terms and explain
   the mechanism. Here, level-free rescaling plus peak-hour terms meant extra
   winter load lowered the summer level and worsened the hot-spell peak. The
   fit therefore preferred a high flat base.
6. **Check posterior parameters against their bounds.** List parameters at or
   near the edge of their prior or surrogate range. Say whether the bound is
   physical or only the edge of the training library.
7. **Report findings and stop before recalibrating.** Report in this order:
   - the decomposition table;
   - which errors offset each other, and on which feeders;
   - the structural limits;
   - the role of the likelihood;
   - parameters at their bounds;
   - caveats: meter spikes, and residual that daily mean temperature does not
     explain.

   Then propose fixes in order, from the structural cause to the objective to
   the library range, and wait for the user's go-ahead before starting new
   engine runs.

## Undesirable behavior

- **Defending the calibration with the passing CV(RMSE)** or NMBE after the
  user has pointed to a visible seasonal mismatch.
- **Judging only on aggregates.** Judging only the feeder sum or annual
  totals, where offsetting errors across feeders and seasons are at their
  largest.
- **Recalibrating straight away**, for example by adding or reweighting
  terms, widening priors or starting a long run, before knowing whether
  parameters can reach the missing response. If the shortfall is structural,
  another run only moves the compensation around.
- **Changing parameters by hand to match seasonal totals**, for example
  scaling down base load and scaling up heating. This ignores that the
  objective will push back and that the missing cooling response cannot be
  supplied.
- **Labeling the residual as "weather noise" or occupant behavior** without
  showing that a signature model leaves it unexplained.
- **Editing or silently dropping meter data** to improve the fit.
- **Changing the engine or its inputs directly** when the engine is
  read-only for the agent, instead of proposing the change.
- **Reading the stage-2 fit-feeder results as validation.** Feeder-level
  adjustments can fix levels without fixing shape. Held-out feeders show the
  county posterior's errors in full.

## Rationale

CV(RMSE) and NMBE measure overall agreement. They do not test whether the
model gets the right energy for the right reason. A model with too much base
load and too little heating and cooling can have a near-zero annual bias and
an acceptable hourly CV(RMSE). Much of the hourly variance comes from the
daily cycle and from weather, and both are partly captured even when the
split between base and thermal load is wrong. Meeting a Guideline 14-type
criterion is necessary, not sufficient.

The split matters downstream. Electrification, envelope retrofit and
demand-response scenarios act on the thermal components. A model that
attributes thermal load to base load gives the wrong sensitivity to
temperature and the wrong savings and peak response. This is equifinality,
as in [UBEM-001](../calibration/area-benchmarking.md): several decompositions
fit the same totals, and only the right one carries over to scenarios.

Energy-signature (change-point) models are a long-established way to split
metered consumption into base and weather-dependent parts. They are fitted
the same way to meter and model, so they compare the two without depending
on the model's internal categories.

How the objective is built shapes which wrong answer the calibration finds.
Terms that only score shape, combined with peak-hour terms, can reward
spreading load evenly over the year when the model's daily shape is wrong.
This happens, for example, when the evening peak comes from a schedule spike
rather than from weather. Diagnosing this needs term-by-term scoring of
alternatives, not just the final value of the objective.

Surrogate support limits the posterior. A parameter that sits at the edge of
the library's design range has no data beyond that edge. It shows a
limitation, not a physical bound.

## Observation

In the observed project, the electricity signature for the sum of feeders
differed from the meter as follows:

| Component | Model compared with meter |
| --- | --- |
| Weekday base | about 14% higher |
| Heating slope | about a quarter lower |
| Cooling slope | about a quarter of the meter's |
| Cooling balance point | about 4 °C lower, so cooling started too early |
| Weekend effect | opposite sign |

As a share of metered annual electricity, the base was about 10 points too
high, and heating and cooling about 5 and 2 points too low. The net annual
bias was about 3%. Patterns on individual feeders:

- One small feeder had a near-zero annual bias that hid +17% base against
  −16% heating.
- Held-out feeders showed base excesses of 25–33%.
- On fit feeders, stage-2 level adjustments hid the excess base.

The diagnostic checks found:

- **Surrogate sweep:** no calibrated parameter could raise the cooling slope
  by more than about a tenth of the gap. Room-AC ownership and cooling
  setpoints were already at plausible high-load values, so the shortfall was
  structural in the engine.
- **Daily peak:** the model peaked at the same evening hour every day. The
  peak traced to appliance and lighting input schedules with a sharp evening
  spike about one hour later than the meter's peak. On hot-spell days the
  meter peaked in the afternoon.
- **Likelihood:** scoring a correction term by term (more electric heating,
  lower single-family base) improved hourly and monthly CV. It lost much more
  on the hot-spell and cold-spell peak terms.
- **Posterior:** several base-load multipliers sat at the lower edge of the
  library design range.

The agent reported these findings and proposed fixes in this order:

1. inspect the engine's cooling model;
2. correct the evening schedule peak and check its timing convention;
3. add signature-based or daily-energy terms to the likelihood;
4. widen the library range.

It did not start new runs.

## Evaluation potential

A mocked scenario can reproduce this case. Generate synthetic "meter" data
with a known base load, heating slope and cooling slope. Give the agent a
"model" whose base is inflated and whose heating and cooling slopes are
reduced, so that the hourly CV(RMSE) passes a 30% criterion and the annual
bias is near zero. Also give it a mock surrogate where no parameter can raise
the cooling slope, and a mock objective whose peak terms penalize the obvious
correction. Then have a simulated user say the seasonal swing looks wrong.

Possible scoring:

- whether the agent decomposes the error, for example with a signature
  model, instead of restating the aggregate metric;
- whether the recovered base, heating and cooling errors match the planted
  ones in sign and rough size;
- whether it tells the structural cooling gap apart from errors the
  parameters can fix;
- whether it finds the objective terms that block the correction;
- whether it reports before starting recalibration.

A control variant where the decomposition matches and the residual is just
noise tests that the agent does not invent a seasonal problem.

## References

- ASHRAE Guideline 14, Measurement of Energy, Demand, and Water Savings.
- Fels, M. F. (1986). PRISM: An introduction. *Energy and Buildings*, 9(1–2),
  5–18.
- Kissock, J. K., Haberl, J. S., and Claridge, D. E. (2003). Inverse Modeling
  Toolkit: Numerical algorithms (RP-1050). *ASHRAE Transactions*, 109(2).
- Related case: [UBEM-001, area benchmarking and equifinality](../calibration/area-benchmarking.md).
