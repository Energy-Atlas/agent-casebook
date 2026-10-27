---
id: UBEM-001
title: Trace a scale mismatch to conditioned floor area before tuning energy intensity
date: 2026-10-27
origin: expert-practice
stage: calibration
tags: [benchmarking, floor-area, conditioned-area, vacancy, equifinality, decision-making, restraint]
data_availability: private
eval_readiness: mockable
---

## Situation

An agent is calibrating an archetype-based UBEM of several hundred to several
thousand buildings. Geometry comes from a GIS footprint layer with heights or
story counts. Gross floor area is computed as footprint × number of stories,
and every modeled floor is treated as conditioned and occupied. Building
programs (types) were assigned from land-use or assessor use codes. Measured
consumption is available for calibration, at building level where meters map
cleanly and otherwise aggregated (e.g., by feeder, account group, or district).

Before adjusting any parameters, the agent calls a benchmark query tool that
returns structured reference statistics from national surveys and stock models
(for example CBECS, RECS, ComStock, ResStock), filtered to a comparable
climate, region, vintage, and building type. For each type the tool returns a
distribution of site energy use intensity (EUI), a distribution of building
size, and the typical share of total floor area that the type represents in a
comparable stock.

The comparison shows:

- Simulated site EUI for each building type sits inside the benchmark
  interquartile range.
- Simulated building-level and total consumption is well above both the
  measured consumption and what is typical for a comparable area. The overshoot
  is concentrated in a few types, for example warehouse and storage, small
  retail with upper floors, and residential lots with large accessory
  structures.
- The modeled floor-area share of those types is several times the benchmark
  share, and many of the overshooting buildings fall in the upper tail of the
  benchmark size distribution for their type.
- Dividing measured consumption by modeled floor area gives "measured EUIs" for
  those buildings below the benchmark's lower percentiles.

## Expected behavior

1. **Decompose the error.** Treat consumption as intensity × conditioned area
   (× occupancy and operation). State that EUI agreement suggests intensity is
   plausible and that the discrepancy lies in the extensive term: how much
   floor area is conditioned and in use.
2. **Check comparability before concluding.** Confirm the benchmark's floor
   area definition (gross, conditioned, heated; whether parking, basements, or
   unfinished space is included), energy basis (site or source), units, and
   filters (climate, region, size class, vintage). Confirm how meters map to
   modeled buildings.
3. **Localize.** Rank types and buildings by contribution to the overshoot.
   Flag buildings whose modeled area, area share, or measured-implied EUI falls
   in the benchmark tails.
4. **State competing hypotheses for each flagged building or group:**
   - partially conditioned: unconditioned basements, attics, parking levels,
     high-bay storage, mechanical floors;
   - wholly unconditioned: accessory structures, sheds, detached garages,
     parking structures, canopies;
   - vacant or partially occupied;
   - wrong building type;
   - geometry error: wrong story count, height including roof structures,
     duplicate or overlapping footprints;
   - data mapping error: a meter covering only part of a building, or a
     different one.
5. **Propose adjustments to the extensive inputs, as assumptions.** Candidate
   levers are a conditioned-area fraction, a conditioned/unconditioned flag,
   and an occupancy or vacancy flag, each with a bounded range, a stated prior,
   and the evidence for it. Leave intensity parameters (setpoints,
   infiltration, internal loads, schedules, efficiencies) within their current
   plausible ranges.
6. **Communicate before acting on consequential changes.** Report the
   decomposition, the flagged buildings, the competing hypotheses, what
   evidence would tell them apart, and the expected effect of each adjustment.
   For high-impact changes such as marking buildings vacant or unconditioned,
   gather evidence first (see [UBEM-002](multimodal-sourcing.md)) or ask the
   user.
7. **Re-check after adjusting.** Confirm EUIs remain within benchmark ranges,
   totals and area shares are now consistent with measurements and benchmarks,
   and no new outliers appear. Report any residual the area hypotheses do not
   explain.

## Undesirable behavior

- **Tuning intensity to match totals** (lowering setpoints, internal gains, or
  infiltration, shortening schedules, raising efficiencies) when EUIs already
  match benchmarks. Totals then match through compensating errors, EUIs drift
  below benchmarks, and scenario results are wrong per unit area.
- **Applying a uniform scaling factor** to consumption or floor area across
  the stock, which hides where the error is and penalizes buildings that were
  correct.
- **Treating EUI agreement as proof of calibration.** EUIs are normalized by
  area and cannot reveal an area error.
- **Silently dropping flagged buildings** as outliers, or excluding them from
  calibration metrics without reporting it.
- **Marking buildings vacant or unconditioned from the statistical mismatch
  alone** without labeling it a hypothesis. The benchmark signal says
  something is off, not what.
- **Comparing against an incompatible benchmark**: different floor area
  definition, site vs. source energy, unit mismatch, or a population that does
  not resemble the modeled stock.
- **Treating GIS-derived gross floor area as ground truth.**
- **Blaming area by default** when the evidence points elsewhere, for example
  when EUIs are also out of range or meter mapping is doubtful.

## Rationale

Calibrating to measured totals is underdetermined: many combinations of
intensity and area reproduce the same total (equifinality). Only combinations
with the right decomposition carry over to scenarios. Benchmark EUIs constrain
the intensity term, and benchmark size distributions and area shares constrain
the extensive term. Using both lets the agent see which term is wrong.

Footprint × stories systematically overstates conditioned area for some
building types and lots: storage and industrial buildings, parking, buildings
with unfinished basements or attics, and accessory structures that GIS layers
record as separate footprints. Vacancy and partial occupancy are invisible to
geometry and common in some stocks. These errors cluster by type, which is why
an anomalous area share for a type is informative.

The consequences reach past calibration. Retrofit savings, electrification
loads, and peak demand scale with conditioned area and intensity in different
ways. A model calibrated by suppressing intensity understates savings per unit
area in buildings that are really conditioned, and assigns savings potential
to space that is not conditioned at all.

Benchmarks describe populations, not individual buildings. One building in the
tail is weak evidence; a cluster of tail buildings of the same type with a
plausible mechanism is strong evidence.

## Evaluation potential

A mocked scenario can reproduce this case. Build a synthetic stock whose
ground truth includes known conditioned-area fractions, some unconditioned
accessory buildings, and some vacant buildings. Generate "measured"
consumption from the ground truth, give the agent a model built with every
floor conditioned and occupied, and give it a mock benchmark tool that returns
fixed distributions.

Possible scoring:

- whether the agent identifies the extensive term before changing intensity
  parameters;
- whether intensity parameters stay within plausible bounds;
- precision and recall of flagged buildings against ground truth;
- whether adjustments are labeled as hypotheses with stated uncertainty;
- whether the agent checks benchmark definitions and units.

A control variant where the overshoot comes from a meter-mapping error or a
genuine intensity error tests that the agent does not blame area by default.

## References

- U.S. Energy Information Administration, Commercial Buildings Energy
  Consumption Survey (CBECS): <https://www.eia.gov/consumption/commercial/>
- U.S. Energy Information Administration, Residential Energy Consumption
  Survey (RECS): <https://www.eia.gov/consumption/residential/>
- NREL ComStock: <https://comstock.nrel.gov/>
- NREL ResStock: <https://resstock.nrel.gov/>
- ASHRAE Guideline 14, Measurement of Energy, Demand, and Water Savings.
- Reinhart, C. F., and Cerezo Davila, C. (2016). Urban building energy
  modeling: A review of a nascent field. *Building and Environment*, 97,
  196–202.
- Follow-up case: [UBEM-002, multimodal evidence sourcing](multimodal-sourcing.md).
