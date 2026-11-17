"""QA additions for PR #45 (review queue + diff): role gate, AI reject, HTTP approve flow,
immutability, one-sided diff rendering."""

from __future__ import annotations

import copy
from typing import Any

import psycopg
import pytest

from cloverproof_app import line_diff
from cloverproof_app.web import templates

from .conftest import Org
from .test_actor_kind import make_service
from .test_plan_flow import create_plan, latest_rec, new_field, signed_in
from .test_review_queue import AI_BADGE, plan_ids, review
from .test_superadmin import make_user

pytestmark = pytest.mark.db


def test_farmer_member_is_refused(db: psycopg.Connection, org_a: Org) -> None:
    farmer = make_user(db, org_a, "farm-user", roles=("farmer",), platform_role=None)
    from .test_web_auth import build_client, email_of, login, with_password

    with_password(db, farmer)
    client = build_client(db)
    assert login(client, email_of(db, farmer)).status_code == 303
    r = client.get("/review", headers={"Accept": "text/html"})
    assert r.status_code in (403, 404)
    assert str(org_a.crop_plan) not in r.text


def test_service_agronomist_cannot_hold_a_password(db: psycopg.Connection, org_a: Org) -> None:
    """A service (AI) agronomist can never sign in, so it never reaches /review."""
    service = make_service(db, org_a)
    from .test_web_auth import with_password

    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        with_password(db, service)


def test_human_superadmin_without_membership_is_refused(db: psycopg.Connection,
                                                         org_a: Org) -> None:  # fmt: skip
    admin = make_user(db, org_a, "super-nomember", roles=(), platform_role="superadmin")
    from .test_web_auth import build_client, email_of, login, with_password

    with_password(db, admin)
    client = build_client(db)
    login(client, email_of(db, admin))
    r = client.get("/review")
    assert r.status_code != 200 or str(org_a.crop_plan) not in r.text


def test_ai_reject_is_never_a_rejection(db: psycopg.Connection, org_a: Org) -> None:
    service = make_service(db, org_a)
    review(db, org_a, org_a.engine_rec, service, "reject", "AI doubts it")
    client, _ = signed_in(db, org_a.agronomist)
    page = client.get("/review").text
    assert plan_ids(page) == [str(org_a.crop_plan)] and AI_BADGE in page
    assert plan_ids(client.get("/review", params={"status": "rejected"}).text) == []


def test_http_approve_removes_plan_and_version_is_immutable(db: psycopg.Connection,
                                                            org_a: Org) -> None:  # fmt: skip
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    plan_id = plan_url.rsplit("/", 1)[1]
    assert plan_id in plan_ids(client.get("/review").text)
    rec = latest_rec(client, plan_url)
    data = {"csrf_token": csrf, "recommendation_id": rec, "decision": "approve"}
    r = client.post(plan_url + "/review", data=data)
    assert r.status_code == 303, r.text
    assert plan_id not in plan_ids(client.get("/review").text)
    assert plan_id in plan_ids(client.get("/review", params={"status": "approved"}).text)
    # Hard rule 4: the app role cannot UPDATE a recommendation.
    with pytest.raises(psycopg.Error), db.transaction():
        db.execute("update recommendation set confidence = 'high' where id = %s", (rec,))


def test_diff_template_renders_one_sided_split(engine_result: dict[str, Any]) -> None:
    final = copy.deepcopy(engine_result)
    extra = copy.deepcopy(final["nitrogen"]["splits"][-1])
    final["nitrogen"]["splits"].append(extra)
    lines = line_diff.diff_lines(engine_result, final)
    only = [ln for ln in lines if ln.only_in]
    assert len(only) == 1 and only[0].only_in == "final"
    d = line_diff.LineDiff(engine_number=1, final_number=2, edit_depth=1, lines=lines)
    html = templates.env.get_template("_diff.html").render(line_diff=d)
    assert "Only in v2" in html and "Not in the engine version" in html
    # removed side
    lines = line_diff.diff_lines(final, engine_result)
    d = line_diff.LineDiff(engine_number=1, final_number=2, edit_depth=1, lines=lines)
    html = templates.env.get_template("_diff.html").render(line_diff=d)
    assert "Removed in v2" in html
