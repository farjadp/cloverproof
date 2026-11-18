"""`fertilizer_product` catalog (migration 0027, story S2-DB-19, GL-09, ADR 0008 §5).

A global per-country catalog, not organisation data. Every product here is synthetic: grades
are label facts and real ones need a source a human confirms, so the migration seeds nothing.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import errors, sql

from .conftest import Org, as_owner, as_role, insert, use_context

pytestmark = pytest.mark.db

ORG_ROLES = ("org_admin", "advisor", "agronomist", "farmer")
EXPECTED_COLUMNS = {
    "id",
    "country_code",
    "name",
    "n",
    "p2o5",
    "k2o",
    "s",
    "form",
    "density_kg_per_l",
    "status",
    "grade_source",
    "created_by",
    "created_at",
    "updated_at",
}
FORBIDDEN_COLUMN = re.compile(
    r"price|cost|vendor|supplier|dealer|retailer|affiliate|commission|url|link", re.IGNORECASE
)


@dataclass
class Actors:
    org: Org
    other_org: Org
    roles: dict[str, UUID]
    superadmin: UUID
    service: UUID


@pytest.fixture
def actors(db: psycopg.Connection, org_a: Org, org_b: Org) -> Actors:
    admin = insert(db, "app_user", email="catalog-admin@example.org", display_name="Org admin")
    farmer = insert(db, "app_user", email="catalog-farmer@example.org", display_name="Farmer")
    insert(db, "membership", organisation_id=org_a.id, user_id=admin, role="org_admin")
    insert(db, "membership", organisation_id=org_a.id, user_id=farmer, role="farmer")
    superadmin = insert(db, "app_user", email="catalog-sa@example.org", display_name="Superadmin")
    with as_owner(db):
        db.execute("update app_user set platform_role = 'superadmin' where id = %s", (superadmin,))
        service = insert(
            db,
            "app_user",
            email="catalog-svc@example.org",
            display_name="Service",
            actor_kind="service",
        )
        insert(db, "membership", organisation_id=org_a.id, user_id=service, role="advisor")
    roles = {
        "org_admin": admin,
        "advisor": org_a.staff,
        "agronomist": org_a.agronomist,
        "farmer": farmer,
    }
    use_context(db, None)
    return Actors(org_a, org_b, roles, superadmin, service)


def product(created_by: UUID, **overrides: Any) -> dict[str, Any]:
    return {
        "country_code": "CA",
        "name": f"TEST-GRADE 10-0-0 {uuid4().hex[:8]}",
        "n": 10,
        "p2o5": 0,
        "k2o": 0,
        "s": 0,
        "form": "granular",
        "grade_source": "TEST synthetic label, not a real product",
        "created_by": created_by,
    } | overrides


def add(db: psycopg.Connection, values: dict[str, Any]) -> UUID:
    """Insert as the current role and context."""
    query = sql.SQL("insert into fertilizer_product ({}) values ({}) returning id").format(
        sql.SQL(", ").join(map(sql.Identifier, values)),
        sql.SQL(", ").join(sql.Placeholder() * len(values)),
    )
    row = db.execute(query, list(values.values())).fetchone()
    assert row is not None
    return row[0]


def seed(db: psycopg.Connection, actors: Actors, status: str, **overrides: Any) -> UUID:
    """Operator insert (superuser, bypasses RLS), to set up a row in any status."""
    with as_owner(db):
        return add(db, product(actors.superadmin, status=status, **overrides))


def visible(db: psycopg.Connection) -> set[UUID]:
    return {r[0] for r in db.execute("select id from fertilizer_product").fetchall()}


def rename(db: psycopg.Connection, product_id: UUID) -> int:
    cur = db.execute(
        "update fertilizer_product set name = %s where id = %s",
        (f"TEST-GRADE renamed {uuid4().hex[:8]}", product_id),
    )
    return cur.rowcount


def activate(db: psycopg.Connection, product_id: UUID) -> int:
    cur = db.execute("update fertilizer_product set status = 'active' where id = %s", (product_id,))
    return cur.rowcount


def denied(db: psycopg.Connection, fn: Callable[[], Any]) -> None:
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        fn()


# --- Shape: no commercial columns (GL-09) -------------------------------------------------


def columns(db: psycopg.Connection) -> set[str]:
    rows = db.execute(
        "select column_name from information_schema.columns"
        " where table_schema = 'public' and table_name = 'fertilizer_product'"
    ).fetchall()
    return {r[0] for r in rows}


def test_no_price_vendor_affiliate_url_or_commission_column(db: psycopg.Connection) -> None:
    names = columns(db)
    assert names
    assert [c for c in names if FORBIDDEN_COLUMN.search(c)] == []


def test_column_list_is_pinned(db: psycopg.Connection) -> None:
    """A new column must be added here on purpose (GL-09: facts only)."""
    assert columns(db) == EXPECTED_COLUMNS


def test_migration_seeds_no_products(db: psycopg.Connection) -> None:
    with as_owner(db):
        assert db.execute("select count(*) from fertilizer_product").fetchone() == (0,)


# --- Reads --------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ORG_ROLES)
def test_org_roles_read_active_but_not_drafts(
    db: psycopg.Connection, actors: Actors, role: str
) -> None:
    active = seed(db, actors, "active")
    seed(db, actors, "draft")
    use_context(db, actors.roles[role], actors.org.id)
    assert visible(db) == {active}


def test_catalog_is_shared_across_organisations(db: psycopg.Connection, actors: Actors) -> None:
    active = seed(db, actors, "active")
    use_context(db, actors.org.agronomist, actors.org.id)
    assert visible(db) == {active}
    use_context(db, actors.other_org.agronomist, actors.other_org.id)
    assert visible(db) == {active}


def test_signed_in_context_needs_no_organisation(db: psycopg.Connection, actors: Actors) -> None:
    active = seed(db, actors, "active")
    use_context(db, actors.org.agronomist)
    assert visible(db) == {active}


def test_superadmin_reads_drafts_without_an_organisation(
    db: psycopg.Connection, actors: Actors
) -> None:
    active = seed(db, actors, "active")
    draft = seed(db, actors, "draft")
    use_context(db, actors.superadmin, None, "superadmin")
    assert visible(db) == {active, draft}


def test_service_context_reads_active_only(db: psycopg.Connection, actors: Actors) -> None:
    active = seed(db, actors, "active")
    seed(db, actors, "draft")
    use_context(db, actors.service, actors.org.id)
    assert visible(db) == {active}


@pytest.mark.parametrize("context", ["none", "org_only", "unknown_user", "disabled_user"])
def test_no_valid_context_sees_nothing(
    db: psycopg.Connection, actors: Actors, context: str
) -> None:
    seed(db, actors, "active")
    seed(db, actors, "draft")
    if context == "none":
        use_context(db, None)
    elif context == "org_only":
        use_context(db, None, actors.org.id)
    elif context == "unknown_user":
        use_context(db, uuid4())
    else:
        with as_owner(db):
            db.execute(
                "update app_user set disabled_at = now() where id = %s",
                (actors.org.agronomist,),
            )
        use_context(db, actors.org.agronomist, actors.org.id)
    assert visible(db) == set()


def test_owner_is_filtered_by_force(db: psycopg.Connection, actors: Actors) -> None:
    seed(db, actors, "active")
    with as_role(db, "cp_migrator"):
        assert visible(db) == set()


# --- Writes: superadmin -------------------------------------------------------------------


def test_superadmin_adds_edits_and_activates_a_draft(
    db: psycopg.Connection, actors: Actors
) -> None:
    use_context(db, actors.superadmin, None, "superadmin")
    new = add(db, product(actors.superadmin))
    row = db.execute("select status from fertilizer_product where id = %s", (new,)).fetchone()
    assert row == ("draft",)
    assert rename(db, new) == 1
    assert activate(db, new) == 1
    row = db.execute("select status from fertilizer_product where id = %s", (new,)).fetchone()
    assert row == ("active",)


def test_insert_cannot_skip_the_draft_step(db: psycopg.Connection, actors: Actors) -> None:
    use_context(db, actors.superadmin, None, "superadmin")
    denied(db, lambda: add(db, product(actors.superadmin, status="active")))


def test_active_product_is_frozen(db: psycopg.Connection, actors: Actors) -> None:
    active = seed(db, actors, "active")
    use_context(db, actors.superadmin, None, "superadmin")
    assert rename(db, active) == 0


def test_superadmin_cannot_forge_the_author(db: psycopg.Connection, actors: Actors) -> None:
    use_context(db, actors.superadmin, None, "superadmin")
    denied(db, lambda: add(db, product(actors.org.agronomist)))


def test_author_and_timestamps_are_not_writable(db: psycopg.Connection, actors: Actors) -> None:
    draft = seed(db, actors, "draft")
    use_context(db, actors.superadmin, None, "superadmin")
    for assignment in ("created_by = created_by", "created_at = now()", "updated_at = now()"):
        denied(
            db,
            lambda a=assignment: db.execute(
                sql.SQL("update fertilizer_product set {} where id = %s").format(sql.SQL(a)),
                (draft,),
            ),
        )


def test_update_refreshes_updated_at(db: psycopg.Connection, actors: Actors) -> None:
    draft = seed(db, actors, "draft")
    with as_owner(db):
        db.execute(
            "update fertilizer_product set created_at = now() - interval '1 day' where id = %s",
            (draft,),
        )
        db.execute("alter table fertilizer_product disable trigger user")
        db.execute("update fertilizer_product set updated_at = created_at where id = %s", (draft,))
        db.execute("alter table fertilizer_product enable trigger user")
    use_context(db, actors.superadmin, None, "superadmin")
    assert rename(db, draft) == 1
    row = db.execute(
        "select updated_at > created_at from fertilizer_product where id = %s", (draft,)
    ).fetchone()
    assert row == (True,)


@pytest.mark.parametrize("role", [None, "cp_admin"])
def test_nobody_can_delete(db: psycopg.Connection, actors: Actors, role: str | None) -> None:
    draft = seed(db, actors, "draft")
    use_context(db, actors.superadmin, None, "superadmin")

    def delete() -> None:
        db.execute("delete from fertilizer_product where id = %s", (draft,))

    if role is None:
        denied(db, delete)
    else:
        with as_role(db, role):
            denied(db, delete)


# --- Writes: denied -----------------------------------------------------------------------


@pytest.mark.parametrize("role", ORG_ROLES)
@pytest.mark.parametrize("claims_superadmin", [False, True])
def test_org_roles_cannot_write(
    db: psycopg.Connection, actors: Actors, role: str, claims_superadmin: bool
) -> None:
    """A forged app.platform_role does not help: it must equal the user's column."""
    draft = seed(db, actors, "draft")
    active = seed(db, actors, "active")
    user = actors.roles[role]
    use_context(db, user, actors.org.id, "superadmin" if claims_superadmin else None)
    denied(db, lambda: add(db, product(user)))
    assert rename(db, draft) == 0
    assert activate(db, draft) == 0
    assert rename(db, active) == 0


