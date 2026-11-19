"""Optional field location (migration 0032): database rules as cp_app with RLS, the create and
edit forms, and the privacy rule that coordinates stay out of plans, proofs and logs.

All coordinates here are made up.
"""

from __future__ import annotations

import json
import logging
import re
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import errors

from cloverproof_app import field_location as fl
from cloverproof_app.repo import farms

from .conftest import Org, use_context
from .test_actor_kind import make_service
from .test_plan_flow import create_plan, new_field, signed_in
from .test_proof_flow import FakeRender, client_for, fake, generate, review  # noqa: F401

pytestmark = pytest.mark.db

LAT, LON = "12.34567", "-76.54321"
LAT_MARK, LON_MARK = "12.345", "76.543"


def stored(db: psycopg.Connection, field_id: object) -> tuple[Any, Any]:
    row = db.execute(
        "select location_lat, location_lon from field where id = %s", (field_id,)
    ).fetchone()
    assert row is not None
    return row[0], row[1]


def set_point(db: psycopg.Connection, field_id: UUID, lat: object, lon: object) -> int:
    cur = db.execute(
        "update field set location_lat = %s::numeric, location_lon = %s::numeric where id = %s",
        (lat, lon, field_id),
    )
    return cur.rowcount


def field_id_of(url: str) -> UUID:
    return UUID(url.rsplit("/", 1)[1])


def farmer_form(client: TestClient, csrf: str) -> tuple[str, dict[str, str]]:
    r = client.post("/farmers", data={"display_name": "Test Farmer", "csrf_token": csrf})
    url = r.headers["location"]
    client.post(url + "/farms", data={"farm_name": "Home", "csrf_token": csrf})
    farm_id = re.search(r'<option value="([0-9a-f-]{36})"', client.get(url).text).group(1)  # type: ignore[union-attr]
    return url + "/fields", {
        "farm_id": farm_id,
        "field_name": "North 40",
        "area_ha": "12.5",
        "csrf_token": csrf,
    }


def field_count(db: psycopg.Connection, org: Org) -> int:
    row = db.execute("select count(*) from field where organisation_id = %s", (org.id,)).fetchone()
    assert row is not None
    return row[0]


# --- database, as cp_app with RLS ----------------------------------------------------------


def test_existing_fields_have_no_location(db: psycopg.Connection, org_a: Org) -> None:
    assert stored(db, org_a.fields[0]) == (None, None)


def test_own_org_can_set_and_clear(db: psycopg.Connection, org_a: Org) -> None:
    assert set_point(db, org_a.fields[0], LAT, LON) == 1
    assert stored(db, org_a.fields[0]) == (Decimal(LAT), Decimal(LON))
    assert set_point(db, org_a.fields[0], None, None) == 1
    assert stored(db, org_a.fields[0]) == (None, None)


