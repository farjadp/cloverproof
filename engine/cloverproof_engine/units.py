"""Unit and nutrient-form conversions.

Only chemistry and unit-definition facts live here, never agronomy:
- oxide factors are computed from standard atomic weights (IUPAC conventional values),
- lb/ac <-> kg/ha uses the exact international pound and acre definitions,
- mg/kg -> kg/ha needs layer thickness and bulk density as *inputs*; this module
  never assumes a bulk density.

All other engine code must convert through this module.
"""

import math
from collections.abc import Iterable
from datetime import date

from cloverproof_engine.models import NutrientForm, nutrient_of

# Standard atomic weights, g/mol (IUPAC conventional values). Chemistry facts.
ATOMIC_MASS_P = 30.973762
ATOMIC_MASS_K = 39.0983
ATOMIC_MASS_O = 15.999

_MOLAR_MASS_P2O5 = 2 * ATOMIC_MASS_P + 5 * ATOMIC_MASS_O
_MOLAR_MASS_K2O = 2 * ATOMIC_MASS_K + ATOMIC_MASS_O

P2O5_TO_P = 2 * ATOMIC_MASS_P / _MOLAR_MASS_P2O5
P_TO_P2O5 = 1 / P2O5_TO_P
K2O_TO_K = 2 * ATOMIC_MASS_K / _MOLAR_MASS_K2O
K_TO_K2O = 1 / K2O_TO_K

# Exact definitions: 1 lb = 0.45359237 kg; 1 international acre = 4046.8564224 m2;
# 1 ha = 10 000 m2.
_KG_PER_LB = 0.45359237
_HA_PER_ACRE = 4046.8564224 / 10_000
LB_PER_AC_TO_KG_PER_HA = _KG_PER_LB / _HA_PER_ACRE
KG_PER_HA_TO_LB_PER_AC = 1 / LB_PER_AC_TO_KG_PER_HA

# 1 ha of a 1 cm layer = 100 m3; at 1 g/cm3 = 1000 kg/m3 that is 100 000 kg of soil.
# mg/kg * kg soil / 1e6 = kg nutrient, so kg/ha = mg/kg * cm * (g/cm3) * 0.1.
_KG_SOIL_PER_HA_CM_PER_G_CM3 = 100_000
_MG_PER_KG = 1_000_000


def p_to_p2o5(value: float) -> float:
    return value * P_TO_P2O5


def p2o5_to_p(value: float) -> float:
    return value * P2O5_TO_P


def k_to_k2o(value: float) -> float:
    return value * K_TO_K2O


def k2o_to_k(value: float) -> float:
    return value * K2O_TO_K


def lb_per_ac_to_kg_per_ha(value: float) -> float:
    return value * LB_PER_AC_TO_KG_PER_HA


def kg_per_ha_to_lb_per_ac(value: float) -> float:
    return value * KG_PER_HA_TO_LB_PER_AC


def ppm_to_mg_per_kg(value: float) -> float:
    """For soil concentrations by mass, ppm and mg/kg are the same quantity."""
    return value


def mg_per_kg_to_kg_per_ha(
    value_mg_per_kg: float, *, layer_thickness_cm: float, bulk_density_g_cm3: float
) -> float:
    """Convert a soil concentration to an amount per hectare for one soil layer.

    Bulk density is a site property and must be supplied by the caller (from the
    soil test or a pack constant); it is never assumed here.
    """
    if layer_thickness_cm <= 0:
        raise ValueError("layer_thickness_cm must be > 0")
    if bulk_density_g_cm3 <= 0:
        raise ValueError("bulk_density_g_cm3 must be > 0")
    soil_kg_per_ha = layer_thickness_cm * bulk_density_g_cm3 * _KG_SOIL_PER_HA_CM_PER_G_CM3
    return value_mg_per_kg * soil_kg_per_ha / _MG_PER_KG


_TO_ELEMENTAL: dict[NutrientForm, float] = {
    NutrientForm.N: 1,
    NutrientForm.NO3_N: 1,
    NutrientForm.P: 1,
    NutrientForm.P2O5: P2O5_TO_P,
    NutrientForm.K: 1,
    NutrientForm.K2O: K2O_TO_K,
}


