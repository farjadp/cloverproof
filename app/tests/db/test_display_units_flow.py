"""The lb/ac view through the real routes (S3-ENG-04): a cookie, and no stored change."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient

from cloverproof_app import display_units as du
from cloverproof_app.pdf import render_html

from .conftest import Org, as_owner
from .test_plan_flow import create_plan, latest_rec, new_field, signed_in
from .test_proof_flow import FakeRender, client_for, fake, generate, review  # noqa: F401

pytestmark = pytest.mark.db

HTMX = {"HX-Request": "true"}


def set_units(client: TestClient, csrf: str, plan_url: str, system: str, **extra: Any) -> Any:
    headers = extra.pop("headers", None)
    data = {"csrf_token": csrf, "unit_system": system, **extra}
    return client.post(f"{plan_url}/units", data=data, headers=headers)


def new_plan(db: psycopg.Connection, org: Org) -> tuple[TestClient, str, str]:
    client, csrf = signed_in(db, org.agronomist)
    return client, csrf, create_plan(client, csrf, new_field(client, csrf))


def text_of(page: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())


def stored_state(db: psycopg.Connection, org: Org) -> dict[str, list[tuple[Any, ...]]]:
    """Every stored row a plan view could touch, as text, with its row version (xmin)."""
    tables = {
        "recommendation": "organisation_id",
        "recommendation_line": "organisation_id",
        "review": "organisation_id",
        "crop_plan": "organisation_id",
    }
    state: dict[str, list[tuple[Any, ...]]] = {}
    with as_owner(db):
        for table, column in tables.items():
            state[table] = db.execute(
                f"select t.xmin::text, t::text from {table} t where t.{column} = %s order by 2",
                (org.id,),
            ).fetchall()
    return state


def test_default_is_metric_and_the_choice_is_remembered(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf, plan_url = new_plan(db, org_a)
    assert "Showing lb/ac" not in client.get(plan_url).text

    r = set_units(client, csrf, plan_url, "imperial")
    assert r.status_code == 303 and r.headers["location"] == plan_url
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{du.COOKIE}=imperial;")
    assert "samesite=lax" in cookie.lower() and "path=/" in cookie.lower()

    page = text_of(client.get(plan_url).text)
    assert "Showing lb/ac. Stored values stay in kg/ha." in page
    assert re.search(r"[\d,.]+ lb N/ac \(stored as [\d,.]+ kg N/ha\)", page)
    assert re.search(r"[\d,.]+ lb N \(stored as [\d,.]+ kg N\)", page)

    assert set_units(client, csrf, plan_url, "metric").status_code == 303
    assert "Showing lb/ac" not in client.get(plan_url).text


def test_csrf_is_required(db: psycopg.Connection, org_a: Org) -> None:
    client, _, plan_url = new_plan(db, org_a)
    r = client.post(f"{plan_url}/units", data={"unit_system": "imperial"})
    assert r.status_code == 403
    assert du.COOKIE not in r.headers.get("set-cookie", "")


@pytest.mark.parametrize("value", ["", "IMPERIAL", "us", "<script>"])
def test_unknown_choice_is_refused_and_sets_nothing(
    db: psycopg.Connection, org_a: Org, value: str
) -> None:
    client, csrf, plan_url = new_plan(db, org_a)
    r = set_units(client, csrf, plan_url, value)
    assert r.status_code == 400 and "Choose kg/ha or lb/ac. Nothing was changed." in r.text
    assert du.COOKIE not in r.headers.get("set-cookie", "")


def test_forged_cookie_falls_back_to_metric(db: psycopg.Connection, org_a: Org) -> None:
    client, _, plan_url = new_plan(db, org_a)
    client.cookies.set(du.COOKIE, "forged")
    page = client.get(plan_url)
    assert page.status_code == 200 and "Showing lb/ac" not in page.text
    assert 'value="metric" aria-pressed="true"' in page.text


def test_another_organisations_plan_is_404(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    _, _, plan_url = new_plan(db, org_a)
    other, other_csrf = signed_in(db, org_b.agronomist)
    assert set_units(other, other_csrf, plan_url, "imperial").status_code == 404


def test_switching_keeps_the_review_being_typed(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf, plan_url = new_plan(db, org_a)
    client.get(plan_url)
    r = set_units(client, csrf, plan_url, "imperial", headers=HTMX,
                  decision="reject", reason="  Field was flooded  ")  # fmt: skip
    assert r.status_code == 200
    assert r.headers["set-cookie"].startswith(f"{du.COOKIE}=imperial;")
    assert "Showing lb/ac" in r.text
    assert "  Field was flooded  </textarea>" in r.text
    assert re.search(r'value="reject"\s+checked', r.text)


def test_no_review_or_timer_side_effect_from_switching(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf, plan_url = new_plan(db, org_a)
    client.get(plan_url)
    before = stored_state(db, org_a)
    set_units(client, csrf, plan_url, "imperial", headers=HTMX, decision="approve")
    assert stored_state(db, org_a) == before


def test_viewing_in_imperial_leaves_every_stored_row_identical(
    db: psycopg.Connection, org_a: Org
) -> None:
    client, csrf, plan_url = new_plan(db, org_a)
    rec = latest_rec(client, plan_url)
    r = client.post(
        f"{plan_url}/edit",
        data={"csrf_token": csrf, "recommendation_id": rec, "n_rate": "120",
              "split_rate": ["48", "72"], "reason": "Manure last fall"},
    )  # fmt: skip
    assert r.status_code == 303, r.text
    before = stored_state(db, org_a)
    assert before["recommendation"] and before["recommendation_line"]

    set_units(client, csrf, plan_url, "imperial")
    page = client.get(plan_url).text
    assert 'id="diff"' in page and "lb N/ac" in page
    set_units(client, csrf, plan_url, "metric")
    client.get(plan_url)

    assert stored_state(db, org_a) == before


def test_edit_form_stays_in_kg_and_saves_what_was_typed(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf, plan_url = new_plan(db, org_a)
    set_units(client, csrf, plan_url, "imperial")
    form = client.get(f"{plan_url}/edit").text
    words = text_of(form)
    assert "Type every rate in kg N/ha, even if the plan page is showing lb/ac." in words
    assert "lb N/ac" not in words and "stored as" not in words

    rec = latest_rec(client, plan_url)
    r = client.post(
        f"{plan_url}/edit",
        data={"csrf_token": csrf, "recommendation_id": rec, "n_rate": "120",
              "split_rate": ["48", "72"], "reason": "Local trial"},
    )  # fmt: skip
    assert r.status_code == 303, r.text
    with as_owner(db):
        [row] = db.execute(
            "select result from recommendation where organisation_id = %s"
            " and parent_id is not null and crop_plan_id = %s",
            (org_a.id, UUID(plan_url.rsplit("/", 1)[1])),
        ).fetchall()
    nitrogen = row[0]["nitrogen"]
    assert nitrogen["rate"]["value"] == 120
    assert nitrogen["rate"]["unit"] == "kg N/ha"
    assert [s["rate"]["value"] for s in nitrogen["splits"]] == [48, 72]


def test_proof_stays_in_kg_per_ha_when_viewing_in_imperial(
    db: psycopg.Connection,
    org_a: Org,
    tmp_path: Path,
    fake: FakeRender,  # noqa: F811
) -> None:
    review(db, org_a, org_a.agronomist)
    client, csrf = client_for(db, org_a.agronomist, tmp_path)
    plan_url = f"/plans/{org_a.crop_plan}"
    set_units(client, csrf, plan_url, "imperial")
    assert "The proof PDF always shows the stored kg/ha values, not the lb/ac view." in text_of(
        client.get(plan_url).text
    )
    assert generate(client, csrf, org_a).status_code == 303
    [proof] = fake.inputs
    rendered = render_html(proof)
    assert "kg N/ha" in rendered
    assert "lb N" not in rendered and "lb/ac" not in rendered and "stored as" not in rendered
