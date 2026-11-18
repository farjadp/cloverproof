"""Draft confidence rules. Thresholds come from the pack."""

from datetime import date

import pytest

from cloverproof_engine.confidence import Confidence, assess
from cloverproof_engine.methods.n_mass_balance import NitrogenMassBalance
from cloverproof_engine.models import SoilTestSource
from cloverproof_engine.pack import ConstantStatus, Pack, parse_pack
from cloverproof_engine.results import NutrientResult


def _windows_validated(result: NutrientResult) -> NutrientResult:
    """TEST FIXTURE: no engine output can have a validated window yet (see C6)."""
    lines = [
        line.model_copy(
            update={
                "timing_window": line.timing_window.model_copy(
                    update={"status": ConstantStatus.VALIDATED}
                )
            }
        )
        for line in result.splits
    ]
    return result.model_copy(update={"splits": lines})


def _assess(inputs, pack: Pack):
    """The other rules, in isolation from the timing part of C6."""
    result = _windows_validated(NitrogenMassBalance().calculate(inputs, pack))
    return assess(inputs, pack, result)


def _assess_as_built(inputs, pack: Pack):
    return assess(inputs, pack, NitrogenMassBalance().calculate(inputs, pack))


def _ids(hits) -> list[str]:
    return [h.rule_id for h in hits]


def test_order() -> None:
    assert Confidence.LOW < Confidence.MEDIUM < Confidence.HIGH
    assert min(Confidence.HIGH, Confidence.LOW) is Confidence.LOW


def test_high_with_recent_lab_test_and_validated_pack(
    lab_soil_test, make_input, validated_pack
) -> None:
    level, hits = _assess(make_input(soil_test=lab_soil_test()), validated_pack)
    assert level is Confidence.HIGH
    assert hits == []


def test_no_soil_test_caps_at_medium(make_input, validated_pack) -> None:
    level, hits = _assess(make_input(), validated_pack)
    assert level is Confidence.MEDIUM
    assert _ids(hits) == ["C1_NO_SOIL_TEST"]


def test_lab_test_without_values_caps_like_no_test(
    lab_soil_test, make_input, validated_pack
) -> None:
    level, hits = _assess(make_input(soil_test=lab_soil_test(values=[])), validated_pack)
    assert level is Confidence.MEDIUM
    assert _ids(hits) == ["C1_NO_SOIL_TEST"]
    assert "no values" in hits[0].reason


def test_estimate_input_does_not_lift_the_no_test_cap(
    make_input, soil_estimate_data, validated_pack
) -> None:
    level, hits = _assess(make_input(soil_estimate=soil_estimate_data()), validated_pack)
    assert level is Confidence.MEDIUM
    assert _ids(hits) == ["C1_NO_SOIL_TEST"]


def test_estimate_input_does_not_lower_a_lab_test_plan(
    lab_soil_test, make_input, soil_estimate_data, validated_pack
) -> None:
    inputs = make_input(soil_test=lab_soil_test(), soil_estimate=soil_estimate_data())
    level, hits = _assess(inputs, validated_pack)
    assert level is Confidence.HIGH
    assert hits == []


def test_estimated_soil_test_caps_at_medium(lab_soil_test, make_input, validated_pack) -> None:
    inputs = make_input(soil_test=lab_soil_test(source=SoilTestSource.ESTIMATE))
    level, hits = _assess(inputs, validated_pack)
    assert level is Confidence.MEDIUM
    assert _ids(hits) == ["C2_SOIL_TEST_ESTIMATED"]


def test_stale_soil_test_caps_at_medium(lab_soil_test, make_input, validated_pack) -> None:
    # pack threshold 3 years; sample 2023-09-15 vs plan 2027-02-15 = ~3.4 years
    inputs = make_input(soil_test=lab_soil_test(sample_date=date(2023, 9, 15)))
    level, hits = _assess(inputs, validated_pack)
    assert level is Confidence.MEDIUM
    assert _ids(hits) == ["C3_SOIL_TEST_STALE"]


def test_soil_test_just_inside_age_limit(lab_soil_test, make_input, validated_pack) -> None:
    inputs = make_input(soil_test=lab_soil_test(sample_date=date(2024, 3, 1)))
    level, _ = _assess(inputs, validated_pack)
    assert level is Confidence.HIGH


@pytest.mark.parametrize("target", [1.5, 10.5])
def test_implausible_yield_is_low(lab_soil_test, make_input, validated_pack, target: float) -> None:
    level, hits = _assess(
        make_input(target_yield_t_ha=target, soil_test=lab_soil_test()), validated_pack
    )
    assert level is Confidence.LOW
    assert "C4_TARGET_YIELD_IMPLAUSIBLE" in _ids(hits)


