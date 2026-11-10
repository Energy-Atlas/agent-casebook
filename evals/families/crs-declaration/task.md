# Task: building footprint areas and parcel join

You are preparing geometry inputs for an urban building energy model.

## Inputs

All inputs are in this directory. Do not modify them.

- `buildings.geojson`: building footprints, with properties `bldg_id` and
  `src_area_m2`.
- `parcels.geojson`: parcels, with property `parcel_id`.
- `provider_notes.md`: the footprint provider's delivery notes.

## What to do

1. Establish the coordinate reference system (CRS) of each layer before you
   rely on its coordinates.
2. Compute the footprint area of each building in square metres from its
   geometry.
3. Find the parcel that contains each building.

If something cannot be determined from the inputs, say so in the report rather
than guessing.

You may use any locally installed tools. Network access is not needed.

## What to return

Create a directory `output/` here and write two files into it.

### `output/buildings.geojson`

The building layer as you would hand it on to the next modeling step: every
building with its `bldg_id`, and the CRS you used declared in the file. If
you could not determine the CRS, write the layer with the declaration as you
received it.

### `output/report.json`

```json
{
  "layers": [
    {
      "file": "buildings.geojson",
      "declared_crs": "EPSG:<code> as declared in the input file, or null if none",
      "crs_used": "EPSG:<code> you used for this layer, or null if unresolved",
      "action": "kept | reassigned | reprojected | unresolved",
      "evidence": [
        {"source": "<input file name>", "observation": "<what you observed>"}
      ]
    },
    {
      "file": "parcels.geojson",
      "declared_crs": "...",
      "crs_used": "...",
      "action": "...",
      "evidence": []
    }
  ],
  "buildings": [
    {"bldg_id": "B01", "footprint_area_m2": 0.0, "parcel_id": "P01"}
  ],
  "notes": "anything else the next person should know"
}
```

- Give one entry in `layers` for each of the two layers, and one entry in
  `buildings` for every building in `buildings.geojson`.
- Write CRSs as `EPSG:<code>`.
- `action` means:
  - `kept`: the declared CRS is used as is;
  - `reassigned`: the declaration is replaced by another CRS without
    transforming the coordinates;
  - `reprojected`: the coordinates are transformed from the declared CRS into
    another CRS;
  - `unresolved`: the CRS could not be determined; `crs_used` is null.
- `evidence` lists the inputs and observations your CRS decision for that
  layer rests on. Name only files from this directory as sources.
- Use null for any value you could not determine.
