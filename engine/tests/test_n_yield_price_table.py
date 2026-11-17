"""N rate looked up in a yield x price-ratio table (method `n_yield_price_table`).

All numbers here are TEST FIXTURE ONLY, chosen so the arithmetic is easy:
yields 4 / 6 t/ha, price ratios 5 / 7, rates
    ratio 5: 100 (4 t/ha), 120 (6 t/ha)
    ratio 7:  80 (4 t/ha), 100 (6 t/ha)
credits canola 0, soybean 10, alfalfa not set; bounds 0..200; one split (1.0).
"""

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from cloverproof_engine import recommend
from cloverproof_engine.confidence import Confidence
from cloverproof_engine.methods import get_method
from cloverproof_engine.methods.n_yield_price_table import (
    MissingInputError,
    NitrogenYieldPriceTable,
    OutsideTableError,
    PackValueNotSetError,
)
from cloverproof_engine.pack import Pack, parse_pack


def _const(value: float | None, unit: str) -> dict[str, Any]:
    return {"value": value, "unit": unit, "status": "PLACEHOLDER", "source": None}


def _table_data(**change: object) -> dict[str, Any]:
    table: dict[str, Any] = {
        "unit": "kg N/ha",
        "status": "PLACEHOLDER",
        "source": None,
        "yield_t_ha": [4, 6],
        "price_ratio": [5, 7],
        "rates": [[100, 120], [80, 100]],
    }
    table.update(change)
    return table


def _pack_data(**table_change: object) -> dict[str, Any]:
    return {
        "id": "test-table",
        "version": "v1",
        "status": "placeholder",
        "crops": {
            "wheat": {
                "nitrogen": {
                    "method": "n_yield_price_table",
                    "rate_table": _table_data(**table_change),
                    "min_rate": _const(0, "kg N/ha"),
                    "max_rate": _const(200, "kg N/ha"),
                    "previous_crop_credits": {
                        "canola": {"label": "Canola", "credit": _const(0, "kg N/ha")},
                        "soybean": {"label": "Soybean", "credit": _const(10, "kg N/ha")},
                        "alfalfa": {"label": "Alfalfa", "credit": _const(None, "kg N/ha")},
                    },
                    "splits": [
                        {"stage_label": "Single pass (TEST)", "fraction": _const(1, "fraction")}
                    ],
                },
                "confidence": {
                    "target_yield_min": _const(4, "t/ha"),
                    "target_yield_max": _const(6, "t/ha"),
                    "max_soil_test_age_years": _const(3, "years"),
                },
            }
        },
    }


def price_for_ratio(ratio: float) -> dict[str, Any]:
    """TEST FIXTURE ONLY: not real prices; grain 0.25/kg so N price = ratio * 0.25."""
    return {
        "n_price_per_kg_n": ratio * 0.25,
        "grain_price_per_kg": 0.25,
        "currency": "CAD",
        "source": "TEST FIXTURE",
        "price_date": "2027-01-20",
    }


@pytest.fixture
def table_pack() -> Pack:
    return parse_pack(_pack_data())


def _calc(make_input, pack: Pack, **inputs: Any):
    ratio = inputs.pop("n_price_ratio", 5.0)
    inputs.setdefault("n_price", price_for_ratio(ratio))
    inputs.setdefault("target_yield_t_ha", 4.0)
    return NitrogenYieldPriceTable().calculate(make_input(**inputs), pack)


def test_registered(table_pack: Pack) -> None:
    method = get_method(table_pack.crops["wheat"].nitrogen.method)
    assert isinstance(method, NitrogenYieldPriceTable)
    assert method.nutrient == "N"


@pytest.mark.parametrize(
    ("yield_t_ha", "ratio", "rate"),
    [(4.0, 5.0, 100.0), (6.0, 5.0, 120.0), (4.0, 7.0, 80.0), (6.0, 7.0, 100.0)],
)
def test_grid_points_return_the_cell(make_input, table_pack, yield_t_ha, ratio, rate) -> None:
    result = _calc(make_input, table_pack, target_yield_t_ha=yield_t_ha, n_price_ratio=ratio)
    assert result.rate.value == pytest.approx(rate)
    assert result.bound_applied is None


def test_grid_point_uses_one_cell(make_input, table_pack) -> None:
    result = _calc(make_input, table_pack, target_yield_t_ha=6.0, n_price_ratio=7.0)
    cells = [c.path for c in result.constants_used if ".rate_table." in c.path]
    assert cells == ["crops.wheat.nitrogen.rate_table.rates[1][1]"]


def test_bilinear_interpolation(make_input, table_pack) -> None:
    # yield 5 (halfway), ratio 6 (halfway): (100 + 120 + 80 + 100) / 4 = 100
    result = _calc(make_input, table_pack, target_yield_t_ha=5.0, n_price_ratio=6.0)
    assert result.rate.value == pytest.approx(100.0)
    cells = sorted(c.path for c in result.constants_used if ".rate_table." in c.path)
    assert len(cells) == 4


def test_interpolation_along_yield_only(make_input, table_pack) -> None:
    # ratio 5 exactly; yield 4.5 -> 100 + 0.25 * 20 = 105
    result = _calc(make_input, table_pack, target_yield_t_ha=4.5, n_price_ratio=5.0)
    assert result.rate.value == pytest.approx(105.0)
    table = next(c for c in result.components if c.name == "table_n_rate")
    assert "interpolated" in table.explanation


