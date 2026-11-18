"""Agronomist edit: parse_edit / edited_document (no database).

The engine document comes from the real engine and the placeholder pack, so split shares
and placeholder flags are whatever the pack says; tests read them from the document.
"""

from __future__ import annotations

import copy
import math
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from cloverproof_app import planning
from cloverproof_app.main import DEFAULT_PACK_PATH
from cloverproof_engine.loaders import load_pack
from cloverproof_engine.models import Crop, RecommendationInput
from cloverproof_engine.pack import parse_pack
from cloverproof_engine.results import Recommendation

REASON = "Field history: lodging at higher rates"
RESCALED = "Rescaled from the agronomist's N rate using the pack split share"
RESCALED_NO_SPLIT = "Rescaled to the agronomist's N rate; the pack defines no split plan."
# TEST FIXTURE pack and product: not agronomy.
PRODUCT_RULES_PACK = Path(__file__).resolve().parents[2] / "packs/placeholder/v0-product-rules.yaml"
FIXTURE_PRODUCT = {
    "id": "id-fixture",
    "name": "TEST FIXTURE granular N 40",
    "n_pct": 40,
    "p2o5_pct": 0,
    "k2o_pct": 0,
    "s_pct": 0,
    "form": "granular",
    "grade_source": "test fixture",
}


@pytest.fixture(scope="module")
def pack() -> Any:
    return load_pack(DEFAULT_PACK_PATH)


@pytest.fixture(scope="module")
def doc(pack: Any) -> dict[str, Any]:
    inputs = RecommendationInput(
        crop=Crop.WHEAT,
        target_yield_t_ha=6,
        previous_crop="canola",
        area_ha=10,
        plan_date=date(2027, 3, 1),
        soil_test=None,
    )
    result = planning.run_engine(inputs, pack)
    assert len(result["nitrogen"]["splits"]) >= 2, "tests need a pack with two or more splits"
    return result


@pytest.fixture(scope="module")
def no_split_doc(pack: Any) -> dict[str, Any]:
    """An engine document from the same pack with its split plan removed."""
    data = pack.model_dump(mode="json")
    del data["crops"]["wheat"]["nitrogen"]["splits"]
    inputs = RecommendationInput(
        crop=Crop.WHEAT,
        target_yield_t_ha=6,
        previous_crop="canola",
        area_ha=10,
        plan_date=date(2027, 3, 1),
        soil_test=None,
    )
    result = planning.run_engine(inputs, parse_pack(data))
    assert result["nitrogen"]["splits"][0]["timing_window"] is None
    return result


@pytest.fixture(scope="module")
def matched_doc() -> dict[str, Any]:
    """An engine document whose lines each carry a matched product."""
    inputs = RecommendationInput.model_validate(
        {
            "crop": "wheat",
            "target_yield_t_ha": 6,
            "previous_crop": "canola",
            "area_ha": 10,
            "plan_date": "2027-03-01",
            "products": [FIXTURE_PRODUCT],
        }
    )
    result = planning.run_engine(inputs, load_pack(PRODUCT_RULES_PACK))
    assert len(result["nitrogen"]["splits"]) >= 2, "tests need a pack with two or more splits"
    assert all(s["product_match"]["matched"] for s in result["nitrogen"]["splits"])
    return result


def engine_rate(doc: dict[str, Any]) -> float:
    return float(doc["nitrogen"]["rate"]["value"])


def engine_splits(doc: dict[str, Any]) -> list[float]:
    return [float(s["rate"]["value"]) for s in doc["nitrogen"]["splits"]]


def fmt(values: list[float]) -> list[str]:
    return [f"{v:g}" for v in values]


def apply(doc: dict[str, Any], rate: str, splits: list[str]) -> dict[str, Any]:
    edit, errors = planning.parse_edit(doc, rate, splits, REASON)
    assert errors == {}
    assert edit is not None
    return planning.edited_document(doc, edit, REASON)


def test_rate_only_rescales_splits_with_pack_share(doc: dict[str, Any]) -> None:
    new_rate = engine_rate(doc) + 30
    new = apply(doc, f"{new_rate:g}", fmt(engine_splits(doc)))
    n = new["nitrogen"]
    assert n["rate"]["value"] == new_rate
    assert n["rate"]["explanation"] == f"Set by agronomist: {REASON}"
    assert n["rate"]["uses_placeholder"] is False
    assert math.isclose(sum(s["rate"]["value"] for s in n["splits"]), new_rate)
    for old, s in zip(doc["nitrogen"]["splits"], n["splits"], strict=True):
        share = old["fraction"]["value"]
        assert math.isclose(s["rate"]["value"], new_rate * share)
        assert math.isclose(s["fraction"]["value"], share)
        # Rescaled, not typed: no "Set by agronomist", placeholder flag kept from the share.
        for key in ("rate", "total"):
            assert s[key]["explanation"].startswith(RESCALED)
            assert "Set by agronomist" not in s[key]["explanation"]
            assert s[key]["uses_placeholder"] is old["fraction"]["uses_placeholder"]
        assert s["fraction"]["uses_placeholder"] is old["fraction"]["uses_placeholder"]


