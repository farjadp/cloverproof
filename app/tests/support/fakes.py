"""Test doubles shared by app tests that do not need a database."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from cloverproof_app.config import Settings

TEST_SECRET = "test-secret-" + "x" * 40


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql://unused.invalid/none",
        "session_secret": TEST_SECRET,
        "env": "test",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


class NoDatabase:
    """A Database that fails loudly if a route touches it."""

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        raise AssertionError("this test must not use the database")
        yield  # pragma: no cover