def test_other_org_cannot_read_or_write(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    use_context(db, org_a.agronomist, org_a.id)
    assert set_point(db, org_a.fields[0], LAT, LON) == 1
    use_context(db, org_b.agronomist, org_b.id)
    assert db.execute(
        "select location_lat from field where id = %s", (org_a.fields[0],)
    ).fetchall() == []  # fmt: skip
    assert set_point(db, org_a.fields[0], "1", "-1") == 0
    assert farms.get_field_location(db, org_a.id, org_a.fields[0]) is None
    assert farms.set_field_location(db, org_b.id, org_a.fields[0], None) is False
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(
            "insert into field (organisation_id, farm_id, name, location_lat, location_lon)"
            " values (%s, %s, 'x', 1, -1)",
            (org_a.id, org_a.farm),
        )
    use_context(db, org_a.agronomist, org_a.id)
    assert stored(db, org_a.fields[0]) == (Decimal(LAT), Decimal(LON))


def test_no_context_sees_nothing(db: psycopg.Connection, org_a: Org) -> None:
    use_context(db, None)
    assert set_point(db, org_a.fields[0], LAT, LON) == 0


def test_service_account_cannot_reach_a_real_farmers_location(
    db: psycopg.Connection, org_a: Org
) -> None:
    assert set_point(db, org_a.fields[0], LAT, LON) == 1
    service = make_service(db, org_a)
    use_context(db, service, org_a.id)
    assert farms.get_field_location(db, org_a.id, org_a.fields[0]) is None
    assert set_point(db, org_a.fields[0], "1", "-1") == 0


@pytest.mark.parametrize(("lat", "lon"), [(LAT, None), (None, LON)])
def test_both_or_neither(db: psycopg.Connection, org_a: Org, lat: Any, lon: Any) -> None:
    with pytest.raises(errors.CheckViolation, match="both_or_neither"), db.transaction():
        set_point(db, org_a.fields[0], lat, lon)


@pytest.mark.parametrize(
    ("lat", "lon", "constraint"),
    [
        ("90.00001", "0", "lat_range"),
        ("-90.00001", "0", "lat_range"),
        ("NaN", "0", "lat_range"),
        ("0", "180.00001", "lon_range"),
        ("0", "-180.00001", "lon_range"),
        ("0", "NaN", "lon_range"),
    ],
)
def test_ranges(db: psycopg.Connection, org_a: Org, lat: str, lon: str, constraint: str) -> None:
    with pytest.raises(errors.CheckViolation, match=constraint), db.transaction():
        set_point(db, org_a.fields[0], lat, lon)


@pytest.mark.parametrize(("lat", "lon"), [("90", "180"), ("-90", "-180"), ("0", "0")])
def test_limits_are_allowed(db: psycopg.Connection, org_a: Org, lat: str, lon: str) -> None:
    assert set_point(db, org_a.fields[0], lat, lon) == 1


# --- create form ---------------------------------------------------------------------------


def test_create_without_location_shows_not_set(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    url = new_field(client, csrf)
    assert stored(db, field_id_of(url)) == (None, None)
    page = client.get(url).text
    assert "Location not set" in page and f'href="{url}/location"' in page


def test_create_with_location(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    action, data = farmer_form(client, csrf)
    r = client.post(action, data=data | {fl.LAT_KEY: LAT, fl.LON_KEY: LON})
    assert r.status_code == 303
    url = r.headers["location"]
    assert stored(db, field_id_of(url)) == (Decimal(LAT), Decimal(LON))
    page = client.get(url).text
    assert f"Latitude {LAT}, longitude {LON}" in page and "Location not set" not in page


@pytest.mark.parametrize(
    ("lat", "lon", "key", "message"),
    [
        (LAT, "", fl.LON_KEY, fl.MISSING_LON),
        ("", LON, fl.LAT_KEY, fl.MISSING_LAT),
        ("north", LON, fl.LAT_KEY, fl.BAD_LAT),
        ("91", LON, fl.LAT_KEY, fl.LAT_RANGE),
        (LAT, "-181", fl.LON_KEY, fl.LON_RANGE),
    ],
)
def test_create_refuses_a_bad_location_and_keeps_the_form(
    db: psycopg.Connection, org_a: Org, lat: str, lon: str, key: str, message: str
) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    action, data = farmer_form(client, csrf)
    before = field_count(db, org_a)
    r = client.post(action, data=data | {fl.LAT_KEY: lat, fl.LON_KEY: lon})
    assert r.status_code == 422 and f'id="{key}-error"' in r.text
    assert message in r.text.replace("&#39;", "'")
    assert 'value="North 40"' in r.text and f'value="{lat or lon}"' in r.text
    assert field_count(db, org_a) == before


def test_create_positive_longitude_needs_confirmation(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    action, data = farmer_form(client, csrf)
    before = field_count(db, org_a)
    data |= {fl.LAT_KEY: LAT, fl.LON_KEY: "76.54321"}
    r = client.post(action, data=data)
    assert r.status_code == 422 and "This longitude is positive" in r.text
    assert 'name="confirm_positive_lon"' in r.text and 'value="76.54321"' in r.text
    assert field_count(db, org_a) == before
    r = client.post(action, data=data | {fl.CONFIRM_KEY: "1"})
    assert r.status_code == 303
    assert stored(db, field_id_of(r.headers["location"])) == (Decimal(LAT), Decimal("76.54321"))


# --- edit form -----------------------------------------------------------------------------


def test_edit_sets_changes_and_clears(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    url = org_url = f"/fields/{org_a.fields[1]}"
    form = client.get(url + "/location")
    assert form.status_code == 200 and "not its boundary" in form.text
    r = client.post(url + "/location", data={fl.LAT_KEY: LAT, fl.LON_KEY: LON, "csrf_token": csrf})
    assert r.status_code == 303 and r.headers["location"] == org_url
    assert stored(db, org_a.fields[1]) == (Decimal(LAT), Decimal(LON))
    assert f'value="{LAT}"' in client.get(url + "/location").text
    client.post(url + "/location", data={fl.LAT_KEY: "1.5", fl.LON_KEY: "-2.5", "csrf_token": csrf})
    assert stored(db, org_a.fields[1]) == (Decimal("1.50000"), Decimal("-2.50000"))
    client.post(url + "/location", data={fl.LAT_KEY: "", fl.LON_KEY: "", "csrf_token": csrf})
    assert stored(db, org_a.fields[1]) == (None, None)
    assert "Location not set" in client.get(url).text


def test_edit_error_changes_nothing(db: psycopg.Connection, org_a: Org) -> None:
    set_point(db, org_a.fields[0], LAT, LON)
    client, csrf = signed_in(db, org_a.agronomist)
    r = client.post(
        f"/fields/{org_a.fields[0]}/location",
        data={fl.LAT_KEY: "95", fl.LON_KEY: LON, "csrf_token": csrf},
    )
    assert r.status_code == 422 and 'id="location_lat-error"' in r.text
    assert stored(db, org_a.fields[0]) == (Decimal(LAT), Decimal(LON))


def test_saved_positive_longitude_can_be_saved_again(db: psycopg.Connection, org_a: Org) -> None:
    set_point(db, org_a.fields[0], LAT, "76.54321")
    client, _ = signed_in(db, org_a.agronomist)
    page = client.get(f"/fields/{org_a.fields[0]}/location").text
    assert re.search(r'name="confirm_positive_lon" type="checkbox" value="1" checked', page)


def test_edit_needs_csrf(db: psycopg.Connection, org_a: Org) -> None:
    client, _ = signed_in(db, org_a.agronomist)
    r = client.post(f"/fields/{org_a.fields[0]}/location", data={fl.LAT_KEY: LAT, fl.LON_KEY: LON})
    assert r.status_code == 403
    assert stored(db, org_a.fields[0]) == (None, None)


def test_edit_needs_login(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    client.cookies.clear()
    url = f"/fields/{org_a.fields[0]}/location"
    assert client.get(url, follow_redirects=False).status_code in (303, 401)
    r = client.post(url, data={fl.LAT_KEY: LAT, fl.LON_KEY: LON, "csrf_token": csrf})
    assert r.status_code in (303, 401, 403)
    assert stored(db, org_a.fields[0]) == (None, None)


def test_other_org_gets_404(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    use_context(db, org_a.agronomist, org_a.id)
    set_point(db, org_a.fields[0], LAT, LON)
    client, csrf = signed_in(db, org_b.agronomist)
    url = f"/fields/{org_a.fields[0]}/location"
    assert client.get(url).status_code == 404
    r = client.post(url, data={fl.LAT_KEY: "1", fl.LON_KEY: "-1", "csrf_token": csrf})
    assert r.status_code == 404
    use_context(db, org_a.agronomist, org_a.id)
    assert stored(db, org_a.fields[0]) == (Decimal(LAT), Decimal(LON))


# --- privacy -------------------------------------------------------------------------------


def assert_no_coordinates(text: str) -> None:
    assert LAT_MARK not in text and LON_MARK not in text
    assert "location_lat" not in text and "location_lon" not in text


def test_plan_of_located_field_holds_no_coordinates(
    db: psycopg.Connection, org_a: Org, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    client, csrf = signed_in(db, org_a.agronomist)
    action, data = farmer_form(client, csrf)
    url = client.post(action, data=data | {fl.LAT_KEY: LAT, fl.LON_KEY: LON}).headers["location"]
    plan_url = create_plan(client, csrf, url)
    row = db.execute(
        "select r.inputs_snapshot, r.result from recommendation r"
        " where r.crop_plan_id = %s",
        (UUID(plan_url.rsplit("/", 1)[1]),),
    ).fetchone()  # fmt: skip
    assert row is not None
    assert_no_coordinates(json.dumps(row[0]))
    assert_no_coordinates(json.dumps(row[1]))
    assert_no_coordinates(client.get(plan_url).text)
    assert LAT_MARK not in caplog.text and LON_MARK not in caplog.text


def test_refused_location_is_not_logged(
    db: psycopg.Connection, org_a: Org, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    client, csrf = signed_in(db, org_a.agronomist)
    r = client.post(
        f"/fields/{org_a.fields[0]}/location",
        data={fl.LAT_KEY: "12.3459", fl.LON_KEY: "76.5439", "csrf_token": csrf},
    )
    assert r.status_code == 422
    assert "12.3459" not in caplog.text and "76.5439" not in caplog.text


def test_proof_of_located_field_holds_no_coordinates(
    db: psycopg.Connection,
    org_a: Org,
    tmp_path: Path,
    fake: FakeRender,  # noqa: F811
) -> None:
    set_point(db, org_a.fields[0], LAT, LON)
    review(db, org_a, org_a.agronomist)
    client, csrf = client_for(db, org_a.agronomist, tmp_path)
    assert generate(client, csrf, org_a).status_code == 303
    assert len(fake.inputs) == 1
    assert_no_coordinates(repr(fake.inputs[0]))
    stored_files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert stored_files
    for path in stored_files:
        assert_no_coordinates(path.read_bytes().decode("utf-8", "ignore"))
