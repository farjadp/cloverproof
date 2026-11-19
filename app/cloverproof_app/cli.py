"""Admin CLI. Accounts are created here only (no self sign-up, ADR 0005 A1).

    DATABASE_URL=... uv run python -m cloverproof_app.cli user-create \\
        --email name@example.org --org "CloverProof" --role agronomist [--create-org]

The password is read with getpass (asked twice), never from argv, and never echoed or
logged. Without a terminal it reads one line from stdin (for scripted setup).
Running it again for an existing email adds the membership; `--reset-password` also
replaces the password with a temporary one: all the user's sessions are revoked and they
must choose a new password at next sign-in (org admins can also reset in /admin/users).
Accounts created here are human (actor_kind = 'human'); service accounts are refused (B1).
Changes are recorded in admin_event by trigger with the database login as the actor (F2).

    ... cli user-unlock --email name@example.org
        Clears the per-account sign-in pause (security review S1) in the running app,
        through Postgres NOTIFY. If the app is not running, there is nothing to clear.

    ... cli user-revoke-sessions --email name@example.org
        Signs the user out on every device (security review S3); the password is unchanged.

    ... cli user-create ... --platform-role superadmin
    ... cli user-set-platform-role --email name@example.org --platform-role superadmin|none
        Platform role (migration 0012, decision 2026-11-16), human accounts only. A human
        superadmin may approve, edit and reject in organisations they are a member of
        (review_kind superadmin_approved, never calibration data). Audited in admin_event.

    ... cli soil-estimate-load --field <id> --season <id> --cache-dir <path> --as <email>
        Stores the cached SoilGrids values at the field's point (migration 0033), acting as the
        named human member of the field's organisation. Operator checkout only: the app image
        has no `data_sources`, and no request ever runs this. Never prints the coordinates.
        Steps: docs/runbook-soilgrids-cache.md.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg import errors
from psycopg.conninfo import make_conninfo

from cloverproof_app import security
from cloverproof_app.config import DEPLOYED_ENVS, is_local_database
from cloverproof_app.db.pool import set_rls_context
from cloverproof_app.ratelimit import UNLOCK_CHANNEL, account_key
from cloverproof_app.repo import admin_users, sessions, soil_estimates, users

ORG_ROLES = ("org_admin", "agronomist", "advisor")
PLATFORM_ROLES = ("superadmin",)  # platform `staff` comes with a later migration (RK-X11)
NO_ESTIMATE_REASONS = {
    "outside_cache": "the field's point is outside the cached area",
    "nodata": "SoilGrids has no prediction at the field's point (masked pixel)",
}


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
    platform_role: str | None = None,
) -> UserCreateResult:
    if role not in ORG_ROLES:
        raise CliError(f"role must be one of {', '.join(ORG_ROLES)}")
    if platform_role is not None and platform_role not in PLATFORM_ROLES:
        raise CliError(f"platform role must be one of {', '.join(PLATFORM_ROLES)}")
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
            if existing.actor_kind != "human":
                # B1/D4: this command manages people. A service account (AI reviewer) gets
                # no password and no roles from here.
                raise CliError("that is a service account; this command manages human accounts")
            if existing.disabled_at is not None:
                raise CliError("that account is disabled; re-enable it in /admin/users first")
            if reset_password:
                # Recovery: a temporary password; the user must change it at next sign-in.
                password = security.hash_password(read_password())
                admin_users.set_temporary_password(conn, user_id, password)
                password_set = True
        users.add_membership(conn, org_id=org_id, user_id=user_id, role=role)
        if platform_role is not None:
            users.set_platform_role(conn, user_id, platform_role)
    return UserCreateResult(user_id, org_id, created_user, created_org, password_set)


def user_set_platform_role(
    conn: psycopg.Connection, *, email: str, platform_role: str | None
) -> UUID:
    """Set (or clear with None) a human account's platform role. Audited by trigger (F2)."""
    if platform_role is not None and platform_role not in PLATFORM_ROLES:
        raise CliError(f"platform role must be one of {', '.join(PLATFORM_ROLES)}")
    with conn.transaction():
        creds = users.get_credentials_by_email(conn, email.strip())
        if creds is None:
            raise CliError("no user with that email")
        if creds.actor_kind != "human":
            raise CliError("that is a service account; platform roles are for human accounts")
        users.set_platform_role(conn, creds.id, platform_role)
        return creds.id


def user_unlock(conn: psycopg.Connection, *, email: str) -> None:
    """Tell the running app to clear the account's sign-in pause (delivered on commit)."""
    conn.execute("select pg_notify(%s, %s)", (UNLOCK_CHANNEL, account_key(email)))
    conn.commit()


