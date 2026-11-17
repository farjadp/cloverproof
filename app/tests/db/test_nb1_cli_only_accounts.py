"""ciso NB1 (PR #7): an org owner cannot take over or lock out a superadmin or another
approver from the web. App refuses (repo + route); the database refuses too (0014).
The CLI (cp_admin) still resets them, and every change is in admin_event."""

from __future__ import annotations

import re
from uuid import UUID

import psycopg
import pytest
from psycopg import errors

from cloverproof_app import cli, security
from cloverproof_app.db.pool import set_rls_context
from cloverproof_app.repo import admin_users

from .conftest import Org, as_role, insert
from .test_account import client
from .test_admin_users import OWNER_EMAIL, flags, owner_client, post
from .test_superadmin import make_user
from .test_web_auth import PASSWORD, email_of, login, with_password

pytestmark = pytest.mark.db


def set_actor(db: psycopg.Connection, user_id: UUID) -> None:
    set_rls_context(db, user_id=user_id)


TEMP_PASSWORD = re.compile(r"([a-km-zA-HJ-NP-Z2-9]{5}-){3}[a-km-zA-HJ-NP-Z2-9]{5}")
HASH = security.hash_password("new password for nb1 tests")


@pytest.fixture
def owner(db: psycopg.Connection, org_a: Org) -> UUID:
    user = insert(db, "app_user", email=OWNER_EMAIL, display_name="Owner A")
    insert(db, "membership", organisation_id=org_a.id, user_id=user, role="org_admin")
    with_password(db, user)
    return user


@pytest.fixture
def superadmin(db: psycopg.Connection, org_a: Org) -> UUID:
    """The expected setup: a member of one org with only the staff role (ciso NB1)."""
    user = make_user(db, org_a, "super-a", roles=("advisor",), platform_role="superadmin")
    with_password(db, user)
    return user


def test_owner_cannot_reset_superadmin_on_the_web(
    db: psycopg.Connection, owner: UUID, superadmin: UUID
) -> None:
    c = owner_client(db)
    page = c.get(f"/admin/users/{superadmin}").text
    assert "Reset password</button>" not in page and "Disable account</button>" not in page
    before = flags(db, superadmin)
    response = post(c, f"/admin/users/{superadmin}/reset-password")
    assert response.status_code == 409 and "user-create" in response.text
    assert TEMP_PASSWORD.search(response.text) is None  # no temporary password shown
    assert flags(db, superadmin) == before
    # The superadmin still signs in with their own password; the owner learned nothing.
    assert login(client(db), email_of(db, superadmin), PASSWORD).status_code == 303


@pytest.mark.parametrize("action", ["disable", "enable"])
def test_owner_cannot_disable_or_enable_superadmin(
    db: psycopg.Connection, owner: UUID, superadmin: UUID, action: str
) -> None:
    before = flags(db, superadmin)
    response = post(owner_client(db), f"/admin/users/{superadmin}/{action}")
    assert response.status_code == 409 and "user-create" in response.text
    assert flags(db, superadmin) == before


def test_owner_cannot_disable_agronomist_on_the_web(
    db: psycopg.Connection, org_a: Org, owner: UUID
) -> None:
    response = post(owner_client(db), f"/admin/users/{org_a.agronomist}/disable")
    assert response.status_code == 409 and "user-create" in response.text
    assert flags(db, org_a.agronomist)[1] is False


def test_repo_refuses_platform_accounts(
    db: psycopg.Connection, org_a: Org, owner: UUID, superadmin: UUID
) -> None:
    with pytest.raises(admin_users.AdminError, match="platform"):
        admin_users.reset_password(
            db, org_id=org_a.id, user_id=superadmin, temporary_password_hash=HASH
        )
    with pytest.raises(admin_users.AdminError, match="platform"):
        admin_users.set_disabled(
            db, actor_id=owner, org_id=org_a.id, user_id=superadmin, disabled=True
        )


