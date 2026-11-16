"""Plan flow: farmers -> farms/fields -> new plan -> engine -> suggestion -> edit -> review.

Every query goes through the org-scoped repo layer with the org from the session; an id
from another organisation is a 404. Role checks are server-side; the database triggers
enforce the same review gate a second time.
"""

from __future__ import annotations

import math
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from cloverproof_app import planning, timer
from cloverproof_app.auth import INTERNAL_ROLES, Conn, OrgContext, SettingsDep, require_org_role
from cloverproof_app.repo import farms, plans
from cloverproof_app.web import render
from cloverproof_engine.pack import Pack

router = APIRouter()

InternalOrg = Annotated[OrgContext, Depends(require_org_role(*INTERNAL_ROLES))]
ONLY_AGRONOMIST = "Only the agronomist can review plans."
ALREADY_REVIEWED = "This plan version is already reviewed. Nothing was saved."
STALE_VERSION = "A newer version of this plan exists. Reload the plan; nothing was saved."
TIMER_MISSING = "The plan timer is missing. Open the plan again, then review. Nothing was saved."
FINAL_DECISIONS = frozenset({"approve", "reject"})
HUMAN_DECISIONS = frozenset({"approve", "edit", "reject"})  # not ai_reviewed (D4)
DECISION_LABELS = {"approve": "Approved", "reject": "Rejected", "edit": "Edited"}

STATUS_LABELS = {
    "draft": "Draft",
    "in_review": "In review",
    "approved": "Approved",
    "rejected": "Rejected",
}


def pack_of(request: Request) -> Pack:
    return request.app.state.pack


def is_agronomist(context: OrgContext) -> bool:
    """A human agronomist (B1/D4): a service account never edits, approves or rejects."""
    return context.user.is_human and "agronomist" in context.roles


def require_agronomist(context: OrgContext) -> None:
    if not is_agronomist(context):
        raise HTTPException(403, ONLY_AGRONOMIST)


def not_found(what: str) -> HTTPException:
    return HTTPException(404, f"{what} not found.")


async def form_data(request: Request) -> Any:
    return await request.form()  # cached by Starlette (csrf_guard read it already)


def text(form: Any, name: str, limit: int = 4000) -> str:
    value = form.get(name)
    return value[:limit] if isinstance(value, str) else ""


# --- farmers --------------------------------------------------------------------------


@router.get("/")
@router.get("/farmers")
def farmers_home(request: Request, conn: Conn, context: InternalOrg, q: str = "") -> Response:
    org = context.org.id
    rows = farms.overview(conn, org, q)
    fields_by_farm: dict[UUID, list[farms.FieldRow]] = {}
    for f in farms.fields_of_org(conn, org):
        fields_by_farm.setdefault(f.farm_id, []).append(f)
    last = plans.last_plan_per_field(conn, org)
    lines = []
    for row in rows:
        farm_fields = fields_by_farm.get(row.farm_id, []) if row.farm_id else []
        latest = max(
            (last[f.id] for f in farm_fields if f.id in last),
            key=lambda s: s.updated_at,
            default=None,
        )
        lines.append({"row": row, "fields": farm_fields, "last": latest})
    name = "_farmer_rows.html" if request.headers.get("HX-Request") else "farmers.html"
    return render(request, name, {"lines": lines, "q": q, "status_labels": STATUS_LABELS})


@router.get("/farmers/new")
def farmer_new(request: Request, context: InternalOrg) -> Response:
    return render(request, "farmer_new.html", {"values": {}, "errors": {}})


@router.post("/farmers")
async def farmer_create(request: Request, conn: Conn, context: InternalOrg) -> Response:
    form = await form_data(request)
    name = text(form, "display_name", 300).strip()
    notes = text(form, "notes").strip() or None
    errors = {}
    if not name:
        errors["display_name"] = "Enter the farmer's name."
    elif len(name) > 200:
        errors["display_name"] = "Name is too long (200 characters at most)."
    if errors:
        values = {"display_name": name, "notes": notes or ""}
        return render(request, "farmer_new.html", {"values": values, "errors": errors}, 422)
    farmer_id = farms.create_farmer(conn, context.org.id, display_name=name, notes=notes)
    return RedirectResponse(f"/farmers/{farmer_id}", status_code=303)


