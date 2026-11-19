"""`/fields/{id}/soil-estimate`, as cp_app with RLS. All points and values are made up."""

from __future__ import annotations

import ast
import html
import re
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest

import cloverproof_app
from cloverproof_app import soil_estimate_view as view
from cloverproof_app.repo import soil_estimates

from .conftest import (
    SOIL_ESTIMATE_CITATION,
    Org,
    as_owner,
    insert,
    locate_field,
    soil_estimate_provenance,
    use_context,
)
from .test_plan_flow import signed_in
from .test_web_auth import build_client, login, with_password

pytestmark = pytest.mark.db

ATTRIBUTION = "SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0"
RETRIEVED = datetime(2026, 11, 16, tzinfo=UTC)
LAT, LON = 12.34567, -76.54321
VALUES: dict[str, tuple[str, float, float, float]] = {
    "phh2o": ("pH", 6.5, 5.5, 7.5),
    "soc": ("mg/kg", 18200, 9100, 30400),
    "nitrogen": ("mg/kg", 1530, 800, 3000),
    "clay": ("%", 22.4, 12.1, 33.3),
    "sand": ("%", 41.6, 25.0, 60.2),
    "silt": ("%", 36.0, 20.5, 50.5),
}


def load(
    db: psycopg.Connection,
    org: Org,
    revision: int,
    *,
    props: tuple[str, ...] = tuple(VALUES),
    depths: tuple[tuple[int, int], ...] = ((0, 5), (5, 15)),
    season: UUID | None = None,
    **overrides: Any,
) -> None:
    """Store rows the way `soil-estimate-load` does."""
    for prop in props:
        unit, value, q05, q95 = VALUES[prop]
        for top, bottom in depths:
            fields: dict[str, Any] = {
                "property": prop,
                "depth_top_cm": top,
                "depth_bottom_cm": bottom,
                "statistic": "mean",
                "value": value,
                "unit": unit,
                "value_q05": q05,
                "value_q95": q95,
                "uncertainty_ratio": 0.9,
                "source": "soilgrids",
                "source_version": "2.0",
                "resolution_m": 250.0,
                "retrieved_at": RETRIEVED,
                "licence": "CC BY 4.0",
                "attribution": ATTRIBUTION,
                "citation": SOIL_ESTIMATE_CITATION,
                "layer_url": soil_estimate_provenance(revision, prop, top, bottom)["layer_url"],
            }
            soil_estimates.insert_estimate(
                db,
                org.id,
                field_id=org.fields[0],
                season_id=season or org.season,
                revision=revision,
                created_by=org.agronomist,
                estimate=soil_estimates.NewEstimate(**(fields | overrides)),
            )


def located(db: psycopg.Connection, org: Org) -> int:
    return locate_field(db, org.id, org.fields[0], LAT, LON)


def url_of(org: Org) -> str:
    return f"/fields/{org.fields[0]}/soil-estimate"


def main_text(page: str) -> str:
    found = re.search(r"<main.*?</main>", page, re.S)
    assert found is not None
    return html.unescape(found.group(0))


def page_of(db: psycopg.Connection, org: Org, query: str = "") -> str:
    client, _ = signed_in(db, org.agronomist)
    r = client.get(url_of(org) + query)
    assert r.status_code == 200
    return main_text(r.text)


# --- access --------------------------------------------------------------------------------


def test_member_sees_values_with_their_source(db: psycopg.Connection, org_a: Org) -> None:
    load(db, org_a, located(db, org_a))
    page = page_of(db, org_a)
    for _, name in view.PROPERTY_NAMES:
        assert name in page
    for text in ("6.5 pH", "5.5\u20137.5 pH", "1,530 mg/kg", "22.4 %", "0.9"):
        assert text in page
    assert "0\u20135 cm" in page and "5\u201315 cm" in page
    for text in ("SoilGrids 2.0", "250 m", "2026-11-16", view.VALUE_NOTE, view.RANGE_NOTE):
        assert text in page
    assert view.RATIO_NOTE in page


def test_every_value_row_has_the_low_badge(db: psycopg.Connection, org_a: Org) -> None:
    load(db, org_a, located(db, org_a))
    page = page_of(db, org_a)
    rows = len(VALUES) * 2
    assert page.count('data-label="Confidence"><span class="badge conf-low">') == rows
    assert "Low confidence" in page
    assert "conf-medium" not in page and "conf-high" not in page


def test_advisor_of_the_org_can_open_it(db: psycopg.Connection, org_a: Org) -> None:
    client, _ = signed_in(db, org_a.staff)
    assert client.get(url_of(org_a)).status_code == 200


