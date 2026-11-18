"""Golden cases (input -> expected or reference) and their comparison. Pure: no file access.

Golden YAML lives in engine/tests/golden/. Every case declares a `kind`:

- `sample`: expected numbers derived from the placeholder pack, only to exercise
  the report. Never counts toward the agreement gate.
- `agronomist_approved`: the agronomist's decision. Must carry `reviewer` (a human,
  never `cp-agronomist`) and `reviewed_on` (top level) and a non-empty
  `expected.reason`. The only kind that counts toward the agreement gate.
- `external_reference`: the output of a public tool or the numbers of an official
  document, entered by hand by a human. Must carry `source` (a tool + URL and/or
  version, or a document: title, publisher, year, page/table locator, URL),
  `accessed_on`, `entered_by`, `region` (metadata, not an engine input) and
  `reference_output`. Information only: the reference is not ground truth and never
  counts toward the gate.
- `ai_reviewed`: same shape as `external_reference`, drafted by the AI agronomist
  `cp-agronomist` from a cited source (CLAUDE.md rule 11). Never agronomist
  validation; information only; never counts toward the gate or calibration.

Only `sample` and `agronomist_approved` cases assert (expected vs actual, ok column).
Reference kinds show the engine-vs-reference difference only, without pass/fail.
Yield is stored only as `input.target_yield_t_ha` (t/ha); a tool's bu/ac display is
recorded as `tool_settings.yield_display_unit`, never as a stored number.

A missing `kind` or a missing required field fails loading; the report shows an
ERROR line. The report is informational: it never fails the build (yet).
"""

from datetime import date
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    StringConstraints,
    TypeAdapter,
    field_validator,
    model_validator,
)

from cloverproof_engine import units
from cloverproof_engine.confidence import Confidence
from cloverproof_engine.models import (
    NonNegativeFloat,
    NutrientForm,
    RecommendationInput,
    nutrient_of,
)
from cloverproof_engine.results import Recommendation

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class GoldenKind(StrEnum):
    SAMPLE = "sample"
    AGRONOMIST_APPROVED = "agronomist_approved"
    EXTERNAL_REFERENCE = "external_reference"
    AI_REVIEWED = "ai_reviewed"


# The only AI agent allowed to draft golden cases (CLAUDE.md rule 11).
AI_AGRONOMIST = "cp-agronomist"
REFERENCE_KINDS = (GoldenKind.EXTERNAL_REFERENCE, GoldenKind.AI_REVIEWED)


class PackRef(_Frozen):
    id: str
    version: str


class Tolerance(_Frozen):
    """Absolute agreement thresholds, set per case (not engine constants)."""

    kg_n_per_ha: float = Field(ge=0)
    kg_n: float = Field(ge=0)


class GoldenExpected(_Frozen):
    n_rate_kg_ha: float
    n_total_kg: float
    split_rates_kg_ha: list[float]
    # Optional: the timing window label per line (null = the line has no window).
    split_timing_windows: list[str | None] | None = None
    confidence: Confidence
    pk_note: str
    reason: str | None = None


