"""Plan form validation, engine call and the agronomist's edited document.

No agronomy lives here. The engine (`cloverproof_engine.recommend`) computes every number;
this module only parses form input into engine models and, for an agronomist edit, copies
the engine document with the agronomist's numbers (rate x area for totals is the same unit
arithmetic the engine documents, nothing more).
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import ValidationError

from cloverproof_engine import recommend
from cloverproof_engine.models import (
    ConcentrationUnit,
    Crop,
    ExtractionMethod,
    NutrientForm,
    RecommendationInput,
    SoilTest,
    SoilTestSource,
    SoilTestValue,
    nutrient_of,
)
from cloverproof_engine.pack import Pack, PackConstant

FORM_LABELS = {"P": "P", "P2O5": "P₂O₅", "K": "K", "K2O": "K₂O", "NO3-N": "NO₃-N", "N": "N"}
VALUE_FORMS = ("P", "P2O5", "K", "K2O", "NO3-N")
UNITS = tuple(u.value for u in ConcentrationUnit)
METHOD_LABELS = {
    "olsen": "Olsen",
    "bray-1": "Bray-1",
    "mehlich-3": "Mehlich-3",
    "ammonium-acetate": "Ammonium acetate",
    "other": "Other",
}
CROP_LABELS = {"wheat": "Wheat"}
VALUE_ROWS = 3  # empty value rows on a fresh form; blank rows are ignored

SAMPLE_AFTER_PLAN = "Sample date is after the plan date."
DEPTH_ORDER = "Bottom must be deeper than top."
NAME_METHOD = "Name the extraction method."
VALUE_NEGATIVE = "Enter a value of zero or more."
EDIT_REASON_MISSING = "Write why you changed the numbers."
EDIT_NOTHING_CHANGED = "No numbers changed. Edit at least one number, or go back."
REJECT_REASON_MISSING = "Add a reason for rejecting."


def previous_crop_choices(pack: Pack, crop: str = "wheat") -> list[tuple[str, str]]:
    cfg = pack.crops[Crop(crop)]
    return [(key, pc.label) for key, pc in cfg.nitrogen.previous_crop_credits.items()]


def _number(raw: str | None) -> float | None:
    """A finite float, or None when blank. Raises ValueError for junk."""
    text = (raw or "").strip().replace(",", ".")
    if not text:
        return None
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(text)
    return value


def parse_number(raw: str | None) -> float | None:
    """Public form of `_number` for route code (same rules)."""
    return _number(raw)


def _date(raw: str | None) -> date | None:
    text = (raw or "").strip()
    return date.fromisoformat(text) if text else None


@dataclass
class ValueRow:
    form: str = ""
    value: str = ""
    unit: str = "mg/kg"
    method: str = ""
    detail: str = ""

    @property
    def blank(self) -> bool:
        return not (self.form or self.value.strip() or self.method or self.detail.strip())


@dataclass
class PlanForm:
    """Raw form values (strings), so the form can be re-rendered exactly as typed."""

    crop: str = "wheat"
    target_yield: str = ""
    previous_crop: str = ""
    area_ha: str = ""
    plan_date: str = ""
    has_soil: str = "no"
    sample_date: str = ""
    depth_top: str = ""
    depth_bottom: str = ""
    source: str = "lab"
    lab: str = ""
    values: list[ValueRow] = field(default_factory=list)

    @classmethod
    def from_form(cls, form: Mapping[str, Any], getlist: Any) -> PlanForm:
        def get(name: str) -> str:
            value = form.get(name)
            return value if isinstance(value, str) else ""

        lists = [getlist(n) for n in ("v_form", "v_value", "v_unit", "v_method", "v_detail")]
        rows = [ValueRow(*(str(x) for x in r)) for r in zip(*lists, strict=False)]
        return cls(
            crop=get("crop"),
            target_yield=get("target_yield"),
            previous_crop=get("previous_crop"),
            area_ha=get("area_ha"),
            plan_date=get("plan_date"),
            has_soil=get("has_soil") or "no",
            sample_date=get("sample_date"),
            depth_top=get("depth_top"),
            depth_bottom=get("depth_bottom"),
            source=get("source") or "lab",
            lab=get("lab"),
            values=rows,
        )


@dataclass
class ParsedPlan:
    inputs: RecommendationInput


def validate_plan_form(f: PlanForm, pack: Pack) -> tuple[ParsedPlan | None, dict[str, str]]:
    """Explicit, per-field errors. Returns (parsed, {}) or (None, errors)."""
    errors: dict[str, str] = {}

    if f.crop not in CROP_LABELS:
        errors["crop"] = "Choose a crop. Only wheat is available for now."

    def positive(name: str, label: str, unit: str) -> float | None:
        raw = getattr(f, name)
        try:
            value = _number(raw)
        except ValueError:
            errors[name] = f"Enter {label} as a number in {unit}."
            return None
        if value is None:
            errors[name] = f"Enter {label} in {unit}."
        elif value <= 0:
            errors[name] = f"Enter {label} greater than zero ({unit})."
        return value

    target = positive("target_yield", "the target yield", "t/ha")
    area = positive("area_ha", "the area", "ha")

    choices = dict(previous_crop_choices(pack)) if f.crop in CROP_LABELS else {}
    if f.previous_crop not in choices:
        errors["previous_crop"] = "Choose the previous crop from the list."

    plan_date = None
    try:
        plan_date = _date(f.plan_date)
        if plan_date is None:
            errors["plan_date"] = "Enter the plan date."
    except ValueError:
        errors["plan_date"] = "Enter the plan date as a date (YYYY-MM-DD)."

    soil: SoilTest | None = None
    if f.has_soil not in {"no", "yes"}:
        errors["has_soil"] = "Choose whether you have a soil test."
    elif f.has_soil == "yes":
        soil = _validate_soil(f, plan_date, errors)

    if errors:
        return None, errors
    assert target is not None and area is not None and plan_date is not None
    try:
        inputs = RecommendationInput(
            crop=Crop(f.crop),
            target_yield_t_ha=target,
            previous_crop=f.previous_crop,
            area_ha=area,
            plan_date=plan_date,
            soil_test=soil,
        )
    except ValidationError as error:  # should not happen after the checks above; never hide it
        return None, {"form": f"The engine rejected the inputs: {error.errors()[0]['msg']}"}
    return ParsedPlan(inputs), {}


def _validate_soil(f: PlanForm, plan_date: date | None, errors: dict[str, str]) -> SoilTest | None:
    sample_date = None
    try:
        sample_date = _date(f.sample_date)
        if sample_date is None:
            errors["sample_date"] = "Enter the sample date."
        elif plan_date is not None and sample_date > plan_date:
            errors["sample_date"] = SAMPLE_AFTER_PLAN
    except ValueError:
        errors["sample_date"] = "Enter the sample date as a date (YYYY-MM-DD)."

    top = bottom = None
    try:
        top = _number(f.depth_top)
        if top is None or top < 0:
            errors["depth_top"] = "Enter the top depth in cm (0 or more)."
    except ValueError:
        errors["depth_top"] = "Enter the top depth as a number in cm."
    try:
        bottom = _number(f.depth_bottom)
        if bottom is None or bottom <= 0:
            errors["depth_bottom"] = "Enter the bottom depth in cm."
        elif top is not None and bottom <= top:
            errors["depth_bottom"] = DEPTH_ORDER
    except ValueError:
        errors["depth_bottom"] = "Enter the bottom depth as a number in cm."

    if f.source not in {s.value for s in SoilTestSource}:
        errors["source"] = "Choose Lab or Estimate."
    lab = f.lab.strip() or None
    if lab is not None and len(lab) > 200:
        errors["lab"] = "Lab name is too long (200 characters at most)."

    values: list[SoilTestValue] = []
    seen: dict[str, str] = {}
    for i, row in enumerate(f.values):
        if row.blank:
            continue
        key = f"v{i}"
        if row.form not in VALUE_FORMS:
            errors[f"{key}_form"] = "Choose the nutrient form (P, P₂O₅, K, K₂O or NO₃-N)."
            continue
        nutrient = nutrient_of(NutrientForm(row.form))
        if nutrient in seen:
            first = FORM_LABELS[seen[nutrient]]
            errors[f"{key}_form"] = (
                f"Each nutrient can appear once. You entered {nutrient} twice"
                f" (as {first} and {FORM_LABELS[row.form]})."
            )
            continue
        seen[nutrient] = row.form
        try:
            value = _number(row.value)
        except ValueError:
            value = -1.0
        if value is None or value < 0:
            errors[f"{key}_value"] = VALUE_NEGATIVE
        if row.unit not in UNITS:
            errors[f"{key}_unit"] = "Choose the unit (mg/kg or ppm)."
        if row.method not in METHOD_LABELS:
            errors[f"{key}_method"] = "Choose the extraction method."
        elif row.method == "other" and not row.detail.strip():
            errors[f"{key}_detail"] = NAME_METHOD
        if any(k.startswith(key + "_") for k in errors):
            continue
        assert value is not None
        values.append(
            SoilTestValue(
                form=NutrientForm(row.form),
                value=value,
                unit=ConcentrationUnit(row.unit),
                extraction_method=ExtractionMethod(row.method),
                extraction_method_detail=row.detail.strip() or None,
            )
        )

    if errors or sample_date is None or top is None or bottom is None:
        return None
    return SoilTest(
        sample_date=sample_date,
        depth_top_cm=top,
        depth_bottom_cm=bottom,
        source=SoilTestSource(f.source),
        lab=lab if f.source == "lab" else None,
        values=values,
    )


def run_engine(inputs: RecommendationInput, pack: Pack) -> dict[str, Any]:
    """The stored `result` document: the engine output, untouched."""
    return recommend(inputs, pack).model_dump(mode="json")


# --- agronomist edit -----------------------------------------------------------------


@dataclass
class EditParsed:
    n_rate: float
    split_rates: list[float]
    changed: set[str]  # every number whose value differs from the edited document
    typed: set[str] = field(default_factory=set)  # the subset the agronomist typed


RESCALED = "Rescaled from the agronomist's N rate using the pack split share."


def _fmt(value: float) -> str:
    return f"{value:,.1f}"


def n_rate_limits(pack: Pack, crop: str) -> tuple[PackConstant, PackConstant]:
    """The pack's min and max N rate for the crop (read from the loaded pack)."""
    cfg = pack.crops[Crop(crop)].nitrogen
    return cfg.min_rate, cfg.max_rate


