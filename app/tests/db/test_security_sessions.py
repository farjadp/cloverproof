"""S3 (security review S2-auth-review-step5): revoke every session of a user."""

from __future__ import annotations

from datetime import timedelta

import psycopg
import pytest

from cloverproof_app import cli
from cloverproof_app.repo import sessions

from .conftest import Org, as_role
from .test_web_auth import PASSWORD, build_client, email_of, login, with_password

pytestmark = pytest.mark.db

NEW_PASSWORD = "a brand new long password"


def active(db: psycopg.Connection, user_id: object) -> int:
    row = db.execute(
        "select count(*) from user_session where user_id = %s and revoked_at is null", (user_id,)
    ).fetchone()
    assert row is not None
    return row[0]


def test_revoke_all_for_user_only_touches_that_user(db: psycopg.Connection, org_a: Org) -> None:
    for i in range(3):
        sessions.create_session(
            db, user_id=org_a.agronomist, token_sha256=f"{i:064x}", absolute=timedelta(hours=1)
        )
    sessions.create_session(
        db, user_id=org_a.staff, token_sha256="f" * 64, absolute=timedelta(hours=1)
    )
    assert sessions.revoke_all_for_user(db, org_a.agronomist) == 3
    assert active(db, org_a.agronomist) == 0 and active(db, org_a.staff) == 1
    assert sessions.revoke_all_for_user(db, org_a.agronomist) == 0  # idempotent


def test_cli_reset_password_kills_a_pre_reset_cookie(db: psycopg.Connection, org_a: Org) -> None:
    with_password(db, org_a.agronomist)
    email = email_of(db, org_a.agronomist)
    attacker = build_client(db)
    assert login(attacker, email).status_code == 303
    assert attacker.get("/").status_code == 200

    with as_role(db, "cp_admin"):  # the CLI logs in as cp_admin_login (ADR 0006)
        cli.user_create(
            db,
            email=email,
            org=str(org_a.id),
            role="agronomist",
            display_name=None,
            create_org=False,
            reset_password=True,
            read_password=lambda: NEW_PASSWORD,
        )
    assert attacker.get("/").status_code == 401
    assert attacker.get("/", headers={"accept": "text/html"}).status_code == 303
    assert active(db, org_a.agronomist) == 0


def test_cli_revoke_sessions_signs_the_user_out_everywhere(
    db: psycopg.Connection, org_a: Org
) -> None:
    with_password(db, org_a.agronomist)
    email = email_of(db, org_a.agronomist)
    laptop, phone = build_client(db), build_client(db)
    login(laptop, email)
    login(phone, email)
    with as_role(db, "cp_admin"):
        assert cli.user_revoke_sessions(db, email=email.upper()) == 2
    assert laptop.get("/").status_code == 401 and phone.get("/").status_code == 401
    # The password still works: this is "sign out everywhere", not a reset.
    assert login(build_client(db), email, PASSWORD).status_code == 303


def test_cli_revoke_sessions_unknown_email_is_explicit(db: psycopg.Connection) -> None:
    with as_role(db, "cp_admin"), pytest.raises(cli.CliError, match="no user"):
        cli.user_revoke_sessions(db, email="nobody@example.org")


def test_cli_revoke_sessions_command_is_wired() -> None:
    args = cli.build_parser().parse_args(["user-revoke-sessions", "--email", "a@b.org"])
    assert args.command == "user-revoke-sessions" and args.email == "a@b.org"
