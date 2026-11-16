"""Golden cases: loader, comparison and report. The report never fails the build."""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from cloverproof_engine import recommend, units
from cloverproof_engine.golden import (
    ExpectedCase,
    ExternalReferenceCase,
    GoldenKind,
    RateUnit,
    ReferenceRate,
    compare,
    parse_golden_case,
)
from cloverproof_engine.golden_report import main, run_report
from cloverproof_engine.loaders import golden_paths, load_golden_cases

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "engine" / "tests" / "golden"
PACKS_DIR = REPO_ROOT / "packs"


def _case_data(**expected_overrides: object) -> dict[str, Any]:
    expected: dict[str, object] = {
        "n_rate_kg_ha": 175.0,
        "n_total_kg": 7000.0,
        "split_rates_kg_ha": [70.0, 105.0],
        "confidence": "low",
        "pk_note": "PK_SOIL_TEST_RECOMMENDED",
    }
    expected.update(expected_overrides)
    return {
        "id": "t",
        "kind": "sample",
        "pack": {"id": "placeholder", "version": "v0"},
        "tolerance": {"kg_n_per_ha": 0.5, "kg_n": 10.0},
        "input": {
            "crop": "wheat",
            "target_yield_t_ha": 6.0,
            "previous_crop": "canola",
            "area_ha": 40.0,
            "plan_date": "2027-02-15",
        },
        "expected": expected,
    }


def _case(**expected_overrides: object) -> ExpectedCase:
    case = parse_golden_case(_case_data(**expected_overrides))
    assert isinstance(case, ExpectedCase)
    return case


def _approved_data(**top: object) -> dict[str, Any]:
    data = _case_data(reason="Test reason for the expected numbers.")
    data.update(
        {"kind": "agronomist_approved", "reviewer": "Test Reviewer", "reviewed_on": "2027-01-10"}
    )
    data.update(top)
    return data


def _external_data(**top: object) -> dict[str, Any]:
    """External reference case. Values are TEST FIXTURE ONLY, not from any tool."""
    data: dict[str, Any] = {
        "id": "t_ext",
        "kind": "external_reference",
        "pack": {"id": "placeholder", "version": "v0"},
        "source": {"tool": "Test Tool", "url": "", "version": "test-1"},
        "accessed_on": "2026-11-16",
        "entered_by": "Test Person",
        "region": "Test Region",
        "input": {
            "crop": "wheat",
            "target_yield_t_ha": 6.0,
            "previous_crop": "canola",
            "area_ha": 40.0,
            "plan_date": "2027-02-15",
        },
        "reference_output": {
            "n_rate": {"value": 100.0, "unit": "lb/ac"},
        },
    }
    data.update(top)
    return data


def test_kind_values() -> None:
    assert {k.value for k in GoldenKind} == {
        "sample",
        "agronomist_approved",
        "external_reference",
    }


def test_missing_kind_is_rejected() -> None:
    data = _case_data()
    del data["kind"]
    with pytest.raises(ValueError, match="kind"):
        parse_golden_case(data)


def test_old_status_field_is_rejected() -> None:
    data = _case_data()
    del data["kind"]
    data["status"] = "SAMPLE"
    with pytest.raises(ValueError, match="status"):
        parse_golden_case(data)


@pytest.mark.parametrize("kind", ["SAMPLE", "approved", "sample — not approved", ""])
def test_unknown_kind_is_rejected(kind: str) -> None:
    data = _case_data()
    data["kind"] = kind
    with pytest.raises(ValidationError):
        parse_golden_case(data)


def test_approved_case_with_review_fields_loads() -> None:
    case = parse_golden_case(_approved_data())
    assert isinstance(case, ExpectedCase)
    assert case.kind == GoldenKind.AGRONOMIST_APPROVED
    assert case.reviewer == "Test Reviewer"
    assert case.reviewed_on == date(2027, 1, 10)


