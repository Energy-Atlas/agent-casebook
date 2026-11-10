"""Generate the crs-declaration pilot fixtures (synthetic and deterministic).

Writes, for each variant, ``<out-root>/<instance-id>/`` with:

- ``agent/``: task.md, buildings.geojson, parcels.geojson, provider_notes.md
- ``reference/expected.json``
- ``submissions/<name>/``: sample submissions for the grader self-test

Both variants share the same geometry, task text, and provider notes. They
differ only in the CRS declared by buildings.geojson:

- crs-declaration-mislabeled: declares EPSG:4326, coordinates are WGS 84 /
  UTM zone 18N (EPSG:32618);
- crs-declaration-control: declares EPSG:32618, which is correct.

The location is arbitrary and the data are invented. Uses only the standard
library; ``random.Random(seed).random()`` is stable across Python versions.

    python evals/families/crs-declaration/generate.py [--out-root evals/instances]
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent.parent / "instances"

SEED = 20261110
TRUE_CRS = "EPSG:32618"
URN = "urn:ogc:def:crs:EPSG::{}"
VARIANTS = {
    "crs-declaration-mislabeled": {"buildings_declared": "EPSG:4326"},
    "crs-declaration-control": {"buildings_declared": "EPSG:32618"},
}

E0, N0 = 498_250.0, 4_705_120.0  # south-west corner of the block, metres
STREET = 15.0  # gap between the two parcel rows
SETBACK = 3.0
BUILDINGS_PER_PARCEL = [2, 1, 3, 0, 2, 1]  # parcels P01..P06, row by row
RECORDED_AREAS = 4  # buildings with a source-recorded area
L_SHAPES = 3  # buildings with a notched (L-shaped) footprint

PROVIDER_NOTES = """\
# Provider notes: building footprints

Footprints for the study block, digitized from orthoimagery by the survey
contractor and exported from the project GIS.

- Coordinate system of the delivered footprints: WGS 84 / UTM zone 18N.
- Linear unit: metre.
- `bldg_id`: contractor building identifier.
- `src_area_m2`: footprint area recorded by the contractor during site visits,
  rounded to 0.1 m². Recorded only for buildings visited on site; empty for
  the others.

