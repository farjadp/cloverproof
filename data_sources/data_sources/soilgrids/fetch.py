"""Windowed read of SoilGrids VRT/COG layers into a local GeoTIFF cache.

Network access happens only through `opener` (default: GDAL /vsicurl/ on files.isric.org).
Tests inject a local opener; nothing here talks to the SoilGrids REST API.
"""

import hashlib
import json
import logging
import math
import os
import shutil
import tempfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from datetime import date
from pathlib import Path
from typing import Final

import rasterio
from rasterio.errors import RasterioError
from rasterio.io import DatasetReader
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds

from data_sources.soilgrids.catalog import (
    ATTRIBUTION,
    CONVERSIONS,
    DEFAULT_BASE_URL,
    LICENSE,
    SOILGRIDS_VERSION,
    STATISTICS,
    UNCERTAINTY_FACTOR,
    layer_name,
    layer_url,
    parse_depths,
    parse_properties,
)

log = logging.getLogger("data_sources.soilgrids")

Opener = Callable[[str], AbstractContextManager[DatasetReader]]
BBox = tuple[float, float, float, float]

MAX_BBOX_DEG: Final = 1.0  # a farm window, not a region; keeps a fetch to a few MB
# Interrupted Goode Homolosine lobe edges (degrees longitude).
_IGH_NORTH_CUTS: Final = (-40.0,)
_IGH_SOUTH_CUTS: Final = (-100.0, -20.0, 80.0)

_GDAL_HTTP_ENV: Final = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".vrt,.tif,.ovr",
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_RETRY_DELAY": "2",
    "GDAL_HTTP_TIMEOUT": "60",
}


class FetchError(RuntimeError):
    pass


@contextmanager
def default_opener(url: str) -> Iterator[DatasetReader]:  # pragma: no cover - network
    """Open a remote VRT through GDAL /vsicurl/ (HTTP range requests; reads only the window)."""
    with rasterio.Env(**_GDAL_HTTP_ENV), rasterio.open(f"/vsicurl/{url}") as ds:
        yield ds


def validate_bbox(bbox: Sequence[float]) -> BBox:
    if len(bbox) != 4:
        raise ValueError("bbox must be minlon,minlat,maxlon,maxlat")
    minlon, minlat, maxlon, maxlat = (float(v) for v in bbox)
    if not all(math.isfinite(v) for v in (minlon, minlat, maxlon, maxlat)):
        raise ValueError("bbox values must be finite")
    if not (-180 <= minlon < maxlon <= 180 and -90 <= minlat < maxlat <= 90):
        raise ValueError("bbox must satisfy -180<=minlon<maxlon<=180 and -90<=minlat<maxlat<=90")
    if maxlon - minlon > MAX_BBOX_DEG or maxlat - minlat > MAX_BBOX_DEG:
        raise ValueError(f"bbox larger than {MAX_BBOX_DEG} degree per side; split it")
    cuts = (_IGH_NORTH_CUTS if maxlat > 0 else ()) + (_IGH_SOUTH_CUTS if minlat < 0 else ())
    for cut in cuts:
        if minlon < cut < maxlon:
            raise ValueError(
                f"bbox crosses the Homolosine interruption at {cut} deg; split it at that meridian"
            )
    return (minlon, minlat, maxlon, maxlat)


def bbox_slug(bbox: BBox) -> str:
    """Stable directory name for a bbox, so re-running the same fetch overwrites in place."""
    canon = ",".join(f"{v:.6f}" for v in bbox)
    return "bbox_" + hashlib.sha256(canon.encode()).hexdigest()[:12]