def farmer_page(request: Request, conn: Conn, context: OrgContext, farmer_id: UUID,
                errors: dict[str, str] | None = None, values: dict[str, str] | None = None,
                status: int = 200) -> Response:  # fmt: skip
    farmer = farms.get_farmer(conn, context.org.id, farmer_id)
    if farmer is None:
        raise not_found("Farmer")
    ctx = {
        "farmer": farmer,
        "farms": farms.list_farms(conn, context.org.id, farmer_id),
        "fields": farms.fields_of_farmer(conn, context.org.id, farmer_id),
        "errors": errors or {},
        "values": values or {},
    }
    return render(request, "farmer.html", ctx, status)


@router.get("/farmers/{farmer_id}")
def farmer_detail(request: Request, conn: Conn, context: InternalOrg, farmer_id: UUID) -> Response:
    return farmer_page(request, conn, context, farmer_id)


@router.post("/farmers/{farmer_id}/farms")
async def farm_create(request: Request, conn: Conn, context: InternalOrg,
                      farmer_id: UUID) -> Response:  # fmt: skip
    if farms.get_farmer(conn, context.org.id, farmer_id) is None:
        raise not_found("Farmer")
    form = await form_data(request)
    name = text(form, "farm_name", 300).strip()
    if not name or len(name) > 200:
        error = "Enter the farm name." if not name else "Farm name is too long (200 at most)."
        return farmer_page(request, conn, context, farmer_id, {"farm_name": error},
                           {"farm_name": name}, 422)  # fmt: skip
    farms.create_farm(conn, context.org.id, farmer_id=farmer_id, name=name)
    return RedirectResponse(f"/farmers/{farmer_id}", status_code=303)


@router.post("/farmers/{farmer_id}/fields")
async def field_create(request: Request, conn: Conn, context: InternalOrg,
                       farmer_id: UUID) -> Response:  # fmt: skip
    org = context.org.id
    if farms.get_farmer(conn, org, farmer_id) is None:
        raise not_found("Farmer")
    form = await form_data(request)
    values = {k: text(form, k, 300).strip() for k in ("farm_id", "field_name", "area_ha")}
    errors: dict[str, str] = {}
    own_farms = {str(f.id) for f in farms.list_farms(conn, org, farmer_id)}
    if values["farm_id"] not in own_farms:
        errors["farm_id"] = "Choose the farm this field belongs to."
    if not values["field_name"] or len(values["field_name"]) > 200:
        errors["field_name"] = "Enter the field name (200 characters at most)."
    area = None
    try:
        area = float(values["area_ha"].replace(",", ".")) if values["area_ha"] else None
    except ValueError:
        area = None
    if area is None or not math.isfinite(area) or area <= 0:
        errors["area_ha"] = "Enter the area in ha, greater than zero."
    if errors:
        return farmer_page(request, conn, context, farmer_id, errors, values, 422)
    assert area is not None
    field_id = farms.create_field(conn, org, farm_id=UUID(values["farm_id"]),
                                  name=values["field_name"])  # fmt: skip
    season = farms.season_for(conn, org, date.today())
    farms.set_manual_area(conn, org, field_id=field_id, season_id=season, area_ha=area,
                          user_id=context.user.id)  # fmt: skip
    return RedirectResponse(f"/fields/{field_id}", status_code=303)


# --- field ----------------------------------------------------------------------------


def load_field(conn: Conn, context: OrgContext, field_id: UUID) -> farms.FieldRow:
    row = farms.get_field(conn, context.org.id, field_id)
    if row is None:
        raise not_found("Field")
    return row


@router.get("/fields/{field_id}")
def field_detail(request: Request, conn: Conn, context: InternalOrg, field_id: UUID) -> Response:
    row = load_field(conn, context, field_id)
    soil = plans.latest_soil_test(conn, context.org.id, field_id)
    ctx = {
        "field": row,
        "soil": soil,
        "soil_values": plans.soil_test_values(conn, context.org.id, soil.id) if soil else [],
        "plans": plans.plans_for_field(conn, context.org.id, field_id),
        "status_labels": STATUS_LABELS,
        "planning": planning,
    }
    return render(request, "field.html", ctx)


