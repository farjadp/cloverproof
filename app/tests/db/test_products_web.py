"""Product catalog page (/products, story S2-APP-09). All products are synthetic."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from cloverproof_app import product_presets as presets
from cloverproof_app import products_web
from cloverproof_app.repo.products import NewProduct

from .conftest import Org, as_owner
from .test_fertilizer_product import add, product
from .test_superadmin import make_user
from .test_web_auth import build_client, email_of, login, page_csrf, with_password

pytestmark = pytest.mark.db

NAME = "TEST-GRADE 10-0-0"
ORG_ROLES = ("org_admin", "advisor", "agronomist", "farmer")
ADD_HEADING = "Add a product"
COMMERCIAL = re.compile(r"price|cost|vendor|supplier|dealer|retailer|affiliate|commission", re.I)
PRESET_NOTICE = (
    "Filled from a published reference. Unconfirmed: check every value against the product"
    " label before activating."
)
S_HINT = "Sulphur is not stated in the source. Enter it from the label (0 if the label shows none)."
CONFIRM = "I checked these values against the product label"


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


def confirmed(csrf: str) -> dict[str, str]:
    return {"csrf_token": csrf, "label_checked": "yes"}


def count_products(db: psycopg.Connection) -> int:
    with as_owner(db):
        row = db.execute("select count(*) from fertilizer_product").fetchone()
    assert row is not None
    return row[0]


def field_value(page: str, name: str) -> str:
    """The value a text input is rendered with."""
    match = re.search(rf'<input id="{name}" [^>]*?value="([^"]*)"', page)
    assert match is not None, name
    return match.group(1)


def selected_option(page: str, name: str) -> str:
    select = re.search(rf'<select id="{name}".*?</select>', page, re.S)
    assert select is not None
    match = re.search(r'<option value="([^"]+)" selected>', select.group(0))
    assert match is not None
    return match.group(1)


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
    assert 'name="grade_source"' not in page.text  # the form waits behind one clear action
    assert 'href="/products?add=1#add-product"' in page.text


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
    activated = client.post(f"/products/{row[0]}/activate", data=confirmed(csrf))
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
    assert client.post(f"/products/{draft}/activate", data=confirmed(csrf)).status_code == 403
    assert client.get(f"/products/{draft}/activate").status_code == 403
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
        ({"country_code": "C"}, "Choose a country from the list."),
        ({"country_code": "C1"}, "Choose a country from the list."),
        ({"country_code": "ß"}, "Choose a country from the list."),
        ({"country_code": "XX"}, "Choose a country from the list."),
        ({"country_code": ""}, "Choose a country from the list."),
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
    assert ">TEST sheet 7</textarea>" in page.text and 'value="abc"' in page.text


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
    page = client.post(f"/products/{draft}/activate", data=confirmed(csrf))
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
    again = client.post(f"/products/{active}/activate", data=confirmed(csrf))
    assert again.status_code == 409 and "already active" in again.text
    missing = client.post(f"/products/{uuid4()}/activate", data=confirmed(csrf))
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
    assert client.post(f"/products/{draft}/activate", data=confirmed(csrf)).status_code == 404
    assert status_of(db, draft) == "draft"


# --- adding from a published fertilizer type ----------------------------------------------


def test_opening_the_add_form_shows_picker_and_manual_entry(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    seed(db, superadmin, "active", name=NAME)
    client, _ = sign_in(db, superadmin)
    page = client.get("/products?add=1").text
    assert "Start from a common fertilizer type" in page and "Enter manually" in page
    for group in ("Nitrogen", "Phosphate", "Potash", "Sulphur", "Blended liquids"):
        assert f'<h4 class="preset-group">{group}</h4>' in page
    assert "/products?preset=urea" in page
    assert selected_option(page, "country_code") == "CA"
    assert page.index('<option value="CA"') < page.index('<option value="AF"')
    assert field_value(page, "n") == ""


def test_empty_catalog_opens_the_form_for_a_superadmin(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, _ = sign_in(db, superadmin)
    page = client.get("/products").text
    assert "The catalog has no products yet." in page and 'name="grade_source"' in page


def test_preset_fills_the_form_and_saves_nothing(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, _ = sign_in(db, superadmin)
    response = client.get("/products?preset=urea")
    assert response.status_code == 200
    page = response.text
    assert PRESET_NOTICE in page
    assert field_value(page, "name") == "Urea"
    assert (field_value(page, "n"), field_value(page, "p2o5")) == ("46", "0")
    assert "OMAFRA Publication 611" in page.split('id="grade_source"')[1].split("</textarea>")[0]
    assert selected_option(page, "product_form") == "granular"
    assert count_products(db) == 0


def test_preset_without_sulphur_leaves_it_empty_with_a_hint(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, _ = sign_in(db, superadmin)
    page = client.get("/products?preset=urea").text
    assert field_value(page, "s") == ""
    assert S_HINT in page
    stated = client.get("/products?preset=ammonium_sulphate").text
    assert field_value(stated, "s") == "24"
    assert S_HINT not in stated


def test_liquid_preset_fills_density_and_missing_density_stays_empty(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, _ = sign_in(db, superadmin)
    uan = client.get("/products?preset=uan_28").text
    assert selected_option(uan, "product_form") == "liquid"
    assert field_value(uan, "density_kg_per_l") == "1.28"
    ammonia = client.get("/products?preset=anhydrous_ammonia").text
    assert field_value(ammonia, "n") == "82" and field_value(ammonia, "k2o") == "0"
    assert field_value(ammonia, "density_kg_per_l") == ""
    assert "Enter it from the label." in ammonia.split('id="density-hint"')[1].split("</p>")[0]


def test_preset_cannot_be_saved_until_sulphur_is_entered(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, csrf = sign_in(db, superadmin)
    data = form(csrf, preset="urea", name="Urea", n="46", s="")
    page = client.post("/products", data=data)
    assert page.status_code == 422
    assert "Enter the S percentage" in page.text
    assert PRESET_NOTICE in page.text and S_HINT in page.text  # still explained after the error
    assert count_products(db) == 0


def test_saving_uses_the_submitted_values_not_the_preset(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, csrf = sign_in(db, superadmin)
    data = form(csrf, preset="urea", name="Edited urea", n="45.5", grade_source="TEST label")
    saved = client.post("/products", data=data)
    assert saved.status_code == 303
    rows = stored(db, "Edited urea")
    assert rows[0][0] == "draft" and rows[0][3] == Decimal("45.50")
    page = client.get(saved.headers["location"]).text
    assert "Saved as a draft. Only superadmins can see it." in page
    assert "Check Edited urea and activate it" in page


def test_a_preset_key_alone_fills_nothing_on_post(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, csrf = sign_in(db, superadmin)
    assert client.post("/products", data={"csrf_token": csrf, "preset": "urea"}).status_code == 422
    assert count_products(db) == 0


def test_unknown_preset_is_explained(db: psycopg.Connection, org_a: Org, superadmin: UUID) -> None:
    client, _ = sign_in(db, superadmin)
    page = client.get("/products?preset=nope")
    assert page.status_code == 404
    assert products_web.UNKNOWN_PRESET in page.text and 'name="grade_source"' in page.text


def test_search_works_without_javascript_and_through_htmx(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, _ = sign_in(db, superadmin)
    plain = client.get("/products", params={"add": "1", "q": "46-0-0"}).text
    assert "/products?preset=urea" in plain
    assert "/products?preset=uan_28" not in plain
    assert 'value="46-0-0"' in plain
    partial = client.get("/products/presets", params={"q": "uan"})
    assert partial.status_code == 200
    assert "/products?preset=uan_28" in partial.text
    assert "/products?preset=urea" not in partial.text and "<html" not in partial.text
    none = client.get("/products/presets", params={"q": "<b>zzz"}).text
    assert "No type matches" in none and "<b>zzz" not in none


@pytest.mark.parametrize("role", ORG_ROLES)
def test_org_roles_get_no_picker_and_no_filled_form(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, role: str
) -> None:
    seed(db, superadmin, "active", name=NAME)
    client, _ = sign_in(db, member(db, org_a, role))
    for url in ("/products?preset=urea", "/products?add=1", "/products?q=urea"):
        page = client.get(url)
        assert page.status_code == 200 and NAME in page.text
        assert "Start from a common fertilizer type" not in page.text
        assert 'name="grade_source"' not in page.text
    assert client.get("/products/presets", params={"q": "urea"}).status_code == 403


def test_the_form_works_without_javascript(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    """The server page alone offers everything: the density field is not hidden by it."""
    client, csrf = sign_in(db, superadmin)
    page = client.get("/products?add=manual").text
    assert 'id="density-field"' in page and "Leave empty for a granular product." in page
    assert 'id="density-field" hidden' not in page
    assert 'method="get" action="/products"' in page
    data = form(csrf, product_form="liquid", density_kg_per_l="1.3", country_code="FR")
    assert client.post("/products", data=data).status_code == 303
    assert stored(db)[0][2] == "FR"


def test_country_names_are_shown_and_an_error_keeps_the_choice(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    seed(db, superadmin, "active", name=NAME, country_code="FR")
    client, csrf = sign_in(db, superadmin)
    assert '<td data-label="Country">France</td>' in client.get("/products").text
    page = client.post("/products", data=form(csrf, country_code="US", n="abc")).text
    assert selected_option(page, "country_code") == "US"


def test_errors_link_from_the_summary_to_each_field(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, csrf = sign_in(db, superadmin)
    page = client.post("/products", data=form(csrf, name="", n="abc", grade_source="")).text
    assert 'id="error-summary"' in page
    for field in ("name", "n", "grade_source"):
        assert f'<a href="#{field}">' in page and f'id="{field}-error"' in page
    assert field_value(page, "n") == "abc"


# --- activation needs the label check -----------------------------------------------------


def test_confirmation_page_states_the_consequences(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client, _ = sign_in(db, superadmin)
    page = client.get(f"/products/{draft}/activate")
    assert page.status_code == 200
    assert CONFIRM in page.text
    assert "can't be edited and is visible to every user" in page.text.replace("&#39;", "'")
    assert status_of(db, draft) == "draft"


def test_activation_without_the_checkbox_is_refused(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client, csrf = sign_in(db, superadmin)
    for data in ({"csrf_token": csrf}, {"csrf_token": csrf, "label_checked": "no"}):
        page = client.post(f"/products/{draft}/activate", data=data)
        assert page.status_code == 422
        assert products_web.LABEL_NOT_CONFIRMED in page.text
        assert status_of(db, draft) == "draft"
    assert client.post(f"/products/{draft}/activate", data=confirmed(csrf)).status_code == 303
    assert status_of(db, draft) == "active"


def test_preset_draft_must_name_the_label_checked_before_activation(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    source = f"TEST reference, p. 1; {products_web.UNCONFIRMED_SOURCE}"
    draft = seed(db, superadmin, "draft", name=NAME, grade_source=source)
    client, csrf = sign_in(db, superadmin)
    assert 'name="grade_source"' in client.get(f"/products/{draft}/activate").text
    for value in ("", source):
        page = client.post(
            f"/products/{draft}/activate", data={**confirmed(csrf), "grade_source": value}
        )
        assert page.status_code == 422 and products_web.CHECKED_SOURCE_MISSING in page.text
        assert status_of(db, draft) == "draft"
    done = client.post(
        f"/products/{draft}/activate",
        data={**confirmed(csrf), "grade_source": "TEST label, 2026 edition"},
    )
    assert done.status_code == 303 and status_of(db, draft) == "active"
    row = db.execute("select grade_source from fertilizer_product where id = %s", (draft,))
    assert row.fetchone() == ("TEST label, 2026 edition",)


def test_confirmation_page_for_active_or_unknown_product(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    active = seed(db, superadmin, "active", name=NAME)
    client, _ = sign_in(db, superadmin)
    assert client.get(f"/products/{active}/activate").status_code == 409
    assert client.get(f"/products/{uuid4()}/activate").status_code == 404


def test_product_pages_have_no_inline_script(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    """The CSP is script-src 'self': an inline script would silently not run."""
    draft = seed(db, superadmin, "draft", name=NAME)
    client, _ = sign_in(db, superadmin)
    for url in ("/products?preset=urea", f"/products/{draft}/activate"):
        scripts = re.findall(r"<script([^>]*)>", client.get(url).text)
        assert scripts and all('src="/static/' in attributes for attributes in scripts)


# --- editing a draft ----------------------------------------------------------------------

UNCONFIRMED = products_web.UNCONFIRMED_SOURCE
EDITED = "TEST-GRADE 12-0-0"
HTML = {"accept": "text/html"}


def row_of(db: psycopg.Connection, product_id: UUID) -> dict[str, Any] | None:
    with as_owner(db), db.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "select country_code, name, n, p2o5, k2o, s, form, density_kg_per_l, status,"
            " grade_source, created_by from fertilizer_product where id = %s",
            (product_id,),
        ).fetchone()


def activates_meanwhile(
    db: psycopg.Connection, draft: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The route reads a draft; right after that read the row becomes active."""
    real = products_web.repo.get_product

    def stale(conn: psycopg.Connection, product_id: UUID) -> Any:
        found = real(conn, product_id)
        with as_owner(db):
            db.execute("update fertilizer_product set status = 'active' where id = %s", (draft,))
        return found

    monkeypatch.setattr(products_web.repo, "get_product", stale)