def test_service_context_cannot_write(db: psycopg.Connection, actors: Actors) -> None:
    draft = seed(db, actors, "draft")
    use_context(db, actors.service, actors.org.id, "superadmin")
    denied(db, lambda: add(db, product(actors.service)))
    assert rename(db, draft) == 0


def test_disabled_superadmin_cannot_write(db: psycopg.Connection, actors: Actors) -> None:
    draft = seed(db, actors, "draft")
    with as_owner(db):
        db.execute("update app_user set disabled_at = now() where id = %s", (actors.superadmin,))
    use_context(db, actors.superadmin, None, "superadmin")
    denied(db, lambda: add(db, product(actors.superadmin)))
    assert rename(db, draft) == 0


def test_no_context_cannot_write(db: psycopg.Connection, actors: Actors) -> None:
    draft = seed(db, actors, "draft")
    use_context(db, None)
    denied(db, lambda: add(db, product(actors.superadmin)))
    assert rename(db, draft) == 0


# --- Writes: cp_admin (CLI) ---------------------------------------------------------------


def test_cli_adds_and_activates_without_a_web_context(
    db: psycopg.Connection, actors: Actors
) -> None:
    use_context(db, None)
    with as_role(db, "cp_admin"):
        new = add(db, product(actors.superadmin))
        assert new in visible(db)
        assert rename(db, new) == 1
        assert activate(db, new) == 1
        assert rename(db, new) == 0  # active is frozen for the CLI too
        denied(db, lambda: add(db, product(actors.superadmin, status="active")))


