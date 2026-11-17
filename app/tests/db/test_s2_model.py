"""Migrations 0016-0020: crop_plan.sequence_no, farmer.record_kind, soil-test lock,
recommendation_state view, access_grant. RLS on all of them is in test_rls.py."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import errors

from .conftest import Org, as_owner, as_role, insert, recommendation_values, use_context
from .test_review_gate import agronomist_edit, approve

pytestmark = pytest.mark.db


def crop_plan(db: psycopg.Connection, org: Org, field: UUID, **extra: Any) -> UUID:
    return insert(
        db,
        "crop_plan",
        organisation_id=org.id,
        field_id=field,
        season_id=org.season,
        crop="wheat",
        target_yield_t_ha=5.0,
        previous_crop="wheat",
        plan_date=date(2027, 2, 1),
        created_by=org.staff,
        **extra,
    )


def one(db: psycopg.Connection, query: str, params: Any = None) -> Any:
    row = db.execute(query, params).fetchone()
    assert row is not None
    return row[0] if len(row) == 1 else row


# --- 0016 crop_plan.sequence_no ---------------------------------------------------------


def test_sequence_no_is_assigned_per_field_and_season(db: psycopg.Connection, org_a: Org) -> None:
    second = crop_plan(db, org_a, org_a.fields[0])  # double crop on the first field
    other_field = crop_plan(db, org_a, org_a.fields[1])
    seq = "select sequence_no from crop_plan where id = %s"
    assert one(db, seq, (org_a.crop_plan,)) == 1
    assert one(db, seq, (second,)) == 2
    assert one(db, seq, (other_field,)) == 1


def test_sequence_no_is_unique_per_field_and_season(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.UniqueViolation), db.transaction():
        crop_plan(db, org_a, org_a.fields[0], sequence_no=1)
    with pytest.raises(errors.CheckViolation), db.transaction():
        crop_plan(db, org_a, org_a.fields[1], sequence_no=0)


# --- 0017 farmer.record_kind ------------------------------------------------------------


def make_superadmin(db: psycopg.Connection, user: UUID) -> None:
    with as_owner(db):
        db.execute("update app_user set platform_role = 'superadmin' where id = %s", (user,))


def new_farmer(db: psycopg.Connection, org: Org) -> UUID:
    return insert(db, "farmer", organisation_id=org.id, display_name="No plan yet")


def test_record_kind_defaults_to_real(db: psycopg.Connection, org_a: Org) -> None:
    assert one(db, "select record_kind from farmer where id = %s", (org_a.farmer,)) == "real"


def test_cp_app_cannot_write_record_kind(db: psycopg.Connection, org_a: Org) -> None:
    farmer = new_farmer(db, org_a)
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute("update farmer set record_kind = 'demo' where id = %s", (farmer,))
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(
            "insert into farmer (organisation_id, display_name, record_kind)"
            " values (%s, 'X', 'demo')",
            (org_a.id,),
        )


def test_cli_without_superadmin_cannot_set_record_kind(db: psycopg.Connection, org_a: Org) -> None:
    farmer = new_farmer(db, org_a)
    with (
        as_role(db, "cp_admin"),
        pytest.raises(errors.InsufficientPrivilege, match="superadmin"),
        db.transaction(),
    ):
        db.execute("update farmer set record_kind = 'demo' where id = %s", (farmer,))


def test_human_superadmin_sets_record_kind_until_a_plan_exists(
    db: psycopg.Connection, org_a: Org
) -> None:
    make_superadmin(db, org_a.agronomist)
    farmer = new_farmer(db, org_a)
    with as_role(db, "cp_admin"):
        db.execute("update farmer set record_kind = 'demo' where id = %s", (farmer,))
        # org_a.farmer has a recommendation: frozen, even for a superadmin.
        with pytest.raises(errors.InsufficientPrivilege, match="frozen"), db.transaction():
            db.execute("update farmer set record_kind = 'demo' where id = %s", (org_a.farmer,))
    assert one(db, "select record_kind from farmer where id = %s", (farmer,)) == "demo"


def test_record_kind_frozen_for_the_operator_too(db: psycopg.Connection, org_a: Org) -> None:
    with (
        as_owner(db),
        pytest.raises(errors.InsufficientPrivilege, match="frozen"),
        db.transaction(),
    ):
        db.execute("update farmer set record_kind = 'demo' where id = %s", (org_a.farmer,))


def test_service_superadmin_impossible(db: psycopg.Connection) -> None:
    with as_owner(db), pytest.raises(errors.CheckViolation), db.transaction():
        db.execute(
            "insert into app_user (email, display_name, actor_kind, platform_role)"
            " values ('svc-sa@example.org', 'Svc', 'service', 'superadmin')"
        )


# --- 0018 soil test lock ----------------------------------------------------------------


@pytest.fixture
def used_soil_test(db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]) -> UUID:
    test = insert(
        db,
        "soil_test",
        organisation_id=org_a.id,
        field_id=org_a.fields[1],
        sample_date=date(2026, 9, 15),
        depth_top_cm=0,
        depth_bottom_cm=15,
        source="lab",
        lab="Example Lab",
        created_by=org_a.staff,
    )
    insert(
        db,
        "soil_test_value",
        organisation_id=org_a.id,
        soil_test_id=test,
        form="P",
        value=12,
        unit="mg/kg",
        extraction_method="olsen",
    )
    plan = crop_plan(db, org_a, org_a.fields[1], soil_test_id=test)
    insert(
        db,
        "recommendation",
        organisation_id=org_a.id,
        crop_plan_id=plan,
        kind="engine",
        created_by=org_a.staff,
        **recommendation_values(engine_result),
    )
    return test


LOCKED = errors.ObjectNotInPrerequisiteState


def test_used_soil_test_is_locked(db: psycopg.Connection, org_a: Org, used_soil_test: UUID) -> None:
    for query in (
        "update soil_test set lab = 'Other lab' where id = %s",
        "delete from soil_test where id = %s",
        "update soil_test_value set value = 99 where soil_test_id = %s",
        "delete from soil_test_value where soil_test_id = %s",
        "insert into soil_test_value (organisation_id, soil_test_id, form, value, unit,"
        " extraction_method) select organisation_id, id, 'K', 100, 'mg/kg', 'olsen'"
        " from soil_test where id = %s",
    ):
        with pytest.raises(LOCKED, match="locked"), db.transaction():
            db.execute(query, (used_soil_test,))


def test_soil_test_without_recommendation_stays_editable(
    db: psycopg.Connection, org_a: Org
) -> None:
    test = insert(
        db,
        "soil_test",
        organisation_id=org_a.id,
        field_id=org_a.fields[1],
        sample_date=date(2026, 9, 15),
        depth_top_cm=0,
        depth_bottom_cm=15,
        source="lab",
        created_by=org_a.staff,
    )
    crop_plan(db, org_a, org_a.fields[1], soil_test_id=test)  # a plan, but no recommendation
    assert db.execute("update soil_test set lab = 'Lab 2' where id = %s", (test,)).rowcount == 1


# --- 0019 recommendation_state ----------------------------------------------------------


def state(db: psycopg.Connection, rec: UUID) -> tuple[Any, ...]:
    return one(
        db,
        "select status, version_no, approval_kind, ai_review_count"
        " from recommendation_state where recommendation_id = %s",
        (rec,),
    )


def make_service(db: psycopg.Connection, org: Org) -> UUID:
    with as_owner(db):
        user = insert(
            db, "app_user", email="svc-state@example.org", display_name="AI", actor_kind="service"
        )
        insert(db, "membership", organisation_id=org.id, user_id=user, role="advisor")
    return user


def test_state_lifecycle(db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]) -> None:
    assert state(db, org_a.engine_rec) == ("in_review", 1, None, 0)
    service = make_service(db, org_a)
    insert(
        db,
        "review",
        organisation_id=org_a.id,
        recommendation_id=org_a.engine_rec,
        decision="approve",
        review_kind="ai_reviewed",
        reviewer_id=service,
        minutes_spent=0,
        reason="Looks plausible",
    )
    use_context(db, org_a.agronomist, org_a.id)
    # Rule 11: an AI "approve" never makes a recommendation approved.
    assert state(db, org_a.engine_rec) == ("in_review", 1, None, 1)
    child = agronomist_edit(db, org_a, engine_result, 80.0)
    assert state(db, org_a.engine_rec)[0] == "superseded"
    assert state(db, child)[:2] == ("in_review", 2)
    approve(db, org_a, child, org_a.agronomist)
    assert state(db, child) == ("approved", 2, "agronomist_approved", 0)


def test_rejected_state(db: psycopg.Connection, org_a: Org) -> None:
    insert(
        db,
        "review",
        organisation_id=org_a.id,
        recommendation_id=org_a.engine_rec,
        decision="reject",
        reason="Wrong previous crop",
        reviewer_id=org_a.agronomist,
        minutes_spent=3,
    )
    assert state(db, org_a.engine_rec)[0] == "rejected"


def test_ai_reviewed_is_never_approved_in_any_row(db: psycopg.Connection, org_a: Org) -> None:
    service = make_service(db, org_a)
    insert(
        db,
        "review",
        organisation_id=org_a.id,
        recommendation_id=org_a.engine_rec,
        decision="approve",
        review_kind="ai_reviewed",
        reviewer_id=service,
        minutes_spent=0,
        reason="ok",
    )
    use_context(db, org_a.agronomist, org_a.id)
    statuses = {r[0] for r in db.execute("select status from recommendation_state").fetchall()}
    assert statuses <= {"approved", "rejected", "superseded", "in_review"}
    row = one(
        db,
        "select count(*) from recommendation_state s join review v"
        " on v.recommendation_id = s.recommendation_id where s.status = 'approved'"
        " and not exists (select 1 from review h where h.recommendation_id = s.recommendation_id"
        " and h.decision = 'approve' and h.review_kind <> 'ai_reviewed')",
    )
    assert row == 0


# --- 0020 access_grant ------------------------------------------------------------------


@pytest.fixture
def farmer_login(db: psycopg.Connection, org_a: Org) -> UUID:
    """org_a.farmer's own login (member of org A with role farmer)."""
    user = insert(db, "app_user", email="farmer-a@example.org", display_name="Farmer A")
    insert(db, "membership", organisation_id=org_a.id, user_id=user, role="farmer")
    db.execute("update farmer set app_user_id = %s where id = %s", (user, org_a.farmer))
    return user


