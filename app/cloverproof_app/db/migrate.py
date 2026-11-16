"""Apply `db/migrations/*.sql` in order, once each, tracked in `schema_migrations`.

Compatible with `website/scripts/migrate.mjs` so both runners can share one database:
- same table: `schema_migrations (name text primary key, applied_at timestamptz)`;
- same key: the migration's file name (no checksum);
- same order: file names sorted as strings;
- same unit of work: one transaction per file, the row is inserted in that transaction.

Additions (invisible to the website runner): a session advisory lock so two deploys
cannot migrate at once, a strict file-name pattern, and a warning for recorded
migrations that are not on disk.

Usage:
    DATABASE_URL=... python -m cloverproof_app.db.migrate             # apply pending
    DATABASE_URL=... python -m cloverproof_app.db.migrate seed FILE   # local only

The URL is read from the environment and never printed.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"

# Same DDL as website/scripts/migrate.mjs. Do not change the shape.
SCHEMA_MIGRATIONS_DDL = """create table if not exists schema_migrations (
    name text primary key, applied_at timestamptz not null default now())"""

# Arbitrary constant key for pg_advisory_lock ("cpmigrat" in ASCII).
ADVISORY_LOCK_KEY = 0x63706D6967726174

MIGRATION_NAME = re.compile(r"^\d{4}_[a-z0-9_]+\.sql$")
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

Log = Callable[[str], None]


class MigrationError(RuntimeError):
    pass


def _stderr(message: str) -> None:
    print(message, file=sys.stderr)


def migration_files(directory: Path) -> list[Path]:
    """Sorted `.sql` files. Names must be `NNNN_snake_case.sql` with unique numbers."""
    if not directory.is_dir():
        raise MigrationError(f"migrations directory not found: {directory}")
    files = sorted((p for p in directory.iterdir() if p.suffix == ".sql"), key=lambda p: p.name)
    bad = [p.name for p in files if not MIGRATION_NAME.match(p.name)]
    if bad:
        raise MigrationError(f"migration file names must match NNNN_snake_case.sql: {bad}")
    numbers = [p.name[:4] for p in files]
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        raise MigrationError(f"duplicate migration numbers: {duplicates}")
    return files


def applied_migrations(conn: psycopg.Connection) -> set[str]:
    conn.execute(SCHEMA_MIGRATIONS_DDL)
    return {row[0] for row in conn.execute("select name from schema_migrations")}


def migrate(conn: psycopg.Connection, directory: Path, log: Log = print) -> list[str]:
    """Apply pending migrations on an autocommit connection. Returns the names applied."""
    if not conn.autocommit:
        raise MigrationError("migrate() needs an autocommit connection")
    files = migration_files(directory)
    conn.execute("select pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
    try:
        done = applied_migrations(conn)
        unknown = sorted(done - {p.name for p in files})
        if unknown:
            _stderr(f"migrate: warning: recorded but not on disk: {', '.join(unknown)}")
        newly_applied: list[str] = []
        for path in files:
            if path.name in done:
                continue
            sql = path.read_text(encoding="utf-8")
            try:
                with conn.transaction():
                    # No parameters -> simple query protocol, so a file may hold many statements.
                    conn.execute(sql)
                    conn.execute("insert into schema_migrations (name) values (%s)", (path.name,))
            except psycopg.Error as error:
                raise MigrationError(f"{path.name} failed: {error}") from error
            log(f"migrate: applied {path.name}")
            newly_applied.append(path.name)
        log("migrate: up to date")
        return newly_applied
    finally:
        conn.execute("select pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,))


def is_local(url: str) -> bool:
    host = conninfo_to_dict(url).get("host") or "localhost"
    return all(h in LOCAL_HOSTS or h.startswith("/") for h in str(host).split(","))


def apply_sql_file(conn: psycopg.Connection, path: Path) -> None:
    """Run one SQL file in a single transaction (used for dev seeds)."""
    sql = path.read_text(encoding="utf-8")
    with conn.transaction():
        conn.execute(sql)


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise MigrationError("DATABASE_URL is not set")
    return url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cloverproof_app.db.migrate")
    sub = parser.add_subparsers(dest="command")
    up = sub.add_parser("up", help="apply pending migrations (default)")
    up.add_argument("--dir", type=Path, default=DEFAULT_MIGRATIONS_DIR)
    seed = sub.add_parser("seed", help="run a seed SQL file (local databases only)")
    seed.add_argument("file", type=Path)
    seed.add_argument(
        "--allow-remote", action="store_true", help="allow a non-local host (never production)"
    )
    args = parser.parse_args(argv)

    try:
        url = _database_url()
        if args.command == "seed" and not (args.allow_remote or is_local(url)):
            raise MigrationError("refusing to seed a non-local database")
        with psycopg.connect(url, autocommit=True) as conn:
            if args.command == "seed":
                apply_sql_file(conn, args.file)
                print(f"seed: applied {args.file.name}")
            else:
                migrate(conn, getattr(args, "dir", DEFAULT_MIGRATIONS_DIR))
    except (MigrationError, psycopg.Error) as error:
        _stderr(f"migrate: error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