@pytest.mark.parametrize("new_rate", [100.0, 0.0])
def test_rate_edit_on_a_no_split_line_claims_no_pack_share(
    no_split_doc: dict[str, Any], new_rate: float
) -> None:
    new = apply(no_split_doc, f"{new_rate:g}", fmt(engine_splits(no_split_doc)))
    line = new["nitrogen"]["splits"][0]
    assert line["rate"]["value"] == new_rate
    assert line["rate"]["explanation"] == RESCALED_NO_SPLIT
    assert line["total"]["explanation"].startswith(RESCALED_NO_SPLIT)
    for key in ("rate", "total"):
        assert "split share" not in line[key]["explanation"]


def thirds_doc(pack: Any) -> dict[str, Any]:
    data = pack.model_dump(mode="json")
    nitrogen = data["crops"]["wheat"]["nitrogen"]
    template = nitrogen["splits"][0]
    nitrogen["splits"] = [
        {**copy.deepcopy(template), "stage_label": f"Stage {i} (TEST)"} for i in range(3)
    ]
    for spec in nitrogen["splits"]:
        spec["fraction"]["value"] = 1 / 3
    inputs = RecommendationInput(
        crop=Crop.WHEAT, target_yield_t_ha=6, previous_crop="canola", area_ha=10,
        plan_date=date(2027, 3, 1), soil_test=None,
    )  # fmt: skip
    return planning.run_engine(inputs, parse_pack(data))


def test_rate_edit_adds_a_rounding_note_when_lines_stop_adding_up(pack: Any) -> None:
    doc = thirds_doc(pack)
    new = apply(doc, "100", [repr(v) for v in engine_splits(doc)])  # 33.3 x 3 = 99.9
    for s in new["nitrogen"]["splits"]:
        assert s["rate"]["explanation"].endswith(planning.explain.rounded_for_display())


def test_typed_lines_that_add_up_lose_a_stale_rounding_note(doc: dict[str, Any]) -> None:
    stale = copy.deepcopy(doc)
    suffix = planning.explain.rounded_for_display()
    for s in stale["nitrogen"]["splits"]:
        s["rate"]["explanation"] += suffix
    rates = engine_splits(doc)
    typed = [f"{round(rates[0] + 1, 1):g}", *fmt(rates[1:])]
    new = apply(stale, f"{round(rates[0] + 1, 1) + sum(rates[1:]):g}", typed)
    for s in new["nitrogen"]["splits"]:
        assert not s["rate"]["explanation"].endswith(suffix)


def test_rate_edit_on_an_engine_0_3_0_line_keeps_the_old_text(
    no_split_doc: dict[str, Any],
) -> None:
    # Engine 0.3.0 documents have no `timing_window` key at all.
    old = copy.deepcopy(no_split_doc)
    del old["nitrogen"]["splits"][0]["timing_window"]
    new = apply(old, "100", fmt(engine_splits(old)))
    assert new["nitrogen"]["splits"][0]["rate"]["explanation"].startswith(RESCALED)


def test_partial_split_edit_recomputes_every_fraction(doc: dict[str, Any]) -> None:
    old = engine_splits(doc)
    new_rate = engine_rate(doc) + 30
    typed = [old[0] + 30, *old[1:]]  # first split typed, the rest left as they were
    new = apply(doc, f"{new_rate:g}", fmt(typed))
    splits = new["nitrogen"]["splits"]
    for i, s in enumerate(splits):
        assert math.isclose(s["fraction"]["value"], typed[i] / new_rate)
    assert math.isclose(sum(s["fraction"]["value"] for s in splits), 1.0)

    first, rest = splits[0], splits[1:]
    assert first["rate"]["explanation"] == f"Set by agronomist: {REASON}"
    assert first["rate"]["uses_placeholder"] is False
    assert first["fraction"]["uses_placeholder"] is False
    for orig, s in zip(doc["nitrogen"]["splits"][1:], rest, strict=True):
        # Rate untouched: explanation and flag stay; only the share changed.
        assert s["rate"] == orig["rate"]
        assert "Set by agronomist" not in s["fraction"]["explanation"]
        assert s["fraction"]["uses_placeholder"] is orig["rate"]["uses_placeholder"]


def test_rate_zero_gives_zero_splits_and_shares(doc: dict[str, Any]) -> None:
    new = apply(doc, "0", fmt(engine_splits(doc)))
    n = new["nitrogen"]
    assert n["rate"]["value"] == 0
    assert n["total"]["value"] == 0
    for s in n["splits"]:
        assert s["rate"]["value"] == 0
        assert s["total"]["value"] == 0
        assert s["fraction"]["value"] == 0
        assert "0 kg N/ha" in s["fraction"]["explanation"]


def test_rate_zero_with_typed_zero_splits(doc: dict[str, Any]) -> None:
    zeros = ["0"] * len(engine_splits(doc))
    new = apply(doc, "0", zeros)
    for s in new["nitrogen"]["splits"]:
        assert s["fraction"]["value"] == 0
        assert s["rate"]["explanation"] == f"Set by agronomist: {REASON}"


