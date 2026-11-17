"""My account (/account) and org admin user management (/admin/users).

Register with `account.register(app)` in main.create_app: it includes `router` and the
`PasswordChangeRequired` handler (redirect to /account/password). Idempotent.

Temporary passwords (new user, admin reset) are generated here, shown once in the POST
response (Cache-Control: no-store from main.py) and stored only as an argon2id hash with
`password_change_required = true`. No email is sent; the org admin hands the password over.
"""

from __future__ import annotations

import logging
import re
import secrets
from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response

from cloverproof_app import security
from cloverproof_app.auth import (
    INTERNAL_ROLES,
    PASSWORD_CHANGE_PATH,
    Conn,
    OrgContext,
    PasswordChangeRequired,
    UserDep,
    require_org_role,
)
from cloverproof_app.ratelimit import LoginRateLimiter
from cloverproof_app.repo import admin_users
from cloverproof_app.repo.admin_users import CLI_ONLY, CLI_ONLY_ROLES, WEB_ROLES, AdminError
from cloverproof_app.web import client_ip, render

log = logging.getLogger(__name__)
router = APIRouter()

InternalOrg = Annotated[OrgContext, Depends(require_org_role(*INTERNAL_ROLES))]
OrgAdminOrg = Annotated[OrgContext, Depends(require_org_role("org_admin"))]

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
MAX_PASSWORD = 1024
ROLE_LABELS = {
    "org_admin": "Org admin",
    "agronomist": "Agronomist",
    "advisor": "Advisor",
    "farmer": "Farmer",
}

# No 0/O/1/l/I: the org admin reads it out or copies it. 20 symbols from 55 = ~115 bits.
TEMP_ALPHABET = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TEMP_GROUPS, TEMP_GROUP_LEN = 4, 5

NAME_SAVED = "Name saved."
PASSWORD_SAVED = "Password changed. You were signed out everywhere else."
WRONG_CURRENT = "Current password is incorrect."
TOO_SHORT = f"New password must be at least {security.MIN_PASSWORD_LENGTH} characters."
NO_MATCH = "The two new passwords do not match."
SAME_AS_CURRENT = "Choose a password different from the current one."
TOO_MANY = "Too many wrong attempts. Wait {minutes} minutes and try again."


def new_temporary_password() -> str:
    groups = (
        "".join(secrets.choice(TEMP_ALPHABET) for _ in range(TEMP_GROUP_LEN))
        for _ in range(TEMP_GROUPS)
    )
    return "-".join(groups)


def register(app: FastAPI) -> None:
    if getattr(app.state, "account_registered", False):
        return
    app.state.account_registered = True
    app.add_exception_handler(PasswordChangeRequired, _password_change_required)
    app.include_router(router)


async def _password_change_required(request: Request, _: Exception) -> Response:
    url = PASSWORD_CHANGE_PATH
    if request.headers.get("HX-Request"):
        return Response(status_code=403, headers={"HX-Redirect": url})
    if request.method in {"GET", "HEAD"}:
        return RedirectResponse(url, status_code=303)
    return PlainTextResponse(
        f"Change your password first: {url}", status_code=403, headers={"Location": url}
    )


def role_label(roles: list[str] | tuple[str, ...]) -> str:
    return ", ".join(ROLE_LABELS.get(r, r) for r in roles) or "No role"


# ---------------------------------------------------------------- my account


def _account_page(
    request: Request, context: OrgContext, *, name: str | None = None,
    error: str | None = None, saved: str | None = None, status: int = 200,
) -> Response:  # fmt: skip
    return render(
        request,
        "account.html",
        {
            "name": context.user.display_name if name is None else name,
            "roles": role_label(context.roles),
            "error": error,
            "saved": saved,
        },
        status,
    )


@router.get("/account")
def account(request: Request, context: InternalOrg, saved: str = "") -> Response:
    message = {"name": NAME_SAVED, "password": PASSWORD_SAVED}.get(saved)
    return _account_page(request, context, saved=message)


@router.post("/account/name")
def account_name(
    request: Request,
    conn: Conn,
    context: InternalOrg,
    display_name: Annotated[str, Form(max_length=1000)] = "",
) -> Response:
    name = display_name.strip()
    if not 1 <= len(name) <= 200:
        error = "Enter a name of 1 to 200 characters."
        return _account_page(request, context, name=display_name, error=error, status=422)
    admin_users.set_display_name(conn, context.user.id, name)
    return RedirectResponse("/account?saved=name", status_code=303)


