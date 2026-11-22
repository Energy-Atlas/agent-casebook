---
id: UBEM-009
title: Match buildings to parcels by spatial overlap, with an explicit policy for ambiguous and unmatched buildings
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [parcels, spatial-join, geometry, coordinate-reference-system, provenance, data-validation]
data_availability: private
eval_readiness: automated
---

## Situation

An agent is linking building footprints to parcels so that each building can
inherit the parcel's assessor attributes: use class, year built, stories,
and lot size. Both layers are available in the same, correctly declared
CRS. Each footprint carries a parcel key filled in by the publisher.

On inspection the agent finds:

- most keys point to a parcel that contains the building;
- some keys point to a parcel the building does not touch, for example
  after a subdivision or renumbering, and some point to parcel ids that do
  not exist in the parcel layer;
- some buildings straddle a parcel line: row houses, buildings built across
  former lot lines, or small offsets between the two layers' digitizing;
- some buildings overlap no parcel at all, because they lie partly or wholly
  in a gap between parcels, typically a road right of way.

An existing matching script in the pipeline uses a nearest-neighbor join
written from parcels to buildings. It gives each parcel its nearest
building, so buildings that are not the nearest to any parcel disappear from
the output, and a building nearest to several parcels appears several
times. A fallback assigns buildings without overlap to the nearest parcel
within a generous distance, which matches some buildings in a road gap to a
parcel across the street.

## Expected behavior

1. **Verify the keys spatially.** For each building, check whether the keyed
   parcel intersects it. Count confirmed, contradicted, and dangling keys
   and report them. If many keys disagree with the geometry in a consistent
   direction, suspect a CRS or registration problem first (see
   [UBEM-004](crs-declaration-check.md)).
2. **Measure overlap in a suitable CRS:** a projected CRS valid at the
   data's location (a local conformal zone or an equal-area projection), not
   longitude and latitude in degrees and not Web Mercator. Absolute area and
   distance thresholds depend on it (see
   [UBEM-005](inherited-geometry-attributes.md)).
3. **Join from buildings to parcels,** so that every building receives at
   most one parcel. The primary rule is the parcel with the largest share of
   the building's footprint.
4. **State a policy for straddling buildings.** When the largest overlap
   share is below a stated fraction, either assign the largest overlap and
   flag the match as ambiguous, or leave the building marked ambiguous with
   its candidate parcels listed. Either is defensible if it is stated and
   applied consistently.
5. **State a policy for buildings without overlap.** Either leave them
   unmatched, or assign the nearest parcel within a small stated distance
   (a few metres) and flag the match as low confidence. Do not match across
   a street: when road data are available, reject candidates on the other
   side of a road; otherwise, treat the case as ambiguous when the nearest
   and second-nearest parcels are almost equally far.
6. **Keep the method and confidence with each building:** key confirmed,
   largest overlap, ambiguous, nearest within distance, or unmatched, plus
   the overlap share or distance.
7. **Check that no building was lost or duplicated.** The number of
   buildings out equals the number in. Parcels with several buildings and
   parcels with none are normal; report their counts.
8. **Report the policy and the counts per method,** and say that other
   policies are possible and what the chosen one implies.

## Undesirable behavior

- **Trusting the parcel keys without a spatial check,** which carries stale
  or dangling keys into the attribute join.
- **A nearest-neighbor join in the wrong direction** (each parcel to its
  nearest building), which silently drops some buildings and duplicates
  others.
- **Distance matches without a limit or a flag,** including matches across
  a street.
- **Evaluating overlap or distance thresholds in a distorting projection**
  or in degrees.
- **Using a centroid-in-parcel test as the only rule without saying so.**
  The centroid of an L-shaped or straddling building can lie outside the
  building or in the neighboring parcel. It is a useful quick check, not a
  policy for edge cases.
- **Dropping unmatched or ambiguous buildings** instead of keeping and
  flagging them.

## Rationale

The parcel is the unit of assessor attributes, and the building is the unit
of the energy model. A wrong match gives a building another parcel's use
class and vintage, and so another archetype (see
[UBEM-008](placeholder-year-built.md) for what vintage controls). Because
neighboring parcels are often similar, such errors look plausible and
survive casual inspection.

Publisher keys are maintained separately from geometry and go stale when
parcels are split, merged, or renumbered. Spatial overlap is independent
evidence, and disagreement between the two is information worth reporting.

Nearest-neighbor joins are asymmetric. Each feature on the left gets one
neighbor on the right, with no guarantee that every right-hand feature is
used or used once. Written from parcels to buildings, the join conserves
parcels and not buildings, which is the wrong invariant for a building
model.

Road rights of way are usually not parcels, so a building digitized a
little into the road, or a parcel layer with small gaps, produces no
overlap. Across a narrow street the nearest parcel can belong to the other
side, so a generous distance fallback converts a missing match into a wrong
one.

Several answers are acceptable here. What matters is that the policy is
explicit, applied consistently, recorded per building, and conserves
buildings.

## Evaluation potential

The evaluation instances `parcel-match` and `parcel-match-control` in the
separate validation package exercise this case (see
[evaluation instances](../../guide/evaluations.md)). Both give the agent a
synthetic town's footprint and parcel layers. It delivers one row per
building with the matched parcel and a match label (confident, ambiguous,
low confidence, or unmatched), and a run log.

- `parcel-match`: some recorded keys name a parcel the footprint does not
  touch, or a key that does not exist; some main buildings straddle a parcel
  line; and the buildings on public land overlap no parcel.
- `parcel-match-control`: every recorded key is correct and no building
  straddles a parcel line. The buildings on public land are still present.

At two decision points the agent declares a policy in the log: for
straddling buildings, the largest overlap or marking them ambiguous; for
buildings without overlap, leaving them unmatched or assigning the nearest
parcel flagged as low confidence. The outputs are checked against the
declared policy, so several policies pass. Also graded: every building is
delivered once, buildings without complications are matched to their parcel
with confidence, wrong keys are resolved from the geometry and reported as
issues, and the sources cited for issues exist. Reporting correct keys as
wrong is a false alarm and fails, which is what the control tests.

Not graded are the CRS in which overlap was computed (only the resulting
assignment is read), whether the agent checked for lost buildings by other
means than the output count, and the process in general, since no
transcript is graded.
