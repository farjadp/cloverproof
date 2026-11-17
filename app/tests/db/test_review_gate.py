"""Review gate, edits as new versions, the diff view and proof documents."""

from typing import Any

import psycopg
import pytest
from psycopg import errors

from .conftest import Org, as_owner, edited, insert, recommendation_values

pytestmark = pytest.mark.db


def approve(db: psycopg.Connection, org: Org, rec: Any, reviewer: Any, minutes: int = 10) -> Any:
    return insert(
        db,
        "review",
        organisation_id=org.id,
        recommendation_id=rec,
        decision="approve",
        reviewer_id=reviewer,
        minutes_spent=minutes,
    )


def agronomist_edit(
    db: psycopg.Connection, org: Org, result: dict[str, Any], n_rate: float, author: Any = None
) -> Any:
    return insert(
        db,
        "recommendation",
        organisation_id=org.id,
        crop_plan_id=org.crop_plan,
        parent_id=org.engine_rec,
        kind="agronomist",
        reason="Field history suggests a lower rate (test)",
        created_by=author or org.agronomist,
        **recommendation_values(edited(result, n_rate)),
    )


def test_staff_cannot_approve(db: psycopg.Connection, org_a: Org) -> None:
    with pytest.raises(errors.InsufficientPrivilege, match="only an agronomist"), db.transaction():
        approve(db, org_a, org_a.engine_rec, org_a.staff)


def test_agronomist_approves(db: psycopg.Connection, org_a: Org) -> None:
    review = approve(db, org_a, org_a.engine_rec, org_a.agronomist, minutes=7)
    row = db.execute(
        "select decision, reviewer_id, minutes_spent from review where id = %s", (review,)
    ).fetchone()
    assert row == ("approve", org_a.agronomist, 7)


