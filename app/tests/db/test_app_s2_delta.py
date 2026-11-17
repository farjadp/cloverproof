"""App side of the S2 delta review (PR #7) for plans: B1 AI review display, F1, F4, N13,
N15 (real database). Identity parts: test_app_identity_s2.py."""

from __future__ import annotations

import re
import time
from uuid import UUID

import psycopg
import pytest

from cloverproof_app import plan_web, security

from ..support.fakes import TEST_SECRET
from .conftest import Org, insert
from .test_app_identity_s2 import make_service
from .test_plan_flow import create_plan, edit_values, latest_rec, new_field, signed_in
from .test_web_auth import PASSWORD, build_client, email_of, login, page_csrf

pytestmark = pytest.mark.db


def test_search_wildcards_match_literally(db: psycopg.Connection, org_a: Org) -> None:
    insert(db, "farmer", organisation_id=org_a.id, display_name="Field_50% Ltd")
    client, _ = signed_in(db, org_a.agronomist)
    assert "Farmer a" in client.get("/farmers", params={"q": ""}).text
    assert "Farmer a" not in client.get("/farmers", params={"q": "%"}).text
    assert "Farmer a" not in client.get("/farmers", params={"q": "_"}).text
    assert "Field_50% Ltd" in client.get("/farmers", params={"q": "_50%"}).text


