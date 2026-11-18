"""Routes for part A of Step 5: login, logout, organisation chooser. Farmers/plans: plan_web.py."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from cloverproof_app import display_units, nav, security, split_display
from cloverproof_app.auth import (
    LOGIN_CSRF_COOKIE,
    ORG_COOKIE,
    SESSION_COOKIE,
    Conn,
    CurrentUser,
    SettingsDep,
    UserDep,
    optional_user,
    org_cookie_value,
    page_shell_org,
    session_token_hash,
)
from cloverproof_app.config import Settings
from cloverproof_app.db.pool import set_rls_context
from cloverproof_app.ratelimit import LoginDecision, LoginGuard
from cloverproof_app.repo import sessions, users

log = logging.getLogger(__name__)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.globals["split_text"] = split_display
templates.env.globals["display_units"] = display_units
router = APIRouter()

# Copy from docs/design/webapp-ui.md §3.1. One generic failure message (unknown email,
# wrong password and disabled account look the same).
LOGIN_FAILED = "Email or password is incorrect."
LOGIN_BLOCKED = "Too many attempts. Wait {minutes} minutes and try again."
LOGIN_PAUSED = "Sign-in is paused for now. Try again later or ask an administrator."
LOGIN_FORM_EXPIRED = "This form expired. Reload the page and sign in again."
SIGNED_OUT = "You were signed out. Sign in again to continue."


def render(request: Request, name: str, context: dict[str, Any], status: int = 200) -> Response:
    user = getattr(request.state, "user", None)
    org = getattr(request.state, "org", None)
    base = {
        "csrf_token": getattr(request.state, "csrf_token", ""),
        "user": user,
        "org_context": org,
        "nav": nav.build_nav(
            request.url.path,
            user,
            org,
            must_choose_org=getattr(request.state, "must_choose_org", False),
            locked=bool(context.get("nav_locked")),
        ),
    }
    return templates.TemplateResponse(request, name, {**base, **context}, status_code=status)


def set_cookie(response: Response, settings: Settings, name: str, value: str, max_age: int) -> None:
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def clear_cookie(response: Response, settings: Settings, name: str) -> None:
    response.delete_cookie(
        name, path="/", httponly=True, secure=settings.cookie_secure, samesite="lax"
    )


def safe_next(target: str | None) -> str:
    """Only local absolute paths, never another host (open redirect)."""
    if target and target.startswith("/") and not target.startswith(("//", "/\\")):
        return target
    return "/"


def client_ip(request: Request, settings: Settings | None = None) -> str:
    """The client address for rate limits (security review S1).

    Default: the TCP peer. Client-sent X-Forwarded-For is never trusted. With
    TRUSTED_PROXY_HEADER set (e.g. X-Real-IP, which the proxy overwrites), that one header is
    read; if it holds a list, the rightmost entry (added by our proxy) is used.
    """
    settings = settings or request.app.state.settings
    peer = request.client.host if request.client else "unknown"
    if not settings.trusted_proxy_header:
        return peer
    raw = request.headers.get(settings.trusted_proxy_header, "")
    value = raw.split(",")[-1].strip()
    return value or peer


def login_page(
    request: Request, settings: Settings, *, email: str = "", next_url: str = "/",
    error: str | None = None, info: str | None = None, status: int = 200,
) -> Response:  # fmt: skip
    token = security.new_token()
    response = render(
        request,
        "login.html",
        {
            "login_csrf": token,
            "email": email,
            "next": safe_next(next_url),
            "error": error,
            "info": info,
        },
        status,
    )
    set_cookie(response, settings, LOGIN_CSRF_COOKIE, token, max_age=3600)
    return response


@router.get("/login")
def login_form(
    request: Request,
    settings: SettingsDep,
    user: Annotated[CurrentUser | None, Depends(optional_user)],
    next: str = "/",
    expired: bool = False,
) -> Response:
    if user is not None:
        return RedirectResponse(safe_next(next), status_code=303)
    return login_page(request, settings, next_url=next, info=SIGNED_OUT if expired else None)


@router.post("/login")
def login(
    request: Request,
    conn: Conn,
    settings: SettingsDep,
    email: Annotated[str, Form(max_length=320)] = "",
    password: Annotated[str, Form(max_length=1024)] = "",
    next: Annotated[str, Form()] = "/",
) -> Response:
    guard: LoginGuard = request.app.state.login_guard
    ip = client_ip(request, settings)
    email = email.strip()
    decision = guard.check(email, ip)
    if decision in {LoginDecision.IP_BLOCKED, LoginDecision.PAIR_BLOCKED}:
        message = LOGIN_BLOCKED.format(minutes=settings.login_window_minutes)
        return login_page(request, settings, email=email, next_url=next, error=message, status=429)
    if decision is not LoginDecision.OK:
        log.warning("login refused: %s limit", decision.value)
        return login_page(
            request, settings, email=email, next_url=next, error=LOGIN_PAUSED, status=503
        )

    creds = users.get_credentials_by_email(conn, email) if email else None
    ok, new_hash = security.verify_password(password, creds.password_hash if creds else None)
    # Disabled, service (B1) and expired temporary passwords (N11) look like a wrong password.
    if not ok or creds is None or not creds.can_sign_in:
        guard.record_failure(email, ip)
        log.info("login failed")  # no email or IP in logs (PII)
        return login_page(
            request, settings, email=email, next_url=next, error=LOGIN_FAILED, status=401
        )

    guard.record_success(email, ip)
    set_rls_context(conn, user_id=creds.id)  # admin_event actor (F2) for the rehash
    if new_hash:
        users.set_password_hash(conn, creds.id, new_hash)
    old = session_token_hash(request)
    if old:
        sessions.revoke_session(conn, token_sha256=old)  # no session fixation
    token = security.new_token()
    absolute = timedelta(hours=settings.session_absolute_hours)
    sessions.create_session(
        conn, user_id=creds.id, token_sha256=security.token_sha256(token), absolute=absolute
    )
    target = safe_next(next)
    if target == "/" and not users.user_organisations(conn, creds.id):
        target = "/products"  # the home page needs an organisation; this one does not
    response = RedirectResponse(target, status_code=303)
    set_cookie(response, settings, SESSION_COOKIE, token, int(absolute.total_seconds()))
    clear_cookie(response, settings, LOGIN_CSRF_COOKIE)
    clear_cookie(response, settings, ORG_COOKIE)
    return response


@router.post("/logout")
def logout(request: Request, conn: Conn, settings: SettingsDep) -> Response:
    token_hash = session_token_hash(request)
    if token_hash:
        sessions.revoke_session(conn, token_sha256=token_hash)
    response = RedirectResponse("/login", status_code=303)
    if request.headers.get("HX-Request"):
        response = Response(status_code=204, headers={"HX-Redirect": "/login"})
    clear_cookie(response, settings, SESSION_COOKIE)
    clear_cookie(response, settings, ORG_COOKIE)
    return response


@router.get("/orgs/choose", dependencies=[Depends(page_shell_org)])
def choose_org_form(request: Request, conn: Conn, user: UserDep) -> Response:
    organisations = users.user_organisations(conn, user.id)
    return render(request, "choose_org.html", {"organisations": organisations})


@router.post("/orgs/choose", dependencies=[Depends(page_shell_org)])
def choose_org(
    request: Request,
    conn: Conn,
    settings: SettingsDep,
    user: UserDep,
    org_id: Annotated[str, Form()] = "",
) -> Response:
    organisations = users.user_organisations(conn, user.id)
    try:
        wanted = UUID(org_id)
    except ValueError:
        wanted = None
    if wanted is None or wanted not in {o.id for o in organisations}:
        raise HTTPException(403, "You are not a member of that organisation.")
    response = RedirectResponse("/", status_code=303)
    value = org_cookie_value(settings, user, wanted)
    set_cookie(response, settings, ORG_COOKIE, value, settings.session_absolute_hours * 3600)
    return response
