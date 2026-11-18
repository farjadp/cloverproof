"""Product catalog page (`/products`, story S2-APP-09, GL-09: label facts, nothing commercial).

Any signed-in user reads active products. A human superadmin also sees drafts, adds, edits,
discards and activates them; an active product never changes. The same rules are enforced
again by RLS and CHECK constraints in migrations 0027 and 0030; a refusal there becomes a
plain error page, never a 500.

Adding a product can start from a published fertilizer type (`product_presets`). A preset only
fills the form on a GET: the values come back through the normal POST and are validated like
typed ones, and activating needs a separate confirmation that the label was checked. Editing
such a draft keeps its "unconfirmed" note, so an edit cannot skip that confirmation.

The catalog is global, so no organisation is required: one is resolved only for the header.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from psycopg import errors as pg_errors

from cloverproof_app import product_presets as presets
from cloverproof_app.auth import (
    Conn,
    CurrentUser,
    OrgSelectionRequired,
    SettingsDep,
    UserDep,
    current_org,
)
from cloverproof_app.countries import COUNTRIES, DEFAULT_COUNTRY
from cloverproof_app.plan_web import form_data, not_found, text
from cloverproof_app.product_presets import (
    DENSITY_MAX,
    DENSITY_PLACES,
    GRADE_PLACES,
    NAME_MAX,
    SOURCE_MAX,
    UNCONFIRMED_SOURCE,
    Preset,
    decimal_places,
    plain_number,
)
from cloverproof_app.repo import products as repo
from cloverproof_app.web import render

router = APIRouter()

ONLY_SUPERADMIN = "Only a superadmin can change the product catalog."
DB_DENIED = "The database refused this change for your account. Nothing was saved."
DB_REFUSED = "The database refused these values. Nothing was saved. Check them and try again."
DUPLICATE_ON_ADD = (
    "An active product with this name already exists in {country}. Nothing was saved."
)
DUPLICATE_ON_ACTIVATE = (
    "An active product with this name already exists in this country. This product stays a draft."
)
ALREADY_ACTIVE = "This product is already active."
UNKNOWN_PRESET = "That fertilizer type is not in the list. Choose another or enter it manually."
CHECKED_SOURCE_MISSING = (
    "Enter the product label or data sheet you checked, with its edition or date."
)
LABEL_NOT_CONFIRMED = (
    "Tick the box to confirm you checked these values against the product label."
    " The product stays a draft."
)
KEEP_UNCONFIRMED = (
    f'Keep "{UNCONFIRMED_SOURCE}" in the source. You name the label you checked when you'
    " activate this draft."
)
ACTIVE_NOT_EDITABLE = "This product is active, so it can't be edited."
ACTIVE_NOT_DISCARDABLE = "This product is active, so it can't be discarded."
DRAFT_IN_USE = "This draft is used elsewhere, so it can't be discarded. Nothing was changed."
DONE_MESSAGES = {
    "added": "Saved as a draft. Only superadmins can see it.",
    "activated": "Product activated. Every signed-in user can now see it.",
    "edited": "Draft updated. It stays a draft until you check and activate it.",
    "discarded": "Draft discarded.",
}
# Notices about drafts: people who can't see drafts never get them.
DRAFT_ONLY_MESSAGES = {"edited", "discarded"}

FORMS = {"granular": "Granular", "liquid": "Liquid"}
GRADES = {"n": "N", "p2o5": "P₂O₅", "k2o": "K₂O", "s": "S"}
NUMBER = re.compile(r"-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
COUNTRY = re.compile(r"[A-Za-z]{2}")
FORM_DEFAULTS = {"country_code": DEFAULT_COUNTRY, "product_form": "granular"}
PRESET_KEY_MAX = 100


def page_org(request: Request, user: UserDep, conn: Conn, settings: SettingsDep) -> None:
    """Fill the header when an organisation is known. Never required here: a superadmin may
    have no membership, and someone with several organisations need not pick one."""
    try:
        current_org(request, user, conn, settings)
    except OrgSelectionRequired:
        return
    except HTTPException as error:
        if error.status_code != 403:
            raise


def may_manage(user: CurrentUser) -> bool:
    return user.is_superadmin


def require_catalog_admin(user: UserDep) -> CurrentUser:
    if not may_manage(user):
        raise HTTPException(403, ONLY_SUPERADMIN)
    return user


CatalogAdmin = Annotated[CurrentUser, Depends(require_catalog_admin)]


def parse_decimal(raw: str) -> Decimal | None:
    value = raw.strip().replace(",", ".")
    if len(value) > 32 or NUMBER.fullmatch(value) is None:
        return None
    return Decimal(value)


def clean_text(
    form: Any, name: str, limit: int, label: str, errors: dict[str, str], missing: str
) -> str:
    value = text(form, name, limit + 100).strip()
    if not value:
        errors[name] = missing
    elif len(value) > limit:
        errors[name] = f"{label} is too long ({limit} characters at most)."
    elif "\x00" in value:
        errors[name] = f"{label} contains a character that cannot be stored."
    return value


def validate(form: Any) -> tuple[repo.NewProduct | None, dict[str, str], dict[str, str]]:
    """Form -> (product or None, values to show again, errors by field)."""
    errors: dict[str, str] = {}
    values: dict[str, str] = {}

    country = text(form, "country_code", 10).strip()
    values["country_code"] = country
    # The pattern comes first: "ß".upper() is "SS", which is a real code.
    if COUNTRY.fullmatch(country) is None or country.upper() not in COUNTRIES:
        errors["country_code"] = "Choose a country from the list."
    country = country.upper()

    values["name"] = clean_text(
        form, "name", NAME_MAX, "Product name", errors, "Enter the product name."
    )

    grades: dict[str, Decimal] = {}
    for key, label in GRADES.items():
        raw = text(form, key, 40).strip()
        values[key] = raw
        value = parse_decimal(raw)
        if not raw:
            errors[key] = f"Enter the {label} percentage from the label (0 if none)."
        elif value is None:
            errors[key] = f"{label} must be a number."
        elif not 0 <= value <= 100:
            errors[key] = f"{label} must be between 0 and 100."
        elif decimal_places(value) > GRADE_PLACES:
            errors[key] = f"{label} can have at most {GRADE_PLACES} decimal places."
        else:
            grades[key] = value
    if len(grades) == len(GRADES) and (total := sum(grades.values(), Decimal(0))) > 100:
        errors["grade"] = (
            f"The grade adds up to {plain_number(total)}%. N + P₂O₅ + K₂O + S cannot exceed 100%."
        )

    product_form = text(form, "product_form", 20).strip()
    values["product_form"] = product_form
    if product_form not in FORMS:
        errors["product_form"] = "Choose granular or liquid."

    raw_density = text(form, "density_kg_per_l", 40).strip()
    values["density_kg_per_l"] = raw_density
    density = parse_decimal(raw_density)
    if product_form == "granular" and raw_density:
        errors["density_kg_per_l"] = "Leave density empty for a granular product."
    elif product_form == "liquid":
        if not raw_density:
            errors["density_kg_per_l"] = "Enter the density from the label for a liquid product."
        elif density is None:
            errors["density_kg_per_l"] = "Density must be a number."
        elif not 0 < density <= DENSITY_MAX:
            errors["density_kg_per_l"] = f"Density must be above 0 and at most {DENSITY_MAX} kg/L."
        elif decimal_places(density) > DENSITY_PLACES:
            errors["density_kg_per_l"] = (
                f"Density can have at most {DENSITY_PLACES} decimal places."
            )

    values["grade_source"] = clean_text(
        form,
        "grade_source",
        SOURCE_MAX,
        "Source",
        errors,
        "Enter where the grade comes from (label or data sheet, with edition or date).",
    )

    if errors:
        return None, values, errors
    product = repo.NewProduct(
        country_code=country,
        name=values["name"],
        n=grades["n"],
        p2o5=grades["p2o5"],
        k2o=grades["k2o"],
        s=grades["s"],
        form=product_form,
        density_kg_per_l=density if product_form == "liquid" else None,
        grade_source=values["grade_source"],
    )
    return product, values, {}


def preset_context(query: str, chosen: Preset | None) -> dict[str, Any]:
    groups = presets.search(query)
    return {
        "preset_groups": groups,
        "preset_count": sum(len(items) for _, items in groups),
        "preset_query": query,
        "preset": chosen,
    }


def catalog_page(
    request: Request,
    conn: psycopg.Connection,
    user: CurrentUser,
    *,
    values: dict[str, str] | None = None,
    errors: dict[str, str] | None = None,
    problem: str | None = None,
    done: str | None = None,
    status: int = 200,
    open_form: bool = False,
    preset: Preset | None = None,
    query: str = "",
    new_draft: str = "",
) -> Response:
    manage = may_manage(user)
    products = repo.list_products(conn, include_drafts=manage)
    ctx = {
        "products": products,
        "manage": manage,
        # The form opens on request, when it has content to show, or when nothing is listed.
        "show_form": manage and (open_form or values is not None or not products),
        "values": values if values is not None else FORM_DEFAULTS,
        "errors": errors or {},
        "problem": problem,
        "done": done,
        "new_draft": next(
            (p for p in products if str(p.id) == new_draft and p.status == "draft"), None
        ),
        "form_labels": FORMS,
        "grades": GRADES,
        "countries": COUNTRIES,
        "number": plain_number,
        **preset_context(query, preset),
    }
    return render(request, "products.html", ctx, status)


@router.get("/products", dependencies=[Depends(page_org)])
def products_list(
    request: Request,
    conn: Conn,
    user: UserDep,
    done: str = "",
    add: str = "",
    preset: str = "",
    q: str = "",
    draft: str = "",
) -> Response:
    message = DONE_MESSAGES.get(done)
    if not may_manage(user):  # Readers get the catalog, whatever the address asks for.
        shown = None if done in DRAFT_ONLY_MESSAGES else message
        return catalog_page(request, conn, user, done=shown)
    chosen = presets.BY_KEY.get(preset)
    return catalog_page(
        request,
        conn,
        user,
        values={**FORM_DEFAULTS, **chosen.form_values()} if chosen else None,
        problem=UNKNOWN_PRESET if preset and chosen is None else None,
        done=message,
        status=404 if preset and chosen is None else 200,
        open_form=bool(add or preset or q),
        preset=chosen,
        query=q,
        new_draft=draft if done == "added" else "",
    )


@router.get("/products/presets")
def preset_results(request: Request, _: CatalogAdmin, q: str = "", preset: str = "") -> Response:
    """The picker's result list, for htmx. The same search also works through GET /products."""
    context = preset_context(q, presets.BY_KEY.get(preset))
    return render(request, "_preset_results.html", {**context, "swap": True})