# --- new plan -------------------------------------------------------------------------


def plan_form_page(request: Request, context: OrgContext, settings: SettingsDep,
                   field_row: farms.FieldRow, form: planning.PlanForm, errors: dict[str, str],
                   started: str, status: int = 200) -> Response:  # fmt: skip
    while len(form.values) < planning.VALUE_ROWS:
        form.values.append(planning.ValueRow())
    ctx = {
        "field": field_row,
        "f": form,
        "errors": errors,
        "started": started,
        "previous_crops": planning.previous_crop_choices(pack_of(request)),
        "planning": planning,
    }
    return render(request, "plan_new.html", ctx, status)


@router.get("/fields/{field_id}/plans/new")
def plan_new(request: Request, conn: Conn, context: InternalOrg, settings: SettingsDep,
             field_id: UUID) -> Response:  # fmt: skip
    row = load_field(conn, context, field_id)
    form = planning.PlanForm(
        area_ha=f"{row.area_ha.normalize():f}" if row.area_ha is not None else "",
        plan_date=date.today().isoformat(),
    )
    started = timer.new_form_token(settings, context.user, field_id)
    return plan_form_page(request, context, settings, row, form, {}, started)


@router.get("/plans/value-row")
def value_row(request: Request, context: InternalOrg, i: int = 0) -> Response:
    ctx = {
        "i": max(0, min(i, 50)),
        "row": planning.ValueRow(),
        "errors": {},
        "planning": planning,
        "oob": True,
    }
    return render(request, "_value_row.html", ctx)


@router.post("/fields/{field_id}/plans")
async def plan_create(request: Request, conn: Conn, context: InternalOrg, settings: SettingsDep,
                      field_id: UUID) -> Response:  # fmt: skip
    org = context.org.id
    row = load_field(conn, context, field_id)
    raw = await form_data(request)
    form = planning.PlanForm.from_form(raw, raw.getlist)
    started_raw = text(raw, "started", 200)
    parsed, errors = planning.validate_plan_form(form, pack_of(request))
    if parsed is None:
        return plan_form_page(request, context, settings, row, form, errors, started_raw, 422)

    inputs = parsed.inputs
    result = planning.run_engine(inputs, pack_of(request))
    season = farms.season_for(conn, org, inputs.plan_date)
    farms.set_manual_area(conn, org, field_id=field_id, season_id=season,
                          area_ha=inputs.area_ha, user_id=context.user.id)  # fmt: skip
    soil_id = None
    if inputs.soil_test is not None:
        soil_id = plans.create_soil_test(conn, org, field_id=field_id, soil=inputs.soil_test,
                                         user_id=context.user.id)  # fmt: skip
    plan_id = plans.create_crop_plan(
        conn, org, field_id=field_id, season_id=season, crop=inputs.crop.value,
        target_yield_t_ha=inputs.target_yield_t_ha, previous_crop=inputs.previous_crop,
        plan_date=inputs.plan_date, soil_test_id=soil_id, user_id=context.user.id,
    )  # fmt: skip
    plans.insert_recommendation(conn, org, crop_plan_id=plan_id, result=result,
                                user_id=context.user.id)  # fmt: skip
    response = RedirectResponse(f"/plans/{plan_id}", status_code=303)
    started = timer.form_start(settings, context.user, field_id, started_raw)
    timer.set_plan_start(response, settings, context.user, plan_id, started)
    return response


# --- suggestion / edit / review --------------------------------------------------------


@dataclass
class PlanView:
    plan: plans.PlanRow
    field: farms.FieldRow
    versions: list[plans.RecRow]
    reviews: list[plans.ReviewRow]
    soil: plans.SoilTestRow | None
    latest: plans.RecRow
    doc: dict[str, Any]
    number: int
    status: str
    final_review: plans.ReviewRow | None
    diff: dict[str, Any] | None
    edits: list[dict[str, Any]] = field(default_factory=list)

    @property
    def read_only(self) -> bool:
        return self.final_review is not None

    @property
    def ai_reviews(self) -> list[plans.ReviewRow]:
        """AI reviews of the version on screen (D4): shown, never an approval."""
        return [
            r for r in self.reviews
            if r.decision == "ai_reviewed" and r.recommendation_id == self.latest.id
        ]  # fmt: skip

    @property
    def last_review_at(self) -> datetime | None:
        """When the agronomist last recorded a review on this plan (F4 timer restart)."""
        return max((r.created_at for r in self.reviews if r.decision in HUMAN_DECISIONS),
                   default=None)  # fmt: skip


