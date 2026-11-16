"""Unit conversions: chemistry and unit facts only (no agronomy)."""

import math

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