@router.post("/products", dependencies=[Depends(page_org)])
async def product_add(request: Request, conn: Conn, user: CatalogAdmin) -> Response:
    form = await form_data(request)
    product, values, errors = validate(form)
    # Only for the notice and hints: every saved value comes from the submitted fields.
    chosen = presets.BY_KEY.get(text(form, "preset", PRESET_KEY_MAX))
    if product is None:
        return catalog_page(
            request, conn, user, values=values, errors=errors, status=422, preset=chosen
        )

    def refused(problem: str, status: int) -> Response:
        return catalog_page(
            request, conn, user, values=values, problem=problem, status=status, preset=chosen
        )

    # The database allows such a draft, but it could never be activated: say so now.
    if repo.active_name_exists(conn, product.country_code, product.name):
        return refused(DUPLICATE_ON_ADD.format(country=product.country_code), 409)
    try:
        draft_id = repo.add_draft(conn, product, created_by=user.id)
    except pg_errors.InsufficientPrivilege:
        return refused(DB_DENIED, 403)
    except (psycopg.IntegrityError, psycopg.DataError):
        return refused(DB_REFUSED, 422)
    return RedirectResponse(f"/products?done=added&draft={draft_id}", status_code=303)


def is_unconfirmed(source: str) -> bool:
    return UNCONFIRMED_SOURCE in source.lower()