def test_previous_crop_credit_is_subtracted(make_input, table_pack) -> None:
    result = _calc(make_input, table_pack, previous_crop="soybean")
    assert result.rate.value == pytest.approx(90.0)
    names = [c.name for c in result.components]
    assert names == ["table_n_rate", "previous_crop_credit"]


def test_total_and_single_split(make_input, table_pack) -> None:
    result = _calc(make_input, table_pack, area_ha=10.0)
    assert result.total.value == pytest.approx(1000.0)
    assert len(result.splits) == 1
    assert result.splits[0].rate.value == pytest.approx(100.0)
    assert result.splits[0].stage_label == "Single pass (TEST)"


def test_rate_floors_at_zero_when_the_credit_exceeds_the_table_rate(make_input) -> None:
    data = _pack_data()
    data["crops"]["wheat"]["nitrogen"]["previous_crop_credits"]["soybean"]["credit"]["value"] = 150
    result = _calc(make_input, parse_pack(data), previous_crop="soybean")
    assert result.rate.value == 0
    assert result.bound_applied == "min"
    assert result.total.value == 0
    assert all(s.rate.value == 0 for s in result.splits)


def test_rate_bounds_apply(make_input) -> None:
    data = _pack_data()
    data["crops"]["wheat"]["nitrogen"]["max_rate"]["value"] = 90
    result = _calc(make_input, parse_pack(data))
    assert result.rate.value == pytest.approx(90.0)
    assert result.bound_applied == "max"


@pytest.mark.parametrize(("yield_t_ha", "ratio"), [(3.9, 5.0), (6.1, 5.0), (5.0, 4.9), (5.0, 7.1)])
def test_no_extrapolation_outside_the_table(make_input, table_pack, yield_t_ha, ratio) -> None:
    with pytest.raises(OutsideTableError, match="no extrapolation"):
        _calc(make_input, table_pack, target_yield_t_ha=yield_t_ha, n_price_ratio=ratio)


def test_price_ratio_is_required(make_input, table_pack) -> None:
    with pytest.raises(MissingInputError, match="n_price"):
        NitrogenYieldPriceTable().calculate(make_input(target_yield_t_ha=4.0), table_pack)


def test_unset_credit_refuses_to_calculate(make_input, table_pack) -> None:
    with pytest.raises(PackValueNotSetError, match="alfalfa"):
        _calc(make_input, table_pack, previous_crop="alfalfa")


def test_every_number_is_explained_and_flags_placeholders(make_input, table_pack) -> None:
    result = _calc(make_input, table_pack, target_yield_t_ha=5.0, n_price_ratio=6.0)
    numbers = [result.rate, result.total, *result.components]
    for split in result.splits:
        numbers += [split.fraction, split.rate, split.total]
    for number in numbers:
        assert number.explanation.strip(), number.name
        assert number.uses_placeholder, number.name
    assert "PLACEHOLDER" in result.rate.explanation or "PLACEHOLDER" in next(
        c.explanation for c in result.components if c.name == "table_n_rate"
    )


def test_recommend_end_to_end_is_low_and_n_only(make_input, table_pack) -> None:
    rec = recommend(make_input(target_yield_t_ha=5.0, n_price=price_for_ratio(6.0)), table_pack)
    assert rec.nitrogen.method_id == "n_yield_price_table"
    assert rec.confidence is Confidence.LOW
    rule_ids = {h.rule_id for h in rec.confidence_reasons}
    assert {"C1_NO_SOIL_TEST", "C6_PLACEHOLDER_CONSTANT_USED"} <= rule_ids
    assert rec.phosphorus_potassium.code == "PK_SOIL_TEST_RECOMMENDED"


def test_mass_balance_method_rejects_a_table_pack(make_input, table_pack) -> None:
    with pytest.raises(ValueError, match="n_mass_balance"):
        get_method("n_mass_balance").calculate(make_input(), table_pack)


# --- table schema --------------------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        {"yield_t_ha": [6, 4]},
        {"yield_t_ha": [4, 4]},
        {"price_ratio": [7, 5]},
        {"yield_t_ha": [0, 6]},
        {"rates": [[100, 120]]},
        {"rates": [[100], [80]]},
        {"rates": [[100, -1], [80, 100]]},
        {"unit": "lb N/ac"},
        {"status": "VALIDATED"},
        {"source": "somewhere"},
        {"yield_t_ha": []},
    ],
)
def test_table_schema_rejects(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        parse_pack(_pack_data(**change))


def test_table_cells_count_as_placeholders(table_pack: Pack) -> None:
    assert table_pack.has_placeholders
    cfg = table_pack.crops["wheat"].nitrogen
    cell = cfg.rate_table.cell(1, 0)
    assert cell.value == 80 and cell.unit == "kg N/ha" and cell.is_placeholder


def test_validated_table_needs_a_source() -> None:
    data = copy.deepcopy(_pack_data(status="VALIDATED", source="TEST FIXTURE ONLY"))
    pack = parse_pack(data)
    assert not pack.crops["wheat"].nitrogen.rate_table.cell(0, 0).is_placeholder
