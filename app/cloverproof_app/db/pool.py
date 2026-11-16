"""Database access for the web app: one psycopg connection pool per process.

Routes get a connection with `Database.connection()`. The block runs in one transaction:
committed on success, rolled back on any exception. Tests swap in a `Database` that hands
out a single connection inside a rolled-back transaction (see app/tests/db/conftest.py).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol

import psycopg
from psycopg_pool import ConnectionPool


class Database(Protocol):
    def open(self) -> None: ...  # pragma: no cover

    def connection(self) -> AbstractContextManager[psycopg.Connection]: ...  # pragma: no cover

    def close(self) -> None: ...  # pragma: no cover


class PooledDatabase:
    def __init__(self, url: str, max_size: int = 5) -> None:
        # open=False: the pool opens on app startup, not at import time.
        self._pool = ConnectionPool(
            url,
            min_size=1,
            max_size=max_size,
            open=False,
            name="cloverproof",
        )

    def open(self) -> None:
        # wait=True fails fast at startup when the database is unreachable.
        self._pool.open(wait=True, timeout=10)

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        # The pool's context manager commits on success and rolls back on error.
        with self._pool.connection() as conn:
            yield conn

    def close(self) -> None:
        self._pool.close()
