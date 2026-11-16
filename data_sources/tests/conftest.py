"""Fixtures: tiny CRS-correct rasters generated in tmp_path. No network, no committed binaries."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.io import DatasetReader
from rasterio.transform import from_origin
from rasterio.warp import transform as warp_transform

from data_sources.soilgrids.catalog import HOMOLOSINE_PROJ4, layer_url

# A point in southern Ontario (rural, not a farm we work with) and a small bbox around it.
POINT_LON, POINT_LAT = -80.25, 43.55
BBOX = (-80.27, 43.53, -80.23, 43.57)
RETRIEVED = date(2026, 11, 16)
NODATA = -32768
PIXEL_M = 250.0
SIZE = 60  # 60 x 250 m = 15 km square, larger than BBOX so the clip is a real sub-window

# Mapped (integer) values written to every pixel of each fixture layer.
MAPPED = {
    ("phh2o", "mean"): 65,
    ("phh2o", "Q0.05"): 55,
    ("phh2o", "Q0.95"): 75,
    ("phh2o", "uncertainty"): 3,
    ("soc", "mean"): 250,
    ("soc", "Q0.05"): 100,
    ("soc", "Q0.95"): 600,
    ("soc", "uncertainty"): 20,
    ("nitrogen", "mean"): 150,
    ("nitrogen", "Q0.05"): 80,
    ("nitrogen", "Q0.95"): 300,
    ("nitrogen", "uncertainty"): 15,
    ("clay", "mean"): 300,
    ("clay", "Q0.05"): 150,
    ("clay", "Q0.95"): 450,
    ("clay", "uncertainty"): 10,
    ("sand", "mean"): 350,
    ("sand", "Q0.05"): 200,
    ("sand", "Q0.95"): 500,
    ("sand", "uncertainty"): 9,
    ("silt", "mean"): 350,
    ("silt", "Q0.05"): 250,
    ("silt", "Q0.95"): 450,
    ("silt", "uncertainty"): 6,
}


def write_fixture_raster(
    path: Path, value: int, *, nodata_at: tuple[int, int] | None = None
) -> None:
    """int16 Homolosine raster centred on the test point, like a SoilGrids tile."""
    crs = CRS.from_proj4(HOMOLOSINE_PROJ4)
    xs, ys = warp_transform("EPSG:4326", crs, [POINT_LON], [POINT_LAT])
    west = xs[0] - SIZE / 2 * PIXEL_M
    north = ys[0] + SIZE / 2 * PIXEL_M
    data = np.full((SIZE, SIZE), value, dtype="int16")
    if nodata_at is not None:
        data[nodata_at] = NODATA
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=SIZE,
        width=SIZE,
        count=1,
        dtype="int16",
        crs=crs,
        transform=from_origin(west, north, PIXEL_M, PIXEL_M),
        nodata=NODATA,
    ) as dst:
        dst.write(data, 1)


@pytest.fixture
def fake_remote(tmp_path: Path) -> dict[str, Path]:
    """URL -> local fixture file for every allowed property, the three test depths and stats."""
    remote = tmp_path / "remote"
    remote.mkdir()
    mapping: dict[str, Path] = {}
    for (prop, stat), value in MAPPED.items():
        for depth in ("0-5cm", "5-15cm", "15-30cm"):
            p = remote / f"{prop}_{depth}_{stat}.tif"
            write_fixture_raster(p, value)
            mapping[layer_url(prop, depth, stat)] = p
    return mapping


@pytest.fixture
def opener(
    fake_remote: dict[str, Path],
) -> Callable[[str], AbstractContextManager[DatasetReader]]:
    opened: list[str] = []

    def _open(url: str) -> AbstractContextManager[DatasetReader]:
        opened.append(url)
        if url not in fake_remote:
            raise rasterio.errors.RasterioIOError(f"fixture has no layer for {url}")
        return rasterio.open(fake_remote[url])

    _open.opened = opened  # type: ignore[attr-defined]
    return _open


@pytest.fixture
def sg() -> SimpleNamespace:
    """Shared constants (tests cannot import conftest under --import-mode=importlib)."""
    return SimpleNamespace(
        POINT_LON=POINT_LON,
        POINT_LAT=POINT_LAT,
        BBOX=BBOX,
        RETRIEVED=RETRIEVED,
        NODATA=NODATA,
        SIZE=SIZE,
        MAPPED=MAPPED,
    )
