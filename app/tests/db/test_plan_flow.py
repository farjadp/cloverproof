"""Plan flow end to end (TestClient + real database): farmer -> field -> plan -> engine ->
edit with reason -> approve; review gate, org scoping, timer."""

from __future__ import annotations

import re
import time
from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient

from cloverproof_app import plan_web, security

from ..support.fakes import TEST_SECRET
from .conftest import Org
from .test_web_auth import build_client, email_of, login, page_csrf, with_password

pytestmark = pytest.mark.db


def signed_in(db: psycopg.Connection, user_id: UUID) -> tuple[TestClient, str]:
    with_password(db, user_id)
    client = build_client(db)
    assert login(client, email_of(db, user_id)).status_code == 303
    return client, page_csrf(client)


def plan_form(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "crop": "wheat",
        "target_yield": "6",
        "previous_crop": "canola",
        "area_ha": "12.5",
        "plan_date": "2027-03-01",
        "has_soil": "no",
    }
    data.update(overrides)
    return data


def new_field(client: TestClient, csrf: str) -> str:
    r = client.post("/farmers", data={"display_name": "Test Farmer", "csrf_token": csrf})
    assert r.status_code == 303
    farmer_url = r.headers["location"]
    assert (
        client.post(
            farmer_url + "/farms", data={"farm_name": "Home", "csrf_token": csrf}
        ).status_code
        == 303
    )
    page = client.get(farmer_url).text
    farm_id = re.search(r'<option value="([0-9a-f-]{36})"', page).group(1)  # type: ignore[union-attr]
    r = client.post(
        farmer_url + "/fields",
        data={"farm_id": farm_id, "field_name": "North 40", "area_ha": "12.5", "csrf_token": csrf},
    )
    assert r.status_code == 303 and r.headers["location"].startswith("/fields/")
    return r.headers["location"]


def create_plan(client: TestClient, csrf: str, field_url: str, **overrides: object) -> str:
    form = client.get(field_url + "/plans/new")
    assert form.status_code == 200
    started = re.search(r'name="started" value="([^"]+)"', form.text).group(1)  # type: ignore[union-attr]
    data = plan_form(**overrides) | {"csrf_token": csrf, "started": started}
    r = client.post(field_url + "/plans", data=data)
    assert r.status_code == 303, r.text
    return r.headers["location"]


def latest_rec(client: TestClient, plan_url: str) -> str:
    page = client.get(plan_url).text
    return re.search(r'name="recommendation_id" value="([^"]+)"', page).group(1)  # type: ignore[union-attr]


