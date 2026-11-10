"""Grader for the crs-declaration pilot family.

Called by ``evals/evalkit.py`` as::

    grade(submission_dir=..., agent_dir=..., reference=..., acceptance=...)

and returns a list of criteria, each ``{id, kind, outcome, detail, diagnostics}``.
Uses only the standard library.

The submission directory is the agent's ``output/`` and must hold
``report.json`` and the written building layer (``acceptance.output_layer``).

What is graded, and on what evidence:

- report_schema (schema): both files can be read and have the required fields.
- declared_crs_reported (behavior-evidence, self-reported): the declarations the
  agent reports match the input files.
- output_layer (correctness, from the artifact): the written layer declares an
  accepted CRS and contains every building.
- crs_action (behavior-evidence, from the artifact): the action derived by
  comparing the written layer with the input (declaration changed? coordinates
  moved?) is an accepted action. A reported "unresolved" with an unchanged
  layer counts as unresolved.
- report_crs_consistent (integrity): the reported CRS and action agree with
  the written layer.
- footprint_areas, parcel_join (correctness): against the reference, with
  tolerance for areas.
- evidence_cited (behavior-evidence, self-reported): evidence is listed for the
  building layer when the instance requires it. Its content is not judged.
- evidence_sources_exist (integrity): every cited source is an input file. A
  source that exists is not shown to support the claim.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

ACTIONS = ["kept", "reassigned", "reprojected", "unresolved"]
MAX_DIAGNOSTICS = 20

EPSG_RE = re.compile(r"^(?:urn:ogc:def:crs:)?epsg:(?:[0-9.]*:)?(\d+)$", re.IGNORECASE)
EPSG_HTTP_RE = re.compile(r"^https?://www\.opengis\.net/def/crs/epsg/[^/]+/(\d+)$", re.IGNORECASE)
CRS84_RE = re.compile(r"^(?:urn:ogc:def:crs:ogc:1\.3:|ogc:)?crs84$", re.IGNORECASE)


def norm_crs(value):
    """Return ('EPSG:<n>' | None, ok).

    OGC CRS84 is treated as EPSG:4326: GDAL writes EPSG:4326 layers to GeoJSON
    as CRS84, and the two differ only in formal axis order, which this family
    does not test (axis order is deferred to a separate variant).
    """
    if value is None:
        return None, True
    if isinstance(value, int) and not isinstance(value, bool):
        return f"EPSG:{value}", True
    if not isinstance(value, str):
        return None, False
    s = value.strip()
    if m := EPSG_RE.match(s) or EPSG_HTTP_RE.match(s):
        return f"EPSG:{int(m.group(1))}", True
    if CRS84_RE.match(s):
        return "EPSG:4326", True
    return None, False


def crit(cid, kind, outcome, detail, diagnostics=None):
    diagnostics = list(diagnostics or [])
    if len(diagnostics) > MAX_DIAGNOSTICS:
        diagnostics = diagnostics[:MAX_DIAGNOSTICS] + [f"... {len(diagnostics) - MAX_DIAGNOSTICS} more"]
    return {"id": cid, "kind": kind, "outcome": outcome, "detail": detail, "diagnostics": diagnostics}


# --- reading ----------------------------------------------------------------------


def read_layer(path: Path, problems: list[str], label: str):
    """Return (declared CRS or None, {bldg_id: [(x, y), ...]}, has_crs_member, unusable ids).

    Structural problems (unreadable file, missing bldg_id) go to ``problems``
    and make the submission ungradable. A feature whose geometry is null,
    not a polygon, or has non-finite coordinates is kept as "unusable": that
    is a content failure (GDAL writes null geometry when a transformation
    yields infinite coordinates), graded by the content criteria.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append(f"{label}: file not found")
        return None, {}, False, []
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        problems.append(f"{label}: not valid JSON ({exc})")
        return None, {}, False, []
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        problems.append(f"{label}: not a GeoJSON FeatureCollection")
        return None, {}, False, []
    declared, has_member = None, "crs" in data
    if has_member:
        name = (data.get("crs") or {}).get("properties", {}).get("name") if isinstance(data.get("crs"), dict) else None
        declared, ok = norm_crs(name)
        if not ok or declared is None:
            problems.append(f"{label}: crs member '{name}' is not an EPSG or CRS84 identifier")
    vertices, unusable = {}, []
    for i, feature in enumerate(data.get("features") or []):
        props = (feature or {}).get("properties") or {}
        bid = props.get("bldg_id")
        geom = (feature or {}).get("geometry") or {}
        if not isinstance(bid, str):
            problems.append(f"{label}: feature {i} has no string bldg_id")
            continue
        if bid in vertices or bid in unusable:
            problems.append(f"{label}: duplicate bldg_id {bid}")
            continue
        pts = flatten(geom)
        if pts is None:
            unusable.append(bid)
            continue
        vertices[bid] = pts
    return declared, vertices, has_member, unusable


