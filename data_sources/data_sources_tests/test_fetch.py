"""Windowed fetch into the cache, through an injected opener (no network)."""

import json
from pathlib import Path

import pytest
import rasterio

from data_sources.soilgrids.catalog import STATISTICS
from data_sources.soilgrids.fetch import FetchError, fetch, validate_bbox

PROPS = ("phh2o", "soc", "nitrogen", "clay", "sand", "silt")
DEPTHS = ("0-5cm", "5-15cm", "15-30cm")


def _run(sg, tmp_path: Path, opener) -> Path:
    return fetch(
        sg.BBOX,
        PROPS,
        DEPTHS,
        cache_dir=tmp_path / "cache",
        opener=opener,
        today=sg.RETRIEVED,
    )


def test_fetch_writes_clips_and_manifest(sg, tmp_path: Path, opener) -> None:
    out = _run(sg, tmp_path, opener)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["source"] == "SoilGrids"
    assert manifest["version"] == "2.0"
    assert manifest["retrieved_on"] == "2026-11-16"
    assert manifest["bbox_wgs84"] == list(sg.BBOX)
    assert "CC BY 4.0" in manifest["license"]
    layers = manifest["layers"]
    assert len(layers) == len(PROPS) * len(DEPTHS) * len(STATISTICS)
    first = layers[0]
    for key in (
        "property",
        "depth",
        "statistic",
        "url",
        "file",
        "crs",
        "resolution_m",
        "mapped_unit",
        "nodata",
        "shape",
    ):
        assert key in first
    assert all(
        layer["url"].startswith("https://files.isric.org/soilgrids/latest/data/")
        for layer in layers
    )
    assert {layer["statistic"] for layer in layers} == {"mean", "Q0.05", "Q0.95", "uncertainty"}


def test_clip_is_a_crs_preserving_sub_window(sg, tmp_path: Path, opener) -> None:
    out = _run(sg, tmp_path, opener)
    with rasterio.open(out / "nitrogen_0-5cm_mean.tif") as ds:
        assert "igh" in ds.crs.to_proj4()
        assert ds.res == (250.0, 250.0)
        assert 0 < ds.width < sg.SIZE and 0 < ds.height < sg.SIZE
        data = ds.read(1)
        assert ds.nodata == sg.NODATA
        assert (data == sg.MAPPED[("nitrogen", "mean")]).all()


def test_clip_covers_the_bbox(sg, tmp_path: Path, opener) -> None:
    from rasterio.warp import transform_bounds

    out = _run(sg, tmp_path, opener)
    with rasterio.open(out / "soc_5-15cm_mean.tif") as ds:
        w, s, e, n = transform_bounds("EPSG:4326", ds.crs, *sg.BBOX, densify_pts=21)
        assert ds.bounds.left <= w and ds.bounds.right >= e
        assert ds.bounds.bottom <= s and ds.bounds.top >= n


def test_fetch_is_idempotent(sg, tmp_path: Path, opener) -> None:
    out1 = _run(sg, tmp_path, opener)
    m1 = (out1 / "manifest.json").read_text()
    out2 = _run(sg, tmp_path, opener)
    assert out1 == out2
    assert (out2 / "manifest.json").read_text() == m1


def test_failed_layer_leaves_no_manifest(sg, tmp_path: Path, opener, fake_remote) -> None:
    missing = next(u for u in fake_remote if u.endswith("silt_15-30cm_uncertainty.vrt"))
    del fake_remote[missing]
    with pytest.raises(FetchError, match="silt_15-30cm_uncertainty"):
        _run(sg, tmp_path, opener)
    assert not list((tmp_path / "cache").rglob("manifest.json"))


def test_bbox_outside_layer_is_an_error(sg, tmp_path: Path, opener) -> None:
    with pytest.raises(FetchError, match="outside"):
        fetch(
            (-100.0, 50.0, -99.9, 50.1),
            ("soc",),
            ("0-5cm",),
            cache_dir=tmp_path / "cache",
            opener=opener,
            today=sg.RETRIEVED,
        )


@pytest.mark.parametrize(
    "bbox",
    [
        (-80.2, 43.5, -80.3, 43.6),  # min > max
        (-80.3, 43.6, -80.2, 43.5),
        (-181.0, 43.5, -80.2, 43.6),
        (-80.3, 43.5, -80.2, 91.0),
        (-80.3, 40.0, -78.0, 43.0),  # larger than the 1 degree cap
    ],
)
def test_invalid_bbox_rejected(bbox: tuple[float, float, float, float]) -> None:
    with pytest.raises(ValueError):
        validate_bbox(bbox)


def test_bbox_crossing_homolosine_interruption_rejected() -> None:
    # Northern-hemisphere lobes of the Interrupted Goode Homolosine split at 40 deg W.
    with pytest.raises(ValueError, match="interruption"):
        validate_bbox((-40.2, 50.0, -39.8, 50.2))
