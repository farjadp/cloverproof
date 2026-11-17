"""site_event: first-party website events (migration 0013, ADR 0010).

- cp_website inserts whitelisted events only: no SELECT, so no RETURNING; id and
  occurred_at come from defaults (server time).
- CHECK constraints refuse unknown events, locales outside en/fr/es/it/tr, oversized or
  query-carrying paths, full referrer URLs, and extras on the wrong event.
- No column can hold an IP, country, email or user agent.
- cp_app has no privilege on the table.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest
from psycopg import errors

from .conftest import as_owner, as_role

pytestmark = pytest.mark.db

DENIED = "permission denied"

COLUMNS = (
    "view_id, event, locale, path, utm_source, utm_medium, utm_campaign, utm_content,"
    " referrer_host, device, question, answer, step, result_type, gaps, cta_location,"
    " form_step, check_scope, error_reason, is_test"
)


def event_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "view_id": "6f1c1f5e-7d9a-4b52-9a57-3c0d2f1e4b11",
        "event": "page_view",
        "locale": "en",
        "path": "/en",
        "utm_source": "coop",
        "utm_medium": "partner",
        "utm_campaign": "pilot-2027-wheat",
        "utm_content": "coop-012-newsletter",
        "referrer_host": "www.example.com",
        "device": "mobile",
        "question": None,
        "answer": None,
        "step": None,
        "result_type": None,
        "gaps": None,
        "cta_location": None,
        "form_step": None,
        "check_scope": None,
        "error_reason": None,
        "is_test": True,
    }
    row.update(overrides)
    return row


INSERT = (
    f"insert into site_event ({COLUMNS}) values ("
    "%(view_id)s, %(event)s, %(locale)s, %(path)s, %(utm_source)s, %(utm_medium)s,"
    " %(utm_campaign)s, %(utm_content)s, %(referrer_host)s, %(device)s, %(question)s,"
    " %(answer)s, %(step)s, %(result_type)s, %(gaps)s, %(cta_location)s, %(form_step)s,"
    " %(check_scope)s, %(error_reason)s, %(is_test)s)"
)


def refused(db: psycopg.Connection, query: str, params: Any = None) -> None:
    with pytest.raises(errors.InsufficientPrivilege, match=DENIED), db.transaction():
        db.execute(query, params)


def rejected(db: psycopg.Connection, params: dict[str, Any]) -> None:
    with pytest.raises(errors.CheckViolation), db.transaction():
        db.execute(INSERT, params)


def count_events(db: psycopg.Connection) -> int:
    with as_owner(db):
        row = db.execute("select count(*) from site_event").fetchone()
    assert row is not None
    return int(row[0])


# ---------------------------------------------------------------- cp_website


VALID_EVENTS = [
    event_row(),
    event_row(event="page_view", locale="tr", path="/tr/privacy", view_id=None),
    event_row(
        event="check_view",
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        utm_content=None,
        referrer_host=None,
        device=None,
    ),
    event_row(event="check_start", locale="fr"),
    event_row(event="check_answer", question="soilTest", answer="unsure", step=0),
    event_row(event="check_back", step=2),
    event_row(event="check_result", result_type="nOnly", gaps=4),
    event_row(event="check_restart", result_type="full"),
    event_row(event="check_cta_click", result_type="confirm"),
    event_row(event="cta_click", cta_location="hero_chip", locale="es"),
    event_row(event="form_step", form_step=1, locale="it"),
    event_row(event="form_back", form_step=3),
    event_row(event="form_submit_success", check_scope="full"),
    event_row(event="form_submit_success", check_scope=None, view_id=None),
    event_row(event="form_submit_error", error_reason="notConnected"),
]


@pytest.mark.parametrize("params", VALID_EVENTS, ids=[p["event"] for p in VALID_EVENTS])
def test_cp_website_inserts_valid_event(db: psycopg.Connection, params: dict[str, Any]) -> None:
    before = count_events(db)
    with as_role(db, "cp_website"):
        db.execute(INSERT, params)
    assert count_events(db) == before + 1


def test_server_sets_id_and_time(db: psycopg.Connection) -> None:
    with as_role(db, "cp_website"):
        db.execute(INSERT, event_row(view_id="00000000-0000-4000-8000-000000000001"))
        refused(
            db,
            "insert into site_event (event, locale, path, occurred_at)"
            " values ('page_view', 'en', '/en', now() - interval '1 year')",
        )
        refused(
            db,
            "insert into site_event (id, event, locale, path)"
            " values (gen_random_uuid(), 'page_view', 'en', '/en')",
        )
    with as_owner(db):
        row = db.execute(
            "select id is not null, occurred_at = now() from site_event"
            " where view_id = '00000000-0000-4000-8000-000000000001'"
        ).fetchone()
    assert row == (True, True)


def test_cp_website_cannot_read_or_change(db: psycopg.Connection) -> None:
    with as_role(db, "cp_website"):
        refused(db, "select count(*) from site_event")
        refused(db, INSERT + " returning id", event_row())
        refused(db, "update site_event set is_test = true")
        refused(db, "delete from site_event")
        refused(db, "truncate site_event")


@pytest.mark.parametrize(
    "params",
    [
        event_row(event="email_captured"),
        event_row(event="PAGE_VIEW"),
        event_row(event=""),
        event_row(locale="fi"),
        event_row(locale="bg"),
        event_row(locale="ar"),
        event_row(locale="de"),
        event_row(locale="EN"),
        event_row(path="/en/" + "a" * 200),
        event_row(path="/en?utm_source=coop"),
        event_row(path="/en#check"),
        event_row(path="https://example.com/en"),
        event_row(path=""),
        event_row(utm_source="c" * 101),
        event_row(utm_content="Jane Doe"),
        event_row(utm_content="jane@example.org"),
        event_row(utm_source="Coop"),
        event_row(referrer_host="https://www.example.com/path?q=1"),
        event_row(referrer_host="www.example.com/path"),
        event_row(referrer_host="www.example.com:8080"),
        event_row(referrer_host="203.0.113.7"),
        event_row(referrer_host="h" * 254),
        event_row(device="tablet"),
        event_row(device="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"),
        # extras outside their event, or out of range
        event_row(event="page_view", question="soilTest"),
        event_row(event="check_answer", question="email", answer="yes", step=0),
        event_row(event="check_answer", question="soilTest", answer="42 ha", step=0),
        event_row(event="check_answer", question="soilTest", answer="yes", step=4),
        event_row(event="check_answer", question=None, answer="yes", step=0),
        event_row(event="check_result", result_type="partial", gaps=1),
        event_row(event="check_result", result_type="full", gaps=5),
        event_row(event="check_result", result_type=None, gaps=None),
        event_row(event="cta_click", cta_location="footer"),
        event_row(event="cta_click", cta_location=None),
        event_row(event="form_step", form_step=4),
        event_row(event="form_step", form_step=None),
        event_row(event="form_submit_success", check_scope="unknown"),
        event_row(event="form_submit_error", error_reason="smtp down"),
        event_row(event="form_submit_error", error_reason=None),
        event_row(event="page_view", error_reason="invalid"),
    ],
)
def test_check_constraints_reject_bad_events(
    db: psycopg.Connection, params: dict[str, Any]
) -> None:
    with as_role(db, "cp_website"):
        rejected(db, params)


def test_no_pii_columns(db: psycopg.Connection) -> None:
    # information_schema only shows columns the current role can use: read as the owner.
    with as_owner(db):
        rows = db.execute(
            "select column_name from information_schema.columns"
            " where table_schema = 'public' and table_name = 'site_event' order by 1"
        ).fetchall()
    columns = {r[0] for r in rows}
    assert columns == {
        "id", "occurred_at", "view_id", "event", "locale", "path", "utm_source", "utm_medium",
        "utm_campaign", "utm_content", "referrer_host", "device", "question", "answer", "step",
        "result_type", "gaps", "cta_location", "form_step", "check_scope", "error_reason",
        "is_test",
    }  # fmt: skip
    forbidden = ("ip", "addr", "country", "email", "user_agent", "ua", "name", "referrer_url",
                 "pilot_request", "notes", "city", "lat", "lon")  # fmt: skip
    for column in columns:
        for word in forbidden:
            assert word not in column.split("_"), column
    assert not {"ip", "ip_address", "country", "email", "user_agent", "referrer"} & columns


# ---------------------------------------------------------------- grants


def test_grants_and_owner(db: psycopg.Connection) -> None:
    owner = db.execute(
        "select tableowner from pg_tables where schemaname = 'public' and tablename = 'site_event'"
    ).fetchone()
    assert owner == ("cp_migrator",)
    with as_owner(db):  # information_schema hides grants the current role is not part of
        table_grants = db.execute(
            "select grantee, privilege_type from information_schema.table_privileges"
            " where table_name = 'site_event' and grantee <> 'cp_migrator' order by 1, 2"
        ).fetchall()
        rows = db.execute(
            "select grantee, privilege_type, column_name from information_schema.column_privileges"
            " where table_name = 'site_event' and grantee <> 'cp_migrator' order by 1, 2, 3"
        ).fetchall()
    assert table_grants == []  # cp_website has column-level INSERT only
    assert {(g, p) for g, p, _ in rows} == {("cp_website", "INSERT")}
    assert {c for _, _, c in rows} == {c.strip() for c in COLUMNS.split(",")}
    for role in ("cp_app", "cp_admin", "cp_website"):
        for privilege in ("SELECT", "UPDATE", "DELETE", "TRUNCATE"):
            sql = "select has_table_privilege(%s, 'site_event', %s)"
            assert db.execute(sql, (role, privilege)).fetchone() == (False,), (role, privilege)
    for role in ("cp_app", "cp_admin"):
        sql = "select has_any_column_privilege(%s, 'site_event', 'INSERT')"
        assert db.execute(sql, (role,)).fetchone() == (False,), role


@pytest.mark.parametrize("role", ["cp_app", "cp_admin"])
def test_app_roles_cannot_insert_or_read(db: psycopg.Connection, role: str) -> None:
    with as_role(db, role):
        refused(db, INSERT, event_row())
        refused(db, "select count(*) from site_event")
