"""Nitrogen from a yield x price-ratio table (method id `n_yield_price_table`).

For guidance published as a table of N rate by expected yield and N:grain price
ratio (e.g. Ontario Publication 811, Table 4-14, pastry winter wheat; pack ca-on).

    table rate = pack table at (target yield, input n_price_ratio); bilinear
                 interpolation between the bracketing cells; no extrapolation
    rate       = (table rate - previous-crop credit) limited to [min_rate, max_rate]
    total      = rate x area
    split i    = rate x fraction_i (fractions from the pack)

The table values, credits, limits and fractions all come from the pack. Linear
interpolation and refusing to extrapolate are engine choices.
TODO(agronomist): confirm interpolation is acceptable between table cells, and how
to treat yields / price ratios outside the table (today: refuse, no number).
"""

from typing import ClassVar

from cloverproof_engine import explain
from cloverproof_engine.methods._shared import (
    KG_N,
    KG_N_PER_HA,
    MissingInputError,
    OutsideTableError,
    PackValueNotSetError,
    UnknownPreviousCropError,
    any_placeholder,
    apply_limits,
    build_splits,
    previous_crop,
)
from cloverproof_engine.methods.base import NutrientMethod
from cloverproof_engine.models import RecommendationInput
from cloverproof_engine.pack import Pack, YieldPriceTableNitrogen
from cloverproof_engine.results import ExplainedNumber, NutrientResult, UsedConstant

__all__ = [
    "MissingInputError",
    "NitrogenYieldPriceTable",
    "OutsideTableError",
    "PackValueNotSetError",
    "UnknownPreviousCropError",
]


def _bracket(axis: list[float], x: float, name: str, unit: str) -> tuple[int, int, float]:
    """Indices of the cells around x and the weight of the upper one (0..1)."""
    low, high = axis[0], axis[-1]
    if not low <= x <= high:
        raise OutsideTableError(
            f"{name} {x:g} {unit} is outside the pack table ({low:g}-{high:g} {unit}); "
            "no extrapolation"
        )
    for k in range(len(axis)):
        if x == axis[k]:
            return k, k, 0.0
        if x < axis[k]:
            lo = k - 1
            return lo, k, (x - axis[lo]) / (axis[k] - axis[lo])
    raise AssertionError("unreachable: x is within the axis range")


class NitrogenYieldPriceTable(NutrientMethod):
    method_id: ClassVar[str] = "n_yield_price_table"
    nutrient: ClassVar[str] = "N"

    def calculate(self, inputs: RecommendationInput, pack: Pack) -> NutrientResult:
        cfg = pack.crops[inputs.crop].nitrogen
        if not isinstance(cfg, YieldPriceTableNitrogen):
            raise ValueError(
                f"pack {pack.id} {pack.version} nitrogen method is {cfg.method!r}, "
                f"not {self.method_id!r}"
            )
        ratio = inputs.n_price_ratio
        if ratio is None:
            raise MissingInputError(
                f"pack {pack.id} {pack.version} looks N up by price ratio: input "
                "n_price_ratio (cost of N $/kg N / grain price $/kg) is required"
            )
        previous, credit_const, credit_path = previous_crop(inputs, pack, cfg.previous_crop_credits)

        table = cfg.rate_table
        target = inputs.target_yield_t_ha
        j0, j1, ty = _bracket(table.yield_t_ha, target, "target yield", "t/ha")
        i0, i1, tr = _bracket(table.price_ratio, ratio, "price ratio", "kg grain/kg N")

        base = f"crops.{inputs.crop.value}.nitrogen"
        weights: dict[tuple[int, int], float] = {}
        for i, wi in ((i0, 1 - tr), (i1, tr)):
            for j, wj in ((j0, 1 - ty), (j1, ty)):
                if wi * wj > 0:
                    weights[(i, j)] = weights.get((i, j), 0) + wi * wj
        cells = [
            UsedConstant.of(f"{base}.rate_table.rates[{i}][{j}]", table.cell(i, j))
            for (i, j) in weights
        ]
        table_rate = sum(w * table.rates[i][j] for (i, j), w in weights.items())

        credit_c = UsedConstant.of(credit_path, credit_const)
        min_c = UsedConstant.of(f"{base}.min_rate", cfg.min_rate)
        max_c = UsedConstant.of(f"{base}.max_rate", cfg.max_rate)
        raw = table_rate - credit_c.value
        rate, bound = apply_limits(raw, min_c, max_c)
        rate_inputs = [*cells, credit_c, min_c, max_c]
        area = inputs.area_ha
        total = rate * area

        components = [
            ExplainedNumber(
                name="table_n_rate",
                value=table_rate,
                unit=KG_N_PER_HA,
                explanation=explain.table_n_rate(
                    target,
                    ratio,
                    table_rate,
                    table.cell(i0, j0),
                    (table.yield_t_ha[j0], table.yield_t_ha[j1]),
                    (table.price_ratio[i0], table.price_ratio[i1]),
                    [table.rates[i][j] for (i, j) in weights],
                ),
                uses_placeholder=any_placeholder(cells),
            ),
            ExplainedNumber(
                name="previous_crop_credit",
                value=credit_c.value,
                unit=KG_N_PER_HA,
                explanation=(
                    f"{explain.previous_crop_credit(previous.label, credit_const)} "
                    f"{explain.table_rate_after_credit(table_rate, credit_c.value, raw)}"
                ),
                uses_placeholder=any_placeholder([credit_c]),
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
                explanation=explain.n_rate(
                    raw, rate, bound, cfg.min_rate, cfg.max_rate, "yield x price-ratio table"
                ),
                uses_placeholder=any_placeholder(rate_inputs),
            ),
            total=ExplainedNumber(
                name="n_total",
                value=total,
                unit=KG_N,
                explanation=explain.n_total(rate, area, total),
                uses_placeholder=any_placeholder(rate_inputs),
            ),
            components=components,
            splits=splits,
            bound_applied=bound,
            constants_used=[*rate_inputs, *fractions],
        )
