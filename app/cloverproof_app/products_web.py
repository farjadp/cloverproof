"""Product catalog page (`/products`, story S2-APP-09, GL-09: label facts, nothing commercial).

Any signed-in user reads active products. A human superadmin also sees drafts, adds drafts
and activates them. The same rules are enforced again by RLS and CHECK constraints in
migration 0027; a refusal there becomes a plain error page, never a 500.

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

from cloverproof_app.auth import (
    Conn,
    CurrentUser,
    OrgSelectionRequired,
    SettingsDep,
    UserDep,
    current_org,
)
from cloverproof_app.plan_web import form_data, not_found, text
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
DONE_MESSAGES = {
    "added": "Draft added. It stays hidden from other users until you activate it.",
    "activated": "Product activated. Every signed-in user can now see it.",
}

FORMS = {"granular": "Granular", "liquid": "Liquid"}
GRADES = {"n": "N", "p2o5": "P₂O₅", "k2o": "K₂O", "s": "S"}
NAME_MAX = 200
SOURCE_MAX = 500
DENSITY_MAX = Decimal("999.999")  # numeric(6,3)
GRADE_PLACES = 2  # numeric(5,2): more digits would be rounded silently
DENSITY_PLACES = 3
NUMBER = re.compile(r"-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
COUNTRY = re.compile(r"[A-Za-z]{2}")
FORM_DEFAULTS = {"country_code": "CA", "product_form": "granular"}


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


def plain_number(value: Decimal) -> str:
    """10.50 -> 10.5, 100.00 -> 100 (never scientific notation)."""
    return format(value.normalize(), "f")


def parse_decimal(raw: str) -> Decimal | None:
    value = raw.strip().replace(",", ".")
    if len(value) > 32 or NUMBER.fullmatch(value) is None:
        return None
    return Decimal(value)


def decimal_places(value: Decimal) -> int:
    exponent = value.normalize().as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else 0


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
    if COUNTRY.fullmatch(country) is None:
        errors["country_code"] = "Enter a two-letter country code, for example CA."
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
) -> Response:
    manage = may_manage(user)
    ctx = {
        "products": repo.list_products(conn, include_drafts=manage),
        "manage": manage,
        "values": values if values is not None else FORM_DEFAULTS,
        "errors": errors or {},
        "problem": problem,
        "done": done,
        "form_labels": FORMS,
        "grades": GRADES,
        "number": plain_number,
    }
    return render(request, "products.html", ctx, status)


@router.get("/products", dependencies=[Depends(page_org)])
def products_list(request: Request, conn: Conn, user: UserDep, done: str = "") -> Response:
    return catalog_page(request, conn, user, done=DONE_MESSAGES.get(done))


@router.post("/products", dependencies=[Depends(page_org)])
async def product_add(request: Request, conn: Conn, user: CatalogAdmin) -> Response:
    product, values, errors = validate(await form_data(request))
    if product is None:
        return catalog_page(request, conn, user, values=values, errors=errors, status=422)

    def refused(problem: str, status: int) -> Response:
        return catalog_page(request, conn, user, values=values, problem=problem, status=status)

    # The database allows such a draft, but it could never be activated: say so now.
    if repo.active_name_exists(conn, product.country_code, product.name):
        return refused(DUPLICATE_ON_ADD.format(country=product.country_code), 409)
    try:
        repo.add_draft(conn, product, created_by=user.id)
    except pg_errors.InsufficientPrivilege:
        return refused(DB_DENIED, 403)
    except (psycopg.IntegrityError, psycopg.DataError):
        return refused(DB_REFUSED, 422)
    return RedirectResponse("/products?done=added", status_code=303)


@router.post("/products/{product_id}/activate", dependencies=[Depends(page_org)])
def product_activate(
    request: Request, conn: Conn, user: CatalogAdmin, product_id: UUID
) -> Response:
    try:
        outcome = repo.activate(conn, product_id)
    except pg_errors.UniqueViolation:
        return catalog_page(request, conn, user, problem=DUPLICATE_ON_ACTIVATE, status=409)
    except pg_errors.InsufficientPrivilege:
        return catalog_page(request, conn, user, problem=DB_DENIED, status=403)
    except (psycopg.IntegrityError, psycopg.DataError):
        return catalog_page(request, conn, user, problem=DB_REFUSED, status=422)
    if outcome is repo.Activation.NOT_FOUND:
        raise not_found("Product")
    if outcome is repo.Activation.ALREADY_ACTIVE:
        return catalog_page(request, conn, user, problem=ALREADY_ACTIVE, status=409)
    return RedirectResponse("/products?done=activated", status_code=303)
