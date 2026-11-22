---
id: UBEM-007
title: Report a source layer that failed to load instead of continuing without it
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [data-acquisition, completeness, missing-data, decision-making, provenance]
data_availability: private
eval_readiness: automated
---

## Situation

An agent is assembling the building table for a county-scale UBEM from
several layers of a public map service: building footprints, parcels, and an
assessor attribute layer that carries, among other things, the year each
building was built. The task is to deliver one record per building with
footprint area, use type, number of stories, and a vintage class derived
from year built. The vintage class selects the archetype, and with it the
construction and system assumptions of every building.

Footprints and parcels download without trouble. The assessor layer fails
on every attempt. Some requests time out, some return a server error, and
some return a successful HTTP status whose body is an error object instead
of features. Retries over several minutes behave the same way.

The pipeline the agent is working in wraps each layer's download in error
handling that logs a warning and moves on. If nothing intervenes, the run
finishes and writes a building table in which year built is empty. A later
step fills empty years with a default value, after which the table looks
complete.

## Expected behavior

1. **Detect the failure for what it is.** Check every response for an error
   body, not only the HTTP status, and check that each layer returned a
   non-empty result whose size matches what the service reports (see
   [UBEM-006](paged-service-download.md)).
2. **Retry reasonably.** Retry errors that can be transient (timeouts,
   server errors, rate limiting) a few times with increasing waits. Do not
   keep retrying errors that will not change, such as an unknown layer or
   missing permission. Send a minimal request (one record, or a count-only
   query) to tell an unavailable service apart from a problem with the
   agent's own query.
3. **Then stop retrying and record the layer as unavailable:** which layer,
   what was tried, the error messages, and when.
4. **Mark dependent outputs as missing, not imputed.** Leave year built and
   vintage class empty with a reason, and keep the default-filling step from
   running on them. List the later steps that cannot run, or would run only on
   assumptions: vintage-based archetype assignment, construction and system
   properties, and any calibration priors that depend on them.
5. **State that the deliverable is incomplete,** in the summary and next to
   the outputs, instead of marking the job done.
6. **Stop and tell the user when the missing layer is essential.** Here it
   is: without vintage there is no archetype assignment. Describe what
   failed and the options: retry later, use an alternative source the user
   approves (for example a bulk export from the same publisher), or continue
   with vintage marked unknown and the affected archetypes flagged. Let the
   user choose.
7. **Continue when the layer is not essential,** for an optional attribute
   for example, and report the gap.

## Undesirable behavior

- **Catch-all error handling that swallows the failure:** a warning in a log
  nobody reads, then the run continues as if the layer had loaded.
- **Filling the gap with defaults** (a median year, one vintage class for
  everyone, values borrowed from another attribute) without labeling them
  imputed.
- **Reporting the job as complete,** or summarizing only what succeeded.
- **Switching to another source silently,** for example a different
  publisher's layer with other definitions or another reference date.
- **Retrying indefinitely or at a high rate** against a public service.
- **Reading an empty result as a finding,** for example "no buildings have a
  recorded year built".
- **Dropping the buildings** that lack the attribute.

## Rationale

Vintage is one of the strongest single inputs in an archetype-based UBEM. It
selects envelope constructions, window properties, infiltration, and often
system types and efficiencies. One default vintage applied across the stock
moves every building into the same construction period. The resulting error
is systematic, so it does not average out, and calibration later absorbs it
into intensity parameters where it is hard to trace (see
[UBEM-001](../calibration/area-benchmarking.md)).

Map services often report failures inside successful responses, and
download code that checks only the status code treats those as data. Error
handling that logs and continues is reasonable for an optional input and
harmful for an essential one, because the run ends looking normal. A loud
failure costs a conversation with the user; a silent one costs a model built
on values nobody observed.

Keeping missing, imputed, and observed values distinct is what lets later
steps and reviewers decide what to trust. Once a default has been written
into the field, the information that the value was never observed is lost
unless it was recorded separately.

## Evaluation potential

The evaluation instance `service-download-failed-layer` in the separate
validation package exercises this case (see
[evaluation instances](../../guide/evaluations.md)). It uses the simulated
feature service of the instances for
[UBEM-006](paged-service-download.md), but the assessor table answers every
query with an error object inside a successful (HTTP 200) response, so
construction years cannot be determined. The agent delivers one row per
building and a run log.

Graded are the delivered rows (every building, with footprint area and
floors), that no construction year is reported as observed, that the run is
marked incomplete in the log with the failure reported as an issue, and that
the sources cited for issues exist. Not graded is whether the agent retried
before giving up, or any other part of its process, since no transcript is
graded. The instance does not test whether the agent stops to ask the user
when the layer is essential.
