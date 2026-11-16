"""Soil tests match the engine's models; field geometry is PostGIS, one version per season."""

from datetime import date
from typing import Any

import psycopg
import pytest
from psycopg import errors

from .conftest import Org, insert

pytestmark = pytest.mark.db


@pytest.fixture
def soil_test(db: psycopg.Connection, org_a: Org) -> Any:
    return insert(
        db,
        "soil_test",
        organisation_id=org_a.id,
        field_id=org_a.fields[0],
        sample_date=date(2026, 9, 15),
        depth_top_cm=0,
        depth_bottom_cm=15,
        source="lab",
        lab="Example Lab",
        created_by=org_a.staff,
    )


def value(org: Org, soil_test: Any, **overrides: Any) -> dict[str, Any]:
    return {
        "organisation_id": org.id,
        "soil_test_id": soil_test,
        "form": "P",
        "value": 12,
        "unit": "mg/kg",
        "extraction_method": "olsen",
    } | overrides


def test_nutrient_is_derived_from_form(db: psycopg.Connection, org_a: Org, soil_test: Any) -> None:
    row_id = insert(db, "soil_test_value", **value(org_a, soil_test, form="P2O5"))
    row = db.execute("select nutrient from soil_test_value where id = %s", (row_id,)).fetchone()
    assert row == ("P",)


def test_one_form_per_nutrient(db: psycopg.Connection, org_a: Org, soil_test: Any) -> None:
    insert(db, "soil_test_value", **value(org_a, soil_test, form="P"))
    with pytest.raises(errors.UniqueViolation), db.transaction():
        insert(db, "soil_test_value", **value(org_a, soil_test, form="P2O5"))


def test_other_method_needs_detail(db: psycopg.Connection, org_a: Org, soil_test: Any) -> None:
    with pytest.raises(errors.CheckViolation), db.transaction():
        insert(
            db,
            "soil_test_value",
            **value(org_a, soil_test, form="K", extraction_method="other"),
        )
    insert(
        db,
        "soil_test_value",
        **value(
            org_a,
            soil_test,
            form="K",
            extraction_method="other",
            extraction_method_detail="ammonium acetate",
        ),
    )


def test_depth_bottom_below_top(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.CheckViolation), db.transaction():
        insert(
            db,
            "soil_test",
            organisation_id=org_a.id,
            field_id=org_a.fields[0],
            sample_date=date(2026, 9, 15),
            depth_top_cm=15,
            depth_bottom_cm=15,
            source="estimate",
            created_by=org_a.staff,
        )


SQUARE = "MULTIPOLYGON(((0 0, 0 0.01, 0.01 0.01, 0.01 0, 0 0)))"


def geometry(org: Org, field: Any) -> dict[str, Any]:
    return {
        "organisation_id": org.id,
        "field_id": field,
        "season_id": org.season,
        "area_ha": 10,
        "area_source": "manual",
        "created_by": org.staff,
    }


def test_geometry_nullable_and_one_per_season(db: psycopg.Connection, org_a: Org) -> None:
    insert(db, "field_geometry_version", **geometry(org_a, org_a.fields[0]))
    with pytest.raises(errors.UniqueViolation), db.transaction():
        insert(db, "field_geometry_version", **geometry(org_a, org_a.fields[0]))


def test_geometry_is_postgis_multipolygon_4326(db: psycopg.Connection, org_a: Org) -> None:
    db.execute(
        """insert into field_geometry_version
             (organisation_id, field_id, season_id, geom, area_ha, area_source, created_by)
           values (%s, %s, %s, st_geomfromtext(%s, 4326), 10, 'geometry', %s)""",
        (org_a.id, org_a.fields[1], org_a.season, SQUARE, org_a.staff),
    )
    row = db.execute(
        "select st_srid(geom), geometrytype(geom) from field_geometry_version where field_id = %s",
        (org_a.fields[1],),
    ).fetchone()
    assert row == (4326, "MULTIPOLYGON")
    with pytest.raises(errors.InvalidParameterValue), db.transaction():
        db.execute(
            """insert into field_geometry_version
                     (organisation_id, field_id, season_id, geom, area_ha, area_source, created_by)
                   values (%s, %s, %s, st_geomfromtext(%s, 3857), 10, 'geometry', %s)""",
            (org_a.id, org_a.fields[0], org_a.season, SQUARE, org_a.staff),
        )
