---
id: UBEM-005
title: Check inherited footprint areas against the geometry before deriving floor area from them
date: 2026-11-11
origin: expert-practice
stage: preprocessing
tags: [geometry, coordinate-reference-system, floor-area, data-validation, provenance, derived-attributes]
data_availability: private
eval_readiness: automated
---

## Situation

An agent is preparing building geometry inputs for a UBEM. It receives a
building layer produced by earlier steps of an existing preprocessing pipeline
(de-duplication, parcel matching, assessment join), written in WGS 84
longitude and latitude. Besides the footprint geometry, each building carries:

- `area` and `perimeter`, added by an earlier integration step and described
  in the pipeline's data dictionary as square metres and metres computed from
  the geometry;
- the number of stories from the assessment roll;
- the shape area and length recorded in the county's footprint layer, in the
  units of the county's native projected CRS (US survey feet).

The task is to produce, for every building, the footprint area, the footprint
perimeter, and the gross floor area (footprint area multiplied by stories).
These feed the energy model's geometry, its floor-area normalization, and
anything derived per square metre, such as occupant density.

Nothing in the layer looks broken. The values are positive and well formed,
and larger buildings have larger values. But the inherited `area` is about
2.2 times the area the geometry gives in the buildings' own UTM zone, for
every building, and `perimeter` is about 1.5 times too long. The county's
recorded areas, converted from square feet, agree with the geometry.

## Expected behavior

1. **Treat inherited derived attributes as claims to verify, not facts.**
   Before reusing `area` or `perimeter`, recompute them for the layer, or a
   sample of it, from the geometry in a CRS suited to measuring at the
   buildings' location: the local UTM zone or state plane zone, an
   equal-area projection, or geodesic computation.
2. **Cross-check against an independent record** when one exists, here the
   county's recorded areas, after converting units (1 US survey foot is
   1200/3937 m, so 1 ft² is about 0.0929 m²).
3. **Read the pattern of disagreement.** A near-constant ratio across all
   buildings points to a systematic cause (wrong CRS, wrong units, a scale
   factor) rather than to individual bad records. A few scattered mismatches
   with the source record, while the geometry and the rest agree, point to
   stale or erroneous records.
4. **Use the values the evidence supports,** here the ones computed from the
   geometry, and say where each value came from.
5. **Report the problem upstream** with what was compared, the size and
   extent of the discrepancy, and the likely cause if it can be identified,
   so the step that produced the attribute can be fixed and other consumers
   of the layer can be warned.
6. **Find what else depends on the bad attribute** in the work at hand,
   such as gross floor area, densities, and any thresholds or weights computed
   from it, and recompute it. Say which of these cannot be recomputed from the
   available inputs.
7. **When computing areas in a projected CRS, check that the CRS is valid at
   the data's location** and in the units assumed. A transverse Mercator
   zone is meant for a few degrees around its central meridian. Web Mercator
   (EPSG:3857) exaggerates areas by about 1/cos²(latitude).

## Undesirable behavior

- **Reusing an attribute because its name and documentation say what it
  should be,** without checking a single value against the geometry.
- **Relying only on internal consistency checks.** A constant scale error
  preserves ranks, ratios between buildings, and area-weighted shares, so
  histograms, rankings, and normalized weights look plausible.
- **Recomputing silently.** Correct values without a report leave the
  upstream step broken and other consumers of the same layer exposed.
- **Substituting the source record wholesale** for the geometry, which hides
  stale records, or "correcting" the geometry to match it.
- **Computing areas or lengths in a CRS that is not suited to the location,**
  such as a UTM zone far from the data or Web Mercator, or mixing feet and
  metres.
- **Rescaling by the observed ratio** (dividing by 2.18) instead of
  recomputing from the geometry. The ratio is a symptom; it varies slightly
  with position and shape and does not apply to other quantities computed in
  the same wrong CRS, such as distances.

## Rationale

Footprint area is one of the most consequential geometric inputs in a UBEM.
It sets gross and conditioned floor area, roof and ground-contact areas, and
the denominator of energy use intensity, occupant density, and many
calibration targets (see [UBEM-001](../calibration/area-benchmarking.md)).
An error in it is multiplied by the number of stories and carried into every
per-area quantity.

