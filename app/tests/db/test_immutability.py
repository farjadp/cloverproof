"""recommendation, review, proof_document: triggers raise for everyone, cp_app lacks grants."""

from typing import Any

import psycopg
import pytest
from psycopg import errors

from .conftest import Org, as_owner, insert

pytestmark = pytest.mark.db

IMMUTABLE = ["recommendation", "review", "proof_document"]


@pytest.fixture
def approved(db: psycopg.Connection, org_a: Org) -> dict[str, Any]:
    review = insert(
        db,
        "review",
        organisation_id=org_a.id,
        recommendation_id=org_a.engine_rec,
        decision="approve",
        reviewer_id=org_a.agronomist,
        minutes_spent=12,
    )
    sha = "a" * 64
    proof = insert(
        db,
        "proof_document",
        organisation_id=org_a.id,
        recommendation_id=org_a.engine_rec,
        sha256=sha,
        storage_key=f"proof/{org_a.id}/{org_a.engine_rec}/{sha}.pdf",
        created_by=org_a.agronomist,
    )
    return {"recommendation": org_a.engine_rec, "review": review, "proof_document": proof}


@pytest.mark.parametrize("table", IMMUTABLE)
def test_update_and_delete_raise_even_for_owner(
    db: psycopg.Connection, approved: dict[str, Any], table: str
) -> None:
    row_id = approved[table]
    for sql in (
        f"update {table} set created_at = now() where id = %s",
        f"delete from {table} where id = %s",
    ):
        with pytest.raises(errors.InsufficientPrivilege, match="rows are immutable"), as_owner(db):
            db.execute(sql, (row_id,))  # type: ignore[arg-type]


@pytest.mark.parametrize("table", IMMUTABLE)
def test_truncate_raises_even_for_owner(
    db: psycopg.Connection, approved: dict[str, Any], table: str
) -> None:
    with pytest.raises(errors.InsufficientPrivilege, match="rows are immutable"), as_owner(db):
        db.execute(f"truncate {table} cascade")  # type: ignore[arg-type]


@pytest.mark.parametrize("table", IMMUTABLE)
def test_cp_app_has_no_update_delete_grant(
    db: psycopg.Connection, approved: dict[str, Any], table: str
) -> None:
    row_id = approved[table]
    for sql in (
        f"update {table} set created_at = now() where id = %s",
        f"delete from {table} where id = %s",
    ):
        # Refused by the grant (permission denied), before any trigger runs.
        with (
            pytest.raises(errors.InsufficientPrivilege, match="permission denied for table"),
            db.transaction(),
        ):
            db.execute(sql, (row_id,))  # type: ignore[arg-type]


def test_cp_app_grants(db: psycopg.Connection) -> None:
    def privileges(table: str) -> set[str]:
        return {
            p
            for p in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
            if db.execute("select has_table_privilege('cp_app', %s, %s)", (table, p)).fetchone()
            == (True,)
        }

    for table in IMMUTABLE:
        assert privileges(table) == {"SELECT", "INSERT"}
    for table in ("farm", "field", "crop_plan", "soil_test", "application_log"):
        assert privileges(table) == {"SELECT", "INSERT", "UPDATE", "DELETE"}
    assert privileges("recommendation_diff") == {"SELECT"}


def test_cp_app_can_update_mutable_tables(db: psycopg.Connection, org_a: Org) -> None:
    db.execute("update farm set name = 'Renamed' where id = %s", (org_a.farm,))
    assert db.execute("select name from farm where id = %s", (org_a.farm,)).fetchone() == (
        "Renamed",
    )
