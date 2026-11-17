"""Platform role `superadmin` and the review gate (migration 0012; decision 2026-11-16).

A human superadmin may approve, edit and reject in an organisation they are a member of,
even without the agronomist role there; the review is then `superadmin_approved`: final
for status, the F1 invariants and proof documents, but never calibration data
(`recommendation_diff`). A human who is an agronomist of the organisation records
`agronomist_approved`, superadmin or not. Service accounts never hold a platform role and
never approve, edit or reject. Only cp_admin (CLI) sets `platform_role`; every change is
audited in `admin_event`.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import errors

from cloverproof_app import cli

from .conftest import Org, as_owner, as_role, edited, insert, recommendation_values
from .test_plan_flow import edit_values, latest_rec, signed_in

pytestmark = pytest.mark.db

SHA = "a" * 64


def make_user(
    db: psycopg.Connection,
    org: Org,
    label: str,
    *,
    roles: tuple[str, ...] = ("staff",),
    platform_role: str | None = "superadmin",
    actor_kind: str = "human",
) -> UUID:
    with as_role(db, "cp_admin"):
        user = insert(
            db,
            "app_user",
            email=f"{label}@example.org",
            display_name=label.replace("-", " ").title(),
            actor_kind=actor_kind,
            platform_role=platform_role,
        )
    for role in roles:
        insert(db, "membership", organisation_id=org.id, user_id=user, role=role)
    return user


@contextmanager
def service_superadmin_allowed(db: psycopg.Connection) -> Iterator[None]:
    """Drop the human-only check for one block (rolled back): tests the triggers alone."""
    with as_owner(db):
        db.execute("alter table app_user drop constraint app_user_platform_role_human")
        yield


def review(db: psycopg.Connection, org: Org, reviewer: UUID, decision: str, **extra: Any) -> UUID:
    values: dict[str, Any] = {
        "organisation_id": org.id,
        "recommendation_id": org.engine_rec,
        "decision": decision,
        "reviewer_id": reviewer,
        "minutes_spent": 4,
        "reason": "test reason",
    }
    values.update(extra)
    return insert(db, "review", **values)


def child(db: psycopg.Connection, org: Org, result: dict[str, Any], author: UUID,
          parent: UUID | None = None) -> UUID:  # fmt: skip
    return insert(
        db,
        "recommendation",
        organisation_id=org.id,
        crop_plan_id=org.crop_plan,
        parent_id=parent or org.engine_rec,
        kind="agronomist",
        reason="Edit (test)",
        created_by=author,
        **recommendation_values(edited(result, 77.0)),
    )


def kind_of(db: psycopg.Connection, review_id: UUID) -> str:
    row = db.execute("select review_kind from review where id = %s", (review_id,)).fetchone()
    assert row is not None
    return row[0]


def diff_ids(db: psycopg.Connection, org: Org) -> dict[UUID, UUID | None]:
    rows = db.execute(
        "select final_recommendation_id, approved_by from recommendation_diff"
        " where organisation_id = %s",
        (org.id,),
    ).fetchall()
    return dict(rows)


def proof(db: psycopg.Connection, org: Org, rec: UUID) -> UUID:
    return insert(
        db,
        "proof_document",
        organisation_id=org.id,
        recommendation_id=rec,
        sha256=SHA,
        storage_key=f"proof/{org.id}/{rec}/{SHA}.pdf",
        created_by=org.staff,
    )


# --- column, values, grants, audit -----------------------------------------------------


def test_platform_role_defaults_to_null(db: psycopg.Connection, org_a: Org) -> None:
    row = db.execute(
        "select platform_role from app_user where id = %s", (org_a.agronomist,)
    ).fetchone()
    assert row == (None,)


def test_platform_role_values_are_checked(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.CheckViolation, match="platform_role"):
        make_user(db, org_a, "x", platform_role="staff")


def test_service_account_cannot_hold_a_platform_role(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.CheckViolation, match="app_user_platform_role_human"):
        make_user(db, org_a, "svc", actor_kind="service")
    service = make_user(db, org_a, "svc2", actor_kind="service", platform_role=None)
    with (
        pytest.raises(errors.CheckViolation, match="app_user_platform_role_human"),
        as_role(db, "cp_admin"),
    ):
        db.execute("update app_user set platform_role = 'superadmin' where id = %s", (service,))


def test_cp_app_cannot_set_platform_role(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute("update app_user set platform_role = 'superadmin' where id = %s", (org_a.staff,))
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(
            "insert into app_user (email, display_name, platform_role)"
            " values ('p@example.org', 'P', 'superadmin')"
        )
    # cp_app can read it (sessions load it).
    assert db.execute("select platform_role from app_user limit 1").fetchone() is not None


def test_platform_role_changes_are_audited(db: psycopg.Connection, org_a: Org) -> None:
    with as_role(db, "cp_admin"):
        db.execute("update app_user set platform_role = 'superadmin' where id = %s", (org_a.staff,))
        db.execute("update app_user set platform_role = null where id = %s", (org_a.staff,))
    rows = db.execute(
        "select action, actor_db_role, old_value, new_value from admin_event"
        " where target_user_id = %s and action = 'platform_role_changed' order by at, id",
        (org_a.staff,),
    ).fetchall()
    assert [(r[0], r[2], r[3]) for r in rows] == [
        ("platform_role_changed", {"platform_role": None}, {"platform_role": "superadmin"}),
        ("platform_role_changed", {"platform_role": "superadmin"}, {"platform_role": None}),
    ]
    created = make_user(db, org_a, "super-new")
    row = db.execute(
        "select new_value->>'platform_role' from admin_event"
        " where target_user_id = %s and action = 'user_created'",
        (created,),
    ).fetchone()
    assert row == ("superadmin",)


# --- the review gate --------------------------------------------------------------------


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_superadmin_without_agronomist_role_records_superadmin_approved(
    db: psycopg.Connection, org_a: Org, decision: str
) -> None:
    sa = make_user(db, org_a, "super-a")
    rid = review(db, org_a, sa, decision)
    assert kind_of(db, rid) == "superadmin_approved"
    # Final: no second final review (also not by an agronomist).
    with pytest.raises(errors.UniqueViolation), db.transaction():
        review(db, org_a, org_a.agronomist, "approve")
    status = db.execute(
        "select count(*) from review where recommendation_id = %s"
        " and review_kind <> 'ai_reviewed' and decision in ('approve', 'reject')",
        (org_a.engine_rec,),
    ).fetchone()
    assert status == (1,)


def test_superadmin_approve_unlocks_proof_but_not_calibration(
    db: psycopg.Connection, org_a: Org
) -> None:
    sa = make_user(db, org_a, "super-a")
    review(db, org_a, sa, "approve", reason=None)
    assert proof(db, org_a, org_a.engine_rec)
    assert org_a.engine_rec not in diff_ids(db, org_a)


def test_superadmin_final_blocks_edit(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    sa = make_user(db, org_a, "super-a")
    review(db, org_a, sa, "reject")
    with (
        pytest.raises(errors.UniqueViolation, match="already approved or rejected"),
        db.transaction(),
    ):
        child(db, org_a, engine_result, org_a.agronomist)


def test_superadmin_edit_is_labelled_and_excluded_from_calibration(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    sa = make_user(db, org_a, "super-a")
    new = child(db, org_a, engine_result, sa)
    edit = review(db, org_a, sa, "edit", resulting_recommendation_id=new)
    assert kind_of(db, edit) == "superadmin_approved"
    # Even a later agronomist approval of that line stays out of calibration.
    approval = review(db, org_a, org_a.agronomist, "approve", recommendation_id=new)
    assert kind_of(db, approval) == "agronomist_approved"
    ids = diff_ids(db, org_a)
    assert new not in ids
    assert ids.get(org_a.engine_rec, "absent") is None  # engine root itself stays


def test_agronomist_who_is_also_superadmin_records_agronomist_approved(
    db: psycopg.Connection, org_a: Org
) -> None:
    both = make_user(db, org_a, "agro-super", roles=("agronomist",))
    rid = review(db, org_a, both, "approve")
    assert kind_of(db, rid) == "agronomist_approved"
    assert diff_ids(db, org_a)[org_a.engine_rec] == both


@pytest.mark.parametrize(
    ("label", "roles", "platform_role", "claimed", "message"),
    [
        ("super-a", ("staff",), "superadmin", "agronomist_approved", "superadmin_approved"),
        ("agro-super", ("agronomist",), "superadmin", "superadmin_approved", "agronomist_approved"),
        ("plain-staff", ("staff",), None, "superadmin_approved", "superadmin"),
    ],
)
def test_review_kind_mismatch_raises(
    db: psycopg.Connection, org_a: Org, label: str, roles: tuple[str, ...],
    platform_role: str | None, claimed: str, message: str,
) -> None:  # fmt: skip
    user = make_user(db, org_a, label, roles=roles, platform_role=platform_role)
    with pytest.raises(errors.InsufficientPrivilege, match=message), db.transaction():
        review(db, org_a, user, "approve", review_kind=claimed)


def test_superadmin_must_be_a_member_of_the_org(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    sa = make_user(db, org_b, "super-b")
    with (
        pytest.raises(errors.InsufficientPrivilege, match="not an active member"),
        db.transaction(),
    ):
        review(db, org_a, sa, "approve")


def test_plain_human_staff_still_cannot_approve(db: psycopg.Connection, org_a: Org) -> None:
    with (
        pytest.raises(errors.InsufficientPrivilege, match="only an agronomist"),
        db.transaction(),
    ):
        review(db, org_a, org_a.staff, "approve")


@pytest.mark.parametrize("roles", [("staff",), ("agronomist",)])
def test_service_superadmin_never_approves_rejects_or_edits(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any], roles: tuple[str, ...]
) -> None:
    with service_superadmin_allowed(db):
        svc = make_user(db, org_a, "svc-super", roles=roles, actor_kind="service")
        for claimed in ("agronomist_approved", "superadmin_approved"):
            for decision in ("approve", "reject"):
                with pytest.raises(errors.InsufficientPrivilege), db.transaction():
                    review(db, org_a, svc, decision, review_kind=claimed)
        with (
            pytest.raises(errors.InsufficientPrivilege, match="service account"),
            db.transaction(),
        ):
            child(db, org_a, engine_result, svc)
        # Its review without a claimed kind is an AI opinion: not final.
        rid = review(db, org_a, svc, "approve")
        assert kind_of(db, rid) == "ai_reviewed"
        with pytest.raises(errors.CheckViolation, match="not approved"), db.transaction():
            proof(db, org_a, org_a.engine_rec)
        assert kind_of(db, review(db, org_a, org_a.agronomist, "approve")) == (
            "agronomist_approved"
        )


# --- app --------------------------------------------------------------------------------


def stored(db: psycopg.Connection, plan_url: str) -> list[tuple[str, str]]:
    return db.execute(
        "select v.decision::text, v.review_kind from review v join recommendation r"
        " on r.id = v.recommendation_id where r.crop_plan_id = %s order by v.created_at",
        (UUID(plan_url.rsplit("/", 1)[1]),),
    ).fetchall()


def test_web_superadmin_approves_and_page_says_superadmin(
    db: psycopg.Connection, org_a: Org
) -> None:
    sa = make_user(db, org_a, "super-a")
    client, csrf = signed_in(db, sa)
    plan_url = f"/plans/{org_a.crop_plan}"
    page = client.get(plan_url).text
    assert "Save review" in page
    data = {"csrf_token": csrf, "recommendation_id": str(org_a.engine_rec), "decision": "approve"}
    assert client.post(plan_url + "/review", data=data).status_code == 303
    assert "Approved by Super A (superadmin)" in client.get(plan_url).text
    assert stored(db, plan_url) == [("approve", "superadmin_approved")]
    assert org_a.engine_rec not in diff_ids(db, org_a)


def test_web_superadmin_edit_is_superadmin_approved(db: psycopg.Connection, org_a: Org) -> None:
    sa = make_user(db, org_a, "super-a")
    client, csrf = signed_in(db, sa)
    plan_url = f"/plans/{org_a.crop_plan}"
    client.get(plan_url)  # starts the timer
    rate, splits = edit_values(client, plan_url)
    data = {
        "csrf_token": csrf, "recommendation_id": latest_rec(client, plan_url),
        "n_rate": str(float(rate) - 10), "split_rate": [str(float(splits[0]) - 10), *splits[1:]],
        "reason": "Superadmin correction (test)",
    }  # fmt: skip
    assert client.post(plan_url + "/edit", data=data).status_code == 303
    assert stored(db, plan_url) == [("edit", "superadmin_approved")]


def test_web_agronomist_label(db: psycopg.Connection, org_a: Org) -> None:
    both = make_user(db, org_a, "agro-super", roles=("agronomist",))
    client, csrf = signed_in(db, both)
    plan_url = f"/plans/{org_a.crop_plan}"
    client.get(plan_url)
    data = {"csrf_token": csrf, "recommendation_id": str(org_a.engine_rec), "decision": "approve"}
    assert client.post(plan_url + "/review", data=data).status_code == 303
    assert "Approved by Agro Super (agronomist)" in client.get(plan_url).text
    assert stored(db, plan_url) == [("approve", "agronomist_approved")]


def test_web_plain_staff_cannot_review(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.staff)
    plan_url = f"/plans/{org_a.crop_plan}"
    client.get(plan_url)
    data = {"csrf_token": csrf, "recommendation_id": str(org_a.engine_rec), "decision": "approve"}
    assert client.post(plan_url + "/review", data=data).status_code == 403


# --- CLI --------------------------------------------------------------------------------


def test_cli_creates_superadmin(db: psycopg.Connection, org_a: Org) -> None:
    with as_role(db, "cp_admin"):
        result = cli.user_create(
            db, email="new.super@example.org", org=str(org_a.id), role="staff",
            display_name=None, create_org=False, reset_password=False,
            read_password=lambda: "a long enough password", platform_role="superadmin",
        )  # fmt: skip
    row = db.execute(
        "select platform_role from app_user where id = %s", (result.user_id,)
    ).fetchone()
    assert row == ("superadmin",)


def test_cli_sets_and_clears_platform_role(db: psycopg.Connection, org_a: Org) -> None:
    email = "staff-a@example.org"
    with as_role(db, "cp_admin"):
        cli.user_set_platform_role(db, email=email, platform_role="superadmin")
        assert db.execute(
            "select platform_role from app_user where id = %s", (org_a.staff,)
        ).fetchone() == ("superadmin",)
        cli.user_set_platform_role(db, email=email, platform_role=None)
    assert db.execute(
        "select platform_role from app_user where id = %s", (org_a.staff,)
    ).fetchone() == (None,)
    actions = db.execute(
        "select count(*) from admin_event where target_user_id = %s"
        " and action = 'platform_role_changed'",
        (org_a.staff,),
    ).fetchone()
    assert actions == (2,)


def test_cli_refuses_platform_role_for_service_account(db: psycopg.Connection, org_a: Org) -> None:
    make_user(db, org_a, "svc", actor_kind="service", platform_role=None)
    with pytest.raises(cli.CliError, match="service account"), as_role(db, "cp_admin"):
        cli.user_set_platform_role(db, email="svc@example.org", platform_role="superadmin")
    with pytest.raises(cli.CliError, match="no user"), as_role(db, "cp_admin"):
        cli.user_set_platform_role(db, email="nobody@example.org", platform_role="superadmin")
