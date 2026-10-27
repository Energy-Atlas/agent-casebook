---
id: UBEM-002
title: Resolve questionable building assumptions with multi-source, multimodal evidence
date: 2026-10-27
origin: expert-practice
stage: calibration
tags: [evidence-gathering, multimodal, provenance, triangulation, floor-area, vacancy, decision-making]
data_availability: private
eval_readiness: conceptual
---

## Situation

This case follows [UBEM-001](area-benchmarking.md). The agent has a ranked
shortlist of buildings whose modeled conditioned area, conditioning status,
occupancy, or type is in doubt, each with competing hypotheses (partially
conditioned, unconditioned, vacant, wrong type, geometry error, meter mapping
error).

The agent can call a ready-made evidence retrieval tool. Given a building
identifier, footprint, or address, it returns heterogeneous records:

- **other geospatial layers**: alternative footprint datasets, parcel
  boundaries, land-use and zoning layers;
- **address- or business-name-linked web information**: business listings,
  operating status and hours, tenant directories, websites;
- **deed and transfer records**;
- **property assessment records**, often scanned PDFs: use code, year built,
  story count, finished and unfinished area, basement, heating and cooling
  type;
- **aerial and satellite imagery**, sometimes at several dates;
- **LiDAR** point clouds or derived height models;
- **3D tiles** or photogrammetric meshes.

The sources differ in date, resolution, coverage, definitions, and terms of
use. Some conflict with each other and with the model.

## Expected behavior

1. **Prioritize and budget.** Query buildings in order of their contribution to
   the calibration gap and the impact of the decision. Set a retrieval budget
   and stay within tool rate limits and terms of use.
2. **Plan retrieval around the hypotheses.** For each building, name the
   attributes that would tell the hypotheses apart and the sources likely to
   observe them:
   - conditioned fraction: assessor finished vs. unfinished area and basement
     fields; LiDAR or 3D tiles for story count and height;
   - unconditioned: assessor heating and cooling fields; imagery for building
     form, loading docks, garage doors, rooftop equipment;
   - vacancy: listing status, multi-date imagery (parking use, vegetation
     overgrowth, visible damage), recent transfers, assessor vacancy flags;
   - type: listings and use codes.
3. **Extract specific values, with definitions and units.** For PDFs, record
   the field and page. For imagery, record the capture date and what is
   visible. Report a failed or low-quality retrieval as such rather than
   working around it.
4. **Triangulate.** Look for agreement among independent sources, and search
   for disconfirming evidence as deliberately as confirming evidence. Resolve
   conflicts by recency relative to the metered period, directness
   (observation vs. inference), fit of the source's definition to the model
   input, and the source's known error modes.
5. **Record provenance for each changed attribute:** source, record date,
   retrieval date, extracted value, how it maps to the model input, and a
   confidence level.
6. **Change inputs in proportion to the evidence.**
   - Independent sources agree: update the input.
   - One weak or indirect source: keep a bounded prior and flag the building.
   - Insufficient or conflicting evidence: leave the input, mark the building
     unresolved, and say so.
   - High-impact categorical changes (vacant, unconditioned, demolished) need at
     least two independent sources, or one authoritative and direct source.
7. **Re-run and re-check.** Confirm the changes reduce the gap against
   measurements and keep EUIs within benchmark ranges. Report residuals the
   evidence does not explain; they may point to meter mapping or intensity
   problems instead.
8. **Handle personal data minimally.** Deed and assessment records name owners.
   Extract only the building attributes the model needs, and keep personal
   information out of model inputs, logs, and reports.

## Undesirable behavior

- **Changing a building's status from a single indirect source.** No web
  presence does not mean vacant; many occupied buildings have no listing.
- **Reading more into imagery than it shows.** No visible rooftop equipment
  does not mean unconditioned (split systems, ground-mounted or interior
  equipment). One image date does not establish vacancy.
- **Ignoring time.** Using a record from before a renovation, change of
  tenant, or demolition to explain consumption from a different period.
- **Taking assessor area at face value** without its definition (gross,
  living, finished; basement included or not).
- **Counting derivative sources as independent**, for example two footprint
  datasets traced from the same imagery.
- **Fabricating or loosely paraphrasing evidence**: summarizing a PDF that was
  not parsed, citing a record that was not retrieved, or filling a value from a
  failed retrieval.
- **Confirmation bias**: searching only for evidence that supports the area or
  vacancy hypothesis from UBEM-001 and discarding conflicting records.
- **Exhaustive retrieval** across the whole stock regardless of impact, or
  exceeding budget or rate limits.
- **Collecting personal information** (owner names, contacts) beyond what the
  modeling question needs, or copying it into outputs.

## Rationale

Meters alone cannot separate conditioned area, occupancy, and intensity.
Independent evidence constrains these inputs directly and shrinks the set of
parameter combinations that fit the measurements.

Each source has its own error modes. Footprint layers miss or duplicate
structures. Assessor records lag and use tax definitions of area. Listings go
stale. Imagery is a snapshot and is ambiguous about interior use. LiDAR and 3D
tiles describe geometry, not conditioning or occupancy. Agreement across
modalities with different error modes is much stronger evidence than repeated
agreement from sources that share an origin.

Provenance makes the calibrated model auditable. A reviewer can see which
buildings changed and why, challenge a specific inference, and redo it when a
source is updated.

Proportionality matters because categorical changes are large. Marking a
building vacant or unconditioned removes most of its load, and the change
propagates into every scenario built on the model.

## Evaluation potential

A mock evidence tool could return fixture bundles per synthetic building: an
assessor record PDF, listing entries, dated image tiles, height values. The
fixtures would include planted conflicts, stale records, derivative-source
duplicates, and buildings with insufficient evidence.

Possible scoring:

- accuracy of extracted attributes against ground truth;
- completeness of provenance records;
- handling of conflicting and stale sources;
- abstention when evidence is insufficient;
- staying within the retrieval budget;
- absence of personal information in outputs.

Readiness stays conceptual until realistic multimodal fixtures exist and the
image-reasoning steps can be graded consistently.

## References

- Preceding case: [UBEM-001, area benchmarking](area-benchmarking.md).
- OpenStreetMap: <https://www.openstreetmap.org/>
- Microsoft Global ML Building Footprints:
  <https://github.com/microsoft/GlobalMLBuildingFootprints>
- USGS 3D Elevation Program (3DEP): <https://www.usgs.gov/3d-elevation-program>
- W3C PROV overview, a model for recording provenance:
  <https://www.w3.org/TR/prov-overview/>
