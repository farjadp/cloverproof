"""Pack inputs on the plan form (S1-exit D1 / Gap 1): with the ca-on v1 pack the form asks
for wheat class, manure and prices; they land in the input snapshot (CLAUDE.md rule 5).
Engine refusals are form errors (422), never a 500, and nothing is saved."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient

from cloverproof_app.db.migrate import REPO_ROOT

from .conftest import Org
from .test_plan_flow import create_plan, new_field, plan_form
from .test_web_auth import build_client, email_of, login, page_csrf, with_password

pytestmark = pytest.mark.db

CA_ON = REPO_ROOT / "packs" / "ca-on" / "v1.yaml"
CA_ON_V2 = REPO_ROOT / "packs" / "ca-on" / "v2.yaml"
PK_RATE_TEXT = re.compile(r"kg\s*(P2O5|K2O|P₂O₅|K₂O|P\b|K\b)")
PACK_FIELDS = ("wheat_class", "manure_applied", "n_price", "grain_price", "price_source",
               "price_date")  # fmt: skip


def ca_on_client(
    db: psycopg.Connection, user_id: UUID, pack: Path = CA_ON
) -> tuple[TestClient, str]:
    with_password(db, user_id)
    client = build_client(db, pack_path=str(pack))
    assert login(client, email_of(db, user_id)).status_code == 303
    return client, page_csrf(client)


def ca_on_form(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "target_yield": "6",
        "previous_crop": "corn",
        "wheat_class": "pastry",
        "manure_applied": "no",
        "n_price": "1.50",
        "grain_price": "0.25",
        "currency": "CAD",
        "price_source": "SYNTHETIC supplier quote",
        "price_date": "2027-02-15",
    }
    data.update(overrides)
    return data


def post_plan(client: TestClient, csrf: str, field_url: str, **overrides: object):  # type: ignore[no-untyped-def]
    form = client.get(field_url + "/plans/new")
    assert form.status_code == 200
    started = re.search(r'name="started" value="([^"]+)"', form.text).group(1)  # type: ignore[union-attr]
    data = plan_form(**ca_on_form(**overrides)) | {"csrf_token": csrf, "started": started}
    return client.post(field_url + "/plans", data=data)


def plan_count(db: psycopg.Connection, user: UUID) -> int:
    row = db.execute("select count(*) from crop_plan where created_by = %s", (user,)).fetchone()
    assert row is not None
    return int(row[0])


def snapshot(db: psycopg.Connection, plan_url: str) -> dict[str, object]:
    plan_id = UUID(plan_url.rsplit("/", 1)[1])
    row = db.execute(
        "select result -> 'input_snapshot', pack_id from recommendation where crop_plan_id = %s",
        (plan_id,),
    ).fetchone()
    assert row is not None and row[1] == "ca-on"
    return row[0]  # type: ignore[no-any-return]


def test_ca_on_form_shows_pack_inputs(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = ca_on_client(db, org_a.agronomist)
    page = client.get(new_field(client, csrf) + "/plans/new").text
    for name in PACK_FIELDS:
        assert f'name="{name}"' in page, name
    assert 'name="currency"' in page and 'value="CAD"' in page


def test_placeholder_form_has_no_pack_inputs(db: psycopg.Connection, org_a: Org) -> None:
    with_password(db, org_a.agronomist)
    client = build_client(db)
    assert login(client, email_of(db, org_a.agronomist)).status_code == 303
    csrf = page_csrf(client)
    page = client.get(new_field(client, csrf) + "/plans/new").text
    for name in (*PACK_FIELDS, "currency"):
        assert f'name="{name}"' not in page, name
    # The placeholder flow still works without them.
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    assert client.get(plan_url).status_code == 200


def test_ca_on_plan_with_all_inputs(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = ca_on_client(db, org_a.agronomist)
    r = post_plan(client, csrf, new_field(client, csrf))
    assert r.status_code == 303, r.text
    plan_url = r.headers["location"]
    snap = snapshot(db, plan_url)
    assert snap["wheat_class"] == "pastry"
    assert snap["manure_applied"] is False
    price = snap["n_price"]
    assert isinstance(price, dict)
    assert price["n_price_per_kg_n"] == 1.5 and price["grain_price_per_kg"] == 0.25
    assert price["currency"] == "CAD"
    assert price["source"] == "SYNTHETIC supplier quote"
    assert price["price_date"] == "2027-02-15"
    assert price["ratio"] == pytest.approx(6.0)
    page = client.get(plan_url).text
    assert "Recommended N rate" in page
    assert "SYNTHETIC supplier quote" in page and "price ratio 6.00" in page


@pytest.mark.parametrize(
    ("overrides", "field", "message"),
    [
        ({"n_price": ""}, "n_price", "Enter the N price (CAD per kg N)."),
        ({"grain_price": "abc"}, "grain_price", "Enter the wheat price as a number"),
        ({"price_source": "  "}, "price_source", "Say where the prices come from"),
        ({"price_date": ""}, "price_date", "Enter the date of the prices."),
        ({"currency": "C1"}, "currency", "3-letter code"),
        ({"wheat_class": ""}, "wheat_class", "Choose the wheat class"),
        (
            {"manure_applied": ""},
            "manure_applied",
            "Say whether manure or another organic amendment was applied",
        ),
    ],
)
def test_ca_on_missing_or_bad_input_is_422(
    db: psycopg.Connection, org_a: Org, overrides: dict[str, str], field: str, message: str
) -> None:
    client, csrf = ca_on_client(db, org_a.agronomist)
    before = plan_count(db, org_a.agronomist)
    r = post_plan(client, csrf, new_field(client, csrf), **overrides)
    assert r.status_code == 422
    assert message in r.text
    assert f'href="#{field}"' in r.text
    assert plan_count(db, org_a.agronomist) == before


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"wheat_class": "hard"}, "hard wheat is not covered"),
        ({"manure_applied": "yes"}, "this pack has no manure N credit yet"),
        ({"previous_crop": "legume_sod"}, "legume fraction"),
        ({"target_yield": "12"}, "target yield"),
    ],
)
def test_engine_refusal_is_a_form_error(
    db: psycopg.Connection, org_a: Org, overrides: dict[str, str], reason: str
) -> None:
    client, csrf = ca_on_client(db, org_a.agronomist)
    before = plan_count(db, org_a.agronomist)
    r = post_plan(client, csrf, new_field(client, csrf), **overrides)
    assert r.status_code == 422, r.text
    assert "The engine gave no number for this plan" in r.text
    assert reason in r.text
    assert "Nothing was saved." in r.text
    assert "Recommended N rate" not in r.text  # no number when the engine refuses
    assert plan_count(db, org_a.agronomist) == before
    # The typed values come back, so only the wrong one needs changing.
    assert 'value="SYNTHETIC supplier quote"' in r.text


def test_previous_crop_soybean_states_zero_credit(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = ca_on_client(db, org_a.agronomist)
    r = post_plan(client, csrf, new_field(client, csrf), previous_crop="soybean")
    assert r.status_code == 303, r.text
    plan_url = r.headers["location"]
    assert snapshot(db, plan_url)["previous_crop"] == "soybean"
    plan_id = UUID(plan_url.rsplit("/", 1)[1])
    row = db.execute(
        "select result -> 'nitrogen' -> 'components' from recommendation where crop_plan_id = %s",
        (plan_id,),
    ).fetchone()
    assert row is not None
    credit = next(c for c in row[0] if c["name"] == "previous_crop_credit")
    assert credit["value"] == 0
    assert "Soybean" in credit["explanation"]
    page = client.get(plan_url).text
    assert "Soybean" in page


def post_v2_lab_plan(client: TestClient, csrf: str) -> str:
    r = post_plan(
        client, csrf, new_field(client, csrf), has_soil="yes", sample_date="2026-10-01",
        depth_top="0", depth_bottom="15", source="lab", lab="Test Lab",
        v_form=["P", "K", ""], v_value=["7", "40", ""], v_unit=["mg/kg", "ppm", "mg/kg"],
        v_method=["olsen", "ammonium-acetate", ""], v_detail=["", "", ""],
    )  # fmt: skip
    assert r.status_code == 303, r.text
    return str(r.headers["location"])


def test_ca_on_v2_lab_test_plan_page_covers_nitrogen_only(
    db: psycopg.Connection, org_a: Org
) -> None:
    client, csrf = ca_on_client(db, org_a.agronomist, CA_ON_V2)
    plan_url = post_v2_lab_plan(client, csrf)
    page = client.get(plan_url).text
    assert "This plan covers nitrogen only." in page
    assert "Get a soil test for P and K" not in page
    assert PK_RATE_TEXT.search(page) is None
    assert "the agronomist decides" not in page
    assert "an agronomist must decide P and K" in page

    rec = re.search(r'name="recommendation_id" value="([^"]+)"', page).group(1)  # type: ignore[union-attr]
    r = client.post(
        plan_url + "/review",
        data={"csrf_token": csrf, "recommendation_id": rec, "decision": "approve"},
    )
    assert r.status_code == 303, r.text
    approved = client.get(plan_url).text
    assert "This plan covers nitrogen only." in approved
    assert PK_RATE_TEXT.search(approved) is None
    assert "the agronomist decides" not in approved
    assert "no P or K decision is recorded in this plan" in approved


def test_edited_ca_on_v2_plan_drops_p_and_k_rates(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = ca_on_client(db, org_a.agronomist, CA_ON_V2)
    plan_url = post_v2_lab_plan(client, csrf)
    rec = re.search(  # type: ignore[union-attr]
        r'name="recommendation_id" value="([^"]+)"', client.get(plan_url).text
    ).group(1)
    r = client.post(
        plan_url + "/edit",
        data={"csrf_token": csrf, "recommendation_id": rec, "n_rate": "100",
              "split_rate": ["100"], "reason": "Local trial history"},
    )  # fmt: skip
    assert r.status_code == 303, r.text
    page = client.get(plan_url).text
    final = re.search(r'name="recommendation_id" value="([^"]+)"', page).group(1)  # type: ignore[union-attr]
    assert final != rec
    r = client.post(
        plan_url + "/review",
        data={"csrf_token": csrf, "recommendation_id": final, "decision": "approve"},
    )
    assert r.status_code == 303, r.text
    assert PK_RATE_TEXT.search(client.get(plan_url).text) is None
    stored = dict(
        db.execute(
            "select kind::text, result ? 'phosphorus_potassium_rates' from recommendation"
            " where crop_plan_id = %s",
            (UUID(plan_url.rsplit("/", 1)[1]),),
        ).fetchall()
    )
    assert stored == {"engine": True, "agronomist": False}


def test_plan_form_asks_about_manure_and_other_organic_amendments(
    db: psycopg.Connection, org_a: Org
) -> None:
    client, csrf = ca_on_client(db, org_a.agronomist, CA_ON_V2)
    form = client.get(new_field(client, csrf) + "/plans/new").text
    assert "Manure or other organic amendment applied for this crop?" in form