def by_lineage(rows: list[plans.RecRow]) -> list[plans.RecRow]:
    """Versions in edit order: by depth in the parent chain (timestamps can tie)."""
    parent = {r.id: r.parent_id for r in rows}

    def depth(rec_id: UUID) -> int:
        d = 0
        while parent.get(rec_id):
            rec_id = parent[rec_id]  # type: ignore[assignment]
            d += 1
        return d

    return sorted(rows, key=lambda r: (depth(r.id), r.created_at))


def load_plan(conn: Conn, context: OrgContext, plan_id: UUID) -> PlanView:
    org = context.org.id
    plan = plans.get_plan(conn, org, plan_id)
    if plan is None:
        raise not_found("Plan")
    versions = by_lineage(plans.recommendations(conn, org, plan_id))
    if not versions:
        raise HTTPException(409, "This plan has no engine result yet.")
    parents = {v.parent_id for v in versions if v.parent_id}
    leaves = [v for v in versions if v.id not in parents]
    latest = leaves[-1]
    reviews = plans.reviews(conn, org, plan_id)
    final = next(
        (r for r in reviews if r.recommendation_id == latest.id and r.decision in FINAL_DECISIONS),
        None,
    )
    status = "in_review" if final is None else ("approved" if final.decision == "approve"
                                                else "rejected")  # fmt: skip
    field_row = farms.get_field(conn, org, plan.field_id)
    assert field_row is not None
    soil = plans.get_soil_test(conn, org, plan.soil_test_id) if plan.soil_test_id else None
    view = PlanView(
        plan=plan, field=field_row, versions=versions, reviews=reviews, soil=soil,
        latest=latest, doc=latest.result, number=versions.index(latest) + 1, status=status,
        final_review=final, diff=plans.diff_row(conn, org, latest.id),
    )  # fmt: skip
    view.edits = [
        {"number": versions.index(v) + 1, "rec": v} for v in versions if v.kind == "agronomist"
    ]
    return view


def comparison(view: PlanView) -> list[dict[str, Any]]:
    """Engine vs final rows for every number that differs (both documents from the view)."""
    if view.diff is None or view.diff["edit_depth"] == 0:
        return []
    engine, final = view.diff["engine_result"]["nitrogen"], view.diff["final_result"]["nitrogen"]
    rows = [("N rate", engine["rate"], final["rate"]), ("N total", engine["total"], final["total"])]
    for e, f in zip(engine["splits"], final["splits"], strict=False):
        rows.append((f"{e['stage_label']}: rate", e["rate"], f["rate"]))
    return [
        {"item": item, "engine": e, "final": f}
        for item, e, f in rows
        if not math.isclose(e["value"], f["value"], abs_tol=1e-9)
    ]


def plan_page(request: Request, conn: Conn, context: OrgContext, settings: SettingsDep,
              plan_id: UUID, *, errors: dict[str, str] | None = None,
              values: dict[str, str] | None = None, status: int = 200) -> Response:  # fmt: skip
    view = load_plan(conn, context, plan_id)
    started = timer.plan_start(request, settings, context.user, plan_id)
    new_start = None
    if started is None and not view.read_only:
        new_start = started = int(time.time())
    minutes = shown_minutes(view, settings, started)
    ctx = {
        "v": view,
        "doc": view.doc,
        **limits_context(request, view.doc, view.doc["nitrogen"]["rate"]["value"]),
        "comparison": comparison(view),
        "minutes": minutes,
        "can_review": is_agronomist(context),
        "decision_labels": DECISION_LABELS,
        "errors": errors or {},
        "values": values or {},
        "status_labels": STATUS_LABELS,
        "previous_crop_label": dict(planning.previous_crop_choices(pack_of(request))).get(
            view.plan.previous_crop, view.plan.previous_crop
        ),
        "planning": planning,
    }
    response = render(request, "plan.html", ctx, status)
    if new_start is not None:
        timer.set_plan_start(response, settings, context.user, plan_id, new_start)
    return response


