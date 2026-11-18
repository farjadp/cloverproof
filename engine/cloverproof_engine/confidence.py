"""Rule-based confidence. DRAFT rules, not agronomist-approved.

How it works: start at `high`; every rule that fires sets a cap; the result is
the lowest cap. All rules that fire are returned with a plain-language reason,
so the agronomist sees why. Thresholds come from the pack
(`crops.<crop>.confidence`), never from code.

Rules (each TODO(agronomist): review):
- C1_NO_SOIL_TEST           no soil test                        -> cap medium
  (hard rule, CLAUDE.md #3: without a soil test, at most medium)
- C2_SOIL_TEST_ESTIMATED    soil test source is `estimate`      -> cap medium
- C3_SOIL_TEST_STALE        soil test older than pack
                            `max_soil_test_age_years` at plan_date -> cap medium
- C4_TARGET_YIELD_IMPLAUSIBLE target yield outside pack
                            [target_yield_min, target_yield_max] -> cap low
- C5_RATE_AT_BOUND          N rate was cut to the pack min/max   -> cap medium
- C6_PLACEHOLDER_CONSTANT_USED a constant the method actually used
                            for this recommendation (its
                            `constants_used`) is PLACEHOLDER    -> cap low
  (numbers built on unvalidated constants are never more than low; unused
  pack entries, e.g. credits for other previous crops, and the confidence
  thresholds themselves do not trigger C6). A PLACEHOLDER timing window counts
  too, under the path `crops.<crop>.nitrogen.splits[i].timing`, and so do the
  constants behind a P or K rate. A refused P or K line used none.
- C6_TIMING_WINDOW_MISSING  a line has no timing window (the pack
                            defines no split plan)              -> cap low
- C7_PLACEHOLDER_PRODUCT_RULE_USED a line's matched product relied
                            on a PLACEHOLDER pack product rule (its
                            `rules_used`)                       -> cap low
  (a line with no matched product does not trigger C7, even if rules were read)

Timing windows have no status of their own yet, so every window is PLACEHOLDER: a
plan is `low` with or without a split plan, so removing timing can never raise confidence,
and no plan can reach `high` until windows can be validated.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from cloverproof_engine import explain
from cloverproof_engine.models import RecommendationInput, SoilTestSource
from cloverproof_engine.pack import ConstantStatus, Pack
from cloverproof_engine.units import years_between

if TYPE_CHECKING:
    from cloverproof_engine.results import NutrientResult, PkResults


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def rank(self) -> int:
        return _ORDER.index(self)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.rank < other.rank

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.rank <= other.rank

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.rank > other.rank

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.rank >= other.rank


_ORDER = (Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH)


class ConfidenceRuleHit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    cap: Confidence
    reason: str


def assess(
    inputs: RecommendationInput,
    pack: Pack,
    nitrogen: NutrientResult,
    pk: PkResults | None = None,
) -> tuple[Confidence, list[ConfidenceRuleHit]]:
    """Apply the draft rules. Returns the level and every rule that fired."""
    thresholds = pack.crops[inputs.crop].confidence
    hits: list[ConfidenceRuleHit] = []
    soil = inputs.soil_test

    # C1 — TODO(agronomist): review. Hard rule from CLAUDE.md #3.
    if soil is None:
        hits.append(
            ConfidenceRuleHit(
                rule_id="C1_NO_SOIL_TEST", cap=Confidence.MEDIUM, reason=explain.c1_no_soil_test()
            )
        )
    else:
        # C2 — TODO(agronomist): review.
        if soil.source is SoilTestSource.ESTIMATE:
            hits.append(
                ConfidenceRuleHit(
                    rule_id="C2_SOIL_TEST_ESTIMATED",
                    cap=Confidence.MEDIUM,
                    reason=explain.c2_soil_test_estimated(),
                )
            )
        # C3 — TODO(agronomist): review threshold and whether the cap should be lower.
        age = years_between(soil.sample_date, inputs.plan_date)
        limit = thresholds.max_soil_test_age_years
        if age > limit.value:
            hits.append(
                ConfidenceRuleHit(
                    rule_id="C3_SOIL_TEST_STALE",
                    cap=Confidence.MEDIUM,
                    reason=explain.c3_soil_test_stale(age, limit),
                )
            )

    # C4 — TODO(agronomist): review range.
    low, high = thresholds.target_yield_min, thresholds.target_yield_max
    if not low.value <= inputs.target_yield_t_ha <= high.value:
        hits.append(
            ConfidenceRuleHit(
                rule_id="C4_TARGET_YIELD_IMPLAUSIBLE",
                cap=Confidence.LOW,
                reason=explain.c4_target_yield_implausible(inputs.target_yield_t_ha, low, high),
            )
        )

    # C5 — TODO(agronomist): review.
    if nitrogen.bound_applied is not None:
        hits.append(
            ConfidenceRuleHit(
                rule_id="C5_RATE_AT_BOUND",
                cap=Confidence.MEDIUM,
                reason=explain.c5_rate_at_bound(nitrogen.bound_applied),
            )
        )

    # C6 — TODO(agronomist): review, including the draft caps for timing windows
    # (PLACEHOLDER window -> low, missing window -> low).
    placeholders = [c.path for c in nitrogen.constants_used if c.is_placeholder]
    windows = [line.timing_window for line in nitrogen.splits]
    placeholders += [
        f"crops.{inputs.crop.value}.nitrogen.splits[{i}].timing"
        for i, window in enumerate(windows)
        if window is not None and window.status is ConstantStatus.PLACEHOLDER
    ]
    for line in pk.lines if pk is not None else ():
        if line.outcome == "recommended":
            placeholders += [c.path for c in line.constants_used if c.is_placeholder]
    placeholders = list(dict.fromkeys(placeholders))
    if placeholders:
        hits.append(
            ConfidenceRuleHit(
                rule_id="C6_PLACEHOLDER_CONSTANT_USED",
                cap=Confidence.LOW,
                reason=explain.c6_placeholder_constant_used(pack.id, pack.version, placeholders),
            )
        )

    if any(window is None for window in windows):
        hits.append(
            ConfidenceRuleHit(
                rule_id="C6_TIMING_WINDOW_MISSING",
                cap=Confidence.LOW,
                reason=explain.c6_timing_window_missing(pack.id, pack.version),
            )
        )

    # C7 — TODO(agronomist): review, including the draft cap.
    product_rules = dict.fromkeys(
        rule.path
        for line in nitrogen.splits
        if line.product_match is not None and line.product_match.matched
        for rule in line.product_match.rules_used
        if rule.status is ConstantStatus.PLACEHOLDER
    )
    if product_rules:
        hits.append(
            ConfidenceRuleHit(
                rule_id="C7_PLACEHOLDER_PRODUCT_RULE_USED",
                cap=Confidence.LOW,
                reason=explain.c7_placeholder_product_rule_used(
                    pack.id, pack.version, list(product_rules)
                ),
            )
        )

    level = min((h.cap for h in hits), default=Confidence.HIGH)
    return level, hits
