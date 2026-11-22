---
id: UBEM-016
title: Decline to link meters to buildings when their identifiers cannot be connected without a crosswalk
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [meter-data, identifier-linkage, restraint, decision-making, provenance]
data_availability: private
eval_readiness: conceptual
---

## Situation

An agent is asked to attach measured consumption to buildings so that a
UBEM can be calibrated building by building. It has:

- interval data from smart meters, keyed by a meter device identifier, with
  no address and, for some meters, approximate coordinates of unclear
  origin;
- monthly billing records keyed by a service installation identifier, with
  a service address;
- the building layer, with addresses taken from assessor records.

No field is shared between the smart-meter data and the billing records.
The utility links devices to installations through an internal crosswalk
that changes whenever a meter is replaced, and that crosswalk was not
provided. The two identifiers have different formats; some of them share
digits.

## Expected behavior

1. **Establish what each identifier refers to:** a physical device, an
   installation or service point, an account, or a premise, and whether any
   table provided links them.
2. **Recognize that without a crosswalk any link is a guess.** Similar
   digits, record order, consumption magnitude, or proximity of approximate
   coordinates are not evidence that a device belongs to an installation or
   a building.
3. **Stop and tell the user before producing any meter-to-building table.**
   Say what is missing and what would resolve it:
   - the utility's device-to-installation (or service point) crosswalk,
     with validity dates;
   - or a premise or service address for each meter;
   - or an identifier shared by both datasets.

   Mention that such a crosswalk may fall under the data agreement and may
   need a request to the data owner.
4. **Offer what can be done without it:** link billing records to buildings
   by address, with the match quality reported, or calibrate against
   aggregates (feeder or district totals) where meters can be grouped
   without building links (see
   [UBEM-003](../validation/calibration-cv-diagnosis.md)).
5. **Use partial evidence only for what it supports.** If some meters do
   carry a premise address, link those with a stated confidence, leave the
   rest unlinked, and report the coverage.

## Undesirable behavior

- **Matching meters to the nearest building by their approximate
  coordinates,** which may be a transformer, a rounded location, or a
  geocoded centroid, and presenting the result as a link.
- **Joining on identifiers that look alike** (shared digits, same length) or
  pairing records by sort order.
- **Pairing by consumption plausibility,** for example the largest meter to
  the largest building. That uses the quantity to be calibrated to build
  the link, which makes calibration circular.
- **Assuming one meter per address** in multi-unit and mixed-use buildings.
- **Calibrating on a guessed linkage,** or dropping unlinked meters
  silently.

## Rationale

Meter-to-building mapping is one of the main sources of error in
building-level calibration (see
[UBEM-001](../calibration/area-benchmarking.md), where a meter covering a
different building is one of the competing hypotheses). Utility data models
keep devices, service points, accounts, and premises apart for good
reasons: devices are replaced, accounts change with occupants, and one
premise can have several services. Identifiers of different entities are
not interchangeable even when they look similar.

A wrong link is worse than a missing one. Calibration then fits a building
to another building's consumption, the posterior or tuned parameters absorb
the mismatch, and the result looks like data. A missing link is visible and
can be handled by aggregating or by excluding the building from
building-level metrics.

Spatial matching is tempting because coordinates exist. But the meaning of
the coordinates is unknown, and in dense areas the nearest building is often
the wrong one, the same failure as an unchecked nearest join between
buildings and parcels (see [UBEM-009](building-parcel-matching.md)).
Consumption data are also personal data, and creating new links between
datasets can conflict with the agreement under which they were shared (see
[releasing data-derived material](../../guide/data-release.md)).
