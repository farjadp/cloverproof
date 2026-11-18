"""Engine output vs the version on screen, line by line (plan page, `_diff.html`).

Read-only. Data comes from the recommendation_diff view (repo.review_queue.diff_source);
lines are built from the stored `result` documents until `recommendation_line` (DM-14)
lands, with the same row shape so the template does not change then. Every value is an
ExplainedNumber dict, so the template always shows it with its explanation.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import psycopg

from cloverproof_app import split_display
from cloverproof_app.repo import review_queue as repo


@dataclass(frozen=True)
class DiffCell:
    """One attribute of a line on both sides. `kind`: number | share | text | confidence."""

    label: str
    kind: str
    engine: Any
    final: Any
    whole_share: bool = False  # engine 0.2/0.3 document: shares stay whole percents

    @property
    def changed(self) -> bool:
        if self.engine is None or self.final is None:
            return self.engine is not self.final
        if self.kind in {"number", "share"}:
            return self.engine.get("unit") != self.final.get("unit") or not math.isclose(
                float(self.engine["value"]), float(self.final["value"]), abs_tol=1e-9
            )
        return bool(self.engine != self.final)


@dataclass(frozen=True)
class DiffLine:
    title: str
    detail: str | None  # stage label, form note
    cells: list[DiffCell]
    only_in: str | None = None  # "engine" | "final" when one side has no such line
    rule_line: bool = False  # P/K soil-test rule line (hard rule 3): never editable

    @property
    def changed(self) -> list[str]:
        return [c.label.lower() for c in self.cells if c.changed]


@dataclass
class LineDiff:
    engine_number: int  # always 1
    final_number: int
    edit_depth: int
    lines: list[DiffLine]
    edits: list[repo.EditStep] = field(default_factory=list)

    @property
    def changed_count(self) -> int:
        return sum(1 for line in self.lines if line.changed or line.only_in)


def _product(split: Mapping[str, Any] | None) -> str | None:
    if split is None:
        return None
    return split_display.product_label(split)


def _timing(split: Mapping[str, Any] | None) -> str | None:
    if split is None:
        return None
    window = split.get("timing")
    if isinstance(window, Mapping) and window.get("start") and window.get("end"):
        basis = f" ({window['basis']})" if window.get("basis") else ""
        return f"{window['start']} to {window['end']}{basis}"
    return split_display.timing_label(split)


def _pk_text(doc: Mapping[str, Any]) -> str:
    note = doc.get("phosphorus_potassium") or {}
    if note.get("code") == "PK_SOIL_TEST_RECOMMENDED":
        return "Soil test recommended. No P or K rate without a soil test."
    return split_display.without_agronomist_claim(str(note.get("text") or "No P/K advice recorded"))


def diff_lines(engine: Mapping[str, Any], final: Mapping[str, Any]) -> list[DiffLine]:
    """Every line of both documents, matched by (nutrient, split position)."""
    en, fn = engine["nitrogen"], final["nitrogen"]
    lines = [
        DiffLine(
            "Plan confidence", None,
            [DiffCell("Confidence", "confidence", engine["confidence"], final["confidence"])],
        ),
        DiffLine(
            "Nitrogen, season", "Elemental N (kg N/ha)",
            [DiffCell("Rate", "number", en["rate"], fn["rate"]),
             DiffCell("Total", "number", en["total"], fn["total"])],
        ),
    ]  # fmt: skip
    e_splits, f_splits = en["splits"], fn["splits"]
    for i in range(max(len(e_splits), len(f_splits))):
        e = e_splits[i] if i < len(e_splits) else None
        f = f_splits[i] if i < len(f_splits) else None
        stage = (f or e or {}).get("stage_label")
        only = "engine" if f is None else ("final" if e is None else None)
        whole_share = split_display.is_old_line(f or e or {})
        lines.append(
            DiffLine(
                f"Nitrogen, split {i + 1}", stage,
                [DiffCell("Rate", "number", e and e["rate"], f and f["rate"]),
                 DiffCell("Share", "share", e and e["fraction"], f and f["fraction"], whole_share),
                 DiffCell("Product", "text", _product(e), _product(f)),
                 DiffCell("Timing", "text", _timing(e), _timing(f))],
                only_in=only,
            )
        )  # fmt: skip
    no_test = (engine.get("phosphorus_potassium") or {}).get("code") == "PK_SOIL_TEST_RECOMMENDED"
    lines.append(
        DiffLine(
            "Phosphorus and potassium", None,
            [DiffCell("Advice", "text", _pk_text(engine), _pk_text(final))],
            rule_line=no_test,
        )
    )  # fmt: skip
    return lines


def plan_diff(conn: psycopg.Connection, org_id: UUID, final_id: UUID,
              final_number: int) -> LineDiff | None:  # fmt: skip
    """Engine output vs the version on screen, for the plan page (`_diff.html`)."""
    source = repo.diff_source(conn, org_id, final_id)
    if source is None:
        return None
    return LineDiff(
        engine_number=1, final_number=final_number, edit_depth=source.edit_depth,
        lines=diff_lines(source.engine_result, source.final_result), edits=source.edits,
    )  # fmt: skip
