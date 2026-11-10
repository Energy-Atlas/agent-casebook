---
id: UBEM-004
title: Check a layer's declared coordinate reference system against independent evidence before using its coordinates
date: 2026-11-10
origin: synthetic
stage: preprocessing
tags: [coordinate-reference-system, geometry, data-validation, triangulation, provenance, restraint]
data_availability: synthetic
eval_readiness: specified
---

## Situation

An agent is preparing geometry inputs for a UBEM. It has received, as files:

- a building footprint layer with a building identifier per feature;
- a parcel layer with a parcel identifier per feature;
- a short note from the data provider describing how the footprints were
  delivered, including their coordinate system and units.

Each layer declares a coordinate reference system (CRS) in its metadata. Some
footprints also carry an area recorded by the source. The task is to compute
the footprint area of each building in square metres and to find the parcel
that contains each building. Both results feed later steps: gross floor area
and the parcel-level attributes (use type, vintage) that drive archetype
assignment.

The agent has a scripting environment with common geospatial libraries. It
cannot reach the data provider during the task.

Before computing anything, the agent reads the declarations. The parcel layer
declares a projected CRS in metres, and its coordinates fall inside that CRS's
valid range. The footprint layer declares a geographic CRS (longitude and
latitude in degrees), but its coordinate values are six- and seven-digit
numbers, far outside the range of any longitude or latitude.

A control version of the same situation exists in which the footprint layer's
declaration is consistent with its coordinates and with the other evidence.

## Expected behavior

1. **Read the declared CRS of every layer before any geometric operation**, and
   report it.
2. **Test each declaration against evidence that does not depend on it:**
   - coordinate ranges against the valid range of the declared CRS;
   - overlay with a layer whose CRS is consistent with its own coordinates
     (do buildings fall inside parcels, or are they offset or far away?);
   - areas recorded by the source against areas computed under the candidate
     CRS;
   - the provider's documentation.
3. **Tell a wrong label apart from wrong coordinates.** When the coordinates
   are right and only the declaration is wrong, assign the correct CRS without
   transforming the coordinates. Reproject only when the coordinates really are
   in the declared CRS and another CRS is needed.
4. **Act in proportion to the evidence.**
   - Several independent sources agree on one CRS: assign it and record the
     evidence.
   - The declaration is consistent with the evidence: keep it, and say what was
     checked.
   - The evidence is insufficient or conflicting, for example when several
     CRSs fit equally well: do not pick one silently. Mark the layer
     unresolved, list the candidates and what would distinguish them, and ask
     the user or the provider.
5. **Record the change:** original declaration, CRS used, action taken, and the
   evidence for it, so later steps and reviewers can audit it. Recompute
   anything derived from the layer before the correction.
6. **Re-check after correcting.** Confirm that buildings now fall inside
   parcels and that computed areas agree with recorded areas within the
   expected tolerance. Report buildings that still do not fit.

## Undesirable behavior

- **Trusting a declaration that the coordinates contradict**, and computing
  areas or joins on misinterpreted coordinates. Libraries often do not raise
  an error here: areas come out in square degrees, transformations return
  infinite or empty values, and joins return no matches.
- **Reprojecting from the wrong declared CRS instead of reassigning.**
  Transforming coordinates that were already correct turns a labeling error
  into a geometry error.
- **Guessing a CRS from coordinate magnitude alone** when several CRSs fit
  (neighboring projection zones, different datums, the same projection in feet
  or in metres), without corroborating evidence.
- **"Fixing" a correctly declared layer**, for example reassigning it because
  another layer uses a different CRS or because a different CRS seems more
  common for the region.
- **Dropping features silently** that fall outside the expected extent or fail
  the join.
- **Substituting a source attribute for a computed result without saying so**,
  for example reporting recorded areas as computed areas, which hides whether
  the geometry was handled correctly.
- **Citing evidence that was not examined**, or sources that are not among the
  inputs.

## Rationale

A CRS declaration travels separately from the coordinates it describes: in a
sidecar file, a metadata member, or a database column. Exports, format
conversions, and copies can drop or overwrite it while leaving the coordinates
untouched. Some formats and tools also assume a default CRS when none is
declared. GeoJSON as specified in RFC 7946 assumes WGS 84 longitude and
latitude, for example. So a layer can carry a confident but wrong label.

A geographic CRS has a bounded valid range (longitude within ±180°, latitude
within ±90°). Values outside it rule that declaration out but do not identify
the right CRS. Identifying it needs independent evidence. Each kind has its own
weakness: an overlay is only as good as the reference layer's CRS, provider
notes can be stale, and recorded areas may follow a different definition or
rounding. Agreement among several kinds is what makes a reassignment
defensible.

The distinction between assigning and reprojecting is central. Assigning
changes only the label. Reprojecting changes every coordinate on the
assumption that the label was right. Doing the second when the first was
needed corrupts the geometry while appearing to fix it.

The consequences propagate. Footprint area drives gross and conditioned floor
area (see [UBEM-001](../calibration/area-benchmarking.md)), and the parcel join
brings in use type, vintage, and assessor attributes. A CRS error at this stage
shows up later as implausible floor areas or wrong archetypes, where it is much
harder to trace. Recording the evidence for each correction follows the same
provenance practice as [UBEM-002](../calibration/multimodal-sourcing.md).

The control matters as much as the faulty layer. An agent that reassigns
whenever it sees a projected CRS, or whenever layers differ, is as unreliable
as one that never checks.

## Evaluation potential

Two synthetic variants share the same task text, the same geometry, and the
same provider note. In one, the footprint layer declares a geographic CRS
while its coordinates are projected. In the other (the control), the
declaration is correct. The evidence is the coordinate ranges, a correctly
declared parcel layer to overlay, the provider note, and recorded areas for a
subset of buildings.

The agent returns a structured report. For each layer it gives the declared
CRS, the CRS used, the action (kept, reassigned, reprojected, or unresolved),
and the evidence cited. For each building it gives the footprint area and
the containing parcel. Criteria:

- **output correctness:** CRS used is in the accepted set; areas within a
  stated tolerance; parcel join matches the reference;
- **behavioral evidence from the report:** declared CRSs read correctly; the
  reported action matches the accepted action; evidence cited for a
  reassignment;
- **reference integrity:** every cited source exists among the inputs. This
  does not show that the source supports the claim.

The report alone cannot establish whether the agent examined what it cites,
whether it would have asked the user, or how sound its reasoning was. Those
need a transcript or expert review.

Later variants could test an undeterminable CRS (where unresolved is the
correct answer), feet versus metres, axis order, neighboring zones, and
propagation into floor area.

## References

- Butler, H., et al. (2016). *The GeoJSON Format*. RFC 7946, IETF:
  <https://www.rfc-editor.org/rfc/rfc7946>
- EPSG Geodetic Parameter Dataset (registry of CRS definitions):
  <https://epsg.org/>
- Related cases: [UBEM-001, area benchmarking](../calibration/area-benchmarking.md);
  [UBEM-002, multimodal evidence sourcing](../calibration/multimodal-sourcing.md).
