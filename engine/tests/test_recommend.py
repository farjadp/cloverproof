"""End-to-end engine call: output envelope, P/K handling, snapshot, versions."""

import json

import pytest

import cloverproof_engine
from cloverproof_engine import recommend
from cloverproof_engine.confidence import Confidence
from cloverproof_engine.models import ConcentrationUnit, NutrientForm, SoilTestValue
from cloverproof_engine.results import Recommendation


def test_envelope(make_input, placeholder_pack) -> None:
    inputs = make_input()
    rec = recommend(inputs, placeholder_pack)
    assert isinstance(rec, Recommendation)
    assert rec.engine_version == cloverproof_engine.__version__
    assert rec.pack_id == "placeholder"
    assert rec.pack_version == "v0"
    assert rec.pack_status == "placeholder"
    assert rec.crop == "wheat"
    assert rec.nitrogen.rate.value == pytest.approx(175.0)
    assert rec.input_snapshot == inputs.model_dump(mode="json")


def test_output_is_json_serialisable(lab_soil_test, make_input, placeholder_pack) -> None:
    rec = recommend(make_input(soil_test=lab_soil_test()), placeholder_pack)
    dumped = json.dumps(rec.model_dump(mode="json"))
    assert Recommendation.model_validate_json(dumped) == rec


def test_no_soil_test_recommends_soil_test_for_pk(make_input, validated_pack) -> None:
    rec = recommend(make_input(), validated_pack)
    assert rec.phosphorus_potassium.code == "PK_SOIL_TEST_RECOMMENDED"
    assert "soil test" in rec.phosphorus_potassium.text.lower()
    assert rec.confidence <= Confidence.MEDIUM


def test_soil_test_present_pk_still_not_recommended(
    lab_soil_test, make_input, validated_pack
) -> None:
    rec = recommend(make_input(soil_test=lab_soil_test()), validated_pack)
    assert rec.phosphorus_potassium.code == "PK_NOT_CALCULATED_V0"


def test_no_pk_numbers_anywhere(lab_soil_test, make_input, placeholder_pack) -> None:
    rec = recommend(make_input(soil_test=lab_soil_test()), placeholder_pack)
    dumped = rec.model_dump(mode="json")
    dumped.pop("input_snapshot")
    text = json.dumps(dumped)
    for token in ("P2O5", "K2O", "kg P/", "kg K/"):
        assert token not in text


def test_placeholder_pack_note(make_input, placeholder_pack) -> None:
    rec = recommend(make_input(), placeholder_pack)
    assert "PACK_HAS_PLACEHOLDERS" in [n.code for n in rec.notes]


def test_unused_soil_nitrate_note(lab_soil_test, make_input, placeholder_pack) -> None:
    values = [SoilTestValue(form=NutrientForm.NO3_N, value=8.0, unit=ConcentrationUnit.MG_PER_KG)]
    rec = recommend(make_input(soil_test=lab_soil_test(values=values)), placeholder_pack)
    assert "SOIL_NITRATE_NOT_USED" in [n.code for n in rec.notes]
    assert rec.nitrogen.rate.value == pytest.approx(175.0)


def test_crop_missing_from_pack(make_input, placeholder_pack) -> None:
    empty = placeholder_pack.model_copy(update={"crops": {}})
    with pytest.raises(ValueError):
        recommend(make_input(), empty)


def test_confidence_reasons_are_recorded(make_input, placeholder_pack) -> None:
    rec = recommend(make_input(), placeholder_pack)
    assert rec.confidence is Confidence.LOW
    assert {h.rule_id for h in rec.confidence_reasons} == {
        "C1_NO_SOIL_TEST",
        "C6_PACK_HAS_PLACEHOLDERS",
    }
