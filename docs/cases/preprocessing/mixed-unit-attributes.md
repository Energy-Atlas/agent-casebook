---
id: UBEM-014
title: Detect mixed units within one attribute column before converting or aggregating it
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [units, assessor-data, parcels, data-validation, provenance]
data_availability: private
eval_readiness: mockable
---

## Situation

An agent needs lot area per parcel to compute lot coverage (footprint area
divided by lot area) and to check floor-area ratios for plausibility. The
assessor table has a lot-size column. Its documentation calls it lot size
and does not state a unit.

The values fall into two groups. Many are small decimals, mostly between a
tenth and a few units, which read naturally as acres. Many others are
integers in the thousands to tens of thousands, which read as square feet,
and for those rows separate frontage and depth columns, in feet, are filled
in and multiply to the lot-size value. A few rows hold 0. The column mean is
meaningless, and a lot-coverage computation with a single unit gives values
that are either far above one or vanishingly small for a whole group of
parcels.

Parcel polygons are available for most parcels.

## Expected behavior

1. **Profile the column before converting it.** On a logarithmic scale the
   two groups separate clearly, by roughly the factor of 43,560 square feet
   per acre. Note which rows are integers and which have frontage and depth.
2. **Look for a unit indicator:** a unit or measure-type code, the
   documentation, the property class (rural parcels are more often recorded
   in acres), or the presence of frontage and depth.
3. **Cross-check against the geometry.** For a sample from each group,
   compare the attribute under each unit interpretation with the parcel
   polygon's area computed in a CRS suited to the location. The
   interpretation that agrees with the geometry is the unit.
4. **Convert row by row according to the evidence,** and record the unit
   inferred for each row and why. Flag rows whose unit cannot be determined,
   and treat 0 as missing.
5. **Decide which source to use and say so:** usually the polygon area where
   the polygon exists and agrees, and the converted attribute as a
   cross-check or a fallback.
6. **Report** the number of rows in each unit, the conversions applied, the
   undetermined rows, and the rows where attribute and geometry disagree.

## Undesirable behavior

- **Applying one unit to the whole column.** Read as square feet, lots
  recorded in acres shrink to a fraction of a square metre; read as acres,
  urban lots of a few thousand square feet grow to tens of square
  kilometres.
- **Aggregating or averaging the column** before the units are resolved.
- **Removing the minority group as outliers** instead of converting it.
- **Treating frontage times depth as the exact lot area** for irregular
  lots without saying that it is a rectangle approximation.
- **Inferring the unit from magnitude alone** for values that are plausible
  under both readings, without corroboration.

## Rationale

Assessment records accumulate over decades, entered by different staff
under different systems and conventions. Rural and large parcels are often
recorded in acres; urban lots are traditionally described by frontage and
depth in feet. When records are migrated into one column, the unit can
survive only implicitly, in the magnitude or in a neighboring column.

A mixed-unit column contaminates every ratio derived from it by a factor of
tens of thousands, and aggregates are dominated by the mis-scaled rows. Lot
coverage and floor-area ratio are useful plausibility checks for footprint
and floor area (see [UBEM-001](../calibration/area-benchmarking.md) for why
floor area matters), and sometimes inputs to typology rules, so the error
can reach archetype assignment as well as quality checks.

For reference: one acre is 43,560 square feet, about 4,046.9 square metres,
and one square foot is about 0.0929 square metres. Parcel polygons provide
an independent measurement, provided the area is computed in a suitable CRS
(see [UBEM-010](threshold-projection.md)).

## Evaluation potential

A mocked scenario can reproduce this case. Build a synthetic assessor table
whose lot-size column mixes acres and square feet from frontage and depth,
with a few zeros and a few values plausible in both units, together with
parcel polygons for most parcels.

Possible scoring: per-parcel lot area within tolerance of the reference,
the unit recorded per row, undetermined rows flagged rather than guessed,
and no rows removed.