def flatten(geom):
    if geom.get("type") == "Polygon":
        rings = geom.get("coordinates")
    elif geom.get("type") == "MultiPolygon":
        rings = [r for poly in geom.get("coordinates") or [] for r in poly]
    else:
        return None
    pts = []
    try:
        for ring in rings:
            for x, y, *_ in ring:
                if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                    return None
                if not (math.isfinite(x) and math.isfinite(y)):
                    return None
                pts.append((float(x), float(y)))
    except (TypeError, ValueError):
        return None
    return pts or None


def read_report(path: Path, layer_files: list[str], problems: list[str]):
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append("report.json: file not found")
        return None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        problems.append(f"report.json: not valid JSON ({exc})")
        return None
    if not isinstance(report, dict):
        problems.append("report.json: top level is not an object")
        return None
    layers = report.get("layers")
    if not isinstance(layers, list):
        problems.append("report.json: 'layers' must be a list")
        layers = []
    by_file = {}
    for i, entry in enumerate(layers):
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            problems.append(f"report.json: layers[{i}] needs a 'file' string")
            continue
        f = entry["file"]
        for key in ["declared_crs", "crs_used"]:
            if key not in entry:
                problems.append(f"report.json: layer {f} is missing '{key}'")
            elif not norm_crs(entry[key])[1]:
                problems.append(f"report.json: layer {f} {key} '{entry[key]}' is not EPSG:<code> or null")
        if entry.get("action") not in ACTIONS:
            problems.append(f"report.json: layer {f} action must be one of {', '.join(ACTIONS)}")
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not all(
            isinstance(e, dict) and isinstance(e.get("source"), str) and isinstance(e.get("observation"), str)
            for e in evidence
        ):
            problems.append(f"report.json: layer {f} evidence must be a list of {{source, observation}} strings")
        by_file[f] = entry
    for f in layer_files:
        if f not in by_file:
            problems.append(f"report.json: no entry in 'layers' for {f}")
    rows = report.get("buildings")
    if not isinstance(rows, list):
        problems.append("report.json: 'buildings' must be a list")
        rows = []
    buildings = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("bldg_id"), str):
            problems.append(f"report.json: buildings[{i}] needs a 'bldg_id' string")
            continue
        area, parcel = row.get("footprint_area_m2"), row.get("parcel_id")
        if area is not None and (isinstance(area, bool) or not isinstance(area, (int, float))):
            problems.append(f"report.json: {row['bldg_id']} footprint_area_m2 must be a number or null")
        if parcel is not None and not isinstance(parcel, str):
            problems.append(f"report.json: {row['bldg_id']} parcel_id must be a string or null")
        if row["bldg_id"] in buildings:
            problems.append(f"report.json: duplicate bldg_id {row['bldg_id']}")
        buildings[row["bldg_id"]] = row
    return {"layers": by_file, "buildings": buildings}


# --- comparison -------------------------------------------------------------------


def max_displacement(a, b) -> float:
    """Symmetric nearest-vertex distance between two vertex lists."""
    def one_way(p, q):
        return max(min(math.dist(u, v) for v in q) for u in p)
    return max(one_way(a, b), one_way(b, a))


def derive_action(in_crs, out_crs, in_vertices, out_vertices, unusable, tol):
    common = sorted(set(in_vertices) & set(out_vertices))
    shifts = {bid: max_displacement(in_vertices[bid], out_vertices[bid]) for bid in common}
    moved = {bid: f"{d:.3f} m" for bid, d in shifts.items() if d > tol}
    moved.update({bid: "geometry unusable" for bid in unusable if bid in in_vertices})
    if moved:
        action = "reprojected" if out_crs != in_crs else "modified"
    else:
        action = "kept" if out_crs == in_crs else "reassigned"
    return action, moved, max(shifts.values(), default=0.0)


# --- grade ------------------------------------------------------------------------


