"""Registry of nutrient methods, selected by id from the pack."""

from typing import Any

from cloverproof_engine.methods._shared import MissingInputError, OutOfScopeError
from cloverproof_engine.methods.base import NutrientMethod
from cloverproof_engine.methods.n_mass_balance import NitrogenMassBalance
from cloverproof_engine.methods.n_yield_price_table import NitrogenYieldPriceTable
from cloverproof_engine.methods.pk_soil_test_table import PkSoilTestTable

_REGISTRY: dict[str, NutrientMethod[Any]] = {
    m.method_id: m for m in (NitrogenMassBalance(), NitrogenYieldPriceTable(), PkSoilTestTable())
}


def get_method(method_id: str) -> NutrientMethod[Any]:
    try:
        return _REGISTRY[method_id]
    except KeyError:
        raise KeyError(f"unknown nutrient method {method_id!r}") from None


__all__ = ["MissingInputError", "NutrientMethod", "OutOfScopeError", "get_method"]
