"""The app writes `recommendation_line` rows with every recommendation version (N only).

Runs through the real routes as cp_app under RLS. Lines are compared with the `result`
document read back from the database: both must always say the same numbers."""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import errors
from psycopg.rows import dict_row

from cloverproof_app import planning
from cloverproof_app.db.migrate import REPO_ROOT
from cloverproof_app.repo import plans

from .conftest import Org, use_context
from .test_plan_flow import create_plan, latest_rec, new_field, plan_form, signed_in
from .test_plan_pack_inputs import ca_on_client, post_plan
from .test_recommendation_line import older_recommendation
from .test_web_auth import build_client, email_of, login, page_csrf, with_password

pytestmark = pytest.mark.db

NO_SPLITS = REPO_ROOT / "packs" / "placeholder" / "v0-no-splits.yaml"
EDIT_TOLERANCE = Decimal("0.05")  # planning.parse_edit: splits must add up to the N rate
NOTHING_SAVED = "nothing was saved"
LAB_SOIL: dict[str, object] = {
    "has_soil": "yes",
    "sample_date": "2026-10-01",
    "depth_top": "0",
    "depth_bottom": "15",
    "source": "lab",
    "lab": "Test Lab",
    "v_form": ["P", "K", ""],
    "v_value": ["12", "150", ""],
    "v_unit": ["mg/kg", "ppm", "mg/kg"],
    "v_method": ["olsen", "other", ""],
    "v_detail": ["", "Ammonium acetate", ""],
}


def plan_id_of(plan_url: str) -> UUID:
    return UUID(plan_url.rsplit("/", 1)[1])


def versions(db: psycopg.Connection, org: Org, plan_id: UUID) -> list[dict[str, Any]]:
    """Versions of a plan, engine first."""
    use_context(db, org.agronomist, org.id)
    with db.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "select id, parent_id, result, confidence::text as confidence, created_by"
            " from recommendation where organisation_id = %s and crop_plan_id = %s"
            " order by parent_id is not null, created_at, id",
            (org.id, plan_id),
        ).fetchall()


def lines_of(db: psycopg.Connection, rec_id: UUID) -> list[dict[str, Any]]:
    with db.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "select nutrient, nutrient_form::text as nutrient_form, rate_kg_ha, no_rate_reason,"
            " split_no, stage_label, timing_window_start, timing_window_end,"
            " timing_basis::text as timing_basis, product_id, explanation, uses_placeholder,"
            " confidence::text as confidence, created_by"
            " from recommendation_line where recommendation_id = %s order by split_no",
            (rec_id,),
        ).fetchall()


def assert_lines_match(lines: list[dict[str, Any]], version: dict[str, Any]) -> None:
    """Same numbers per split, and the sum within the edit tolerance of the N rate."""
    nitrogen = version["result"]["nitrogen"]
    splits = nitrogen["splits"]
    assert len(lines) == len(splits)
    for line, split in zip(lines, splits, strict=True):
        assert line["rate_kg_ha"] == Decimal(str(split["rate"]["value"]))
    total = sum(line["rate_kg_ha"] for line in lines)
    assert abs(total - Decimal(str(nitrogen["rate"]["value"]))) <= EDIT_TOLERANCE


def assert_n_line_columns(line: dict[str, Any], version: dict[str, Any], user: UUID) -> None:
    assert (line["nutrient"], line["nutrient_form"]) == ("N", "N")
    assert line["no_rate_reason"] is None
    # The pack gives wording, not dates or a timing method.
    assert line["timing_window_start"] is None and line["timing_window_end"] is None
    assert line["timing_basis"] is None
    assert line["product_id"] is None
    assert line["confidence"] == version["confidence"] == version["result"]["confidence"]
    assert line["created_by"] == user


def post_edit(client: TestClient, csrf: str, plan_url: str, rate: str, splits: list[str],
              reason: str = "Local trial history"):  # type: ignore[no-untyped-def]  # fmt: skip
    return client.post(
        plan_url + "/edit",
        data={"csrf_token": csrf, "recommendation_id": latest_rec(client, plan_url),
              "n_rate": rate, "split_rate": splits, "reason": reason},
    )  # fmt: skip


def error_page_client(client: TestClient) -> TestClient:
    """Same session, but a server error comes back as the page the user would see."""
    return TestClient(
        client.app,
        base_url="https://testserver",
        follow_redirects=False,
        raise_server_exceptions=False,
        cookies=dict(client.cookies),
    )


def no_splits_client(db: psycopg.Connection, user_id: UUID) -> tuple[TestClient, str]:
    with_password(db, user_id)
    client = build_client(db, pack_path=str(NO_SPLITS))
    assert login(client, email_of(db, user_id)).status_code == 303
    return client, page_csrf(client)


def count(db: psycopg.Connection, query: str, *params: object) -> int:
    row = db.execute(query, params).fetchone()
    assert row is not None
    return row[0]


