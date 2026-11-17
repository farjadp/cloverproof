"""Review queue (/review) and the engine-vs-final diff on the plan page (real database).

Queue: org-scoped, sort + filter via query params, AI review never shown as approval,
403 for anyone who may not review. Diff: engine vs edited values, edit reason, unchanged
lines labelled, nothing shown as approved without a human final review.
"""

from __future__ import annotations

import copy
import re
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import psycopg
import pytest

from .conftest import Org, edited, insert, recommendation_values
from .test_actor_kind import make_service
from .test_plan_flow import create_plan, edit_values, latest_rec, new_field, signed_in
from .test_superadmin import make_user

pytestmark = pytest.mark.db

AI_BADGE = "not an approval"


def plan_ids(html: str) -> list[str]:
    """Plan ids in queue order."""
    return re.findall(r'<td data-label="Plan"><a href="/plans/([0-9a-f-]{36})"', html)


def add_plan(db: psycopg.Connection, org: Org, result: dict[str, Any], *, farmer: str,
             field: str, created: datetime, confidence: str | None = None) -> UUID:  # fmt: skip
    doc = copy.deepcopy(result)
    if confidence:
        doc["confidence"] = confidence
    farmer_id = insert(db, "farmer", organisation_id=org.id, display_name=farmer)
    farm = insert(db, "farm", organisation_id=org.id, farmer_id=farmer_id, name=f"{farmer} farm")
    field_id = insert(db, "field", organisation_id=org.id, farm_id=farm, name=field)
    plan = insert(
        db, "crop_plan", organisation_id=org.id, field_id=field_id, season_id=org.season,
        crop="wheat", target_yield_t_ha=5.0, previous_crop="wheat", plan_date=date(2027, 2, 1),
        created_by=org.staff,
    )  # fmt: skip
    insert(
        db, "recommendation", organisation_id=org.id, crop_plan_id=plan, kind="engine",
        created_by=org.staff, created_at=created, **recommendation_values(doc),
    )  # fmt: skip
    return plan


def engine_rec_of(db: psycopg.Connection, plan: UUID) -> UUID:
    row = db.execute("select id from recommendation where crop_plan_id = %s", (plan,)).fetchone()
    assert row is not None
    return row[0]


def review(db: psycopg.Connection, org: Org, rec: UUID, reviewer: UUID, decision: str,
           reason: str | None = "checked") -> None:  # fmt: skip
    insert(
        db, "review", organisation_id=org.id, recommendation_id=rec, decision=decision,
        reviewer_id=reviewer, minutes_spent=2, reason=reason,
    )  # fmt: skip


# --- access ---------------------------------------------------------------------------


