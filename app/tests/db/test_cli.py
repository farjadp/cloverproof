"""`user-create` CLI against a real database."""

import psycopg
import pytest

from cloverproof_app import cli, security
from cloverproof_app.repo import users

from .conftest import Org, as_role

pytestmark = pytest.mark.db

PASSWORD = "a long enough password"


def run(db: psycopg.Connection, **overrides: object) -> cli.UserCreateResult:
    values: dict[str, object] = {
        "email": "new.agronomist@example.org",
        "org": "New org",
        "role": "agronomist",
        "display_name": None,
        "create_org": True,
        "reset_password": False,
        "read_password": lambda: PASSWORD,
    }
    values.update(overrides)
    with as_role(db, "cp_admin"):  # the CLI logs in as cp_admin_login (ADR 0007)
        return cli.user_create(db, **values)  # type: ignore[arg-type]


def test_creates_org_user_and_membership(db: psycopg.Connection) -> None:
    result = run(db)
    assert result.created_user and result.created_org and result.password_set
    creds = users.get_credentials_by_email(db, "new.agronomist@example.org")
    assert creds is not None and creds.password_hash is not None
    assert creds.password_hash.startswith("$argon2id$")
    assert security.verify_password(PASSWORD, creds.password_hash)[0]
    assert users.has_org_role(db, user_id=result.user_id, org_id=result.org_id, role="agronomist")


def test_missing_org_without_flag_fails(db: psycopg.Connection) -> None:
    with pytest.raises(cli.CliError, match="--create-org"):
        run(db, create_org=False)


def test_existing_user_gets_membership_password_unchanged(
    db: psycopg.Connection, org_a: Org
) -> None:
    asked = []
    result = run(
        db,
        email="agro-a@example.org",
        org=str(org_a.id),
        role="org_admin",
        read_password=lambda: asked.append(1) or PASSWORD,
    )
    assert not result.created_user and not result.password_set and not asked
    assert users.org_roles(db, user_id=org_a.agronomist, org_id=org_a.id) == [
        "org_admin",
        "agronomist",
    ]


def test_reset_password(db: psycopg.Connection, org_a: Org) -> None:
    run(db, email="agro-a@example.org", org="Test org a", reset_password=True)
    creds = users.get_credentials_by_email(db, "agro-a@example.org")
    assert creds is not None and security.verify_password(PASSWORD, creds.password_hash)[0]


def test_short_password_rejected(db: psycopg.Connection) -> None:
    with pytest.raises(ValueError, match="at least"):
        run(db, read_password=lambda: "short")


def test_farmer_role_not_allowed(db: psycopg.Connection) -> None:
    with pytest.raises(cli.CliError, match="role"):
        run(db, role="farmer")