def outside_limits(rate: float, limits: tuple[PackConstant, PackConstant]) -> bool:
    low, high = limits
    return rate < low.value or rate > high.value


def parse_edit(
    doc: Mapping[str, Any], raw_rate: str, raw_splits: Sequence[str], reason: str
) -> tuple[EditParsed | None, dict[str, str]]:
    """Validate the agronomist's numbers against the document they edit."""
    errors: dict[str, str] = {}
    nitrogen = doc["nitrogen"]
    old_rate = float(nitrogen["rate"]["value"])
    old_splits = [float(s["rate"]["value"]) for s in nitrogen["splits"]]

    def number(raw: str, key: str) -> float | None:
        try:
            value = _number(raw)
        except ValueError:
            value = None
        if value is None or value < 0:
            errors[key] = "Enter a rate of zero or more, in kg N/ha."
            return None
        return value

    rate = number(raw_rate, "n_rate")
    if len(raw_splits) != len(old_splits):
        errors["form"] = "The split rows do not match this plan. Reload the page."
        return None, errors
    splits = [number(r, f"split_{i}") for i, r in enumerate(raw_splits)]
    if errors:
        return None, errors
    assert rate is not None
    final_splits = [s for s in splits if s is not None]

    def differs(a: float, b: float) -> bool:
        return not math.isclose(a, b, abs_tol=1e-9)

    typed: set[str] = set()
    if differs(rate, old_rate):
        typed.add("n_rate")

    def moved(new_splits: list[float]) -> set[str]:
        pairs = enumerate(zip(new_splits, old_splits, strict=True))
        return {f"split_{i}" for i, (a, b) in pairs if differs(a, b)}

    typed |= moved(final_splits)
    if typed == {"n_rate"}:
        # Splits left as they were: keep the same shares of the new rate.
        fractions = [float(s["fraction"]["value"]) for s in nitrogen["splits"]]
        final_splits = [rate * fr for fr in fractions]
    changed = typed | moved(final_splits)

    if not changed:
        errors["form"] = EDIT_NOTHING_CHANGED
    elif not math.isclose(sum(final_splits), rate, abs_tol=0.05):
        errors["splits"] = (
            f"The split rates add up to {_fmt(sum(final_splits))} kg N/ha,"
            f" but the N rate is {_fmt(rate)} kg N/ha. Make them match."
        )
    if not reason.strip():
        errors["reason"] = EDIT_REASON_MISSING
    if errors:
        return None, errors
    return EditParsed(rate, final_splits, changed, typed), {}


