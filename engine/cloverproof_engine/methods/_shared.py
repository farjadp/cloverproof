"""Steps every nitrogen method shares: errors, previous-crop lookup, limits, splits.

No agronomy here: every number comes from the pack or the inputs.
"""

from typing import Literal

from cloverproof_engine import explain
from cloverproof_engine.models import RecommendationInput, WheatClass
from cloverproof_engine.pack import (
    ConstantStatus,
    Pack,
    PackConstant,
    PreviousCrop,
    UnsetConstant,
)
from cloverproof_engine.results import (
    ExplainedNumber,
    SplitApplication,
    TimingWindow,
    UsedConstant,
)

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


class OutOfScopeError(ValueError):
    """The case is outside what the pack (or the engine) covers; no number is given."""


def check_scope(inputs: RecommendationInput, pack: Pack) -> None:
    """Refuse cases the pack's guidance does not cover (pack `scope`), before any number.

    Manure is refused for every pack: no method has a manure N credit yet.
    """
    scope = pack.crops[inputs.crop].scope
    who = f"pack {pack.id} {pack.version}"
    wheat = scope.wheat_class if scope else None
    if wheat is not None:
        if inputs.wheat_class is None:
            raise MissingInputError(
                f"{who} covers {wheat.label}: input wheat_class "
                f"({' | '.join(c.value for c in WheatClass)}) is required"
            )
        if inputs.wheat_class not in wheat.allowed:
            raise OutOfScopeError(
                f"{who}, wheat_class {inputs.wheat_class.value!r}: {wheat.refusal}"
            )
    manure = scope.manure if scope else None
    if manure is not None and inputs.manure_applied is None:
        raise MissingInputError(
            f"{who} needs input manure_applied (true | false): it has no manure N credit, "
            "so it must know that no manure was applied"
        )
    if inputs.manure_applied:
        reason = manure.refusal if manure is not None else explain.manure_not_supported()
        raise OutOfScopeError(f"{who}, manure_applied true: {reason}")


def scope_sentences(inputs: RecommendationInput, pack: Pack) -> str:
    """What the N rate assumes about scope, for the rate explanation ("" if nothing)."""
    scope = pack.crops[inputs.crop].scope
    parts: list[str] = []
    if scope is not None and scope.wheat_class is not None:
        parts.append(explain.wheat_class_scope(scope.wheat_class.label))
    if inputs.manure_applied is False:
        parts.append(explain.assumes_no_manure())
    return "".join(f" {p}" for p in parts)


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
        needs = (
            f" It needs an input the engine does not take yet: {entry.needs_input}."
            if (entry.needs_input)
            else ""
        )
        raise PackValueNotSetError(
            f"pack {pack.id} {pack.version}: the N credit after {inputs.previous_crop!r} "
            f"({entry.label}) is not set yet ({path}); the agronomist must set it "
            f"before the engine can recommend N after this crop.{needs}"
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
    """Split the final rate by the pack fractions. Returns the lines and fractions used.

    A pack with no split plan gives one full-rate line with no timing window.

    Rates are exact (rate x pack fraction): no pack has a rounding rule, so nothing is
    rounded and no residual is moved between lines (engine choice, not from a source).
    TODO(agronomist): say whether split rates should be rounded, and to what step
    (docs/agronomist-todo.md #21).
    """
    cfg = pack.crops[inputs.crop].nitrogen
    specs = cfg.splits
    if specs is None:
        return [_single_line(inputs, pack, rate, rate_inputs)], []
    base = f"crops.{inputs.crop.value}.nitrogen"
    fractions = [
        UsedConstant.of(f"{base}.splits[{i}].fraction", spec.fraction)
        for i, spec in enumerate(specs)
    ]
    window_status = (
        ConstantStatus.VALIDATED if pack.status == "validated" else ConstantStatus.PLACEHOLDER
    )
    area = inputs.area_ha
    count = len(specs)
    splits: list[SplitApplication] = []
    for index, (spec, fraction_c) in enumerate(zip(specs, fractions, strict=True), 1):
        fraction = fraction_c.value
        split_rate = rate * fraction
        split_total = split_rate * area
        split_inputs = [*rate_inputs, fraction_c]
        splits.append(
            SplitApplication(
                stage_label=spec.stage_label,
                timing_window=TimingWindow(
                    label=spec.stage_label, status=window_status, citation=spec.timing_citation
                ),
                explanation=explain.split_line(
                    index, count, spec.stage_label, window_status, spec.timing_citation
                ),
                fraction=ExplainedNumber(
                    name=f"split_{index}_fraction",
                    value=fraction,
                    unit="fraction",
                    explanation=explain.split_fraction(
                        index, count, spec.stage_label, spec.fraction, spec.timing_citation
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


def _single_line(
    inputs: RecommendationInput, pack: Pack, rate: float, rate_inputs: list[UsedConstant]
) -> SplitApplication:
    """The one line of a pack with no split plan. Its share of 1 is structural."""
    crop = inputs.crop.value
    total = rate * inputs.area_ha
    placeholder = any_placeholder(rate_inputs)
    return SplitApplication(
        stage_label=explain.no_split_stage_label(),
        timing_window=None,
        explanation=explain.no_split_line(pack.id, pack.version, crop),
        fraction=ExplainedNumber(
            name="split_1_fraction",
            value=1.0,
            unit="fraction",
            explanation=explain.no_split_fraction(pack.id, pack.version, crop),
            uses_placeholder=False,
        ),
        rate=ExplainedNumber(
            name="split_1_rate",
            value=rate,
            unit=KG_N_PER_HA,
            explanation=explain.split_rate(1, 1.0, rate, rate),
            uses_placeholder=placeholder,
        ),
        total=ExplainedNumber(
            name="split_1_total",
            value=total,
            unit=KG_N,
            explanation=explain.split_total(1, rate, inputs.area_ha, total),
            uses_placeholder=placeholder,
        ),
    )