def user_revoke_sessions(conn: psycopg.Connection, *, email: str) -> int:
    with conn.transaction():
        creds = users.get_credentials_by_email(conn, email.strip())
        if creds is None:
            raise CliError("no user with that email")
        return sessions.revoke_all_for_user(conn, creds.id)


@dataclass(frozen=True)
class SoilEstimateLoad:
    stored: int
    revision: int
    no_estimate_reason: str | None = None


def is_hosted_target(env: str, host: str) -> bool:
    """True for a deployed ENV, and for any non-local database whatever ENV says.

    ADR 0009 must hold when an operator's shell lacks ENV or still says `development`.
    """
    deployed = env.strip().lower() in DEPLOYED_ENVS
    return deployed or not is_local_database(make_conninfo(host=host))


def _soilgrids_lookup() -> tuple[Any, str]:
    # Imported here: the app image does not install data_sources (see Dockerfile).
    try:
        from data_sources.soilgrids import lookup_estimate
        from data_sources.soilgrids.catalog import LICENSE
    except ImportError as error:
        raise CliError(
            "soil-estimate-load needs the data_sources package, which the app image does not"
            " install; run it from an operator checkout after `uv sync`"
        ) from error
    return lookup_estimate, LICENSE


def _operator_context(
    conn: psycopg.Connection, email: str, field_id: UUID
) -> tuple[UUID, UUID, str]:
    """Set the RLS context of the named member; returns (user, organisation, record kind)."""
    creds = users.get_credentials_by_email(conn, email)
    if creds is None:
        raise CliError("no user with that email")
    if creds.actor_kind != "human":
        raise CliError("--as must name a person; that is a service account")
    if creds.disabled_at is not None:
        raise CliError("that account is disabled")
    for org in users.user_organisations(conn, creds.id):
        set_rls_context(conn, user_id=creds.id, org_id=org.id)
        kind = soil_estimates.field_record_kind(conn, org.id, field_id)
        if kind is not None:
            return creds.id, org.id, kind
    raise CliError("no such field in an organisation this user belongs to")


def _new_estimates(estimate: Any, licence: str) -> list[soil_estimates.NewEstimate]:
    return [
        soil_estimates.NewEstimate(
            property=v.property,
            depth_top_cm=v.depth_top_cm,
            depth_bottom_cm=v.depth_bottom_cm,
            statistic=v.statistic,
            value=v.value,
            unit=v.unit,
            value_q05=v.q05,
            value_q95=v.q95,
            uncertainty_ratio=v.uncertainty_ratio,
            source=v.provider.lower(),
            source_version=v.version,
            resolution_m=v.resolution_m,
            # The cache records a date; 0031 stores it as 00:00 UTC of that day.
            retrieved_at=datetime.combine(v.retrieved_on, time.min, UTC),
            licence=licence,
            attribution=estimate.attribution,
            citation=estimate.citation,
            layer_url=v.url,
        )
        for v in estimate.values
    ]