@router.get("/plans/{plan_id}")
def plan_detail(request: Request, conn: Conn, context: InternalOrg, settings: SettingsDep,
                plan_id: UUID) -> Response:  # fmt: skip
    return plan_page(request, conn, context, settings, plan_id)


@router.get("/plans/{plan_id}/timer")
def plan_timer(request: Request, conn: Conn, context: InternalOrg, settings: SettingsDep,
               plan_id: UUID) -> Response:  # fmt: skip
    view = load_plan(conn, context, plan_id)
    started = timer.plan_start(request, settings, context.user, plan_id)
    minutes = shown_minutes(view, settings, started)
    return render(request, "_timer.html", {"v": view, "minutes": minutes})


def shown_minutes(view: PlanView, settings: SettingsDep, started: int | None) -> int | None:
    """What the next review would record (same rule as the stored value)."""
    if started is None:
        return None
    return timer.review_minutes(started, view.last_review_at,
                                cap=settings.review_minutes_cap).minutes  # fmt: skip


def limits_context(request: Request, doc: dict[str, Any], rate: Any) -> dict[str, Any]:
    """Pack N-rate limits (from the loaded pack) and whether `rate` is outside them."""
    low, high = planning.n_rate_limits(pack_of(request), doc["crop"])
    try:
        value = planning.parse_number(str(rate))
    except ValueError:
        value = None
    outside = value is not None and planning.outside_limits(value, (low, high))
    return {"n_limits": (low, high), "n_outside_limits": outside}


def edit_page(request: Request, view: PlanView, errors: dict[str, str],
              values: dict[str, Any], status: int = 200) -> Response:  # fmt: skip
    # The notice follows the number on screen: the current version, or what was just typed.
    rate = values.get("n_rate") if errors else view.doc["nitrogen"]["rate"]["value"]
    ctx = {"v": view, "doc": view.doc, "errors": errors, "values": values,
           **limits_context(request, view.doc, rate)}  # fmt: skip
    return render(request, "plan_edit.html", ctx, status)


@router.get("/plans/{plan_id}/edit")
def plan_edit(request: Request, conn: Conn, context: InternalOrg, plan_id: UUID) -> Response:
    require_agronomist(context)
    view = load_plan(conn, context, plan_id)
    if view.read_only:
        raise HTTPException(409, ALREADY_REVIEWED)
    nitrogen = view.doc["nitrogen"]
    values = {
        "n_rate": f"{nitrogen['rate']['value']:g}",
        "splits": [f"{s['rate']['value']:g}" for s in nitrogen["splits"]],
        "reason": "",
    }
    return edit_page(request, view, {}, values)


def reviewed_minutes(request: Request, settings: SettingsDep, context: OrgContext,
                     view: PlanView) -> timer.ReviewMinutes:  # fmt: skip
    """F4: minutes since the previous review on this plan (or since open), capped."""
    started = timer.plan_start(request, settings, context.user, view.plan.id)
    if started is None:
        raise HTTPException(400, TIMER_MISSING)
    return timer.review_minutes(started, view.last_review_at, cap=settings.review_minutes_cap)


def with_cap_note(reason: str | None, spent: timer.ReviewMinutes) -> str | None:
    """A capped review says so in its reason, so the stored minutes are never mistaken."""
    if not spent.capped:
        return reason
    note = f"[timer capped: {spent.measured} minutes measured, {spent.minutes} stored]"
    return f"{reason}\n{note}" if reason else note


def locked_plan(conn: Conn, context: OrgContext, plan_id: UUID) -> PlanView:
    """The plan, read after taking its row lock (F1): no other edit/review interleaves."""
    if not plans.lock_plan(conn, context.org.id, plan_id):
        raise not_found("Plan")
    return load_plan(conn, context, plan_id)


# Database guards against forks and double final reviews (migrations 0007, 0012); each
# raises SQLSTATE 23505 with one of these names. Should one fire (a request that got past
# the lock), the user gets the same 409 as from the app's own check, and nothing is saved.
STALE_CONSTRAINTS = frozenset({"recommendation_one_child_idx", "review_final_after_child"})
REVIEWED_CONSTRAINTS = frozenset(
    {"review_one_final_idx", "review_one_approval_idx", "recommendation_child_after_final"}
)