def edited_document(doc: Mapping[str, Any], edit: EditParsed, reason: str) -> dict[str, Any]:
    """Same document shape as the engine output, with the agronomist's final numbers.

    Only numbers the agronomist typed say "Set by agronomist". Splits rescaled from the new
    N rate with the pack shares say so and keep the share's PLACEHOLDER flag. Every split
    share is recomputed against the final N rate, typed or not.
    """
    new = copy.deepcopy(dict(doc))
    nitrogen = new["nitrogen"]
    area = float(new["input_snapshot"]["area_ha"])
    note = f"Set by agronomist: {reason.strip()}"
    final_rate = edit.n_rate if "n_rate" in edit.changed else float(nitrogen["rate"]["value"])

    def set_number(number: dict[str, Any], value: float, explanation: str,
                   placeholder: bool) -> None:  # fmt: skip
        number["value"] = value
        number["explanation"] = explanation
        number["uses_placeholder"] = placeholder

    def total_text(prefix: str, rate: float) -> str:
        return f"{prefix} Total = {_fmt(rate)} kg N/ha x {_fmt(area)} ha."

    if "n_rate" in edit.changed:
        set_number(nitrogen["rate"], edit.n_rate, note, False)
        nitrogen["bound_applied"] = None
        set_number(nitrogen["total"], edit.n_rate * area, total_text(note, edit.n_rate), False)

    for i, split in enumerate(nitrogen["splits"]):
        key = f"split_{i}"
        rate = edit.split_rates[i]
        share = rate / final_rate if final_rate > 0 else 0.0
        fraction = split["fraction"]
        if key in edit.typed:
            set_number(split["rate"], rate, note, False)
            set_number(split["total"], rate * area, total_text(note, rate), False)
            set_number(fraction, share, f"{note} Share of the final N rate.", False)
        elif key in edit.changed:  # rescaled from the agronomist's N rate
            flag = bool(fraction["uses_placeholder"])
            set_number(split["rate"], rate, RESCALED, flag)
            set_number(split["total"], rate * area, total_text(RESCALED, rate), flag)
            if final_rate > 0:
                fraction["value"] = share  # the pack share, recomputed from the final rate
            else:
                set_number(fraction, 0.0, "The final N rate is 0 kg N/ha: no share.", False)
        elif not math.isclose(share, float(fraction["value"]), abs_tol=1e-9):
            # Rate left as it was, but the final N rate changed: only the share moves.
            set_number(
                fraction,
                share,
                f"Share of the final N rate: {_fmt(rate)} of {_fmt(final_rate)} kg N/ha.",
                bool(split["rate"]["uses_placeholder"]),
            )
    return new
