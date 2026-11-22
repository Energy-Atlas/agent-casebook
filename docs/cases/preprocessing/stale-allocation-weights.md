---
id: UBEM-013
title: Recompute allocation weights after an upstream change to the buildings they cover
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [allocation, derived-attributes, parcels, floor-area, data-validation, provenance]
data_availability: private
eval_readiness: mockable
---

## Situation

Some assessor attributes are recorded per parcel, not per building:
assessed living area and the number of dwelling units, for example. An
earlier step of the pipeline spread them over the buildings on each parcel
in proportion to footprint area and stored each building's weight as an
attribute.

A later step reclassified small structures. Detached garages, sheds, and
similar structures were marked as accessory, and on parcels where only one
main building remained, that building's weight was set to one. The
accessory records stayed in the layer with their old weights. On a few
parcels, accessory records were deleted instead, and the remaining weights
were left as they were. The step that now allocates living area and
dwelling units does not filter by class.

The agent is asked to produce building-level floor area and dwelling units
for the model. When it sums the weights per parcel, it finds totals above
one on many parcels and below one on a few. The allocated living area for
the stock exceeds the sum of the parcel values.

## Expected behavior

1. **Check the invariant before using allocated values:** on every parcel,
   the weights sum to one, and the allocated quantities sum to the parcel's
   value. Repeat the check whenever group membership or the weighting
   quantity changes.
2. **Find the cause** instead of only the symptom: identify which step
   changed the membership (here, the reclassification), and which records
   carry weights from before it.
3. **Recompute the weights from the current membership and the current
   geometry,** after the last step that changes either.
4. **State the policy for accessory structures:** for example, no dwelling
   units, and either no share of living area or a share only when there is
   evidence that the structure is finished space.
5. **Re-check after recomputing:** weights sum to one on every parcel, and
   allocated totals match parcel totals within rounding, for each parcel
   and for the stock.
6. **Report** how many parcels were affected, how large the over- and
   under-allocation was for the stock, and which later results were
   recomputed.
7. **Make the order safe:** compute weights as late as possible or derive
   them from membership when needed, and record which step and version
   computed them.

## Undesirable behavior

- **Aggregating allocated values without checking** that they conserve the
  parcel totals.
- **Renormalizing the stale weights** on each parcel (dividing by their
  sum) without fixing the membership. The totals then add up, but
  accessory structures keep a share of living area and dwelling units.
- **Fixing only the parcels where the error is large,** or only the
  over-allocated ones.
- **Treating the resulting area excess as a calibration problem** and
  adjusting intensity parameters to compensate (see
  [UBEM-001](../calibration/area-benchmarking.md)).

## Rationale

Allocation weights are derived attributes. Like inherited areas (see
[UBEM-005](inherited-geometry-attributes.md)), they are correct only for the
state of the data they were computed on, and a stored value does not
announce that its inputs have changed. Steps that add, remove, merge,
reassign, or reclassify buildings (de-duplication, parcel matching,
accessory detection; see [UBEM-009](building-parcel-matching.md) and
[UBEM-012](duplicate-footprints.md)) all change the groups the weights were
computed over.

Allocation by footprint area assumes that the allocated quantity scales
with footprint. Accessory structures violate that assumption: a large
detached garage has footprint but no dwelling units and usually no
conditioned living area. A weight left on such a structure moves floor area
and occupants from the house to the garage, or, as here, adds them on top.

Conservation checks are cheap and catch a whole class of ordering errors in
pipelines. A quantity spread over parts must add back up to the whole, and
when it does not, the cause is upstream.

## Evaluation potential

A mocked scenario can reproduce this case. Build synthetic parcels with a
main building and accessory structures, parcel-level living area and
dwelling units, weights computed before a reclassification step, and the
reclassified layer with stale weights. Ask the agent for building-level
floor area and dwelling units.

Possible scoring: conservation of parcel totals for every parcel, no
dwelling units on accessory structures, recomputed rather than renormalized
weights, and a report that names the reclassification as the cause.
