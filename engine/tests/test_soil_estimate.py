"""SoilGrids estimate as context: N only, never a P or K rate, changes no number."""

import ast
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import cloverproof_engine
from cloverproof_engine import recommend
from cloverproof_engine.golden import parse_golden_case
from cloverproof_engine.loaders import load_pack
from cloverproof_engine.models import SoilEstimate, SoilTestSource
from cloverproof_engine.results import Recommendation

REPO_ROOT = Path(__file__).resolve().parents[2]
CA_ON_V2 = REPO_ROOT / "packs" / "ca-on" / "v2.yaml"
ATTRIBUTION = "SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0"
LAB_TEST_SENTENCE = (
    "A lab soil test was also given; the estimate does not replace it and is context only."
)


def _without_estimate(doc: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in doc.items() if k != "soil_estimate"}
    out["input_snapshot"] = {k: v for k, v in doc["input_snapshot"].items() if k != "soil_estimate"}
    return out


def _value(soil_estimate_data, **overrides: Any) -> dict[str, Any]:
    return {**soil_estimate_data()["values"][0], **overrides}


# --- input ---------------------------------------------------------------------------


def test_absent_estimate_leaves_snapshot_and_result_unchanged(make_input, placeholder_pack) -> None:
    doc = recommend(make_input(), placeholder_pack).model_dump(mode="json")
    assert "soil_estimate" not in doc
    assert "soil_estimate" not in doc["input_snapshot"]


def test_snapshot_keeps_version_and_retrieval_date(
    make_input, soil_estimate_data, placeholder_pack
) -> None:
    inputs = make_input(soil_estimate=soil_estimate_data())
    snapshot = recommend(inputs, placeholder_pack).input_snapshot["soil_estimate"]
    assert snapshot["provider"] == "SoilGrids"
    assert snapshot["version"] == "2.0"
    assert snapshot["attribution"] == ATTRIBUTION
    assert snapshot["values"][0]["retrieved_on"] == "2026-11-18"
    assert snapshot["values"][0]["resolution_m"] == 250.0


@pytest.mark.parametrize(
    "name", ["phosphorus", "potassium", "P", "K", "P2O5", "K2O", "olsen_p", "nitrate", "NO3-N"]
)
def test_property_outside_the_allowlist_is_refused(soil_estimate_data, name: str) -> None:
    data = soil_estimate_data(values=[_value(soil_estimate_data, property=name)])
    with pytest.raises(ValidationError):
        SoilEstimate.model_validate(data)


@pytest.mark.parametrize("field", ["p_mg_kg", "k_mg_kg", "form", "extraction_method"])
def test_value_cannot_carry_extra_fields(soil_estimate_data, field: str) -> None:
    data = soil_estimate_data(values=[_value(soil_estimate_data, **{field: "x"})])
    with pytest.raises(ValidationError):
        SoilEstimate.model_validate(data)


def test_estimate_cannot_carry_extra_fields(soil_estimate_data) -> None:
    with pytest.raises(ValidationError):
        SoilEstimate.model_validate(soil_estimate_data(phosphorus=12.0))


def test_only_soilgrids_is_accepted(soil_estimate_data) -> None:
    with pytest.raises(ValidationError):
        SoilEstimate.model_validate(soil_estimate_data(provider="Other"))


@pytest.mark.parametrize(
    "overrides",
    [
        {"unit": "mg/kg"},  # pH must be in pH
        {"depth": "0-10cm"},
        {"value": -1.0},
        {"value": float("nan")},
        {"resolution_m": 0.0},
        {"q05": 7.5, "q95": 7.0},
    ],
)
def test_bad_value_is_refused(soil_estimate_data, overrides: dict[str, Any]) -> None:
    data = soil_estimate_data(values=[_value(soil_estimate_data, **overrides)])
    with pytest.raises(ValidationError):
        SoilEstimate.model_validate(data)


def test_estimate_needs_values(soil_estimate_data) -> None:
    with pytest.raises(ValidationError):
        SoilEstimate.model_validate(soil_estimate_data(values=[]))


def test_same_property_and_depth_twice_is_refused(soil_estimate_data) -> None:
    value = _value(soil_estimate_data)
    with pytest.raises(ValidationError):
        SoilEstimate.model_validate(soil_estimate_data(values=[value, value]))


