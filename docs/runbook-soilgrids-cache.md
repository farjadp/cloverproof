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

## Load estimates into the database

`soil-estimate-load` stores the cached values at one field's point, for one season, in `soil_estimate`. It runs from an operator checkout (`uv sync`), never in the app: the app image has no `data_sources`, and no web request reaches this code. It reads the cache only and opens nothing on the network.

Before you start:

- Migration 0033 is applied to the target database.
- The cache is built (steps above). It stays on the operator's machine; only the values go to the database.
- The field has a location, set on its page in the app.
- `--as` names an enabled human member of the field's organisation, any role. The rows are written under that person's RLS context and record them as `created_by`.

### Hosted environments: synthetic farmers only

Staging and production hold synthetic or de-identified data only (ADR 0009). The command refuses a field whose farmer has `record_kind = 'real'` when `ENV` is `staging` or `production`, and also for any database that is not on this machine, whatever `ENV` says.

`record_kind` defaults to `real`, and the app cannot change it, so **a test farmer created in the app counts as real until it is marked**. Mark it before its first plan: the value is frozen once the farmer has a recommendation (then create a new farmer instead). You need the `cp_admin_login` URL and a human superadmin who is a member of the farmer's organisation:

```sql
-- psql, logged in as cp_admin_login
begin;
select set_config('app.user_id', '<superadmin user id>', true),
       set_config('app.org_id', '<organisation id>', true);
update farmer set record_kind = 'demo' where organisation_id = '<organisation id>' and id = '<farmer id>';
commit;
```

Only do this for a farmer that really is synthetic or de-identified. It is the check that keeps real farm data out of hosted environments.

### Run it

Log in as `cp_app_login`: the step needs no more than that. A superuser or `BYPASSRLS` login is refused on a hosted database.

```sh
ENV=staging DATABASE_URL='<cp_app_login URL>' uv run python -m cloverproof_app.cli soil-estimate-load \
  --field <field id> --season <season id> \
  --cache-dir data/cache/soilgrids --as <operator email>
```

Locally, leave `ENV` unset and use the local `DATABASE_URL`.

| Output | Meaning |
|---|---|
| `stored N estimate value(s) ...` | All values were stored, in one transaction |
| `no estimate stored: ...` | The point is outside the cache, or on a masked pixel. Nothing was stored; exit code 0 |
| `error: this field has no location ...` | Add the location first |
| `error: this retrieval is already stored ...` | Same cache, same location. Nothing was changed |
| `error: refused: this field belongs to a real farmer ...` | See above |
| `error: the SoilGrids cache could not be read ...` | Check `--cache-dir`, or rebuild the cache |

The command never prints the field's coordinates. Do not paste a real field's point into the check in step 3 above: its output contains the coordinates.

### When a field moves

Changing or clearing a field's location raises `field.location_revision`. Its stored estimates stop being current at once; they stay in the table (it is immutable). Run the command again to store values for the new point: the same cache can be used. A point moved back to an earlier position also needs a new load.

## Attribution

Wherever a value is shown, use `SoilEstimate.attribution` (`SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0`) and `SoilEstimate.citation`.