def test_wrong_current_password_does_not_lock_sign_in(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    client.post("/logout", data={"csrf_token": csrf})
    c = build_client(db, login_max_failures=2)
    email = email_of(db, org_a.agronomist)
    assert login(c, email).status_code == 303
    token = page_csrf(c, "/account/password")
    for _ in range(2):
        r = c.post(
            "/account/password",
            data={"csrf_token": token, "current_password": "wrong password!!",
                  "new_password": "x" * 20, "confirm_password": "x" * 20},
        )  # fmt: skip
        assert r.status_code == 422
    c.post("/logout", data={"csrf_token": token})
    assert login(c, email, PASSWORD).status_code == 303


# --- F1: stale and double submits are 409, never a fork or a 500 ------------------------


def edit_data(csrf: str, rec: str, rate: str, splits: list[str], reason: str) -> dict:  # type: ignore[type-arg]
    return {"csrf_token": csrf, "recommendation_id": rec, "n_rate": rate,
            "split_rate": splits, "reason": reason}  # fmt: skip


def counts(db: psycopg.Connection, plan_url: str) -> tuple[int, int]:
    plan_id = plan_url.rsplit("/", 1)[1]
    row = db.execute(
        "select (select count(*) from recommendation where crop_plan_id = %(p)s),"
        " (select count(*) from review v join recommendation r on r.id = v.recommendation_id"
        "   where r.crop_plan_id = %(p)s)",
        {"p": plan_id},
    ).fetchone()
    assert row is not None
    return row[0], row[1]


def test_two_sequential_stale_submits_are_409(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    v1 = latest_rec(client, plan_url)
    _, splits = edit_values(client, plan_url)
    first = client.post(plan_url + "/edit", data=edit_data(csrf, v1, "101", splits, "Tab one"))
    assert first.status_code == 303
    # Second tab still shows v1: an edit and an approve of v1 are both refused.
    stale_edit = client.post(plan_url + "/edit", data=edit_data(csrf, v1, "99", splits, "Tab 2"))
    assert stale_edit.status_code == 409 and plan_web.STALE_VERSION in stale_edit.text
    data = {"csrf_token": csrf, "recommendation_id": v1, "decision": "approve"}
    stale_approve = client.post(plan_url + "/review", data=data)
    assert stale_approve.status_code == 409 and plan_web.STALE_VERSION in stale_approve.text
    assert counts(db, plan_url) == (2, 1)


@pytest.fixture
def no_app_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the app's version check, as a racing request would, so the DB must refuse."""
    monkeypatch.setattr(plan_web, "check_version", lambda view, form: None)


def test_db_refuses_second_final_review_as_409(
    db: psycopg.Connection, org_a: Org, no_app_check: None
) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    v1 = latest_rec(client, plan_url)
    data = {"csrf_token": csrf, "recommendation_id": v1, "decision": "approve"}
    assert client.post(plan_url + "/review", data=data).status_code == 303
    # A second tab still holds its own timer cookie (approve cleared this one).
    set_start(client, db, org_a.agronomist, UUID(plan_url.rsplit("/", 1)[1]), 60)
    again = client.post(plan_url + "/review", data=data | {"decision": "reject", "reason": "x"})
    assert again.status_code == 409 and plan_web.ALREADY_REVIEWED in again.text
    assert counts(db, plan_url) == (1, 1)


def test_db_refuses_fork_as_409(
    db: psycopg.Connection, org_a: Org, no_app_check: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    v1 = latest_rec(client, plan_url)
    _, splits = edit_values(client, plan_url)
    first = client.post(plan_url + "/edit", data=edit_data(csrf, v1, "101", splits, "A"))
    assert first.status_code == 303
    # A request that read the plan before that edit committed still sees v1 as latest.
    real_load_plan = plan_web.load_plan

    def stale_view(conn, context, plan_id):  # type: ignore[no-untyped-def]
        view = real_load_plan(conn, context, plan_id)
        view.latest = next(v for v in view.versions if str(v.id) == v1)
        view.doc = view.latest.result
        return view

    monkeypatch.setattr(plan_web, "load_plan", stale_view)
    fork = client.post(plan_url + "/edit", data=edit_data(csrf, v1, "99", splits, "B"))
    assert fork.status_code == 409 and plan_web.STALE_VERSION in fork.text
    data = {"csrf_token": csrf, "recommendation_id": v1, "decision": "approve"}
    approve_parent = client.post(plan_url + "/review", data=data)
    assert approve_parent.status_code == 409 and plan_web.STALE_VERSION in approve_parent.text
    assert counts(db, plan_url) == (2, 1)


# --- B1: service accounts never sign in, never count as approval -----------------------


@pytest.mark.parametrize("ai_decision", ["approve", "reject"])
def test_ai_review_is_shown_but_never_as_final(
    db: psycopg.Connection, org_a: Org, ai_decision: str
) -> None:
    service = make_service(db, org_a)
    insert(
        db, "review", organisation_id=org_a.id, recommendation_id=org_a.engine_rec,
        decision=ai_decision, review_kind="ai_reviewed", reviewer_id=service, minutes_spent=0,
        reason="Looks plausible",
    )  # fmt: skip
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = f"/plans/{org_a.crop_plan}"
    page = client.get(plan_url).text
    assert "AI review" in page and "not an approval" in page
    assert "Approved by" not in page and "Rejected by" not in page
    assert "Save review" in page  # still open for the human
    assert "In review" in client.get("/farmers").text
    data = {"csrf_token": csrf, "recommendation_id": str(org_a.engine_rec), "decision": "approve"}
    assert client.post(plan_url + "/review", data=data).status_code == 303
    assert "Approved by Agro a" in client.get(plan_url).text
    kinds = db.execute(
        "select review_kind, count(*) from review where recommendation_id = %s"
        " group by review_kind order by review_kind",
        (org_a.engine_rec,),
    ).fetchall()
    assert kinds == [("agronomist_approved", 1), ("ai_reviewed", 1)]


# --- F4: minutes per review, capped, timer reset ----------------------------------------


def session_id(db: psycopg.Connection, user: UUID) -> UUID:
    row = db.execute(
        "select id from user_session where user_id = %s and revoked_at is null"
        " order by created_at desc limit 1",
        (user,),
    ).fetchone()
    assert row is not None
    return row[0]


def set_start(client, db: psycopg.Connection, user: UUID, plan_id: UUID, ago: int) -> int:  # type: ignore[no-untyped-def]
    started = int(time.time()) - ago
    signature = security.sign(TEST_SECRET, f"timer:{session_id(db, user)}:{plan_id}", str(started))
    client.cookies.set(
        f"cp_timer_{plan_id.hex}", f"{started}.{signature}", path=f"/plans/{plan_id}"
    )
    return started


def stored_reviews(db: psycopg.Connection, plan_id: UUID) -> list[tuple]:  # type: ignore[type-arg]
    return db.execute(
        "select v.decision::text, v.minutes_spent, extract(epoch from v.started_at)::bigint,"
        " v.reason from review v join recommendation r on r.id = v.recommendation_id"
        " where r.crop_plan_id = %s order by v.created_at, v.id",
        (plan_id,),
    ).fetchall()


def test_edit_then_approve_counts_minutes_once(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    plan_id = UUID(plan_url.rsplit("/", 1)[1])
    started = set_start(client, db, org_a.agronomist, plan_id, 600)
    v1 = latest_rec(client, plan_url)
    _, splits = edit_values(client, plan_url)
    r = client.post(plan_url + "/edit", data=edit_data(csrf, v1, "101", splits, "Trial"))
    assert r.status_code == 303
    assert any(c.name == f"cp_timer_{plan_id.hex}" for c in client.cookies.jar)  # reset, kept
    v2 = latest_rec(client, plan_url)
    data = {"csrf_token": csrf, "recommendation_id": v2, "decision": "approve"}
    r = client.post(plan_url + "/review", data=data)
    assert r.status_code == 303
    assert (
        f"cp_timer_{plan_id.hex}=" in r.headers["set-cookie"]
        and "Max-Age=0" in r.headers["set-cookie"]
    )  # N14: deleted after the final review
    # One test transaction: both rows share created_at, so order edit first explicitly.
    rows = sorted(stored_reviews(db, plan_id), key=lambda row: row[0] != "edit")
    assert [(d, m) for d, m, _, _ in rows] == [("edit", 10), ("approve", 0)]
    assert rows[0][2] == started and rows[1][2] >= started + 600 - 1


def test_minutes_are_capped_and_flagged(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    client.close()
    c = build_client(db, review_minutes_cap=30)
    c.cookies = client.cookies
    csrf = re.search(r'"X-CSRF-Token": "([0-9a-f]{64})"', c.get("/").text).group(1)  # type: ignore[union-attr]
    plan_id = org_a.crop_plan
    set_start(c, db, org_a.agronomist, plan_id, 45 * 60)
    data = {"csrf_token": csrf, "recommendation_id": str(org_a.engine_rec), "decision": "approve"}
    assert c.post(f"/plans/{plan_id}/review", data=data).status_code == 303
    [(decision, minutes, _, reason)] = stored_reviews(db, plan_id)
    assert (decision, minutes) == ("approve", 30)
    assert reason == "[timer capped: 45 minutes measured, 30 stored]"
