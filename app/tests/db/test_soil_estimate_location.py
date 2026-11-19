"""Migration 0033: estimates are tied to the field location they were looked up for."""

from __future__ import annotations

import secrets
import shutil
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import errors
from psycopg.conninfo import make_conninfo

from cloverproof_app.db.migrate import DEFAULT_MIGRATIONS_DIR, migrate
from cloverproof_app.repo import soil_estimates

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
MIGRATION = "0033_soil_estimate_location_revision.sql"


def row(org: Org, revision: int, **overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "organisation_id": org.id,
        "field_id": org.fields[0],
        "season_id": org.season,
        "property": "nitrogen",
        "value": 1500,
        "unit": "mg/kg",
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
    return soil_estimate_provenance(revision) | values | overrides


def revision_of(db: psycopg.Connection, field: UUID) -> int:
    found = db.execute("select location_revision from field where id = %s", (field,)).fetchone()
    assert found is not None
    return int(found[0])


def current(db: psycopg.Connection, org: Org) -> list[soil_estimates.CurrentEstimate]:
    return soil_estimates.current_estimates(db, org.id, org.fields[0], org.season)


def stale(db: psycopg.Connection, org: Org) -> bool:
    return soil_estimates.has_stale_estimates(db, org.id, org.fields[0], org.season)


def refused(
    db: psycopg.Connection, expected: Any, values: dict[str, Any], match: str | None = None
) -> None:
    with pytest.raises(expected, match=match), db.transaction():
        insert(db, "soil_estimate", **values)


# --- field.location_revision -----------------------------------------------------------------


def test_revision_counts_only_real_changes_of_the_point(db: psycopg.Connection, org_a: Org) -> None:
    field = org_a.fields[0]
    assert revision_of(db, field) == 0
    assert locate_field(db, org_a.id, field, 43.55, -80.25) == 1
    assert locate_field(db, org_a.id, field, 43.55, -80.25) == 1  # same point
    db.execute("update field set name = 'Renamed' where id = %s", (field,))
    assert revision_of(db, field) == 1
    assert locate_field(db, org_a.id, field, 43.56, -80.25) == 2
    assert locate_field(db, org_a.id, field, 43.56, -80.24) == 3
    db.execute("update field set location_lat = null, location_lon = null where id = %s", (field,))
    assert revision_of(db, field) == 4  # clearing is a change
    db.execute("update field set location_lat = null, location_lon = null where id = %s", (field,))
    assert revision_of(db, field) == 4


def test_cp_app_cannot_forge_the_revision(db: psycopg.Connection, org_a: Org) -> None:
    field = org_a.fields[0]
    locate_field(db, org_a.id, field)
    db.execute("update field set location_revision = 99 where id = %s", (field,))
    assert revision_of(db, field) == 1
    db.execute("update field set location_revision = 0, name = 'Again' where id = %s", (field,))
    assert revision_of(db, field) == 1
    # Moving while naming a revision: the value is still the next one.
    db.execute(
        "update field set location_lat = 44, location_lon = -80, location_revision = 1"
        " where id = %s",
        (field,),
    )
    assert revision_of(db, field) == 2
    created = insert(
        db,
        "field",
        organisation_id=org_a.id,
        farm_id=org_a.farm,
        name="New",
        location_revision=99,
    )
    assert revision_of(db, created) == 0


# --- What a new row must carry ----------------------------------------------------------------


def test_new_columns_hold_no_coordinates(db: psycopg.Connection) -> None:
    columns = db.execute(
        "select column_name, data_type from information_schema.columns"
        " where table_schema = 'public' and table_name = 'soil_estimate'"
    ).fetchall()
    names = {name for name, _ in columns}
    assert {"field_location_revision", "statistic", "layer_url", "citation"} <= names
    assert not [n for n in names if any(p in n for p in ("lat", "lon", "geom", "point"))]
    assert "USER-DEFINED" not in {kind for _, kind in columns}


def test_checks_are_not_valid_and_still_refuse_new_rows(db: psycopg.Connection, org_a: Org) -> None:
    names = {
        "soil_estimate_location_revision_required",
        "soil_estimate_statistic_mean",
        "soil_estimate_standard_depth",
        "soil_estimate_layer_url_published",
        "soil_estimate_citation_text",
    }
    found = db.execute(
        "select conname, convalidated from pg_constraint"
        " where conrelid = 'soil_estimate'::regclass and conname = any(%s)",
        (list(names),),
    ).fetchall()
    assert dict(found) == dict.fromkeys(names, False)

    revision = locate_field(db, org_a.id, org_a.fields[0])
    good = row(org_a, revision)
    url = good["layer_url"]
    for overrides in (
        {"statistic": None},
        {"statistic": "Q0.05"},
        {"layer_url": None},
        {"citation": None},
        {"citation": "   "},
        {"layer_url": f"{url}?lat=43.55&lon=-80.25"},
        {"layer_url": url.replace("nitrogen/", "soc/")},
        {"layer_url": url.replace("0-5cm", "5-15cm")},
        {"layer_url": url.replace("_mean", "_Q0.05")},
        {"layer_url": url.replace("https://files.isric.org", "https://example.org")},
        # A depth SoilGrids does not publish, even with a matching address.
        {"depth_bottom_cm": 7, "layer_url": url.replace("0-5cm", "0-7cm")},
    ):
        refused(db, errors.CheckViolation, good | overrides)
    insert(db, "soil_estimate", **good)


def test_row_needs_the_fields_current_revision(db: psycopg.Connection, org_a: Org) -> None:
    field = org_a.fields[0]
    refused(db, errors.CheckViolation, row(org_a, 0), match="no location")

    revision = locate_field(db, org_a.id, field)
    for wrong in (revision - 1, revision + 1, None):
        refused(
            db,
            errors.CheckViolation,
            row(org_a, revision, field_location_revision=wrong),
            match="another location",
        )
    insert(db, "soil_estimate", **row(org_a, revision))

    db.execute("update field set location_lat = null, location_lon = null where id = %s", (field,))
    cleared = revision_of(db, field)
    refused(db, errors.CheckViolation, row(org_a, cleared), match="no location")


def test_other_org_cannot_insert_or_read(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    revision = locate_field(db, org_a.id, org_a.fields[0])
    insert(db, "soil_estimate", **row(org_a, revision))

    # Org B's member, naming org A's field under either organisation.
    use_context(db, org_b.agronomist, org_b.id)
    assert current(db, org_a) == []
    assert not stale(db, org_a)
    values = row(org_a, revision, created_by=org_b.agronomist)
    columns = ", ".join(values)
    marks = ", ".join(["%s"] * len(values))
    query = f"insert into soil_estimate ({columns}) values ({marks})"
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(query, list(values.values()))  # type: ignore[arg-type]
    with pytest.raises(errors.ForeignKeyViolation), db.transaction():
        db.execute(
            query,  # type: ignore[arg-type]
            list((values | {"organisation_id": org_b.id, "season_id": org_b.season}).values()),
        )


def test_service_account_cannot_load_a_real_farmers_field(
    db: psycopg.Connection, org_a: Org
) -> None:
    """Rule 12: the location check must fail closed when the field row is hidden."""
    revision = locate_field(db, org_a.id, org_a.fields[0])
    with as_owner(db):
        service = insert(
            db,
            "app_user",
            email="service@example.org",
            display_name="Service",
            actor_kind="service",
        )
    insert(db, "membership", organisation_id=org_a.id, user_id=service, role="advisor")
    use_context(db, service, org_a.id)
    values = row(org_a, revision, created_by=service)
    columns = ", ".join(values)
    marks = ", ".join(["%s"] * len(values))
    with pytest.raises(errors.ForeignKeyViolation), db.transaction():
        db.execute(
            f"insert into soil_estimate ({columns}) values ({marks})",  # type: ignore[arg-type]
            list(values.values()),
        )


def test_service_account_cannot_read_a_real_farmers_estimates(
    db: psycopg.Connection, org_a: Org
) -> None:
    """Rule 12: values from a public map could point to the farm."""
    revision = locate_field(db, org_a.id, org_a.fields[0])
    with as_owner(db):
        service = insert(
            db,
            "app_user",
            email="service-read@example.org",
            display_name="Service",
            actor_kind="service",
        )
        insert(db, "membership", organisation_id=org_a.id, user_id=service, role="advisor")
        insert(db, "soil_estimate", **row(org_a, revision))
    use_context(db, service, org_a.id)
    assert db.execute("select count(*) from soil_estimate").fetchone() == (0,)
    use_context(db, org_a.agronomist, org_a.id)
    assert db.execute("select count(*) from soil_estimate").fetchone() == (1,)


def test_rows_stay_immutable_after_a_move(db: psycopg.Connection, org_a: Org) -> None:
    revision = locate_field(db, org_a.id, org_a.fields[0])
    row_id = insert(db, "soil_estimate", **row(org_a, revision))
    locate_field(db, org_a.id, org_a.fields[0], 44.0, -80.0)
    for sql in (
        "update soil_estimate set field_location_revision = 2 where id = %s",
        "delete from soil_estimate where id = %s",
    ):
        with pytest.raises(errors.InsufficientPrivilege), db.transaction():
            db.execute(sql, (row_id,))  # type: ignore[arg-type]
        with pytest.raises(errors.InsufficientPrivilege, match="immutable"), as_owner(db):
            db.execute(sql, (row_id,))  # type: ignore[arg-type]


# --- Current and stale ------------------------------------------------------------------------


def test_latest_retrieval_of_the_current_revision_is_current(
    db: psycopg.Connection, org_a: Org
) -> None:
    revision = locate_field(db, org_a.id, org_a.fields[0])
    assert current(db, org_a) == []
    assert not stale(db, org_a)
    insert(db, "soil_estimate", **row(org_a, revision))
    later = RETRIEVED + timedelta(days=7)
    insert(db, "soil_estimate", **row(org_a, revision, retrieved_at=later, value=1600))
    other_depth = soil_estimate_provenance(revision, "nitrogen", 5, 15)
    insert(
        db,
        "soil_estimate",
        **row(org_a, revision, depth_top_cm=5, depth_bottom_cm=15, value=1200) | other_depth,
    )

    rows = current(db, org_a)
    assert [(r.depth, r.value, r.retrieved_on) for r in rows] == [
        ("0-5cm", Decimal("1600"), later.date()),
        ("5-15cm", Decimal("1200"), RETRIEVED.date()),
    ]
    assert not stale(db, org_a)


def test_move_makes_rows_stale_and_a_reload_replaces_them(
    db: psycopg.Connection, org_a: Org
) -> None:
    first = locate_field(db, org_a.id, org_a.fields[0])
    old_id = insert(db, "soil_estimate", **row(org_a, first))

    moved = locate_field(db, org_a.id, org_a.fields[0], 44.0, -80.0)
    assert current(db, org_a) == []
    assert stale(db, org_a)

    # Same retrieval date as the old row: the revision keeps them apart.
    insert(db, "soil_estimate", **row(org_a, moved, value=1700))
    assert [r.value for r in current(db, org_a)] == [Decimal("1700")]
    assert not stale(db, org_a)
    kept = db.execute("select count(*) from soil_estimate where id = %s", (old_id,)).fetchone()
    assert kept == (1,)

    with pytest.raises(errors.UniqueViolation), db.transaction():
        insert(db, "soil_estimate", **row(org_a, moved, value=1800))


def test_newer_row_of_an_old_location_does_not_hide_the_current_one(
    db: psycopg.Connection, org_a: Org
) -> None:
    first = locate_field(db, org_a.id, org_a.fields[0])
    later = RETRIEVED + timedelta(days=7)
    insert(db, "soil_estimate", **row(org_a, first, retrieved_at=later))
    moved = locate_field(db, org_a.id, org_a.fields[0], 44.0, -80.0)
    insert(db, "soil_estimate", **row(org_a, moved, value=1700))
    assert [r.value for r in current(db, org_a)] == [Decimal("1700")]


def test_returning_to_the_old_point_still_needs_a_reload(
    db: psycopg.Connection, org_a: Org
) -> None:
    first = locate_field(db, org_a.id, org_a.fields[0])
    insert(db, "soil_estimate", **row(org_a, first))
    locate_field(db, org_a.id, org_a.fields[0], 44.0, -80.0)
    locate_field(db, org_a.id, org_a.fields[0])
    assert current(db, org_a) == []
    assert stale(db, org_a)


def test_clearing_the_location_makes_rows_stale(db: psycopg.Connection, org_a: Org) -> None:
    revision = locate_field(db, org_a.id, org_a.fields[0])
    insert(db, "soil_estimate", **row(org_a, revision))
    db.execute(
        "update field set location_lat = null, location_lon = null where id = %s",
        (org_a.fields[0],),
    )
    assert current(db, org_a) == []
    assert stale(db, org_a)


# --- Upgrade of a database that already has 0031 rows (staging) ---------------------------------


@pytest.fixture
def before_0033(admin_url: str, tmp_path: Path) -> Iterator[str]:
    """A private database migrated up to, not including, 0033."""
    name = f"cp_test_{secrets.token_hex(4)}"
    older = tmp_path / "older"
    older.mkdir()
    for path in DEFAULT_MIGRATIONS_DIR.glob("*.sql"):
        if path.name < MIGRATION:
            shutil.copy(path, older / path.name)
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(f'create database "{name}"')
    url = make_conninfo(admin_url, dbname=name)
    try:
        with psycopg.connect(url, autocommit=True) as conn:
            migrate(conn, older, log=lambda _: None)
        yield url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(f'drop database if exists "{name}" with (force)')


def one_id(conn: psycopg.Connection, sql: str, params: tuple[Any, ...]) -> UUID:
    found = conn.execute(sql, params).fetchone()  # type: ignore[arg-type]
    assert found is not None
    return found[0]


def test_upgrade_keeps_old_rows_as_stale_and_a_load_blocks_a_move(before_0033: str) -> None:
    with psycopg.connect(before_0033, autocommit=True) as su:
        org = one_id(su, "insert into organisation (name) values ('O') returning id", ())
        user = one_id(
            su,
            "insert into app_user (email, display_name) values ('u@example.org', 'U') returning id",
            (),
        )
        su.execute(
            "insert into membership (organisation_id, user_id, role) values (%s, %s, 'agronomist')",
            (org, user),
        )
        farmer = one_id(
            su,
            "insert into farmer (organisation_id, display_name) values (%s, 'F') returning id",
            (org,),
        )
        farm = one_id(
            su,
            "insert into farm (organisation_id, farmer_id, name) values (%s, %s, 'A') returning id",
            (org, farmer),
        )
        field = one_id(
            su,
            "insert into field (organisation_id, farm_id, name, location_lat, location_lon)"
            " values (%s, %s, 'N', 43.55, -80.25) returning id",
            (org, farm),
        )
        season = one_id(
            su, "insert into season (organisation_id, label) values (%s, '2027') returning id",
            (org,),
        )  # fmt: skip
        legacy = (
            org, field, season, "nitrogen", 1500, "mg/kg", 0.9, "soilgrids", "2.0", 250, 0, 5,
            RETRIEVED, "CC BY 4.0", "SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0",
            user,
        )  # fmt: skip
        su.execute(
            "insert into soil_estimate (organisation_id, field_id, season_id, property, value,"
            " unit, uncertainty_ratio, source, source_version, resolution_m, depth_top_cm,"
            " depth_bottom_cm, retrieved_at, licence, attribution, created_by)"
            " values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            legacy,
        )
        assert migrate(su, DEFAULT_MIGRATIONS_DIR, log=lambda _: None) == [MIGRATION]
        assert su.execute("select location_revision from field").fetchone() == (0,)

    with psycopg.connect(before_0033) as loader, psycopg.connect(before_0033) as mover:
        loader.execute("set local role cp_app")
        use_context(loader, user, org)
        assert soil_estimates.current_estimates(loader, org, field, season) == []
        assert soil_estimates.has_stale_estimates(loader, org, field, season)

        estimate = soil_estimates.NewEstimate(
            property="nitrogen", depth_top_cm=0, depth_bottom_cm=5, statistic="mean", value=1500.0,
            unit="mg/kg", value_q05=None, value_q95=None, uncertainty_ratio=0.9,
            source="soilgrids", source_version="2.0", resolution_m=250.0, retrieved_at=RETRIEVED,
            licence="CC BY 4.0", attribution="SoilGrids 2.0, ISRIC, CC BY 4.0",
            citation="Poggio et al. 2021",
            layer_url=soil_estimate_provenance(0)["layer_url"],
        )  # fmt: skip
        soil_estimates.insert_estimate(
            loader, org, field_id=field, season_id=season, revision=0, created_by=user,
            estimate=estimate,
        )  # fmt: skip
        assert not soil_estimates.has_stale_estimates(loader, org, field, season)

        # The uncommitted load holds the field: a move has to wait for it.
        mover.execute("set local lock_timeout = '200ms'")
        with pytest.raises(errors.LockNotAvailable):
            mover.execute("update field set location_lat = 44 where id = %s", (field,))
        mover.rollback()
        loader.rollback()