def test_happy_path_engine_edit_approve(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    field_url = new_field(client, csrf)
    plan_url = create_plan(
        client, csrf, field_url, has_soil="yes", sample_date="2026-10-01", depth_top="0",
        depth_bottom="15", source="lab", lab="Test Lab",
        v_form=["P", "K", ""], v_value=["12", "150", ""], v_unit=["mg/kg", "ppm", "mg/kg"],
        v_method=["olsen", "other", ""], v_detail=["", "Ammonium acetate", ""],
    )  # fmt: skip
    page = client.get(plan_url)
    assert page.status_code == 200
    assert "Nitrogen plan for North 40" in page.text
    assert "Recommended N rate" in page.text  # explanation under the number
    assert "Placeholder" in page.text and "confidence" in page.text
    assert "Get a soil test for P and K" not in page.text
    plan_id = UUID(plan_url.rsplit("/", 1)[1])
    stored = db.execute(
        "select kind, n_rate_kg_ha, pack_id, confidence::text from recommendation"
        " where crop_plan_id = %s",
        (plan_id,),
    ).fetchall()
    assert len(stored) == 1 and stored[0][0] == "engine" and stored[0][2] == "placeholder"
    values = db.execute(
        "select v.form::text, v.extraction_method::text, v.extraction_method_detail"
        " from soil_test_value v join crop_plan p on p.soil_test_id = v.soil_test_id"
        " where p.id = %s order by v.form",
        (plan_id,),
    ).fetchall()
    assert sorted(values) == [("K", "other", "Ammonium acetate"), ("P", "olsen", None)]

    engine_rec = latest_rec(client, plan_url)
    r = client.post(
        plan_url + "/edit",
        data={"csrf_token": csrf, "recommendation_id": engine_rec, "n_rate": "120",
              "split_rate": ["48", "72"], "reason": "Local trial history"},
    )  # fmt: skip
    assert r.status_code == 303, r.text
    page = client.get(plan_url).text
    assert "Engine vs latest version" in page and "Set by reviewer: Local trial history" in page
    assert "Plan v2" in page

    final_rec = latest_rec(client, plan_url)
    assert final_rec != engine_rec
    r = client.post(
        plan_url + "/review",
        data={"csrf_token": csrf, "recommendation_id": final_rec, "decision": "approve"},
    )
    assert r.status_code == 303
    page = client.get(plan_url).text
    assert "Approved by Agro a" in page and "read-only" in page

    diff = db.execute(
        "select engine_n_rate_kg_ha, final_n_rate_kg_ha, edit_reason, approved_by"
        " from recommendation_diff where crop_plan_id = %s and edit_depth = 1",
        (plan_id,),
    ).fetchone()
    assert diff is not None
    assert float(diff[1]) == 120.0 and float(diff[0]) != 120.0
    assert diff[2] == "Local trial history" and diff[3] == org_a.agronomist
    decisions = db.execute(
        "select v.decision::text from review v join recommendation r on r.id = v.recommendation_id"
        # One test transaction gives both reviews the same now(): order by lineage too
        # (the edit is on the engine root v1, the approval on the edited child v2).
        " where r.crop_plan_id = %s order by v.created_at, r.parent_id is not null, v.id",
        (plan_id,),
    ).fetchall()
    assert [d[0] for d in decisions] == ["edit", "approve"]

    # Read-only after approval: another review is refused, nothing saved.
    again = client.post(
        plan_url + "/review",
        data={"csrf_token": csrf, "recommendation_id": final_rec, "decision": "reject",
              "reason": "x"},
    )  # fmt: skip
    assert again.status_code == 409


def test_no_soil_test_shows_n_only_and_pk_note(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    page = client.get(plan_url).text
    assert "Get a soil test for P and K" in page
    assert "This plan covers nitrogen only." in page
    assert "kg P" not in page and "kg K" not in page and "P₂O₅" not in page
    assert "High confidence" not in page  # max medium without a soil test


def test_plan_form_errors_are_explicit(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    field_url = new_field(client, csrf)
    data = plan_form(
        target_yield="", has_soil="yes", sample_date="2027-04-01", depth_top="20",
        depth_bottom="10", v_form=["P", "P2O5"], v_value=["5", "-1"], v_unit=["mg/kg", "mg/kg"],
        v_method=["other", "olsen"], v_detail=["", ""],
    ) | {"csrf_token": csrf}  # fmt: skip
    r = client.post(field_url + "/plans", data=data)
    assert r.status_code == 422
    for message in (
        "Sample date is after the plan date.",
        "Bottom must be deeper than top.",
        "Name the extraction method.",
        "You entered P twice (as P and P₂O₅).",
        "Enter the target yield in t/ha.",
        "before running the engine",
    ):
        assert message in r.text, message
    assert 'value="2027-04-01"' in r.text  # typed values stay in the form
    plans = db.execute("select count(*) from crop_plan where created_by = %s", (org_a.agronomist,))
    assert plans.fetchone() == (0,)


def test_staff_cannot_approve_or_edit(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.staff)
    plan_url = f"/plans/{org_a.crop_plan}"
    page = client.get(plan_url)
    assert page.status_code == 200 and "Waiting for a human review." in page.text
    data = {"csrf_token": csrf, "recommendation_id": str(org_a.engine_rec), "decision": "approve"}
    r = client.post(plan_url + "/review", data=data)
    assert r.status_code == 403 and plan_web.ONLY_AGRONOMIST in r.text
    assert client.get(plan_url + "/edit").status_code == 403
    count = db.execute(
        "select count(*) from review where recommendation_id = %s", (org_a.engine_rec,)
    ).fetchone()
    assert count is not None and count[0] == 0


def test_edit_without_reason_is_rejected(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    rec = latest_rec(client, plan_url)
    data = {"csrf_token": csrf, "recommendation_id": rec, "n_rate": "99", "reason": "  "}
    page = client.get(plan_url + "/edit").text
    splits = re.findall(r'name="split_rate" type="text" inputmode="decimal" value="([^"]*)"', page)
    r = client.post(plan_url + "/edit", data=data | {"split_rate": splits})
    assert r.status_code == 422 and "Write why you changed the numbers." in r.text
    r = client.post(
        plan_url + "/edit",
        data={"csrf_token": csrf, "recommendation_id": rec, "split_rate": splits,
              "n_rate": re.search(r'name="n_rate"[^>]*value="([^"]*)"', page).group(1),  # type: ignore[union-attr]
              "reason": "no change"},
    )  # fmt: skip
    assert r.status_code == 422 and "No numbers changed." in r.text
    plan_id = plan_url.rsplit("/", 1)[1]
    count = db.execute("select count(*) from recommendation where crop_plan_id = %s", (plan_id,))
    assert count.fetchone()[0] == 1  # type: ignore[index]


def test_reject_needs_reason(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    rec = latest_rec(client, plan_url)
    data = {"csrf_token": csrf, "recommendation_id": rec, "decision": "reject", "reason": ""}
    r = client.post(plan_url + "/review", data=data)
    assert r.status_code == 422 and "Add a reason for rejecting." in r.text
    r = client.post(plan_url + "/review", data=data | {"reason": "Wrong field"})
    assert r.status_code == 303
    assert "Rejected by" in client.get(plan_url).text


def test_cross_org_is_404(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    assert client.get(f"/plans/{org_b.crop_plan}").status_code == 404
    assert client.get(f"/fields/{org_b.fields[0]}").status_code == 404
    assert client.get(f"/farmers/{org_b.farmer}").status_code == 404
    assert client.get(f"/fields/{org_b.fields[0]}/plans/new").status_code == 404
    data = {"csrf_token": csrf, "recommendation_id": str(org_b.engine_rec), "decision": "approve"}
    assert client.post(f"/plans/{org_b.crop_plan}/review", data=data).status_code == 404
    other_field = f"/fields/{org_b.fields[0]}/plans"
    assert client.post(other_field, data=plan_form() | {"csrf_token": csrf}).status_code == 404
    home = client.get("/farmers").text
    assert "Farmer a" in home and "Farmer b" not in home


def test_minutes_spent_stored_from_signed_start(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    plan_id = UUID(plan_url.rsplit("/", 1)[1])
    rec = latest_rec(client, plan_url)
    # Pretend the plan was opened 7.5 minutes ago (server-signed, as the app does).
    session = db.execute(
        "select id from user_session where user_id = %s and revoked_at is null"
        " order by created_at desc limit 1",
        (org_a.agronomist,),
    ).fetchone()
    assert session is not None
    started = int(time.time()) - 450
    signature = security.sign(TEST_SECRET, f"timer:{session[0]}:{plan_id}", str(started))
    client.cookies.set(
        f"cp_timer_{plan_id.hex}", f"{started}.{signature}", path=f"/plans/{plan_id}"
    )
    assert (
        'Minutes on this plan: <span class="num">7</span>' in client.get(plan_url + "/timer").text
    )

    data = {"csrf_token": csrf, "recommendation_id": rec, "decision": "approve"}
    r = client.post(plan_url + "/review", data=data)
    assert r.status_code == 303
    minutes = db.execute(
        "select minutes_spent from review where recommendation_id = %s", (UUID(rec),)
    ).fetchone()
    assert minutes is not None and minutes[0] == 7
    assert "7 minutes recorded" in client.get(plan_url).text


def test_tampered_timer_is_not_trusted(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_id = org_a.crop_plan
    started = int(time.time()) - 3600
    client.cookies.set(f"cp_timer_{plan_id.hex}", f"{started}.{'0' * 64}", path=f"/plans/{plan_id}")
    data = {"csrf_token": csrf, "recommendation_id": str(org_a.engine_rec), "decision": "approve"}
    r = client.post(f"/plans/{plan_id}/review", data=data)
    assert r.status_code == 400 and "timer is missing" in r.text


def test_review_without_timer_is_refused(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    data = {"csrf_token": csrf, "recommendation_id": str(org_a.engine_rec), "decision": "approve"}
    r = client.post(f"/plans/{org_a.crop_plan}/review", data=data)  # never opened: no timer
    assert r.status_code == 400 and "timer is missing" in r.text


PLACEHOLDER_BANNER = "Placeholder pack: these numbers are not agronomic advice."


def edit_values(client: TestClient, plan_url: str) -> tuple[str, list[str]]:
    page = client.get(plan_url + "/edit").text
    rate = re.search(r'name="n_rate"[^>]*value="([^"]*)"', page).group(1)  # type: ignore[union-attr]
    splits = re.findall(r'name="split_rate" type="text" inputmode="decimal" value="([^"]*)"', page)
    return rate, splits


def test_placeholder_pack_banner_everywhere(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    page = client.get(plan_url).text
    assert page.count(PLACEHOLDER_BANNER) == 2  # top of the page and next to Approve
    assert "Do not send to a farmer." in page
    assert "approval is for testing only" in page
    assert "Approving releases these numbers" not in page
    assert PLACEHOLDER_BANNER in client.get(plan_url + "/edit").text
    # Approval is not blocked on a placeholder pack.
    rec = latest_rec(client, plan_url)
    r = client.post(
        plan_url + "/review",
        data={"csrf_token": csrf, "recommendation_id": rec, "decision": "approve"},
    )
    assert r.status_code == 303
    assert PLACEHOLDER_BANNER in client.get(plan_url).text


def test_estimate_soil_test_still_asks_for_pk_test(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(
        client, csrf, new_field(client, csrf), has_soil="yes", sample_date="2026-10-01",
        depth_top="0", depth_bottom="15", source="estimate",
        v_form=["P"], v_value=["12"], v_unit=["mg/kg"], v_method=["olsen"], v_detail=[""],
    )  # fmt: skip
    assert "Get a soil test for P and K" in client.get(plan_url).text


def test_rate_only_edit_rescales_splits(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    rate, splits = edit_values(client, plan_url)
    r = client.post(
        plan_url + "/edit",
        data={"csrf_token": csrf, "recommendation_id": latest_rec(client, plan_url),
              "n_rate": f"{float(rate) + 10:g}", "split_rate": splits, "reason": "Wet spring"},
    )  # fmt: skip
    assert r.status_code == 303, r.text
    page = client.get(plan_url).text
    assert "Set by reviewer: Wet spring" in page
    assert "Rescaled from the reviewer&#39;s N rate, keeping this line&#39;s current share" in page
    assert "outside the pack limits" not in page


def test_rate_outside_pack_limits_is_flagged(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    edit_page = client.get(plan_url + "/edit").text
    assert "Pack limits:" in edit_page
    _, splits = edit_values(client, plan_url)
    high = 10_000  # far above any pack maximum
    r = client.post(
        plan_url + "/edit",
        data={"csrf_token": csrf, "recommendation_id": latest_rec(client, plan_url),
              "n_rate": str(high), "split_rate": splits, "reason": "Test only"},
    )  # fmt: skip
    assert r.status_code == 303, r.text
    page = client.get(plan_url).text
    assert "outside the pack limits" in page
    # The edit page of the new version shows the notice too.
    assert "outside the pack limits" in client.get(plan_url + "/edit").text


def test_field_summary_shows_form_and_method(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    field_url = new_field(client, csrf)
    create_plan(
        client, csrf, field_url, has_soil="yes", sample_date="2026-10-01", depth_top="0",
        depth_bottom="15", source="lab", lab="Test Lab",
        v_form=["P2O5", "K"], v_value=["30", "150"], v_unit=["mg/kg", "ppm"],
        v_method=["bray-1", "other"], v_detail=["", "Ammonium acetate"],
    )  # fmt: skip
    page = client.get(field_url).text
    assert "P₂O₅ 30 mg/kg (Bray-1)" in page
    assert "K 150 ppm (Other: Ammonium acetate)" in page