def grant(db: psycopg.Connection, org: Org, by: UUID, grantee_org: UUID) -> UUID:
    use_context(db, by, org.id)
    row = db.execute(
        "insert into access_grant (owner_organisation_id, farmer_id, grantee_organisation_id,"
        " scope, granted_by) values (%s, %s, %s, 'view', %s) returning id",
        (org.id, org.farmer, grantee_org, by),
    ).fetchone()
    assert row is not None
    return row[0]


def revoke(db: psycopg.Connection, grant_id: UUID, by: UUID, when: str = "now()") -> int:
    return db.execute(
        f"update access_grant set revoked_at = {when}, revoked_by = %s,"
        " revoke_reason = 'farmer changed advisor' where id = %s",
        (by, grant_id),
    ).rowcount


def test_farmer_grants_and_revokes(
    db: psycopg.Connection, org_a: Org, org_b: Org, farmer_login: UUID
) -> None:
    g = grant(db, org_a, farmer_login, org_b.id)
    assert revoke(db, g, farmer_login, "now() + interval '30 days'") == 1
    # Server time, not the caller's.
    assert one(db, "select revoked_at <= now() from access_grant where id = %s", (g,)) is True
    with pytest.raises(errors.InsufficientPrivilege, match="already revoked"), db.transaction():
        revoke(db, g, farmer_login)
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(
            "update access_grant set revoked_at = null, revoked_by = null, revoke_reason = null"
            " where id = %s",
            (g,),
        )
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute("delete from access_grant where id = %s", (g,))
    with (
        as_owner(db),
        pytest.raises(errors.InsufficientPrivilege, match="immutable"),
        db.transaction(),
    ):
        db.execute("delete from access_grant where id = %s", (g,))


