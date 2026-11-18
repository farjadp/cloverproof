"""Pack P/K config: schema rules, and the ca-on tables checked by a second hand entry."""

import copy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from cloverproof_engine.loaders import load_pack
from cloverproof_engine.models import Crop, ExtractionMethod, NutrientForm
from cloverproof_engine.pack import CitationBasis, ConstantStatus, Pack, pack_sha256, parse_pack

CA_ON_DIR = Path(__file__).resolve().parents[2] / "packs" / "ca-on"
CA_ON_PATH = CA_ON_DIR / "v2.yaml"

# Fingerprints. v1 is frozen: recommendations may record it, so P/K went into a new version.
CA_ON_V1_SHA256 = "84d874e7c6f0119cfeb44e5c5de8a9dfe04e3e9961a0dae0819cd856b1996e58"
CA_ON_V2_SHA256 = "2f2c8cf38dba08d73e38d86ea8219664a8716fd99d5b3ed8c97e7cda3b77aca7"

# Second, separate entry of the winter wheat columns (low, high, kg/ha, rating), from
# OMAFRA Pub 811 (PDF edition 2022-10-13) p. 131 Table 4-20 and p. 132 Table 4-21.
TABLE_4_20_WINTER_WHEAT = [
    (0, 3, 70, "HR"),
    (4, 5, 60, "HR"),
    (6, 7, 50, "HR"),
    (8, 9, 30, "HR"),
    (10, 12, 20, "MR"),
    (13, 15, 20, "MR"),
    (16, 20, 20, "MR"),
    (21, 25, 20, "MR"),
    (26, 30, 20, "MR"),
    (31, 40, 0, "LR"),
    (41, 50, 0, "RR"),
    (51, 60, 0, "RR"),
    (61, None, 0, "NR"),
]
TABLE_4_21_WINTER_WHEAT = [
    (0, 15, 50, "HR"),
    (16, 30, 40, "HR"),
    (31, 45, 30, "HR"),
    (46, 60, 20, "HR"),
    (61, 80, 20, "MR"),
    (81, 100, 20, "MR"),
    (101, 120, 20, "LR"),
    (121, 150, 0, "RR"),
    (151, 180, 0, "RR"),
    (181, 210, 0, "RR"),
    (211, 250, 0, "RR"),
    (251, None, 0, "NR"),
]


@pytest.fixture
def pack() -> Pack:
    return load_pack(CA_ON_PATH)


def _data(pack: Pack) -> dict[str, Any]:
    return copy.deepcopy(pack.model_dump(mode="json"))


def _p_table(data: dict[str, Any]) -> dict[str, Any]:
    return data["crops"]["wheat"]["phosphorus_potassium"]["nutrients"]["P"]["tables"]["olsen"]


@pytest.mark.parametrize(
    ("nutrient", "method", "form", "expected", "table_name"),
    [
        ("P", ExtractionMethod.OLSEN, NutrientForm.P2O5, TABLE_4_20_WINTER_WHEAT, "Table 4-20"),
        (
            "K",
            ExtractionMethod.AMMONIUM_ACETATE,
            NutrientForm.K2O,
            TABLE_4_21_WINTER_WHEAT,
            "Table 4-21",
        ),
    ],
)
def test_ca_on_tables_match_the_second_entry(
    pack: Pack,
    nutrient: str,
    method: ExtractionMethod,
    form: NutrientForm,
    expected: list[tuple[float, float | None, float, str]],
    table_name: str,
) -> None:
    cfg = pack.crops[Crop.WHEAT].phosphorus_potassium
    assert cfg is not None
    tables = cfg.nutrients[nutrient].tables
    assert list(tables) == [method]  # no other method can reach this table
    table = tables[method]
    assert table.rate_form is form
    assert [(b.low, b.high, b.rate, b.response) for b in table.bands] == expected
    assert table.status is ConstantStatus.PLACEHOLDER
    assert table.source is None
    assert table.citation is not None
    assert table.citation.basis is CitationBasis.STATED
    assert table_name in table.citation.locator
    assert "Winter Wheat" in table.citation.locator


