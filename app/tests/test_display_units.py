"""Display-only lb/ac view of the plan page (S3-ENG-04). Stored numbers never change."""

from __future__ import annotations

import copy
import html
import re
from types import SimpleNamespace

import pytest

from cloverproof_app import display_units as du
from cloverproof_engine import units

from .support.split_docs import GRANULAR, LIQUID, build, edited, liquid, plan_page, product

KG_PER_LB = 0.45359237  # exact definition, independent of the code under test
HA_PER_ACRE = 0.40468564224


def text_of(page: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())


def expected_pair(value: float, unit: str) -> str:
    shown = du.convert(value, unit, du.IMPERIAL)
    assert shown is not None
    return f"{shown.value:,.1f} {shown.unit} (stored as {value:,.1f} {unit})"


@pytest.mark.parametrize("form", ["N", "P", "P2O5", "K", "K2O", "S", "product"])
def test_rate_uses_the_engine_factor_and_keeps_the_form(form: str) -> None:
    shown = du.convert(134.5, f"kg {form}/ha", du.IMPERIAL)
    assert shown is not None
    assert shown.unit == f"lb {form}/ac"
    assert shown.value == pytest.approx(units.kg_per_ha_to_lb_per_ac(134.5), rel=1e-12)
    assert shown.value == pytest.approx(134.5 / KG_PER_LB * HA_PER_ACRE, rel=1e-12)


def test_the_briefed_example_reads_as_specified() -> None:
    assert expected_pair(134.5, "kg N/ha") == "120.0 lb N/ac (stored as 134.5 kg N/ha)"


@pytest.mark.parametrize("form", ["N", "P2O5", "K2O", "product"])
def test_total_is_converted_to_pounds_and_keeps_the_form(form: str) -> None:
    shown = du.convert(1000, f"kg {form}", du.IMPERIAL)
    assert shown is not None
    assert shown.unit == f"lb {form}"
    assert shown.value == pytest.approx(1000 / KG_PER_LB, rel=1e-12)


def test_rate_round_trips_through_the_engine_inverse() -> None:
    shown = du.convert(134.5, "kg N/ha", du.IMPERIAL)
    assert shown is not None
    assert units.lb_per_ac_to_kg_per_ha(shown.value) == pytest.approx(134.5, rel=1e-12)


@pytest.mark.parametrize(
    "unit", ["kg N/t", "L product/ha", "% N", "fraction", "mg P/kg", "t/ha", "ha", "kg/ha"]
)
def test_units_without_a_rule_stay_as_stored(unit: str) -> None:
    assert du.convert(5, unit, du.IMPERIAL) is None


def test_metric_converts_nothing() -> None:
    assert du.convert(134.5, "kg N/ha", du.METRIC) is None


@pytest.mark.parametrize(
    ("cookies", "expected"),
    [
        ({}, du.METRIC),
        ({du.COOKIE: "metric"}, du.METRIC),
        ({du.COOKIE: "imperial"}, du.IMPERIAL),
        ({du.COOKIE: "IMPERIAL"}, du.METRIC),
        ({du.COOKIE: "<script>"}, du.METRIC),
    ],
)
def test_cookie_is_validated_and_defaults_to_metric(cookies: dict[str, str], expected: str) -> None:
    request = SimpleNamespace(cookies=cookies)
    assert du.from_request(request) == expected  # type: ignore[arg-type]


def test_imperial_page_shows_every_converted_number_with_its_stored_value() -> None:
    doc = build(products=[product(), liquid()])
    n = doc["nitrogen"]
    page = text_of(plan_page(doc, unit_system=du.IMPERIAL))
    numbers = [n["rate"], n["total"], *[c for c in n["components"] if c["unit"] == "kg N/ha"]]
    for split in n["splits"]:
        numbers += [split["rate"], split["total"]]
    for number in numbers:
        assert expected_pair(number["value"], number["unit"]) in page


def test_imperial_page_converts_product_quantities_but_not_litres() -> None:
    for name, products in ((GRANULAR, [product()]), (LIQUID, [liquid()])):
        doc = build(products=products)
        match = doc["nitrogen"]["splits"][0]["product_match"]
        assert match["matched"], name
        page = text_of(plan_page(doc, unit_system=du.IMPERIAL))
        assert expected_pair(match["rate"]["value"], "kg product/ha") in page
        assert expected_pair(match["total"]["value"], "kg product") in page
        if match.get("volume_rate"):
            volume = match["volume_rate"]["value"]
            assert f"{volume:,.1f} L product/ha" in page
            assert f"(stored as {volume:,.1f} L product/ha" not in page


def test_explanations_stay_as_stored_and_the_page_says_so() -> None:
    doc = build()
    page = text_of(plan_page(doc, unit_system=du.IMPERIAL))
    assert " ".join(doc["nitrogen"]["rate"]["explanation"].split()) in page
    assert "Showing lb/ac. Stored values stay in kg/ha." in page
    assert "Explanations are shown as stored, so they still quote kg/ha." in page


def test_the_page_says_what_stays_metric_and_that_the_proof_is_kg_per_ha() -> None:
    page = text_of(plan_page(build(), unit_system=du.IMPERIAL))
    assert "Target yield stays in t/ha" in page
    assert "Field area stays in ha" in page
    assert "The proof PDF always shows the stored kg/ha values." in page
    assert "target 5.0 t/ha" in page and "10.0 ha" in page


def test_approving_in_imperial_names_the_stored_values() -> None:
    sentence = "You approve the stored kg/ha values."
    assert sentence in text_of(plan_page(build(), unit_system=du.IMPERIAL, can_review=True))
    assert sentence not in text_of(plan_page(build(), can_review=True))


def test_metric_page_has_no_imperial_text() -> None:
    page = plan_page(build(products=[product()]))
    assert "lb N" not in page and "stored as" not in page and "Showing lb/ac" not in page
    assert 'value="imperial"' in page  # the control is still offered


def test_control_marks_the_current_choice() -> None:
    pressed = 'value="imperial" aria-pressed="true"'
    assert pressed in plan_page(build(), unit_system=du.IMPERIAL)
    assert pressed not in plan_page(build())


def test_diff_converts_both_sides_and_keeps_the_change_detection() -> None:
    engine = build()
    doc = edited(engine, "120", ["48", "72"])
    page = text_of(plan_page(doc, engine, unit_system=du.IMPERIAL))
    diff = page.split("Engine vs latest version", 1)[1]
    assert expected_pair(engine["nitrogen"]["rate"]["value"], "kg N/ha") in diff
    assert expected_pair(120, "kg N/ha") in diff
    assert expected_pair(48, "kg N/ha") in diff
    assert "Elemental N (lb N/ac, stored as kg N/ha)" in diff
    assert "Rates in lb/ac with the nutrient form written out" in diff
    assert "Changed: rate, total" in diff
    metric = text_of(plan_page(doc, engine))
    assert metric.count("Changed:") == page.count("Changed:")
    assert "Elemental N (kg N/ha)" in metric


def test_rendering_never_changes_the_documents() -> None:
    engine = build(products=[product(), liquid()])
    doc = edited(engine, "120", ["48", "72"])
    engine_before, doc_before = copy.deepcopy(engine), copy.deepcopy(doc)
    plan_page(doc, engine, unit_system=du.IMPERIAL)
    assert engine == engine_before and doc == doc_before