@pytest.mark.parametrize("field", ["provider", "version", "attribution", "citation"])
def test_provenance_is_required(soil_estimate_data, field: str) -> None:
    data = soil_estimate_data()
    del data[field]
    with pytest.raises(ValidationError):
        SoilEstimate.model_validate(data)


@pytest.mark.parametrize("field", ["attribution", "citation", "version"])
def test_provenance_must_not_be_blank(soil_estimate_data, field: str) -> None:
    with pytest.raises(ValidationError):
        SoilEstimate.model_validate(soil_estimate_data(**{field: "  "}))


# --- no number changes ---------------------------------------------------------------


def test_no_test_estimate_changes_no_number(
    make_input, soil_estimate_data, placeholder_pack
) -> None:
    without = recommend(make_input(), placeholder_pack).model_dump(mode="json")
    inputs = make_input(soil_estimate=soil_estimate_data())
    with_estimate = recommend(inputs, placeholder_pack).model_dump(mode="json")
    assert _without_estimate(with_estimate) == without
    assert with_estimate["phosphorus_potassium"]["code"] == "PK_SOIL_TEST_RECOMMENDED"
    assert "phosphorus_potassium_rates" not in with_estimate


def _pk_pack_input() -> dict[str, Any]:
    return {
        "crop": "wheat",
        "target_yield_t_ha": 6.5,
        "previous_crop": "corn",
        "area_ha": 20.0,
        "plan_date": "2027-03-15",
        "n_price": {
            "n_price_per_kg_n": 1.375,
            "grain_price_per_kg": 0.25,
            "currency": "CAD",
            "source": "SAMPLE",
            "price_date": "2027-01-20",
        },
        "wheat_class": "pastry",
        "manure_applied": False,
    }


def _lab_test() -> dict[str, Any]:
    return {
        "sample_date": "2026-09-15",
        "depth_top_cm": 0,
        "depth_bottom_cm": 15,
        "source": "lab",
        "values": [
            {"form": "P", "value": 7, "unit": "mg/kg", "extraction_method": "olsen"},
            {"form": "K", "value": 40, "unit": "ppm", "extraction_method": "ammonium-acetate"},
        ],
    }


def _ca_on(make_input, **extra: Any) -> dict[str, Any]:
    inputs = make_input(**{**_pk_pack_input(), **extra})
    return recommend(inputs, load_pack(CA_ON_V2)).model_dump(mode="json")


def test_pack_with_pk_tables_gives_no_rate_from_an_estimate(make_input, soil_estimate_data) -> None:
    doc = _ca_on(make_input, soil_estimate=soil_estimate_data())
    assert "phosphorus_potassium_rates" not in doc
    assert doc["phosphorus_potassium"]["code"] == "PK_SOIL_TEST_RECOMMENDED"
    assert "soil test" in doc["phosphorus_potassium"]["text"].lower()


def test_estimate_does_not_replace_a_lab_test(make_input, soil_estimate_data) -> None:
    without = _ca_on(make_input, soil_test=_lab_test())
    both = _ca_on(make_input, soil_test=_lab_test(), soil_estimate=soil_estimate_data())
    assert _without_estimate(both) == without
    assert both["phosphorus_potassium"]["code"] == "PK_FROM_LAB_TEST"
    assert both["soil_estimate"]["lab_test_given"] is True
    explanation = both["soil_estimate"]["explanation"]
    assert LAB_TEST_SENTENCE in explanation
    assert "decides" not in explanation


def test_lab_test_without_values_is_not_reported_as_given(make_input, soil_estimate_data) -> None:
    empty = {**_lab_test(), "values": []}
    block = _ca_on(make_input, soil_test=empty, soil_estimate=soil_estimate_data())["soil_estimate"]
    assert block["lab_test_given"] is False
    assert LAB_TEST_SENTENCE not in block["explanation"]
    assert "do not count as a soil test" in block["explanation"]


def test_estimate_sourced_soil_test_is_not_a_lab_test(
    lab_soil_test, make_input, soil_estimate_data, placeholder_pack
) -> None:
    soil = lab_soil_test(source=SoilTestSource.ESTIMATE)
    inputs = make_input(soil_test=soil, soil_estimate=soil_estimate_data())
    block = recommend(inputs, placeholder_pack).soil_estimate
    assert block is not None
    assert block.lab_test_given is False


# --- the context block ----------------------------------------------------------------


def _block(make_input, soil_estimate_data, placeholder_pack, **extra: Any):
    data = soil_estimate_data(**extra)
    block = recommend(make_input(soil_estimate=data), placeholder_pack).soil_estimate
    assert block is not None
    return block


