"""Migration 0031: soil_estimate (S3-DB-01, XD-08). The generic RLS allow/deny matrix for this
table runs from TENANT_CASES in test_rls.py and the immutability matrix from
test_immutability.py; this file covers what is specific to estimates."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import psycopg
import pytest
from psycopg import errors

from .conftest import (
    Org,
    as_owner,
    insert,
    locate_field,
    soil_estimate_provenance,
    use_context,
)

pytestmark = pytest.mark.db

RETRIEVED = datetime(2026, 11, 1, tzinfo=UTC)
CANONICAL_UNITS = {
    "phh2o": "pH",
    "soc": "mg/kg",
    "nitrogen": "mg/kg",
    "clay": "%",
    "sand": "%",
    "silt": "%",
}
# Refused by NOT NULL. organisation_id and created_by are also tested, below: the RLS check
# runs before NOT NULL and refuses them first.
REQUIRED = [
    "field_id",
    "season_id",
    "property",
    "value",
    "unit",
    "source",
    "source_version",
    "resolution_m",
    "depth_top_cm",
    "depth_bottom_cm",
    "retrieved_at",
    "licence",
    "attribution",
    "created_at",
]


# Migration 0033 needs a located field; setting the point makes its revision 1.
REVISION = 1


@pytest.fixture
def org_a(db: psycopg.Connection, org_a: Org) -> Org:
    assert locate_field(db, org_a.id, org_a.fields[0]) == REVISION
    return org_a


@pytest.fixture
def org_b(db: psycopg.Connection, org_b: Org) -> Org:
    assert locate_field(db, org_b.id, org_b.fields[0]) == REVISION
    return org_b


def estimate(org: Org, **overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "organisation_id": org.id,
        "field_id": org.fields[0],
        "season_id": org.season,
        "property": "nitrogen",
        "value": 1500,
        "unit": "mg/kg",
        "value_q05": 900,
        "value_q95": 2300,
        "uncertainty_ratio": 0.9,
        "source": "soilgrids",
        "source_version": "2.0",
        "resolution_m": 250,
        "depth_top_cm": 0,
        "depth_bottom_cm": 5,
        "retrieved_at": RETRIEVED,
        "licence": "CC BY 4.0",
        "attribution": "SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0",
        "created_by": org.staff,
    }
    values |= overrides
    # The address follows the row, so a test of another column fails on that column only.
    provenance = soil_estimate_provenance(
        REVISION, values["property"], values["depth_top_cm"], values["depth_bottom_cm"]
    )
    return provenance | values


def refused(db: psycopg.Connection, expected: Any, values: dict[str, Any]) -> None:
    with pytest.raises(expected), db.transaction():
        insert(db, "soil_estimate", **values)


def count(db: psycopg.Connection) -> int:
    row = db.execute("select count(*) from soil_estimate").fetchone()
    assert row is not None
    return int(row[0])


def test_only_uncertainty_and_0033_columns_are_nullable(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select column_name from information_schema.columns where table_schema = 'public'"
        " and table_name = 'soil_estimate' and is_nullable = 'YES'"
    ).fetchall()
    # The last four are nullable for rows older than 0033; CHECKs require them on new rows.
    assert {r[0] for r in rows} == {
        "value_q05",
        "value_q95",
        "uncertainty_ratio",
        "field_location_revision",
        "statistic",
        "layer_url",
        "citation",
    }


def test_field_and_season_use_composite_foreign_keys(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select confrelid::regclass::text, array_length(conkey, 1) from pg_constraint"
        " where conrelid = 'soil_estimate'::regclass and contype = 'f'"
        " and confrelid in ('field'::regclass, 'season'::regclass)"
    ).fetchall()
    assert sorted(rows) == [("field", 2), ("season", 2)]


# --- Organisation boundary (two users, two organisations) -----------------------------------


def test_allowed_user_reads_and_other_org_user_is_denied(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    row_id = insert(db, "soil_estimate", **estimate(org_a))
    use_context(db, org_a.agronomist, org_a.id)
    assert db.execute("select id from soil_estimate").fetchall() == [(row_id,)]

    use_context(db, org_b.agronomist, org_b.id)
    assert db.execute("select id from soil_estimate").fetchall() == []
    # A user of org B naming org A in the context is not a member there either.
    use_context(db, org_b.agronomist, org_a.id)
    assert db.execute("select id from soil_estimate").fetchall() == []


def test_no_context_reads_nothing_and_cannot_insert(db: psycopg.Connection, org_a: Org) -> None:
    insert(db, "soil_estimate", **estimate(org_a))
    use_context(db, None)
    assert count(db) == 0
    columns = estimate(org_a)
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(
            f"insert into soil_estimate ({', '.join(columns)})"  # type: ignore[arg-type]
            f" values ({', '.join(['%s'] * len(columns))})",
            list(columns.values()),
        )


@pytest.mark.parametrize("column", ["field_id", "season_id"])
def test_cannot_point_at_another_orgs_field_or_season(
    db: psycopg.Connection, org_a: Org, org_b: Org, column: str
) -> None:
    foreign = org_a.fields[0] if column == "field_id" else org_a.season
    refused(db, errors.ForeignKeyViolation, estimate(org_b, **{column: foreign}))


def test_author_is_bound_to_the_context_user(db: psycopg.Connection, org_a: Org) -> None:
    use_context(db, org_a.agronomist, org_a.id)
    columns = estimate(org_a)  # created_by = org_a.staff, not the context user
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(
            f"insert into soil_estimate ({', '.join(columns)})"  # type: ignore[arg-type]
            f" values ({', '.join(['%s'] * len(columns))})",
            list(columns.values()),
        )


# --- XD-08: every metadata field is required ------------------------------------------------


@pytest.mark.parametrize("column", REQUIRED)
def test_missing_metadata_is_refused(db: psycopg.Connection, org_a: Org, column: str) -> None:
    refused(db, errors.NotNullViolation, estimate(org_a, **{column: None}))


@pytest.mark.parametrize("column", ["organisation_id", "created_by"])
def test_missing_owner_or_author_is_refused(
    db: psycopg.Connection, org_a: Org, column: str
) -> None:
    refused(
        db,
        (errors.InsufficientPrivilege, errors.NotNullViolation),
        estimate(org_a, **{column: None}),
    )


@pytest.mark.parametrize("column", ["source_version", "licence", "attribution"])
def test_blank_metadata_is_refused(db: psycopg.Connection, org_a: Org, column: str) -> None:
    refused(db, errors.CheckViolation, estimate(org_a, **{column: "   "}))


@pytest.mark.parametrize(
    "overrides",
    [
        {"value_q05": None, "value_q95": None, "uncertainty_ratio": None},
        {"value_q95": None, "uncertainty_ratio": None},
        {"value_q05": None},  # half a quantile pair, even with a ratio
    ],
)
def test_uncertainty_is_required(
    db: psycopg.Connection, org_a: Org, overrides: dict[str, Any]
) -> None:
    refused(db, errors.CheckViolation, estimate(org_a, **overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        {"uncertainty_ratio": None},
        {"value_q05": None, "value_q95": None},
    ],
)
def test_quantiles_or_ratio_is_enough(
    db: psycopg.Connection, org_a: Org, overrides: dict[str, Any]
) -> None:
    insert(db, "soil_estimate", **estimate(org_a, **overrides))


# --- Rule 3: no P or K, ever ----------------------------------------------------------------


@pytest.mark.parametrize(
    "prop",
    ["P", "K", "p", "k", "P2O5", "K2O", "phosphorus", "potassium", "olsen_p", "NITROGEN", ""],
)
def test_property_outside_the_allowlist_is_refused(
    db: psycopg.Connection, org_a: Org, prop: str
) -> None:
    refused(db, errors.CheckViolation, estimate(org_a, property=prop))


@pytest.mark.parametrize(("prop", "unit"), sorted(CANONICAL_UNITS.items()))
def test_each_allowed_property_stores_in_its_canonical_unit(
    db: psycopg.Connection, org_a: Org, prop: str, unit: str
) -> None:
    insert(db, "soil_estimate", **estimate(org_a, property=prop, unit=unit))


def test_allowlist_and_units_match_the_soilgrids_catalog() -> None:
    from data_sources.soilgrids.catalog import ALLOWED_PROPERTIES, CONVERSIONS

    assert set(ALLOWED_PROPERTIES) == set(CANONICAL_UNITS)
    assert {p: CONVERSIONS[p].canonical_unit for p in ALLOWED_PROPERTIES} == CANONICAL_UNITS


# --- Values ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"unit": "g/kg"},  # stored canonical only (rule 7)
        {"source": "lab"},
        {"source": "SoilGrids"},
        {"value": -1},
        {"value": Decimal("NaN")},
        {"value": Decimal("Infinity")},
        {"value_q05": Decimal("NaN")},
        {"value_q95": Decimal("Infinity")},
        {"value_q05": 3000},  # lower quantile above the upper one
        {"uncertainty_ratio": -0.1},
        {"uncertainty_ratio": Decimal("NaN")},
        {"resolution_m": 0},
        {"resolution_m": Decimal("Infinity")},
        {"depth_top_cm": -5},
        {"depth_top_cm": 5},  # empty layer
        {"depth_top_cm": 15},  # bottom above top
        {"retrieved_at": datetime(2999, 1, 1, tzinfo=UTC)},  # after the row was stored
    ],
    ids=str,
)
def test_invalid_values_are_refused(
    db: psycopg.Connection, org_a: Org, overrides: dict[str, Any]
) -> None:
    refused(db, errors.CheckViolation, estimate(org_a, **overrides))


# --- Refresh rule: a retrieval adds rows, nothing is overwritten ----------------------------


def test_new_retrieval_adds_a_row_and_keeps_the_old_one(db: psycopg.Connection, org_a: Org) -> None:
    first = insert(db, "soil_estimate", **estimate(org_a))
    later = RETRIEVED + timedelta(days=7)
    second = insert(db, "soil_estimate", **estimate(org_a, retrieved_at=later, value=1600))
    use_context(db, org_a.staff, org_a.id)
    rows = db.execute(
        "select id, value from soil_estimate order by retrieved_at desc, id"
    ).fetchall()
    assert rows == [(second, Decimal("1600")), (first, Decimal("1500"))]


def test_same_retrieval_cannot_be_stored_twice(db: psycopg.Connection, org_a: Org) -> None:
    insert(db, "soil_estimate", **estimate(org_a))
    refused(db, errors.UniqueViolation, estimate(org_a, value=1600))


# --- soil_test.source = 'estimate' stays as it is -------------------------------------------


def test_existing_soil_test_estimates_are_kept_and_not_copied(
    db: psycopg.Connection, org_a: Org
) -> None:
    test = insert(
        db,
        "soil_test",
        organisation_id=org_a.id,
        field_id=org_a.fields[0],
        sample_date=date(2026, 9, 15),
        depth_top_cm=0,
        depth_bottom_cm=15,
        source="estimate",
        created_by=org_a.staff,
    )
    with as_owner(db):
        row = db.execute("select source from soil_test where id = %s", (test,)).fetchone()
        assert row is not None and row[0] == "estimate"
        assert count(db) == 0


@pytest.mark.parametrize("source", ["lucas", "wosis"])
def test_only_soilgrids_is_accepted_for_now(
    db: psycopg.Connection, org_a: Org, source: str
) -> None:
    refused(db, errors.CheckViolation, estimate(org_a, source=source))