def _password_page(
    request: Request, conn: Conn, user: UserDep, *, errors: dict[str, str] | None = None,
    status: int = 200,
) -> Response:  # fmt: skip
    return render(
        request,
        "account_password.html",
        {
            "required": admin_users.password_change_required(conn, user.id),
            "errors": errors or {},
            "min_length": security.MIN_PASSWORD_LENGTH,
        },
        status,
    )


@router.get(PASSWORD_CHANGE_PATH)
def password_form(request: Request, conn: Conn, user: UserDep) -> Response:
    return _password_page(request, conn, user)


@router.post(PASSWORD_CHANGE_PATH)
def change_password(
    request: Request,
    conn: Conn,
    user: UserDep,
    current_password: Annotated[str, Form(max_length=MAX_PASSWORD)] = "",
    new_password: Annotated[str, Form(max_length=MAX_PASSWORD)] = "",
    confirm_password: Annotated[str, Form(max_length=MAX_PASSWORD)] = "",
) -> Response:
    limiter: LoginRateLimiter = request.app.state.password_limiter
    settings = request.app.state.settings
    ip = client_ip(request)
    if limiter.is_blocked(user.email, ip):
        message = TOO_MANY.format(minutes=settings.login_window_minutes)
        return _password_page(request, conn, user, errors={"current": message}, status=429)

    ok, _ = security.verify_password(current_password, admin_users.get_password_hash(conn, user.id))
    if not ok:
        limiter.record_failure(user.email, ip)
        log.info("password change: wrong current password")
        return _password_page(request, conn, user, errors={"current": WRONG_CURRENT}, status=422)
    limiter.reset(user.email, ip)

    errors: dict[str, str] = {}
    if len(new_password) < security.MIN_PASSWORD_LENGTH:
        errors["new"] = TOO_SHORT
    elif new_password == current_password:
        errors["new"] = SAME_AS_CURRENT
    if not errors and confirm_password != new_password:
        errors["confirm"] = NO_MATCH
    if errors:
        return _password_page(request, conn, user, errors=errors, status=422)

    revoked = admin_users.set_own_password(
        conn,
        user_id=user.id,
        password_hash=security.hash_password(new_password),
        keep_session_id=user.session_id,
    )
    log.info("password changed; %d other sessions revoked", revoked)
    return RedirectResponse("/account?saved=password", status_code=303)


# ---------------------------------------------------------------- user management


def _users_page(
    request: Request, conn: Conn, context: OrgContext, *, form: dict[str, str] | None = None,
    errors: dict[str, str] | None = None, created: dict[str, str] | None = None,
    status: int = 200,
) -> Response:  # fmt: skip
    return render(
        request,
        "admin_users.html",
        {
            "members": admin_users.list_members(conn, context.org.id),
            "role_label": role_label,
            "roles": [(r, ROLE_LABELS[r]) for r in WEB_ROLES],
            "cli_roles": [ROLE_LABELS[r] for r in CLI_ONLY_ROLES],
            "form": form or {"email": "", "display_name": "", "role": "advisor"},
            "errors": errors or {},
            "created": created,
        },
        status,
    )


@router.get("/admin/users")
def users_list(request: Request, conn: Conn, context: OrgAdminOrg) -> Response:
    return _users_page(request, conn, context)


@router.post("/admin/users")
def users_create(
    request: Request,
    conn: Conn,
    context: OrgAdminOrg,
    email: Annotated[str, Form(max_length=1000)] = "",
    display_name: Annotated[str, Form(max_length=1000)] = "",
    role: Annotated[str, Form(max_length=50)] = "",
) -> Response:
    form = {"email": email.strip(), "display_name": display_name.strip(), "role": role}
    errors: dict[str, str] = {}
    if len(form["email"]) > 320 or not EMAIL_RE.match(form["email"]):
        errors["email"] = "Enter an email address like name@example.org."
    if not 1 <= len(form["display_name"]) <= 200:
        errors["display_name"] = "Enter a name of 1 to 200 characters."
    if role in CLI_ONLY_ROLES:
        errors["role"] = CLI_ONLY
    elif role not in WEB_ROLES:
        errors["role"] = "Choose a role."
    if errors:
        return _users_page(request, conn, context, form=form, errors=errors, status=422)

    password = new_temporary_password()
    try:
        with conn.transaction():
            user_id = admin_users.create_member(
                conn,
                actor_id=context.user.id,
                org_id=context.org.id,
                email=form["email"],
                display_name=form["display_name"],
                role=role,
                temporary_password_hash=security.hash_password(password),
            )
    except AdminError as error:
        errors["email"] = str(error)
        return _users_page(request, conn, context, form=form, errors=errors, status=409)
    log.info("org admin created user %s", user_id)
    created = {"email": form["email"], "name": form["display_name"], "password": password}
    return _users_page(request, conn, context, created=created)


