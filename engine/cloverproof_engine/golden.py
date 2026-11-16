"""Golden cases (input -> expected) and their comparison. Pure: no file access.

Golden YAML lives in engine/tests/golden/. `sample_*.yaml` are SAMPLE cases
derived from the placeholder pack; the agronomist's real cases replace them.
The report is informational: it never fails the build (yet).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from cloverproof_engine.confidence import Confidence
from cloverproof_engine.models import RecommendationInput
from cloverproof_engine.results import Recommendation


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


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


class GoldenCase(_Frozen):
    id: str
    status: str
    description: str = ""
    pack: PackRef
    tolerance: Tolerance
    input: RecommendationInput
    expected: GoldenExpected


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


def compare(case: GoldenCase, rec: Recommendation) -> list[DiffRow]:
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


def format_case(case: GoldenCase, rows: list[DiffRow], rec: Recommendation) -> str:
    header = (
        f"== {case.id}  [{case.status}]  pack {rec.pack_id} {rec.pack_version}  "
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