@pytest.mark.parametrize(
    "change",
    [
        {"reviewer": None},
        {"reviewer": "  "},
        {"reviewed_on": None},
        {"reviewed_on": "not a date"},
    ],
)
def test_approved_case_requires_reviewer_and_date(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        parse_golden_case(_approved_data(**change))


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_approved_case_requires_reason(reason: str | None) -> None:
    data = _approved_data()
    data["expected"]["reason"] = reason
    with pytest.raises(ValidationError):
        parse_golden_case(data)


def test_sample_case_needs_no_review_fields() -> None:
    case = _case()
    assert case.kind == GoldenKind.SAMPLE
    assert case.reviewer is None and case.reviewed_on is None


def test_external_reference_case_loads() -> None:
    case = parse_golden_case(_external_data())
    assert isinstance(case, ExternalReferenceCase)
    assert case.kind == GoldenKind.EXTERNAL_REFERENCE
    assert case.accessed_on == date(2026, 11, 16)
    assert case.region == "Test Region"
    assert case.reference_output.n_rate.unit is RateUnit.LB_PER_AC
    assert case.reference_output.phosphorus is None
    assert case.reference_output.n_splits == []


def test_external_reference_full_optional_block_loads() -> None:
    ref = {
        "n_rate": {"value": 120.0, "unit": "kg/ha"},
        "n_splits": [
            {"value": 40.0, "unit": "kg/ha", "timing": "pre-plant"},
            {"value": 80.0, "unit": "kg/ha", "timing": "in-crop"},
        ],
        "phosphorus": {"value": 30.0, "unit": "lb/ac", "form": "P2O5"},
        "potassium": {"value": 20.0, "unit": "kg/ha", "form": "K"},
    }
    case = parse_golden_case(
        _external_data(reference_output=ref, tool_settings={"price_ratio": "0.1"}, notes="x")
    )
    assert isinstance(case, ExternalReferenceCase)
    assert case.reference_output.phosphorus is not None
    assert case.reference_output.phosphorus.form.value == "P2O5"
    assert len(case.reference_output.n_splits) == 2


@pytest.mark.parametrize(
    "missing", ["source", "accessed_on", "entered_by", "region", "reference_output", "input"]
)
def test_external_reference_requires_field(missing: str) -> None:
    data = _external_data()
    del data[missing]
    with pytest.raises(ValidationError):
        parse_golden_case(data)


@pytest.mark.parametrize(
    "change",
    [
        {"entered_by": "  "},
        {"region": ""},
        {"accessed_on": "not a date"},
        {"source": {"tool": "", "version": "1"}},
        {"source": {"tool": "Test Tool", "url": " ", "version": None}},
        {"reference_output": {}},
        {"reference_output": {"n_rate": {"value": 100.0}}},
        {"reference_output": {"n_rate": {"value": 100.0, "unit": "bu/ac"}}},
        {"reference_output": {"n_rate": {"value": -1.0, "unit": "kg/ha"}}},
    ],
)
def test_external_reference_rejects_bad_metadata(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        parse_golden_case(_external_data(**change))


@pytest.mark.parametrize(
    ("slot", "form"),
    [("phosphorus", "K2O"), ("phosphorus", "N"), ("potassium", "P2O5"), ("potassium", None)],
)
def test_external_reference_pk_form_must_match_nutrient(slot: str, form: str | None) -> None:
    ref: dict[str, Any] = {
        "n_rate": {"value": 100.0, "unit": "kg/ha"},
        slot: {"value": 10.0, "unit": "kg/ha", "form": form},
    }
    with pytest.raises(ValidationError):
        parse_golden_case(_external_data(reference_output=ref))


def test_external_reference_has_no_expected_block() -> None:
    data = _external_data(expected=_case_data()["expected"])
    with pytest.raises(ValidationError):
        parse_golden_case(data)


def test_reference_rate_converts_lb_per_ac_through_units() -> None:
    rate = ReferenceRate(value=100.0, unit=RateUnit.LB_PER_AC)
    assert rate.kg_per_ha == pytest.approx(units.lb_per_ac_to_kg_per_ha(100.0))
    assert ReferenceRate(value=50.0, unit=RateUnit.KG_PER_HA).kg_per_ha == 50.0


def test_report_shows_invalid_approved_case_as_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _approved_data(id="approved_without_reviewer", reviewer=None)
    (tmp_path / "approved_without_reviewer.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    assert main(["--golden-dir", str(tmp_path), "--packs-dir", str(PACKS_DIR)]) == 0
    out = capsys.readouterr().out
    assert "approved_without_reviewer.yaml  ERROR" in out
    assert "1 error(s)" in out


def test_loads_sample_cases() -> None:
    cases = load_golden_cases(GOLDEN_DIR)
    assert len(cases) >= 2
    for path, case in cases:
        if path.name.startswith("sample_"):
            assert case.kind == GoldenKind.SAMPLE


def test_compare_all_match(placeholder_pack) -> None:
    case = _case()
    rows = compare(case, recommend(case.input, placeholder_pack))
    assert rows and all(r.ok for r in rows)
    fields = [r.field for r in rows]
    assert fields == [
        "n_rate_kg_ha",
        "n_total_kg",
        "split_1_rate_kg_ha",
        "split_2_rate_kg_ha",
        "confidence",
        "pk_note",
    ]


def test_compare_reports_differences(placeholder_pack) -> None:
    case = _case(n_rate_kg_ha=150.0, confidence="medium", split_rates_kg_ha=[70.0])
    rows = {r.field: r for r in compare(case, recommend(case.input, placeholder_pack))}
    assert rows["n_rate_kg_ha"].diff == pytest.approx(25.0)
    assert not rows["n_rate_kg_ha"].ok
    assert not rows["confidence"].ok
    assert rows["split_2_rate_kg_ha"].expected is None
    assert not rows["split_2_rate_kg_ha"].ok


def test_tolerance_applies(placeholder_pack) -> None:
    case = _case(n_rate_kg_ha=175.4)
    rows = {r.field: r for r in compare(case, recommend(case.input, placeholder_pack))}
    assert rows["n_rate_kg_ha"].ok


def test_report_lists_every_case_and_diff() -> None:
    report = run_report(GOLDEN_DIR, PACKS_DIR)
    for path, case in load_golden_cases(GOLDEN_DIR):
        assert case.id in report, path
    assert "expected" in report and "actual" in report and "diff" in report
    assert "report only" in report.lower()


def test_report_shows_errors_without_raising(tmp_path: Path) -> None:
    (tmp_path / "broken.yaml").write_text("id: broken\n", encoding="utf-8")
    report = run_report(tmp_path, PACKS_DIR)
    assert "broken" in report
    assert "ERROR" in report


def test_report_handles_missing_pack(tmp_path: Path) -> None:
    src_path = next(GOLDEN_DIR.glob("sample_*.yaml"))
    src = src_path.read_text(encoding="utf-8")
    (tmp_path / src_path.name).write_text(
        src.replace("version: v0", "version: v99"), encoding="utf-8"
    )
    report = run_report(tmp_path, PACKS_DIR)
    assert "ERROR" in report
    assert "v99" in report


def test_main_always_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "broken.yaml").write_text("not: [valid", encoding="utf-8")
    code = main(["--golden-dir", str(tmp_path), "--packs-dir", str(PACKS_DIR)])
    assert code == 0
    assert "ERROR" in capsys.readouterr().out


def test_main_on_real_dir(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--golden-dir", str(GOLDEN_DIR), "--packs-dir", str(PACKS_DIR)]) == 0
    assert "sample_" in capsys.readouterr().out


def test_loader_skips_underscore_files(tmp_path: Path) -> None:
    (tmp_path / "_TEMPLATE_x.yaml").write_text("kind:\nid:\n", encoding="utf-8")
    (tmp_path / "t.yaml").write_text(yaml.safe_dump(_case_data()), encoding="utf-8")
    assert [p.name for p in golden_paths(tmp_path)] == ["t.yaml"]
    assert [c.id for _, c in load_golden_cases(tmp_path)] == ["t"]
    report = run_report(tmp_path, PACKS_DIR)
    assert "_TEMPLATE_x" not in report
    assert "ERROR" not in report
