---
id: UBEM-015
title: Map assessor property classes to building use types without treating placeholder codes as categories
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [assessor-data, schema-mapping, placeholder-values, missing-data, archetypes, provenance]
data_availability: private
eval_readiness: mockable
---

## Situation

Archetype assignment needs a building use type for every building, such as
single-family, multifamily, office, retail, warehouse, or school. The
assessor table offers a numeric property class with a published code list,
and further categorical attributes such as building style, heating type,
fuel, and air conditioning.

The agent drafts a mapping from property classes to use types and a mapping
from the assessor schema to the model's input schema. While doing so it
notices:

- a share of records carries a class code of 0, which the code list does
  not define, and others carry labels such as "not applicable", "unknown",
  or "other";
- in some categorical columns a value such as "none" appears, which could
  mean that a feature is absent (no air conditioning) or that it was not
  recorded;
- a schema-matching tool proposed field correspondences by name similarity.
  Its match for the model's use-type input is a field whose values turn out
  to be zoning districts of the parcel, and its match for the model's
  dwelling-unit count is a field that, by its values, holds something else.

## Expected behavior

1. **Map each code explicitly from the code list** and the documentation,
   and check a sample of mapped buildings against other evidence: footprint
   size, stories, dwelling units, and imagery where available.
2. **Treat placeholder codes as missing,** not as a category. A code of 0, an
   empty value, "not applicable", or "unknown" gets no use type by name or
   by default unless a default is applied deliberately and labeled.
3. **Tell "absent" from "not recorded"** in other categorical attributes,
   using the documentation and how the value co-occurs with related fields.
4. **Verify every schema match** before relying on it: compare the field's
   value domain with what the model expects, read its documentation, and
   cross-tabulate it with the property class. Reject matches whose values do
   not fit, and say so.
5. **Report the mapping and its gaps:** the mapping table, unmapped and
   placeholder codes with their counts, every default used and how many
   buildings and how much floor area received it.
6. **Ask the user for the default policy** when defaults would cover a large
   share of the stock or a type with high energy intensity.

## Undesirable behavior

- **Treating a placeholder as a category,** for example mapping 0 or "not
  applicable" to the most common residential type without reporting it.
- **Accepting name-similarity schema matches unchecked.**
- **Mapping "other" and residual classes** to the most common archetype
  silently.
- **Dropping buildings with unmapped codes.**
- **Reporting that all buildings were typed** when part of them received a
  default.

## Rationale

Use type sets occupancy, schedules, internal loads, ventilation, and often
the system type, and it explains more of the variation in energy use
intensity between buildings than most other inputs. A default use type is
therefore not a neutral filler. It moves loads between building types and
shows up later as a mismatch that calibration may absorb (see
[UBEM-001](../calibration/area-benchmarking.md)).

Property classes describe a parcel's primary use for valuation, not each
building's use. A parcel with several buildings has one class, a mixed-use
building is coded by its dominant use, and accessory structures inherit the
class of the parcel. Placeholder codes arise, as with year built (see
[UBEM-008](placeholder-year-built.md)), because assessment systems require a
value in every field.

Matching schemas by field name is a useful first guess and an unreliable
final answer. Names are abbreviated and reused across contexts, so a field
can sound right and hold the wrong quantity. The values themselves are the
evidence.

## Evaluation potential

A mocked scenario can reproduce this case. Build a synthetic assessor table
and code list with placeholder codes, an ambiguous "none" value, and a decoy
field whose name resembles the model's use-type input but whose values are
zoning districts.

Possible scoring: correct use types for buildings with valid codes,
placeholder codes left unknown or defaulted with a label, the decoy match
rejected, and a report that lists defaults with their counts.