def _window_for(ds: DatasetReader, bbox: BBox) -> Window:
    # Project the lon/lat bbox into the raster CRS (Homolosine) with edge densification,
    # then snap the window outwards to whole pixels so the clip fully covers the bbox.
    west, south, east, north = transform_bounds("EPSG:4326", ds.crs, *bbox, densify_pts=21)
    if not all(math.isfinite(v) for v in (west, south, east, north)):
        raise FetchError("bbox does not project into the layer CRS")
    win = from_bounds(west, south, east, north, transform=ds.transform)
    col0, row0 = math.floor(win.col_off), math.floor(win.row_off)
    col1 = math.ceil(win.col_off + win.width)
    row1 = math.ceil(win.row_off + win.height)
    col0, row0 = max(col0, 0), max(row0, 0)
    col1, row1 = min(col1, ds.width), min(row1, ds.height)
    if col1 <= col0 or row1 <= row0:
        raise FetchError("bbox is outside the layer extent")
    return Window(col0, row0, col1 - col0, row1 - row0)


def _clip(ds: DatasetReader, bbox: BBox, dest: Path) -> dict[str, object]:
    win = _window_for(ds, bbox)
    data = ds.read(1, window=win)
    profile = {
        "driver": "GTiff",
        "height": int(win.height),
        "width": int(win.width),
        "count": 1,
        "dtype": data.dtype.name,
        "crs": ds.crs,
        "transform": ds.window_transform(win),
        "nodata": ds.nodata,
        "compress": "deflate",
    }
    with rasterio.open(dest, "w", **profile) as out:
        out.write(data, 1)
    return {
        "crs": ds.crs.to_string(),
        "resolution_m": [abs(ds.res[0]), abs(ds.res[1])],
        "nodata": ds.nodata,
        "shape": [int(win.height), int(win.width)],
        "window": [int(win.col_off), int(win.row_off), int(win.width), int(win.height)],
    }


def planned_layers(
    props: Sequence[str], depths: Sequence[str], *, base_url: str = DEFAULT_BASE_URL
) -> list[tuple[str, str, str, str]]:
    return [
        (p, d, s, layer_url(p, d, s, base_url=base_url))
        for p in props
        for d in depths
        for s in STATISTICS
    ]


def fetch(
    bbox: Sequence[float],
    properties: Sequence[str] | str,
    depths: Sequence[str] | str,
    *,
    cache_dir: Path,
    opener: Opener = default_opener,
    today: date | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> Path:
    """Clip every (property, depth, statistic) layer to `bbox`; return the bbox cache dir.

    Idempotent: the same bbox always maps to the same directory, which is replaced
    atomically only after every layer succeeded (no half-written cache, no stale manifest).
    """
    box = validate_bbox(bbox)
    props = parse_properties(properties)
    deps = parse_depths(depths)
    retrieved = today or date.today()
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    final = cache_dir / bbox_slug(box)
    staging = Path(tempfile.mkdtemp(prefix=".staging_", dir=cache_dir))
    layers: list[dict[str, object]] = []
    try:
        for prop, depth, stat, url in planned_layers(props, deps, base_url=base_url):
            name = layer_name(prop, depth, stat)
            conv = UNCERTAINTY_FACTOR if stat == "uncertainty" else CONVERSIONS[prop]
            try:
                with opener(url) as ds:
                    info = _clip(ds, box, staging / f"{name}.tif")
            except FetchError as exc:
                raise FetchError(f"{name}: {exc}") from exc
            except (RasterioError, OSError) as exc:
                raise FetchError(f"{name}: cannot read {url}: {exc}") from exc
            layers.append(
                {
                    "property": prop,
                    "depth": depth,
                    "statistic": stat,
                    "url": url,
                    "file": f"{name}.tif",
                    "mapped_unit": conv.mapped_unit,
                    "conversion_source": conv.source_url,
                    **info,
                }
            )
            log.info("soilgrids.layer_clipped", extra={"layer": name, "shape": info["shape"]})
        manifest = {
            "source": "SoilGrids",
            "version": SOILGRIDS_VERSION,
            "base_url": base_url,
            "license": LICENSE,
            "attribution": ATTRIBUTION,
            "retrieved_on": retrieved.isoformat(),
            "bbox_wgs84": list(box),
            "crs": layers[0]["crs"] if layers else None,
            "layers": layers,
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        if final.exists():
            shutil.rmtree(final)
        os.replace(staging, final)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    log.info("soilgrids.fetch_done", extra={"dir": str(final), "layers": len(layers)})
    return final
