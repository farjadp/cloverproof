"""N mass balance (wheat). Expected numbers are derived from the placeholder pack.

Placeholder pack: uptake 30 kg N/t, soil supply 40 kg N/ha, efficiency 0.8,
rate bounds 0..200 kg N/ha, credits canola 0 / soybean 20, splits 0.4 / 0.6.
"""

import pytest

from cloverproof_engine.methods import NutrientMethod, get_method
from cloverproof_engine.methods.n_mass_balance import (
    NitrogenMassBalance,
    UnknownPreviousCropError,
)
from cloverproof_engine.pack import ConstantStatus, Pack


def test_registry_returns_mass_balance(placeholder_pack: Pack) -> None:
    method = get_method(placeholder_pack.crops["wheat"].nitrogen.method)
    assert isinstance(method, NitrogenMassBalance)
    assert isinstance(method, NutrientMethod)
    assert method.nutrient == "N"


def test_unknown_method_id() -> None:
    with pytest.raises(KeyError):
        get_method("does_not_exist")


def test_basic_rate(make_input, placeholder_pack: Pack) -> None:
    # demand 6*30=180; net 180-40-0=140; rate 140/0.8=175
    result = NitrogenMassBalance().calculate(make_input(), placeholder_pack)
    assert result.nutrient == "N"
    assert result.rate.value == pytest.approx(175.0)
    assert result.rate.unit == "kg N/ha"
    assert result.total.value == pytest.approx(175.0 * 40.0)
    assert result.total.unit == "kg N"
    assert result.bound_applied is None


def test_previous_crop_credit(make_input, placeholder_pack: Pack) -> None:
    # net 180-40-20=120; rate 150
    result = NitrogenMassBalance().calculate(make_input(previous_crop="soybean"), placeholder_pack)
    assert result.rate.value == pytest.approx(150.0)


def test_clamped_to_max(make_input, placeholder_pack: Pack) -> None:
    # demand 9*30=270; net 230; raw 287.5 -> 200
    result = NitrogenMassBalance().calculate(make_input(target_yield_t_ha=9.0), placeholder_pack)
    assert result.rate.value == pytest.approx(200.0)
    assert result.bound_applied == "max"
    assert "upper limit" in result.rate.explanation


def test_clamped_to_min(make_input, placeholder_pack: Pack) -> None:
    # demand 1*30=30; net -10; raw -12.5 -> 0
    result = NitrogenMassBalance().calculate(make_input(target_yield_t_ha=1.0), placeholder_pack)
    assert result.rate.value == pytest.approx(0.0)
    assert result.bound_applied == "min"
    assert "lower limit" in result.rate.explanation


def test_splits(make_input, placeholder_pack: Pack) -> None:
    result = NitrogenMassBalance().calculate(make_input(), placeholder_pack)
    assert [s.fraction.value for s in result.splits] == pytest.approx([0.4, 0.6])
    assert [s.rate.value for s in result.splits] == pytest.approx([70.0, 105.0])
    assert [s.total.value for s in result.splits] == pytest.approx([2800.0, 4200.0])
    labels = [s.stage_label for s in result.splits]
    pack_labels = [s.stage_label for s in placeholder_pack.crops["wheat"].nitrogen.splits]
    assert labels == pack_labels
    assert sum(s.rate.value for s in result.splits) == pytest.approx(result.rate.value)


def test_components_are_explained(make_input, placeholder_pack: Pack) -> None:
    result = NitrogenMassBalance().calculate(make_input(), placeholder_pack)
    names = [c.name for c in result.components]
    assert names == [
        "crop_n_demand",
        "soil_n_supply",
        "previous_crop_credit",
        "net_n_requirement",
        "unbounded_rate",
    ]
    values = {c.name: c.value for c in result.components}
    assert values["crop_n_demand"] == pytest.approx(180.0)
    assert values["soil_n_supply"] == pytest.approx(40.0)
    assert values["previous_crop_credit"] == pytest.approx(0.0)
    assert values["net_n_requirement"] == pytest.approx(140.0)
    assert values["unbounded_rate"] == pytest.approx(175.0)


def test_every_number_has_an_explanation(make_input, placeholder_pack: Pack) -> None:
    result = NitrogenMassBalance().calculate(make_input(), placeholder_pack)
    numbers = [result.rate, result.total, *result.components]
    for s in result.splits:
        numbers += [s.fraction, s.rate, s.total]
    for n in numbers:
        assert n.explanation.strip(), n.name
        assert n.unit.strip(), n.name


def test_explanations_flag_placeholders(make_input, placeholder_pack: Pack) -> None:
    result = NitrogenMassBalance().calculate(make_input(), placeholder_pack)
    assert "PLACEHOLDER" in result.components[0].explanation
    assert "PLACEHOLDER" in result.rate.explanation


def test_explanations_cite_source_when_validated(make_input, validated_pack: Pack) -> None:
    result = NitrogenMassBalance().calculate(make_input(), validated_pack)
    assert "PLACEHOLDER" not in result.components[0].explanation
    assert "TEST FIXTURE ONLY" in result.components[0].explanation