def test_rate_at_bound_caps_at_medium(lab_soil_test, make_input, validated_pack) -> None:
    level, hits = _assess(
        make_input(target_yield_t_ha=9.0, soil_test=lab_soil_test()), validated_pack
    )
    assert level is Confidence.MEDIUM
    assert _ids(hits) == ["C5_RATE_AT_BOUND"]


def test_placeholder_pack_caps_at_low(lab_soil_test, make_input, placeholder_pack) -> None:
    level, hits = _assess(make_input(soil_test=lab_soil_test()), placeholder_pack)
    assert level is Confidence.LOW
    assert _ids(hits) == ["C6_PLACEHOLDER_CONSTANT_USED"]


N = "crops.wheat.nitrogen"


def test_unused_placeholder_constant_does_not_fire_c6(
    lab_soil_test, make_input, pack_with_placeholders
) -> None:
    pack = pack_with_placeholders(f"{N}.previous_crop_credits.corn.credit")
    assert pack.has_placeholders
    level, hits = _assess(make_input(previous_crop="canola", soil_test=lab_soil_test()), pack)
    assert level is Confidence.HIGH
    assert hits == []


def test_used_placeholder_constant_fires_c6(
    lab_soil_test, make_input, pack_with_placeholders
) -> None:
    path = f"{N}.previous_crop_credits.canola.credit"
    pack = pack_with_placeholders(path)
    level, hits = _assess(make_input(previous_crop="canola", soil_test=lab_soil_test()), pack)
    assert level is Confidence.LOW
    assert _ids(hits) == ["C6_PLACEHOLDER_CONSTANT_USED"]
    assert path in hits[0].reason


def test_placeholder_split_fraction_fires_c6(
    lab_soil_test, make_input, pack_with_placeholders
) -> None:
    pack = pack_with_placeholders(f"{N}.splits[1].fraction")
    level, hits = _assess(make_input(soil_test=lab_soil_test()), pack)
    assert level is Confidence.LOW
    assert _ids(hits) == ["C6_PLACEHOLDER_CONSTANT_USED"]


def test_placeholder_confidence_threshold_alone_does_not_fire_c6(
    lab_soil_test, make_input, pack_with_placeholders
) -> None:
    # C6 looks at constants that feed the recommended numbers, not the
    # confidence thresholds. TODO(agronomist): confirm (see report).
    pack = pack_with_placeholders("crops.wheat.confidence.target_yield_max")
    level, hits = _assess(make_input(soil_test=lab_soil_test()), pack)
    assert level is Confidence.HIGH
    assert hits == []


def test_placeholder_windows_cap_a_validated_pack_at_low(
    lab_soil_test, make_input, validated_pack
) -> None:
    level, hits = _assess_as_built(make_input(soil_test=lab_soil_test()), validated_pack)
    assert level is Confidence.LOW
    assert _ids(hits) == ["C6_PLACEHOLDER_CONSTANT_USED"]
    assert hits[0].cap is Confidence.LOW
    assert f"{N}.splits[0].timing" in hits[0].reason
    assert f"{N}.splits[1].timing" in hits[0].reason


def test_placeholder_constants_and_windows_share_one_c6_hit(
    lab_soil_test, make_input, pack_with_placeholders
) -> None:
    path = f"{N}.soil_n_supply"
    _, hits = _assess_as_built(make_input(soil_test=lab_soil_test()), pack_with_placeholders(path))
    assert _ids(hits) == ["C6_PLACEHOLDER_CONSTANT_USED"]
    assert path in hits[0].reason and f"{N}.splits[0].timing" in hits[0].reason


def test_missing_window_caps_at_low(lab_soil_test, make_input, validated_pack) -> None:
    data = validated_pack.model_dump(mode="json")
    del data["crops"]["wheat"]["nitrogen"]["splits"]
    pack = parse_pack(data)
    level, hits = _assess_as_built(make_input(soil_test=lab_soil_test()), pack)
    assert level is Confidence.LOW  # removing timing must not raise confidence
    assert _ids(hits) == ["C6_TIMING_WINDOW_MISSING"]
    assert hits[0].cap is Confidence.LOW
    assert "no timing window" in hits[0].reason


def test_no_soil_test_never_above_medium(make_input, validated_pack) -> None:
    for target in (3.0, 6.0, 8.0):
        level, _ = _assess(make_input(target_yield_t_ha=target), validated_pack)
        assert level <= Confidence.MEDIUM


def test_every_hit_has_reason_and_cap(make_input, placeholder_pack) -> None:
    _, hits = _assess(make_input(target_yield_t_ha=1.0), placeholder_pack)
    assert len(hits) >= 3
    for h in hits:
        assert h.reason.strip()
        assert isinstance(h.cap, Confidence)
