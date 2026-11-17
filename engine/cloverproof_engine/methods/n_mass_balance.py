"""Nitrogen mass balance, engine v0.

    crop demand     = target yield x N uptake per tonne
    net requirement = crop demand - soil N supply - previous-crop credit
    unbounded rate  = net requirement / fertilizer N efficiency
    rate            = unbounded rate limited to [min_rate, max_rate]
    total           = rate x area
    split i         = rate x fraction_i (fractions from the pack)

Every constant comes from the pack. TODO(agronomist): review the method form.

Every constant used is recorded in `constants_used` (with its path and label),
and every number says whether a PLACEHOLDER constant feeds it.
"""

from typing import ClassVar

from cloverproof_engine import explain
from cloverproof_engine.methods._shared import (
    KG_N,
    KG_N_PER_HA,
    UnknownPreviousCropError,
    apply_limits,
    build_splits,
    check_scope,
    previous_crop,
    scope_sentences,
)
from cloverproof_engine.methods._shared import (
    any_placeholder as _any_placeholder,
)
from cloverproof_engine.methods.base import NutrientMethod
from cloverproof_engine.models import RecommendationInput
from cloverproof_engine.pack import MassBalanceNitrogen, Pack
from cloverproof_engine.results import ExplainedNumber, NutrientResult, UsedConstant

__all__ = ["NitrogenMassBalance", "UnknownPreviousCropError"]


class NitrogenMassBalance(NutrientMethod):
    method_id: ClassVar[str] = "n_mass_balance"
    nutrient: ClassVar[str] = "N"

    def calculate(self, inputs: RecommendationInput, pack: Pack) -> NutrientResult:
        cfg = pack.crops[inputs.crop].nitrogen
        if not isinstance(cfg, MassBalanceNitrogen):
            raise ValueError(
                f"pack {pack.id} {pack.version} nitrogen method is {cfg.method!r}, "
                f"not {self.method_id!r}"
            )
        check_scope(inputs, pack)
        previous, credit_const, credit_path = previous_crop(inputs, pack, cfg.previous_crop_credits)

        base = f"crops.{inputs.crop.value}.nitrogen"
        uptake = UsedConstant.of(f"{base}.n_uptake_per_t_grain", cfg.n_uptake_per_t_grain)
        soil_c = UsedConstant.of(f"{base}.soil_n_supply", cfg.soil_n_supply)
        credit_c = UsedConstant.of(credit_path, credit_const)
        efficiency = UsedConstant.of(f"{base}.fertilizer_n_efficiency", cfg.fertilizer_n_efficiency)
        min_c = UsedConstant.of(f"{base}.min_rate", cfg.min_rate)
        max_c = UsedConstant.of(f"{base}.max_rate", cfg.max_rate)

        # Which constants feed each number (directly or through earlier steps).
        net_inputs = [uptake, soil_c, credit_c]
        raw_inputs = [*net_inputs, efficiency]
        # Both limits are always compared against, so both feed the final rate.
        rate_inputs = [*raw_inputs, min_c, max_c]

        target = inputs.target_yield_t_ha
        demand = target * uptake.value
        soil = soil_c.value
        credit = credit_c.value
        net = demand - soil - credit
        raw = net / efficiency.value
        rate, bound = apply_limits(raw, min_c, max_c)
        area = inputs.area_ha
        total = rate * area

        components = [
            ExplainedNumber(
                name="crop_n_demand",
                value=demand,
                unit=KG_N_PER_HA,
                explanation=explain.crop_n_demand(target, cfg.n_uptake_per_t_grain, demand),
                uses_placeholder=_any_placeholder([uptake]),
            ),
            ExplainedNumber(
                name="soil_n_supply",
                value=soil,
                unit=KG_N_PER_HA,
                explanation=explain.soil_n_supply(cfg.soil_n_supply),
                uses_placeholder=_any_placeholder([soil_c]),
            ),
            ExplainedNumber(
                name="previous_crop_credit",
                value=credit,
                unit=KG_N_PER_HA,
                explanation=explain.previous_crop_credit(previous.label, credit_const),
                uses_placeholder=_any_placeholder([credit_c]),
            ),
            ExplainedNumber(
                name="net_n_requirement",
                value=net,
                unit=KG_N_PER_HA,
                explanation=explain.net_n_requirement(demand, soil, credit, net),
                uses_placeholder=_any_placeholder(net_inputs),
            ),
            ExplainedNumber(
                name="unbounded_rate",
                value=raw,
                unit=KG_N_PER_HA,
                explanation=explain.unbounded_rate(net, cfg.fertilizer_n_efficiency, raw),
                uses_placeholder=_any_placeholder(raw_inputs),
            ),
        ]

        splits, fractions = build_splits(inputs, pack, rate, rate_inputs)

        return NutrientResult(
            nutrient="N",
            method_id=self.method_id,
            rate=ExplainedNumber(
                name="n_rate",
                value=rate,
                unit=KG_N_PER_HA,
                explanation=explain.n_rate(raw, rate, bound, cfg.min_rate, cfg.max_rate)
                + scope_sentences(inputs, pack),
                uses_placeholder=_any_placeholder(rate_inputs),
            ),
            total=ExplainedNumber(
                name="n_total",
                value=total,
                unit=KG_N,
                explanation=explain.n_total(rate, area, total),
                uses_placeholder=_any_placeholder(rate_inputs),
            ),
            components=components,
            splits=splits,
            bound_applied=bound,
            constants_used=[*rate_inputs, *fractions],
        )
