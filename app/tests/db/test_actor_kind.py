"""Human vs service accounts (migration 0012, security review B1 / D4) and N11 expiry.

A service account (e.g. the AI reviewer `cp-agronomist`) may hold an agronomist membership
but its reviews are always `ai_reviewed` (opinion only, never edit, never final); it never
authors an agronomist recommendation and never holds a password. Only cp_admin (CLI) sets
`actor_kind`.
"""

from datetime import timedelta
from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import errors

from .conftest import Org, as_owner, as_role, edited, insert, recommendation_values

pytestmark = pytest.mark.db

HASH = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA"


def make_service(db: psycopg.Connection, org: Org, role: str = "agronomist") -> UUID:
    with as_role(db, "cp_admin"):
        user = insert(
            db,
            "app_user",
            email="cp-agronomist@example.org",
            display_name="AI reviewer",
            actor_kind="service",
        )
    insert(db, "membership", organisation_id=org.id, user_id=user, role=role)
    return user


def review(db: psycopg.Connection, org: Org, reviewer: UUID, decision: str, **extra: Any) -> UUID:
    values: dict[str, Any] = {
        "organisation_id": org.id,
        "recommendation_id": org.engine_rec,
        "decision": decision,
        "reviewer_id": reviewer,
        "minutes_spent": 3,
        "reason": "test reason",
    }
    values.update(extra)
    return insert(db, "review", **values)


def test_existing_and_new_users_default_to_human(db: psycopg.Connection, org_a: Org) -> None:
    row = db.execute(
        "select actor_kind from app_user where id = %s", (org_a.agronomist,)
    ).fetchone()
    assert row == ("human",)


def test_actor_kind_values_are_checked(db: psycopg.Connection) -> None:
    with pytest.raises(errors.CheckViolation), as_role(db, "cp_admin"):
        insert(db, "app_user", email="x@example.org", display_name="X", actor_kind="ai")


def kind_of(db: psycopg.Connection, review_id: UUID) -> tuple[str, str]:
    row = db.execute(
        "select decision::text, review_kind from review where id = %s", (review_id,)
    ).fetchone()
    assert row is not None
    return row


# review_kind (CLAUDE.md rule 11): the reviewer's actor_kind decides it; the trigger fills
# it when omitted and refuses a mismatch.


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_human_agronomist_review_is_agronomist_approved(
    db: psycopg.Connection, org_a: Org, decision: str
) -> None:
    rid = review(db, org_a, org_a.agronomist, decision)
    assert kind_of(db, rid) == (decision, "agronomist_approved")


def test_explicit_agronomist_approved_is_accepted(db: psycopg.Connection, org_a: Org) -> None:
    rid = review(db, org_a, org_a.agronomist, "approve", review_kind="agronomist_approved")
    assert kind_of(db, rid) == ("approve", "agronomist_approved")


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_service_review_is_ai_reviewed(db: psycopg.Connection, org_a: Org, decision: str) -> None:
    service = make_service(db, org_a)
    rid = review(db, org_a, service, decision)
    assert kind_of(db, rid) == (decision, "ai_reviewed")
    again = review(db, org_a, service, decision, review_kind="ai_reviewed")
    assert kind_of(db, again) == (decision, "ai_reviewed")


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_service_cannot_claim_agronomist_approved(
    db: psycopg.Connection, org_a: Org, decision: str
) -> None:
    service = make_service(db, org_a)
    with (
        pytest.raises(errors.InsufficientPrivilege, match="service account"),
        db.transaction(),
    ):
        review(db, org_a, service, decision, review_kind="agronomist_approved")


def test_human_agronomist_cannot_record_ai_reviewed(db: psycopg.Connection, org_a: Org) -> None:
    with (
        pytest.raises(errors.InsufficientPrivilege, match="only a service account"),
        db.transaction(),
    ):
        review(db, org_a, org_a.agronomist, "approve", review_kind="ai_reviewed")


def test_review_kind_values_are_checked(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.CheckViolation, match="review_kind"), db.transaction():
        review(db, org_a, org_a.agronomist, "approve", review_kind="human")


def test_ai_reviewed_is_not_a_decision(db: psycopg.Connection, org_a: Org) -> None:
    service = make_service(db, org_a)
    with pytest.raises(errors.InvalidTextRepresentation), db.transaction():
        review(db, org_a, service, "ai_reviewed")