The parcel layer is a separate cadastral extract and is not covered by these
notes.
"""


# --- geometry ---------------------------------------------------------------------


def shoelace(ring: list[list[float]]) -> float:
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:]))) / 2


def rect(x0, y0, x1, y1) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]


def r2(v: float) -> float:
    return round(v, 2)


def pick(rng: random.Random, n: int, k: int) -> set[int]:
    keys = [(rng.random(), i) for i in range(n)]
    return {i for _, i in sorted(keys)[:k]}


def build_block() -> tuple[list[dict], list[dict]]:
    rng = random.Random(SEED)
    uni = lambda a, b: a + (b - a) * rng.random()  # noqa: E731

    parcels = []
    y = N0
    for row in range(2):
        depth = r2(uni(38, 48))
        x = E0
        for col in range(3):
            width = r2(uni(32, 44))
            pid = f"P{row * 3 + col + 1:02d}"
            parcels.append({"parcel_id": pid, "ring": rect(r2(x), r2(y), r2(x + width), r2(y + depth))})
            x += width
        y += depth + STREET

    buildings = []
    for parcel, count in zip(parcels, BUILDINGS_PER_PARCEL):
        (px0, py0), _, (px1, py1) = parcel["ring"][0], parcel["ring"][1], parcel["ring"][2]
        if count == 0:
            continue
        slot = (px1 - px0 - 2 * SETBACK) / count
        usable_depth = py1 - py0 - 2 * SETBACK
        for k in range(count):
            width = slot * uni(0.55, 0.8)
            depth = usable_depth * uni(0.4, 0.75)
            x0 = px0 + SETBACK + k * slot + uni(0, slot - width)
            y0 = py0 + SETBACK + uni(0, usable_depth - depth)
            buildings.append({
                "parcel_id": parcel["parcel_id"],
                "box": (x0, y0, x0 + width, y0 + depth),
                "notch": (uni(0.3, 0.45), uni(0.3, 0.45)),
            })

    l_shaped = pick(rng, len(buildings), L_SHAPES)
    recorded = pick(rng, len(buildings), RECORDED_AREAS)
    for i, b in enumerate(buildings):
        x0, y0, x1, y1 = (r2(v) for v in b.pop("box"))
        fw, fd = b.pop("notch")
        if i in l_shaped:
            nx, ny = r2(x1 - (x1 - x0) * fw), r2(y1 - (y1 - y0) * fd)
            ring = [[x0, y0], [x1, y0], [x1, ny], [nx, ny], [nx, y1], [x0, y1], [x0, y0]]
        else:
            ring = rect(x0, y0, x1, y1)
        b["bldg_id"] = f"B{i + 1:02d}"
        b["ring"] = ring
        b["area"] = r2(shoelace(ring))
        b["src_area_m2"] = round(b["area"], 1) if i in recorded else None
    return parcels, buildings


# --- writers ------------------------------------------------------------------------


def feature_collection(name: str, crs: str | None, features: list[dict]) -> str:
    lines = ["{", '"type": "FeatureCollection",', f'"name": "{name}",']
    if crs is not None:
        # GDAL writes EPSG:4326 layers to GeoJSON as OGC CRS84; samples mimic that.
        name = "urn:ogc:def:crs:OGC:1.3:CRS84" if crs == "OGC:CRS84" else URN.format(crs.split(":")[1])
        lines.append(f'"crs": {{ "type": "name", "properties": {{ "name": "{name}" }} }},')
    lines.append('"features": [')
    lines.append(",\n".join(json.dumps(f) for f in features))
    lines += ["]", "}"]
    return "\n".join(lines) + "\n"


def polygon(ring) -> dict:
    return {"type": "Polygon", "coordinates": [ring]}


def building_features(buildings, shift=(0.0, 0.0), null_geometry=False) -> list[dict]:
    dx, dy = shift
    return [
        {
            "type": "Feature",
            "properties": {"bldg_id": b["bldg_id"], "src_area_m2": b["src_area_m2"]},
            "geometry": None if null_geometry else polygon([[r2(x + dx), r2(y + dy)] for x, y in b["ring"]]),
        }
        for b in buildings
    ]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def write_json(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2) + "\n")


# --- sample submissions -----------------------------------------------------------


def layer_entry(file, declared, used, action, evidence):
    return {
        "file": file,
        "declared_crs": declared,
        "crs_used": used,
        "action": action,
        "evidence": [{"source": s, "observation": o} for s, o in evidence],
    }


def building_rows(buildings, areas=True, parcels=True):
    return [
        {
            "bldg_id": b["bldg_id"],
            "footprint_area_m2": b["area"] if areas else None,
            "parcel_id": b["parcel_id"] if parcels else None,
        }
        for b in buildings
    ]


EVIDENCE_REASSIGN = [
    ("buildings.geojson", "Coordinates are about 498,260 to 498,360 east and 4,705,130 to 4,705,200 north, "
     "outside any longitude or latitude range, so the declared EPSG:4326 cannot be right."),
    ("provider_notes.md", "States the footprints were delivered in WGS 84 / UTM zone 18N, in metres (EPSG:32618)."),
    ("parcels.geojson", "Declared EPSG:32618 with consistent coordinates; read in EPSG:32618, every building "
     "lies inside exactly one parcel."),
    ("buildings.geojson", "For the four buildings with src_area_m2, the planar area in metres matches the "
     "recorded area to within 0.1 m2."),
]
EVIDENCE_PARCELS = [("parcels.geojson", "Coordinates fall within the valid range of the declared EPSG:32618.")]
EVIDENCE_KEEP = [
    ("buildings.geojson", "Coordinates fall within the valid range of the declared EPSG:32618."),
    ("provider_notes.md", "States WGS 84 / UTM zone 18N, which is EPSG:32618, in metres."),
    ("parcels.geojson", "With both layers in EPSG:32618, every building lies inside exactly one parcel."),
]


def samples(variant: str, buildings) -> dict[str, tuple[dict, str]]:
    """Return {name: (report, output layer text)}."""
    parcels_layer = layer_entry("parcels.geojson", "EPSG:32618", "EPSG:32618", "kept", EVIDENCE_PARCELS)
    rows = building_rows(buildings)
    same = building_features(buildings)
    out = {}

    def add(name, buildings_layer, out_crs, rows=rows, features=same, drop=None):
        report = {"layers": [buildings_layer, parcels_layer], "buildings": rows, "notes": f"sample submission: {name}"}
        if drop:
            del report[drop]
        out[name] = (report, feature_collection("buildings", out_crs, features))

    if variant == "crs-declaration-mislabeled":
        reassign = layer_entry("buildings.geojson", "EPSG:4326", "EPSG:32618", "reassigned", EVIDENCE_REASSIGN)
        add("correct", reassign, "EPSG:32618")
        # Declaration trusted; GDAL writes the unchanged layer with a CRS84 urn.
        add("trusted-declaration",
            layer_entry("buildings.geojson", "EPSG:4326", "EPSG:4326", "kept", []), "OGC:CRS84")
        # Reprojected from the wrong declaration: the transformation yields
        # infinite coordinates, which GDAL writes as null geometries.
        add("reprojected-null-geometry",
            layer_entry("buildings.geojson", "EPSG:4326", "EPSG:32618", "reprojected",
                        [("provider_notes.md", "States WGS 84 / UTM zone 18N.")]),
            "EPSG:32618",
            rows=building_rows(buildings, areas=False, parcels=False),
            features=building_features(buildings, null_geometry=True))
        # Coordinates transformed although only the label was wrong.
        add("reprojected",
            layer_entry("buildings.geojson", "EPSG:4326", "EPSG:32618", "reprojected",
                        [("provider_notes.md", "States WGS 84 / UTM zone 18N.")]),
            "EPSG:32618",
            rows=building_rows(buildings, parcels=False),
            features=building_features(buildings, shift=(12.5, 210.0)))
        # Unresolved; the layer is written without a crs member (RFC 7946 default).
        add("unresolved",
            layer_entry("buildings.geojson", "EPSG:4326", None, "unresolved", EVIDENCE_REASSIGN[:1]),
            None,
            rows=building_rows(buildings, areas=False, parcels=False))
        add("claims-without-change", reassign, "EPSG:4326")
        fabricated = json.loads(json.dumps(reassign))
        fabricated["evidence"].append({
            "source": "contractor_survey_2019.pdf",
            "observation": "Survey report confirms UTM zone 18N.",
        })
        add("fabricated-source", fabricated, "EPSG:32618")
        add("malformed", reassign, "EPSG:32618", drop="buildings")
    else:
        keep = layer_entry("buildings.geojson", "EPSG:32618", "EPSG:32618", "kept", EVIDENCE_KEEP)
        add("correct", keep, "EPSG:32618")
        add("unnecessary-reassignment",
            layer_entry("buildings.geojson", "EPSG:32618", "EPSG:26918", "reassigned",
                        [("buildings.geojson", "Assumed the NAD83 datum, as is usual for US municipal data.")]),
            "EPSG:26918")
        misread = json.loads(json.dumps(keep))
        misread["declared_crs"] = "EPSG:4326"
        add("misread-declaration", misread, "EPSG:32618")
    return out


# --- main -------------------------------------------------------------------------


def generate(out_root: Path) -> None:
    parcels, buildings = build_block()
    parcel_features = [
        {"type": "Feature", "properties": {"parcel_id": p["parcel_id"]}, "geometry": polygon(p["ring"])}
        for p in parcels
    ]
    for variant, cfg in VARIANTS.items():
        base = out_root / variant
        for sub in ["agent", "reference", "submissions"]:
            if (base / sub).exists():
                shutil.rmtree(base / sub)
        agent = base / "agent"
        write(agent / "task.md", (HERE / "task.md").read_text(encoding="utf-8"))
        write(agent / "provider_notes.md", PROVIDER_NOTES)
        write(agent / "parcels.geojson", feature_collection("parcels", TRUE_CRS, parcel_features))
        write(agent / "buildings.geojson",
              feature_collection("buildings", cfg["buildings_declared"], building_features(buildings)))
        write_json(base / "reference" / "expected.json", {
            "layers": {
                "buildings.geojson": {"declared_crs": cfg["buildings_declared"]},
                "parcels.geojson": {"declared_crs": TRUE_CRS},
            },
            "buildings": {
                b["bldg_id"]: {"footprint_area_m2": b["area"], "parcel_id": b["parcel_id"]} for b in buildings
            },
        })
        for name, (report, layer) in samples(variant, buildings).items():
            write_json(base / "submissions" / name / "report.json", report)
            write(base / "submissions" / name / "buildings.geojson", layer)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    generate(parser.parse_args().out_root)


if __name__ == "__main__":
    main()
