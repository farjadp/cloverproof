"""Superadmin page: create or join an organisation (/admin/organisations, migration 0029).

Only a human superadmin reaches it; the database functions check the same again. The role
offered is `org_admin` or `advisor`, never `agronomist` (rule 8). After creating or joining,
that organisation becomes the current one, so it can be used straight away.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from psycopg import errors

from cloverproof_app.auth import (
    ORG_COOKIE,
    Conn,
    CurrentUser,
    SettingsDep,
    UserDep,
    org_cookie_value,
    page_shell_org,
)
from cloverproof_app.nav import ROLE_LABELS, role_label
from cloverproof_app.repo import organisations
from cloverproof_app.repo.organisations import (
    JOIN_ROLES,
    NoSuchOrganisation,
    OrganisationNameTaken,
)
from cloverproof_app.web import render, set_cookie

router = APIRouter(dependencies=[Depends(page_shell_org)])

PAGE = "/admin/organisations"
MAX_NAME = 200
ONLY_SUPERADMIN = "Only a superadmin can manage organisations."
BAD_NAME = f"Enter a name of 1 to {MAX_NAME} characters, without line breaks."
NAME_TAKEN = "An organisation with this name already exists. Join it from the list instead."
BAD_ROLE = "Choose Org admin or Advisor. The Agronomist role cannot be taken here."
DONE = {
    "created": "Organisation created. You are its first member.",
    "joined": "You joined this organisation.",
    "already": "You already had this role here. Nothing changed.",
}


def require_superadmin(user: UserDep) -> CurrentUser:
    if not user.is_superadmin:
        raise HTTPException(403, ONLY_SUPERADMIN)
    return user


SuperadminDep = Annotated[CurrentUser, Depends(require_superadmin)]


def _page(
    request: Request, conn: Conn, user: CurrentUser, *, form: dict[str, str] | None = None,
    errors_: dict[str, str] | None = None, join_error: tuple[UUID, str] | None = None,
    done: str | None = None, status: int = 200,
) -> Response:  # fmt: skip
    return render(
        request,
        "admin_organisations.html",
        {
            "organisations": organisations.list_all(conn, user.id),
            "join_roles": JOIN_ROLES,
            "role_names": ROLE_LABELS,
            "role_label": role_label,
            "form": form or {"name": "", "role": "org_admin"},
            "errors": errors_ or {},
            "join_error": join_error,
            "done": done,
        },
        status,
    )


def _into_org(settings: SettingsDep, user: CurrentUser, org_id: UUID, done: str) -> Response:
    """Back to the page with this organisation as the current one."""
    response = RedirectResponse(f"{PAGE}?done={done}", status_code=303)
    value = org_cookie_value(settings, user, org_id)
    set_cookie(response, settings, ORG_COOKIE, value, settings.session_absolute_hours * 3600)
    return response


@router.get(PAGE)
def organisations_page(
    request: Request, conn: Conn, user: SuperadminDep, done: str = ""
) -> Response:
    return _page(request, conn, user, done=DONE.get(done))


@router.post(PAGE)
def organisation_create(
    request: Request,
    conn: Conn,
    settings: SettingsDep,
    user: SuperadminDep,
    name: Annotated[str, Form(max_length=1000)] = "",
    role: Annotated[str, Form(max_length=50)] = "",
) -> Response:
    form = {"name": name.strip(), "role": role}
    problems: dict[str, str] = {}
    if not 1 <= len(form["name"]) <= MAX_NAME or not form["name"].isprintable():
        problems["name"] = BAD_NAME
    if role not in JOIN_ROLES:
        problems["role"] = BAD_ROLE
    if problems:
        return _page(request, conn, user, form=form, errors_=problems, status=422)
    try:
        with conn.transaction():
            org_id = organisations.create(conn, actor_id=user.id, name=form["name"], role=role)
    except OrganisationNameTaken:
        return _page(request, conn, user, form=form, errors_={"name": NAME_TAKEN}, status=409)
    except errors.InsufficientPrivilege as error:  # e.g. the platform role was just removed
        raise HTTPException(403, ONLY_SUPERADMIN) from error
    return _into_org(settings, user, org_id, "created")


@router.post(PAGE + "/{org_id}/join")
def organisation_join(
    request: Request,
    conn: Conn,
    settings: SettingsDep,
    user: SuperadminDep,
    org_id: UUID,
    role: Annotated[str, Form(max_length=50)] = "",
) -> Response:
    if role not in JOIN_ROLES:
        return _page(request, conn, user, join_error=(org_id, BAD_ROLE), status=422)
    try:
        with conn.transaction():
            added = organisations.join(conn, actor_id=user.id, org_id=org_id, role=role)
    except NoSuchOrganisation as error:
        raise HTTPException(404, "No such organisation.") from error
    except errors.InsufficientPrivilege as error:
        raise HTTPException(403, ONLY_SUPERADMIN) from error
    return _into_org(settings, user, org_id, "joined" if added else "already")
