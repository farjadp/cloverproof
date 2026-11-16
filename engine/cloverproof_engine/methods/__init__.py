"""Registry of nutrient methods, selected by id from the pack."""

from cloverproof_engine.methods.base import NutrientMethod
from cloverproof_engine.methods.n_mass_balance import NitrogenMassBalance

_REGISTRY: dict[str, NutrientMethod] = {m.method_id: m for m in (NitrogenMassBalance(),)}


def get_method(method_id: str) -> NutrientMethod:
    try:
        return _REGISTRY[method_id]
    except KeyError:
        raise KeyError(f"unknown nutrient method {method_id!r}") from None


__all__ = ["NutrientMethod", "get_method"]