def element_of(form: NutrientForm) -> str:
    """The element a form expresses ("N", "P" or "K")."""
    return nutrient_of(form)


_ELEMENTAL_FORM: dict[str, NutrientForm] = {"P": NutrientForm.P, "K": NutrientForm.K}
_OXIDE_FORM: dict[str, NutrientForm] = {"P": NutrientForm.P2O5, "K": NutrientForm.K2O}


def elemental_form(nutrient: str) -> NutrientForm:
    """The element form of "P" or "K"."""
    return _ELEMENTAL_FORM[nutrient]


def oxide_form(nutrient: str) -> NutrientForm:
    """The oxide form of "P" (P2O5) or "K" (K2O)."""
    return _OXIDE_FORM[nutrient]


def to_elemental(value: float, form: NutrientForm) -> float:
    """Express a value given in `form` as the element (P2O5 -> P, K2O -> K)."""
    return value * _TO_ELEMENTAL[form]


def convert_form(value: float, from_form: NutrientForm, to_form: NutrientForm) -> float:
    """Convert between forms of the same element, e.g. P2O5 -> P."""
    if element_of(from_form) != element_of(to_form):
        raise ValueError(f"cannot convert {from_form.value} to {to_form.value}")
    if from_form is to_form:
        return value
    return to_elemental(value, from_form) / _TO_ELEMENTAL[to_form]


# Product grades are mass percentages (unit definition: 100 % = the whole product).
PERCENT = 100


def grades_fit_in_product(grades_pct: Iterable[float]) -> bool:
    """Mass percentages of one product cannot add up to more than the whole product.

    The closeness check keeps a label that sums to exactly 100 from failing on float error.
    """
    total = math.fsum(grades_pct)
    return total <= PERCENT or math.isclose(total, PERCENT)


class NonFiniteQuantityError(ValueError):
    """A product quantity came out as infinity or not-a-number, so it cannot be used."""


def finite_quantity(value: float, what: str) -> float:
    """`value`, or NonFiniteQuantityError when it is not a finite number."""
    if not math.isfinite(value):
        raise NonFiniteQuantityError(f"{what} is not a finite number")
    return value


def _check_grade(grade_pct: float) -> None:
    if not 0 <= grade_pct <= PERCENT:
        raise ValueError(f"grade must be between 0 and {PERCENT} %, got {grade_pct}")


def nutrient_to_product_kg(nutrient_kg: float, grade_pct: float) -> float:
    """Product mass that holds `nutrient_kg`, at a grade in % of the same nutrient form."""
    _check_grade(grade_pct)
    if grade_pct == 0:
        raise ValueError("grade must be > 0: this product does not hold the nutrient")
    fraction = grade_pct / PERCENT
    if fraction == 0:  # a grade so small that it underflows
        raise NonFiniteQuantityError("product mass is not a finite number")
    return finite_quantity(nutrient_kg / fraction, "product mass")


def product_kg_to_nutrient(product_kg: float, grade_pct: float) -> float:
    """Nutrient mass held by `product_kg`, in the form the grade is expressed in."""
    _check_grade(grade_pct)
    return finite_quantity(product_kg * (grade_pct / PERCENT), "nutrient mass")


def _check_density(density_kg_per_l: float) -> None:
    if density_kg_per_l <= 0:
        raise ValueError("density_kg_per_l must be > 0")
    finite_quantity(density_kg_per_l, "density_kg_per_l")


def kg_to_litres(kg: float, density_kg_per_l: float) -> float:
    """Volume of a liquid. The density is a product fact supplied by the caller."""
    _check_density(density_kg_per_l)
    return finite_quantity(kg / density_kg_per_l, "product volume")


def litres_to_kg(litres: float, density_kg_per_l: float) -> float:
    _check_density(density_kg_per_l)
    return finite_quantity(litres * density_kg_per_l, "product mass")


# Julian year (unit definition, IAU): exactly 365.25 days.
DAYS_PER_JULIAN_YEAR = 365.25


def years_between(earlier: date, later: date) -> float:
    """Elapsed time in Julian years (negative if `later` is before `earlier`)."""
    return (later - earlier).days / DAYS_PER_JULIAN_YEAR
