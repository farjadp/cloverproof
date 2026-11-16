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

from typing import ClassVar, Literal

from cloverproof_engine import explain
from cloverproof_engine.methods.base import NutrientMethod
from cloverproof_engine.models import RecommendationInput
from cloverproof_engine.pack import Pack
from cloverproof_engine.results import (
    ExplainedNumber,
    NutrientResult,
    SplitApplication,
    UsedConstant,
)

KG_N_PER_HA = "kg N/ha"
KG_N = "kg N"


class UnknownPreviousCropError(ValueError):
    pass


class NitrogenMassBalance(NutrientMethod):
    method_id: ClassVar[str] = "n_mass_balance"
    nutrient: ClassVar[str] = "N"

    def calculate(self, inputs: RecommendationInput, pack: Pack) -> NutrientResult:
        cfg = pack.crops[inputs.crop].nitrogen
        previous = cfg.previous_crop_credits.get(inputs.previous_crop)
        if previous is None:
            options = ", ".join(sorted(cfg.previous_crop_credits))
            raise UnknownPreviousCropError(
                f"previous crop {inputs.previous_crop!r} is not in pack "
                f"{pack.id} {pack.version}; options: {options}"
            )

        base = f"crops.{inputs.crop.value}.nitrogen"
        uptake = UsedConstant.of(f"{base}.n_uptake_per_t_grain", cfg.n_uptake_per_t_grain)
        soil_c = UsedConstant.of(f"{base}.soil_n_supply", cfg.soil_n_supply)
        credit_c = UsedConstant.of(
            f"{base}.previous_crop_credits.{inputs.previous_crop}.credit", previous.credit
        )
        efficiency = UsedConstant.of(f"{base}.fertilizer_n_efficiency", cfg.fertilizer_n_efficiency)
        min_c = UsedConstant.of(f"{base}.min_rate", cfg.min_rate)
        max_c = UsedConstant.of(f"{base}.max_rate", cfg.max_rate)
        fractions = [
            UsedConstant.of(f"{base}.splits[{i}].fraction", spec.fraction)
            for i, spec in enumerate(cfg.splits)
        ]

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
        low, high = min_c.value, max_c.value
        bound: Literal["min", "max"] | None = None
        rate = raw
        if raw < low:
            rate, bound = low, "min"
        elif raw > high:
            rate, bound = high, "max"
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
                explanation=explain.previous_crop_credit(previous.label, previous.credit),
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

        count = len(cfg.splits)
        splits: list[SplitApplication] = []
        for index, (spec, fraction_c) in enumerate(zip(cfg.splits, fractions, strict=True), 1):
            fraction = fraction_c.value
            split_rate = rate * fraction
            split_total = split_rate * area
            split_inputs = [*rate_inputs, fraction_c]
            splits.append(
                SplitApplication(
                    stage_label=spec.stage_label,
                    fraction=ExplainedNumber(
                        name=f"split_{index}_fraction",
                        value=fraction,
                        unit="fraction",
                        explanation=explain.split_fraction(
                            index, count, spec.stage_label, spec.fraction
                        ),
                        uses_placeholder=_any_placeholder([fraction_c]),
                    ),
                    rate=ExplainedNumber(
                        name=f"split_{index}_rate",
                        value=split_rate,
                        unit=KG_N_PER_HA,
                        explanation=explain.split_rate(index, fraction, rate, split_rate),
                        uses_placeholder=_any_placeholder(split_inputs),
                    ),
                    total=ExplainedNumber(
                        name=f"split_{index}_total",
                        value=split_total,
                        unit=KG_N,
                        explanation=explain.split_total(index, split_rate, area, split_total),
                        uses_placeholder=_any_placeholder(split_inputs),
                    ),
                )
            )

        return NutrientResult(
            nutrient="N",
            method_id=self.method_id,
            rate=ExplainedNumber(
                name="n_rate",
                value=rate,
                unit=KG_N_PER_HA,
                explanation=explain.n_rate(raw, rate, bound, cfg.min_rate, cfg.max_rate),
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


def _any_placeholder(constants: list[UsedConstant]) -> bool:
    return any(c.is_placeholder for c in constants)