def test_unknown_previous_crop(make_input, placeholder_pack: Pack) -> None:
    with pytest.raises(UnknownPreviousCropError) as exc:
        NitrogenMassBalance().calculate(make_input(previous_crop="lupin"), placeholder_pack)
    assert "canola" in str(exc.value)


def test_values_follow_the_pack_not_the_code(make_input, placeholder_pack: Pack) -> None:
    nitrogen = placeholder_pack.crops["wheat"].nitrogen
    changed_n = nitrogen.model_copy(
        update={
            "soil_n_supply": nitrogen.soil_n_supply.model_copy(update={"value": 60.0}),
        }
    )
    crop = placeholder_pack.crops["wheat"].model_copy(update={"nitrogen": changed_n})
    pack = placeholder_pack.model_copy(update={"crops": {"wheat": crop}})
    result = NitrogenMassBalance().calculate(make_input(), pack)
    assert result.rate.value == pytest.approx((180.0 - 60.0) / 0.8)


N = "crops.wheat.nitrogen"


def _numbers(result) -> dict[str, object]:
    found = {n.name: n for n in [result.rate, result.total, *result.components]}
    for s in result.splits:
        found.update({s.fraction.name: s.fraction, s.rate.name: s.rate, s.total.name: s.total})
    return found


def test_constants_used_are_listed(make_input, placeholder_pack: Pack) -> None:
    result = NitrogenMassBalance().calculate(make_input(), placeholder_pack)
    assert [c.path for c in result.constants_used] == [
        f"{N}.n_uptake_per_t_grain",
        f"{N}.soil_n_supply",
        f"{N}.previous_crop_credits.canola.credit",
        f"{N}.fertilizer_n_efficiency",
        f"{N}.min_rate",
        f"{N}.max_rate",
        f"{N}.splits[0].fraction",
        f"{N}.splits[1].fraction",
    ]
    soil = result.constants_used[1]
    assert (soil.value, soil.unit, soil.status, soil.source) == (
        40.0,
        "kg N/ha",
        ConstantStatus.PLACEHOLDER,
        None,
    )


def test_unused_credits_are_not_listed(make_input, placeholder_pack: Pack) -> None:
    result = NitrogenMassBalance().calculate(make_input(previous_crop="soybean"), placeholder_pack)
    credits = [c.path for c in result.constants_used if ".previous_crop_credits." in c.path]
    assert credits == [f"{N}.previous_crop_credits.soybean.credit"]


def test_every_number_uses_placeholder_with_placeholder_pack(
    make_input, placeholder_pack: Pack
) -> None:
    result = NitrogenMassBalance().calculate(make_input(), placeholder_pack)
    assert all(n.uses_placeholder for n in _numbers(result).values())


def test_no_number_uses_placeholder_with_validated_pack(make_input, validated_pack: Pack) -> None:
    result = NitrogenMassBalance().calculate(make_input(), validated_pack)
    assert not any(n.uses_placeholder for n in _numbers(result).values())


def test_placeholder_flag_follows_the_constant_into_derived_numbers(
    make_input, pack_with_placeholders
) -> None:
    pack = pack_with_placeholders(f"{N}.soil_n_supply")
    flags = {
        k: n.uses_placeholder
        for k, n in _numbers(NitrogenMassBalance().calculate(make_input(), pack)).items()
    }
    assert flags == {
        "crop_n_demand": False,
        "soil_n_supply": True,
        "previous_crop_credit": False,
        "net_n_requirement": True,
        "unbounded_rate": True,
        "n_rate": True,
        "n_total": True,
        "split_1_fraction": False,
        "split_1_rate": True,
        "split_1_total": True,
        "split_2_fraction": False,
        "split_2_rate": True,
        "split_2_total": True,
    }


def test_rate_limits_feed_the_rate_but_not_the_components(
    make_input, pack_with_placeholders
) -> None:
    pack = pack_with_placeholders(f"{N}.max_rate")
    numbers = _numbers(NitrogenMassBalance().calculate(make_input(), pack))
    assert numbers["n_rate"].uses_placeholder
    assert numbers["n_total"].uses_placeholder
    assert not numbers["unbounded_rate"].uses_placeholder
    assert not numbers["split_1_fraction"].uses_placeholder


def test_split_fraction_flag_stays_in_its_split(make_input, pack_with_placeholders) -> None:
    pack = pack_with_placeholders(f"{N}.splits[1].fraction")
    numbers = _numbers(NitrogenMassBalance().calculate(make_input(), pack))
    assert not numbers["n_rate"].uses_placeholder
    assert not numbers["split_1_rate"].uses_placeholder
    assert numbers["split_2_fraction"].uses_placeholder
    assert numbers["split_2_rate"].uses_placeholder
    assert numbers["split_2_total"].uses_placeholder


def test_unused_placeholder_credit_flags_nothing(make_input, pack_with_placeholders) -> None:
    pack = pack_with_placeholders(f"{N}.previous_crop_credits.corn.credit")
    result = NitrogenMassBalance().calculate(make_input(previous_crop="canola"), pack)
    assert not any(n.uses_placeholder for n in _numbers(result).values())
