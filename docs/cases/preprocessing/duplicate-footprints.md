---
id: UBEM-012
title: Merge duplicate footprints by group with an explicit survivor rule, and leave stacked parcels intact
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [duplicates, geometry, parcels, provenance, floor-area, restraint]
data_availability: private
eval_readiness: mockable
---

## Situation

An agent is producing one footprint per building from a layer assembled
from several sources and capture campaigns. Many buildings appear more than
once as overlapping or nearly identical polygons, and the copies differ:
one has height and stories, another has only geometry, a third comes from a
more recent capture. Some groups form chains: A overlaps B almost entirely,
B overlaps C almost entirely, but A and C overlap less. Elsewhere, row
houses and attached buildings share walls, so their polygons touch along an
edge without overlapping.

The parcel layer, which the agent uses next to bring in assessor
attributes, contains stacked parcels: identical polygons on top of each
other, one per condominium unit, each with its own owner record, unit floor
area, and use. A generic duplicate-removal step in the pipeline would treat
those as duplicates too.

The existing de-duplication code loops over pairs of overlapping
footprints, keeps the first of each pair it meets, and deletes the other.

## Expected behavior

1. **Define what counts as a duplicate, explicitly:** for example a mutual
   overlap share above a stated threshold, computed in a CRS suited to
   measuring at the data's location (see
   [UBEM-010](threshold-projection.md)), optionally combined with agreement
   of attributes. Attached buildings that only share an edge must not
   qualify.
2. **Group duplicates as connected components,** not pair by pair, and
   inspect chained groups whose members do not all overlap each other. A
   sloppy polygon can bridge two distinct buildings; split or flag such
   groups rather than merging them blindly.
3. **Choose the survivor of each group by a stated rule,** for example the
   most authoritative or most recent source first, then the most complete
   attributes, then geometric quality. Fill gaps in the survivor from other
   members when they agree, and record which attribute came from which
   record.
4. **Keep the merged records traceable:** the ids of all members, the rule
   applied, and any conflicts between members, such as different story
   counts.
5. **Report** the number of groups, the number of records merged, the rule,
   and the conflicts.
6. **Leave stacked parcels intact.** Identical parcel polygons with
   distinct unit records are a representation of condominium ownership, not
   an error. Keep every unit record and aggregate the unit attributes to the
   building: sum the unit floor areas, combine use types into mixed-use
   shares, and count units.
7. **When coincident parcels could be either units or errors,** look for
   evidence (distinct owner or unit identifiers, unit numbers, condominium
   class codes, a total unit floor area plausible for the building) and
   report the ones that remain unclear.

## Undesirable behavior

- **Keeping the least complete record,** for example whichever copy comes
  first, and losing heights and stories that another copy had.
- **Merging pairwise in a loop,** so that the result depends on processing
  order: chains of three or more leave duplicates behind or lose every
  member.
- **Matching only identical geometry,** which misses near-duplicates, or
  using a threshold so loose that attached buildings are merged.
- **Deleting stacked condominium parcels as duplicates,** which removes
  units, their floor area, and often the non-residential uses in a
  mixed-use building.
- **Removing records without keeping track** of which source records were
  dropped and why.

## Rationale

Duplicate footprints inflate building counts and floor area, and they do so
unevenly: they concentrate where sources were combined or recaptured. The
result is an area excess that later looks like a calibration problem (see
[UBEM-001](../calibration/area-benchmarking.md)). Duplicates can also
originate in the download itself, when pages overlap (see
[UBEM-006](paged-service-download.md)); that kind is removed by object id
before any geometric de-duplication.

Which copy survives decides the attributes the building carries forward.
A rule that ignores completeness often keeps an outline without height or
stories, which then has to be imputed. Grouping before choosing is what
makes the outcome independent of record order; a pairwise loop is not
transitive.

Attached buildings are common in older urban stocks and legitimately share
boundaries. Their shared walls matter for the energy model, so merging them
destroys real information.

Many assessment systems treat each condominium unit as a separate taxable
parcel. Some represent units as identical polygons stacked over the
building's lot, others as a parent parcel with unit records and no geometry
of their own. In both, the unit records hold the floor areas and uses the
building model needs. They should be aggregated to the building, the
building matched to its lot once (see
[UBEM-009](building-parcel-matching.md)), and never thinned out as
duplicates.

## Evaluation potential

A mocked scenario can reproduce this case. Build synthetic footprints with
duplicate groups of two to four records, including a chain and a group
bridged by a distinct building, with varying attribute completeness; a row
of attached houses sharing walls; and a parcel layer with stacked unit
parcels over one lot.

Possible scoring: the final building count and footprints against the
reference, survivor attributes as complete as the group allows, attached
houses kept separate, condominium units preserved and aggregated, and a
report that states the rule and lists the merged ids.
