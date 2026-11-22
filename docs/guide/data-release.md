# Releasing data-derived material

This repository is public and licensed under CC BY 4.0. Many cases come from
work on data that cannot be published: utility meter records, assessor and
parcel data, building surveys, private repositories. This page describes how
to contribute what such work teaches without publishing the data.

The short rule: **publish the mechanism, not the data.** A case is worth
recording because of the situation and the behavior it calls for, and these
can almost always be described, measured, and reproduced without a single
real record.

## What may be published

From safest to riskiest:

| Tier | What becomes public | Default |
| --- | --- | --- |
| 0. Qualitative case | The situation, the expected and undesirable behavior, the reasoning. No data | Always allowed |
| 1. Synthetic reconstruction | Newly constructed data that reproduces the structure of the real problem: the mechanism, magnitudes, units, and the evidence an agent would use | Allowed; record how it was reconstructed |
| 2. Aggregate statistics | Ratios, distributions, counts, and error magnitudes measured on the private data | Allowed above the thresholds below |
| 3. Open third-party data | Records from openly licensed sources, used under their licenses | Allowed after a license check |
| 4. Transformed real records | Real geometry or attributes, shifted, coarsened, masked, or with identifiers removed | Not by default. Only with written approval from whoever controls the data |

Prefer the lowest tier that keeps what the case needs. Evaluation instances,
which live in the separate validation package, should normally be tier 1: the
instance `inherited-footprint-area` reconstructs a real workflow's error with
invented footprints, and a provenance record kept with it says what was kept
and what was changed.

## Why removing identifiers is not enough

Building and energy data resist anonymization:

- **Geometry identifies.** A real footprint outline, even shifted or rotated,
  can be matched against public footprint datasets. Removing identifier
  columns or offsetting coordinates does not anonymize it.
- **Location-derived identifiers can be reversed.** Building identifiers built
  from coordinates (such as UBIDs) encode location. Hashing a small
  identifier space can be reversed by enumeration, and a key stored next to
  the data protects nothing.
- **Attribute combinations identify.** Year built, stories, floor area, use
  type, and lot size together often single out one building in public
  assessment records.
- **Energy use is personal data.** Per-building consumption reveals
  occupancy. Utilities typically release it only in aggregates with minimum
  group sizes, for example California's "15/15" rule: at least 15 customers,
  and no single customer above 15 % of the total.
- **The agreement decides, not the technique.** A data agreement or NDA may
  cover derived data as well as the original records. "Anonymized" does not
  mean "permitted" unless the data owner says so. Source code without a
  license is not reusable either: describe its mechanisms in your own words,
  and do not copy it.
- **Redaction can remove the case.** Moving data to another location changes
  projection distortion, rounding values can hide a stale record, and
  dropping rows can remove the one that matters. Check every transformation
  against what the case depends on.

## Release checklist

For any case, instance, or document that draws on non-public data:

1. **Classify each file** by the tiers above. Anything derived from restricted
   data (tier 2 and above) needs a check by the person responsible for the
   data agreement before it is pushed.
2. **Name sources by description and commit only**, for example "historical
   preprocessing repository (private), commit `1a2b3c4`". Keep
   the key from labels to actual repositories, projects, and places outside
   this repository, for example with the run artifacts or in a private
   companion repository.
3. **Leave out identifying context** when the source is restricted: project
   names, city or campus names, client names, people, and file paths that
   contain them.
4. **Record reconstruction decisions** with the reconstruction (for an
   evaluation instance, in the validation package): what was kept, what was
   changed or dropped, and the effect on realism.
5. **Aggregate thresholds.** A statistic quoted from private data must
   describe at least 15 buildings or customers, with no single one dominating
   it. Do not quote values for individual real buildings.
6. **Coordinates.** Synthetic fixtures need a location only when the case
   depends on it (projection zone, latitude). Place them where the mechanism
   holds, without reproducing the private study area's real layout.
7. **Agent-run artifacts stay private.** Transcripts, submissions, and logs
   contain local paths and user names, and can echo inputs. Bring back
   findings and checksums, not the artifacts.
8. **Run the checks.** `python scripts/casebook.py check` includes the release
   scan (below). It catches accidents, not deliberate re-identification, so a
   human review is still required.
9. **Review the story as well as the data.** A case can be data-safe and still
   sensitive, for example when it describes a mistake in an identifiable
   project. When in doubt, ask the owner of the work.

## Release scan

`python scripts/casebook.py check` scans every tracked or new, non-ignored
text file in the repository for:

| Finding | What it looks for |
| --- | --- |
| `secret` | API keys and tokens in common formats, private key blocks, and credential-like assignments |
| `secret-file` | File names that suggest credentials (`api_key.txt`, `credentials.json`, `.env`, `*.pem`), since a bare key inside has no recognizable format |
| `email` | Email addresses, except `example.com`/`example.org` and commit-attribution addresses |
| `local-path` | Paths into a personal user folder (Windows, macOS, Linux) |
| `street-address` | A house number followed by a street name and suffix |
| `parcel-id` | Section-block-lot style parcel numbers |
| `building-id` | UBID-style building identifiers |

Matched text is masked in the output, so a found secret is not printed
again. To scan files before adding them, for example a candidate fixture:

```bash
python scripts/casebook.py scan <file-or-directory> ...
```

A line that legitimately matches can be exempted by adding the marker
`release-scan: allow` on that line, for example in a Markdown or code
comment. Use it sparingly and say why.

The scan does not find real footprint geometry, quasi-identifying attribute
combinations, or identifying context written in prose. Those need the
checklist and a reviewer.