def conflict_message(error: psycopg.Error) -> str | None:
    diag = error.diag
    if error.sqlstate != "23505":
        return None
    if diag.constraint_name in STALE_CONSTRAINTS:
        return STALE_VERSION
    if diag.constraint_name in REVIEWED_CONSTRAINTS:
        return ALREADY_REVIEWED
    return None


@contextmanager
def conflicts_as_409(conn: Conn) -> Iterator[None]:
    """Run the inserts in a savepoint; a version/review conflict becomes 409, nothing saved."""
    try:
        with conn.transaction():
            yield
    except psycopg.Error as error:
        message = conflict_message(error)
        if message is None:
            raise
        raise HTTPException(409, message) from error


def check_version(view: PlanView, form: Any) -> None:
    if view.read_only:
        raise HTTPException(409, ALREADY_REVIEWED)
    if text(form, "recommendation_id", 100) != str(view.latest.id):
        raise HTTPException(409, STALE_VERSION)


@router.post("/plans/{plan_id}/edit")
async def plan_edit_save(request: Request, conn: Conn, context: InternalOrg,
                         settings: SettingsDep, plan_id: UUID) -> Response:  # fmt: skip
    require_agronomist(context)
    view = locked_plan(conn, context, plan_id)
    form = await form_data(request)
    check_version(view, form)
    reason = text(form, "reason").strip()
    raw_rate = text(form, "n_rate", 50)
    raw_splits = [s if isinstance(s, str) else "" for s in form.getlist("split_rate")]
    edit, errors = planning.parse_edit(view.doc, raw_rate, raw_splits, reason)
    if edit is None:
        values = {"n_rate": raw_rate, "splits": raw_splits, "reason": reason}
        return edit_page(request, view, errors, values, 422)
    spent = reviewed_minutes(request, settings, context, view)
    org = context.org.id
    document = planning.edited_document(view.doc, edit, reason)
    with conflicts_as_409(conn):
        new_id = plans.insert_recommendation(
            conn, org, crop_plan_id=plan_id, result=document, user_id=context.user.id,
            parent_id=view.latest.id, reason=reason,
        )  # fmt: skip
        plans.insert_review(
            conn, org, recommendation_id=view.latest.id, decision="edit",
            reason=with_cap_note(reason, spent), reviewer_id=context.user.id,
            minutes_spent=spent.minutes, started_at=spent.started_at,
            resulting_recommendation_id=new_id,
        )  # fmt: skip
    response = RedirectResponse(f"/plans/{plan_id}#review", status_code=303)
    # F4: the next review counts from now (the edit's minutes are already stored).
    timer.set_plan_start(response, settings, context.user, plan_id, int(time.time()))
    return response


@router.post("/plans/{plan_id}/review")
async def plan_review(request: Request, conn: Conn, context: InternalOrg, settings: SettingsDep,
                      plan_id: UUID) -> Response:  # fmt: skip
    require_agronomist(context)
    view = locked_plan(conn, context, plan_id)
    form = await form_data(request)
    check_version(view, form)
    decision = text(form, "decision", 20)
    reason = text(form, "reason").strip()
    errors: dict[str, str] = {}
    if decision not in {"approve", "reject"}:
        errors["decision"] = "Choose Approve or Reject."
    elif decision == "reject" and not reason:
        errors["reason"] = planning.REJECT_REASON_MISSING
    if errors:
        values = {"decision": decision, "reason": reason}
        return plan_page(request, conn, context, settings, plan_id, errors=errors,
                         values=values, status=422)  # fmt: skip
    spent = reviewed_minutes(request, settings, context, view)
    with conflicts_as_409(conn):
        plans.insert_review(
            conn, context.org.id, recommendation_id=view.latest.id, decision=decision,
            reason=with_cap_note(reason or None, spent), reviewer_id=context.user.id,
            minutes_spent=spent.minutes, started_at=spent.started_at,
        )  # fmt: skip
    response = RedirectResponse(f"/plans/{plan_id}", status_code=303)
    timer.clear_plan_start(response, settings, plan_id)  # N14: plan is final, no more timing
    return response