def test_queue_shows_only_own_org(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    client, _ = signed_in(db, org_a.agronomist)
    page = client.get("/review")
    assert page.status_code == 200
    assert str(org_a.crop_plan) in plan_ids(page.text)
    assert str(org_b.crop_plan) not in page.text
    assert "Field b1" not in page.text and "Farmer b" not in page.text
    assert "Field a1" in page.text and "Farmer a" in page.text
    # A search for the other org's names finds nothing either.
    assert plan_ids(client.get("/review", params={"q": "Farmer b"}).text) == []


def test_staff_gets_403_and_no_menu_link(db: psycopg.Connection, org_a: Org) -> None:
    client, _ = signed_in(db, org_a.staff)
    r = client.get("/review", headers={"Accept": "text/html"})
    assert r.status_code == 403
    assert "Only an agronomist or a superadmin can review plans." in r.text
    assert 'href="/review"' not in client.get("/farmers").text


def test_owner_gets_403(db: psycopg.Connection, org_a: Org) -> None:
    owner = make_user(db, org_a, "org-owner", roles=("org_admin",), platform_role=None)
    client, _ = signed_in(db, owner)
    assert client.get("/review").status_code == 403


def test_superadmin_member_sees_queue(db: psycopg.Connection, org_a: Org) -> None:
    admin = make_user(db, org_a, "super-admin", roles=("advisor",))
    client, _ = signed_in(db, admin)
    page = client.get("/review")
    assert page.status_code == 200 and str(org_a.crop_plan) in plan_ids(page.text)


def test_agronomist_sees_menu_link(db: psycopg.Connection, org_a: Org) -> None:
    client, _ = signed_in(db, org_a.agronomist)
    assert 'href="/review"' in client.get("/farmers").text
    page = client.get("/review").text
    assert '<a class="nav-link" href="/review" aria-current="page">' in page


def test_signed_out_is_sent_to_login(db: psycopg.Connection, org_a: Org) -> None:
    from .test_web_auth import build_client

    r = build_client(db).get("/review", headers={"Accept": "text/html"})
    assert r.status_code == 303 and r.headers["location"].startswith("/login")


# --- status: human final reviews only -------------------------------------------------


def test_ai_review_is_never_an_approval(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    service = make_service(db, org_a)
    review(db, org_a, org_a.engine_rec, service, "approve", "Looks plausible")
    client, _ = signed_in(db, org_a.agronomist)
    page = client.get("/review").text
    assert plan_ids(page) == [str(org_a.crop_plan)]  # still awaiting
    assert "AI review" in page and AI_BADGE in page
    assert "Waiting for a human review" in page
    assert "status-approved" not in page and ">Approved<" not in page.split("<tbody>")[1]
    assert plan_ids(client.get("/review", params={"status": "approved"}).text) == []
    assert plan_ids(client.get("/review", params={"ai": "yes"}).text) == [str(org_a.crop_plan)]
    assert plan_ids(client.get("/review", params={"ai": "no"}).text) == []


def test_human_final_review_leaves_the_queue(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    rejected = add_plan(db, org_a, engine_result, farmer="Rae", field="Rae south",
                        created=datetime(2025, 1, 2, tzinfo=UTC))  # fmt: skip
    review(db, org_a, org_a.engine_rec, org_a.agronomist, "approve")
    review(db, org_a, engine_rec_of(db, rejected), org_a.agronomist, "reject", "Wrong field")
    client, _ = signed_in(db, org_a.agronomist)
    assert plan_ids(client.get("/review").text) == []
    assert "No plans waiting for a decision." in client.get("/review").text
    approved = client.get("/review", params={"status": "approved"}).text
    assert plan_ids(approved) == [str(org_a.crop_plan)] and "status-approved" in approved
    assert "By superadmin" not in approved  # an agronomist approval is not relabelled
    assert plan_ids(client.get("/review", params={"status": "rejected"}).text) == [str(rejected)]
    assert len(plan_ids(client.get("/review", params={"status": "all"}).text)) == 2


def test_superadmin_final_review_counts_as_human(db: psycopg.Connection, org_a: Org) -> None:
    admin = make_user(db, org_a, "super-admin", roles=("advisor",))
    review(db, org_a, org_a.engine_rec, admin, "approve")
    client, _ = signed_in(db, org_a.agronomist)
    assert plan_ids(client.get("/review").text) == []
    approved = client.get("/review", params={"status": "approved"}).text
    assert plan_ids(approved) == [str(org_a.crop_plan)]
    assert "By superadmin, not an agronomist review" in approved


def test_edit_review_keeps_the_new_version_awaiting(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    v2 = insert(
        db, "recommendation", organisation_id=org_a.id, crop_plan_id=org_a.crop_plan,
        parent_id=org_a.engine_rec, kind="agronomist", reason="Manure last fall",
        created_by=org_a.agronomist, **recommendation_values(edited(engine_result, 90.0)),
    )  # fmt: skip
    insert(
        db, "review", organisation_id=org_a.id, recommendation_id=org_a.engine_rec,
        decision="edit", reviewer_id=org_a.agronomist, minutes_spent=3, reason="Manure",
        resulting_recommendation_id=v2,
    )  # fmt: skip
    client, _ = signed_in(db, org_a.agronomist)
    page = client.get("/review").text
    assert plan_ids(page) == [str(org_a.crop_plan)]
    assert "v2" in page and "edited" in page


# --- sorting and filters ----------------------------------------------------------------


@pytest.fixture
def three_plans(db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]) -> list[str]:
    """org_a's own plan (low, created now) plus two older ones with other confidences."""
    older = add_plan(db, org_a, engine_result, farmer="Zed", field="Zed east",
                     created=datetime(2025, 1, 1, tzinfo=UTC), confidence="high")  # fmt: skip
    middle = add_plan(db, org_a, engine_result, farmer="Abe", field="Abe west",
                      created=datetime(2025, 1, 5, tzinfo=UTC), confidence="medium")  # fmt: skip
    return [str(older), str(middle), str(org_a.crop_plan)]


def test_default_sort_is_oldest_first(db: psycopg.Connection, org_a: Org,
                                      three_plans: list[str]) -> None:  # fmt: skip
    client, _ = signed_in(db, org_a.agronomist)
    assert plan_ids(client.get("/review").text) == three_plans
    assert plan_ids(client.get("/review", params={"sort": "newest"}).text) == three_plans[::-1]


def test_sort_by_farmer_and_confidence(db: psycopg.Connection, org_a: Org,
                                       three_plans: list[str]) -> None:  # fmt: skip
    older, middle, own = three_plans
    client, _ = signed_in(db, org_a.agronomist)
    # Abe < Farmer a < Zed
    assert plan_ids(client.get("/review", params={"sort": "farmer"}).text) == [middle, own, older]
    # low (own) < medium < high
    by_conf = plan_ids(client.get("/review", params={"sort": "confidence"}).text)
    assert by_conf == [own, middle, older]


def test_filters(db: psycopg.Connection, org_a: Org, three_plans: list[str]) -> None:
    older, middle, own = three_plans
    client, _ = signed_in(db, org_a.agronomist)
    assert plan_ids(client.get("/review", params={"confidence": "high"}).text) == [older]
    assert plan_ids(client.get("/review", params={"confidence": "low"}).text) == [own]
    assert plan_ids(client.get("/review", params={"crop": "wheat"}).text) == three_plans
    assert plan_ids(client.get("/review", params={"q": "abe"}).text) == [middle]
    page = client.get("/review", params={"confidence": "high"}).text
    assert 'href="/review">Clear filters' in page


def test_invalid_params_fall_back_to_defaults(db: psycopg.Connection, org_a: Org,
                                              three_plans: list[str]) -> None:  # fmt: skip
    client, _ = signed_in(db, org_a.agronomist)
    params = {"sort": "drop table", "status": "<script>", "confidence": "x", "crop": "rice",
              "ai": "maybe"}  # fmt: skip
    r = client.get("/review", params=params)
    assert r.status_code == 200 and plan_ids(r.text) == three_plans
    assert "drop table" not in r.text and "<script>" not in r.text


def test_htmx_returns_the_results_partial(db: psycopg.Connection, org_a: Org) -> None:
    client, _ = signed_in(db, org_a.agronomist)
    r = client.get("/review", headers={"HX-Request": "true"})
    assert r.status_code == 200
    assert r.text.lstrip().startswith('<div id="queue-results">') and "<html" not in r.text
    assert plan_ids(r.text) == [str(org_a.crop_plan)]


def test_placeholder_pack_flag(db: psycopg.Connection, org_a: Org) -> None:
    client, _ = signed_in(db, org_a.agronomist)
    assert "Placeholder pack" in client.get("/review").text


# --- engine vs final diff on the plan page -------------------------------------------------


def test_diff_shows_engine_vs_edited_values_and_reason(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    page = client.get(plan_url).text
    assert "No edits. v1 has the engine's numbers." in page
    engine_rate, _splits = edit_values(client, plan_url)
    r = client.post(
        plan_url + "/edit",
        data={"csrf_token": csrf, "recommendation_id": latest_rec(client, plan_url),
              "n_rate": "120", "split_rate": ["48", "72"], "reason": "Manure last fall"},
    )  # fmt: skip
    assert r.status_code == 303, r.text
    page = client.get(plan_url).text
    diff = page.split('id="diff"', 1)[1].split("</section>", 1)[0]
    assert "Engine (v1)" in diff and "v2 (latest)" in diff
    assert f"{float(engine_rate):,.1f} kg N/ha" in diff  # engine value kept
    assert "120.0 kg N/ha" in diff and "48.0 kg N/ha" in diff and "72.0 kg N/ha" in diff
    assert "Changed: rate, total" in diff  # season line
    assert diff.count("Changed: rate</strong>") == 2  # splits: same 40/60 shares, new rates
    assert 'class="tag-changed"' in diff and ", was " in diff
    assert "“Manure last fall”" in diff and "edited by Agro a" in diff
    assert "Elemental N (kg N/ha)" in diff
    # No soil test: P/K is a rule line on both sides, unchanged.
    assert diff.count("Soil test recommended. No P or K rate without a soil test.") == 2
    assert "Set by rule, not editable: no P or K rate without a soil test." in diff
    # Every number keeps its explanation on both sides.
    assert "Set by agronomist: Manure last fall" in diff and "Recommended N rate" in diff
    # Still nothing approved: no human final review yet.
    assert "Approved by" not in page and "status-in_review" in page


def test_diff_after_approval_and_ai_review_wording(db: psycopg.Connection, org_a: Org) -> None:
    service = make_service(db, org_a)
    review(db, org_a, org_a.engine_rec, service, "approve", "AI says fine")
    client, _ = signed_in(db, org_a.agronomist)
    page = client.get(f"/plans/{org_a.crop_plan}").text
    assert "Approved by" not in page and "not an approval" in page
    assert "No edits. v1 has the engine's numbers." in page
