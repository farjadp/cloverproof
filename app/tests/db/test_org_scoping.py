"""Org scoping: two users in two organisations never see each other's rows."""

from datetime import date

import psycopg
import pytest
from psycopg import errors

from .conftest import Org, insert

pytestmark = pytest.mark.db

SCOPED_QUERIES = {
    "field": "select id from field where organisation_id in (select member_organisation_ids(%s))",
    "farmer": "select id from farmer where organisation_id in (select member_organisation_ids(%s))",
    "recommendation": (
        "select id from recommendation"
        " where organisation_id in (select member_organisation_ids(%s))"
    ),
    "recommendation_diff": (
        "select final_recommendation_id from recommendation_diff"
        " where organisation_id in (select member_organisation_ids(%s))"
    ),
}


def ids(db: psycopg.Connection, sql: str, user: object) -> set[object]:
    return {row[0] for row in db.execute(sql, (user,))}  # type: ignore[arg-type]


def test_member_organisation_ids(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    sql = "select member_organisation_ids(%s)"
    assert ids(db, sql, org_a.agronomist) == {org_a.id}
    assert ids(db, sql, org_b.agronomist) == {org_b.id}


@pytest.mark.parametrize("name", sorted(SCOPED_QUERIES))
def test_scoped_queries_do_not_cross_orgs(
    db: psycopg.Connection, org_a: Org, org_b: Org, name: str
) -> None:
    sql = SCOPED_QUERIES[name]
    seen_a = ids(db, sql, org_a.agronomist)
    seen_b = ids(db, sql, org_b.agronomist)
    assert seen_a
    assert seen_b
    assert seen_a.isdisjoint(seen_b)
    expected_a = {
        "field": set(org_a.fields),
        "farmer": {org_a.farmer},
        "recommendation": {org_a.engine_rec},
        "recommendation_diff": {org_a.engine_rec},
    }[name]
    assert seen_a == expected_a


def test_disabled_user_sees_nothing(db: psycopg.Connection, org_a: Org) -> None:
    db.execute("update app_user set disabled_at = now() where id = %s", (org_a.staff,))
    assert ids(db, SCOPED_QUERIES["field"], org_a.staff) == set()


def test_child_cannot_point_at_other_org_parent(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    cases = [
        ("farm", {"organisation_id": org_a.id, "farmer_id": org_b.farmer, "name": "x"}),
        ("field", {"organisation_id": org_a.id, "farm_id": org_b.farm, "name": "x"}),
        (
            "crop_plan",
            {
                "organisation_id": org_a.id,
                "field_id": org_a.fields[0],
                "season_id": org_b.season,
                "crop": "wheat",
                "target_yield_t_ha": 5,
                "previous_crop": "wheat",
                "plan_date": date(2027, 2, 1),
                "created_by": org_a.staff,
            },
        ),
    ]
    for table, values in cases:
        with pytest.raises(errors.ForeignKeyViolation), db.transaction():
            insert(db, table, **values)
