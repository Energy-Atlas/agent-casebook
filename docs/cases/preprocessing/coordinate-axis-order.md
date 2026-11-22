---
id: UBEM-011
title: Check the axis order of coordinate pairs before building points from them
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [coordinate-reference-system, geometry, spatial-join, data-validation]
data_availability: private
eval_readiness: mockable
---

## Situation

An agent builds a point layer from tabular coordinates so that the points
can be joined to building footprints. The coordinates come from two places:

- a geocoding step that turned service addresses into coordinate pairs and
  wrote them as two numeric columns;
- an older table of building points whose coordinates were written by an
  earlier version of the pipeline, before its geometry and CRS libraries
  were upgraded.

The agent constructs points by taking the first value as x and the second
as y, declares them as WGS 84 longitude and latitude, and runs a spatial
join to the footprints. For one of the sources the join returns almost no
matches. Plotted, those points sit in another hemisphere, in the ocean, or
fail to load because their "latitude" is beyond ±90°. A later step that
drops points outside the study area would remove them without comment, and
a nearest-building join without a distance limit would attach each of them
to some building at the edge of the study area.

## Expected behavior

1. **Find out the axis order each source uses** instead of assuming it from
   column position or names such as x and y. Read the geocoder's
   documentation and the format's specification, and check how the
   libraries in use interpret the CRS.
2. **Make the order explicit in code:** name the longitude and latitude
   columns, and use the library's option for traditional GIS order
   (longitude first) where it has one.
3. **Check the points after construction,** before any join: coordinate
   ranges, the bounding box against the study area and the footprint layer,
   and the share of points that fall inside the study area.
4. **Test the swap hypothesis when points fall outside.** If swapping the
   two values brings the affected points into the study area and onto
   buildings, swap them for that source and record that you did. If only
   one source is affected, fix only that source.
5. **Report the fix:** which source, how many points, the evidence, and the
   check after the fix.
6. **Re-run the check after library upgrades** or changes to the geometry
   stack, because the default order can change with them.

## Undesirable behavior

- **Assuming the order from column position or names** without checking
  the result against the study area.
- **Dropping points outside the study area as bad geocodes** without
  testing whether they are swapped.
- **Nearest joins without a distance limit,** which hide swapped points by
  attaching them to edge buildings.
- **Swapping every source** when only one is affected.
- **Treating a swap as the explanation for every misplaced point.** Points
  in projected coordinates under a geographic label are a CRS problem, not
  an axis-order problem (see [UBEM-004](crs-declaration-check.md)).

## Rationale

Two conventions coexist. The EPSG definition of WGS 84 geographic
coordinates lists latitude first, and many geocoding services and
human-readable outputs give latitude, longitude. Most GIS software, the
GeoJSON format (RFC 7946), and the x, y convention of plane geometry put
longitude first. Since version 6, the widely used PROJ library follows the
axis order defined by the authority unless the caller asks for traditional
GIS order, so code that produced correct points with an older version can
start swapping them after an upgrade without any other change.

At mid latitudes a swap is detectable in one of two ways. Where the
absolute longitude exceeds 90°, the swapped latitude is invalid and the
point fails or becomes empty. Where it does not, the swapped point is valid
and lands far away, often in an ocean or near a pole. Neither case raises
an error in a spatial join: it simply finds nothing, or, with a nearest
join, finds the wrong thing.

The consequence depends on what the points carry. Points that link meters or
addresses to buildings decide which measured data calibrate which model
(see [UBEM-001](../calibration/area-benchmarking.md)), so a swapped source
either loses those links or, through an unbounded nearest join, assigns
them to the wrong buildings.

## Evaluation potential

A mocked scenario can reproduce this case. Provide synthetic footprints at a
mid latitude and two point tables, one in longitude-latitude order and one
in latitude-longitude order with otherwise identical column naming. Ask the
agent to link each point to a building.

Possible scoring: correct links for both sources, no silently dropped
points, the swap applied only to the affected source and reported. A
variant with points placed where both orders give valid coordinates tests
whether the agent checks against the study area rather than only against
the valid range.

## References

- Butler, H., et al. (2016). *The GeoJSON Format*. RFC 7946, IETF:
  <https://www.rfc-editor.org/rfc/rfc7946>
- EPSG Geodetic Parameter Dataset (definition of EPSG:4326, including its
  axis order): <https://epsg.org/>
