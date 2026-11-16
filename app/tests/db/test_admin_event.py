"""Append-only audit of the actions that create approvers (migration 0012, review F2).

Rows are written only by triggers on `membership` and `app_user`, whoever changes them
(web functions as cp_app, CLI as cp_admin, an operator in psql). The app identifies the
acting user with `SET LOCAL app.user_id = '<uuid>'`; without it only the database login
(`session_user`) is recorded.
"""

from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import errors

from .conftest import Org, as_owner, as_role, insert

pytestmark = pytest.mark.db

HASH = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA"


def events(db: psycopg.Connection, target: UUID) -> list[tuple[Any, ...]]:
    return db.execute(
        "select action, actor_user_id, organisation_id, old_value, new_value"
        " from admin_event where target_user_id = %s order by at, id",
        (target,),
    ).fetchall()


def set_actor(db: psycopg.Connection, user: UUID) -> None:
    db.execute("select set_config('app.user_id', %s, true)", (str(user),))


@pytest.fixture
def owner(db: psycopg.Connection, org_a: Org) -> UUID:
    user = insert(db, "app_user", email="owner-a@example.org", display_name="Owner A")
    insert(db, "membership", organisation_id=org_a.id, user_id=user, role="owner")
    return user


def test_user_creation_and_memberships_are_recorded(db: psycopg.Connection, org_a: Org) -> None:
    rows = events(db, org_a.agronomist)
    assert [r[0] for r in rows] == ["user_created", "membership_granted"]
    assert rows[1][2] == org_a.id
    assert rows[1][4] == {"role": "agronomist"}
    # No PII and no hash in the audit row.
    assert rows[0][4] == {
        "actor_kind": "human",
        "has_password": False,
        "password_change_required": False,
        "disabled": False,
    }


def test_web_grant_and_revoke_record_the_actor(
    db: psycopg.Connection, org_a: Org, owner: UUID
) -> None:
    set_actor(db, owner)
    target = insert(db, "app_user", email="new@example.org", display_name="New")
    db.execute("select web_grant_member_role(%s, %s, %s, 'staff')", (owner, org_a.id, target))
    db.execute("select web_revoke_member_role(%s, %s, %s, 'staff')", (owner, org_a.id, target))
    rows = events(db, target)
    assert [(r[0], r[1]) for r in rows] == [
        ("user_created", owner),
        ("membership_granted", owner),
        ("membership_revoked", owner),
    ]
    assert rows[2][3] == {"role": "staff"}


def test_cli_change_records_the_db_login(db: psycopg.Connection, org_a: Org) -> None:
    with as_role(db, "cp_admin"):
        db.execute(
            "update membership set role = 'owner' where user_id = %s and role = 'staff'",
            (org_a.staff,),
        )
    row = db.execute(
        "select action, actor_user_id, actor_db_role = session_user, old_value, new_value"
        " from admin_event where target_user_id = %s and action = 'membership_changed'",
        (org_a.staff,),
    ).fetchone()
    assert row == ("membership_changed", None, True, {"role": "staff"}, {"role": "owner"})


def test_password_reset_is_recorded(db: psycopg.Connection, org_a: Org, owner: UUID) -> None:
    set_actor(db, owner)
    db.execute(
        "update app_user set password_hash = %s, password_change_required = true where id = %s",
        (HASH, org_a.staff),
    )
    action, actor, _, old, new = events(db, org_a.staff)[-1]
    assert (action, actor) == ("password_reset", owner)
    assert old == {"has_password": False, "password_change_required": False}
    assert new == {"has_password": True, "password_change_required": True}


def test_disable_and_actor_kind_are_recorded(db: psycopg.Connection, org_a: Org) -> None:
    db.execute("update app_user set disabled_at = now() where id = %s", (org_a.staff,))
    with as_role(db, "cp_admin"):
        db.execute("update app_user set actor_kind = 'service' where id = %s", (org_a.staff,))
    actions = [r[0] for r in events(db, org_a.staff)]
    assert actions[-2:] == ["user_disabled", "actor_kind_changed"]


def test_unaudited_change_writes_nothing(db: psycopg.Connection, org_a: Org) -> None:
    before = len(events(db, org_a.staff))
    db.execute("update app_user set display_name = 'Renamed' where id = %s", (org_a.staff,))
    db.execute(
        "update app_user set disabled_at = null where id = %s", (org_a.staff,)
    )  # already null: no change
    assert len(events(db, org_a.staff)) == before


def test_invalid_actor_setting_is_refused(db: psycopg.Connection, org_a: Org) -> None:
    db.execute("select set_config('app.user_id', 'not-a-uuid', true)")
    with pytest.raises(errors.InvalidParameterValue), db.transaction():
        db.execute("update app_user set disabled_at = now() where id = %s", (org_a.staff,))


def test_cp_app_cannot_write_admin_event(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(
            "insert into admin_event (target_user_id, action) values (%s, 'user_created')",
            (org_a.staff,),
        )
    for statement in ("update admin_event set action = 'x'", "delete from admin_event"):
        with pytest.raises(errors.InsufficientPrivilege), db.transaction():
            db.execute(statement)


@pytest.mark.parametrize(
    "statement",
    [
        "update admin_event set action = 'user_created'",
        "delete from admin_event",
        "truncate admin_event",
    ],
)
def test_admin_event_is_immutable_even_for_owner(
    db: psycopg.Connection, org_a: Org, statement: str
) -> None:
    assert events(db, org_a.staff)  # rows exist, so row-level triggers fire
    with pytest.raises(errors.InsufficientPrivilege, match="immutable"), as_owner(db):
        db.execute(statement)
