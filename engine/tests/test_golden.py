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
    compare_external,
    parse_golden_case,
)
from cloverproof_engine.golden_report import main, run_report
from cloverproof_engine.loaders import golden_paths, load_golden_cases, load_pack

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
        "ai_reviewed",
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


@pytest.mark.parametrize(
    "reviewer", ["cp-agronomist", "CP-Agronomist", "  cp-agronomist  ", "cp-agronomist (AI)"]
)
def test_approved_case_rejects_the_ai_agronomist_as_reviewer(reviewer: str) -> None:
    # CLAUDE.md rule 11: cp-agronomist can never approve.
    with pytest.raises(ValidationError, match="cp-agronomist"):
        parse_golden_case(_approved_data(reviewer=reviewer))


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


def test_lab_test_without_values_golden_case_fires_the_no_test_rule() -> None:
    cases = dict((path.stem, case) for path, case in load_golden_cases(GOLDEN_DIR))
    case = cases["sample_ca_on_lab_test_no_values"]
    rec = recommend(case.input, load_pack(PACKS_DIR / "ca-on" / "v2.yaml"))
    assert [r.field for r in compare(case, rec) if not r.ok] == []


def test_compare_reports_unexpected_confidence_rules(placeholder_pack) -> None:
    case = _case(confidence_rules=["C1_NO_SOIL_TEST"])
    rows = {r.field: r for r in compare(case, recommend(case.input, placeholder_pack))}
    assert rows["confidence_rules"].expected == "C1_NO_SOIL_TEST"
    assert not rows["confidence_rules"].ok


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