def draft_or_refusal(
    request: Request,
    conn: psycopg.Connection,
    user: CurrentUser,
    product_id: UUID,
    active_message: str,
) -> repo.Product | Response:
    """The draft to work on, or the page that says why not. 404 also covers a draft RLS hides."""
    product = repo.get_product(conn, product_id)
    if product is None:
        raise not_found("Product")
    if product.status != "draft":
        return catalog_page(request, conn, user, problem=active_message, status=409)
    return product


def form_values_of(product: repo.Product) -> dict[str, str]:
    density = product.density_kg_per_l
    return {
        "country_code": product.country_code,
        "name": product.name,
        "n": plain_number(product.n),
        "p2o5": plain_number(product.p2o5),
        "k2o": plain_number(product.k2o),
        "s": plain_number(product.s),
        "product_form": product.form,
        "density_kg_per_l": "" if density is None else plain_number(density),
        "grade_source": product.grade_source,
    }


def edit_page(
    request: Request,
    product: repo.Product,
    values: dict[str, str],
    *,
    errors: dict[str, str] | None = None,
    problem: str | None = None,
    status: int = 200,
) -> Response:
    ctx = {
        "product": product,
        "values": values,
        "errors": errors or {},
        "problem": problem,
        "source_unconfirmed": is_unconfirmed(product.grade_source),
        "unconfirmed_note": UNCONFIRMED_SOURCE,
        "form_labels": FORMS,
        "grades": GRADES,
        "countries": COUNTRIES,
    }
    return render(request, "product_edit.html", ctx, status)