# --- Engine run --------------------------------------------------------------------------


def test_engine_plan_writes_one_n_line_per_split(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_id = plan_id_of(create_plan(client, csrf, new_field(client, csrf)))

    [version] = versions(db, org_a, plan_id)
    lines = lines_of(db, version["id"])
    splits = version["result"]["nitrogen"]["splits"]

    assert_lines_match(lines, version)
    assert [line["split_no"] for line in lines] == [1, 2]
    for line, split in zip(lines, splits, strict=True):
        assert_n_line_columns(line, version, org_a.agronomist)
        assert line["stage_label"] == split["timing_window"]["label"]
        assert line["explanation"] == split["explanation"]
        assert line["uses_placeholder"] is True


def test_real_pack_plan_writes_its_lines(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = ca_on_client(db, org_a.agronomist)
    r = post_plan(client, csrf, new_field(client, csrf))
    assert r.status_code == 303, r.text

    [version] = versions(db, org_a, plan_id_of(r.headers["location"]))
    lines = lines_of(db, version["id"])

    assert_lines_match(lines, version)
    assert [line["stage_label"] for line in lines] == [
        s["timing_window"]["label"] for s in version["result"]["nitrogen"]["splits"]
    ]


def test_lab_soil_test_still_gives_n_lines_only(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf), **LAB_SOIL)
    assert post_edit(client, csrf, plan_url, "120", ["48", "72"]).status_code == 303

    engine, final = versions(db, org_a, plan_id_of(plan_url))
    for version in (engine, final):
        assert {line["nutrient"] for line in lines_of(db, version["id"])} == {"N"}
        assert version["result"]["phosphorus_potassium"]["text"]  # the note stays in the document
    assert count(
        db,
        "select count(*) from recommendation_line where organisation_id = %s"
        " and nutrient <> 'N'",
        org_a.id,
    ) == 0  # fmt: skip


def test_no_split_pack_gives_one_season_line_without_stage(
    db: psycopg.Connection, org_a: Org
) -> None:
    client, csrf = no_splits_client(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))

    [version] = versions(db, org_a, plan_id_of(plan_url))
    [line] = lines_of(db, version["id"])
    split = version["result"]["nitrogen"]["splits"][0]

    assert_lines_match([line], version)
    assert_n_line_columns(line, version, org_a.agronomist)
    assert line["split_no"] == 0  # 0026: 0 = season total, 1..n = splits
    assert line["stage_label"] is None
    assert line["explanation"] == split["explanation"]

    rate = f"{split['rate']['value'] + 10:g}"
    assert post_edit(client, csrf, plan_url, rate, [rate]).status_code == 303
    _, final = versions(db, org_a, plan_id_of(plan_url))
    [edited] = lines_of(db, final["id"])
    assert_lines_match([edited], final)
    assert (edited["split_no"], edited["stage_label"]) == (0, None)


# --- Agronomist edit ---------------------------------------------------------------------


def test_edit_writes_lines_for_the_new_version_and_keeps_the_parents(
    db: psycopg.Connection, org_a: Org
) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    plan_id = plan_id_of(plan_url)
    [engine] = versions(db, org_a, plan_id)
    before = lines_of(db, engine["id"])

    assert post_edit(client, csrf, plan_url, "120", ["48", "72"]).status_code == 303

    parent, final = versions(db, org_a, plan_id)
    assert parent["id"] == engine["id"] and final["parent_id"] == engine["id"]
    assert lines_of(db, parent["id"]) == before
    lines = lines_of(db, final["id"])
    assert_lines_match(lines, final)
    assert [line["rate_kg_ha"] for line in lines] == [Decimal("48.0"), Decimal("72.0")]
    for line, split in zip(lines, final["result"]["nitrogen"]["splits"], strict=True):
        assert_n_line_columns(line, final, org_a.agronomist)
        assert line["explanation"] == split["explanation"]
        # The rate is the agronomist's now, but the timing wording is still PLACEHOLDER.
        assert split["rate"]["uses_placeholder"] is False
        assert line["uses_placeholder"] is True


def test_rescaled_edit_stores_the_exact_document_rates(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    [engine] = versions(db, org_a, plan_id_of(plan_url))
    unchanged = [f"{s['rate']['value']:g}" for s in engine["result"]["nitrogen"]["splits"]]

    # 101.37 x the pack shares needs more digits than float8 -> numeric keeps.
    assert post_edit(client, csrf, plan_url, "101.37", unchanged).status_code == 303

    _, final = versions(db, org_a, plan_id_of(plan_url))
    assert_lines_match(lines_of(db, final["id"]), final)


def test_splits_inside_the_tolerance_are_stored_as_typed(
    db: psycopg.Connection, org_a: Org
) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))

    assert post_edit(client, csrf, plan_url, "120", ["48.02", "72"]).status_code == 303

    _, final = versions(db, org_a, plan_id_of(plan_url))
    lines = lines_of(db, final["id"])
    assert_lines_match(lines, final)
    assert lines[0]["rate_kg_ha"] == Decimal("48.02")


