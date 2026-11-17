"""Engine-vs-final line diff and queue filter parsing (no database)."""

from __future__ import annotations

import copy
from datetime import date
from typing import Any

import pytest

from cloverproof_app import planning
from cloverproof_app.db.migrate import REPO_ROOT
from cloverproof_app.line_diff import diff_lines
from cloverproof_app.review_queue import parse_filters
from cloverproof_engine.loaders import load_pack
from cloverproof_engine.models import Crop, RecommendationInput


@pytest.fixture(scope="module")
def engine_doc() -> dict[str, Any]:
    pack = load_pack(REPO_ROOT / "packs" / "placeholder" / "v0.yaml")
    inputs = RecommendationInput(
        crop=Crop.WHEAT, target_yield_t_ha=5.0, previous_crop="wheat", area_ha=10.0,
        plan_date=date(2027, 2, 1),
    )  # fmt: skip
    return planning.run_engine(inputs, pack)


def edit(doc: dict[str, Any], rate: str, splits: list[str]) -> dict[str, Any]:
    parsed, errors = planning.parse_edit(doc, rate, splits, "Local trial")
    assert parsed is not None, errors
    return planning.edited_document(doc, parsed, "Local trial")


def by_title(lines: list[Any]) -> dict[str, Any]:
    return {line.title: line for line in lines}


def test_unedited_plan_has_no_changes(engine_doc: dict[str, Any]) -> None:
    lines = diff_lines(engine_doc, engine_doc)
    assert [line.changed for line in lines] == [[]] * len(lines)
    assert not any(line.only_in for line in lines)


def test_rate_edit_with_new_shares(engine_doc: dict[str, Any]) -> None:
    final = edit(engine_doc, "120", ["60", "60"])
    lines = by_title(diff_lines(engine_doc, final))
    assert lines["Nitrogen, season"].changed == ["rate", "total"]
    assert lines["Nitrogen, split 1"].changed == ["rate", "share"]
    assert lines["Nitrogen, split 2"].changed == ["rate", "share"]
    assert lines["Plan confidence"].changed == []
    pk = lines["Phosphorus and potassium"]
    assert pk.changed == [] and pk.rule_line  # no soil test: rule line, never editable
    rate = lines["Nitrogen, season"].cells[0]
    assert rate.engine["value"] == engine_doc["nitrogen"]["rate"]["value"]
    assert rate.final["value"] == 120.0 and rate.final["unit"] == "kg N/ha"
    assert rate.final["explanation"].startswith("Set by agronomist: Local trial")


def test_product_and_timing_placeholders(engine_doc: dict[str, Any]) -> None:
    split = by_title(diff_lines(engine_doc, engine_doc))["Nitrogen, split 1"]
    cells = {c.label: c for c in split.cells}
    assert cells["Product"].final == "No product matched yet"
    assert cells["Timing"].final.endswith("(no dates yet)")


def test_split_only_on_one_side(engine_doc: dict[str, Any]) -> None:
    final = copy.deepcopy(engine_doc)
    final["nitrogen"]["splits"] = final["nitrogen"]["splits"][:1]
    lines = by_title(diff_lines(engine_doc, final))
    assert lines["Nitrogen, split 2"].only_in == "engine"
    assert lines["Nitrogen, split 1"].only_in is None


def test_confidence_change_is_a_change(engine_doc: dict[str, Any]) -> None:
    final = copy.deepcopy(engine_doc) | {"confidence": "high"}
    assert by_title(diff_lines(engine_doc, final))["Plan confidence"].changed == ["confidence"]


def test_filters_default_and_fall_back() -> None:
    q = parse_filters({}, ["wheat"])
    assert (q.status, q.confidence, q.crop, q.ai, q.sort, q.q) == (
        "awaiting", "any", "any", "any", "oldest", "",
    )  # fmt: skip
    bad = parse_filters(
        {"status": "x", "confidence": "huge", "crop": "rice", "ai": "?", "sort": "1;--"},
        ["wheat"],
    )
    assert bad == q
    good = parse_filters(
        {"status": "all", "confidence": "low", "crop": "wheat", "ai": "yes", "sort": "farmer",
         "q": "  " + "a" * 150},
        ["wheat"],
    )  # fmt: skip
    assert (good.status, good.confidence, good.crop, good.ai, good.sort) == (
        "all", "low", "wheat", "yes", "farmer",
    )  # fmt: skip
    assert len(good.q) == 100
