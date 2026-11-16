"""Allowlist, URL layout and unit factors."""

import pytest

from data_sources.soilgrids import catalog
from data_sources.soilgrids.catalog import (
    ALLOWED_PROPERTIES,
    UnsupportedDepthError,
    UnsupportedPropertyError,
    layer_url,
    parse_depths,
    parse_properties,
)

ISRIC_LAYERS_DOC = "https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html"


def test_allowlist_is_exactly_the_six_approved_properties() -> None:
    assert set(ALLOWED_PROPERTIES) == {"phh2o", "soc", "nitrogen", "clay", "sand", "silt"}


@pytest.mark.parametrize(
    "prop", ["phosphorus", "p", "P", "potassium", "k", "K", "p_olsen", "k_exch", "cec", "bdod"]
)
def test_anything_outside_allowlist_is_rejected(prop: str) -> None:
    with pytest.raises(UnsupportedPropertyError):
        parse_properties(f"phh2o,{prop}")


@pytest.mark.parametrize("prop", ["phosphorus", "potassium", "P", "K2O", "p2o5"])
def test_p_and_k_rejection_names_the_n_only_rule(prop: str) -> None:
    with pytest.raises(UnsupportedPropertyError, match="N-only"):
        parse_properties(prop)


def test_parse_properties_keeps_order_and_dedupes() -> None:
    assert parse_properties("soc, phh2o,soc") == ("soc", "phh2o")


def test_depths_are_standard_intervals_only() -> None:
    assert parse_depths("0-5cm,5-15cm,15-30cm") == ("0-5cm", "5-15cm", "15-30cm")
    with pytest.raises(UnsupportedDepthError):
        parse_depths("0-20cm")


def test_layer_url_matches_isric_file_layout() -> None:
    assert (
        layer_url("phh2o", "0-5cm", "mean")
        == "https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_0-5cm_mean.vrt"
    )
    assert (
        layer_url("soc", "15-30cm", "Q0.95")
        == "https://files.isric.org/soilgrids/latest/data/soc/soc_15-30cm_Q0.95.vrt"
    )


def test_rest_api_host_is_refused() -> None:
    with pytest.raises(ValueError, match="REST"):
        layer_url("soc", "0-5cm", "mean", base_url="https://rest.isric.org/soilgrids/v2.0")
    with pytest.raises(ValueError, match="REST"):
        layer_url("soc", "0-5cm", "mean", base_url="https://example.org/properties/query")


def test_no_rest_endpoint_anywhere_in_the_package_source() -> None:
    from pathlib import Path

    pkg = Path(catalog.__file__).parent
    for f in pkg.glob("*.py"):
        text = f.read_text()
        # The guard itself names the forbidden host; nothing else may.
        if f.name == "catalog.py":
            text = text.replace('_FORBIDDEN_URL_PARTS = ("rest.isric.org", "properties/query")', "")
        assert "rest.isric.org" not in text, f.name
        assert "properties/query" not in text, f.name


@pytest.mark.parametrize(
    ("prop", "mapped", "expected", "unit"),
    [
        ("phh2o", 65, 6.5, "pH"),
        ("soc", 250, 25_000.0, "mg/kg"),  # 250 dg/kg = 25 g/kg = 25 000 mg/kg
        ("nitrogen", 150, 1_500.0, "mg/kg"),  # 150 cg/kg = 1.5 g/kg = 1 500 mg/kg
        ("clay", 300, 30.0, "%"),
        ("sand", 350, 35.0, "%"),
        ("silt", 350, 35.0, "%"),
    ],
)
def test_unit_conversion(prop: str, mapped: int, expected: float, unit: str) -> None:
    conv = catalog.CONVERSIONS[prop]
    assert conv.to_canonical(mapped) == pytest.approx(expected)
    assert conv.canonical_unit == unit


def test_every_factor_is_cited_and_verified() -> None:
    for prop in ALLOWED_PROPERTIES:
        conv = catalog.CONVERSIONS[prop]
        assert conv.source_url == ISRIC_LAYERS_DOC
        assert conv.verified, f"{prop} factor is not verified"
    assert catalog.UNCERTAINTY_FACTOR.source_url == ISRIC_LAYERS_DOC


def test_uncertainty_layer_is_divided_by_ten() -> None:
    assert catalog.UNCERTAINTY_FACTOR.to_canonical(25) == pytest.approx(2.5)
