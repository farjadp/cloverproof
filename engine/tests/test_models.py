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


def _soil_test(**overrides: object) -> SoilTest:
    data: dict[str, object] = {
        "sample_date": date(2026, 9, 15),
        "depth_top_cm": 0.0,
        "depth_bottom_cm": 15.0,
        "extraction_method": ExtractionMethod.OLSEN,
        "source": SoilTestSource.LAB,
        "lab": "Example Lab",
        "values": [
            SoilTestValue(form=NutrientForm.P, value=12.0, unit=ConcentrationUnit.MG_PER_KG),
            SoilTestValue(form=NutrientForm.K, value=150.0, unit=ConcentrationUnit.MG_PER_KG),
        ],
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
    assert inp.soil_test.extraction_method is ExtractionMethod.OLSEN


def test_extraction_method_values() -> None:
    assert {m.value for m in ExtractionMethod} == {"olsen", "bray-1", "mehlich-3", "other"}


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
        SoilTestValue(form=NutrientForm.P, value=-1.0, unit=ConcentrationUnit.MG_PER_KG)


def test_soil_test_rejects_duplicate_forms() -> None:
    dup = SoilTestValue(form=NutrientForm.P, value=12.0, unit=ConcentrationUnit.MG_PER_KG)
    with pytest.raises(ValidationError):
        _soil_test(values=[dup, dup])


def test_soil_test_rejects_same_nutrient_in_two_forms() -> None:
    p = SoilTestValue(form=NutrientForm.P, value=12.0, unit=ConcentrationUnit.MG_PER_KG)
    p2o5 = SoilTestValue(form=NutrientForm.P2O5, value=27.0, unit=ConcentrationUnit.MG_PER_KG)
    with pytest.raises(ValidationError):
        _soil_test(values=[p, p2o5])


def test_soil_test_must_not_be_after_plan_date() -> None:
    with pytest.raises(ValidationError):
        _input(plan_date=date(2026, 1, 1), soil_test=_soil_test())


def test_soil_test_value_in_mg_per_kg() -> None:
    v = SoilTestValue(form=NutrientForm.P, value=12.0, unit=ConcentrationUnit.PPM)
    assert v.value_mg_per_kg == 12.0


def test_input_is_immutable() -> None:
    inp = _input()
    with pytest.raises(ValidationError):
        inp.area_ha = 10.0  # type: ignore[misc]


def test_input_snapshot_round_trips() -> None:
    inp = _input(soil_test=_soil_test())
    snap = inp.model_dump(mode="json")
    assert RecommendationInput.model_validate(snap) == inp
