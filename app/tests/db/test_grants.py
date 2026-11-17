"""Least-privilege roles (migration 0011, ADR 0007; security review S5 and A1).

- cp_app cannot write organisation/membership and only some app_user columns, so it can
  never make anyone an approver; staff/farmer roles go through SECURITY DEFINER functions.
- cp_admin (CLI) keeps the identity writes.
- cp_website can only insert pilot requests.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import errors

from .conftest import Org, as_owner, as_role, insert

pytestmark = pytest.mark.db

DENIED = "permission denied"


def refused(db: psycopg.Connection, query: str, params: Any = None, match: str = DENIED) -> None:
    with pytest.raises(errors.InsufficientPrivilege, match=match), db.transaction():
        db.execute(query, params)  # type: ignore[arg-type]


def roles_of(db: psycopg.Connection, org_id: UUID, user_id: UUID) -> list[str]:
    rows = db.execute(
        "select m.role::text from membership m where m.organisation_id = %s and m.user_id = %s"
        " order by m.role",
        (org_id, user_id),
    ).fetchall()
    return [r[0] for r in rows]


@pytest.fixture
def owner(db: psycopg.Connection, org_a: Org) -> UUID:
    user = insert(db, "app_user", email="owner-a@example.org", display_name="Owner A")
    insert(db, "membership", organisation_id=org_a.id, user_id=user, role="owner")
    return user


# ---------------------------------------------------------------- cp_app


def test_roles_exist_without_login(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select rolname, rolcanlogin from pg_roles"
        " where rolname in ('cp_admin', 'cp_website') order by 1"
    ).fetchall()
    assert rows == [("cp_admin", False), ("cp_website", False)]
    assert db.execute("select pg_has_role('cp_admin', 'cp_app', 'usage')").fetchone() == (True,)
    assert db.execute("select pg_has_role('cp_app', 'cp_admin', 'member')").fetchone() == (False,)
    assert db.execute("select pg_has_role('cp_website', 'cp_app', 'member')").fetchone() == (False,)


@pytest.mark.parametrize(
    "query",
    [
        "insert into membership (organisation_id, user_id, role) values (%(org)s, %(user)s,"
        " 'agronomist')",
        "update membership set role = 'agronomist' where user_id = %(user)s",
        "delete from membership where user_id = %(user)s",
        "insert into organisation (name) values ('Rogue org')",
        "update organisation set name = 'Renamed' where id = %(org)s",
        "delete from organisation where id = %(org)s",
        "delete from app_user where id = %(user)s",
        "select 1 from membership where user_id = %(user)s for update",
    ],
)
def test_cp_app_cannot_write_identity(db: psycopg.Connection, org_a: Org, query: str) -> None:
    refused(db, query, {"org": org_a.id, "user": org_a.staff})
    assert roles_of(db, org_a.id, org_a.staff) == ["staff"]


@pytest.mark.parametrize(
    "assignment",
    [
        "email = 'other@example.org'",
        "totp_secret = 'x'",
        "auth_provider = 'oidc', external_subject = 'x'",
        "external_subject = 'x'",
        "created_at = now()",
        "id = gen_random_uuid()",
    ],
)
def test_cp_app_cannot_update_other_app_user_columns(
    db: psycopg.Connection, org_a: Org, assignment: str
) -> None:
    refused(db, f"update app_user set {assignment} where id = %s", (org_a.staff,))


def test_cp_app_updates_allowed_app_user_columns(db: psycopg.Connection, org_a: Org) -> None:
    db.execute(
        "update app_user set display_name = 'Renamed', password_change_required = true,"
        " disabled_at = now(), password_hash = null where id = %s",
        (org_a.staff,),
    )
    db.execute("update app_user set disabled_at = null where id = %s", (org_a.staff,))


def test_cp_app_inserts_app_user_with_allowed_columns_only(db: psycopg.Connection) -> None:
    insert(
        db, "app_user", email="new@example.org", display_name="New", password_change_required=True
    )
    refused(
        db,
        "insert into app_user (email, display_name, totp_secret)"
        " values ('t@example.org', 'T', 'x')",
    )
    refused(
        db,
        "insert into app_user (email, display_name, disabled_at)"
        " values ('d@example.org', 'D', now())",
    )


def test_cp_app_column_grants(db: psycopg.Connection) -> None:
    def columns(privilege: str) -> set[str]:
        rows = db.execute(
            "select attname from pg_attribute where attrelid = 'app_user'::regclass"
            " and attnum > 0 and not attisdropped"
            " and has_column_privilege('cp_app', 'app_user', attname, %s)",
            (privilege,),
        ).fetchall()
        return {r[0] for r in rows}

    assert columns("UPDATE") == {
        "display_name",
        "password_hash",
        "password_change_required",
        "disabled_at",
    }
    assert columns("INSERT") == {
        "email",
        "display_name",
        "password_hash",
        "password_change_required",
    }
    for table in ("organisation", "membership"):
        for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
            assert db.execute(
                "select has_table_privilege('cp_app', %s, %s)", (table, privilege)
            ).fetchone() == (False,)
        assert db.execute(
            "select has_table_privilege('cp_app', %s, 'SELECT')", (table,)
        ).fetchone() == (True,)


# ---------------------------------------------------------------- web role functions


def grant(db: psycopg.Connection, actor: UUID, org: UUID, user: UUID, role: str) -> None:
    db.execute("select web_grant_member_role(%s, %s, %s, %s)", (actor, org, user, role))


def revoke(db: psycopg.Connection, actor: UUID, org: UUID, user: UUID, role: str) -> None:
    db.execute("select web_revoke_member_role(%s, %s, %s, %s)", (actor, org, user, role))


def test_owner_grants_and_revokes_staff(db: psycopg.Connection, org_a: Org, owner: UUID) -> None:
    grant(db, owner, org_a.id, org_a.agronomist, "staff")
    assert roles_of(db, org_a.id, org_a.agronomist) == ["agronomist", "staff"]
    grant(db, owner, org_a.id, org_a.agronomist, "staff")  # idempotent
    revoke(db, owner, org_a.id, org_a.agronomist, "staff")
    assert roles_of(db, org_a.id, org_a.agronomist) == ["agronomist"]
    grant(db, owner, org_a.id, org_a.staff, "farmer")
    assert roles_of(db, org_a.id, org_a.staff) == ["staff", "farmer"]


def test_owner_adds_brand_new_user(db: psycopg.Connection, org_a: Org, owner: UUID) -> None:
    user = insert(db, "app_user", email="fresh@example.org", display_name="Fresh")
    grant(db, owner, org_a.id, user, "staff")
    assert roles_of(db, org_a.id, user) == ["staff"]


@pytest.mark.parametrize("role", ["agronomist", "owner"])
@pytest.mark.parametrize("fn", [grant, revoke])
def test_functions_refuse_agronomist_and_owner(
    db: psycopg.Connection, org_a: Org, owner: UUID, role: str, fn: Any
) -> None:
    target = org_a.staff if fn is grant else org_a.agronomist
    before = roles_of(db, org_a.id, target)
    with pytest.raises(errors.InsufficientPrivilege, match="CLI"), db.transaction():
        fn(db, owner, org_a.id, target, role)
    assert roles_of(db, org_a.id, target) == before


@pytest.mark.parametrize("fn", [grant, revoke])
def test_functions_refuse_non_owner_actor(
    db: psycopg.Connection, org_a: Org, org_b: Org, owner: UUID, fn: Any
) -> None:
    other_owner = insert(db, "app_user", email="owner-b@example.org", display_name="Owner B")
    insert(db, "membership", organisation_id=org_b.id, user_id=other_owner, role="owner")
    target = insert(db, "app_user", email="t@example.org", display_name="T")
    insert(db, "membership", organisation_id=org_a.id, user_id=target, role="staff")
    for actor in (org_a.agronomist, org_a.staff, other_owner):
        with pytest.raises(errors.InsufficientPrivilege, match="owner"), db.transaction():
            fn(db, actor, org_a.id, target, "staff")
    with as_owner(db):  # operator setup; cp_app cannot disable approvers (0014)
        db.execute("update app_user set disabled_at = now() where id = %s", (owner,))
    with pytest.raises(errors.InsufficientPrivilege, match="owner"), db.transaction():
        fn(db, owner, org_a.id, target, "staff")
    assert roles_of(db, org_a.id, target) == ["staff"]


def test_grant_refuses_member_of_another_org(
    db: psycopg.Connection, org_a: Org, org_b: Org, owner: UUID
) -> None:
    with (
        pytest.raises(errors.InsufficientPrivilege, match="another organisation"),
        db.transaction(),
    ):
        grant(db, owner, org_a.id, org_b.staff, "staff")
    assert roles_of(db, org_a.id, org_b.staff) == []


def test_functions_are_definer_with_pinned_search_path(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select p.proname, p.prosecdef, p.proconfig, pg_get_userbyid(p.proowner),"
        " has_function_privilege('cp_app', p.oid, 'execute'),"
        " has_function_privilege('cp_website', p.oid, 'execute')"
        " from pg_proc p where p.proname in ('web_grant_member_role', 'web_revoke_member_role')"
        " order by 1"
    ).fetchall()
    assert [r[0] for r in rows] == ["web_grant_member_role", "web_revoke_member_role"]
    for _, definer, config, owner, app_exec, website_exec in rows:
        assert definer is True and owner == "cp_migrator"
        assert config == ['search_path=""']
        assert app_exec is True and website_exec is False


# ---------------------------------------------------------------- cp_admin


def test_cp_admin_writes_identity(db: psycopg.Connection, org_a: Org) -> None:
    with as_role(db, "cp_admin"):
        org = db.execute("insert into organisation (name) values ('CLI org') returning id")
        org_id = org.fetchone()[0]  # type: ignore[index]
        db.execute(
            "insert into membership (organisation_id, user_id, role) values (%s, %s, 'agronomist')",
            (org_id, org_a.staff),
        )
        db.execute("update app_user set totp_secret = null where id = %s", (org_a.staff,))
        db.execute(
            "delete from membership where organisation_id = %s and user_id = %s",
            (org_id, org_a.staff),
        )
        # Inherits cp_app (sessions, farm data), but not the immutable-table bypass.
        refused(db, "delete from review")


# ---------------------------------------------------------------- cp_website

PILOT_INSERT = """
insert into pilot_request
  (locale, full_name, email, country, farm_size_text, main_crop, notes, consent_at, consent_text)
