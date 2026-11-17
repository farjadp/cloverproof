"""Migration 0015: organisation roles owner -> org_admin, staff -> advisor (RK-X11 = A).

The other identity tests (test_grants, test_admin_users, test_nb1_cli_only_accounts) run
on the new labels; this file pins the enum itself and the app's constants.
"""

from __future__ import annotations

import psycopg
import pytest
from psycopg import errors

from cloverproof_app import auth, cli
from cloverproof_app.repo import admin_users

from .conftest import Org

pytestmark = pytest.mark.db

NEW_LABELS = ["org_admin", "agronomist", "advisor", "farmer"]


def test_enum_has_the_new_labels_only(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select e.enumlabel from pg_enum e join pg_type t on t.oid = e.enumtypid"
        " where t.typname = 'membership_role' order by e.enumsortorder"
    ).fetchall()
    assert [r[0] for r in rows] == NEW_LABELS


@pytest.mark.parametrize("old", ["owner", "staff"])
def test_old_labels_are_invalid(db: psycopg.Connection, old: str) -> None:
    with pytest.raises(errors.InvalidTextRepresentation), db.transaction():
        db.execute("select %s::membership_role", (old,))


def test_app_constants_use_the_new_labels() -> None:
    assert auth.INTERNAL_ROLES == ("org_admin", "agronomist", "advisor")
    assert admin_users.INTERNAL_ROLES == auth.INTERNAL_ROLES
    assert admin_users.WEB_ROLES == ("advisor",)
    assert admin_users.CLI_ONLY_ROLES == ("org_admin", "agronomist")
    assert cli.ORG_ROLES == auth.INTERNAL_ROLES


def test_no_function_names_an_old_label(db: psycopg.Connection) -> None:
    """Every function body that compared with 'owner'/'staff' was recreated in 0015."""
    rows = db.execute(
        "select p.proname from pg_proc p where p.pronamespace = 'public'::regnamespace"
        " and (p.prosrc ~ '''owner''' or p.prosrc ~ '''staff''')"
    ).fetchall()
    assert rows == []


def test_fixture_advisor_holds_the_advisor_role(db: psycopg.Connection, org_a: Org) -> None:
    row = db.execute(
        "select role::text from membership where organisation_id = %s and user_id = %s",
        (org_a.id, org_a.staff),
    ).fetchone()
    assert row == ("advisor",)
