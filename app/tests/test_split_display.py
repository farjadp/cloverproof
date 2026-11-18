"""Timing status and product outcome per N line: plan page and engine-vs-final diff.

Documents come from the engine with the placeholder test packs (synthetic TEST products).
"""

from __future__ import annotations

import copy
import html
import re
from pathlib import Path
from typing import Any

from cloverproof_app import split_display
from cloverproof_app.line_diff import diff_lines
from cloverproof_engine import explain

from .support.split_docs import (
    GRANULAR,
    LIQUID,
    NO_SPLITS,
    SPLITS,
    build,
    edited,
    liquid,
    old_document,
    plan_page,
    product,
    sulphur_pack,
)

NO_TIMING = "No timing set: the pack has no split plan"
RULE_WARNING = "Selected by a PLACEHOLDER pack rule, not validated"
WITHDRAWN = "Any product outcome withdrawn: the N rate was edited"
UNCHOSEN = "Products the pack rules did not choose between"
OTHERS = [product("TEST other A"), product("TEST other B")]
NEW_WORDING = (NO_TIMING, RULE_WARNING, WITHDRAWN, UNCHOSEN, "No product matched", "Grade source")


def text_of(markup: str) -> str:
    body = re.sub(r"<(style|script).*?</\1>", " ", markup, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()


def page(doc: dict[str, Any], engine: dict[str, Any] | None = None) -> str:
    return text_of(plan_page(doc, engine))


def squash(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def cells(engine: dict[str, Any], final: dict[str, Any], title: str) -> dict[str, Any]:
    line = next(x for x in diff_lines(engine, final) if x.title == title)
    return {c.label: c for c in line.cells}


# --- timing and line explanation ----------------------------------------------------


def test_split_line_shows_pack_timing_status_and_explanation() -> None:
    doc = build(SPLITS)
    markup = plan_page(doc)
    text = text_of(markup)
    for split in doc["nitrogen"]["splits"]:
        assert f"Timing {split['timing_window']['label']} Placeholder" in text
        assert squash(split["explanation"]) in text
    assert NO_TIMING not in text


def test_no_split_line_says_no_timing_is_set() -> None:
    doc = build(NO_SPLITS)
    text = page(doc)
    assert f"Timing {NO_TIMING}" in text
    assert squash(doc["nitrogen"]["splits"][0]["explanation"]) in text


def test_share_keeps_one_decimal_like_the_engine_text() -> None:
    doc = build(SPLITS)
    splits = doc["nitrogen"]["splits"]
    splits[0]["fraction"]["value"] = 0.125
    splits[1]["fraction"]["value"] = 0.875
    markup = plan_page(doc)
    assert f'<span class="value">{explain.pct(0.125)}</span>' in markup
    assert '<span class="value">12.5%</span>' in markup
    assert '<span class="value">87.5%</span>' in markup


def test_whole_share_has_no_decimal() -> None:
    doc = build(SPLITS)
    doc["nitrogen"]["splits"][0]["fraction"]["value"] = 0.4
    assert '<span class="value">40%</span>' in plan_page(doc)


# --- product outcome ----------------------------------------------------------------


def test_matched_granular_product() -> None:
    doc = build(products=[product()])
    match = doc["nitrogen"]["splits"][0]["product_match"]
    assert match["matched"] is True
    text = page(doc)
    assert f"Product {GRANULAR} (granular)" in text
    for grade in ("40 % N", "0 % P2O5", "0 % K2O", "0 % S"):
        assert grade in text
    assert squash(match["grade"]["n"]["explanation"]) in text
    assert f"{match['rate']['value']:,.1f} kg product/ha" in text
    assert squash(match["rate"]["explanation"]) in text
    assert "Grade source: TEST label" in text
    assert RULE_WARNING in text
    assert squash(match["explanation"]) in text
    assert "L product/ha" not in text and "kg S/ha" not in text


def test_matched_liquid_product_shows_litres() -> None:
    doc = build(products=[liquid()])
    match = doc["nitrogen"]["splits"][0]["product_match"]
    text = page(doc)
    assert f"Product {LIQUID} (liquid)" in text
    assert f"{match['volume_rate']['value']:,.1f} L product/ha" in text
    assert squash(match["volume_rate"]["explanation"]) in text


def test_matched_product_with_sulphur_shows_kg_s(tmp_path: Path) -> None:
    doc = build(sulphur_pack(tmp_path), [product(s_pct=5)])
    match = doc["nitrogen"]["splits"][0]["product_match"]
    text = page(doc)
    assert f"{match['sulphur_rate']['value']:,.1f} kg S/ha" in text
    assert "5 % S" in text


def test_rule_warning_only_for_placeholder_rules() -> None:
    doc = build(products=[product()])
    for split in doc["nitrogen"]["splits"]:
        for rule in split["product_match"]["rules_used"]:
            rule["status"] = "VALIDATED"
    assert RULE_WARNING not in page(doc)


def test_not_matched_shows_the_reason_and_no_quantity() -> None:
    doc = build(products=OTHERS)
    outcome = doc["nitrogen"]["splits"][0]["product_match"]
    assert outcome["code"] == "several_fit"
    text = page(doc)
    assert "Product No product matched" in text
    assert squash(outcome["explanation"]) in text
    assert f"{UNCHOSEN}: TEST other A, TEST other B" in text
    assert "kg product/ha" not in text and RULE_WARNING not in text
    assert "recommended product" not in text.lower()
    assert "Fitting products" not in text and "Products that fit" not in text


def test_rate_edit_shows_the_withdrawal_plainly() -> None:
    engine = build(products=[product()])
    final = edited(engine, "120", ["60", "60"])
    assert final["nitrogen"]["splits"][0]["product_match"]["code"] == "rate_edited"
    latest = text_of(plan_page(final).split('id="n-h"', 1)[1])
    assert f"Product {WITHDRAWN}" in latest
    assert squash(final["nitrogen"]["splits"][0]["product_match"]["explanation"]) in latest
    assert "kg product/ha" not in latest and GRANULAR not in latest


def test_document_without_product_outcome_shows_no_product_text() -> None:
    text = page(build(SPLITS))
    assert "No product matched" not in text and "Grade source" not in text


def test_old_document_renders_without_the_new_lines() -> None:
    doc = old_document()
    markup = plan_page(doc)
    text = text_of(markup)
    for wording in NEW_WORDING:
        assert wording not in text, wording
    assert "Timing and product" not in markup
    # Whole-percent shares, as these documents have always been shown.
    assert '<span class="value">12%</span>' in markup
    assert '<span class="value">88%</span>' in markup
    assert '<span class="value">12.5%</span>' not in markup


# --- edited numbers -----------------------------------------------------------------


def test_stored_edit_wording_is_neutral_at_display() -> None:
    neutral = split_display.neutral_edit_text
    assert neutral("Set by agronomist: Wet spring") == "Set by reviewer: Wet spring"
    assert neutral("Rescaled from the agronomist's N rate, keeping this line's current share.") == (
        "Rescaled from the reviewer's N rate, keeping this line's current share."
    )
    assert neutral("Rescaled to the agronomist's N rate; the pack defines no split plan.") == (
        "Rescaled to the reviewer's N rate; the pack defines no split plan."
    )


def test_neutral_edit_text_leaves_the_free_text_reason_alone() -> None:
    neutral = split_display.neutral_edit_text
    stored = "Set by agronomist: Set by agronomist: the agronomist's N rate was high"
    assert neutral(stored) == "Set by reviewer: Set by agronomist: the agronomist's N rate was high"
    assert neutral("Reason: Set by agronomist: x") == "Reason: Set by agronomist: x"


# --- engine vs final diff -----------------------------------------------------------


def test_diff_reads_the_matched_product_name() -> None:
    doc = build(products=[product()])
    cell = cells(doc, doc, "Nitrogen, split 1")["Product"]
    assert cell.engine == GRANULAR and cell.final == GRANULAR and not cell.changed


def test_diff_shows_the_withdrawn_product_as_a_change() -> None:
    engine = build(products=[product()])
    final = edited(engine, "120", ["60", "60"])
    cell = cells(engine, final, "Nitrogen, split 1")["Product"]
    assert (cell.engine, cell.final) == (GRANULAR, "No product matched")
    assert cell.changed
    line = next(x for x in diff_lines(engine, final) if x.title == "Nitrogen, split 1")
    assert "product" in line.changed


def test_diff_not_matched_says_no_product_matched() -> None:
    doc = build(products=OTHERS)
    assert cells(doc, doc, "Nitrogen, split 1")["Product"].final == "No product matched"


def test_diff_timing_uses_the_window_and_its_status() -> None:
    doc = build(SPLITS)
    label = doc["nitrogen"]["splits"][0]["timing_window"]["label"]
    cell = cells(doc, doc, "Nitrogen, split 1")["Timing"]
    assert cell.final == f"{label}, PLACEHOLDER (no dates yet)"


def test_diff_timing_of_a_no_split_line() -> None:
    doc = build(NO_SPLITS)
    assert cells(doc, doc, "Nitrogen, split 1")["Timing"].final == NO_TIMING


def test_diff_of_an_old_document_is_unchanged() -> None:
    doc = old_document()
    split = cells(doc, doc, "Nitrogen, split 1")
    assert split["Product"].final == "No product matched yet"
    assert split["Timing"].final == f"{doc['nitrogen']['splits'][0]['stage_label']} (no dates yet)"
    assert split["Share"].whole_share


def test_diff_page_formats_shares_by_document_generation() -> None:
    new = build(SPLITS)
    new_final = copy.deepcopy(new)
    new_final["nitrogen"]["splits"][0]["fraction"]["value"] = 0.125
    assert '<span class="value">12.5%</span>' in plan_page(new_final, new).split('id="diff"')[1]
    old = old_document()
    assert '<span class="value">12%</span>' in plan_page(old, old).split('id="diff"')[1]
