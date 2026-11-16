"""Migration runner checks that need no database (always run in CI)."""

from pathlib import Path

import pytest

from cloverproof_app.db.migrate import (
    DEFAULT_MIGRATIONS_DIR,
    REPO_ROOT,
    MigrationError,
    is_local,
    main,
    migration_files,
)


def test_default_dir_is_repo_db_migrations() -> None:
    assert DEFAULT_MIGRATIONS_DIR == REPO_ROOT / "db" / "migrations"
    names = [p.name for p in migration_files(DEFAULT_MIGRATIONS_DIR)]
    assert names[0] == "0001_pilot_request.sql"
    assert names == sorted(names)


def test_website_migration_copied_verbatim() -> None:
    # The shared folder must keep the website's applied file byte-for-byte: the website
    # runner tracks it by name, so a changed body would never be re-applied anywhere.
    website = REPO_ROOT / "website" / "db" / "migrations" / "0001_pilot_request.sql"
    shared = DEFAULT_MIGRATIONS_DIR / "0001_pilot_request.sql"
    assert shared.read_bytes() == website.read_bytes()


def test_files_sorted_and_non_sql_ignored(tmp_path: Path) -> None:
    for name in ["0010_b.sql", "0002_a.sql", "README.md"]:
        (tmp_path / name).write_text("select 1;")
    assert [p.name for p in migration_files(tmp_path)] == ["0002_a.sql", "0010_b.sql"]


@pytest.mark.parametrize("name", ["2_a.sql", "0002-a.sql", "0002_A.sql"])
def test_bad_file_name_rejected(tmp_path: Path, name: str) -> None:
    (tmp_path / name).write_text("select 1;")
    with pytest.raises(MigrationError, match="must match"):
        migration_files(tmp_path)


def test_duplicate_number_rejected(tmp_path: Path) -> None:
    (tmp_path / "0002_a.sql").write_text("select 1;")
    (tmp_path / "0002_b.sql").write_text("select 1;")
    with pytest.raises(MigrationError, match="duplicate"):
        migration_files(tmp_path)


def test_missing_dir_rejected(tmp_path: Path) -> None:
    with pytest.raises(MigrationError, match="not found"):
        migration_files(tmp_path / "nope")


@pytest.mark.parametrize(
    ("url", "local"),
    [
        ("postgresql://u:p@127.0.0.1:5432/db", True),
        ("postgresql://u:p@localhost/db", True),
        ("postgresql:///db", True),
        ("postgresql://u:p@db.example.internal:5432/db", False),
        ("postgresql://u:p@localhost,db.example.internal/db", False),
    ],
)
def test_is_local(url: str, local: bool) -> None:
    assert is_local(url) is local


def test_main_without_database_url_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main([]) == 1
    assert "DATABASE_URL is not set" in capsys.readouterr().err


def test_seed_refuses_remote_host_before_connecting(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example.internal:5432/db")
    assert main(["seed", "db/seeds/dev.sql"]) == 1
    assert "refusing to seed a non-local database" in capsys.readouterr().err
