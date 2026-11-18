"""Product catalog page (/products, story S2-APP-09). All products are synthetic."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from cloverproof_app import products_web
from cloverproof_app.repo.products import NewProduct

from .conftest import Org, as_owner
from .test_fertilizer_product import add, product
from .test_superadmin import make_user
from .test_web_auth import build_client, email_of, login, page_csrf, with_password

pytestmark = pytest.mark.db

NAME = "TEST-GRADE 10-0-0"
ORG_ROLES = ("org_admin", "advisor", "agronomist", "farmer")
ADD_HEADING = "Add a draft product"
COMMERCIAL = re.compile(r"price|cost|vendor|supplier|dealer|retailer|affiliate|commission", re.I)


def sign_in(db: psycopg.Connection, user: UUID) -> tuple[TestClient, str]:
    with_password(db, user)
    client = build_client(db)
    assert login(client, email_of(db, user)).status_code == 303
    return client, page_csrf(client, "/products")


def member(db: psycopg.Connection, org: Org, role: str) -> UUID:
    return make_user(db, org, f"catalog-{role}", roles=(role,), platform_role=None)


@pytest.fixture
def superadmin(db: psycopg.Connection, org_a: Org) -> UUID:
    return make_user(db, org_a, "catalog-root", roles=())


def seed(db: psycopg.Connection, author: UUID, status: str, **overrides: Any) -> UUID:
    with as_owner(db):
        return add(db, product(author, status=status, **overrides))


def stored(db: psycopg.Connection, name: str = NAME) -> list[tuple[Any, ...]]:
    with as_owner(db):
        return db.execute(
            "select status, created_by, country_code, n, density_kg_per_l"
            " from fertilizer_product where name = %s",
            (name,),
        ).fetchall()


def status_of(db: psycopg.Connection, product_id: UUID) -> str:
    with as_owner(db):
        row = db.execute(
            "select status from fertilizer_product where id = %s", (product_id,)
        ).fetchone()
    assert row is not None
    return row[0]


def form(csrf: str | None, **overrides: str) -> dict[str, str]:
    data = {
        "country_code": "CA",
        "name": NAME,
        "n": "10",
        "p2o5": "0",
        "k2o": "0",
        "s": "0",
        "product_form": "granular",
        "density_kg_per_l": "",
        "grade_source": "TEST synthetic label, not a real product",
    }
    if csrf is not None:
        data["csrf_token"] = csrf
    return data | overrides


# --- reading ------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ORG_ROLES)
def test_org_roles_read_active_only_and_get_no_form(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, role: str
) -> None:
    seed(db, superadmin, "active", name=NAME, n=10.5, grade_source="TEST label 2026")
    seed(db, superadmin, "draft", name="TEST-GRADE hidden draft")
    client, _ = sign_in(db, member(db, org_a, role))
    page = client.get("/products")
    assert page.status_code == 200
    assert NAME in page.text and "10.5-0-0-0" in page.text and "TEST label 2026" in page.text
    assert "TEST-GRADE hidden draft" not in page.text
    assert ADD_HEADING not in page.text
    assert "/activate" not in page.text
    assert 'action="/products"' not in page.text


def test_page_needs_a_session(db: psycopg.Connection) -> None:
    page = build_client(db).get("/products", headers={"accept": "text/html"})
    assert page.status_code == 303
    assert page.headers["location"].startswith("/login")


def test_empty_catalog_says_so(db: psycopg.Connection, org_a: Org) -> None:
    client, _ = sign_in(db, org_a.agronomist)
    page = client.get("/products")
    assert "The catalog has no products yet." in page.text
    assert "confirmed label source" in page.text
    assert "<table" not in page.text


def test_page_has_the_columns_and_nothing_commercial(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    seed(db, superadmin, "active", name=NAME, form="liquid", density_kg_per_l=1.28)
    for user in (org_a.agronomist, superadmin):
        page = sign_in(db, user)[0].get("/products")
        headers = re.findall(r'<th scope="col">([^<]+)</th>', page.text)
        assert headers[:6] == [
            "Name",
            "Country",
            "Grade N-P₂O₅-K₂O-S (label %)",
            "Form",
            "Density",
            "Source of the grade",
        ]
        assert "1.28 kg/L" in page.text
        # Only the page body: the header loads /static/vendor/htmx.
        assert COMMERCIAL.search(page.text.partition('<main id="main"')[2]) is None


def test_nav_link_is_shown(db: psycopg.Connection, org_a: Org) -> None:
    client, _ = sign_in(db, org_a.agronomist)
    assert 'href="/products"' in client.get("/farmers").text


def test_superadmin_without_organisation_sees_drafts_marked(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client, _ = sign_in(db, superadmin)
    page = client.get("/products")
    assert page.status_code == 200
    assert NAME in page.text and ">Draft</span>" in page.text
    assert ADD_HEADING in page.text
    assert f"/products/{draft}/activate" in page.text


# --- adding and activating ----------------------------------------------------------------


def test_superadmin_adds_a_draft_then_activates_it(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, csrf = sign_in(db, superadmin)
    forged = form(csrf, created_by=str(org_a.agronomist), status="active")
    added = client.post("/products", data=forged)
    assert added.status_code == 303
    rows = stored(db)
    assert len(rows) == 1 and rows[0][:3] == ("draft", superadmin, "CA")
    assert ">Draft</span>" in client.get(added.headers["location"]).text

    reader, _ = sign_in(db, org_a.agronomist)
    assert NAME not in reader.get("/products").text

    with as_owner(db):
        row = db.execute("select id from fertilizer_product where name = %s", (NAME,)).fetchone()
    assert row is not None
    activated = client.post(f"/products/{row[0]}/activate", data={"csrf_token": csrf})
    assert activated.status_code == 303
    assert status_of(db, row[0]) == "active"
    assert NAME in reader.get("/products").text


def test_liquid_product_stores_density_and_country_is_uppercased(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, csrf = sign_in(db, superadmin)
    data = form(csrf, product_form="liquid", density_kg_per_l="1,28", country_code="ca")
    assert client.post("/products", data=data).status_code == 303
    row = stored(db)[0]
    assert row[2] == "CA" and row[4] == Decimal("1.280")


@pytest.mark.parametrize("role", ORG_ROLES)
def test_org_roles_get_403_on_every_write(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, role: str
) -> None:
    draft = seed(db, superadmin, "draft")
    client, csrf = sign_in(db, member(db, org_a, role))
    assert client.post("/products", data=form(csrf)).status_code == 403
    assert client.post(f"/products/{draft}/activate", data={"csrf_token": csrf}).status_code == 403
    assert stored(db) == []
    assert status_of(db, draft) == "draft"


def test_csrf_is_required(db: psycopg.Connection, org_a: Org, superadmin: UUID) -> None:
    draft = seed(db, superadmin, "draft")
    client, _ = sign_in(db, superadmin)
    assert client.post("/products", data=form(None)).status_code == 403
    assert client.post("/products", data=form("0" * 64)).status_code == 403
    assert client.post(f"/products/{draft}/activate", data={}).status_code == 403
    assert stored(db) == []
    assert status_of(db, draft) == "draft"


# --- validation ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": "   "}, "Enter the product name."),
        ({"name": "x" * 201}, "Product name is too long"),
        ({"country_code": "C"}, "two-letter country code"),
        ({"country_code": "C1"}, "two-letter country code"),
        ({"country_code": "ß"}, "two-letter country code"),
        ({"n": ""}, "Enter the N percentage"),
        ({"n": "abc"}, "N must be a number."),
        ({"n": "1e1"}, "N must be a number."),
        ({"n": "NaN"}, "N must be a number."),
        ({"p2o5": "-1"}, "must be between 0 and 100."),
        ({"k2o": "100.01"}, "must be between 0 and 100."),
        ({"s": "1.234"}, "at most 2 decimal places"),
        ({"n": "50", "p2o5": "30", "k2o": "20", "s": "0.01"}, "adds up to 100.01%"),
        ({"product_form": "powder"}, "Choose granular or liquid."),
        ({"product_form": "liquid"}, "Enter the density"),
        ({"product_form": "liquid", "density_kg_per_l": "0"}, "Density must be above 0"),
        ({"product_form": "liquid", "density_kg_per_l": "x"}, "Density must be a number."),
        ({"product_form": "liquid", "density_kg_per_l": "1.2345"}, "at most 3 decimal places"),
        ({"density_kg_per_l": "1.2"}, "Leave density empty"),
        ({"grade_source": "  "}, "Enter where the grade comes from"),
    ],
    ids=str,
)
def test_validation_errors_are_explicit(
    db: psycopg.Connection,
    org_a: Org,
    superadmin: UUID,
    overrides: dict[str, str],
    message: str,
) -> None:
    client, csrf = sign_in(db, superadmin)
    page = client.post("/products", data=form(csrf, **overrides))
    assert page.status_code == 422
    assert message in page.text
    with as_owner(db):
        assert db.execute("select count(*) from fertilizer_product").fetchone() == (0,)


def test_typed_values_stay_after_an_error(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, csrf = sign_in(db, superadmin)
    page = client.post("/products", data=form(csrf, n="abc", grade_source="TEST sheet 7"))
    assert 'value="TEST sheet 7"' in page.text and 'value="abc"' in page.text


def test_full_grade_of_exactly_100_is_accepted(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, csrf = sign_in(db, superadmin)
    data = form(csrf, n="25", p2o5="25", k2o="25", s="25")
    assert client.post("/products", data=data).status_code == 303


# --- duplicates and database refusals -----------------------------------------------------


def test_activating_a_duplicate_name_is_a_plain_409(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    seed(db, superadmin, "active", name=NAME)
    draft = seed(db, superadmin, "draft", name=NAME.lower())
    client, csrf = sign_in(db, superadmin)
    page = client.post(f"/products/{draft}/activate", data={"csrf_token": csrf})
    assert page.status_code == 409
    assert "already exists in this country" in page.text
    assert status_of(db, draft) == "draft"


def test_adding_a_name_already_active_is_a_plain_409(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    seed(db, superadmin, "active", name=NAME)
    client, csrf = sign_in(db, superadmin)
    page = client.post("/products", data=form(csrf, name=NAME.lower()))
    assert page.status_code == 409
    assert "already exists in CA" in page.text
    assert stored(db, NAME.lower()) == []


def test_same_name_in_another_country_is_allowed(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    seed(db, superadmin, "active", name=NAME)
    client, csrf = sign_in(db, superadmin)
    assert client.post("/products", data=form(csrf, country_code="US")).status_code == 303


def test_activating_twice_or_unknown_is_plain(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    active = seed(db, superadmin, "active")
    client, csrf = sign_in(db, superadmin)
    again = client.post(f"/products/{active}/activate", data={"csrf_token": csrf})
    assert again.status_code == 409 and "already active" in again.text
    missing = client.post(f"/products/{uuid4()}/activate", data={"csrf_token": csrf})
    assert missing.status_code == 404


def test_database_check_refusal_is_a_plain_error(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skip the app validation: the CHECK constraint refuses, the page still renders."""
    bad = NewProduct(
        "CA", NAME, Decimal(60), Decimal(60), Decimal(0), Decimal(0), "granular", None, "TEST"
    )
    monkeypatch.setattr(products_web, "validate", lambda _form: (bad, {"name": NAME}, {}))
    client, csrf = sign_in(db, superadmin)
    page = client.post("/products", data=form(csrf))
    assert page.status_code == 422
    assert products_web.DB_REFUSED in page.text
    assert stored(db) == []


def test_database_rls_refusal_is_a_plain_error(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skip the app role check: RLS still refuses, and drafts stay hidden."""
    draft = seed(db, superadmin, "draft", name="TEST-GRADE hidden draft")
    monkeypatch.setattr(products_web, "may_manage", lambda _user: True)
    client, csrf = sign_in(db, org_a.agronomist)
    page = client.post("/products", data=form(csrf))
    assert page.status_code == 403
    assert products_web.DB_DENIED in page.text
    assert "TEST-GRADE hidden draft" not in page.text
    assert stored(db) == []
    assert client.post(f"/products/{draft}/activate", data={"csrf_token": csrf}).status_code == 404
    assert status_of(db, draft) == "draft"
