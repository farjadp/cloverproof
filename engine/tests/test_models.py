"""Input models: validation of farm data (no agronomy)."""

from datetime import date

import pytest
from pydantic import ValidationError

from cloverproof_engine.models import (
    ConcentrationUnit,
    Crop,
    ExtractionMethod,
    NutrientForm,
    RecommendationInput,
    SoilTest,
    SoilTestSource,
    SoilTestValue,
)


def _value(form: NutrientForm, value: float, method: ExtractionMethod, **extra: object):
    return SoilTestValue.model_validate(
        {
            "form": form,
            "value": value,
            "unit": ConcentrationUnit.MG_PER_KG,
            "extraction_method": method,
            **extra,
        }
    )


def _p(**extra: object) -> SoilTestValue:
    return _value(NutrientForm.P, 12.0, ExtractionMethod.OLSEN, **extra)


def _k(**extra: object) -> SoilTestValue:
    return _value(
        NutrientForm.K,
        150.0,
        ExtractionMethod.OTHER,
        extraction_method_detail="ammonium acetate",
        **extra,
    )


def _soil_test(**overrides: object) -> SoilTest:
    data: dict[str, object] = {
        "sample_date": date(2026, 9, 15),
        "depth_top_cm": 0.0,
        "depth_bottom_cm": 15.0,
        "source": SoilTestSource.LAB,
        "lab": "Example Lab",
        "values": [_p(), _k()],
    }
    data.update(overrides)
    return SoilTest.model_validate(data)


def _input(**overrides: object) -> RecommendationInput:
    data: dict[str, object] = {
        "crop": Crop.WHEAT,
        "target_yield_t_ha": 6.0,
        "previous_crop": "canola",
        "area_ha": 40.0,
        "plan_date": date(2027, 2, 15),
        "soil_test": None,
    }
    data.update(overrides)
    return RecommendationInput.model_validate(data)


def test_valid_input_without_soil_test() -> None:
    inp = _input()
    assert inp.soil_test is None
    assert inp.crop is Crop.WHEAT


def test_valid_input_with_soil_test() -> None:
    inp = _input(soil_test=_soil_test())
    assert inp.soil_test is not None
    assert inp.soil_test.value_for("P").extraction_method is ExtractionMethod.OLSEN
    assert inp.soil_test.value_for("K").extraction_method is ExtractionMethod.OTHER


def test_extraction_method_is_per_value_not_per_test() -> None:
    assert "extraction_method" not in SoilTest.model_fields
    with pytest.raises(ValidationError):
        _soil_test(extraction_method=ExtractionMethod.OLSEN)


def test_each_value_keeps_its_own_extraction_method() -> None:
    nitrate = _value(
        NutrientForm.NO3_N, 8.0, ExtractionMethod.OTHER, extraction_method_detail="2 M KCl"
    )
    soil = _soil_test(values=[_p(), _k(), nitrate])
    assert [v.extraction_method for v in soil.values] == [
        ExtractionMethod.OLSEN,
        ExtractionMethod.OTHER,
        ExtractionMethod.OTHER,
    ]
    assert soil.value_for("N").extraction_method_detail == "2 M KCl"


def test_extraction_method_is_required_on_a_value() -> None:
    with pytest.raises(ValidationError):
        SoilTestValue(form=NutrientForm.P, value=12.0, unit=ConcentrationUnit.MG_PER_KG)


@pytest.mark.parametrize("detail", [None, "", "   "])
def test_other_method_requires_a_detail(detail: str | None) -> None:
    with pytest.raises(ValidationError):
        _value(NutrientForm.K, 150.0, ExtractionMethod.OTHER, extraction_method_detail=detail)


def test_named_method_detail_is_optional() -> None:
    assert _p().extraction_method_detail is None
    assert _p(extraction_method_detail="NaHCO3").extraction_method_detail == "NaHCO3"


def test_extraction_method_values() -> None:
    assert {m.value for m in ExtractionMethod} == {
        "olsen",
        "bray-1",
        "mehlich-3",
        "ammonium-acetate",
        "other",
    }


def test_source_values() -> None:
    assert {s.value for s in SoilTestSource} == {"lab", "estimate"}


@pytest.mark.parametrize("field", ["target_yield_t_ha", "area_ha"])
def test_rejects_non_positive_numbers(field: str) -> None:
    with pytest.raises(ValidationError):
        _input(**{field: 0.0})


def test_rejects_unknown_crop() -> None:
    with pytest.raises(ValidationError):
        _input(crop="barley")


def test_rejects_empty_previous_crop() -> None:
    with pytest.raises(ValidationError):
        _input(previous_crop="  ")


def test_previous_crop_is_normalised() -> None:
    assert _input(previous_crop=" Canola ").previous_crop == "canola"


def test_soil_test_depth_must_be_ordered() -> None:
    with pytest.raises(ValidationError):
        _soil_test(depth_top_cm=15.0, depth_bottom_cm=15.0)


def test_soil_test_value_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        _value(NutrientForm.P, -1.0, ExtractionMethod.OLSEN)


def test_soil_test_rejects_duplicate_forms() -> None:
    dup = _p()
    with pytest.raises(ValidationError):
        _soil_test(values=[dup, dup])


def test_soil_test_rejects_same_nutrient_in_two_forms() -> None:
    p = _p()
    p2o5 = _value(NutrientForm.P2O5, 27.0, ExtractionMethod.OLSEN)
    with pytest.raises(ValidationError):
        _soil_test(values=[p, p2o5])


def test_soil_test_must_not_be_after_plan_date() -> None:
    with pytest.raises(ValidationError):
        _input(plan_date=date(2026, 1, 1), soil_test=_soil_test())


def test_soil_test_value_in_mg_per_kg() -> None:
    v = _p(unit=ConcentrationUnit.PPM)
    assert v.value_mg_per_kg == 12.0


def test_input_is_immutable() -> None:
    inp = _input()
    with pytest.raises(ValidationError):
        inp.area_ha = 10.0  # type: ignore[misc]


def test_input_snapshot_round_trips() -> None:
    inp = _input(soil_test=_soil_test())
    snap = inp.model_dump(mode="json")
    assert RecommendationInput.model_validate(snap) == inp


# --- n_price_ratio (needed by table-based N methods, e.g. pack ca-on v1) ----------


def test_price_ratio_is_optional_and_left_out_of_the_snapshot_when_absent() -> None:
    inp = _input()
    assert inp.n_price_ratio is None
    # Snapshots of inputs without a ratio are unchanged from engine 0.2.0.
    assert "n_price_ratio" not in inp.model_dump(mode="json")


def test_price_ratio_round_trips() -> None:
    inp = _input(n_price_ratio=6.5)
    snap = inp.model_dump(mode="json")
    assert snap["n_price_ratio"] == 6.5
    assert RecommendationInput.model_validate(snap) == inp


@pytest.mark.parametrize("ratio", [0, -1.0, float("inf"), float("nan")])
def test_price_ratio_must_be_positive_and_finite(ratio: float) -> None:
    with pytest.raises(ValidationError):
        _input(n_price_ratio=ratio)


def test_ammonium_acetate_is_a_named_extraction_method() -> None:
    # Ontario's accredited soil-test K uses an ammonium acetate extract (pack ca-on).
    assert ExtractionMethod("ammonium-acetate") is ExtractionMethod.AMMONIUM_ACETATE
    value = _value(NutrientForm.K, 120.0, ExtractionMethod.AMMONIUM_ACETATE)
    assert value.extraction_method is ExtractionMethod.AMMONIUM_ACETATE
    assert value.extraction_method_detail is None