@router.get("/products/{product_id}/edit", dependencies=[Depends(page_org)])
def product_edit_form(
    request: Request, conn: Conn, user: CatalogAdmin, product_id: UUID
) -> Response:
    product = draft_or_refusal(request, conn, user, product_id, ACTIVE_NOT_EDITABLE)
    if isinstance(product, Response):
        return product
    return edit_page(request, product, form_values_of(product))


@router.post("/products/{product_id}/edit", dependencies=[Depends(page_org)])
async def product_edit(
    request: Request, conn: Conn, user: CatalogAdmin, product_id: UUID
) -> Response:
    form = await form_data(request)
    draft = draft_or_refusal(request, conn, user, product_id, ACTIVE_NOT_EDITABLE)
    if isinstance(draft, Response):
        return draft
    product, values, errors = validate(form)
    # Without this, an edit could turn a published reference into a confirmed-looking source
    # and activation would no longer ask which label was checked.
    if (
        "grade_source" not in errors
        and is_unconfirmed(draft.grade_source)
        and not is_unconfirmed(values["grade_source"])
    ):
        errors["grade_source"] = KEEP_UNCONFIRMED
    if product is None or errors:
        return edit_page(request, draft, values, errors=errors, status=422)

    def refused(problem: str, status: int) -> Response:
        return edit_page(request, draft, values, problem=problem, status=status)

    if repo.active_name_exists(conn, product.country_code, product.name):
        return refused(DUPLICATE_ON_ADD.format(country=product.country_code), 409)
    try:
        outcome = repo.update_draft(conn, product_id, product)
    except pg_errors.InsufficientPrivilege:
        return refused(DB_DENIED, 403)
    except (psycopg.IntegrityError, psycopg.DataError):
        return refused(DB_REFUSED, 422)
    if outcome is repo.DraftChange.NOT_FOUND:
        raise not_found("Product")
    if outcome is repo.DraftChange.NOT_A_DRAFT:
        return catalog_page(request, conn, user, problem=ACTIVE_NOT_EDITABLE, status=409)
    if outcome is repo.DraftChange.REFUSED:
        return refused(DB_DENIED, 403)
    return RedirectResponse("/products?done=edited", status_code=303)


def discard_page(
    request: Request, product: repo.Product, *, problem: str | None = None, status: int = 200
) -> Response:
    ctx = {
        "product": product,
        "problem": problem,
        "form_labels": FORMS,
        "country": COUNTRIES.get(product.country_code, product.country_code),
        "number": plain_number,
    }
    return render(request, "product_discard.html", ctx, status)


@router.get("/products/{product_id}/discard", dependencies=[Depends(page_org)])
def product_discard_form(
    request: Request, conn: Conn, user: CatalogAdmin, product_id: UUID
) -> Response:
    product = draft_or_refusal(request, conn, user, product_id, ACTIVE_NOT_DISCARDABLE)
    if isinstance(product, Response):
        return product
    return discard_page(request, product)