def test_cli_author_must_be_an_enabled_human(db: psycopg.Connection, actors: Actors) -> None:
    use_context(db, None)
    with as_role(db, "cp_admin"):
        denied(db, lambda: add(db, product(actors.service)))


def test_cli_with_a_context_cannot_name_another_author(
    db: psycopg.Connection, actors: Actors
) -> None:
    use_context(db, actors.org.agronomist, actors.org.id)
    with as_role(db, "cp_admin"):
        denied(db, lambda: add(db, product(actors.superadmin)))


def test_cli_with_a_service_context_is_denied(db: psycopg.Connection, actors: Actors) -> None:
    draft = seed(db, actors, "draft")
    use_context(db, actors.service, actors.org.id)
    with as_role(db, "cp_admin"):
        denied(db, lambda: add(db, product(actors.superadmin)))
        assert rename(db, draft) == 0
        assert draft not in visible(db)


# --- Website roles ------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["cp_website", "cp_website_admin"])
def test_website_roles_have_no_access(db: psycopg.Connection, actors: Actors, role: str) -> None:
    for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        row = db.execute(
            "select has_table_privilege(%s, 'fertilizer_product', %s)", (role, privilege)
        ).fetchone()
        assert row == (False,), privilege
    use_context(db, actors.superadmin, None, "superadmin")
    with as_role(db, role):
        denied(db, lambda: db.execute("select 1 from fertilizer_product"))
        denied(db, lambda: add(db, product(actors.superadmin)))