def soil_estimate_load(
    conn: psycopg.Connection,
    *,
    field_id: UUID,
    season_id: UUID,
    cache_dir: Path,
    operator_email: str,
    hosted: bool,
) -> SoilEstimateLoad:
    """Store the cached values at the field's point, all of them or none, in one transaction.

    Runs under the RLS context of a named, enabled human member of the field's organisation, so
    no policy changes and no privileged path are needed. The field stays locked from reading its
    point to commit. No message here may contain the point: third-party error text is dropped.
    """
    lookup_estimate, licence = _soilgrids_lookup()
    try:
        with conn.transaction():
            if hosted:
                row = conn.execute(
                    "select rolsuper or rolbypassrls from pg_roles where rolname = current_user"
                ).fetchone()
                if row is None or row[0]:
                    raise CliError("on a hosted database, log in as cp_app_login (RLS must apply)")
            user_id, org_id, record_kind = _operator_context(conn, operator_email, field_id)
            if hosted and record_kind == "real":
                raise CliError(
                    "refused: this field belongs to a real farmer and hosted environments hold"
                    " synthetic or de-identified data only (ADR 0009)"
                )
            if not soil_estimates.season_exists(conn, org_id, season_id):
                raise CliError("no such season in the field's organisation")
            point = soil_estimates.lock_field_point(conn, org_id, field_id)
            if point is None:
                raise CliError("this field has no location; add one on the field page first")
            try:
                result = lookup_estimate(float(point.lon), float(point.lat), cache_dir=cache_dir)
            except Exception as error:
                raise CliError(
                    f"the SoilGrids cache could not be read ({error.__class__.__name__});"
                    " check --cache-dir and docs/runbook-soilgrids-cache.md"
                ) from None
            if result.status == "no_estimate":
                reason = NO_ESTIMATE_REASONS[result.reason]
                return SoilEstimateLoad(0, point.revision, reason)
            rows = _new_estimates(result, licence)
            for estimate in rows:
                soil_estimates.insert_estimate(
                    conn,
                    org_id,
                    field_id=field_id,
                    season_id=season_id,
                    revision=point.revision,
                    created_by=user_id,
                    estimate=estimate,
                )
    except errors.UniqueViolation:
        raise CliError(
            "this retrieval is already stored for this field, season and location;"
            " nothing was changed"
        ) from None
    return SoilEstimateLoad(len(rows), point.revision)


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
    create.add_argument("--role", required=True, choices=ORG_ROLES)
    create.add_argument("--name", help="display name (default: part of the email before @)")
    create.add_argument("--create-org", action="store_true", help="create the org if missing")
    create.add_argument(
        "--reset-password",
        action="store_true",
        help="existing user: set a temporary password (must be changed at next sign-in)",
    )
    create.add_argument(
        "--platform-role", choices=PLATFORM_ROLES, help="also set this platform role"
    )
    platform = commands.add_parser(
        "user-set-platform-role", help="set or clear a human account's platform role"
    )
    platform.add_argument("--email", required=True)
    platform.add_argument(
        "--platform-role", required=True, choices=(*PLATFORM_ROLES, "none"),
        help="'none' clears it",
    )  # fmt: skip
    unlock = commands.add_parser(
        "user-unlock", help="clear the sign-in pause after too many failed attempts"
    )
    unlock.add_argument("--email", required=True)
    revoke = commands.add_parser(
        "user-revoke-sessions", help="sign the user out on every device (password unchanged)"
    )
    revoke.add_argument("--email", required=True)
    load = commands.add_parser(
        "soil-estimate-load", help="store cached SoilGrids values for a field and season"
    )
    load.add_argument("--field", required=True, type=UUID, help="field id")
    load.add_argument("--season", required=True, type=UUID, help="season id")
    load.add_argument("--cache-dir", required=True, type=Path, help="SoilGrids cache directory")
    load.add_argument(
        "--as", required=True, dest="operator", help="email of an enabled member of the org"
    )
    return parser


def run_command(conn: psycopg.Connection, args: argparse.Namespace) -> str:
    if args.command == "user-unlock":
        user_unlock(conn, email=args.email)
        return (
            f"unlock sent for {args.email.strip()} (account {account_key(args.email)[:12]});"
            " the app applies it at the next sign-in attempt"
        )
    if args.command == "user-set-platform-role":
        wanted = None if args.platform_role == "none" else args.platform_role
        user_set_platform_role(conn, email=args.email, platform_role=wanted)
        return f"platform role of {args.email.strip()}: {args.platform_role}"
    if args.command == "user-revoke-sessions":
        count = user_revoke_sessions(conn, email=args.email)
        return f"revoked {count} active session(s) for {args.email.strip()}"
    if args.command == "soil-estimate-load":
        load = soil_estimate_load(
            conn,
            field_id=args.field,
            season_id=args.season,
            cache_dir=args.cache_dir,
            operator_email=args.operator,
            hosted=is_hosted_target(os.environ.get("ENV", ""), conn.info.host),
        )
        if load.no_estimate_reason is not None:
            return f"no estimate stored: {load.no_estimate_reason}"
        return (
            f"stored {load.stored} estimate value(s) for field {args.field},"
            f" season {args.season}, location revision {load.revision}"
        )
    result = user_create(
        conn,
        email=args.email,
        org=args.org,
        role=args.role,
        display_name=args.name,
        create_org=args.create_org,
        reset_password=args.reset_password,
        read_password=prompt_password,
        platform_role=args.platform_role,
    )
    return (
        f"{'created' if result.created_user else 'existing'} user {result.user_id};"
        f" {'created' if result.created_org else 'existing'} organisation {result.org_id};"
        f" role {args.role}; password {'set' if result.password_set else 'unchanged'}"
        + (f"; platform role {args.platform_role}" if args.platform_role else "")
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("error: DATABASE_URL is not set", file=sys.stderr)
        return 2
    try:
        with psycopg.connect(url) as conn:
            message = run_command(conn, args)
    except (CliError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except psycopg.Error as error:
        # The message can quote a value (e.g. a rejected email), never the password.
        print(f"database error: {error.__class__.__name__}: {error}", file=sys.stderr)
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
