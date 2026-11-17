"""Point lookup against the local SoilGrids cache. Never touches the network."""

import json
import os
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Final

import rasterio
from rasterio.warp import transform

from data_sources.soilgrids.catalog import (
    CONVERSIONS,
    UNCERTAINTY_FACTOR,
    depth_bounds_cm,
    parse_depths,
    parse_properties,
)
from data_sources.soilgrids.models import EstimateValue, SoilEstimate

CACHE_ENV: Final = "CLOVERPROOF_SOILGRIDS_CACHE"
DEFAULT_CACHE_DIR: Final = Path("data/cache/soilgrids")


class CacheMissingError(LookupError):
    """The cache has no data for this point/property/depth. Run the fetch CLI first."""


class NoDataError(LookupError):
    """SoilGrids has no prediction at this pixel (masked: water, urban, ice, bare)."""


def default_cache_dir() -> Path:
    return Path(os.environ.get(CACHE_ENV) or DEFAULT_CACHE_DIR)


def _contains(bbox: Sequence[float], lon: float, lat: float) -> bool:
    minlon, minlat, maxlon, maxlat = bbox
    return minlon <= lon <= maxlon and minlat <= lat <= maxlat


def _find_manifest(cache_dir: Path, lon: float, lat: float) -> tuple[Path, dict]:
    if not cache_dir.is_dir():
        raise CacheMissingError(
            f"SoilGrids cache {cache_dir} does not exist; run "
            "`uv run python -m data_sources.soilgrids fetch --bbox ...` first"
        )
    hits: list[tuple[str, str, Path, dict]] = []
    for mf in sorted(cache_dir.glob("*/manifest.json")):
        try:
            manifest = json.loads(mf.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise CacheMissingError(f"unreadable manifest {mf}: {exc}") from exc
        if _contains(manifest["bbox_wgs84"], lon, lat):
            hits.append((manifest["retrieved_on"], mf.parent.name, mf.parent, manifest))
    if not hits:
        raise CacheMissingError(f"no cached SoilGrids bbox contains ({lon}, {lat}) in {cache_dir}")
    _, _, folder, manifest = max(hits, key=lambda h: (h[0], h[1]))
    return folder, manifest


def _sample(path: Path, lon: float, lat: float) -> int | None:
    """Raw mapped value at the pixel containing (lon, lat); None if nodata."""
    with rasterio.open(path) as ds:
        xs, ys = transform("EPSG:4326", ds.crs, [lon], [lat])
        row, col = ds.index(xs[0], ys[0])
        if not (0 <= row < ds.height and 0 <= col < ds.width):
            raise CacheMissingError(f"point ({lon}, {lat}) falls outside {path.name}")
        value = ds.read(1, window=((row, row + 1), (col, col + 1)))[0, 0]
        if ds.nodata is not None and value == ds.nodata:
            return None
        return int(value)


def estimate_at(
    lon: float,
    lat: float,
    *,
    cache_dir: Path | None = None,
    properties: Sequence[str] | None = None,
    depths: Sequence[str] | None = None,
) -> SoilEstimate:
    """SoilGrids estimate at a point from the offline cache.

    `properties` / `depths` default to everything cached for the bbox. Explicitly
    requested layers that are not cached raise CacheMissingError; a masked pixel
    in a `mean` layer raises NoDataError. No silent defaults.
    """
    folder, manifest = _find_manifest(Path(cache_dir or default_cache_dir()), lon, lat)
    layers = {(lyr["property"], lyr["depth"], lyr["statistic"]): lyr for lyr in manifest["layers"]}
    cached_pd = list(dict.fromkeys((p, d) for p, d, s in layers if s == "mean"))

    want_props = parse_properties(tuple(properties)) if properties is not None else None
    want_depths = parse_depths(tuple(depths)) if depths is not None else None
    if want_props is None and want_depths is None:
        pairs = cached_pd
    else:
        props = want_props or tuple(dict.fromkeys(p for p, _ in cached_pd))
        deps = want_depths or tuple(dict.fromkeys(d for _, d in cached_pd))
        pairs = [(p, d) for p in props for d in deps]
        missing = [f"{p}@{d}" for p, d in pairs if (p, d) not in cached_pd]
        if missing:
            raise CacheMissingError(f"not in cache {folder.name}: {', '.join(missing)}")
    retrieved = date.fromisoformat(manifest["retrieved_on"])

    values: list[EstimateValue] = []
    for prop, depth in pairs:
        conv = CONVERSIONS[prop]
        mean_layer = layers[(prop, depth, "mean")]
        mapped = _sample(folder / mean_layer["file"], lon, lat)
        if mapped is None:
            raise NoDataError(f"SoilGrids has no {prop} {depth} prediction at ({lon}, {lat})")

        def extra(stat: str, prop: str = prop, depth: str = depth) -> int | None:
            lyr = layers.get((prop, depth, stat))
            return None if lyr is None else _sample(folder / lyr["file"], lon, lat)

        q05, q95, unc = extra("Q0.05"), extra("Q0.95"), extra("uncertainty")
        top, bottom = depth_bounds_cm(depth)
        values.append(
            EstimateValue(
                property=prop,
                depth=depth,
                depth_top_cm=top,
                depth_bottom_cm=bottom,
                statistic="mean",
                value=conv.to_canonical(mapped),
                unit=conv.canonical_unit,
                mapped_value=mapped,
                mapped_unit=conv.mapped_unit,
                conversion_factor_source=conv.source_url,
                q05=None if q05 is None else conv.to_canonical(q05),
                q95=None if q95 is None else conv.to_canonical(q95),
                uncertainty_ratio=None if unc is None else UNCERTAINTY_FACTOR.to_canonical(unc),
                url=mean_layer["url"],
                retrieved_on=retrieved,
                resolution_m=float(mean_layer["resolution_m"][0]),
            )
        )
    return SoilEstimate(lon=lon, lat=lat, values=tuple(values))