def test_every_value_is_labelled(make_input, soil_estimate_data, placeholder_pack) -> None:
    block = _block(make_input, soil_estimate_data, placeholder_pack)
    assert block.confidence.value == "low"
    assert block.lab_test_given is False
    assert block.changes_numbers is False
    assert block.attribution == ATTRIBUTION
    assert block.citation == soil_estimate_data()["citation"]
    for line in block.values:
        assert line.confidence.value == "low"
        assert line.source == "SoilGrids"
        assert line.version == "2.0"
        assert line.attribution == ATTRIBUTION
        assert line.retrieved_on.isoformat() == "2026-11-18"
        assert line.resolution_m == 250.0
        assert line.depth == "0-5cm"
        assert line.value.uses_placeholder is False


def test_attribution_is_kept_exactly_as_supplied(
    make_input, soil_estimate_data, placeholder_pack
) -> None:
    wording = "Exact  wording, CC BY 4.0 "
    block = _block(make_input, soil_estimate_data, placeholder_pack, attribution=wording)
    assert block.attribution == wording
    assert {line.attribution for line in block.values} == {wording}


def test_every_number_is_explained(make_input, soil_estimate_data, placeholder_pack) -> None:
    line = _block(make_input, soil_estimate_data, placeholder_pack).values[0]
    numbers = (line.value, line.q05, line.q95, line.uncertainty_ratio)
    for number in numbers:
        assert number is not None
        assert number.explanation.strip()
    assert (line.value.value, line.value.unit) == (6.5, "pH")
    assert (line.q05.value, line.q95.value) == (5.8, 7.2)
    assert line.uncertainty_ratio.unit == "ratio"


def test_missing_quantiles_stay_absent(make_input, soil_estimate_data, placeholder_pack) -> None:
    line = _block(make_input, soil_estimate_data, placeholder_pack).values[1]
    assert line.q05 is None and line.q95 is None and line.uncertainty_ratio is None


def test_explanation_says_modelled_and_rate_unchanged(
    make_input, soil_estimate_data, placeholder_pack
) -> None:
    block = _block(make_input, soil_estimate_data, placeholder_pack)
    for text in (block.explanation, block.values[0].value.explanation):
        assert "modelled estimate" in text
        assert "did not change the N rate" in text
    assert "not a lab" in block.explanation
    assert "phosphorus" in block.explanation.lower()


def test_total_nitrogen_is_never_presented_as_nitrate(
    make_input, soil_estimate_data, placeholder_pack
) -> None:
    inputs = make_input(soil_estimate=soil_estimate_data())
    rec = recommend(inputs, placeholder_pack)
    assert "SOIL_NITRATE_NOT_USED" not in [n.code for n in rec.notes]
    assert rec.soil_estimate is not None
    line = next(v for v in rec.soil_estimate.values if v.property == "nitrogen")
    assert line.value.name == "Total soil nitrogen (estimate)"
    assert "not nitrate (NO3-N)" in line.value.explanation
    assert "form" not in line.model_dump()


def test_document_round_trips(make_input, soil_estimate_data, placeholder_pack) -> None:
    rec = recommend(make_input(soil_estimate=soil_estimate_data()), placeholder_pack)
    assert Recommendation.model_validate(rec.model_dump(mode="json")) == rec


# --- golden and purity ----------------------------------------------------------------


def test_golden_expected_line_uses_the_allowlist() -> None:
    data = {
        "id": "t",
        "kind": "sample",
        "pack": {"id": "placeholder", "version": "v0"},
        "tolerance": {"kg_n_per_ha": 0.5, "kg_n": 10.0},
        "input": _pk_pack_input(),
        "expected": {
            "n_rate_kg_ha": 1.0,
            "n_total_kg": 1.0,
            "split_rates_kg_ha": [1.0],
            "confidence": "low",
            "pk_note": "x",
            "soil_estimate": [
                {
                    "property": "phosphorus",
                    "depth": "0-5cm",
                    "value": 1.0,
                    "unit": "mg/kg",
                    "confidence": "low",
                }
            ],
        },
    }
    with pytest.raises(ValidationError, match="soil_estimate"):
        parse_golden_case(data)


def test_engine_never_imports_data_sources() -> None:
    package = Path(cloverproof_engine.__file__).resolve().parent
    for path in package.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            assert not any(n.split(".")[0] == "data_sources" for n in names), path
