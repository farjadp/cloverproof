# ADR 0006 — SoilGrids v2.0 as an offline, N-only estimate cache

- Status: Accepted (2026-11-16)
- Decider: Farjad Iranmehr
- Related: CLAUDE.md hard rules 2, 3, 5, 7, 9; ADR 0001 (repo and stack); `data_sources/` workspace member

## Context
Farms without a soil test still need context (pH, organic carbon, total N, texture) for the N recommendation. ISRIC's SoilGrids 2.0 gives modelled values at 250 m for six standard depths with 5 %/95 % quantiles and an uncertainty layer, under CC BY 4.0.

- The SoilGrids REST API (`/properties/query`) is labelled beta, has been paused or rate-limited before, and ISRIC itself recommends WebDAV or web services for anything beyond one-off queries. A per-request call is also slow and makes a plan depend on a third-party service at review time.
- Rule 5 needs the input snapshot to be reproducible. "Latest" SoilGrids is a rolling release; a value fetched live today can differ next season. A clip stored with its retrieval date and source URL is reproducible; a live call is not.
- CC BY 4.0 requires attribution on anything we derive from it (proof PDF, UI).
- The engine is pure (no I/O, CLAUDE.md stack). Fetching cannot live there.
- Rule 3: without a lab test we recommend N only. SoilGrids has no P or K layers, but nothing must make it possible to feed an estimate into a P/K path later.

## Decision
- New uv workspace member `data_sources/` (package `cloverproof-data-sources`, import `data_sources`), separate from `engine/`. Dependency: `rasterio` (GDAL). No paid service.
- `python -m data_sources.soilgrids fetch --bbox minlon,minlat,maxlon,maxlat --props ... --depths ...` reads the public file tree `https://files.isric.org/soilgrids/latest/data/<prop>/<prop>_<depth>_<stat>.vrt` through GDAL `/vsicurl/` with a windowed read. The lon/lat bbox is projected into the layers' Interrupted Goode Homolosine CRS (ESRI:54052) with edge densification and snapped outwards to whole pixels; clips stay in native Homolosine (no resampling, values unchanged). A bbox crossing a Homolosine interruption or wider than 1 degree is refused. The REST API is never called; a guard rejects its host and path.
- Per (property, depth) we clip `mean`, `Q0.05`, `Q0.95` and `uncertainty` into `data/cache/soilgrids/bbox_<hash>/` (gitignored) with a `manifest.json`: source, version, base URL, license and attribution, retrieval date, bbox, CRS, and per layer URL, file, statistic, mapped unit, resolution, nodata, window. Same bbox, same directory; the directory is replaced atomically only after every layer succeeded.
- `estimate_at(lon, lat, *, cache_dir=...)` reads the cache only. It returns `SoilEstimate` with values converted to canonical units (pH; soc and total N in mg/kg; clay/sand/silt in %), the raw mapped integer, Q0.05/Q0.95, the uncertainty ratio, depth, statistic, resolution, URL and retrieval date. Missing cache, missing layer or a masked pixel raise; there is no default value.
- Unit factors are ISRIC's own table (https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html), cited next to each factor in `catalog.py`. g/kg to mg/kg is an SI prefix step, not an agronomic constant.

## How N-only is enforced
1. Property allowlist is exactly `phh2o, soc, nitrogen, clay, sand, silt`; any P/K-like name (`p`, `k`, `phosph*`, `potass*`, `P2O5`, `K2O`, Olsen/Bray/Mehlich) is rejected with an error naming rule 3, in the CLI, in `fetch` and in `estimate_at`.
2. `SoilEstimate` / `EstimateValue` are pydantic models with `extra="forbid"` and `frozen=True`; `property` is a Literal of the six names. There is no field that can hold P or K.
3. `source` is `Literal["estimate"]` (never `lab`), `provider` is `SoilGrids`, `confidence` is `Literal["low"]`.
4. Tests in `data_sources/tests/` prove each point, using tiny Homolosine rasters generated in `tmp_path`; no network.

## Consequences
- A plan for a farm without a soil test needs a `fetch` for its window before review (one-off, small). Cached values are stable until we re-fetch; the retrieval date travels with every value.
- Attribution must appear wherever a SoilGrids-derived value is shown (proof PDF, UI): use `SoilEstimate.attribution`.
- `rasterio` brings GDAL wheels (large, but no system install); only the `data_sources` member uses it.
- Mapping `SoilEstimate` to the engine's `SoilTest(source="estimate")` (depth, form, units) is a separate adapter step, not part of this ADR.
- Left to `cp-engine`: an engine-side golden test asserting that a soil test with `source = estimate` never yields a P or K rate (and caps confidence per rule 3). Not written here.
- Not verified live: files.isric.org did not answer from our network on 2026-11-16; the file layout was confirmed from archived directory listings (phh2o, soc, nitrogen, clay). The first real fetch should be checked by hand.
