"""The fertilizer type presets: file rules and search. No database needed."""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any

import pytest
import yaml

from cloverproof_app.countries import COUNTRIES, DEFAULT_COUNTRY
from cloverproof_app.product_presets import (
    BY_KEY,
    GROUPS,
    PRESETS,
    PRESETS_PATH,
    PresetError,
    load_presets,
    parse_presets,
    search,
)

COMMERCIAL_KEY = ("brand", "vendor", "supplier", "dealer", "retailer", "price", "cost", "sku")


def raw_rows() -> list[dict[str, Any]]:
    return yaml.safe_load(PRESETS_PATH.read_text(encoding="utf-8"))


def names(query: str) -> list[str]:
    return [preset.key for _, presets in search(query) for preset in presets]


def test_the_shipped_file_loads_and_lives_inside_the_package() -> None:
    assert len(load_presets()) == 30
    assert PRESETS_PATH.parent.parent.name == "cloverproof_app"  # the Docker image copies it


def test_the_file_says_what_it_is() -> None:
    header = PRESETS_PATH.read_text(encoding="utf-8").split("- slug:", 1)[0]
    for word in ("PLACEHOLDER", "ai_reviewed", "TODO(agronomist)", "NOT validated", "label"):
        assert word in header


def test_shipped_rows_follow_every_rule() -> None:
    rows = raw_rows()
    keys = [row["slug"] for row in rows]
    assert len(keys) == len(set(keys))
    for row in rows:
        grade = [row[name] for name in ("n", "p2o5", "k2o", "s")]
        known = [value for value in grade if value is not None]
        assert all(0 <= value <= 100 for value in known), row["slug"]
        assert sum(known) <= 100, row["slug"]
        assert row["source"].strip(), row["slug"]
        assert row["url"].startswith("https://"), row["slug"]
        assert row["group"] in GROUPS, row["slug"]
        if row["form"] == "granular":
            assert row["density_kg_per_l"] is None, row["slug"]
        assert not [k for k in row if any(word in k.lower() for word in COMMERCIAL_KEY)]


def test_every_group_is_used() -> None:
    assert {preset.group for preset in PRESETS} == set(GROUPS)


def test_anhydrous_ammonia_is_nitrogen_and_has_no_density() -> None:
    ammonia = BY_KEY["anhydrous_ammonia"]
    assert ammonia.grade == "82-0-0"
    assert ammonia.density_kg_per_l is None and ammonia.needs_density


def test_unknown_values_stay_empty_in_the_form() -> None:
    urea = BY_KEY["urea"].form_values()
    assert urea["n"] == "46" and urea["s"] == "" and urea["density_kg_per_l"] == ""
    uan = BY_KEY["uan_28"].form_values()
    assert uan["product_form"] == "liquid" and uan["density_kg_per_l"] == "1.28"
    assert BY_KEY["ammonium_sulphate"].form_values()["s"] == "24"
    assert BY_KEY["liquid_blend_5_10_15"].form_values()["density_kg_per_l"] == ""


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"n": 101}, "between 0 and 100"),
        ({"k2o": -1}, "between 0 and 100"),
        ({"n": True}, "must be a number"),
        ({"n": None}, "only s may be null"),
        ({"n": 60, "p2o5": 50}, "more than 100"),
        ({"n": 1.234}, "decimal places"),
        ({"source": "  "}, "source must be non-empty"),
        ({"url": ""}, "url must be non-empty"),
        ({"url": "http://example.org"}, "https://"),
        ({"density_kg_per_l": 1.2}, "granular type has no density"),
        ({"group": "Micronutrients"}, "unknown group"),
        ({"form": "powder"}, "granular or liquid"),
        ({"price": 10}, "unknown fields"),
        ({"brand": "Example"}, "unknown fields"),
        ({"vendor": "Example"}, "unknown fields"),
    ],
    ids=str,
)
def test_a_bad_row_stops_the_load(change: dict[str, Any], message: str) -> None:
    rows = copy.deepcopy(raw_rows())
    rows[0].update(change)  # urea: granular
    with pytest.raises(PresetError, match=message):
        parse_presets(rows)


def test_duplicate_keys_stop_the_load() -> None:
    rows = copy.deepcopy(raw_rows())
    rows[1]["slug"] = rows[0]["slug"]
    with pytest.raises(PresetError, match="duplicate preset keys"):
        parse_presets(rows)


def test_search_by_name_grade_group_and_spelling() -> None:
    assert names("urea")[0] == "urea"
    assert names("46-0-0") == ["urea"]
    assert names("21-0-0-24") == ["ammonium_sulphate"]
    assert names("UAN 28%") == ["uan_28"]
    assert "ammonium_thiosulphate" in names("thiosulfate")
    assert set(names("potash")) >= {"muriate_of_potash_red", "potassium_sulphate"}
    assert "monoammonium_phosphate" not in names("1-52")
    assert names("no such fertilizer") == []
    assert len(names("")) == len(PRESETS)


def test_search_keeps_the_group_order() -> None:
    assert [group for group, _ in search("")] == list(GROUPS)


def test_grades_are_decimals_not_floats() -> None:
    assert BY_KEY["liquid_blend_9_9_9"].density_kg_per_l == Decimal("1.257")


def test_country_list_starts_with_canada_and_uses_alpha_2() -> None:
    assert DEFAULT_COUNTRY == "CA" and next(iter(COUNTRIES)) == "CA"
    assert COUNTRIES["CA"] == "Canada" and COUNTRIES["US"] == "United States"
    assert len(COUNTRIES) == 249
    assert all(len(code) == 2 and code.isascii() and code.isupper() for code in COUNTRIES)


def test_a_preset_source_must_say_it_is_unconfirmed() -> None:
    rows = yaml.safe_load(PRESETS_PATH.read_text(encoding="utf-8"))
    rows[0]["source"] = "TEST reference, p. 1"
    with pytest.raises(PresetError, match="source must say"):
        parse_presets(rows)
