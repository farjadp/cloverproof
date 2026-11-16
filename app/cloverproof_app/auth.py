"""Request dependencies: DB connection, session, current user, organisation, roles, CSRF.

- `current_user`: 401 when not signed in (browser GETs are redirected to /login). While
  the account has `password_change_required` (admin-set temporary password), every path
  except /account/password and /logout raises `PasswordChangeRequired` (handled by
  `account.register`: redirect to the change-password form).
- `current_org`: the user's only organisation, or the one picked on /orgs/choose (kept in
  a cookie signed with SESSION_SECRET and bound to the session; membership is re-checked
  on every request).
- `require_org_role(*roles)`: 403 unless the user holds one of the roles in that org.
- `csrf_guard`: app-wide; every non-GET needs the per-session token, as form field
  `csrf_token` or header `X-CSRF-Token` (HTMX sends it via `hx-headers` in base.html).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import Depends, HTTPException, Request

from cloverproof_app import security
from cloverproof_app.config import Settings
from cloverproof_app.repo import admin_users, sessions, users
from cloverproof_app.repo.users import Organisation

SESSION_COOKIE = "cp_session"
ORG_COOKIE = "cp_org"
LOGIN_CSRF_COOKIE = "cp_login_csrf"
CSRF_HEADER = "X-CSRF-Token"
CSRF_FIELD = "csrf_token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
TOUCH_EVERY = timedelta(seconds=60)
PASSWORD_CHANGE_PATH = "/account/password"
PASSWORD_CHANGE_EXEMPT = frozenset({PASSWORD_CHANGE_PATH, "/logout"})

# Roles that may use the internal tool at all. `farmer` is for the Phase 4 portal.
INTERNAL_ROLES = ("owner", "agronomist", "staff")


class NotAuthenticated(Exception):
    """No live session. Handled in main.py: redirect browsers, 401 for the rest."""


class PasswordChangeRequired(Exception):
    """Signed in with a temporary password. Handled by account.register: go to the form."""


class OrgSelectionRequired(Exception):
    """Several organisations and none chosen yet. Handled in main.py: go to the chooser."""


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str
    display_name: str
    session_id: UUID
    token_sha256: str
    actor_kind: str = "human"

    @property
    def is_human(self) -> bool:
        return self.actor_kind == "human"


@dataclass(frozen=True)
class OrgContext:
    user: CurrentUser
    org: Organisation
    roles: tuple[str, ...]
    organisations: tuple[Organisation, ...]


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def db_conn(request: Request) -> Iterator[psycopg.Connection]:
    # Used with scope="function": the transaction commits before the response is sent,
    # so a failed commit becomes an error response instead of silently lost data.
    with request.app.state.database.connection() as conn:
        yield conn


Conn = Annotated[psycopg.Connection, Depends(db_conn, scope="function")]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def session_token_hash(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    return security.token_sha256(token) if token else None


def optional_user(request: Request, conn: Conn, settings: SettingsDep) -> CurrentUser | None:
    token_hash = session_token_hash(request)
    if token_hash is None:
        return None
    live = sessions.get_active_session(
        conn, token_sha256=token_hash, idle=timedelta(minutes=settings.session_idle_minutes)
    )
    if live is None:
        return None
    if datetime.now(UTC) - live.last_seen_at > TOUCH_EVERY:
        sessions.touch_session(conn, live.session_id)
    user = CurrentUser(
        live.user_id, live.email, live.display_name, live.session_id, token_hash, live.actor_kind
    )
    users.set_actor(conn, user.id)  # F2: admin_event records this user for the request
    request.state.user = user
    request.state.csrf_token = security.csrf_token(settings.session_secret, token_hash)
    return user


def current_user(
    request: Request, user: Annotated[CurrentUser | None, Depends(optional_user)], conn: Conn
) -> CurrentUser:
    if user is None:
        raise NotAuthenticated()
    if request.url.path not in PASSWORD_CHANGE_EXEMPT and admin_users.password_change_required(
        conn, user.id
    ):
        raise PasswordChangeRequired()
    return user


UserDep = Annotated[CurrentUser, Depends(current_user)]


def org_cookie_value(settings: Settings, user: CurrentUser, org_id: UUID) -> str:
    signature = security.sign(settings.session_secret, f"org:{user.session_id}", str(org_id))
    return f"{org_id}.{signature}"


def chosen_org_id(request: Request, settings: Settings, user: CurrentUser) -> UUID | None:
    raw = request.cookies.get(ORG_COOKIE, "")
    org_part, _, signature = raw.partition(".")
    try:
        org_id = UUID(org_part)
    except ValueError:
        return None
    expected = org_cookie_value(settings, user, org_id).partition(".")[2]
    return org_id if security.same(signature, expected) else None


def current_org(request: Request, user: UserDep, conn: Conn, settings: SettingsDep) -> OrgContext:
    organisations = tuple(users.user_organisations(conn, user.id))
    if not organisations:
        raise HTTPException(403, "Your account is not a member of any organisation.")
    if len(organisations) == 1:
        org = organisations[0]
    else:
        wanted = chosen_org_id(request, settings, user)
        org = next((o for o in organisations if o.id == wanted), None)
        if org is None:
            raise OrgSelectionRequired()
    roles = tuple(users.org_roles(conn, user_id=user.id, org_id=org.id))
    context = OrgContext(user, org, roles, organisations)
    request.state.org = context
    return context


OrgDep = Annotated[OrgContext, Depends(current_org)]


def require_org_role(*roles: str) -> Callable[..., OrgContext]:
    """Dependency: the current user must hold at least one of `roles` in the current org."""
    if not roles:
        raise ValueError("require_org_role needs at least one role")

    def dependency(context: OrgDep, conn: Conn) -> OrgContext:
        for role in roles:
            if users.has_org_role(conn, user_id=context.user.id, org_id=context.org.id, role=role):
                return context
        raise HTTPException(403, f"This needs the {' or '.join(roles)} role.")

    return dependency


async def csrf_guard(request: Request, settings: SettingsDep) -> None:
    """App-wide dependency. Rejects any non-GET request without a valid CSRF token."""
    if request.method in SAFE_METHODS:
        return
    sent = request.headers.get(CSRF_HEADER)
    if sent is None and request.headers.get("content-type", "").startswith(
        ("application/x-www-form-urlencoded", "multipart/form-data")
    ):
        form = await request.form()  # cached by Starlette; the route reads the same form
        value = form.get(CSRF_FIELD)
        sent = value if isinstance(value, str) else None
    if request.url.path == "/login":
        # No session yet: double-submit cookie set by GET /login.
        expected = request.cookies.get(LOGIN_CSRF_COOKIE)
    else:
        token_hash = session_token_hash(request)
        expected = security.csrf_token(settings.session_secret, token_hash) if token_hash else None
    if not security.same(sent, expected):
        raise HTTPException(403, "Security check failed (missing or invalid CSRF token).")
