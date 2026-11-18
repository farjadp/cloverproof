"""Unit conversions: chemistry and unit facts only (no agronomy)."""

import math
from collections.abc import Callable

import pytest

from cloverproof_engine import units
from cloverproof_engine.models import NutrientForm


def test_p2o5_to_p_factor_from_atomic_masses() -> None:
    # P2O5 molar mass = 2*30.973762 + 5*15.999 = 141.942524 g/mol
    expected = (2 * 30.973762) / (2 * 30.973762 + 5 * 15.999)
    assert pytest.approx(expected, rel=1e-12) == units.P2O5_TO_P
    assert pytest.approx(0.4364, abs=1e-4) == units.P2O5_TO_P
    assert pytest.approx(1 / expected, rel=1e-12) == units.P_TO_P2O5
    assert pytest.approx(2.2914, abs=1e-4) == units.P_TO_P2O5


def test_k2o_to_k_factor_from_atomic_masses() -> None:
    expected = (2 * 39.0983) / (2 * 39.0983 + 15.999)
    assert pytest.approx(expected, rel=1e-12) == units.K2O_TO_K
    assert pytest.approx(0.8301, abs=1e-4) == units.K2O_TO_K
    assert pytest.approx(1.2046, abs=1e-4) == units.K_TO_K2O


@pytest.mark.parametrize("value", [0.0, 1.0, 17.3, 250.0])
def test_p_round_trip(value: float) -> None:
    assert units.p2o5_to_p(units.p_to_p2o5(value)) == pytest.approx(value, rel=1e-12)
    assert units.p_to_p2o5(units.p2o5_to_p(value)) == pytest.approx(value, rel=1e-12)


@pytest.mark.parametrize("value", [0.0, 1.0, 42.5, 300.0])
def test_k_round_trip(value: float) -> None:
    assert units.k2o_to_k(units.k_to_k2o(value)) == pytest.approx(value, rel=1e-12)
    assert units.k_to_k2o(units.k2o_to_k(value)) == pytest.approx(value, rel=1e-12)


def test_lb_per_acre_to_kg_per_ha() -> None:
    # 1 lb = 0.45359237 kg (exact), 1 acre = 4046.8564224 m2 (exact)
    assert pytest.approx(0.45359237 / 0.40468564224, rel=1e-12) == units.LB_PER_AC_TO_KG_PER_HA
    assert units.lb_per_ac_to_kg_per_ha(100.0) == pytest.approx(112.085, abs=1e-3)


@pytest.mark.parametrize("value", [0.0, 1.0, 89.2, 160.0])
def test_lb_kg_round_trip(value: float) -> None:
    there = units.lb_per_ac_to_kg_per_ha(value)
    assert units.kg_per_ha_to_lb_per_ac(there) == pytest.approx(value, rel=1e-12)


def test_ppm_equals_mg_per_kg() -> None:
    assert units.ppm_to_mg_per_kg(12.5) == 12.5


def test_mg_per_kg_to_kg_per_ha_for_soil_layer() -> None:
    # 10 mg/kg in a 15 cm layer at 1.3 g/cm3:
    # soil mass = 0.15 m * 10000 m2 * 1300 kg/m3 = 1 950 000 kg/ha -> 19.5 kg/ha
    assert units.mg_per_kg_to_kg_per_ha(
        10.0, layer_thickness_cm=15.0, bulk_density_g_cm3=1.3
    ) == pytest.approx(19.5, rel=1e-12)


def test_mg_per_kg_to_kg_per_ha_rejects_non_positive_layer() -> None:
    with pytest.raises(ValueError):
        units.mg_per_kg_to_kg_per_ha(10.0, layer_thickness_cm=0.0, bulk_density_g_cm3=1.3)
    with pytest.raises(ValueError):
        units.mg_per_kg_to_kg_per_ha(10.0, layer_thickness_cm=15.0, bulk_density_g_cm3=0.0)


@pytest.mark.parametrize(
    ("value", "from_form", "to_form", "expected"),
    [
        (100.0, NutrientForm.P2O5, NutrientForm.P, 100.0 * units.P2O5_TO_P),
        (100.0, NutrientForm.P, NutrientForm.P2O5, 100.0 * units.P_TO_P2O5),
        (100.0, NutrientForm.K2O, NutrientForm.K, 100.0 * units.K2O_TO_K),
        (100.0, NutrientForm.K, NutrientForm.K2O, 100.0 * units.K_TO_K2O),
        (55.0, NutrientForm.P, NutrientForm.P, 55.0),
    ],
)
def test_convert_form(
    value: float, from_form: NutrientForm, to_form: NutrientForm, expected: float
) -> None:
    assert units.convert_form(value, from_form, to_form) == pytest.approx(expected, rel=1e-12)


