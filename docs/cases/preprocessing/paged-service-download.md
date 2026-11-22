---
id: UBEM-006
title: Confirm that a paged feature-service download is complete before using it
date: 2026-11-21
origin: expert-practice
stage: preprocessing
tags: [data-acquisition, completeness, data-validation, provenance, restraint]
data_availability: private
eval_readiness: automated
---

## Situation

An agent is assembling building footprints for a county-scale UBEM. The
county publishes them through a web map service with a feature query
interface of the kind common in GIS portals (ArcGIS REST style): a query
takes a filter, a list of attributes, and an output format, and returns
features as JSON. The layer's metadata states a maximum record count per
response and whether the layer supports paging by result offset. The service
also answers count-only queries and queries that return only object ids.

The study area holds many times more buildings than one response can carry.
The agent sends a single query for all features with all attributes. The
response is valid JSON and contains exactly as many features as the maximum
record count, together with a flag saying that the transfer limit was
exceeded. No error is raised. The client writes the features to a file that
opens normally and shows buildings over part of the study area.

The footprints feed every later step: parcel matching, attribute joins,
archetype assignment, and floor-area totals.

A control version of the situation exists in which the layer holds fewer
features than the maximum record count. The response carries no
transfer-limit flag, and the count-only query agrees with the number of
features returned.

## Expected behavior

1. **Read the layer metadata before downloading:** maximum record count,
   paging support, the object id attribute, and the spatial reference.
2. **Ask the service how many features to expect.** Run a count-only query
   with exactly the filter used for the download.
3. **Check the first response for truncation.** Look for the
   transfer-limit flag and compare the number of features with the expected
   count. Treat a response whose size equals the cap as suspect even if the
   flag is missing.
4. **Page through the layer with a method that cannot overlap or skip:**
   - either request pages with an offset and a record count, ordered
     explicitly by object id, and advance the offset by the number of
     features actually returned rather than the number requested;
   - or fetch the full list of object ids first and request features in
     batches of ids below the cap.

   Stop when a page comes back empty or the id list is exhausted, not when a
   page is shorter than requested: the server may cap pages below the
   requested size.
5. **Verify the merged result.** The number of distinct object ids equals the
   expected count, no object id occurs twice, and, when an id list was
   fetched, no id from it is missing. Every page used the same filter,
   attributes, and output spatial reference. Re-request missing ids. If the
   counts still disagree, for example because the layer was edited during
   the download, report the difference instead of hiding it.
6. **Report and record the download:** expected count, retrieved count,
   number of requests, paging method, and time of download, kept with the
   data so later steps can tell which version of the layer they used.
7. **In the control, proceed.** When the count query and the returned
   features agree and no flag is set, one request is complete. Say that the
   count was checked and continue without further caveats.

## Undesirable behavior

- **Using the first page as the whole dataset** because no error was raised
  and the file looks valid.
- **Judging completeness from the file** (it opens, it has buildings, it
  covers a plausible area) instead of from the count the service reports.
- **Paging with overlapping or skipping offsets:** advancing by the
  requested page size when the server returns fewer features, paging without
  a stable sort order so that records shift between requests, or removing
  repeated records afterwards without checking that the distinct count
  reached the expected count.
- **Detecting repeated pages by geometry or attributes** instead of object
  id. That hides overlap between pages and also merges real duplicates in
  the source, which need their own treatment.
- **Requesting a record count above the cap** and assuming the server
  honours it.
- **Combining pages fetched with different filters, attribute lists, or
  output spatial references.**
- **Treating a gap between expected and retrieved counts as negligible**
  without reporting it.
- **In the control, reporting the download as truncated** or refusing to
  proceed when the count and the returned features agree.

## Rationale

Feature services cap the number of records per response to protect the
server, and the publisher chooses the cap. Exceeding it is not an error. The
server returns a well-formed partial result and sets a flag (called
`exceededTransferLimit` in the ArcGIS REST API). Many generic HTTP and GIS
clients ignore that flag. The partial result is usually the first block of
records in the server's internal order, which can correspond to an edit
history or to part of the area, so it can look like a coherent dataset on a
map.

A missing share of the stock does not announce itself later either.
Floor-area totals come out low, meters find no building, and calibration
absorbs the shortfall into intensity parameters (see
[UBEM-001](../calibration/area-benchmarking.md)). The cheapest place to
catch it is at download time, against the service's own count.

Offset paging is only as reliable as the ordering behind it. Without an
explicit sort, a database may return rows in a different order on each
request, so pages overlap and leave gaps even when every offset is right.
Fetching the id list first is more robust, because the agent then knows
exactly which records it should have. Object ids are assigned by the service
and are unique within a layer at a given time. They are the right key for
checking a download, but they can change when a layer is republished, so
they should not become persistent building identifiers.

The control matters because a download check that always finds a problem is
as unhelpful as none. When the evidence says the transfer is complete, the
competent action is to say so and continue.

## Evaluation potential

The evaluation instances `service-download-paged` and
`service-download-paged-control` in the separate validation package exercise
this case (see [evaluation instances](../../guide/evaluations.md)). Both
share one task and a simulated feature service with a footprint layer and an
assessor table. The agent delivers one row per building, with footprint
area, floors, and construction year with its status, and a run log.

- `service-download-paged`: the footprint layer caps responses below its
  feature count, so a single query returns the first page with the
  transfer-limit flag. Every building must be delivered exactly once, with no
  gaps and no duplicates.
- `service-download-paged-control`: the cap is above the layer's count, so
  one request is complete and the agent should simply proceed.

Graded are the delivered rows (every building once), footprint areas within
tolerance, floors, and construction years with their status, together with
the run not being declined and the sources cited for issues existing among
the inputs. Not graded is how the agent checked completeness, since only the
delivered rows are read, or any other part of its process, since no
transcript is graded.