def test_ca_on_tables_match_the_declared_soil_tests(pack: Pack) -> None:
    crop = pack.crops[Crop.WHEAT]
    assert crop.phosphorus_potassium is not None and crop.soil_test_methods is not None
    for nutrient, spec in crop.soil_test_methods.items():
        assert spec.extraction_method in crop.phosphorus_potassium.nutrients[nutrient].tables


def test_sample_depth_is_a_cited_placeholder(pack: Pack) -> None:
    cfg = pack.crops[Crop.WHEAT].phosphorus_potassium
    assert cfg is not None
    depth = cfg.sample_depth_cm
    assert (depth.value, depth.unit, depth.status) == (15, "cm", ConstantStatus.PLACEHOLDER)
    assert depth.source is None
    assert depth.citation is not None and depth.citation.basis is CitationBasis.STATED


def test_table_cells_count_as_pack_constants(pack: Pack) -> None:
    constants = list(pack.iter_constants())
    assert sum(c.unit == "kg P2O5/ha" for c in constants) == len(TABLE_4_20_WINTER_WHEAT)
    assert sum(c.unit == "kg K2O/ha" for c in constants) == len(TABLE_4_21_WINTER_WHEAT)


def test_a_validated_pack_cannot_hold_a_placeholder_pk_table(pack: Pack) -> None:
    data = _data(pack)
    data["status"] = "validated"
    with pytest.raises(ValidationError, match="PLACEHOLDER"):
        parse_pack(data)


@pytest.mark.parametrize(
    "bands",
    [
        [],
        [{"low": 5, "high": 3, "rate": 1, "response": "HR"}],
        [{"low": 0, "rate": 1, "response": "HR"}, {"low": 5, "rate": 1, "response": "HR"}],
        [
            {"low": 0, "high": 5, "rate": 1, "response": "HR"},
            {"low": 5, "rate": 1, "response": "HR"},
        ],
        [
            {"low": 6, "high": 9, "rate": 1, "response": "HR"},
            {"low": 0, "high": 5, "rate": 1, "response": "HR"},
        ],
        [{"low": 0, "rate": -1, "response": "HR"}],
        [{"low": -1, "rate": 1, "response": "HR"}],
        [{"low": 0, "rate": 1, "response": "not in the legend"}],
    ],
)
def test_bad_bands_are_rejected(pack: Pack, bands: list[dict[str, Any]]) -> None:
    data = _data(pack)
    _p_table(data)["bands"] = bands
    with pytest.raises(ValidationError):
        parse_pack(data)


def test_rate_form_must_express_the_nutrient(pack: Pack) -> None:
    data = _data(pack)
    _p_table(data)["rate_form"] = "K2O"
    with pytest.raises(ValidationError, match="rate_form"):
        parse_pack(data)


def test_a_table_cannot_be_keyed_to_method_other(pack: Pack) -> None:
    data = _data(pack)
    tables = data["crops"]["wheat"]["phosphorus_potassium"]["nutrients"]["P"]["tables"]
    tables["other"] = tables.pop("olsen")
    with pytest.raises(ValidationError, match="other"):
        parse_pack(data)


def test_placeholder_table_must_have_no_source(pack: Pack) -> None:
    data = _data(pack)
    _p_table(data)["source"] = "somewhere"
    with pytest.raises(ValidationError, match="source: null"):
        parse_pack(data)


def test_v1_stays_frozen_without_p_and_k_tables() -> None:
    v1 = load_pack(CA_ON_DIR / "v1.yaml")
    assert (v1.version, pack_sha256(v1)) == ("v1", CA_ON_V1_SHA256)
    assert v1.crops[Crop.WHEAT].phosphorus_potassium is None


def test_v2_is_pinned(pack: Pack) -> None:
    assert (pack.id, pack.version, pack_sha256(pack)) == ("ca-on", "v2", CA_ON_V2_SHA256)