values ('en', 'Test Person', 'test@example.org', 'Canada', '100 ha', 'wheat', null, now(),
        'I agree.')
"""


def test_cp_website_can_only_insert_pilot_requests(db: psycopg.Connection, org_a: Org) -> None:
    with as_role(db, "cp_website"):
        db.execute(PILOT_INSERT)
        refused(db, "select count(*) from pilot_request")
        refused(db, PILOT_INSERT + " returning id")
        refused(db, "update pilot_request set status = 'accepted'")
        refused(db, "delete from pilot_request")
        refused(
            db,
            "insert into pilot_request (locale, full_name, email, country, farm_size_text,"
            " main_crop, consent_at, consent_text, status) values ('en', 'X', 'x@example.org',"
            " 'CA', '1 ha', 'wheat', now(), 'ok', 'accepted')",
        )
        for table in ("app_user", "user_session", "membership", "organisation", "recommendation"):
            refused(db, f"select 1 from {table} limit 1")
        refused(db, "insert into organisation (name) values ('Website org')")
        refused(db, "select web_grant_member_role(%s, %s, %s, 'staff')", (org_a.staff,) * 3)
    with as_owner(db):
        row = db.execute("select count(*) from pilot_request where email = 'test@example.org'")
        assert row.fetchone() == (1,)