def test_edit_of_a_document_from_an_older_engine_keeps_working(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    """Engine 0.3.0 documents have no `timing_window` or line `explanation`."""
    old = copy.deepcopy(engine_result)
    for split in old["nitrogen"]["splits"]:
        del split["timing_window"], split["explanation"]
        split["rate"]["uses_placeholder"] = False

    rec_id = plans.insert_recommendation(
        db, org_a.id, crop_plan_id=org_a.crop_plan, result=old, user_id=org_a.agronomist
    )

    lines = lines_of(db, rec_id)
    assert [line["split_no"] for line in lines] == [1, 2]
    for line, split in zip(lines, old["nitrogen"]["splits"], strict=True):
        assert line["stage_label"] == split["stage_label"]
        assert line["explanation"] == split["rate"]["explanation"]
        assert line["uses_placeholder"] is True  # wording with no status is never validated


# --- Access and sealing ------------------------------------------------------------------


def test_other_org_cannot_read_the_lines(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_id = plan_id_of(create_plan(client, csrf, new_field(client, csrf)))
    [version] = versions(db, org_a, plan_id)
    assert db.execute("select current_user").fetchone() == ("cp_app",)
    assert len(lines_of(db, version["id"])) == 2

    use_context(db, org_b.agronomist, org_b.id)
    assert lines_of(db, version["id"]) == []


def test_lines_cannot_be_added_to_a_stored_recommendation(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    older = older_recommendation(db, org_a, engine_result)
    use_context(db, org_a.staff, org_a.id)
    with pytest.raises(errors.ObjectNotInPrerequisiteState, match="sealed"), db.transaction():
        plans.insert_recommendation_lines(
            db, org_a.id, recommendation_id=older, result=engine_result, user_id=org_a.staff
        )
    assert lines_of(db, older) == []


# --- Nothing half-saved ------------------------------------------------------------------


def with_bad_line(document: dict[str, Any]) -> dict[str, Any]:
    """A document the recommendation row accepts but whose second line the DB refuses."""
    bad = copy.deepcopy(document)
    bad["nitrogen"]["splits"][1]["rate"]["value"] = -1.0
    return bad


def test_line_failure_on_a_new_plan_saves_nothing(
    db: psycopg.Connection, org_a: Org, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    field_url = new_field(client, csrf)
    form = client.get(field_url + "/plans/new").text
    started = form.split('name="started" value="')[1].split('"')[0]
    real = planning.run_engine
    monkeypatch.setattr(planning, "run_engine", lambda i, p: with_bad_line(real(i, p)))

    r = error_page_client(client).post(
        field_url + "/plans",
        data=plan_form(**LAB_SOIL) | {"csrf_token": csrf, "started": started},
    )

    assert r.status_code == 500 and NOTHING_SAVED in r.text
    use_context(db, org_a.agronomist, org_a.id)
    field_id = UUID(field_url.rsplit("/", 1)[1])
    assert count(db, "select count(*) from crop_plan where field_id = %s", field_id) == 0
    assert count(db, "select count(*) from soil_test where field_id = %s", field_id) == 0
    assert count(
        db, "select count(*) from recommendation where created_by = %s", org_a.agronomist
    ) == 0  # fmt: skip
    assert count(
        db, "select count(*) from recommendation_line where created_by = %s", org_a.agronomist
    ) == 0  # fmt: skip


def test_line_failure_on_an_edit_saves_nothing(
    db: psycopg.Connection, org_a: Org, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    plan_url = create_plan(client, csrf, new_field(client, csrf))
    plan_id = plan_id_of(plan_url)
    [engine] = versions(db, org_a, plan_id)
    before = lines_of(db, engine["id"])
    real = planning.edited_document
    monkeypatch.setattr(planning, "edited_document", lambda d, e, r: with_bad_line(real(d, e, r)))

    r = post_edit(error_page_client(client), csrf, plan_url, "120", ["48", "72"])

    assert r.status_code == 500 and NOTHING_SAVED in r.text
    assert [v["id"] for v in versions(db, org_a, plan_id)] == [engine["id"]]
    assert lines_of(db, engine["id"]) == before
    assert count(db, "select count(*) from review where recommendation_id = %s", engine["id"]) == 0


def test_document_without_splits_is_refused_and_not_saved(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    empty = copy.deepcopy(engine_result)
    empty["nitrogen"]["splits"] = []
    query = "select count(*) from recommendation where crop_plan_id = %s"
    existing = count(db, query, org_a.crop_plan)

    with pytest.raises(ValueError, match="no N split"):
        plans.insert_recommendation(
            db, org_a.id, crop_plan_id=org_a.crop_plan, result=empty, user_id=org_a.agronomist
        )

    assert count(db, query, org_a.crop_plan) == existing