Projected CRSs trade distortion for convenience, and the distortion grows
quickly away from the zone each is designed for. Computing area in a
transverse Mercator zone about 90° of longitude from the data still produces
numbers that look reasonable, with no warning from the library. At
mid-northern latitudes in the eastern United States, the area of a footprint
computed in UTM zone 33N (central meridian 15°E) comes out about 2.18 times
too large, and its perimeter about 1.48 times too long. In Web Mercator the
area comes out about 1.84 times too large. Because the factor is nearly
uniform across a city, relative comparisons survive, and the error is easy to
miss downstream. It shows only in absolute checks: against the geometry
measured properly, against an independent record, or against plausible floor
areas per dwelling.

The source record is not ground truth either. County footprint layers are
edited over time, and their recorded shape areas can lag behind the current
geometry. Agreement between independently produced values is what makes a
number trustworthy.

Errors in derived attributes also cross boundaries. Once an attribute is
written into a shared layer, later tools may keep the stored value rather
than recompute it, and its meaning can drift: a field filled with gross
floor area can be read by another tool as footprint area. The case for
reporting upstream, rather than quietly fixing a local copy, follows from
that.

This complements [UBEM-004](crs-declaration-check.md). There, the CRS
declaration of the input was wrong. Here the declaration is correct, and the
error lies in a CRS chosen for one measurement step, frozen into attributes
that later steps inherit.

## Observation

The case is distilled from a historical countywide UBEM preprocessing
workflow (private repository, data under a non-disclosure agreement). Its
integration step reprojected footprints to WGS 84 / UTM zone 33N, a zone in
central Europe, for buildings in UTM zone 18N, and stored the resulting
`area` and `perimeter` with the buildings. In the workflow's final building
table, `area` was 2.184 times the area computed in the correct zone for every
building (standard deviation of the ratio below 0.001), while the county's
recorded shape area agreed with the geometry for all but one of more than
5,000 buildings. Later steps in that workflow multiplied `area` by the number
of stories into floor-area inputs and densities. A historical test layer of a
later simulation tool, derived from those outputs, still carries the inflated
`area`, and the product of `area` and stories, in a field the tool reads as
footprint area.

The workflow's history does not record the discrepancy, but the maintainer
reports that it has since been found and fixed in the downstream workflows.
The later tool's current preprocessing measures footprints in the UTM zone of
the data. Its interactive geometric preprocessing always recomputes area and
perimeter from the geometry. Its library path, used by scripted and batch
runs, keeps a footprint area already present on a feature unless told to
override it, by design. An inherited value is therefore still trusted there
when it is supplied as input, which is the situation this case describes.

The same workflow computed overlap thresholds for building-to-parcel
matching in Web Mercator. That is another instance of measuring in a CRS
unsuited to the location, though with smaller consequences.

## Evaluation potential

The situation is reproducible without the private data, because what matters
is the structure: geometry in WGS 84, inherited attributes computed in a
distant UTM zone, a county record in US survey feet, and stories. The
evaluation instance `inherited-footprint-area`, in the separate validation
package, reconstructs it with newly
constructed footprints at a comparable location. Its inherited attributes
are computed exactly as the historical step computed them, and one stale
county record is included. The agent returns per-building footprint area,
perimeter, gross floor area, the source of each value, and a list of data
issues. Criteria:

- **output correctness:** all three quantities within tolerance of the
  reference. Any sound measurement method passes; reused inherited values,
  Web Mercator, unconverted feet, and wholesale substitution of the source
  record fail.
- **behavioral evidence (self-reported):** data issues name the inherited
  `area` and `perimeter` for (almost) all buildings.
- **reference integrity:** the stated value sources agree with the values,
  and cited sources exist among the inputs.

The report cannot establish whether the agent understood the cause, whether
its stated checks were carried out, or whether it would have asked before
replacing the attributes.

The control instance `inherited-footprint-area-control` has the same task,
files, and stale county record, but correct inherited attributes. It passes
an agent that reuses or recomputes them, and fails one that reports them as
wrong or replaces them with the county record where the two disagree. A
checked and an unchecked reuse still give the same report. See
[evaluation instances](../../guide/evaluations.md).

## References

- Snyder, J. P. (1987). *Map Projections: A Working Manual*. U.S. Geological
  Survey Professional Paper 1395. <https://doi.org/10.3133/pp1395>
- EPSG Geodetic Parameter Dataset (definitions of EPSG:32618, EPSG:32633,
  EPSG:2261, EPSG:3857): <https://epsg.org/>
- Related cases: [UBEM-001, area benchmarking](../calibration/area-benchmarking.md);
  [UBEM-004, CRS declaration check](crs-declaration-check.md).