def test_farmer_role_cannot_open_it(db: psycopg.Connection, org_a: Org) -> None:
    with as_owner(db):
        user = insert(db, "app_user", email="farmer-a@example.org", display_name="Farmer")
    insert(db, "membership", organisation_id=org_a.id, user_id=user, role="farmer")
    with_password(db, user)
    client = build_client(db)
    assert login(client, "farmer-a@example.org").status_code == 303
    assert client.get(url_of(org_a)).status_code == 403


def test_other_org_gets_404_and_no_values(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    load(db, org_a, located(db, org_a))
    client, _ = signed_in(db, org_b.agronomist)
    r = client.get(url_of(org_a))
    assert r.status_code == 404
    assert "6.5 pH" not in r.text and ATTRIBUTION not in r.text
    assert client.get(f"{url_of(org_a)}?season={org_a.season}").status_code == 404


def test_rls_hides_the_rows_from_another_org(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    load(db, org_a, located(db, org_a))
    use_context(db, org_b.agronomist, org_b.id)
    assert soil_estimates.seasons_for_field(db, org_a.id, org_a.fields[0]) == []
    assert soil_estimates.seasons_for_field(db, org_b.id, org_a.fields[0]) == []


def test_signed_out_is_sent_to_login(db: psycopg.Connection, org_a: Org) -> None:
    client, _ = signed_in(db, org_a.agronomist)
    client.cookies.clear()
    assert client.get(url_of(org_a)).status_code in (303, 401)


def test_field_page_links_here(db: psycopg.Connection, org_a: Org) -> None:
    client, _ = signed_in(db, org_a.agronomist)
    page = client.get(f"/fields/{org_a.fields[0]}").text
    assert f'href="{url_of(org_a)}"' in page and "View soil estimate" in page


# --- seasons -------------------------------------------------------------------------------


def second_season(db: psycopg.Connection, org: Org, label: str = "2028") -> UUID:
    """A newer season used only by the other field of the farm."""
    season = insert(db, "season", organisation_id=org.id, label=label)
    insert(
        db, "field_geometry_version", organisation_id=org.id, field_id=org.fields[1],
        season_id=season, area_ha=5, area_source="manual", created_by=org.agronomist,
    )  # fmt: skip
    return season


def test_one_season_has_no_selector(db: psycopg.Connection, org_a: Org) -> None:
    page = page_of(db, org_a)
    assert "<select" not in page and "2027" in page


def test_default_is_the_season_with_values_and_the_selector_switches(
    db: psycopg.Connection, org_a: Org
) -> None:
    other = second_season(db, org_a)
    load(db, org_a, located(db, org_a))
    client, _ = signed_in(db, org_a.agronomist)
    page = main_text(client.get(url_of(org_a)).text)
    assert "2027 (estimates loaded)" in page and f'value="{other}"' in page
    assert f'value="{org_a.season}" selected' in page and "6.5 pH" in page
    page = main_text(client.get(f"{url_of(org_a)}?season={other}").text)
    assert f'value="{other}" selected' in page and "6.5 pH" not in page
    assert view.NOT_LOADED_TITLE in page


def test_default_opens_the_season_that_needs_the_warning(
    db: psycopg.Connection, org_a: Org
) -> None:
    second_season(db, org_a)
    load(db, org_a, located(db, org_a))
    locate_field(db, org_a.id, org_a.fields[0], 44.0, -80.0)
    page = page_of(db, org_a)
    assert "2027 (location changed)" in page and view.STALE_TITLE in page


def test_season_of_another_org_or_unknown_is_refused(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    client, _ = signed_in(db, org_a.agronomist)
    assert client.get(f"{url_of(org_a)}?season={org_b.season}").status_code == 404
    assert client.get(f"{url_of(org_a)}?season={uuid4()}").status_code == 404
    assert client.get(f"{url_of(org_a)}?season=nonsense").status_code == 422


# --- states --------------------------------------------------------------------------------


def test_no_location(db: psycopg.Connection, org_a: Org) -> None:
    page = page_of(db, org_a)
    assert view.NO_LOCATION_TITLE in page and f'href="/fields/{org_a.fields[0]}/location"' in page
    assert view.NOT_LOADED_TITLE not in page and "<table" not in page


def test_location_without_a_load(db: psycopg.Connection, org_a: Org) -> None:
    located(db, org_a)
    page = page_of(db, org_a)
    assert view.NOT_LOADED_TITLE in page and view.OPERATOR_NOTE in page
    assert view.NOT_LOADED_BODY in page
    assert view.NO_LOCATION_TITLE not in page and "<table" not in page


def test_gaps_say_no_value_for_this_point(db: psycopg.Connection, org_a: Org) -> None:
    revision = located(db, org_a)
    load(db, org_a, revision, props=("nitrogen",))
    load(db, org_a, revision, props=("phh2o",), depths=((0, 5),))
    page = page_of(db, org_a)
    # pH misses one depth; soc, clay, sand and silt miss every depth.
    assert page.count(view.NO_VALUE) == 5
    assert "1,530 mg/kg" in page and view.NOT_LOADED_TITLE not in page


def test_statement_and_soil_test_link_without_any_estimate(
    db: psycopg.Connection, org_a: Org
) -> None:
    page = page_of(db, org_a)
    assert view.STATEMENT in page
    assert f'href="/fields/{org_a.fields[0]}/plans/new#has_soil"' in page
    assert "Add a real soil test" in page


def test_moved_field_warns_and_shows_no_old_value(db: psycopg.Connection, org_a: Org) -> None:
    load(db, org_a, located(db, org_a))
    locate_field(db, org_a.id, org_a.fields[0], 44.0, -80.0)
    page = page_of(db, org_a)
    assert view.STALE_TITLE in page and view.STALE_BODY in page and view.OPERATOR_NOTE in page
    assert "6.5 pH" not in page and "<table" not in page and ATTRIBUTION not in page
    assert view.NOT_LOADED_TITLE not in page


def test_partly_reloaded_field_warns_and_shows_only_current_rows(
    db: psycopg.Connection, org_a: Org
) -> None:
    load(db, org_a, located(db, org_a))
    moved = locate_field(db, org_a.id, org_a.fields[0], 44.0, -80.0)
    load(db, org_a, moved, props=("nitrogen",), value=1700.0)
    page = page_of(db, org_a)
    assert view.STALE_TITLE in page and "1,700 mg/kg" in page
    assert "1,530 mg/kg" not in page and "6.5 pH" not in page
    assert view.NO_VALUE in page


def test_cleared_location_asks_for_one_and_warns(db: psycopg.Connection, org_a: Org) -> None:
    load(db, org_a, located(db, org_a))
    db.execute(
        "update field set location_lat = null, location_lon = null where id = %s",
        (org_a.fields[0],),
    )
    page = page_of(db, org_a)
    assert view.NO_LOCATION_TITLE in page and view.STALE_TITLE in page
    assert view.OPERATOR_NOTE not in page and "6.5 pH" not in page


# --- attribution, wording, privacy ----------------------------------------------------------


def test_attribution_and_citation_once_with_a_reference(db: psycopg.Connection, org_a: Org) -> None:
    load(db, org_a, located(db, org_a))
    page = page_of(db, org_a)
    assert page.count(ATTRIBUTION) == 1 and page.count(SOIL_ESTIMATE_CITATION) == 1
    assert "Licence: CC BY 4.0" in page
    assert 'href="#attribution"' in page and 'id="attribution"' in page


def test_a_different_stored_attribution_is_not_dropped(db: psycopg.Connection, org_a: Org) -> None:
    revision = located(db, org_a)
    load(db, org_a, revision, props=("nitrogen",))
    load(db, org_a, revision, props=("clay",), attribution="Another stored attribution")
    page = page_of(db, org_a)
    assert page.count(ATTRIBUTION) == 1 and page.count("Another stored attribution") == 1


def test_p_and_k_appear_only_in_the_statement(db: psycopg.Connection, org_a: Org) -> None:
    load(db, org_a, located(db, org_a))
    page = page_of(db, org_a)
    assert view.STATEMENT in page
    rest = page.replace(view.STATEMENT, "")
    assert not re.search(r"\b(P|K|P2O5|K2O|P₂O₅|K₂O)\b", rest)
    assert not re.search(r"phosph|potass|recommend", rest, re.I)


def test_page_holds_no_coordinates_or_layer_address(db: psycopg.Connection, org_a: Org) -> None:
    load(db, org_a, located(db, org_a))
    client, _ = signed_in(db, org_a.agronomist)
    page = client.get(url_of(org_a)).text
    assert "12.345" not in page and "76.543" not in page
    assert not re.search(r"latitude|longitude|location_l", page, re.I)
    assert "files.isric.org" not in page


def test_opening_the_page_uses_no_network(
    db: psycopg.Connection, org_a: Org, monkeypatch: pytest.MonkeyPatch
) -> None:
    load(db, org_a, located(db, org_a))
    client, _ = signed_in(db, org_a.agronomist)

    def refuse(*_: object, **__: object) -> None:
        raise AssertionError("the page opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    assert client.get(url_of(org_a)).status_code == 200


def test_page_code_does_not_import_data_sources() -> None:
    root = Path(cloverproof_app.__file__).parent
    for name in ("soil_estimate_view.py", "plan_web.py", "repo/soil_estimates.py"):
        imported: set[str] = set()
        for node in ast.walk(ast.parse((root / name).read_text())):
            if isinstance(node, ast.Import):
                imported |= {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        assert not [m for m in imported if m.split(".")[0] == "data_sources"], name