def test_ai_review_needs_a_reason(db: psycopg.Connection, org_a: Org) -> None:
    service = make_service(db, org_a)
    with pytest.raises(errors.CheckViolation, match="review_ai_reason"), db.transaction():
        review(db, org_a, service, "approve", reason=None)


def test_service_cannot_edit(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    service = make_service(db, org_a)
    child = insert(
        db,
        "recommendation",
        organisation_id=org_a.id,
        crop_plan_id=org_a.crop_plan,
        parent_id=org_a.engine_rec,
        kind="agronomist",
        reason="Human edit (test)",
        created_by=org_a.agronomist,
        **recommendation_values(edited(engine_result, 80.0)),
    )
    with pytest.raises(errors.CheckViolation, match="review_ai_no_edit"), db.transaction():
        review(db, org_a, service, "edit", resulting_recommendation_id=child)


def test_staff_cannot_reject(db: psycopg.Connection, org_a: Org) -> None:
    # N16: the database gate covers reject too, not only approve.
    with pytest.raises(errors.InsufficientPrivilege, match="only an agronomist"), db.transaction():
        review(db, org_a, org_a.staff, "reject")


def test_service_cannot_hold_password(db: psycopg.Connection, org_a: Org) -> None:
    service = make_service(db, org_a)
    with (
        pytest.raises(errors.CheckViolation, match="app_user_service_no_password"),
        db.transaction(),
        as_role(db, "cp_admin"),  # cp_app cannot touch approver accounts at all (0014)
    ):
        db.execute("update app_user set password_hash = %s where id = %s", (HASH, service))
    with pytest.raises(errors.CheckViolation), as_role(db, "cp_admin"):
        insert(
            db,
            "app_user",
            email="svc2@example.org",
            display_name="Svc",
            actor_kind="service",
            password_hash=HASH,
        )


def test_human_with_password_cannot_become_service(db: psycopg.Connection) -> None:
    user = insert(db, "app_user", email="h@example.org", display_name="H", password_hash=HASH)
    with pytest.raises(errors.CheckViolation), as_role(db, "cp_admin"):
        db.execute("update app_user set actor_kind = 'service' where id = %s", (user,))


def test_cp_app_cannot_set_actor_kind(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute("update app_user set actor_kind = 'service' where id = %s", (org_a.staff,))
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(
            "insert into app_user (email, display_name, actor_kind)"
            " values ('s@example.org', 'S', 'service')"
        )


def test_cp_admin_can_set_actor_kind(db: psycopg.Connection, org_a: Org) -> None:
    with as_role(db, "cp_admin"):
        db.execute("update app_user set actor_kind = 'service' where id = %s", (org_a.staff,))
    row = db.execute("select actor_kind from app_user where id = %s", (org_a.staff,)).fetchone()
    assert row == ("service",)


# N11: temporary passwords expire (set by trigger; cp_app cannot write the column).


def expiry(db: psycopg.Connection, user: UUID) -> Any:
    row = db.execute(
        "select temp_password_expires_at - now() from app_user where id = %s", (user,)
    ).fetchone()
    assert row is not None
    return row[0]


def test_temporary_password_gets_expiry(db: psycopg.Connection, org_a: Org) -> None:
    assert expiry(db, org_a.staff) is None
    db.execute(
        "update app_user set password_hash = %s, password_change_required = true where id = %s",
        (HASH, org_a.staff),
    )
    assert expiry(db, org_a.staff) == timedelta(hours=72)
    # The user chooses their own password: the expiry is cleared.
    db.execute(
        "update app_user set password_hash = %s, password_change_required = false where id = %s",
        (HASH + "x", org_a.staff),
    )
    assert expiry(db, org_a.staff) is None


def test_created_with_temporary_password_gets_expiry(db: psycopg.Connection) -> None:
    user = insert(
        db,
        "app_user",
        email="t@example.org",
        display_name="T",
        password_hash=HASH,
        password_change_required=True,
    )
    assert expiry(db, user) == timedelta(hours=72)


def test_cp_app_cannot_write_expiry(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(
            "update app_user set temp_password_expires_at = now() + interval '1 year'"
            " where id = %s",
            (org_a.staff,),
        )


def test_expiry_requires_temporary_password(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.CheckViolation), as_owner(db):
        db.execute(
            "update app_user set temp_password_expires_at = now() where id = %s", (org_a.staff,)
        )
