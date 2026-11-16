"""Golden cases (input -> expected or reference) and their comparison. Pure: no file access.

Golden YAML lives in engine/tests/golden/. Every case declares a `kind`:

- `sample`: expected numbers derived from the placeholder pack, only to exercise
  the report. Never counts toward the agreement gate.
- `agronomist_approved`: the agronomist's decision. Must carry `reviewer` and
  `reviewed_on` (top level) and a non-empty `expected.reason`. The only kind that
  counts toward the agreement gate.
- `external_reference`: the output of a public tool, entered by hand. Must carry
  `source` (tool + URL and/or version), `accessed_on`, `entered_by`, `region`
  (metadata, not an engine input) and `reference_output`. Information only: the
  reference is not ground truth and never counts toward the gate.

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
    StringConstraints,
    TypeAdapter,
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
    tool: NonBlankStr
    url: str | None = None
    version: str | None = None

    @model_validator(mode="after")
    def _check_locator(self) -> Self:
        if not (self.url or "").strip() and not (self.version or "").strip():
            raise ValueError("source needs a url or a version")
        return self


class ExternalReferenceCase(_Frozen):
    """An `external_reference` case: input -> a public tool's output. Not ground truth."""

    id: str
    kind: Literal["external_reference"]
    description: str = ""
    pack: PackRef
    source: ReferenceSource
    accessed_on: date
    entered_by: NonBlankStr
    # Metadata only (where the reference tool applies); not an engine input.
    region: NonBlankStr
    tool_settings: dict[str, Any] | None = None
    notes: str | None = None
    input: RecommendationInput
    reference_output: ReferenceOutput


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
    widths = [max(len(row[i]) for row in table) for i in range(len(table[0]))]
    lines = [header]
    lines += [
        "  " + "  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)) for row in table
    ]
    return "\n".join(line.rstrip() for line in lines)


def format_error(name: str, message: str) -> str:
    first = message.strip().splitlines()[0] if message.strip() else "unknown error"
    return f"== {name}  ERROR: {first}"
