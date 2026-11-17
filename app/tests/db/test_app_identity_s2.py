"""App side of the S2 delta review (PR #7) for identity: B1 sign-in and CLI, F2 audit
actor, N11 temporary password expiry (real database, migration 0012)."""

from __future__ import annotations

from uuid import UUID

import psycopg
import pytest

from cloverproof_app import cli, security

from .conftest import Org, as_owner, as_role, insert
from .test_plan_flow import signed_in
from .test_web_auth import PASSWORD, build_client, email_of, login

pytestmark = pytest.mark.db


def make_service(db: psycopg.Connection, org: Org) -> UUID:
    with as_role(db, "cp_admin"):
        user = insert(
            db, "app_user", email="cp-agronomist@example.org", display_name="AI reviewer",
            actor_kind="service",
        )  # fmt: skip
    insert(db, "membership", organisation_id=org.id, user_id=user, role="agronomist")
    return user


def test_service_account_cannot_sign_in(db: psycopg.Connection, org_a: Org) -> None:
    make_service(db, org_a)
    c = build_client(db)
    r = login(c, "cp-agronomist@example.org", PASSWORD)
    assert r.status_code == 401 and "Email or password is incorrect" in r.text


def test_cli_refuses_service_accounts(db: psycopg.Connection, org_a: Org) -> None:
    make_service(db, org_a)
    with pytest.raises(cli.CliError, match="service account"), as_role(db, "cp_admin"):
        cli.user_create(
            db, email="cp-agronomist@example.org", org=str(org_a.id), role="agronomist",
            display_name=None, create_org=False, reset_password=True,
            read_password=lambda: "a long enough password",
        )  # fmt: skip


def test_cli_creates_humans(db: psycopg.Connection) -> None:
    with as_role(db, "cp_admin"):
        result = cli.user_create(
            db, email="person@example.org", org="CLI org", role="agronomist", display_name=None,
            create_org=True, reset_password=False, read_password=lambda: "a long enough password",
        )  # fmt: skip
    row = db.execute("select actor_kind from app_user where id = %s", (result.user_id,))
    assert row.fetchone() == ("human",)


# --- F2: admin and account changes record the acting user ------------------------------


def audit(db: psycopg.Connection, target: UUID) -> list[tuple[str, UUID | None]]:
    rows = db.execute(
        "select action, actor_user_id from admin_event where target_user_id = %s order by at, id",
        (target,),
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def test_admin_actions_record_the_owner(db: psycopg.Connection, org_a: Org) -> None:
    owner = insert(db, "app_user", email="owner-a@example.org", display_name="Owner A")
    insert(db, "membership", organisation_id=org_a.id, user_id=owner, role="owner")
    client, csrf = signed_in(db, owner)
    r = client.post(
        "/admin/users",
        data={"csrf_token": csrf, "email": "new@example.org", "display_name": "New",
              "role": "staff"},
    )  # fmt: skip
    assert r.status_code == 200
    new = db.execute("select id from app_user where email = 'new@example.org'").fetchone()
    assert new is not None
    assert (
        client.post(f"/admin/users/{new[0]}/disable", data={"csrf_token": csrf}).status_code == 303
    )
    assert audit(db, new[0]) == [
        ("user_created", owner),
        ("membership_granted", owner),
        ("user_disabled", owner),
    ]


def test_own_password_change_records_the_user(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    r = client.post(
        "/account/password",
        data={"csrf_token": csrf, "current_password": PASSWORD,
              "new_password": "another long password", "confirm_password": "another long password"},
    )  # fmt: skip
    assert r.status_code == 303
    assert audit(db, org_a.agronomist)[-1] == ("password_set", org_a.agronomist)


# --- N11: expired temporary passwords ---------------------------------------------------


def test_expired_temporary_password_gets_the_generic_error(
    db: psycopg.Connection, org_a: Org
) -> None:
    db.execute(
        "update app_user set password_hash = %s, password_change_required = true where id = %s",
        (security.hash_password(PASSWORD), org_a.staff),
    )
    email = email_of(db, org_a.staff)
    assert login(build_client(db), email).status_code == 303  # still valid
    with as_owner(db):
        db.execute(
            "update app_user set temp_password_expires_at = now() - interval '1 minute'"
            " where id = %s",
            (org_a.staff,),
        )
    r = login(build_client(db), email)
    assert r.status_code == 401 and "Email or password is incorrect" in r.text
