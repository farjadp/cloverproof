"""Migration 0026: recommendation_line (S2-DB-09). The generic RLS allow/deny matrix for this
table runs from TENANT_CASES in test_rls.py and the immutability matrix from
test_immutability.py; this file covers what is specific to lines."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import errors

from .conftest import Org, as_owner, insert, recommendation_values, use_context

pytestmark = pytest.mark.db

INSERT_LINE = (
    "insert into recommendation_line (organisation_id, recommendation_id, nutrient,"
    " nutrient_form, rate_kg_ha, explanation, uses_placeholder, confidence, created_by)"
    " values (%s, %s, 'N', 'N', 1, 'x', true, 'low', %s)"
)


def line(org: Org, **overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "organisation_id": org.id,
        "recommendation_id": org.engine_rec,
        "nutrient": "N",
        "nutrient_form": "N",
        "rate_kg_ha": 100,
        "explanation": "Synthetic line",
        "uses_placeholder": True,
        "confidence": "low",
        "created_by": org.staff,
    }
    return values | overrides


def refused(db: psycopg.Connection, expected: Any, values: dict[str, Any]) -> None:
    with pytest.raises(expected), db.transaction():
        insert(db, "recommendation_line", **values)


def test_columns_match_the_story(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select column_name, is_nullable, udt_name from information_schema.columns"
        " where table_schema = 'public' and table_name = 'recommendation_line'"
    ).fetchall()
    columns = {name: (nullable, kind) for name, nullable, kind in rows}
    assert columns["recommendation_id"] == ("NO", "uuid")
    assert columns["nutrient"] == ("NO", "text")
    assert columns["nutrient_form"] == ("NO", "nutrient_form")
    assert columns["rate_kg_ha"] == ("YES", "numeric")
    assert columns["product_id"] == ("YES", "uuid")
    assert columns["split_no"] == ("NO", "int2")
    assert columns["timing_window_start"] == ("YES", "date")
    assert columns["timing_window_end"] == ("YES", "date")
    assert columns["timing_basis"] == ("YES", "timing_basis")
    assert columns["explanation"] == ("NO", "text")
    assert columns["confidence"] == ("NO", "confidence_level")
    assert not {"unit", "rate_unit"} & set(columns)  # always kg/ha of nutrient_form


def test_product_id_has_no_foreign_key_yet(db: psycopg.Connection) -> None:
    row = db.execute(
        "select count(*) from pg_constraint c join pg_attribute a"
        " on a.attrelid = c.conrelid and a.attnum = any(c.conkey)"
        " where c.conrelid = 'recommendation_line'::regclass and c.contype = 'f'"
        " and a.attname = 'product_id'"
    ).fetchone()
    assert row == (0,)


def test_no_p_or_k_rate_columns_on_recommendation(db: psycopg.Connection) -> None:
    row = db.execute(
        "select count(*) from information_schema.columns where table_name = 'recommendation'"
        " and column_name in ('p_rate_kg_ha', 'k_rate_kg_ha')"
    ).fetchone()
    assert row == (0,)


@pytest.mark.parametrize(
    ("nutrient", "form"), [("N", "N"), ("P", "P"), ("P", "P2O5"), ("K", "K"), ("K", "K2O")]
)
def test_valid_nutrient_and_form_are_stored_unconverted(
    db: psycopg.Connection, org_a: Org, nutrient: str, form: str
) -> None:
    row_id = insert(
        db,
        "recommendation_line",
        **line(org_a, nutrient=nutrient, nutrient_form=form, rate_kg_ha=42.5),
    )
    row = db.execute(
        "select nutrient, nutrient_form::text, rate_kg_ha::text from recommendation_line"
        " where id = %s",
        (row_id,),
    ).fetchone()
    assert row == (nutrient, form, "42.5")


@pytest.mark.parametrize("nutrient", ["P", "K"])
def test_p_or_k_without_form_is_refused(db: psycopg.Connection, org_a: Org, nutrient: str) -> None:
    values = line(org_a, nutrient=nutrient)
    del values["nutrient_form"]
    refused(db, errors.NotNullViolation, values)


@pytest.mark.parametrize(
    ("nutrient", "form"),
    [("N", "NO3-N"), ("N", "P"), ("P", "K2O"), ("P", "N"), ("K", "P2O5"), ("K", "NO3-N")],
)
def test_form_of_another_nutrient_is_refused(
    db: psycopg.Connection, org_a: Org, nutrient: str, form: str
) -> None:
    refused(db, errors.CheckViolation, line(org_a, nutrient=nutrient, nutrient_form=form))


@pytest.mark.parametrize("rate", ["-1", "NaN", "Infinity"])
def test_rate_must_be_finite_and_not_negative(
    db: psycopg.Connection, org_a: Org, rate: str
) -> None:
    refused(db, errors.CheckViolation, line(org_a, rate_kg_ha=rate))


def test_missing_rate_needs_a_reason_and_a_rate_excludes_one(
    db: psycopg.Connection, org_a: Org
) -> None:
    insert(
        db,
        "recommendation_line",
        **line(
            org_a,
            nutrient="P",
            nutrient_form="P2O5",
            rate_kg_ha=None,
            no_rate_reason="soil_test_required",
        ),
    )
    no_reason = line(org_a, nutrient="K", nutrient_form="K2O", rate_kg_ha=None)
    refused(db, errors.CheckViolation, no_reason)
    refused(db, errors.CheckViolation, line(org_a, split_no=1, no_rate_reason="not needed"))


def test_splits_are_separate_lines_and_unique(db: psycopg.Connection, org_a: Org) -> None:
    insert(db, "recommendation_line", **line(org_a))  # season total
    insert(db, "recommendation_line", **line(org_a, split_no=1, stage_label="Tillering"))
    refused(db, errors.UniqueViolation, line(org_a, split_no=1))
    refused(db, errors.CheckViolation, line(org_a, split_no=-1))


def test_timing_window_rules(db: psycopg.Connection, org_a: Org) -> None:
    start, end = date(2027, 4, 1), date(2027, 4, 20)
    insert(
        db,
        "recommendation_line",
        **line(org_a, timing_window_start=start, timing_window_end=end, timing_basis="calendar"),
    )
    bad: list[dict[str, Any]] = [
        {"split_no": 1, "timing_window_start": start, "timing_basis": "manual"},
        {
            "split_no": 2,
            "timing_window_start": end,
            "timing_window_end": start,
            "timing_basis": "gdd",
        },
        {"split_no": 3, "timing_window_start": start, "timing_window_end": end},
    ]
    for extra in bad:
        refused(db, errors.CheckViolation, line(org_a, **extra))
    refused(db, errors.InvalidTextRepresentation, line(org_a, split_no=4, timing_basis="moon"))


def test_confidence_is_the_enum(db: psycopg.Connection, org_a: Org) -> None:
    refused(db, errors.InvalidTextRepresentation, line(org_a, confidence="certain"))


# --- Allowed / denied between two users of different organisations -----------------------


def test_member_reads_lines_and_other_org_user_reads_none(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    row_id = insert(db, "recommendation_line", **line(org_a))
    query = "select count(*) from recommendation_line where id = %s"
    use_context(db, org_a.agronomist, org_a.id)
    assert db.execute(query, (row_id,)).fetchone() == (1,)
    use_context(db, org_b.agronomist, org_b.id)
    assert db.execute(query, (row_id,)).fetchone() == (0,)


def test_other_org_user_cannot_add_a_line_to_this_org(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    use_context(db, org_b.staff, org_b.id)
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(INSERT_LINE, (org_a.id, org_a.engine_rec, org_b.staff))


def test_recommendation_of_another_org_cannot_be_referenced(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    refused(db, errors.InsufficientPrivilege, line(org_a, recommendation_id=org_b.engine_rec))


def test_author_is_bound_to_the_context_user(db: psycopg.Connection, org_a: Org) -> None:
    use_context(db, org_a.agronomist, org_a.id)  # writes in the staff user's name
    with pytest.raises(errors.InsufficientPrivilege, match="row-level security"), db.transaction():
        db.execute(INSERT_LINE, (org_a.id, org_a.engine_rec, org_a.staff))


def test_line_author_must_be_the_recommendation_author(db: psycopg.Connection, org_a: Org) -> None:
    refused(db, errors.InsufficientPrivilege, line(org_a, created_by=org_a.agronomist))


# --- A stored recommendation cannot gain numbers later -----------------------------------


def older_recommendation(db: psycopg.Connection, org: Org, result: dict[str, Any]) -> UUID:
    """A recommendation created by an earlier transaction."""
    row = db.execute("select transaction_timestamp() - interval '1 hour'").fetchone()
    assert row is not None
    return insert(
        db,
        "recommendation",
        organisation_id=org.id,
        crop_plan_id=org.crop_plan,
        kind="engine",
        created_by=org.staff,
        created_at=row[0],
        **recommendation_values(result),
    )


def test_line_cannot_be_added_to_an_earlier_recommendation(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    older = older_recommendation(db, org_a, engine_result)
    with pytest.raises(errors.ObjectNotInPrerequisiteState, match="sealed"), db.transaction():
        insert(db, "recommendation_line", **line(org_a, recommendation_id=older))
    # The operator is held to the same rule.
    with pytest.raises(errors.ObjectNotInPrerequisiteState, match="sealed"), as_owner(db):
        db.execute(INSERT_LINE, (org_a.id, older, org_a.staff))