@pytest.mark.parametrize(
    "statement",
    [
        "update app_user set password_hash = %(h)s, password_change_required = true"
        " where id = %(id)s",
        "update app_user set password_hash = %(h)s where id = %(id)s",
        "update app_user set password_change_required = true where id = %(id)s",
        "update app_user set disabled_at = now() where id = %(id)s",
    ],
)
def test_db_refuses_cp_app_writes_to_approver_accounts(
    db: psycopg.Connection, org_a: Org, owner: UUID, superadmin: UUID, statement: str
) -> None:
    set_actor(db, owner)  # the owner page acting
    for target in (superadmin, org_a.agronomist):
        with pytest.raises(errors.InsufficientPrivilege, match="CLI only"), db.transaction():
            db.execute(statement, {"h": HASH, "id": target})
    # Unset actor (no session) is refused too.
    db.execute("select set_config('app.user_id', '', true)")
    with pytest.raises(errors.InsufficientPrivilege, match="CLI only"), db.transaction():
        db.execute(statement, {"h": HASH, "id": superadmin})


def test_db_refuses_owner_account_of_someone_else(
    db: psycopg.Connection, org_a: Org, owner: UUID
) -> None:
    second = insert(db, "app_user", email="owner2-a@example.org", display_name="Owner 2")
    insert(db, "membership", organisation_id=org_a.id, user_id=second, role="org_admin")
    set_actor(db, owner)
    with pytest.raises(errors.InsufficientPrivilege, match="CLI only"), db.transaction():
        db.execute("update app_user set disabled_at = now() where id = %s", (second,))


def test_cp_app_cannot_change_platform_role_or_actor_kind(
    db: psycopg.Connection, superadmin: UUID
) -> None:
    for statement in (
        "update app_user set platform_role = null where id = %s",
        "update app_user set actor_kind = 'service' where id = %s",
    ):
        with pytest.raises(errors.InsufficientPrivilege), db.transaction():
            db.execute(statement, (superadmin,))


def test_db_still_allows_own_password_and_staff_reset(
    db: psycopg.Connection, org_a: Org, owner: UUID, superadmin: UUID
) -> None:
    set_actor(db, superadmin)  # My account / login rehash: the holder's own change
    db.execute(
        "update app_user set password_hash = %s, password_change_required = false where id = %s",
        (HASH, superadmin),
    )
    set_actor(db, owner)  # owner resets a plain staff member: still allowed
    db.execute(
        "update app_user set password_hash = %s, password_change_required = true where id = %s",
        (HASH, org_a.staff),
    )
    assert flags(db, org_a.staff)[0] is True


def test_cli_resets_superadmin_and_it_is_audited(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    email = email_of(db, superadmin)
    with as_role(db, "cp_admin"):  # the CLI logs in as cp_admin_login (ADR 0007)
        result = cli.user_create(
            db, email=email, org=str(org_a.id), role="advisor", display_name=None,
            create_org=False, reset_password=True, read_password=lambda: "temporary password 9",
        )  # fmt: skip
    assert result.password_set
    required, _, stored = flags(db, superadmin)
    assert required is True and security.verify_password("temporary password 9", stored)[0]
    row = db.execute(
        "select action, actor_db_role from admin_event"
        " where target_user_id = %s order by at desc, id desc limit 1",
        (superadmin,),
    ).fetchone()
    assert row is not None and row[0] == "password_reset"
    assert login(client(db), email, "temporary password 9").status_code == 303


def test_refused_web_reset_leaves_no_audit_row(
    db: psycopg.Connection, owner: UUID, superadmin: UUID
) -> None:
    def resets() -> int:
        row = db.execute(
            "select count(*) from admin_event"
            " where target_user_id = %s and action = 'password_reset'",
            (superadmin,),
        ).fetchone()
        assert row is not None
        return row[0]

    before = resets()
    assert post(owner_client(db), f"/admin/users/{superadmin}/reset-password").status_code == 409
    assert resets() == before