def test_mismatched_splits_are_an_error(doc: dict[str, Any]) -> None:
    old = engine_splits(doc)
    typed = [old[0] + 10, *old[1:]]
    edit, errors = planning.parse_edit(doc, f"{engine_rate(doc):g}", fmt(typed), REASON)
    assert edit is None
    assert "splits" in errors
    assert "add up to" in errors["splits"]


def test_split_row_count_mismatch_is_an_error(doc: dict[str, Any]) -> None:
    edit, errors = planning.parse_edit(doc, "100", ["100"] * 5, REASON)
    assert edit is None and "form" in errors


def test_nothing_changed_and_missing_reason(doc: dict[str, Any]) -> None:
    edit, errors = planning.parse_edit(doc, f"{engine_rate(doc):g}", fmt(engine_splits(doc)), "")
    assert edit is None
    assert errors["form"] == planning.EDIT_NOTHING_CHANGED
    assert errors["reason"] == planning.EDIT_REASON_MISSING


def test_negative_and_junk_numbers(doc: dict[str, Any]) -> None:
    edit, errors = planning.parse_edit(doc, "-5", ["abc", *fmt(engine_splits(doc))[1:]], REASON)
    assert edit is None
    assert "n_rate" in errors and "split_0" in errors


def test_total_uses_area(doc: dict[str, Any]) -> None:
    new_rate = engine_rate(doc) + 30
    new = apply(doc, f"{new_rate:g}", fmt(engine_splits(doc)))
    area = float(doc["input_snapshot"]["area_ha"])
    assert math.isclose(new["nitrogen"]["total"]["value"], new_rate * area)
    for s in new["nitrogen"]["splits"]:
        assert math.isclose(s["total"]["value"], s["rate"]["value"] * area)


def test_engine_document_is_not_mutated(doc: dict[str, Any]) -> None:
    before = copy.deepcopy(doc)
    apply(doc, f"{engine_rate(doc) + 30:g}", fmt(engine_splits(doc)))
    assert doc == before


def assert_withdrawn(line: dict[str, Any], index: int) -> None:
    match = line["product_match"]
    assert match["matched"] is False
    assert match["code"] == "rate_edited"
    assert match["fitting_products"] == []
    assert match["rules_used"] == []
    assert f"application {index}" in match["explanation"]
    assert "withdrawn" in match["explanation"]


def test_edited_line_loses_its_product_and_unchanged_line_keeps_it(
    matched_doc: dict[str, Any],
) -> None:
    old = engine_splits(matched_doc)
    new_rate = engine_rate(matched_doc) + 30
    new = apply(matched_doc, f"{new_rate:g}", fmt([old[0] + 30, *old[1:]]))
    splits = new["nitrogen"]["splits"]
    assert_withdrawn(splits[0], 1)
    for before, after in zip(matched_doc["nitrogen"]["splits"][1:], splits[1:], strict=True):
        assert after["product_match"] == before["product_match"]
    Recommendation.model_validate(new)


@pytest.mark.parametrize("delta", [30.0, None])
def test_total_rate_rescale_withdraws_every_product(
    matched_doc: dict[str, Any], delta: float | None
) -> None:
    new_rate = 0.0 if delta is None else engine_rate(matched_doc) + delta
    new = apply(matched_doc, f"{new_rate:g}", fmt(engine_splits(matched_doc)))
    for i, line in enumerate(new["nitrogen"]["splits"], 1):
        assert_withdrawn(line, i)
    Recommendation.model_validate(new)


def test_a_line_that_needed_no_n_stops_saying_so_once_edited(
    matched_doc: dict[str, Any],
) -> None:
    source = copy.deepcopy(matched_doc)
    old = engine_splits(source)
    first = source["nitrogen"]["splits"][0]
    first["rate"]["value"] = 0.0
    first["product_match"] = {
        "matched": False,
        "code": "no_n_needed",
        "fitting_products": [],
        "rules_used": [],
        "explanation": "Application 1 needs no N, so no product is named.",
    }
    source["nitrogen"]["rate"]["value"] = sum(old[1:])
    new = apply(source, f"{sum(old):g}", fmt(old))
    assert_withdrawn(new["nitrogen"]["splits"][0], 1)


def test_edit_adds_no_product_outcome_to_a_document_without_one(doc: dict[str, Any]) -> None:
    new = apply(doc, f"{engine_rate(doc) + 30:g}", fmt(engine_splits(doc)))
    assert all("product_match" not in s for s in new["nitrogen"]["splits"])


def test_pack_limits_come_from_the_pack(pack: Any) -> None:
    cfg = pack.crops[Crop.WHEAT].nitrogen
    low, high = planning.n_rate_limits(pack, "wheat")
    assert (low.value, high.value) == (cfg.min_rate.value, cfg.max_rate.value)
    assert planning.outside_limits(high.value + 1, (low, high))
    assert not planning.outside_limits(high.value, (low, high))
    assert planning.outside_limits(low.value - 1, (low, high))
