"""FastAPI entry point. Run locally with `make dev` (uvicorn --factory).

`create_app()` reads settings from the environment and fails fast when a required
variable is missing. Tests pass their own `Settings` and `Database`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from cloverproof_app.auth import SESSION_COOKIE, NotAuthenticated, OrgSelectionRequired, csrf_guard
from cloverproof_app.config import Settings
from cloverproof_app.db.pool import Database, PooledDatabase
from cloverproof_app.ratelimit import LoginRateLimiter
from cloverproof_app.web import LOGIN_FORM_EXPIRED, clear_cookie, login_page, render, router

STATIC_DIR = Path(__file__).parent / "static"

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
    database = database or PooledDatabase(settings.database_url, settings.db_pool_max_size)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.open()
        try:
            yield
        finally:
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
    app.state.login_limiter = LoginRateLimiter(
        settings.login_max_failures, settings.login_window_minutes * 60
    )

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

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(router)
    return app
