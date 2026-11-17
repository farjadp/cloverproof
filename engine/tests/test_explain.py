"""Explanations: every quoted pack constant carries its own status tag."""

from cloverproof_engine import explain
from cloverproof_engine.pack import ConstantStatus, PackConstant

PLACEHOLDER_TAG = "(PLACEHOLDER, not agronomist-validated)"
SOURCE = "TEST FIXTURE ONLY - not a real source"
SOURCE_TAG = f"(source: {SOURCE})"


def _placeholder(value: float, unit: str) -> PackConstant:
    return PackConstant(value=value, unit=unit, status=ConstantStatus.PLACEHOLDER, source=None)


def _validated(value: float, unit: str) -> PackConstant:
    return PackConstant(value=value, unit=unit, status=ConstantStatus.VALIDATED, source=SOURCE)


def test_n_rate_within_limits_tags_min_and_max_separately() -> None:
    text = explain.n_rate(
        raw=150.0,
        rate=150.0,
        bound=None,
        min_rate=_validated(10.0, "kg N/ha"),
        max_rate=_placeholder(200.0, "kg N/ha"),
    )
    assert f"10.0 kg N/ha {SOURCE_TAG}" in text
    assert f"200.0 kg N/ha {PLACEHOLDER_TAG}" in text


def test_n_rate_within_limits_tags_placeholder_min() -> None:
    text = explain.n_rate(
        raw=150.0,
        rate=150.0,
        bound=None,
        min_rate=_placeholder(10.0, "kg N/ha"),
        max_rate=_validated(200.0, "kg N/ha"),
    )
    assert f"10.0 kg N/ha {PLACEHOLDER_TAG}" in text
    assert f"200.0 kg N/ha {SOURCE_TAG}" in text


def test_c4_tags_both_yield_bounds_separately() -> None:
    text = explain.c4_target_yield_implausible(
        12.0, _validated(2.0, "t/ha"), _placeholder(10.0, "t/ha")
    )
    assert f"2.0 t/ha {SOURCE_TAG}" in text
    assert f"10.0 t/ha {PLACEHOLDER_TAG}" in text


def test_c4_tags_placeholder_lower_bound() -> None:
    text = explain.c4_target_yield_implausible(
        1.0, _placeholder(2.0, "t/ha"), _validated(10.0, "t/ha")
    )
    assert f"2.0 t/ha {PLACEHOLDER_TAG}" in text
    assert f"10.0 t/ha {SOURCE_TAG}" in text


# --- citation basis (stated / derived / inferred) ---------------------------------


def _cited(basis: str, note: str | None = None) -> PackConstant:
    """TEST FIXTURE ONLY: not a real document."""
    return PackConstant.model_validate(
        {
            "value": 5.0,
            "unit": "kg N/ha",
            "status": "PLACEHOLDER",
            "source": None,
            "citation": {
                "title": "Test Guide",
                "publisher": "Test Publisher",
                "year": 2025,
                "locator": "Table 1",
                "url": "https://example.invalid/guide",
                "accessed_on": "2026-11-17",
                "basis": basis,
                "note": note,
            },
        }
    )


def test_tag_stated_value_reads_from_the_source() -> None:
    text = explain.tag(_cited("stated"))
    assert "read from Test Guide, Table 1" in text
    assert "PLACEHOLDER" in text
    assert "inferred" not in text


def test_tag_inferred_value_never_says_read_from() -> None:
    text = explain.tag(_cited("inferred", note="Test note."))
    assert "read from" not in text
    assert "inferred by the engine from Test Guide, Table 1, not a value stated there" in text
    assert "Test note." in text


def test_tag_derived_value_never_says_read_from() -> None:
    text = explain.tag(_cited("derived", note="Largest test cell."))
    assert "read from" not in text
    assert "inferred by the engine from Test Guide, Table 1, not a value stated there" in text
    assert "Largest test cell." in text