# --- Check constraints --------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"country_code": "ca"},
        {"country_code": "C1"},
        {"country_code": "C"},
        {"name": ""},
        {"name": " TEST-GRADE padded"},
        {"n": -1},
        {"p2o5": 100.01},
        {"k2o": -0.01},
        {"s": 101},
        {"n": 50, "p2o5": 30, "k2o": 20, "s": 0.01},
        {"form": "powder"},
        {"status": "retired"},
        {"grade_source": ""},
        {"grade_source": "   "},
        {"form": "liquid"},
        {"form": "liquid", "density_kg_per_l": 0},
        {"form": "liquid", "density_kg_per_l": -1.2},
        {"form": "granular", "density_kg_per_l": 1.2},
    ],
    ids=str,
)
def test_check_constraints_refuse(
    db: psycopg.Connection, actors: Actors, overrides: dict[str, Any]
) -> None:
    with as_owner(db), pytest.raises(errors.CheckViolation), db.transaction():
        add(db, product(actors.superadmin, **overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        {"n": 100},
        {"n": 25, "p2o5": 25, "k2o": 25, "s": 25},
        {"form": "liquid", "density_kg_per_l": 1.28},
    ],
    ids=str,
)
def test_check_constraints_accept(
    db: psycopg.Connection, actors: Actors, overrides: dict[str, Any]
) -> None:
    with as_owner(db):
        add(db, product(actors.superadmin, **overrides))


def test_grade_source_is_required(db: psycopg.Connection, actors: Actors) -> None:
    values = product(actors.superadmin)
    del values["grade_source"]
    with as_owner(db), pytest.raises(errors.NotNullViolation), db.transaction():
        add(db, values)


# --- Uniqueness ---------------------------------------------------------------------------


def test_active_name_is_unique_per_country_ignoring_case(
    db: psycopg.Connection, actors: Actors
) -> None:
    seed(db, actors, "active", name="TEST-GRADE 10-0-0")
    with pytest.raises(errors.UniqueViolation), db.transaction():
        seed(db, actors, "active", name="test-grade 10-0-0")


def test_same_name_is_allowed_in_another_country_or_as_draft(
    db: psycopg.Connection, actors: Actors
) -> None:
    seed(db, actors, "active", name="TEST-GRADE 10-0-0")
    seed(db, actors, "active", name="TEST-GRADE 10-0-0", country_code="US")
    seed(db, actors, "draft", name="TEST-GRADE 10-0-0")
    seed(db, actors, "draft", name="test-grade 10-0-0")


def test_activating_a_duplicate_fails(db: psycopg.Connection, actors: Actors) -> None:
    seed(db, actors, "active", name="TEST-GRADE 10-0-0")
    draft = seed(db, actors, "draft", name="TEST-GRADE 10-0-0")
    use_context(db, actors.superadmin, None, "superadmin")
    with pytest.raises(errors.UniqueViolation), db.transaction():
        activate(db, draft)