def _member_or_404(conn: Conn, context: OrgContext, user_id: UUID) -> admin_users.Member:
    member = admin_users.get_member(conn, context.org.id, user_id)
    if member is None:
        raise HTTPException(404, "No such member in this organisation.")
    return member


def _member_page(
    request: Request, conn: Conn, context: OrgContext, user_id: UUID, *,
    error: str | None = None, notice: str | None = None, temp_password: str | None = None,
    status: int = 200,
) -> Response:  # fmt: skip
    member = _member_or_404(conn, context, user_id)
    return render(
        request,
        "admin_user.html",
        {
            "member": member,
            "is_self": member.id == context.user.id,
            "role_label": role_label,
            "roles": [(r, ROLE_LABELS[r]) for r in WEB_ROLES],
            "cli_roles": [(r, ROLE_LABELS[r]) for r in CLI_ONLY_ROLES],
            "error": error,
            "notice": notice,
            "temp_password": temp_password,
        },
        status,
    )


@router.get("/admin/users/{user_id}")
def member_detail(
    request: Request, conn: Conn, context: OrgAdminOrg, user_id: UUID, saved: str = ""
) -> Response:
    notice = {
        "roles": "Roles saved.",
        "disabled": "Account disabled. All its sessions were signed out.",
        "enabled": "Account re-enabled.",
    }.get(saved)
    return _member_page(request, conn, context, user_id, notice=notice)


def _apply(
    request: Request,
    conn: Conn,
    context: OrgContext,
    user_id: UUID,
    action: Callable[[], None],
    saved: str,
) -> Response:
    _member_or_404(conn, context, user_id)
    try:
        with conn.transaction():
            action()
    except AdminError as error:
        return _member_page(request, conn, context, user_id, error=str(error), status=409)
    return RedirectResponse(f"/admin/users/{user_id}?saved={saved}", status_code=303)


@router.post("/admin/users/{user_id}/roles")
def member_roles(
    request: Request,
    conn: Conn,
    context: OrgAdminOrg,
    user_id: UUID,
    roles: Annotated[list[str] | None, Form()] = None,
) -> Response:
    chosen = set(roles or [])
    return _apply(
        request,
        conn,
        context,
        user_id,
        lambda: admin_users.set_roles(
            conn, actor_id=context.user.id, org_id=context.org.id, user_id=user_id, roles=chosen
        ),
        "roles",
    )


@router.post("/admin/users/{user_id}/reset-password")
def member_reset_password(
    request: Request, conn: Conn, context: OrgAdminOrg, user_id: UUID
) -> Response:
    _member_or_404(conn, context, user_id)
    if user_id == context.user.id:
        error = "Change your own password on My account."
        return _member_page(request, conn, context, user_id, error=error, status=409)
    password = new_temporary_password()
    try:
        with conn.transaction():
            revoked = admin_users.reset_password(
                conn,
                org_id=context.org.id,
                user_id=user_id,
                temporary_password_hash=security.hash_password(password),
            )
    except AdminError as error:
        return _member_page(request, conn, context, user_id, error=str(error), status=409)
    log.info("org admin reset password of %s; %d sessions revoked", user_id, revoked)
    return _member_page(request, conn, context, user_id, temp_password=password)


@router.post("/admin/users/{user_id}/disable")
def member_disable(request: Request, conn: Conn, context: OrgAdminOrg, user_id: UUID) -> Response:
    def action() -> None:
        admin_users.set_disabled(
            conn, actor_id=context.user.id, org_id=context.org.id, user_id=user_id,
            disabled=True,
        )  # fmt: skip

    response = _apply(request, conn, context, user_id, action, "disabled")
    if user_id == context.user.id and response.status_code == 303:
        return RedirectResponse("/login", status_code=303)  # own session was revoked
    return response


@router.post("/admin/users/{user_id}/enable")
def member_enable(request: Request, conn: Conn, context: OrgAdminOrg, user_id: UUID) -> Response:
    def action() -> None:
        admin_users.set_disabled(
            conn, actor_id=context.user.id, org_id=context.org.id, user_id=user_id,
            disabled=False,
        )  # fmt: skip

    return _apply(request, conn, context, user_id, action, "enabled")
