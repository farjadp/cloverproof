"""Soil estimate page helpers: number formats, gaps, credits and the default season."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from cloverproof_app import soil_estimate_view as view
from cloverproof_app.repo.soil_estimates import CurrentEstimate, EstimateSeason


def estimate(**overrides: object) -> CurrentEstimate:
    values: dict[str, object] = {
        "property": "nitrogen",
        "depth_top_cm": 0,
        "depth_bottom_cm": 5,
        "statistic": "mean",
        "value": Decimal("1500"),
        "unit": "mg/kg",
        "value_q05": Decimal("800"),
        "value_q95": Decimal("3000"),
        "uncertainty_ratio": Decimal("1.50"),
        "source": "soilgrids",
        "source_version": "2.0",
        "resolution_m": Decimal("250.0"),
        "retrieved_at": datetime(2026, 11, 16, tzinfo=UTC),
        "licence": "CC BY 4.0",
        "attribution": "Attribution text",
        "citation": "Citation text",
        "layer_url": "https://example.org/layer",
        "field_location_revision": 1,
    }
    return CurrentEstimate(**(values | overrides))  # type: ignore[arg-type]


def season(label: str, current: bool = False, stored: bool = False) -> EstimateSeason:
    return EstimateSeason(uuid4(), label, current, stored or current)


def test_row_formats_each_value_with_its_unit() -> None:
    row = view.estimate_row(estimate())
    assert row.value == "1,500 mg/kg" and row.range == "800\u20133,000 mg/kg"
    assert row.ratio == "1.5" and row.depth == "0\u20135 cm"
    assert (row.source, row.resolution, row.retrieved) == ("SoilGrids 2.0", "250 m", "2026-11-16")


def test_ph_and_percent_keep_one_decimal() -> None:
    assert view.amount(Decimal("6.5"), "pH") == "6.5"
    assert view.amount(Decimal("32"), "%") == "32.0"


def test_a_missing_range_or_ratio_stays_missing() -> None:
    row = view.estimate_row(estimate(value_q05=None, value_q95=None))
    assert row.range is None and row.ratio == "1.5"
    assert view.estimate_row(estimate(uncertainty_ratio=None)).ratio is None


def test_groups_keep_every_property_and_show_gaps() -> None:
    ph = estimate(property="phh2o", unit="pH", value=Decimal("6.5"), value_q05=None, value_q95=None)
    groups = view.property_groups([estimate(), estimate(depth_top_cm=5, depth_bottom_cm=15), ph])
    by_name = {g.name: g.rows for g in groups}
    assert [g.name for g in groups] == [name for _, name in view.PROPERTY_NAMES]
    assert [r.value for r in by_name["Soil pH in water"]] == ["6.5 pH", None]
    assert by_name["Soil pH in water"][1].depth == "5\u201315 cm"
    assert by_name["Clay"] == []


def test_no_estimates_give_no_groups() -> None:
    assert view.property_groups([]) == []


def test_each_distinct_credit_is_kept_once() -> None:
    first = estimate()
    other = replace(first, attribution="Other text")
    assert [c.attribution for c in view.credits_of([first, first, other])] == [
        "Attribution text",
        "Other text",
    ]


def test_default_prefers_usable_values_then_older_rows_then_this_year() -> None:
    today = date(2027, 3, 1)
    newest, this_year = season("2028"), season("2027")
    stored, current = season("2026", stored=True), season("2025", current=True)
    assert view.default_season([newest, this_year, stored, current], today) is current
    assert view.default_season([newest, this_year, stored], today) is stored
    assert view.default_season([newest, this_year], today) is this_year
    assert view.default_season([newest], today) is newest
    assert view.default_season([], today) is None


def test_season_option_says_what_the_season_holds() -> None:
    assert view.season_option(season("2027", current=True)) == "2027 (estimates loaded)"
    assert view.season_option(season("2027", stored=True)) == "2027 (location changed)"
    assert view.season_option(season("2027")) == "2027"
