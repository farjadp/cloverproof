"""End-to-end engine call: output envelope, P/K handling, snapshot, versions."""

import json

import pytest

import cloverproof_engine
from cloverproof_engine import recommend
from cloverproof_engine.confidence import Confidence
from cloverproof_engine.methods import OutOfScopeError
from cloverproof_engine.models import ExtractionMethod, NutrientForm, SoilTestSource
from cloverproof_engine.pack import pack_sha256
from cloverproof_engine.results import Recommendation


def test_envelope(make_input, placeholder_pack) -> None:
    inputs = make_input()
    rec = recommend(inputs, placeholder_pack)
    assert isinstance(rec, Recommendation)
    assert rec.engine_version == cloverproof_engine.__version__
    assert rec.pack_id == "placeholder"
    assert rec.pack_version == "v0"
    assert rec.pack_status == "placeholder"
    assert rec.pack_sha256 == pack_sha256(placeholder_pack)
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


def test_estimated_soil_test_recommends_soil_test_for_pk(
    lab_soil_test, make_input, validated_pack
) -> None:
    soil = lab_soil_test(source=SoilTestSource.ESTIMATE)
    rec = recommend(make_input(soil_test=soil), validated_pack)
    assert rec.phosphorus_potassium.code == "PK_SOIL_TEST_RECOMMENDED"
    assert "estimate" in rec.phosphorus_potassium.text.lower()


def test_lab_test_without_p_or_k_recommends_soil_test_for_pk(
    lab_soil_test, soil_value, make_input, validated_pack
) -> None:
    nitrate = soil_value(
        NutrientForm.NO3_N, 8.0, ExtractionMethod.OTHER, extraction_method_detail="2 M KCl"
    )
    rec = recommend(make_input(soil_test=lab_soil_test(values=[nitrate])), validated_pack)
    assert rec.phosphorus_potassium.code == "PK_SOIL_TEST_RECOMMENDED"
    assert "no p or k value" in rec.phosphorus_potassium.text.lower()


def test_lab_test_with_no_values_recommends_soil_test_for_pk(
    lab_soil_test, make_input, validated_pack
) -> None:
    rec = recommend(make_input(soil_test=lab_soil_test(values=[])), validated_pack)
    assert rec.phosphorus_potassium.code == "PK_SOIL_TEST_RECOMMENDED"


def test_lab_test_with_p_only_is_not_calculated_v0(
    lab_soil_test, soil_value, make_input, validated_pack
) -> None:
    soil = lab_soil_test(values=[soil_value(NutrientForm.P, 12.0)])
    rec = recommend(make_input(soil_test=soil), validated_pack)
    assert rec.phosphorus_potassium.code == "PK_NOT_CALCULATED_V0"


def test_lab_test_with_k_only_is_not_calculated_v0(
    lab_soil_test, soil_value, make_input, validated_pack
) -> None:
    k2o = soil_value(
        NutrientForm.K2O, 180.0, ExtractionMethod.OTHER, extraction_method_detail="ammonium acetate"
    )
    rec = recommend(make_input(soil_test=lab_soil_test(values=[k2o])), validated_pack)
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


def test_unused_soil_nitrate_note(lab_soil_test, soil_value, make_input, placeholder_pack) -> None:
    values = [
        soil_value(
            NutrientForm.NO3_N, 8.0, ExtractionMethod.OTHER, extraction_method_detail="2 M KCl"
        )
    ]
    rec = recommend(make_input(soil_test=lab_soil_test(values=values)), placeholder_pack)
    assert "SOIL_NITRATE_NOT_USED" in [n.code for n in rec.notes]
    assert rec.nitrogen.rate.value == pytest.approx(175.0)


def test_manure_applied_is_refused_by_every_pack(make_input, placeholder_pack) -> None:
    # The engine has no manure N credit for any pack yet: never ignore manure silently.
    with pytest.raises(OutOfScopeError, match="manure"):
        recommend(make_input(manure_applied=True), placeholder_pack)


def test_placeholder_pack_ignores_absent_scope_inputs(make_input, placeholder_pack) -> None:
    rec = recommend(make_input(), placeholder_pack)
    assert "wheat_class" not in rec.input_snapshot
    assert "manure" not in rec.nitrogen.rate.explanation


def test_crop_missing_from_pack(make_input, placeholder_pack) -> None:
    empty = placeholder_pack.model_copy(update={"crops": {}})
    with pytest.raises(ValueError):
        recommend(make_input(), empty)


def test_confidence_reasons_are_recorded(make_input, placeholder_pack) -> None:
    rec = recommend(make_input(), placeholder_pack)
    assert rec.confidence is Confidence.LOW
    assert {h.rule_id for h in rec.confidence_reasons} == {
        "C1_NO_SOIL_TEST",
        "C6_PLACEHOLDER_CONSTANT_USED",
    }
