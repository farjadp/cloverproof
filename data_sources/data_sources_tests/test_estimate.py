"""estimate_at reads the cache only."""

from pathlib import Path

import pytest
import rasterio

from data_sources.soilgrids.estimate import CacheMissingError, NoDataError, estimate_at
from data_sources.soilgrids.fetch import fetch

PROPS = ("phh2o", "soc", "nitrogen", "clay", "sand", "silt")
DEPTHS = ("0-5cm", "5-15cm", "15-30cm")


@pytest.fixture
def cache(sg, tmp_path: Path, opener) -> Path:
    cache_dir = tmp_path / "cache"
    fetch(sg.BBOX, PROPS, DEPTHS, cache_dir=cache_dir, opener=opener, today=sg.RETRIEVED)
    return cache_dir


def test_estimate_returns_converted_values_with_metadata(sg, cache: Path) -> None:
    est = estimate_at(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache)
    assert est.source == "estimate"
    assert est.provider == "SoilGrids"
    assert est.confidence == "low"
    assert est.version == "2.0"
    assert len(est.values) == len(PROPS) * len(DEPTHS)
    by_key = {(v.property, v.depth): v for v in est.values}

    n = by_key[("nitrogen", "0-5cm")]
    assert n.value == pytest.approx(1500.0)
    assert n.unit == "mg/kg"
    assert n.mapped_value == 150
    assert n.mapped_unit == "cg/kg"
    assert n.q05 == pytest.approx(800.0)
    assert n.q95 == pytest.approx(3000.0)
    assert n.uncertainty_ratio == pytest.approx(1.5)
    assert n.statistic == "mean"
    assert n.retrieved_on == sg.RETRIEVED
    assert n.resolution_m == pytest.approx(250.0)
    assert (n.depth_top_cm, n.depth_bottom_cm) == (0, 5)
    assert n.url.endswith("nitrogen/nitrogen_0-5cm_mean.vrt")

    assert by_key[("phh2o", "15-30cm")].value == pytest.approx(6.5)
    assert by_key[("soc", "5-15cm")].value == pytest.approx(25_000.0)
    assert by_key[("clay", "0-5cm")].value == pytest.approx(30.0)
    assert by_key[("clay", "0-5cm")].unit == "%"


def test_estimate_filters_properties_and_depths(sg, cache: Path) -> None:
    est = estimate_at(
        sg.POINT_LON, sg.POINT_LAT, cache_dir=cache, properties=("nitrogen",), depths=("0-5cm",)
    )
    assert [(v.property, v.depth) for v in est.values] == [("nitrogen", "0-5cm")]


def test_missing_cache_dir_is_an_explicit_error(sg, tmp_path: Path) -> None:
    with pytest.raises(CacheMissingError):
        estimate_at(sg.POINT_LON, sg.POINT_LAT, cache_dir=tmp_path / "nope")


def test_point_outside_cached_bboxes_is_an_explicit_error(cache: Path) -> None:
    with pytest.raises(CacheMissingError, match="no cached"):
        estimate_at(-100.0, 50.0, cache_dir=cache)


def test_missing_requested_layer_is_an_explicit_error(sg, tmp_path: Path, opener) -> None:
    cache_dir = tmp_path / "cache"
    fetch(sg.BBOX, ("soc",), ("0-5cm",), cache_dir=cache_dir, opener=opener, today=sg.RETRIEVED)
    with pytest.raises(CacheMissingError, match="nitrogen"):
        estimate_at(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache_dir, properties=("nitrogen",))


def test_nodata_pixel_is_an_explicit_error(sg, cache: Path) -> None:
    clip = next(cache.rglob("soc_0-5cm_mean.tif"))
    with rasterio.open(clip, "r+") as ds:
        row, col = ds.index(*_to_raster(ds, sg.POINT_LON, sg.POINT_LAT))
        data = ds.read(1)
        data[row, col] = ds.nodata
        ds.write(data, 1)
    with pytest.raises(NoDataError, match="soc"):
        estimate_at(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache)


def test_estimate_rejects_p_and_k(sg, cache: Path) -> None:
    from data_sources.soilgrids.catalog import UnsupportedPropertyError

    with pytest.raises(UnsupportedPropertyError):
        estimate_at(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache, properties=("phosphorus",))


def _to_raster(ds, lon: float, lat: float) -> tuple[float, float]:
    from rasterio.warp import transform

    xs, ys = transform("EPSG:4326", ds.crs, [lon], [lat])
    return xs[0], ys[0]
