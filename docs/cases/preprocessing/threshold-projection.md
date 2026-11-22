---
id: UBEM-010
title: Evaluate area and distance thresholds only in a projection that preserves them
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [coordinate-reference-system, geometry, spatial-join, data-validation]
data_availability: private
eval_readiness: mockable
---

## Situation

An agent maintains a footprint preprocessing pipeline that applies several
absolute thresholds stated in metres and square metres:

- footprints below a minimum area are treated as sheds or digitizing debris
  and set aside;
- two buildings closer than a small gap are treated as attached, which
  later decides shared walls and adjacency in the energy model;
- parcels are buffered by a small tolerance before buildings are matched to
  them, and a match needs a minimum overlap area (see
  [UBEM-009](building-parcel-matching.md)).

The geometry is in Web Mercator because it was downloaded from a web map
service in that CRS, and the script computes areas, distances, and buffers
directly on those coordinates. The study area lies at mid latitudes. The
CRS's unit is the metre, so nothing in the code or the output looks wrong,
and no library raises a warning.

## Expected behavior

1. **Check the CRS of the geometry before applying any absolute area or
   length threshold.** If it is geographic, Web Mercator, or a projected
   zone far from the data, transform to a CRS that preserves the quantity at
   the data's location, or use geodesic computation:
   - for building-scale areas and distances, a local conformal zone such as
     UTM or a state plane zone;
   - for areas over large extents, an equal-area projection.
2. **Tell absolute thresholds from relative ones.** A ratio such as the
   share of a footprint inside a parcel is nearly unaffected by a scale
   error that is uniform over a building. A threshold in metres or square
   metres is affected in full.
3. **Check thresholds that earlier steps applied.** When reusing a
   classification (attached or not, too small or not, matched or not),
   find out in which CRS it was computed. Where it was a distorting one,
   rerun the step and report how many buildings change class (see
   [UBEM-005](inherited-geometry-attributes.md) for inherited attributes
   computed in an unsuitable CRS).
4. **Make sure the declared CRS is right first.** A threshold evaluated in a
   correct projection of wrongly labeled coordinates is still wrong (see
   [UBEM-004](crs-declaration-check.md)).
5. **State the CRS used for each measurement** in the report and with the
   derived attributes.

## Undesirable behavior

- **Computing areas or distances directly in Web Mercator or in degrees**
  and comparing them with thresholds meant for ground metres.
- **Assuming a CRS is fit for measuring because its unit is the metre.**
- **Rescaling every threshold by one factor** instead of transforming the
  geometry, without saying so. The factor varies with latitude and differs
  between lengths and areas, so this hides the cause and tends to be copied
  into places where it no longer fits.
- **Reusing earlier classifications** without asking where their
  thresholds were evaluated.

## Rationale

Web Mercator is conformal: it keeps local shapes and angles and gives up
scale. Its scale factor grows with latitude roughly as 1/cos(latitude), the
same in every direction, so lengths are stretched by that factor and areas
by its square. At 40° latitude lengths come out about 1.31 times too long
and areas about 1.70 times too large; at 45° the factors are 1.41 and 2.0;
at 50° they are 1.56 and 2.42.

For a threshold the effect is inverted. A minimum area of A applied in Web
Mercator at 45° keeps every building whose real area exceeds about A/2, so
sheds the rule was meant to set aside stay in the stock. A gap tolerance of
d treats buildings as attached only when they are within about 0.7 d of
each other on the ground, so some attached buildings are modeled as
detached and gain exterior wall area. A buffer of d around a parcel reaches
about 0.7 d. None of this raises an error, and because the factor is nearly
uniform over a city, relative comparisons look normal.

The same applies to any CRS used far from where it was designed for. A
transverse Mercator zone a long way from the data distorts lengths and areas
by factors of the same order (see UBEM-005). Choosing the measurement CRS is
therefore a separate decision from choosing the storage or display CRS, and
it should be made where measuring happens.

## Evaluation potential

A mocked scenario can reproduce this case. Place synthetic footprints at a
mid latitude in Web Mercator, with areas around the minimum-area threshold
and gaps between neighbors around the attachment threshold. Compute the
reference classification in a local conformal zone. Ask the agent to apply
the pipeline's filters and report the CRS used.

Possible scoring: agreement of the size and adjacency classification with
the reference, whether the CRS used for measuring is stated, and whether
relative thresholds were left alone. A control with geometry already in a
suitable local CRS tests that the agent does not transform without need.

## References

- Snyder, J. P. (1987). *Map Projections: A Working Manual*. U.S. Geological
  Survey Professional Paper 1395. <https://doi.org/10.3133/pp1395>
- EPSG Geodetic Parameter Dataset (definition of EPSG:3857 and of local
  projected CRSs): <https://epsg.org/>
