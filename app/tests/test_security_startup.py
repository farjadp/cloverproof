"""S4 + N7 (security review S2-auth-review-step5): database role check and explicit ENV."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from cloverproof_app.config import ConfigError, Settings
from cloverproof_app.db.pool import check_least_privilege
from cloverproof_app.main import create_app

from .support.fakes import make_settings

SECRET = "s" * 40


class FakeResult:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self.row = row

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.row


class FakeConn:
    """Answers the role query the startup check runs."""

    def __init__(
        self, *, superuser: bool, bypassrls: bool, member: bool, admin: bool = False
    ) -> None:
        self.row = (superuser, bypassrls, member, admin)
        self.queries: list[str] = []

    def execute(self, query: str, params: object = None) -> FakeResult:
        self.queries.append(query)
        assert "rolsuper" in query and "current_user" in query, query
        return FakeResult(self.row)


@pytest.mark.parametrize(
    ("superuser", "bypassrls", "member", "admin", "message"),
    [
        (True, False, True, False, "superuser"),
        (False, True, True, False, "BYPASSRLS"),
        (False, False, False, False, "cp_app"),
        (False, False, True, True, "cp_admin"),
    ],
)
def test_role_check_refuses_privileged_or_foreign_roles(
    superuser: bool, bypassrls: bool, member: bool, admin: bool, message: str
) -> None:
    conn = FakeConn(superuser=superuser, bypassrls=bypassrls, member=member, admin=admin)
    with pytest.raises(ConfigError, match=message):
        check_least_privilege(conn)  # type: ignore[arg-type]


def test_role_check_accepts_cp_app_member() -> None:
    conn = FakeConn(superuser=False, bypassrls=False, member=True)
    check_least_privilege(conn)  # type: ignore[arg-type]
    assert any("current_user" in q for q in conn.queries)


class FakeDatabase:
    def __init__(self, conn: FakeConn) -> None:
        self.conn = conn
        self.opened = self.closed = False

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.closed = True

    @contextmanager
    def connection(self) -> Iterator[FakeConn]:
        yield self.conn


def production(**overrides: object) -> Settings:
    values: dict[str, object] = {"env": "production"}
    values.update(overrides)
    return make_settings(**values)


def test_production_startup_fails_as_superuser() -> None:
    database = FakeDatabase(FakeConn(superuser=True, bypassrls=True, member=True))
    app = create_app(production(), database)  # type: ignore[arg-type]
    with pytest.raises(ConfigError, match="superuser"), TestClient(app):
        pass
    assert database.closed


def test_production_startup_ok_as_cp_app() -> None:
    database = FakeDatabase(FakeConn(superuser=False, bypassrls=False, member=True))
    with TestClient(create_app(production(), database)) as client:  # type: ignore[arg-type]
        assert client.get("/healthz").status_code == 200


def test_development_skips_the_role_check() -> None:
    conn = FakeConn(superuser=True, bypassrls=True, member=False)
    with TestClient(create_app(make_settings(env="development"), FakeDatabase(conn))):  # type: ignore[arg-type]
        pass
    assert conn.queries == []


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@db.railway.internal:5432/app",
        "postgresql://u:p@203.0.113.5/app",
        "host=db.example.org dbname=app user=u",
    ],
)
def test_remote_database_requires_explicit_env(url: str) -> None:
    with pytest.raises(ConfigError, match="ENV"):
        Settings.from_env({"DATABASE_URL": url, "SESSION_SECRET": SECRET})
    explicit = Settings.from_env(
        {"DATABASE_URL": url, "SESSION_SECRET": SECRET, "ENV": "development"}
    )
    assert explicit.env == "development"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@localhost:5432/app",
        "postgresql://u:p@127.0.0.1:55432/app",
        "postgresql://u:p@[::1]/app",
        "postgresql:///app",  # unix socket
    ],
)
def test_local_database_defaults_to_development(url: str) -> None:
    assert Settings.from_env({"DATABASE_URL": url, "SESSION_SECRET": SECRET}).env == "development"


def test_error_does_not_print_the_database_url() -> None:
    url = "postgresql://user:hunter2-secret@db.example.org/app"
    with pytest.raises(ConfigError) as error:
        Settings.from_env({"DATABASE_URL": url, "SESSION_SECRET": SECRET})
    assert "hunter2" not in str(error.value) and "db.example.org" not in str(error.value)
