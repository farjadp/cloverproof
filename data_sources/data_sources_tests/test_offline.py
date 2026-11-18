"""S3-ENG-01: estimates come from local files only, or the answer is "no estimate"."""

import json
import socket
from pathlib import Path

import pytest
import rasterio
from pydantic import TypeAdapter, ValidationError

from data_sources.soilgrids import (
    ATTRIBUTION,
    CITATION,
    CacheMissingError,
    NoEstimate,
    SoilEstimate,
    SoilLookup,
    UnsupportedPropertyError,
    estimate_at,
    fetch,
    lookup_estimate,
)

PROPS = ("nitrogen", "soc")
DEPTHS = ("0-5cm",)
DOCS_ATTRIBUTION = "SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0"


class NetworkBlocked(AssertionError):
    pass


@pytest.fixture
def cache(sg, tmp_path: Path, opener) -> Path:
    cache_dir = tmp_path / "cache"
    fetch(sg.BBOX, PROPS, DEPTHS, cache_dir=cache_dir, opener=opener, today=sg.RETRIEVED)
    return cache_dir


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise NetworkBlocked(f"network attempt: {args}")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


@pytest.fixture
def opened_paths(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every dataset GDAL is asked for; GDAL's libcurl does not go through Python sockets."""
    seen: list[str] = []
    real_open = rasterio.open

    def spy(path: object, *args: object, **kwargs: object):
        seen.append(str(path))
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(rasterio, "open", spy)
    return seen


def _edit_manifest(cache: Path, change) -> None:
    path = next(cache.glob("*/manifest.json"))
    manifest = json.loads(path.read_text())
    change(manifest)
    path.write_text(json.dumps(manifest))


def _mask_point(sg, clip: Path) -> None:
    from rasterio.warp import transform

    with rasterio.open(clip, "r+") as ds:
        xs, ys = transform("EPSG:4326", ds.crs, [sg.POINT_LON], [sg.POINT_LAT])
        row, col = ds.index(xs[0], ys[0])
        data = ds.read(1)
        data[row, col] = ds.nodata
        ds.write(data, 1)


@pytest.mark.usefixtures("no_network")
def test_the_network_block_is_real() -> None:
    with pytest.raises(NetworkBlocked):
        socket.socket()
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("127.0.0.1", 9))
    with pytest.raises(NetworkBlocked):
        socket.getaddrinfo("files.isric.org", 443)


@pytest.mark.usefixtures("no_network")
def test_estimate_succeeds_with_network_blocked(sg, cache: Path, opened_paths) -> None:
    result = lookup_estimate(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache)
    assert isinstance(result, SoilEstimate)
    assert {v.property for v in result.values} == set(PROPS)
    assert opened_paths
    assert all(Path(p).is_relative_to(cache) for p in opened_paths)
    assert not any("vsi" in p or "://" in p for p in opened_paths)


@pytest.mark.parametrize("name", ["/vsicurl/https://example.org/x.tif", "../x.tif", "x.vrt"])
def test_manifest_cannot_redirect_a_read(sg, cache: Path, opened_paths, name: str) -> None:
    def change(manifest: dict) -> None:
        for layer in manifest["layers"]:
            layer["file"] = name

    _edit_manifest(cache, change)
    with pytest.raises(CacheMissingError, match="non-local"):
        lookup_estimate(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache)
    assert not opened_paths


def test_every_value_carries_its_provenance(sg, cache: Path) -> None:
    result = estimate_at(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache)
    for value in result.model_dump(mode="json")["values"]:
        assert value["provider"] == "SoilGrids"
        assert value["version"] == "2.0"
        assert value["resolution_m"] == 250.0
        assert value["depth"] == "0-5cm"
        assert (value["depth_top_cm"], value["depth_bottom_cm"]) == (0, 5)
        assert value["retrieved_on"] == sg.RETRIEVED.isoformat()


@pytest.mark.parametrize(
    ("lon", "lat"),
    [(-100.0, 50.0), (-80.2, 43.55), (200.0, 0.0), (float("nan"), 43.55)],
)
def test_point_outside_the_cache_is_no_estimate(cache: Path, lon: float, lat: float) -> None:
    assert lookup_estimate(lon, lat, cache_dir=cache) == NoEstimate(reason="outside_cache")


def test_point_in_bbox_but_off_the_clip_is_no_estimate(sg, cache: Path) -> None:
    _edit_manifest(cache, lambda m: m.update(bbox_wgs84=[-90.0, 40.0, -70.0, 50.0]))
    result = lookup_estimate(-85.0, 45.0, cache_dir=cache)
    assert result == NoEstimate(reason="outside_cache")


def test_nodata_pixel_is_no_estimate(sg, cache: Path) -> None:
    _mask_point(sg, next(cache.rglob("nitrogen_0-5cm_mean.tif")))
    result = lookup_estimate(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache)
    assert result == NoEstimate(reason="nodata")
    assert "value" not in result.model_dump()


def test_nodata_is_per_requested_layer(sg, cache: Path) -> None:
    _mask_point(sg, next(cache.rglob("soc_0-5cm_mean.tif")))
    result = lookup_estimate(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache, properties=("nitrogen",))
    assert isinstance(result, SoilEstimate)


def test_missing_cache_stays_a_fault_not_a_no_estimate(sg, tmp_path: Path) -> None:
    with pytest.raises(CacheMissingError):
        lookup_estimate(sg.POINT_LON, sg.POINT_LAT, cache_dir=tmp_path / "nope")


def test_other_source_version_is_refused(sg, cache: Path) -> None:
    _edit_manifest(cache, lambda m: m.update(version="3.0"))
    with pytest.raises(CacheMissingError, match="unsupported source"):
        lookup_estimate(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache)


def test_p_or_k_request_raises(sg, cache: Path) -> None:
    with pytest.raises(UnsupportedPropertyError):
        lookup_estimate(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache, properties=("potassium",))


def test_p_or_k_layer_in_a_manifest_is_refused(sg, cache: Path) -> None:
    def change(manifest: dict) -> None:
        manifest["layers"].append({**manifest["layers"][0], "property": "phosphorus"})

    _edit_manifest(cache, change)
    with pytest.raises(UnsupportedPropertyError):
        lookup_estimate(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache)


def test_attribution_matches_the_data_sources_register(sg, cache: Path) -> None:
    assert ATTRIBUTION == DOCS_ATTRIBUTION
    result = estimate_at(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache)
    assert result.attribution == DOCS_ATTRIBUTION
    assert result.citation == CITATION
    assert "SOIL 7, 217-240" in CITATION and "10.5194/soil-7-217-2021" in CITATION


def test_output_round_trips_as_plain_json(sg, cache: Path) -> None:
    adapter = TypeAdapter(SoilLookup)
    for result in (
        lookup_estimate(sg.POINT_LON, sg.POINT_LAT, cache_dir=cache),
        lookup_estimate(-100.0, 50.0, cache_dir=cache),
    ):
        plain = json.loads(result.model_dump_json())
        assert adapter.validate_python(plain) == result


@pytest.mark.parametrize("field", ["phosphorus", "potassium", "value"])
def test_no_estimate_cannot_carry_numbers(field: str) -> None:
    with pytest.raises(ValidationError):
        NoEstimate(reason="nodata", **{field: 1.0})