def test_edit_form_is_filled_from_the_draft(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(
        db,
        superadmin,
        "draft",
        name=NAME,
        country_code="FR",
        n=10.5,
        form="liquid",
        density_kg_per_l=1.28,
    )
    client, _ = sign_in(db, superadmin)
    response = client.get(f"/products/{draft}/edit")
    assert response.status_code == 200
    page = response.text
    assert f'action="/products/{draft}/edit"' in page
    assert field_value(page, "name") == NAME
    assert (field_value(page, "n"), field_value(page, "p2o5")) == ("10.5", "0")
    assert field_value(page, "density_kg_per_l") == "1.28"
    assert selected_option(page, "country_code") == "FR"
    assert selected_option(page, "product_form") == "liquid"
    assert 'id="grade-summary"' in page and "/static/product_form.js" in page
    assert "Start from a common fertilizer type" not in page


def test_saving_an_edit_replaces_the_values_and_stays_a_draft(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client, csrf = sign_in(db, superadmin)
    data = form(
        csrf,
        name=EDITED,
        n="12",
        country_code="us",
        product_form="liquid",
        density_kg_per_l="1,3",
        grade_source="TEST label, edition 2",
        status="active",
        created_by=str(org_a.agronomist),
    )
    saved = client.post(f"/products/{draft}/edit", data=data)
    assert saved.status_code == 303
    row = row_of(db, draft)
    assert row is not None
    assert row["name"] == EDITED and row["n"] == Decimal("12.00") and row["country_code"] == "US"
    assert row["form"] == "liquid" and row["density_kg_per_l"] == Decimal("1.300")
    assert row["grade_source"] == "TEST label, edition 2"
    assert row["status"] == "draft" and row["created_by"] == superadmin
    assert count_products(db) == 1
    assert products_web.DONE_MESSAGES["edited"] in client.get(saved.headers["location"]).text


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": "  "}, "Enter the product name."),
        ({"country_code": "XX"}, "Choose a country from the list."),
        ({"n": "abc"}, "N must be a number."),
        ({"n": "50", "p2o5": "30", "k2o": "20", "s": "1"}, "adds up to 101%"),
        ({"product_form": "liquid"}, "Enter the density"),
        ({"density_kg_per_l": "1.2"}, "Leave density empty"),
        ({"grade_source": " "}, "Enter where the grade comes from"),
    ],
    ids=str,
)
def test_edit_is_validated_like_add_and_changes_nothing(
    db: psycopg.Connection,
    org_a: Org,
    superadmin: UUID,
    overrides: dict[str, str],
    message: str,
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    before = row_of(db, draft)
    client, csrf = sign_in(db, superadmin)
    data = form(csrf, name=EDITED) | overrides
    page = client.post(f"/products/{draft}/edit", data=data)
    assert page.status_code == 422
    assert message in page.text and 'id="error-summary"' in page.text
    assert f'action="/products/{draft}/edit"' in page.text
    assert row_of(db, draft) == before


def test_edit_keeps_typed_values_after_an_error(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client, csrf = sign_in(db, superadmin)
    data = form(csrf, name=EDITED, n="abc", country_code="US")
    page = client.post(f"/products/{draft}/edit", data=data).text
    assert field_value(page, "name") == EDITED and field_value(page, "n") == "abc"
    assert selected_option(page, "country_code") == "US"


def test_edit_cannot_take_the_name_of_an_active_product(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    seed(db, superadmin, "active", name=EDITED)
    draft = seed(db, superadmin, "draft", name=NAME)
    client, csrf = sign_in(db, superadmin)
    page = client.post(f"/products/{draft}/edit", data=form(csrf, name=EDITED.lower()))
    assert page.status_code == 409 and "already exists in CA" in page.text
    row = row_of(db, draft)
    assert row is not None and row["name"] == NAME


def test_active_product_cannot_be_edited(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    active = seed(db, superadmin, "active", name=NAME)
    before = row_of(db, active)
    client, csrf = sign_in(db, superadmin)
    for page in (
        client.get(f"/products/{active}/edit"),
        client.post(f"/products/{active}/edit", data=form(csrf, name=EDITED)),
    ):
        assert page.status_code == 409
        assert products_web.ACTIVE_NOT_EDITABLE.replace("'", "&#39;") in page.text
    assert row_of(db, active) == before


def test_draft_activated_meanwhile_is_not_edited(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client, csrf = sign_in(db, superadmin)
    activates_meanwhile(db, draft, monkeypatch)
    page = client.post(f"/products/{draft}/edit", data=form(csrf, name=EDITED))
    assert page.status_code == 409
    row = row_of(db, draft)
    assert row is not None and row["name"] == NAME


def test_unknown_product_is_404_on_edit_and_discard(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    client, csrf = sign_in(db, superadmin)
    missing = uuid4()
    assert client.get(f"/products/{missing}/edit").status_code == 404
    assert client.post(f"/products/{missing}/edit", data=form(csrf)).status_code == 404
    assert client.get(f"/products/{missing}/discard").status_code == 404
    assert client.post(f"/products/{missing}/discard", data={"csrf_token": csrf}).status_code == 404


# --- a draft from a published type still needs the label checked ---------------------------


def preset_draft(db: psycopg.Connection, superadmin: UUID) -> tuple[UUID, str]:
    source = presets.BY_KEY["urea"].source
    assert UNCONFIRMED in source.lower()
    return seed(db, superadmin, "draft", name=NAME, grade_source=source), source


def test_preset_draft_still_needs_the_checked_label_after_an_edit(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft, source = preset_draft(db, superadmin)
    client, csrf = sign_in(db, superadmin)
    data = form(csrf, name=EDITED, n="45", grade_source=source)
    assert client.post(f"/products/{draft}/edit", data=data).status_code == 303

    assert 'name="grade_source"' in client.get(f"/products/{draft}/activate").text
    refused = client.post(f"/products/{draft}/activate", data=confirmed(csrf))
    assert refused.status_code == 422 and products_web.CHECKED_SOURCE_MISSING in refused.text
    assert status_of(db, draft) == "draft"
    unticked = client.post(
        f"/products/{draft}/activate", data={"csrf_token": csrf, "grade_source": "TEST label 2026"}
    )
    assert unticked.status_code == 422 and status_of(db, draft) == "draft"
    done = client.post(
        f"/products/{draft}/activate", data={**confirmed(csrf), "grade_source": "TEST label 2026"}
    )
    assert done.status_code == 303 and status_of(db, draft) == "active"


@pytest.mark.parametrize("cut", ["whole", "marker"])
def test_an_edit_cannot_remove_the_unconfirmed_note(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, cut: str
) -> None:
    """Otherwise an edit would turn a published reference into a confirmed-looking source."""
    draft, source = preset_draft(db, superadmin)
    client, csrf = sign_in(db, superadmin)
    without_note = re.sub(re.escape(UNCONFIRMED), "", source, flags=re.I).strip(" ;,.")
    value = "TEST label 2026" if cut == "whole" else without_note
    page = client.post(f"/products/{draft}/edit", data=form(csrf, grade_source=value))
    assert page.status_code == 422
    assert products_web.KEEP_UNCONFIRMED.replace('"', "&#34;") in page.text
    row = row_of(db, draft)
    assert row is not None and row["grade_source"] == source and row["name"] == NAME


def test_edit_page_explains_the_unconfirmed_source(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft, _ = preset_draft(db, superadmin)
    plain = seed(db, superadmin, "draft", name="TEST-GRADE plain")
    client, _csrf = sign_in(db, superadmin)
    assert UNCONFIRMED in client.get(f"/products/{draft}/edit").text.split('id="product-form"')[0]
    assert UNCONFIRMED not in client.get(f"/products/{plain}/edit").text


# --- discarding a draft -------------------------------------------------------------------


def test_discard_asks_first_and_names_the_product(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client, _ = sign_in(db, superadmin)
    page = client.get(f"/products/{draft}/discard")
    assert page.status_code == 200
    assert f"Discard {NAME}?" in page.text and "10-0-0-0" in page.text
    assert f'action="/products/{draft}/discard"' in page.text and 'name="csrf_token"' in page.text
    assert status_of(db, draft) == "draft"


def test_discard_really_deletes_the_draft(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    other = seed(db, superadmin, "draft", name="TEST-GRADE keep me")
    client, csrf = sign_in(db, superadmin)
    done = client.post(f"/products/{draft}/discard", data={"csrf_token": csrf})
    assert done.status_code == 303
    assert row_of(db, draft) is None and row_of(db, other) is not None
    page = client.get(done.headers["location"]).text
    assert products_web.DONE_MESSAGES["discarded"] in page and NAME not in page


def test_active_product_cannot_be_discarded(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    active = seed(db, superadmin, "active", name=NAME)
    client, csrf = sign_in(db, superadmin)
    for page in (
        client.get(f"/products/{active}/discard"),
        client.post(f"/products/{active}/discard", data={"csrf_token": csrf}),
    ):
        assert page.status_code == 409
        assert products_web.ACTIVE_NOT_DISCARDABLE.replace("'", "&#39;") in page.text
    assert status_of(db, active) == "active"


def test_draft_activated_meanwhile_is_not_discarded(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client, csrf = sign_in(db, superadmin)
    activates_meanwhile(db, draft, monkeypatch)
    page = client.post(f"/products/{draft}/discard", data={"csrf_token": csrf})
    assert page.status_code == 409 and status_of(db, draft) == "active"


def test_referenced_draft_is_refused_not_deleted(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    """Nothing references products today. The day something does, discarding must refuse."""
    draft = seed(db, superadmin, "draft", name=NAME)
    with as_owner(db):
        db.execute("create table test_product_ref (p uuid references fertilizer_product (id))")
        db.execute("insert into test_product_ref values (%s)", (draft,))
    client, csrf = sign_in(db, superadmin)
    page = client.post(f"/products/{draft}/discard", data={"csrf_token": csrf})
    assert page.status_code == 409 and products_web.DRAFT_IN_USE.replace("'", "&#39;") in page.text
    assert status_of(db, draft) == "draft"


# --- who may edit and discard -------------------------------------------------------------


@pytest.mark.parametrize("role", ORG_ROLES)
def test_org_roles_cannot_edit_or_discard(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, role: str
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    active = seed(db, superadmin, "active", name="TEST-GRADE listed")
    before = row_of(db, draft)
    client, csrf = sign_in(db, member(db, org_a, role))
    for product_id in (draft, active):
        assert client.get(f"/products/{product_id}/edit").status_code == 403
        assert client.get(f"/products/{product_id}/discard").status_code == 403
        data = form(csrf, name=EDITED)
        assert client.post(f"/products/{product_id}/edit", data=data).status_code == 403
        gone = client.post(f"/products/{product_id}/discard", data={"csrf_token": csrf})
        assert gone.status_code == 403
    assert row_of(db, draft) == before and status_of(db, active) == "active"


def test_rls_still_refuses_when_the_role_check_is_skipped(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    before = row_of(db, draft)
    monkeypatch.setattr(products_web, "may_manage", lambda _user: True)
    client, csrf = sign_in(db, org_a.agronomist)
    assert client.post(f"/products/{draft}/edit", data=form(csrf)).status_code == 404
    assert client.post(f"/products/{draft}/discard", data={"csrf_token": csrf}).status_code == 404
    assert row_of(db, draft) == before


def test_service_account_gets_no_session_so_cannot_edit_or_discard(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    before = row_of(db, draft)
    service = make_user(
        db, org_a, "catalog-service", roles=("advisor",), platform_role=None, actor_kind="service"
    )
    client = build_client(db)
    assert login(client, email_of(db, service)).status_code != 303
    assert client.get(f"/products/{draft}/edit", headers=HTML).status_code == 303
    assert client.post(f"/products/{draft}/edit", data=form("0" * 64)).status_code == 403
    assert client.post(f"/products/{draft}/discard", data=form("0" * 64)).status_code == 403
    assert row_of(db, draft) == before


def test_without_a_session_edit_and_discard_go_to_login(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client = build_client(db)
    for path in (f"/products/{draft}/edit", f"/products/{draft}/discard"):
        page = client.get(path, headers=HTML)
        assert page.status_code == 303 and page.headers["location"].startswith("/login")
        assert client.post(path, data=form(None)).status_code == 403
    assert status_of(db, draft) == "draft"


def test_edit_and_discard_need_the_csrf_token(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    before = row_of(db, draft)
    client, _ = sign_in(db, superadmin)
    for token in (None, "0" * 64):
        data = form(token, name=EDITED)
        assert client.post(f"/products/{draft}/edit", data=data).status_code == 403
        assert client.post(f"/products/{draft}/discard", data=data).status_code == 403
    assert row_of(db, draft) == before


# --- the catalog list ---------------------------------------------------------------------


def test_list_offers_edit_and_discard_for_drafts_only(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    active = seed(db, superadmin, "active", name="TEST-GRADE listed")
    client, _ = sign_in(db, superadmin)
    page = client.get("/products").text
    for action in ("activate", "edit", "discard"):
        assert f'href="/products/{draft}/{action}"' in page
        assert f"/products/{active}/{action}" not in page


@pytest.mark.parametrize("role", ORG_ROLES)
def test_ordinary_users_see_no_edit_or_discard(
    db: psycopg.Connection, org_a: Org, superadmin: UUID, role: str
) -> None:
    active = seed(db, superadmin, "active", name=NAME)
    client, _ = sign_in(db, member(db, org_a, role))
    for url in ("/products", "/products?done=edited", "/products?done=discarded"):
        page = client.get(url).text
        assert NAME in page
        assert f"/products/{active}/" not in page
        assert products_web.DONE_MESSAGES["edited"] not in page
        assert products_web.DONE_MESSAGES["discarded"] not in page


def test_activation_page_points_to_edit(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client, _ = sign_in(db, superadmin)
    assert f'href="/products/{draft}/edit"' in client.get(f"/products/{draft}/activate").text


def test_edit_and_discard_pages_have_no_inline_script(
    db: psycopg.Connection, org_a: Org, superadmin: UUID
) -> None:
    draft = seed(db, superadmin, "draft", name=NAME)
    client, _ = sign_in(db, superadmin)
    for url in (f"/products/{draft}/edit", f"/products/{draft}/discard"):
        scripts = re.findall(r"<script([^>]*)>", client.get(url).text)
        assert scripts and all('src="/static/' in attributes for attributes in scripts)
