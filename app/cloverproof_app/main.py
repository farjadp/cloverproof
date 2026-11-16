"""FastAPI entry point. Run locally with `make dev` (uvicorn --factory).

`create_app()` reads settings from the environment and fails fast when a required
variable is missing. Tests pass their own `Settings` and `Database`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cloverproof_app.config import Settings
from cloverproof_app.db.pool import Database, PooledDatabase


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
    )
    app.state.settings = settings
    app.state.database = database

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app