def _write(directory: Path, data: dict[str, Any]) -> None:
    (directory / f"{data['id']}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def _mixed_dir(tmp_path: Path) -> Path:
    """One sample, two approved (one agrees, one does not), one external reference."""
    _write(tmp_path, {**_case_data(), "id": "s1"})
    _write(tmp_path, _approved_data(id="a_ok"))
    bad = _approved_data(id="a_off")
    bad["expected"]["n_rate_kg_ha"] = 150.0
    _write(tmp_path, bad)
    ext = _external_data(id="e1")
    ext["reference_output"] = {
        "n_rate": {"value": 100.0, "unit": "lb/ac"},
        "phosphorus": {"value": 30.0, "unit": "lb/ac", "form": "P2O5"},
        "potassium": {"value": 20.0, "unit": "kg/ha", "form": "K2O"},
    }
    _write(tmp_path, ext)
    return tmp_path


def test_report_has_one_section_per_kind_in_order(tmp_path: Path) -> None:
    report = run_report(_mixed_dir(tmp_path), PACKS_DIR)
    heads = [
        report.index("## sample (1)"),
        report.index("## agronomist_approved (2)"),
        report.index("## external_reference (1)"),
    ]
    assert heads == sorted(heads)
    assert heads[0] < report.index("== s1") < heads[1]
    assert heads[1] < report.index("== a_ok") < heads[2]
    assert heads[2] < report.index("== e1")


def test_report_empty_sections_say_none(tmp_path: Path) -> None:
    _write(tmp_path, {**_case_data(), "id": "s1"})
    report = run_report(tmp_path, PACKS_DIR)
    assert "## agronomist_approved (0)" in report
    assert "## external_reference (0)" in report
    assert "## ai_reviewed (0)" in report
    assert report.count("(none)") == 3
    assert "## errors" not in report


def test_agreement_counts_only_approved_cases(tmp_path: Path) -> None:
    report = run_report(_mixed_dir(tmp_path), PACKS_DIR)
    assert (
        "agreement gate (agronomist_approved only): 1/2 = 50.0% — gate not enforced yet" in report
    )
    assert "target" not in report.lower()


def test_agreement_with_no_approved_cases(tmp_path: Path) -> None:
    _write(tmp_path, {**_case_data(), "id": "s1"})
    report = run_report(tmp_path, PACKS_DIR)
    assert "agreement gate (agronomist_approved only): 0/0 = n/a — gate not enforced yet" in report


def test_agreement_target_only_from_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _mixed_dir(tmp_path)
    args = ["--golden-dir", str(tmp_path), "--packs-dir", str(PACKS_DIR)]
    assert main([*args, "--agreement-target", "0.9"]) == 0
    out = capsys.readouterr().out
    assert "target 90.0% (from --agreement-target), not met" in out
    assert main([*args, "--agreement-target", "0.5"]) == 0
    assert "target 50.0% (from --agreement-target), met" in capsys.readouterr().out


def test_agreement_target_must_be_a_fraction(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--golden-dir", str(GOLDEN_DIR), "--agreement-target", "90"])


def test_external_comparison_converts_lb_per_ac(placeholder_pack) -> None:
    case = parse_golden_case(_external_data())
    assert isinstance(case, ExternalReferenceCase)
    rec = recommend(case.input, placeholder_pack)
    rows = {r.field: r for r in compare_external(case, rec)}
    n = rows["n_rate"]
    assert n.reference == "100.0 lb/ac"
    assert n.reference_kg_ha == pytest.approx(units.lb_per_ac_to_kg_per_ha(100.0))
    assert n.engine_kg_ha == pytest.approx(rec.nitrogen.rate.value)
    assert n.diff_kg_ha == pytest.approx(n.engine_kg_ha - n.reference_kg_ha)


def test_external_comparison_splits_by_position(placeholder_pack) -> None:
    ref = {
        "n_rate": {"value": 150.0, "unit": "kg/ha"},
        "n_splits": [{"value": 150.0, "unit": "kg/ha", "timing": "pre-plant"}],
    }
    case = parse_golden_case(_external_data(reference_output=ref))
    assert isinstance(case, ExternalReferenceCase)
    rec = recommend(case.input, placeholder_pack)
    rows = {r.field: r for r in compare_external(case, rec)}
    assert rows["split_1"].reference_kg_ha == 150.0
    assert rows["split_2"].reference_kg_ha is None
    assert rows["split_2"].engine_kg_ha == pytest.approx(rec.nitrogen.splits[1].rate.value)


def test_report_external_section_is_information_only(tmp_path: Path) -> None:
    report = run_report(_mixed_dir(tmp_path), PACKS_DIR)
    ext = report[report.index("## external_reference") :]
    assert "information only — reference is not ground truth" in ext
    assert "100.0 lb/ac" in ext
    assert f"{units.lb_per_ac_to_kg_per_ha(100.0):.1f}" in ext
    assert "30.0 lb/ac P2O5" in ext and "20.0 kg/ha K2O" in ext
    assert ext.count("reference only, not compared") == 2
    assert "Test Tool" in ext and "2026-11-16" in ext and "Test Region" in ext


def test_report_errors_have_their_own_section(tmp_path: Path) -> None:
    _mixed_dir(tmp_path)
    (tmp_path / "broken.yaml").write_text("id: broken\n", encoding="utf-8")
    report = run_report(tmp_path, PACKS_DIR)
    errors = report[report.index("## errors (1)") :]
    assert "== broken.yaml  ERROR" in errors


# --- ai_reviewed cases, document citations, template ------------------------------


def _document_source(**change: object) -> dict[str, Any]:
    """A citation of a published document. TEST FIXTURE ONLY, not a real document."""
    src: dict[str, Any] = {
        "title": "Test Guide",
        "publisher": "Test Publisher",
        "year": 2025,
        "locator": "Table 1, p. 2",
        "url": "https://example.invalid/test-guide",
    }
    src.update(change)
    return src


def _ai_data(**top: object) -> dict[str, Any]:
    data = _external_data(
        id="t_ai", kind="ai_reviewed", entered_by="cp-agronomist", source=_document_source()
    )
    data.update(top)
    return data


def test_ai_reviewed_case_loads_with_reference_shape() -> None:
    case = parse_golden_case(_ai_data())
    assert isinstance(case, ExternalReferenceCase)
    assert case.kind == GoldenKind.AI_REVIEWED
    assert case.entered_by == "cp-agronomist"


def test_ai_reviewed_case_has_no_expected_block() -> None:
    with pytest.raises(ValidationError):
        parse_golden_case(_ai_data(expected=_case_data()["expected"]))


def test_ai_reviewed_must_be_entered_by_the_ai_agronomist() -> None:
    with pytest.raises(ValidationError, match="cp-agronomist"):
        parse_golden_case(_ai_data(entered_by="Test Person"))


def test_external_reference_cannot_be_entered_by_the_ai_agronomist() -> None:
    # A case the AI drafts is ai_reviewed (rule 11), never external_reference.
    with pytest.raises(ValidationError, match="ai_reviewed"):
        parse_golden_case(_external_data(entered_by="cp-agronomist"))


def test_document_citation_loads() -> None:
    case = parse_golden_case(_external_data(source=_document_source()))
    assert isinstance(case, ExternalReferenceCase)
    assert case.source.title == "Test Guide"
    assert case.source.year == 2025
    assert case.source.locator == "Table 1, p. 2"


@pytest.mark.parametrize("missing", ["publisher", "year", "locator", "url"])
def test_document_citation_needs_every_field(missing: str) -> None:
    src = _document_source()
    del src[missing]
    with pytest.raises(ValidationError):
        parse_golden_case(_external_data(source=src))


def test_source_needs_a_tool_or_a_title() -> None:
    with pytest.raises(ValidationError):
        parse_golden_case(_external_data(source={"url": "https://example.invalid"}))


@pytest.mark.parametrize(
    "settings",
    [
        {"yield_display_unit": "bu/ac"},
        {"yield_display_unit": "t/ha", "price_ratio": "0.1"},
        {"include_fungicide": True},
    ],
)
def test_tool_settings_display_only_allowed(settings: dict[str, object]) -> None:
    case = parse_golden_case(_external_data(tool_settings=settings))
    assert isinstance(case, ExternalReferenceCase)


@pytest.mark.parametrize(
    "settings",
    [
        {"target_yield_bu_ac": 90},
        {"yield": "90 bu/ac"},
        {"yield_display_unit": "bushels"},
        {"n_rate": 120},
    ],
)
def test_tool_settings_never_store_yield_or_numbers(settings: dict[str, object]) -> None:
    # Yield is stored only as input.target_yield_t_ha; bu/ac is a display setting.
    with pytest.raises(ValidationError):
        parse_golden_case(_external_data(tool_settings=settings))


def test_report_ai_reviewed_section_is_information_only(tmp_path: Path) -> None:
    _mixed_dir(tmp_path)
    _write(tmp_path, _ai_data(id="ai1"))
    report = run_report(tmp_path, PACKS_DIR)
    ext_head = report.index("## external_reference (1)")
    ai_head = report.index("## ai_reviewed (1)")
    assert ext_head < ai_head < report.index("== ai1")
    ai = report[ai_head:]
    assert "drafted by cp-agronomist (AI), not agronomist validation" in ai
    assert "Test Guide" in ai and "Table 1, p. 2" in ai
    # Diff only: the table has no pass/fail column; never counted toward agreement.
    block = ai[ai.index("== ai1") :].splitlines()
    header = next(line for line in block if "engine kg/ha" in line)
    assert not header.rstrip().endswith("ok")
    assert "1/2 = 50.0%" in report


TEMPLATE = GOLDEN_DIR / "_template.yaml"


def test_template_exists_and_is_skipped() -> None:
    assert TEMPLATE.is_file()
    assert TEMPLATE not in golden_paths(GOLDEN_DIR)


def test_template_covers_the_reference_case_fields() -> None:
    data = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    assert data["kind"] == "external_reference"
    fields = set(ExternalReferenceCase.model_fields)
    assert set(data) <= fields
    required = {n for n, f in ExternalReferenceCase.model_fields.items() if f.is_required()}
    assert required <= set(data)
    assert set(data["source"]) >= {"title", "publisher", "year", "locator", "url"}
    assert "target_yield_t_ha" in data["input"]
    assert not any("bu" in key for key in data["input"])


def test_template_fails_validation_until_filled_in() -> None:
    # Copying the template without entering a real reference must not load silently.
    data = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    with pytest.raises(ValueError):
        parse_golden_case(data)
