"""Steps every nitrogen method shares: errors, previous-crop lookup, limits, splits.

No agronomy here: every number comes from the pack or the inputs.
"""

from typing import Literal

from cloverproof_engine import explain
from cloverproof_engine.models import RecommendationInput
from cloverproof_engine.pack import Pack, PackConstant, PreviousCrop, UnsetConstant
from cloverproof_engine.results import ExplainedNumber, SplitApplication, UsedConstant

KG_N_PER_HA = "kg N/ha"
KG_N = "kg N"


class UnknownPreviousCropError(ValueError):
    pass


class PackValueNotSetError(ValueError):
    """The pack lists the entry but its value is not set yet (`value: null`)."""


class MissingInputError(ValueError):
    """The pack's method needs an input the caller did not give."""


class OutsideTableError(ValueError):
    """An input lies outside a pack table; the engine never extrapolates."""


def previous_crop(
    inputs: RecommendationInput, pack: Pack, credits: dict[str, PreviousCrop]
) -> tuple[PreviousCrop, PackConstant, str]:
    """The previous-crop entry, its (set) credit constant and the constant's path."""
    entry = credits.get(inputs.previous_crop)
    if entry is None:
        options = ", ".join(sorted(credits))
        raise UnknownPreviousCropError(
            f"previous crop {inputs.previous_crop!r} is not in pack "
            f"{pack.id} {pack.version}; options: {options}"
        )
    path = f"crops.{inputs.crop.value}.nitrogen.previous_crop_credits.{inputs.previous_crop}.credit"
    if isinstance(entry.credit, UnsetConstant):
        raise PackValueNotSetError(
            f"pack {pack.id} {pack.version}: the N credit after {inputs.previous_crop!r} "
            f"({entry.label}) is not set yet ({path}); the agronomist must set it "
            "before the engine can recommend N after this crop"
        )
    return entry, entry.credit, path


def apply_limits(
    raw: float, min_c: UsedConstant, max_c: UsedConstant
) -> tuple[float, Literal["min", "max"] | None]:
    if raw < min_c.value:
        return min_c.value, "min"
    if raw > max_c.value:
        return max_c.value, "max"
    return raw, None


def any_placeholder(constants: list[UsedConstant]) -> bool:
    return any(c.is_placeholder for c in constants)


def build_splits(
    inputs: RecommendationInput,
    pack: Pack,
    rate: float,
    rate_inputs: list[UsedConstant],
) -> tuple[list[SplitApplication], list[UsedConstant]]:
    """Split the final rate by the pack fractions. Returns the splits and fractions used."""
    cfg = pack.crops[inputs.crop].nitrogen
    base = f"crops.{inputs.crop.value}.nitrogen"
    fractions = [
        UsedConstant.of(f"{base}.splits[{i}].fraction", spec.fraction)
        for i, spec in enumerate(cfg.splits)
    ]
    area = inputs.area_ha
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
                    uses_placeholder=any_placeholder([fraction_c]),
                ),
                rate=ExplainedNumber(
                    name=f"split_{index}_rate",
                    value=split_rate,
                    unit=KG_N_PER_HA,
                    explanation=explain.split_rate(index, fraction, rate, split_rate),
                    uses_placeholder=any_placeholder(split_inputs),
                ),
                total=ExplainedNumber(
                    name=f"split_{index}_total",
                    value=split_total,
                    unit=KG_N,
                    explanation=explain.split_total(index, split_rate, area, split_total),
                    uses_placeholder=any_placeholder(split_inputs),
                ),
            )
        )
    return splits, fractions