def test_convert_form_rejects_cross_nutrient() -> None:
    with pytest.raises(ValueError):
        units.convert_form(10.0, NutrientForm.P, NutrientForm.K2O)


def test_to_elemental() -> None:
    assert units.to_elemental(10.0, NutrientForm.P2O5) == pytest.approx(10.0 * units.P2O5_TO_P)
    assert units.to_elemental(10.0, NutrientForm.K) == 10.0
    assert math.isclose(units.to_elemental(10.0, NutrientForm.NO3_N), 10.0)


def test_years_between_dates() -> None:
    from datetime import date

    # Julian year = 365.25 days (unit definition).
    assert units.DAYS_PER_JULIAN_YEAR == 365.25
    assert units.years_between(date(2024, 1, 1), date(2025, 1, 1)) == pytest.approx(366 / 365.25)
    assert units.years_between(date(2025, 1, 1), date(2024, 1, 1)) < 0


# --- product quantities ---------------------------------------------------------


def test_nutrient_to_product_divides_by_the_grade() -> None:
    assert units.nutrient_to_product_kg(50.0, 25.0) == pytest.approx(200.0)


@pytest.mark.parametrize("grade", [0.5, 25.0, 33.33, 100.0])
def test_product_quantity_round_trip(grade: float) -> None:
    product = units.nutrient_to_product_kg(87.5, grade)
    assert units.product_kg_to_nutrient(product, grade) == pytest.approx(87.5, rel=1e-12)


@pytest.mark.parametrize("grade", [0.0, -1.0, 100.5])
def test_nutrient_to_product_rejects_an_impossible_grade(grade: float) -> None:
    with pytest.raises(ValueError, match="grade"):
        units.nutrient_to_product_kg(50.0, grade)


def test_product_to_nutrient_accepts_a_zero_grade() -> None:
    assert units.product_kg_to_nutrient(200.0, 0.0) == 0.0


@pytest.mark.parametrize("grade", [-1.0, 100.5])
def test_product_to_nutrient_rejects_an_impossible_grade(grade: float) -> None:
    with pytest.raises(ValueError, match="grade"):
        units.product_kg_to_nutrient(200.0, grade)


def test_liquid_kg_to_litres_uses_the_density() -> None:
    assert units.kg_to_litres(250.0, 1.25) == pytest.approx(200.0)


@pytest.mark.parametrize("density", [0.8, 1.0, 1.33])
def test_liquid_round_trip(density: float) -> None:
    litres = units.kg_to_litres(123.4, density)
    assert units.litres_to_kg(litres, density) == pytest.approx(123.4, rel=1e-12)


@pytest.mark.parametrize("density", [0.0, -1.0])
def test_liquid_conversion_rejects_a_bad_density(density: float) -> None:
    with pytest.raises(ValueError, match="density"):
        units.kg_to_litres(1.0, density)
    with pytest.raises(ValueError, match="density"):
        units.litres_to_kg(1.0, density)


def test_grades_fit_in_one_hundred_percent() -> None:
    assert units.grades_fit_in_product([46.0, 0.0, 0.0, 0.0])
    # Sums to exactly 100 on the label, slightly over in binary floats.
    assert units.grades_fit_in_product([33.33, 33.33, 33.34])
    assert not units.grades_fit_in_product([60.0, 30.0, 20.0])


@pytest.mark.parametrize(
    ("convert", "args"),
    [
        (units.nutrient_to_product_kg, (100.0, 1e-320)),
        (units.nutrient_to_product_kg, (100.0, 5e-324)),
        (units.product_kg_to_nutrient, (math.inf, 50.0)),
        (units.kg_to_litres, (100.0, 1e-320)),
        (units.kg_to_litres, (100.0, math.inf)),
        (units.kg_to_litres, (100.0, math.nan)),
        (units.litres_to_kg, (1e308, 1e308)),
        (units.litres_to_kg, (100.0, math.inf)),
    ],
)
def test_product_conversions_refuse_a_result_that_is_not_finite(
    convert: Callable[[float, float], float], args: tuple[float, float]
) -> None:
    with pytest.raises(ValueError, match="finite"):
        convert(*args)


def test_converting_a_form_to_itself_keeps_the_exact_value() -> None:
    assert units.convert_form(20.0, NutrientForm.K2O, NutrientForm.K2O) == 20.0


def test_kg_to_lb_and_ha_to_ac_use_the_exact_definitions() -> None:
    assert units.kg_to_lb(0.45359237) == pytest.approx(1.0)
    assert units.ha_to_ac(0.40468564224) == pytest.approx(1.0)
