"""FastAPI entry point. Run locally with `make dev` (uvicorn --factory).

`create_app()` reads settings from the environment and fails fast when a required
variable is missing. Tests pass their own `Settings` and `Database`.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from cloverproof_app import account, security
from cloverproof_app.auth import SESSION_COOKIE, NotAuthenticated, OrgSelectionRequired, csrf_guard
from cloverproof_app.config import ConfigError, Settings
from cloverproof_app.db.migrate import REPO_ROOT
from cloverproof_app.db.pool import Database, PooledDatabase, check_least_privilege
from cloverproof_app.plan_web import router as plan_router
from cloverproof_app.ratelimit import LoginGuard, UnlockListener
from cloverproof_app.web import (
    LOGIN_FORM_EXPIRED,
    LOGIN_PAUSED,
    clear_cookie,
    login_page,
    render,
    router,
)
from cloverproof_engine.loaders import load_pack
from cloverproof_engine.pack import Pack

STATIC_DIR = Path(__file__).parent / "static"
DEPLOYED_ENVS = frozenset({"staging", "production"})
DEFAULT_PACK_PATH = REPO_ROOT / "packs" / "placeholder" / "v0.yaml"
SERVER_ERROR = (
    "Something went wrong and nothing was saved. Try again."
    " If it keeps happening, note the time: {time}."
)
log = logging.getLogger(__name__)


def load_configured_pack(settings: Settings) -> Pack:
    """The country pack the engine runs with. Fails fast at startup if it cannot load."""
    path = Path(settings.pack_path) if settings.pack_path else DEFAULT_PACK_PATH
    try:
        return load_pack(path)
    except (OSError, ValueError) as error:
        name = error.__class__.__name__
        raise ConfigError(f"PACK_PATH: cannot load country pack ({name})") from error


# htmx is vendored and loaded from 'self'; its inline indicator styles are disabled in
# base.html, so no 'unsafe-inline' is needed.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:;"
        " form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}


def wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "") or bool(
        request.headers.get("HX-Request")
    )


def redirect(request: Request, url: str, status: int) -> Response:
    if request.headers.get("HX-Request"):
        return Response(status_code=status, headers={"HX-Redirect": url})
    if request.method in {"GET", "HEAD"} and wants_html(request):
        return RedirectResponse(url, status_code=303)
    return PlainTextResponse(f"See {url}", status_code=status, headers={"Location": url})


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    login_guard = LoginGuard(
        pair_max=settings.login_max_failures,
        pair_window=settings.login_window_minutes * 60,
        ip_max=settings.login_ip_max_failures,
        ip_window=settings.login_window_minutes * 60,
        account_max=settings.login_account_max_failures,
        account_window=settings.login_account_window_minutes * 60,
        global_max=settings.login_global_max_failures_per_minute,
        global_window=60,
    )
    security.configure_hashing(
        max_concurrency=settings.argon2_max_concurrency,
        acquire_timeout_seconds=settings.argon2_acquire_timeout_seconds,
    )
    if database is None:
        database = PooledDatabase(settings.database_url, settings.db_pool_max_size)
        # `cli user-unlock` reaches this process through LISTEN/NOTIFY (production only;
        # tests pass their own Database and call unlock_account directly).
        login_guard.unlock_listener = UnlockListener(settings.database_url)
    unlock_listener = login_guard.unlock_listener

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.open()
        if settings.env in DEPLOYED_ENVS:
            try:
                with database.connection() as conn:
                    check_least_privilege(conn)
            except BaseException:
                database.close()
                raise
        if unlock_listener is not None:
            unlock_listener.open()
        try:
            yield
        finally:
            if unlock_listener is not None:
                unlock_listener.close()
            database.close()

    app = FastAPI(
        title="CloverProof internal tool",
        version="0.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(csrf_guard)],
    )
    app.state.settings = settings
    app.state.database = database
    app.state.pack = load_configured_pack(settings)
    app.state.login_guard = login_guard
    app.state.login_limiter = login_guard.pair  # (email, IP) limit, also used by account.py

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if not request.url.path.startswith("/static/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(NotAuthenticated)
    async def not_authenticated(request: Request, _: NotAuthenticated) -> Response:
        target = request.url.path
        if request.url.query:
            target += "?" + request.url.query
        params = [] if target == "/" else [f"next={quote(target, safe='')}"]
        stale = SESSION_COOKIE in request.cookies  # had a session that is no longer valid
        if stale:
            params.append("expired=1")
        url = "/login" + ("?" + "&".join(params) if params else "")
        response = redirect(request, url, 401)
        if stale:
            clear_cookie(response, request.app.state.settings, SESSION_COOKIE)
        return response

    @app.exception_handler(OrgSelectionRequired)
    async def org_selection_required(request: Request, _: OrgSelectionRequired) -> Response:
        return redirect(request, "/orgs/choose", 409)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException) -> Response:
        if request.url.path == "/login" and error.status_code == 403:
            settings_ = request.app.state.settings
            return login_page(request, settings_, error=LOGIN_FORM_EXPIRED, status=403)
        if wants_html(request):
            return render(
                request, "error.html", {"status": error.status_code, "detail": error.detail},
                error.status_code,
            )  # fmt: skip
        return PlainTextResponse(str(error.detail), status_code=error.status_code)

    @app.exception_handler(security.HashingBusy)
    async def hashing_busy(request: Request, _: security.HashingBusy) -> Response:
        # Too many password checks at once (S2): nothing was saved; ask to retry.
        headers = {"Retry-After": "30"}
        if request.url.path == "/login":
            response = login_page(request, settings, error=LOGIN_PAUSED, status=503)
            response.headers.update(headers)
            return response
        detail = "The server is busy. Nothing was saved. Try again in a minute."
        if wants_html(request):
            response = render(request, "error.html", {"status": 503, "detail": detail}, 503)
            response.headers.update(headers)
            return response
        return PlainTextResponse(detail, status_code=503, headers=headers)

    @app.exception_handler(Exception)
    async def server_error(request: Request, error: Exception) -> Response:
        # The request's transaction was rolled back (Database.connection), so nothing is saved.
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        detail = SERVER_ERROR.format(time=datetime.now().strftime("%H:%M"))
        if wants_html(request):
            return render(request, "error.html", {"status": 500, "detail": detail}, 500)
        return PlainTextResponse(detail, status_code=500)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(router)
    app.include_router(plan_router)
    account.register(app)
    return app
