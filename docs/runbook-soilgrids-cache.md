# Runbook: SoilGrids Ontario cache

Operator step. The app never downloads SoilGrids: it reads the local cache only (ADR 0006). The fetch reads the public file tree `https://files.isric.org/soilgrids/latest/data/` and never the REST API. The cache directory is gitignored; never commit rasters.

## What the command fetches

| Item | Value |
|---|---|
| Bbox (WGS84, minlon,minlat,maxlon,maxlat) | `-95.2,41.6,-74.3,56.9`: Ontario's extreme points rounded outwards to 0.1 degree. It also covers parts of neighbouring provinces and the US |
| Properties | `phh2o,soc,nitrogen,clay,sand,silt` (no P/K exists or is accepted) |
| Depths | `0-5cm,5-15cm,15-30cm` |
| Statistics | `mean,Q0.05,Q0.95,uncertainty` |
| Layers | 6 x 3 x 4 = 72 |
| Expected size (estimate) | about 7283 x 6434 px per layer at 250 m; about 94 MB per layer and 6.7 GB in total uncompressed. Files are deflate-compressed, so disk use is lower; the ratio has not been measured |

Download time has not been measured. Plan for a long run and at least 7 GB free disk, plus about 100 MB of memory per layer.

## Steps

1. Check the plan. This opens nothing on the network:

   ```sh
   uv run python -m data_sources.soilgrids fetch --region ontario --dry-run
   ```

2. Run the fetch from a machine with network access:

   ```sh
   uv run python -m data_sources.soilgrids fetch --region ontario \
     --props phh2o,soc,nitrogen,clay,sand,silt --depths 0-5cm,5-15cm,15-30cm
   ```

   The default target is `data/cache/soilgrids/`; `--cache-dir` or `CLOVERPROOF_SOILGRIDS_CACHE` changes it. The command prints the path of `manifest.json` when it finishes.

3. Check one known point offline:

   ```sh
   uv run python -c "from data_sources.soilgrids import lookup_estimate; print(lookup_estimate(-80.25, 43.55, properties=['nitrogen'], depths=['0-5cm']).model_dump_json(indent=2))"
   ```

## Behaviour to know

- All or nothing: the bbox directory is replaced only after all 72 layers succeed. A failed run leaves the previous cache untouched, but it does not resume; rerun it from the start.
- Re-running replaces the directory and sets a new retrieval date. Values can change, because `latest` is a rolling path. Recommendations keep the retrieval date they used.
- The version recorded is `2.0`, set in code. The file tree does not pin it, so check ISRIC's release notes before a re-fetch.
- A point outside the cached bbox, or on a masked pixel, gives `no_estimate`. A missing or damaged cache raises an error.

## Attribution

Wherever a value is shown, use `SoilEstimate.attribution` (`SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0`) and `SoilEstimate.citation`.
