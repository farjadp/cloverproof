"""Row-level security (migrations 0021, 0022; ADR 0008; ciso criteria adr-0008-rls-review-criteria).

Every table with RLS enabled must be a key of TENANT_CASES (or in WEBSITE_TABLES or
CATALOG_TABLES): the coverage test reads the list from pg_class, so a new RLS table without
a case here fails. Catalog tables are global and deliberately not organisation-scoped, so
they are not tenant cases and no org boundary is demanded of them; their allow/deny tests
are in test_fertilizer_product.py.
Per tenant table, parametrized: same org reads and writes its rows; another org's context
sees 0 rows and cannot insert, update, move or delete across the boundary; no context,
an empty context, a context for an organisation the user is not in, and the owner role
(FORCE) all see 0 rows (deny by default). Catalog checks C-0 / C-1 and the role checks of
ciso §1 are at the end.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
import yaml
from psycopg import errors, sql
from psycopg.types.json import Jsonb

from cloverproof_app.db.migrate import REPO_ROOT
from cloverproof_app.db.pool import reset_connection

from .conftest import (
    MigratedDb,
    Org,
    as_owner,
    as_role,
    insert,
    locate_field,
    recommendation_values,
    soil_estimate_provenance,
    use_context,
)

pytestmark = pytest.mark.db

RLS_TABLES = yaml.safe_load((REPO_ROOT / "db" / "rls_tables.yaml").read_text())
WEBSITE_TABLES = {"pilot_request", "site_event"}
# Global reference data, not org data: never add these to TENANT_CASES (ADR 0008 §5).
CATALOG_TABLES = {"fertilizer_product"}
SQUARE = "MULTIPOLYGON(((0 0, 0 0.01, 0.01 0.01, 0.01 0, 0 0)))"


def org_col(table: str) -> str:
    return RLS_TABLES["tenant"][table]


def org_admin_of(db: psycopg.Connection, org: Org) -> UUID:
    row = db.execute(
        "select user_id from membership where organisation_id = %s and role = 'org_admin'",
        (org.id,),
    ).fetchone()
    assert row is not None
    return row[0]


# --- Fresh row builders: values for one new row of `org` (prerequisites created as needed).


def _crop_plan(db: psycopg.Connection, org: Org) -> UUID:
    return insert(
        db,
        "crop_plan",
        organisation_id=org.id,
        field_id=org.fields[1],
        season_id=org.season,
        crop="wheat",
        target_yield_t_ha=5.0,
        previous_crop="wheat",
        plan_date=date(2027, 2, 1),
        created_by=org.staff,
    )


def _soil_test(db: psycopg.Connection, org: Org) -> dict[str, Any]:
    return {
        "organisation_id": org.id,
        "field_id": org.fields[1],
        "sample_date": date(2026, 9, 15),
        "depth_top_cm": 0,
        "depth_bottom_cm": 15,
        "source": "lab",
        "lab": "Example Lab",
        "created_by": org.staff,
    }


def _recommendation(db: psycopg.Connection, org: Org, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "organisation_id": org.id,
        "crop_plan_id": _crop_plan(db, org),
        "kind": "engine",
        "created_by": org.staff,
        **recommendation_values(result),
    }


def _line(org: Org, recommendation: UUID) -> dict[str, Any]:
    return {
        "organisation_id": org.id,
        "recommendation_id": recommendation,
        "nutrient": "N",
        "nutrient_form": "N",
        "rate_kg_ha": 100,
        "explanation": "Synthetic line",
        "uses_placeholder": True,
        "confidence": "low",
        "created_by": org.staff,
    }


def _soil_estimate(db: psycopg.Connection, org: Org, field: UUID) -> dict[str, Any]:
    return soil_estimate_provenance(locate_field(db, org.id, field)) | {
        "organisation_id": org.id,
        "field_id": field,
        "season_id": org.season,
        "property": "nitrogen",
        "value": 1500,
        "unit": "mg/kg",
        "value_q05": 900,
        "value_q95": 2300,
        "source": "soilgrids",
        "source_version": "2.0",
        "resolution_m": 250,
        "depth_top_cm": 0,
        "depth_bottom_cm": 5,
        "retrieved_at": datetime(2026, 11, 1, tzinfo=UTC),
        "licence": "CC BY 4.0",
        "attribution": "SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0",
        "created_by": org.staff,
    }


Builder = Callable[[psycopg.Connection, Org, dict[str, Any]], dict[str, Any]]

# table -> (fresh row builder, column cp_app may UPDATE or None, cp_app may DELETE)
TENANT_CASES: dict[str, tuple[Builder, str | None, bool]] = {
    "farmer": (
        lambda db, o, r: {"organisation_id": o.id, "display_name": "New farmer"},
        "display_name",
        True,
    ),
    "farm": (
        lambda db, o, r: {"organisation_id": o.id, "farmer_id": o.farmer, "name": "New farm"},
        "name",
        True,
    ),
    "field": (
        lambda db, o, r: {"organisation_id": o.id, "farm_id": o.farm, "name": "New field"},
        "name",
        True,
    ),
    "season": (
        lambda db, o, r: {"organisation_id": o.id, "label": f"S-{uuid4().hex[:8]}"},
        "label",
        True,
    ),
    "field_geometry_version": (
        lambda db, o, r: {
            "organisation_id": o.id,
            "field_id": o.fields[1],
            "season_id": o.season,
            "area_ha": 10,
            "area_source": "manual",
            "created_by": o.staff,
        },
        "area_ha",
        True,
    ),
    "soil_test": (lambda db, o, r: _soil_test(db, o), "lab", True),
    "soil_test_value": (
        lambda db, o, r: {
            "organisation_id": o.id,
            "soil_test_id": insert(db, "soil_test", **_soil_test(db, o)),
            "form": "K",
            "value": 120,
            "unit": "mg/kg",
            "extraction_method": "olsen",
        },
        "value",
        True,
    ),
    "soil_estimate": (lambda db, o, r: _soil_estimate(db, o, o.fields[1]), None, False),
    "crop_plan": (
        lambda db, o, r: {
            "organisation_id": o.id,
            "field_id": o.fields[1],
            "season_id": o.season,
            "crop": "wheat",
            "target_yield_t_ha": 5.0,
            "previous_crop": "wheat",
            "plan_date": date(2027, 2, 1),
            "created_by": o.staff,
        },
        "target_yield_t_ha",
        True,
    ),
    "application_log": (
        lambda db, o, r: {
            "organisation_id": o.id,
            "crop_plan_id": o.crop_plan,
            "form": "N",
            "planned_rate_kg_ha": 100,
            "created_by": o.staff,
        },
        "notes",
        True,
    ),
    "recommendation": (lambda db, o, r: _recommendation(db, o, r), None, False),
    "recommendation_line": (
        lambda db, o, r: _line(o, insert(db, "recommendation", **_recommendation(db, o, r))),
        None,
        False,
    ),
    "review": (
        lambda db, o, r: {
            "organisation_id": o.id,
            "recommendation_id": insert(db, "recommendation", **_recommendation(db, o, r)),
            "decision": "reject",
            "reason": "Yield target too high",
            "reviewer_id": o.agronomist,
            "minutes_spent": 5,
        },
        None,
        False,
    ),
    "proof_document": (
        lambda db, o, r: {
            "organisation_id": o.id,
            "recommendation_id": o.engine_rec,
            "sha256": "b" * 64,
            "storage_key": f"proof/{o.id}/{o.engine_rec}/{'b' * 64}.pdf",
            "created_by": o.agronomist,
        },
        None,
        False,
    ),
    "access_grant": (
        lambda db, o, r: {
            "owner_organisation_id": o.id,
            "farmer_id": o.farmer,
            "grantee_user_id": o.staff,
            "scope": "view",
            "granted_by": org_admin_of(db, o),
        },
        "revoke_reason",
        False,
    ),
}


def complete(db: psycopg.Connection, org: Org, result: dict[str, Any]) -> None:
    """Give org one row in every tenant table (make_org has the first six)."""
    admin = insert(db, "app_user", email=f"admin-{org.id}@example.org", display_name="Org admin")
    insert(db, "membership", organisation_id=org.id, user_id=admin, role="org_admin")
    insert(
        db,
        "field_geometry_version",
        organisation_id=org.id,
        field_id=org.fields[0],
        season_id=org.season,
        area_ha=10,
        area_source="manual",
        created_by=org.staff,
    )
    test = insert(db, "soil_test", **(_soil_test(db, org) | {"field_id": org.fields[0]}))
    insert(
        db,
        "soil_test_value",
        organisation_id=org.id,
        soil_test_id=test,
        form="P",
        value=12,
        unit="mg/kg",
        extraction_method="olsen",
    )
    insert(db, "soil_estimate", **_soil_estimate(db, org, org.fields[0]))
    insert(
        db,
        "application_log",
        organisation_id=org.id,
        crop_plan_id=org.crop_plan,
        form="N",
        planned_rate_kg_ha=90,
        created_by=org.staff,
    )
    insert(db, "recommendation_line", **_line(org, org.engine_rec))
    insert(
        db,
        "review",
        organisation_id=org.id,
        recommendation_id=org.engine_rec,
        decision="approve",
        reviewer_id=org.agronomist,
        minutes_spent=12,
    )
    insert(
        db,
        "proof_document",
        organisation_id=org.id,
        recommendation_id=org.engine_rec,
        sha256="a" * 64,
        storage_key=f"proof/{org.id}/{org.engine_rec}/{'a' * 64}.pdf",
        created_by=org.agronomist,
    )
    insert(
        db,
        "access_grant",
        owner_organisation_id=org.id,
        farmer_id=org.farmer,
        grantee_user_id=org.agronomist,
        scope="view",
        granted_by=admin,
    )


@pytest.fixture
def two_orgs(
    db: psycopg.Connection, org_a: Org, org_b: Org, engine_result: dict[str, Any]
) -> tuple[Org, Org]:
    complete(db, org_a, engine_result)
    complete(db, org_b, engine_result)
    use_context(db, org_a.agronomist, org_a.id)
    return org_a, org_b


def count(db: psycopg.Connection, table: str, org_id: UUID | None = None) -> int:
    query = sql.SQL("select count(*) from {}").format(sql.Identifier(table))
    params: tuple[Any, ...] = ()
    if org_id is not None:
        query += sql.SQL(" where {} = %s").format(sql.Identifier(org_col(table)))
        params = (org_id,)
    row = db.execute(query, params).fetchone()
    assert row is not None
    return int(row[0])


def total(db: psycopg.Connection, table: str, org_id: UUID) -> int:
    with as_owner(db):
        return count(db, table, org_id)


def insert_row(db: psycopg.Connection, table: str, values: dict[str, Any]) -> None:
    """Insert as the current role and context (no fixture context switch)."""
    query = sql.SQL("insert into {} ({}) values ({})").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, values)),
        sql.SQL(", ").join(sql.Placeholder() * len(values)),
    )
    params = [Jsonb(v) if isinstance(v, dict) else v for v in values.values()]
    db.execute(query, params)


def refused(db: psycopg.Connection, fn: Callable[[], Any], table: str = "") -> None:
    # proof_document's BEFORE trigger reads the approval under RLS first: from the wrong
    # context it sees none and fails closed with 23514 before the policy check runs.
    expected: Any = errors.InsufficientPrivilege
    if table == "proof_document":
        expected = (errors.InsufficientPrivilege, errors.CheckViolation)
    with pytest.raises(expected), db.transaction():
        fn()


TENANT = sorted(TENANT_CASES)


# --- Coverage -------------------------------------------------------------------------


def test_every_rls_table_has_a_case(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select relname from pg_class where relnamespace = 'public'::regnamespace"
        " and relkind in ('r', 'p') and relrowsecurity"
    ).fetchall()
    assert {r[0] for r in rows} == set(TENANT_CASES) | WEBSITE_TABLES | CATALOG_TABLES
    assert set(RLS_TABLES["tenant"]) == set(TENANT_CASES)


def test_c0_every_public_table_is_classified_once(db: psycopg.Connection) -> None:
    listed = (
        list(RLS_TABLES["tenant"])
        + RLS_TABLES["identity"]
        + RLS_TABLES["website"]
        + RLS_TABLES["website_admin"]
        + RLS_TABLES["catalog"]
        + RLS_TABLES["global"]
    )
    assert len(listed) == len(set(listed))
    rows = db.execute(
        "select relname from pg_class where relnamespace = 'public'::regnamespace"
        " and relkind in ('r', 'p')"
    ).fetchall()
    assert {r[0] for r in rows} == set(listed)
    assert set(RLS_TABLES["website"]) == WEBSITE_TABLES
    assert set(RLS_TABLES["catalog"]) == CATALOG_TABLES


def test_c1_catalog_state_matches_class(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select relname, relrowsecurity, relforcerowsecurity from pg_class"
        " where relnamespace = 'public'::regnamespace and relkind in ('r', 'p')"
    ).fetchall()
    state = {r[0]: (r[1], r[2]) for r in rows}
    for table in list(RLS_TABLES["tenant"]) + RLS_TABLES["catalog"]:
        assert state[table] == (True, True), table
    for table in RLS_TABLES["website"]:
        assert state[table] == (True, False), table
    for table in RLS_TABLES["identity"] + RLS_TABLES["website_admin"] + RLS_TABLES["global"]:
        assert state[table] == (False, False), table


@pytest.mark.parametrize("table", TENANT)
def test_tenant_table_has_restrictive_org_boundary(db: psycopg.Connection, table: str) -> None:
    rows = db.execute(
        "select qual, with_check from pg_policies where schemaname = 'public'"
        " and tablename = %s and permissive = 'RESTRICTIVE' and cmd = 'ALL'"
        " and roles = '{cp_app}' and qual like %s and with_check like %s",
        (table, "%app_ctx_org()%", "%app_ctx_org()%"),
    ).fetchall()
    assert rows, f"{table}: no restrictive org boundary policy"


@pytest.mark.parametrize("table", sorted(CATALOG_TABLES))
def test_catalog_table_is_deliberately_not_org_scoped(db: psycopg.Connection, table: str) -> None:
    assert table not in TENANT_CASES
    columns = db.execute(
        "select column_name from information_schema.columns"
        " where table_schema = 'public' and table_name = %s and column_name like %s",
        (table, "%organisation%"),
    ).fetchall()
    assert columns == []
    policies = db.execute(
        "select policyname from pg_policies where schemaname = 'public' and tablename = %s"
        " and (coalesce(qual, '') like %s or coalesce(with_check, '') like %s)",
        (table, "%app_ctx_org()%", "%app_ctx_org()%"),
    ).fetchall()
    assert policies == []


@pytest.mark.parametrize("table", TENANT)
def test_tenant_table_has_index_led_by_org_column(db: psycopg.Connection, table: str) -> None:
    row = db.execute(
        "select count(*) from pg_index i join pg_attribute a"
        " on a.attrelid = i.indrelid and a.attnum = i.indkey[0]"
        " where i.indrelid = %s::regclass and a.attname = %s",
        (table, org_col(table)),
    ).fetchone()
    assert row is not None and row[0] >= 1


def test_policies_never_to_public_and_insert_update_have_check(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select tablename, policyname from pg_policies where schemaname = 'public'"
        " and ('public' = any(roles) or (cmd in ('INSERT', 'UPDATE') and with_check is null))"
    ).fetchall()
    assert rows == []


def test_no_cp_app_policy_grants_by_platform_role(db: psycopg.Connection) -> None:
    """Platform role opens no organisation data. Only catalog tables may name it."""
    rows = db.execute(
        "select tablename, policyname from pg_policies where 'cp_app' = any(roles)"
        " and (coalesce(qual, '') ilike '%%platform_role%%'"
        "      or coalesce(with_check, '') ilike '%%platform_role%%')"
        " and not tablename = any(%s)",
        (sorted(CATALOG_TABLES),),
    ).fetchall()
    assert rows == []


def test_catalog_policies_read_platform_role_only_through_the_helper(
    db: psycopg.Connection,
) -> None:
    """The raw setting can be forged; app_ctx_platform_role() checks it against the user."""
    rows = db.execute(
        "select policyname from pg_policies where tablename = any(%s)"
        " and (coalesce(qual, '') ilike '%%app.platform_role%%'"
        "      or coalesce(with_check, '') ilike '%%app.platform_role%%'"
        "      or coalesce(qual, '') ilike '%%current_setting%%'"
        "      or coalesce(with_check, '') ilike '%%current_setting%%')",
        (sorted(CATALOG_TABLES),),
    ).fetchall()
    assert rows == []


def test_roles_cannot_bypass(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select rolname, rolbypassrls, rolsuper from pg_roles"
        " where rolname in ('cp_app', 'cp_admin', 'cp_website', 'cp_migrator')"
    ).fetchall()
    assert len(rows) == 4
    assert all(not bypass and not superuser for _, bypass, superuser in rows)
    for other in ("cp_migrator", "pg_read_all_data", "pg_write_all_data"):
        row = db.execute("select pg_has_role('cp_app', %s, 'member')", (other,)).fetchone()
        assert row == (False,), other


def test_cp_app_owns_nothing(db: psycopg.Connection) -> None:
    for catalog, owner in (
        ("pg_class", "relowner"),
        ("pg_proc", "proowner"),
        ("pg_type", "typowner"),
    ):
        row = db.execute(
            sql.SQL(
                "select count(*) from {} where {} in"
                " (select oid from pg_roles where not rolsuper"
                " and pg_has_role(oid, 'cp_app', 'member'))"
            ).format(sql.Identifier(catalog), sql.Identifier(owner))
        ).fetchone()
        assert row == (0,), catalog


def test_cp_app_has_no_truncate_references_trigger(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select c.relname from pg_class c where c.relnamespace = 'public'::regnamespace"
        " and c.relkind in ('r', 'p') and (has_table_privilege('cp_app', c.oid, 'TRUNCATE')"
        " or has_table_privilege('cp_app', c.oid, 'REFERENCES')"
        " or has_table_privilege('cp_app', c.oid, 'TRIGGER'))"
    ).fetchall()
    assert rows == []


def test_views_are_security_invoker(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select relname from pg_class where relkind = 'v'"
        " and relnamespace = 'public'::regnamespace"
        " and relname not in ('geometry_columns', 'geography_columns')"
        " and not coalesce('security_invoker=true' = any(reloptions), false)"
    ).fetchall()
    assert rows == []


def test_no_app_settings_in_role_or_database_defaults(db: psycopg.Connection) -> None:
    row = db.execute(
        "select count(*) from pg_db_role_setting s, unnest(s.setconfig) c where c like 'app.%'"
    ).fetchone()
    assert row == (0,)


def test_context_helpers_are_stable_pinned_and_owned_by_migrator(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select p.proname, p.provolatile, p.prosecdef, pg_get_userbyid(p.proowner), p.proconfig"
        " from pg_proc p where p.pronamespace = 'public'::regnamespace"
        " and p.proname like 'app_ctx_%'"
    ).fetchall()
    assert len(rows) == 4
    for name, volatile, secdef, owner, config in rows:
        assert (volatile, secdef, owner) == ("s", False, "cp_migrator"), name
        assert any(c.startswith("search_path=") for c in config), name


# --- Allowed: same org ------------------------------------------------------------------


@pytest.mark.parametrize("table", TENANT)
def test_same_org_sees_its_rows(
    db: psycopg.Connection, two_orgs: tuple[Org, Org], table: str
) -> None:
    a, _ = two_orgs
    assert count(db, table, a.id) == total(db, table, a.id) >= 1
    assert count(db, table) == count(db, table, a.id)


@pytest.mark.parametrize("table", TENANT)
def test_same_org_can_insert(
    db: psycopg.Connection,
    two_orgs: tuple[Org, Org],
    engine_result: dict[str, Any],
    table: str,
) -> None:
    a, _ = two_orgs
    values = TENANT_CASES[table][0](db, a, engine_result)
    author = next(
        (values[c] for c in ("created_by", "reviewer_id", "granted_by") if c in values), None
    )
    use_context(db, author or a.agronomist, a.id)
    before = count(db, table, a.id)
    insert_row(db, table, values)
    assert count(db, table, a.id) == before + 1


@pytest.mark.parametrize("table", [t for t in TENANT if TENANT_CASES[t][1]])
def test_same_org_can_update(db: psycopg.Connection, two_orgs: tuple[Org, Org], table: str) -> None:
    a, _ = two_orgs
    column = TENANT_CASES[table][1]
    if table == "access_grant":
        use_context(db, org_admin_of(db, a), a.id)
        cur = db.execute(
            "update access_grant set revoked_at = now(), revoked_by = %s, revoke_reason = 'test'"
            " where owner_organisation_id = %s",
            (org_admin_of(db, a), a.id),
        )
    else:
        cur = db.execute(
            sql.SQL("update {t} set {c} = {c} where {o} = %s").format(
                t=sql.Identifier(table), c=sql.Identifier(column), o=sql.Identifier(org_col(table))
            ),
            (a.id,),
        )
    assert cur.rowcount >= 1


# --- Denied: other org ------------------------------------------------------------------


@pytest.mark.parametrize("table", TENANT)
def test_other_org_rows_are_invisible(
    db: psycopg.Connection, two_orgs: tuple[Org, Org], table: str
) -> None:
    _, b = two_orgs
    assert total(db, table, b.id) >= 1
    assert count(db, table, b.id) == 0


def test_other_org_rows_invisible_in_views(
    db: psycopg.Connection, two_orgs: tuple[Org, Org]
) -> None:
    _, b = two_orgs
    for view in ("recommendation_state", "recommendation_diff"):
        row = db.execute(
            sql.SQL("select count(*) from {} where organisation_id = %s").format(
                sql.Identifier(view)
            ),
            (b.id,),
        ).fetchone()
        assert row == (0,), view


@pytest.mark.parametrize("table", TENANT)
def test_insert_into_other_org_is_refused(
    db: psycopg.Connection,
    two_orgs: tuple[Org, Org],
    engine_result: dict[str, Any],
    table: str,
) -> None:
    a, b = two_orgs
    values = TENANT_CASES[table][0](db, b, engine_result)
    # Org A's context; author columns name org A's user, as a forging app bug would.
    for column in ("created_by", "reviewer_id"):
        if column in values:
            values[column] = a.agronomist
    if "granted_by" in values:
        values["granted_by"] = org_admin_of(db, a)
        use_context(db, values["granted_by"], a.id)
    else:
        use_context(db, a.agronomist, a.id)
    before = total(db, table, b.id)
    refused(db, lambda: insert_row(db, table, values), table)
    assert total(db, table, b.id) == before


@pytest.mark.parametrize("table", TENANT)
def test_update_and_delete_of_other_org_touch_nothing(
    db: psycopg.Connection, two_orgs: tuple[Org, Org], table: str
) -> None:
    _, b = two_orgs
    _, column, deletable = TENANT_CASES[table]
    org = sql.Identifier(org_col(table))
    t = sql.Identifier(table)
    if column is None:
        # No UPDATE grant at all (immutable tables, ADR 0002).
        refused(db, lambda: db.execute(sql.SQL("update {} set {} = {}").format(t, org, org)))
    else:
        c = sql.Identifier(column)
        cur = db.execute(
            sql.SQL("update {t} set {c} = {c} where {o} = %s").format(t=t, c=c, o=org), (b.id,)
        )
        assert cur.rowcount == 0
    if deletable:
        cur = db.execute(sql.SQL("delete from {} where {} = %s").format(t, org), (b.id,))
        assert cur.rowcount == 0
    else:
        refused(
            db, lambda: db.execute(sql.SQL("delete from {} where {} = %s").format(t, org), (b.id,))
        )


@pytest.mark.parametrize("table", ["farmer", "farm", "field", "season", "crop_plan", "soil_test"])
def test_row_cannot_move_to_other_org(
    db: psycopg.Connection, two_orgs: tuple[Org, Org], table: str
) -> None:
    a, b = two_orgs
    refused(
        db,
        lambda: db.execute(
            sql.SQL("update {} set organisation_id = %s where organisation_id = %s").format(
                sql.Identifier(table)
            ),
            (b.id, a.id),
        ),
    )


def test_review_author_cannot_be_forged(db: psycopg.Connection, two_orgs: tuple[Org, Org]) -> None:
    a, _ = two_orgs
    use_context(db, a.staff, a.id)  # staff writes a review in the agronomist's name
    refused(
        db,
        lambda: insert_row(
            db,
            "review",
            {
                "organisation_id": a.id,
                "recommendation_id": a.engine_rec,
                "decision": "reject",
                "reason": "forged",
                "reviewer_id": a.agronomist,
                "minutes_spent": 1,
            },
        ),
    )


def test_cross_org_reference_fails(db: psycopg.Connection, two_orgs: tuple[Org, Org]) -> None:
    a, b = two_orgs
    with pytest.raises(psycopg.Error), db.transaction():
        insert_row(db, "field", {"organisation_id": a.id, "farm_id": b.farm, "name": "x"})


# --- Deny by default --------------------------------------------------------------------


@pytest.mark.parametrize(
    "context",
    ["none", "user_only", "wrong_org", "superadmin_wrong_org"],
)
def test_missing_or_wrong_context_sees_nothing(
    db: psycopg.Connection, two_orgs: tuple[Org, Org], context: str
) -> None:
    a, b = two_orgs
    if context == "none":
        use_context(db, None)
    elif context == "user_only":
        use_context(db, a.agronomist)
    elif context == "wrong_org":
        use_context(db, a.agronomist, b.id)  # valid user, organisation they are not in
    else:
        with as_owner(db):
            db.execute(
                "update app_user set platform_role = 'superadmin' where id = %s", (a.agronomist,)
            )
        use_context(db, a.agronomist, b.id, "superadmin")
    for table in TENANT:
        assert count(db, table) == 0, table


@pytest.mark.parametrize("table", TENANT)
def test_insert_without_context_is_refused(
    db: psycopg.Connection,
    two_orgs: tuple[Org, Org],
    engine_result: dict[str, Any],
    table: str,
) -> None:
    a, _ = two_orgs
    values = TENANT_CASES[table][0](db, a, engine_result)
    use_context(db, None)
    refused(db, lambda: insert_row(db, table, values), table)


def test_garbage_context_raises(db: psycopg.Connection, two_orgs: tuple[Org, Org]) -> None:
    db.execute("select set_config('app.org_id', 'garbage', true)")
    with pytest.raises(errors.InvalidTextRepresentation), db.transaction():
        db.execute("select count(*) from farm")


def test_owner_is_filtered_by_force(db: psycopg.Connection, two_orgs: tuple[Org, Org]) -> None:
    use_context(db, None)
    with as_role(db, "cp_migrator"):
        for table in TENANT:
            assert count(db, table) == 0, table


def test_context_does_not_survive_the_transaction(
    migrated_db: MigratedDb, engine_result: dict[str, Any]
) -> None:
    """T-CTX-2 / T-POOL-4: context set and committed in one transaction is gone in the next."""
    with psycopg.connect(migrated_db.url) as conn:
        conn.execute("set local role cp_app")
        conn.execute("select set_config('app.org_id', %s, true)", (str(uuid4()),))
        conn.commit()
        conn.execute("set local role cp_app")
        row = conn.execute("select current_setting('app.org_id', true)").fetchone()
        assert row == ("",)
        assert conn.execute("select public.app_ctx_org()").fetchone() == (None,)
        conn.rollback()


def test_autocommit_set_config_lasts_one_statement(migrated_db: MigratedDb) -> None:
    """T-POOL-2: in autocommit a transaction-local context ends with its statement."""
    with psycopg.connect(migrated_db.url, autocommit=True) as conn:
        conn.execute("select set_config('app.org_id', %s, true)", (str(uuid4()),))
        assert conn.execute("select current_setting('app.org_id', true)").fetchone() == ("",)


def test_pool_reset_clears_a_session_level_context(migrated_db: MigratedDb) -> None:
    """T-POOL-3 (reset path): a session-level `SET app.*` by mistake is cleared on return."""
    with psycopg.connect(migrated_db.url) as conn:
        conn.execute("select set_config('app.org_id', %s, false)", (str(uuid4()),))
        conn.execute("select set_config('app.user_id', %s, false)", (str(uuid4()),))
        conn.commit()
        reset_connection(conn)
        row = conn.execute(
            "select nullif(current_setting('app.org_id', true), ''),"
            " nullif(current_setting('app.user_id', true), '')"
        ).fetchone()
        assert row == (None, None)


# --- Website role (0022) ----------------------------------------------------------------


def test_website_policies_are_insert_only_to_cp_website(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select tablename, cmd, roles, permissive from pg_policies"
        " where tablename in ('pilot_request', 'site_event') order by tablename"
    ).fetchall()
    assert rows == [
        ("pilot_request", "INSERT", ["cp_website"], "PERMISSIVE"),
        ("site_event", "INSERT", ["cp_website"], "PERMISSIVE"),
    ]


def test_cp_website_reads_and_writes_no_tenant_table(db: psycopg.Connection) -> None:
    with as_role(db, "cp_website"):
        for table in TENANT:
            refused(
                db,
                lambda t=table: db.execute(sql.SQL("select 1 from {}").format(sql.Identifier(t))),
            )


def test_cp_app_reads_no_website_rows(db: psycopg.Connection) -> None:
    for table in sorted(WEBSITE_TABLES):
        refused(
            db, lambda t=table: db.execute(sql.SQL("select 1 from {}").format(sql.Identifier(t)))
        )


# --- Rule 12: AI / service context ------------------------------------------------------


def test_service_context_sees_no_real_farmer_rows(
    db: psycopg.Connection, two_orgs: tuple[Org, Org]
) -> None:
    a, _ = two_orgs
    with as_owner(db):
        service = insert(
            db, "app_user", email="svc-rls@example.org", display_name="Svc", actor_kind="service"
        )
        insert(db, "membership", organisation_id=a.id, user_id=service, role="advisor")
        demo = insert(db, "farmer", organisation_id=a.id, display_name="Demo", record_kind="demo")
    use_context(db, service, a.id)
    for table in ("farmer", "farm", "field", "field_geometry_version"):
        rows = db.execute(
            sql.SQL("select count(*) from {}").format(sql.Identifier(table))
        ).fetchone()
        expected = 1 if table == "farmer" else 0
        assert rows == (expected,), table
    assert db.execute("select id from farmer").fetchone() == (demo,)
    # A human of the same org still sees the real rows.
    use_context(db, a.agronomist, a.id)
    assert count(db, "farmer") == 2