@router.post("/products/{product_id}/discard", dependencies=[Depends(page_org)])
def product_discard(request: Request, conn: Conn, user: CatalogAdmin, product_id: UUID) -> Response:
    draft = draft_or_refusal(request, conn, user, product_id, ACTIVE_NOT_DISCARDABLE)
    if isinstance(draft, Response):
        return draft
    try:
        outcome = repo.delete_draft(conn, product_id)
    except pg_errors.ForeignKeyViolation:
        return discard_page(request, draft, problem=DRAFT_IN_USE, status=409)
    except pg_errors.InsufficientPrivilege:
        return discard_page(request, draft, problem=DB_DENIED, status=403)
    if outcome is repo.DraftChange.NOT_FOUND:
        raise not_found("Product")
    if outcome is repo.DraftChange.NOT_A_DRAFT:
        return catalog_page(request, conn, user, problem=ACTIVE_NOT_DISCARDABLE, status=409)
    if outcome is repo.DraftChange.REFUSED:
        return discard_page(request, draft, problem=DB_DENIED, status=403)
    return RedirectResponse("/products?done=discarded", status_code=303)


def activation_page(
    request: Request,
    product: repo.Product,
    *,
    errors: dict[str, str] | None = None,
    checked_source: str = "",
    problem: str | None = None,
    status: int = 200,
) -> Response:
    ctx = {
        "product": product,
        "errors": errors or {},
        "needs_checked_source": is_unconfirmed(product.grade_source),
        "checked_source": checked_source,
        "problem": problem,
        "form_labels": FORMS,
        "grades": GRADES,
        "country": COUNTRIES.get(product.country_code, product.country_code),
        "number": plain_number,
    }
    return render(request, "product_activate.html", ctx, status)


@router.get("/products/{product_id}/activate", dependencies=[Depends(page_org)])
def product_activate_form(
    request: Request, conn: Conn, user: CatalogAdmin, product_id: UUID
) -> Response:
    product = repo.get_product(conn, product_id)
    if product is None:
        raise not_found("Product")
    if product.status != "draft":
        return catalog_page(request, conn, user, problem=ALREADY_ACTIVE, status=409)
    return activation_page(request, product)


@router.post("/products/{product_id}/activate", dependencies=[Depends(page_org)])
async def product_activate(
    request: Request, conn: Conn, user: CatalogAdmin, product_id: UUID
) -> Response:
    form = await form_data(request)
    product = repo.get_product(conn, product_id)
    if product is None:
        raise not_found("Product")
    if product.status != "draft":
        return catalog_page(request, conn, user, problem=ALREADY_ACTIVE, status=409)
    errors: dict[str, str] = {}
    checked_source = ""
    if is_unconfirmed(product.grade_source):
        checked_source = clean_text(
            form, "grade_source", SOURCE_MAX, "Source", errors, CHECKED_SOURCE_MISSING
        )
        if is_unconfirmed(checked_source):
            errors["grade_source"] = CHECKED_SOURCE_MISSING
    if text(form, "label_checked", 10) != "yes":
        errors["label_checked"] = LABEL_NOT_CONFIRMED
    if errors:
        return activation_page(
            request, product, errors=errors, checked_source=checked_source, status=422
        )

    def refused(problem: str, status: int) -> Response:
        return activation_page(
            request, product, checked_source=checked_source, problem=problem, status=status
        )

    try:
        outcome = repo.activate(conn, product_id, grade_source=checked_source or None)
    except pg_errors.UniqueViolation:
        return refused(DUPLICATE_ON_ACTIVATE, 409)
    except pg_errors.InsufficientPrivilege:
        return refused(DB_DENIED, 403)
    except (psycopg.IntegrityError, psycopg.DataError):
        return refused(DB_REFUSED, 422)
    if outcome is repo.Activation.NOT_FOUND:
        raise not_found("Product")
    if outcome is repo.Activation.ALREADY_ACTIVE:
        return catalog_page(request, conn, user, problem=ALREADY_ACTIVE, status=409)
    return RedirectResponse("/products?done=activated", status_code=303)