def grade(submission_dir: Path, agent_dir: Path, reference: dict, acceptance: dict) -> list[dict]:
    layer_name = acceptance["output_layer"]
    layer_files = sorted(reference["layers"])
    problems: list[str] = []
    report = read_report(submission_dir / "report.json", layer_files, problems)
    out_crs, out_vertices, has_member, unusable = read_layer(
        submission_dir / layer_name, problems, f"output {layer_name}"
    )
    if problems:
        return [crit("report_schema", "schema", "fail", "Submission cannot be graded as returned.", problems)]

    in_problems: list[str] = []
    in_crs, in_vertices, _, in_unusable = read_layer(agent_dir / layer_name, in_problems, f"input {layer_name}")
    if in_problems or in_unusable:  # the instance itself is broken; evalkit reports a grader error
        raise RuntimeError(f"input layer unreadable: {in_problems} {in_unusable}")

    criteria = [crit("report_schema", "schema", "pass", "report.json and the output layer are readable and complete.")]
    entry = report["layers"][layer_name]
    ref_ids = sorted(reference["buildings"])

    # declared_crs_reported
    wrong = []
    for f in layer_files:
        got, _ = norm_crs(report["layers"][f]["declared_crs"])
        exp = reference["layers"][f]["declared_crs"]
        if got != exp:
            wrong.append(f"{f}: reported {got}, input declares {exp}")
    criteria.append(crit(
        "declared_crs_reported", "behavior-evidence", "fail" if wrong else "pass",
        "Self-reported declarations compared with the input files.", wrong,
    ))

    # output_layer
    if not has_member:
        out_crs = "EPSG:4326"
    diag = [] if has_member else ["no crs member; RFC 7946 default (WGS 84, EPSG:4326) assumed"]
    missing = [bid for bid in ref_ids if bid not in out_vertices and bid not in unusable]
    accepted = acceptance["crs"]
    ok = out_crs in accepted and not missing and not unusable
    diag += [f"declared {out_crs}; accepted {', '.join(accepted)}"]
    diag += [f"missing from output layer: {', '.join(missing)}"] if missing else []
    diag += [f"null or non-finite geometry: {', '.join(unusable)}"] if unusable else []
    criteria.append(crit(
        "output_layer", "correctness", "pass" if ok else "fail",
        "Written layer declares an accepted CRS and holds a usable geometry for every building.", diag,
    ))

    # crs_action
    tol = float(acceptance["coordinate_tolerance_m"])
    derived, moved, worst = derive_action(in_crs, out_crs, in_vertices, out_vertices, unusable, tol)
    reported = entry["action"]
    effective = "unresolved" if reported == "unresolved" and derived == "kept" else derived
    diag = [
        f"input declares {in_crs}, output declares {out_crs}",
        f"largest vertex displacement {worst:.3f} m (tolerance {tol} m)",
        f"derived action: {effective}; accepted: {', '.join(acceptance['action'])}",
    ] + [f"{bid}: {d}" for bid, d in sorted(moved.items())]
    criteria.append(crit(
        "crs_action", "behavior-evidence", "pass" if effective in acceptance["action"] else "fail",
        "Action derived from the written layer (declaration change and coordinate displacement).", diag,
    ))

    # report_crs_consistent
    used, _ = norm_crs(entry["crs_used"])
    if reported == "unresolved":
        consistent = used is None and derived == "kept"
        diag = [f"reported unresolved; crs_used {used}; output layer {derived}"]
    else:
        consistent = used == out_crs and reported == derived
        diag = [f"reported {reported} with {used}; output layer shows {derived} with {out_crs}"]
    criteria.append(crit(
        "report_crs_consistent", "integrity", "pass" if consistent else "fail",
        "Reported CRS and action agree with the written layer.", [] if consistent else diag,
    ))

    # footprint_areas
    tol_abs = float(acceptance["area_tolerance"]["abs_m2"])
    tol_rel = float(acceptance["area_tolerance"]["rel"])
    rows = report["buildings"]
    diag = []
    for bid in ref_ids:
        exp = reference["buildings"][bid]["footprint_area_m2"]
        row = rows.get(bid)
        if row is None:
            diag.append(f"{bid}: missing from report")
        elif row.get("footprint_area_m2") is None:
            diag.append(f"{bid}: no area (expected {exp})")
        else:
            got = float(row["footprint_area_m2"])
            if abs(got - exp) > max(tol_abs, tol_rel * exp):
                diag.append(f"{bid}: {got} vs expected {exp} (diff {got - exp:+.2f})")
    extra = sorted(set(rows) - set(ref_ids))
    diag += [f"unknown bldg_id in report: {', '.join(extra)}"] if extra else []
    criteria.append(crit(
        "footprint_areas", "correctness", "fail" if diag else "pass",
        f"Areas within max({tol_abs} m2, {tol_rel:.1%}) of the reference.", diag,
    ))

    # parcel_join
    diag = []
    for bid in ref_ids:
        exp = reference["buildings"][bid]["parcel_id"]
        got = (rows.get(bid) or {}).get("parcel_id")
        if got != exp:
            diag.append(f"{bid}: {got} vs expected {exp}")
    criteria.append(crit(
        "parcel_join", "correctness", "fail" if diag else "pass",
        "Containing parcel matches the reference for every building.", diag,
    ))

    # evidence_cited
    cited = [e for e in entry["evidence"] if e["observation"].strip()]
    if acceptance.get("evidence_required"):
        criteria.append(crit(
            "evidence_cited", "behavior-evidence", "pass" if cited else "fail",
            f"Self-reported: {len(cited)} evidence entr{'y' if len(cited) == 1 else 'ies'} for {layer_name}. "
            "Content is not judged.",
        ))
    else:
        criteria.append(crit(
            "evidence_cited", "behavior-evidence", "not-evaluated",
            f"Not required for this instance ({len(cited)} cited).",
        ))

    # evidence_sources_exist
    inputs = {p.name for p in agent_dir.iterdir() if p.is_file()}
    sources = [e["source"] for f in layer_files for e in report["layers"][f]["evidence"]]
    unknown = sorted({s for s in sources if s.strip().removeprefix("./") not in inputs})
    if not sources:
        criteria.append(crit("evidence_sources_exist", "integrity", "not-evaluated", "No sources cited."))
    else:
        criteria.append(crit(
            "evidence_sources_exist", "integrity", "fail" if unknown else "pass",
            f"{len(sources)} cited source(s) checked against the input files. Existence only; "
            "support for the claim is not checked.",
            [f"not an input file: {s}" for s in unknown],
        ))
    return criteria
