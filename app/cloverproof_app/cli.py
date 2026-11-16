"""Admin CLI. Accounts are created here only (no self sign-up, ADR 0005 A1).

    DATABASE_URL=... uv run python -m cloverproof_app.cli user-create \\
        --email name@example.org --org "CloverProof" --role agronomist [--create-org]

The password is read with getpass (asked twice), never from argv, and never echoed or
logged. Without a terminal it reads one line from stdin (for scripted setup).
Running it again for an existing email adds the membership; `--reset-password` also
replaces the password with a temporary one: all the user's sessions are revoked and they
must choose a new password at next sign-in (owners can also reset in /admin/users).
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import psycopg

from cloverproof_app import security
from cloverproof_app.repo import admin_users, users

STAFF_ROLES = ("owner", "agronomist", "staff")


class CliError(RuntimeError):
    pass


@dataclass(frozen=True)
class UserCreateResult:
    user_id: UUID
    org_id: UUID
    created_user: bool
    created_org: bool
    password_set: bool


def resolve_org(conn: psycopg.Connection, org: str, create: bool) -> tuple[UUID, bool]:
    try:
        org_id = UUID(org)
    except ValueError:
        pass
    else:
        row = conn.execute("select id from organisation where id = %s", (org_id,)).fetchone()
        if row is None:
            raise CliError("no organisation with that id")
        return org_id, False
    matches = users.find_organisation_by_name(conn, org)
    if len(matches) > 1:
        raise CliError(f"{len(matches)} organisations are named {org!r}; pass the id instead")
    if matches:
        return matches[0].id, False
    if not create:
        raise CliError(f"no organisation named {org!r}; add --create-org to create it")
    return users.create_organisation(conn, org), True


def user_create(
    conn: psycopg.Connection,
    *,
    email: str,
    org: str,
    role: str,
    display_name: str | None,
    create_org: bool,
    reset_password: bool,
    read_password: Callable[[], str],
) -> UserCreateResult:
    if role not in STAFF_ROLES:
        raise CliError(f"role must be one of {', '.join(STAFF_ROLES)}")
    with conn.transaction():
        org_id, created_org = resolve_org(conn, org, create_org)
        existing = users.get_credentials_by_email(conn, email)
        password_set = False
        if existing is None:
            password_hash = security.hash_password(read_password())
            name = (display_name or email.split("@")[0]).strip()
            user_id = users.create_user(
                conn, email=email, display_name=name, password_hash=password_hash
            )
            created_user = password_set = True
        else:
            user_id, created_user = existing.id, False
            if existing.disabled_at is not None:
                raise CliError("that account is disabled; re-enable it in /admin/users first")
            if reset_password:
                # Recovery: a temporary password; the user must change it at next sign-in.
                password = security.hash_password(read_password())
                admin_users.set_temporary_password(conn, user_id, password)
                password_set = True
        users.add_membership(conn, org_id=org_id, user_id=user_id, role=role)
    return UserCreateResult(user_id, org_id, created_user, created_org, password_set)


def prompt_password() -> str:
    if not sys.stdin.isatty():
        line = sys.stdin.readline().rstrip("\n")
        if not line:
            raise CliError("no password on stdin")
        return line
    first = getpass.getpass("Password (min 12 characters): ")
    if len(first) < security.MIN_PASSWORD_LENGTH:
        raise CliError(f"password must be at least {security.MIN_PASSWORD_LENGTH} characters")
    if getpass.getpass("Repeat password: ") != first:
        raise CliError("passwords do not match")
    return first


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cloverproof_app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("user-create", help="create a user and/or add a membership")
    create.add_argument("--email", required=True)
    create.add_argument("--org", required=True, help="organisation name or id")
    create.add_argument("--role", required=True, choices=STAFF_ROLES)
    create.add_argument("--name", help="display name (default: part of the email before @)")
    create.add_argument("--create-org", action="store_true", help="create the org if missing")
    create.add_argument(
        "--reset-password",
        action="store_true",
        help="existing user: set a temporary password (must be changed at next sign-in)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("error: DATABASE_URL is not set", file=sys.stderr)
        return 2
    try:
        with psycopg.connect(url) as conn:
            result = user_create(
                conn,
                email=args.email,
                org=args.org,
                role=args.role,
                display_name=args.name,
                create_org=args.create_org,
                reset_password=args.reset_password,
                read_password=prompt_password,
            )
    except (CliError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except psycopg.Error as error:
        # The message can quote a value (e.g. a rejected email), never the password.
        print(f"database error: {error.__class__.__name__}: {error}", file=sys.stderr)
        return 1
    print(
        f"{'created' if result.created_user else 'existing'} user {result.user_id};"
        f" {'created' if result.created_org else 'existing'} organisation {result.org_id};"
        f" role {args.role}; password {'set' if result.password_set else 'unchanged'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