def test_scope_change_is_refused(
    db: psycopg.Connection, org_a: Org, org_b: Org, farmer_login: UUID
) -> None:
    g = grant(db, org_a, farmer_login, org_b.id)
    with as_owner(db), pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(
            "update access_grant set scope = 'edit', revoked_at = now(), revoked_by = %s,"
            " revoke_reason = 'x' where id = %s",
            (farmer_login, g),
        )


def test_advisor_and_service_cannot_grant(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        grant(db, org_a, org_a.staff, org_b.id)
    with as_owner(db):
        svc = insert(
            db, "app_user", email="svc-admin@example.org", display_name="Svc", actor_kind="service"
        )
        insert(db, "membership", organisation_id=org_a.id, user_id=svc, role="org_admin")
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        grant(db, org_a, svc, org_b.id)


def test_grantee_sees_grant_but_no_farm_data_and_revoked_grant_changes_nothing(
    db: psycopg.Connection, org_a: Org, org_b: Org, farmer_login: UUID
) -> None:
    g = grant(db, org_a, farmer_login, org_b.id)
    farm_rows = "select count(*) from farmer where organisation_id = %s"
    use_context(db, org_b.agronomist, org_b.id)
    assert one(db, "select count(*) from access_grant where id = %s", (g,)) == 1
    assert one(db, farm_rows, (org_a.id,)) == 0  # no read path through grants before S9
    use_context(db, farmer_login, org_a.id)
    revoke(db, g, farmer_login)
    use_context(db, org_b.agronomist, org_b.id)
    assert one(db, farm_rows, (org_a.id,)) == 0
    # The grantee can read but never revoke or edit the owner's grant.
    assert revoke(db, g, org_b.agronomist) == 0
