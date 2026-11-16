"""Nitrogen mass balance, engine v0.

    crop demand     = target yield x N uptake per tonne
    net requirement = crop demand - soil N supply - previous-crop credit
    unbounded rate  = net requirement / fertilizer N efficiency
    rate            = unbounded rate limited to [min_rate, max_rate]
    total           = rate x area
    split i         = rate x fraction_i (fractions from the pack)

Every constant comes from the pack. TODO(agronomist): review the method form.
"""

from typing import ClassVar, Literal

from cloverproof_engine import explain
from cloverproof_engine.methods.base import NutrientMethod
from cloverproof_engine.models import RecommendationInput
from cloverproof_engine.pack import Pack
from cloverproof_engine.results import ExplainedNumber, NutrientResult, SplitApplication

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

        target = inputs.target_yield_t_ha
        demand = target * cfg.n_uptake_per_t_grain.value
        soil = cfg.soil_n_supply.value
        credit = previous.credit.value
        net = demand - soil - credit
        raw = net / cfg.fertilizer_n_efficiency.value
        low, high = cfg.min_rate.value, cfg.max_rate.value
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
            ),
            ExplainedNumber(
                name="soil_n_supply",
                value=soil,
                unit=KG_N_PER_HA,
                explanation=explain.soil_n_supply(cfg.soil_n_supply),
            ),
            ExplainedNumber(
                name="previous_crop_credit",
                value=credit,
                unit=KG_N_PER_HA,
                explanation=explain.previous_crop_credit(previous.label, previous.credit),
            ),
            ExplainedNumber(
                name="net_n_requirement",
                value=net,
                unit=KG_N_PER_HA,
                explanation=explain.net_n_requirement(demand, soil, credit, net),
            ),
            ExplainedNumber(
                name="unbounded_rate",
                value=raw,
                unit=KG_N_PER_HA,
                explanation=explain.unbounded_rate(net, cfg.fertilizer_n_efficiency, raw),
            ),
        ]

        count = len(cfg.splits)
        splits: list[SplitApplication] = []
        for index, spec in enumerate(cfg.splits, start=1):
            fraction = spec.fraction.value
            split_rate = rate * fraction
            split_total = split_rate * area
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
                    ),
                    rate=ExplainedNumber(
                        name=f"split_{index}_rate",
                        value=split_rate,
                        unit=KG_N_PER_HA,
                        explanation=explain.split_rate(index, fraction, rate, split_rate),
                    ),
                    total=ExplainedNumber(
                        name=f"split_{index}_total",
                        value=split_total,
                        unit=KG_N,
                        explanation=explain.split_total(index, split_rate, area, split_total),
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
            ),
            total=ExplainedNumber(
                name="n_total",
                value=total,
                unit=KG_N,
                explanation=explain.n_total(rate, area, total),
            ),
            components=components,
            splits=splits,
            bound_applied=bound,
        )