def test_agronomist_of_other_org_cannot_approve(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    with (
        pytest.raises(errors.InsufficientPrivilege, match="not an active member"),
        db.transaction(),
    ):
        approve(db, org_a, org_a.engine_rec, org_b.agronomist)


def test_disabled_agronomist_cannot_approve(db: psycopg.Connection, org_a: Org) -> None:
    with as_owner(db):  # operator setup; cp_app cannot disable approvers (0014)
        db.execute("update app_user set disabled_at = now() where id = %s", (org_a.agronomist,))
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        approve(db, org_a, org_a.engine_rec, org_a.agronomist)


def test_review_organisation_must_match_recommendation(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    # Claiming org B for org A's recommendation breaks the (organisation_id, id) foreign key.
    with pytest.raises(errors.ForeignKeyViolation), db.transaction():
        approve(db, org_b, org_a.engine_rec, org_b.agronomist)


def test_only_one_approval(db: psycopg.Connection, org_a: Org) -> None:
    approve(db, org_a, org_a.engine_rec, org_a.agronomist)
    with pytest.raises(errors.UniqueViolation), db.transaction():
        approve(db, org_a, org_a.engine_rec, org_a.agronomist)


def test_minutes_spent_required_and_non_negative(db: psycopg.Connection, org_a: Org) -> None:
    for minutes in (None, -1):
        with pytest.raises((errors.NotNullViolation, errors.CheckViolation)), db.transaction():
            approve(db, org_a, org_a.engine_rec, org_a.agronomist, minutes=minutes)  # type: ignore[arg-type]


def test_reject_needs_reason(db: psycopg.Connection, org_a: Org) -> None:
    values = {
        "organisation_id": org_a.id,
        "recommendation_id": org_a.engine_rec,
        "decision": "reject",
        "reviewer_id": org_a.agronomist,
        "minutes_spent": 3,
    }
    with pytest.raises(errors.CheckViolation), db.transaction():
        insert(db, "review", **values)
    insert(db, "review", reason="Target yield unrealistic (test)", **values)


def test_edit_creates_new_version_and_diff(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    engine_rate = engine_result["nitrogen"]["rate"]["value"]
    final_rate = engine_rate + 15
    child = agronomist_edit(db, org_a, engine_result, final_rate)
    insert(
        db,
        "review",
        organisation_id=org_a.id,
        recommendation_id=org_a.engine_rec,
        decision="edit",
        reason="Field history suggests a different rate (test)",
        reviewer_id=org_a.agronomist,
        minutes_spent=9,
        resulting_recommendation_id=child,
    )
    approve(db, org_a, child, org_a.agronomist, minutes=2)

    # The engine row is untouched; the edit is a new row pointing at it.
    rows = db.execute(
        "select id, kind, parent_id, n_rate_kg_ha from recommendation"
        " where crop_plan_id = %s order by created_at, kind",
        (org_a.crop_plan,),
    ).fetchall()
    assert [(r[1], r[2]) for r in rows] == [("engine", None), ("agronomist", org_a.engine_rec)]
    assert float(rows[0][3]) == engine_rate

    diff = db.execute(
        """select engine_recommendation_id, final_recommendation_id, edit_depth,
                  engine_n_rate_kg_ha, final_n_rate_kg_ha, n_rate_delta_kg_ha,
                  edit_reason, approved_by, approval_minutes_spent
           from recommendation_diff
           where organisation_id = %s and approved_at is not null""",
        (org_a.id,),
    ).fetchall()
    assert len(diff) == 1
    (engine_id, final_id, depth, engine_n, final_n, delta, reason, approved_by, minutes) = diff[0]
    assert (engine_id, final_id, depth) == (org_a.engine_rec, child, 1)
    assert (float(engine_n), float(final_n), float(delta)) == (engine_rate, final_rate, 15.0)
    assert reason.startswith("Field history")
    assert (approved_by, minutes) == (org_a.agronomist, 2)


def test_edit_review_must_point_at_child(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    # resulting_recommendation_id must be a child of the reviewed recommendation.
    other_root = insert(
        db,
        "recommendation",
        organisation_id=org_a.id,
        crop_plan_id=org_a.crop_plan,
        kind="engine",
        created_by=org_a.staff,
        **recommendation_values(engine_result),
    )
    with pytest.raises(errors.ForeignKeyViolation), db.transaction():
        insert(
            db,
            "review",
            organisation_id=org_a.id,
            recommendation_id=org_a.engine_rec,
            decision="edit",
            reason="test",
            reviewer_id=org_a.agronomist,
            minutes_spent=1,
            resulting_recommendation_id=other_root,
        )


def test_edit_needs_reason(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    with pytest.raises(errors.CheckViolation), db.transaction():
        insert(
            db,
            "recommendation",
            organisation_id=org_a.id,
            crop_plan_id=org_a.crop_plan,
            parent_id=org_a.engine_rec,
            kind="agronomist",
            reason="  ",
            created_by=org_a.agronomist,
            **recommendation_values(edited(engine_result, 1.0)),
        )


def test_staff_cannot_create_agronomist_version(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    with pytest.raises(errors.InsufficientPrivilege, match="only an agronomist"), db.transaction():
        agronomist_edit(db, org_a, engine_result, 1.0, author=org_a.staff)


def test_parent_must_be_same_crop_plan(
    db: psycopg.Connection, org_a: Org, org_b: Org, engine_result: dict[str, Any]
) -> None:
    with pytest.raises(errors.ForeignKeyViolation), db.transaction():
        insert(
            db,
            "recommendation",
            organisation_id=org_a.id,
            crop_plan_id=org_a.crop_plan,
            parent_id=org_b.engine_rec,
            kind="agronomist",
            reason="test",
            created_by=org_a.agronomist,
            **recommendation_values(edited(engine_result, 1.0)),
        )


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("engine_version", "9.9.9"),
        ("pack_sha256", "b" * 64),
        ("confidence", "high"),
        ("inputs_snapshot", {"crop": "other"}),
    ],
)
def test_typed_columns_must_match_result(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any], column: str, value: Any
) -> None:
    values = recommendation_values(engine_result) | {column: value}
    with pytest.raises(errors.CheckViolation), db.transaction():
        insert(
            db,
            "recommendation",
            organisation_id=org_a.id,
            crop_plan_id=org_a.crop_plan,
            kind="engine",
            created_by=org_a.staff,
            **values,
        )


def test_proof_document_requires_approval(db: psycopg.Connection, org_a: Org) -> None:
    sha = "c" * 64
    values = {
        "organisation_id": org_a.id,
        "recommendation_id": org_a.engine_rec,
        "sha256": sha,
        "storage_key": f"proof/{org_a.id}/{org_a.engine_rec}/{sha}.pdf",
        "created_by": org_a.agronomist,
    }
    with pytest.raises(errors.CheckViolation, match="not approved"), db.transaction():
        insert(db, "proof_document", **values)
    approve(db, org_a, org_a.engine_rec, org_a.agronomist)
    insert(db, "proof_document", **values)


def test_proof_document_key_matches_hash(db: psycopg.Connection, org_a: Org) -> None:
    approve(db, org_a, org_a.engine_rec, org_a.agronomist)
    with pytest.raises(errors.CheckViolation), db.transaction():
        insert(
            db,
            "proof_document",
            organisation_id=org_a.id,
            recommendation_id=org_a.engine_rec,
            sha256="d" * 64,
            storage_key=f"proof/{org_a.id}/{org_a.engine_rec}/{'e' * 64}.pdf",
            created_by=org_a.agronomist,
        )


def test_engine_rows_appear_in_diff_with_zero_delta(db: psycopg.Connection, org_a: Org) -> None:
    approve(db, org_a, org_a.engine_rec, org_a.agronomist)
    with as_owner(db):
        row = db.execute(
            "select edit_depth, n_rate_delta_kg_ha from recommendation_diff"
            " where final_recommendation_id = %s",
            (org_a.engine_rec,),
        ).fetchone()
    assert row is not None
    assert (row[0], float(row[1])) == (0, 0.0)