class ExpectedCase(_Frozen):
    """A `sample` or `agronomist_approved` case: input -> expected engine output."""

    id: str
    kind: Literal["sample", "agronomist_approved"]
    reviewer: str | None = None
    reviewed_on: date | None = None
    description: str = ""
    pack: PackRef
    tolerance: Tolerance
    input: RecommendationInput
    expected: GoldenExpected

    @model_validator(mode="after")
    def _check_review(self) -> Self:
        if self.kind != GoldenKind.AGRONOMIST_APPROVED:
            return self
        missing = [
            name
            for name, value in (
                ("reviewer", self.reviewer),
                ("reviewed_on", self.reviewed_on),
                ("expected.reason", self.expected.reason),
            )
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if missing:
            raise ValueError(f"agronomist_approved case needs non-empty: {', '.join(missing)}")
        if AI_AGRONOMIST in (self.reviewer or "").lower():
            raise ValueError(
                f"{AI_AGRONOMIST} (AI) can never approve: an agronomist_approved case needs "
                "a human reviewer (CLAUDE.md rule 11); use kind ai_reviewed"
            )
        return self


class RateUnit(StrEnum):
    """Application-rate units a reference tool may report in."""

    KG_PER_HA = "kg/ha"
    LB_PER_AC = "lb/ac"


class ReferenceRate(_Frozen):
    value: NonNegativeFloat
    unit: RateUnit

    @property
    def kg_per_ha(self) -> float:
        """The value in kg/ha, converted only through `units.py`."""
        if self.unit is RateUnit.LB_PER_AC:
            return units.lb_per_ac_to_kg_per_ha(self.value)
        return self.value


class ReferenceSplit(ReferenceRate):
    timing: str | None = None


class ReferenceNutrient(ReferenceRate):
    """A P or K rate from the reference tool, with its form (elemental or oxide)."""

    form: NutrientForm


class ReferenceOutput(_Frozen):
    """What the external tool reported, as entered by hand. Stored for comparison only:
    the engine compares N; P/K are kept for reference (the engine gives no P/K rate).
    """

    n_rate: ReferenceRate
    n_splits: list[ReferenceSplit] = Field(default_factory=list)
    phosphorus: ReferenceNutrient | None = None
    potassium: ReferenceNutrient | None = None

    @model_validator(mode="after")
    def _check_forms(self) -> Self:
        for slot, value, element in (
            ("phosphorus", self.phosphorus, "P"),
            ("potassium", self.potassium, "K"),
        ):
            if value is not None and nutrient_of(value.form) != element:
                raise ValueError(f"{slot} form must express {element}, got {value.form.value}")
        return self


class ReferenceSource(_Frozen):
    """Where the reference numbers come from: a public tool, or an official document.

    Tool: `tool` + a `url` and/or `version`. Document: `title`, `publisher`, `year`,
    `locator` (page / table) and `url`, all required. The access date is the case's
    top-level `accessed_on`.
    """

    tool: NonBlankStr | None = None
    url: str | None = None
    version: str | None = None
    title: NonBlankStr | None = None
    publisher: NonBlankStr | None = None
    year: int | None = Field(default=None, gt=0)
    locator: NonBlankStr | None = None

    @model_validator(mode="after")
    def _check_locator(self) -> Self:
        if self.tool is None and self.title is None:
            raise ValueError("source needs a tool or a document title")
        url = (self.url or "").strip()
        if self.title is not None:
            missing = [
                name
                for name, value in (
                    ("publisher", self.publisher),
                    ("year", self.year),
                    ("locator", self.locator),
                    ("url", url or None),
                )
                if value is None
            ]
            if missing:
                raise ValueError(f"document source needs: {', '.join(missing)}")
        elif not url and not (self.version or "").strip():
            raise ValueError("source needs a url or a version")
        return self

    def describe(self) -> str:
        if self.title is not None:
            return f"{self.title}, {self.publisher}, {self.year}, {self.locator}, {self.url}"
        locator = ", ".join(
            x for x in ((self.version or "").strip(), (self.url or "").strip()) if x
        )
        return f"{self.tool} ({locator})"


YIELD_DISPLAY_KEY = "yield_display_unit"
YIELD_DISPLAY_UNITS = ("t/ha", "bu/ac")


class ExternalReferenceCase(_Frozen):
    """An `external_reference` or `ai_reviewed` case: input -> a reference output.

    Not ground truth; information only.
    """

    id: str
    kind: Literal["external_reference", "ai_reviewed"]
    description: str = ""
    pack: PackRef
    source: ReferenceSource
    accessed_on: date
    entered_by: NonBlankStr
    # Metadata only (where the reference applies); not an engine input.
    region: NonBlankStr
    # Settings as shown in the tool (text or on/off), never data: no numbers, no yield.
    tool_settings: dict[str, StrictStr | StrictBool] | None = None
    notes: str | None = None
    input: RecommendationInput
    reference_output: ReferenceOutput

    @field_validator("tool_settings")
    @classmethod
    def _check_settings(cls, value: dict[str, str | bool] | None) -> dict[str, str | bool] | None:
        for key, setting in (value or {}).items():
            if key == YIELD_DISPLAY_KEY:
                if setting not in YIELD_DISPLAY_UNITS:
                    raise ValueError(f"{key} must be one of {', '.join(YIELD_DISPLAY_UNITS)}")
            elif "yield" in key.lower():
                raise ValueError(
                    f"tool_settings.{key}: yield is stored only as input.target_yield_t_ha; "
                    f"use {YIELD_DISPLAY_KEY} for the display unit"
                )
        return value

    @model_validator(mode="after")
    def _check_author(self) -> Self:
        is_ai = AI_AGRONOMIST in self.entered_by.lower()
        if self.kind == GoldenKind.AI_REVIEWED and not is_ai:
            raise ValueError(f"an ai_reviewed case is entered by {AI_AGRONOMIST}")
        if self.kind == GoldenKind.EXTERNAL_REFERENCE and is_ai:
            raise ValueError(f"a case entered by {AI_AGRONOMIST} must be kind ai_reviewed")
        return self


GoldenCase = Annotated[ExpectedCase | ExternalReferenceCase, Field(discriminator="kind")]
_GOLDEN_CASE: TypeAdapter[ExpectedCase | ExternalReferenceCase] = TypeAdapter(GoldenCase)


def parse_golden_case(data: dict[str, Any]) -> ExpectedCase | ExternalReferenceCase:
    """Validate one golden case mapping. Raises ValueError (incl. ValidationError)."""
    if "kind" not in data:
        kinds = ", ".join(k.value for k in GoldenKind)
        hint = " (`status` was replaced by `kind`)" if "status" in data else ""
        raise ValueError(f"missing `kind`{hint}; one of: {kinds}")
    return _GOLDEN_CASE.validate_python(data)


class DiffRow(_Frozen):
    field: str
    expected: float | str | None
    actual: float | str | None
    diff: float | None
    ok: bool
    kind: Literal["number", "label"]


def _number(field: str, expected: float | None, actual: float | None, tol: float) -> DiffRow:
    if expected is None or actual is None:
        return DiffRow(
            field=field, expected=expected, actual=actual, diff=None, ok=False, kind="number"
        )
    diff = actual - expected
    return DiffRow(
        field=field,
        expected=expected,
        actual=actual,
        diff=diff,
        ok=abs(diff) <= tol,
        kind="number",
    )


def _label(field: str, expected: str, actual: str) -> DiffRow:
    return DiffRow(
        field=field,
        expected=expected,
        actual=actual,
        diff=None,
        ok=expected == actual,
        kind="label",
    )


def compare(case: ExpectedCase, rec: Recommendation) -> list[DiffRow]:
    exp, tol, n = case.expected, case.tolerance, rec.nitrogen
    rows = [
        _number("n_rate_kg_ha", exp.n_rate_kg_ha, n.rate.value, tol.kg_n_per_ha),
        _number("n_total_kg", exp.n_total_kg, n.total.value, tol.kg_n),
    ]
    actual_splits = [s.rate.value for s in n.splits]
    for i in range(max(len(exp.split_rates_kg_ha), len(actual_splits))):
        e = exp.split_rates_kg_ha[i] if i < len(exp.split_rates_kg_ha) else None
        a = actual_splits[i] if i < len(actual_splits) else None
        rows.append(_number(f"split_{i + 1}_rate_kg_ha", e, a, tol.kg_n_per_ha))
    if exp.split_timing_windows is not None:
        actual_windows = [s.timing_window.label if s.timing_window else None for s in n.splits]
        for i in range(max(len(exp.split_timing_windows), len(actual_windows))):
            e_w = exp.split_timing_windows[i] if i < len(exp.split_timing_windows) else None
            a_w = actual_windows[i] if i < len(actual_windows) else None
            rows.append(_label(f"split_{i + 1}_timing_window", e_w or "-", a_w or "-"))
    rows.append(_label("confidence", exp.confidence.value, rec.confidence.value))
    rows.append(_label("pk_note", exp.pk_note, rec.phosphorus_potassium.code))
    return rows


def _cell(value: float | str | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        return value
    return f"{value:.1f}"


def format_case(case: ExpectedCase, rows: list[DiffRow], rec: Recommendation) -> str:
    header = (
        f"== {case.id}  [{case.kind}]  pack {rec.pack_id} {rec.pack_version}  "
        f"engine {rec.engine_version}"
    )
    table = [("field", "expected", "actual", "diff", "ok")]
    for r in rows:
        diff = "-" if r.diff is None else f"{r.diff:+.1f}"
        table.append((r.field, _cell(r.expected), _cell(r.actual), diff, "yes" if r.ok else "NO"))
    lines = [header, *_table(table)]
    return "\n".join(line.rstrip() for line in lines)


def format_error(name: str, message: str) -> str:
    first = message.strip().splitlines()[0] if message.strip() else "unknown error"
    return f"== {name}  ERROR: {first}"


def case_agrees(rows: list[DiffRow]) -> bool:
    """A case agrees when every compared number is within the case tolerance."""
    return all(r.ok for r in rows if r.kind == "number")


class ExternalRow(_Frozen):
    """Engine N vs an external tool's N, both in kg/ha. Information only."""

    field: str
    engine_kg_ha: float | None
    reference: str | None
    reference_kg_ha: float | None
    diff_kg_ha: float | None


def _as_entered(rate: ReferenceRate) -> str:
    return f"{rate.value:.1f} {rate.unit.value}"


def _external_row(field: str, engine: float | None, ref: ReferenceRate | None) -> ExternalRow:
    ref_kg = None if ref is None else ref.kg_per_ha
    diff = None if engine is None or ref_kg is None else engine - ref_kg
    return ExternalRow(
        field=field,
        engine_kg_ha=engine,
        reference=None if ref is None else _as_entered(ref),
        reference_kg_ha=ref_kg,
        diff_kg_ha=diff,
    )


def compare_external(case: ExternalReferenceCase, rec: Recommendation) -> list[ExternalRow]:
    """N rate and splits (by position). P/K are not compared: the engine gives no P/K."""
    ref = case.reference_output
    rows = [_external_row("n_rate", rec.nitrogen.rate.value, ref.n_rate)]
    if ref.n_splits:
        engine_splits = [s.rate.value for s in rec.nitrogen.splits]
        for i in range(max(len(ref.n_splits), len(engine_splits))):
            e = engine_splits[i] if i < len(engine_splits) else None
            r = ref.n_splits[i] if i < len(ref.n_splits) else None
            rows.append(_external_row(f"split_{i + 1}", e, r))
    return rows


def _table(rows: list[tuple[str, ...]]) -> list[str]:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    return ["  " + "  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)) for row in rows]


def format_external(
    case: ExternalReferenceCase, rows: list[ExternalRow], rec: Recommendation
) -> str:
    lines = [
        f"== {case.id}  [{case.kind}]  pack {rec.pack_id} {rec.pack_version}  "
        f"engine {rec.engine_version}",
        f"  source: {case.source.describe()}; accessed {case.accessed_on.isoformat()} "
        f"by {case.entered_by}; region {case.region}",
    ]
    if case.kind == GoldenKind.AI_REVIEWED:
        lines.append(f"  drafted by {AI_AGRONOMIST} (AI), not agronomist validation")
    table = [("field", "engine kg/ha", "reference", "reference kg/ha", "diff kg/ha")]
    for r in rows:
        diff = "-" if r.diff_kg_ha is None else f"{r.diff_kg_ha:+.1f}"
        table.append(
            (r.field, _cell(r.engine_kg_ha), r.reference or "-", _cell(r.reference_kg_ha), diff)
        )
    lines += _table(table)
    ref = case.reference_output
    for name, value in (("phosphorus", ref.phosphorus), ("potassium", ref.potassium)):
        if value is not None:
            lines.append(
                f"  {name}: {_as_entered(value)} {value.form.value} "
                "- reference only, engine gives no P/K"
            )
    return "\n".join(line.rstrip() for line in lines)
