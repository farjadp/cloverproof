"""Split plan from the pack (S2-ENG-04): one line per application, or one full-rate line.

Every pack number here is a TEST FIXTURE or a PLACEHOLDER pack value, not agronomy.
"""

import copy
import math
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from cloverproof_engine import recommend
from cloverproof_engine.golden import ExpectedCase, compare
from cloverproof_engine.loaders import load_golden_case, load_pack, pack_path, read_yaml
from cloverproof_engine.models import RecommendationInput
from cloverproof_engine.pack import CitationBasis, ConstantStatus, Pack, pack_sha256, parse_pack
from cloverproof_engine.results import Recommendation

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKS_DIR = REPO_ROOT / "packs"
GOLDEN_DIR = REPO_ROOT / "engine" / "tests" / "golden"
V0_PATH = PACKS_DIR / "placeholder" / "v0.yaml"
CA_ON_PATH = PACKS_DIR / "ca-on" / "v1.yaml"

# Fingerprint of packs/ca-on/v1.yaml before the split plan work (engine 0.3.0).
CA_ON_V1_SHA256 = "84d874e7c6f0119cfeb44e5c5de8a9dfe04e3e9961a0dae0819cd856b1996e58"


def _raw() -> dict[str, Any]:
    return copy.deepcopy(read_yaml(V0_PATH))


def _without_splits(**nitrogen: Any) -> Pack:
    data = _raw()
    del data["crops"]["wheat"]["nitrogen"]["splits"]
    data["crops"]["wheat"]["nitrogen"].update(nitrogen)
    return parse_pack(data)


def _with_empty_splits() -> Pack:
    return _without_splits(splits=[])


def _with_fractions(*values: float) -> Pack:
    """TEST FIXTURE: the placeholder pack with other split fractions."""
    data = _raw()
    data["crops"]["wheat"]["nitrogen"]["splits"] = [
        {
            "stage_label": f"Stage {i} (TEST)",
            "fraction": {"value": v, "unit": "fraction", "status": "PLACEHOLDER", "source": None},
        }
        for i, v in enumerate(values, 1)
    ]
    return parse_pack(data)


def _ca_on_input() -> RecommendationInput:
    return RecommendationInput.model_validate(
        {
            "crop": "wheat",
            "target_yield_t_ha": 6.0,
            "previous_crop": "corn",
            "area_ha": 10.0,
            "plan_date": date(2027, 3, 1),
            # TEST FIXTURE ONLY: not real prices.
            "n_price": {
                "n_price_per_kg_n": 1.25,
                "grain_price_per_kg": 0.25,
                "currency": "CAD",
                "source": "TEST FIXTURE",
                "price_date": "2027-01-20",
            },
            "wheat_class": "pastry",
            "manure_applied": False,
        }
    )


# --- pack with splits -----------------------------------------------------------


def test_lines_sum_to_the_rate_and_carry_rate_share_window_explanation(make_input) -> None:
    pack = load_pack(V0_PATH)
    n = recommend(make_input(target_yield_t_ha=5.3), pack).nitrogen
    specs = pack.crops["wheat"].nitrogen.splits
    assert len(n.splits) == len(specs)
    assert math.isclose(sum(s.rate.value for s in n.splits), n.rate.value)
    assert math.isclose(sum(s.total.value for s in n.splits), n.total.value)
    for line, spec in zip(n.splits, specs, strict=True):
        assert line.fraction.value == spec.fraction.value
        assert math.isclose(line.rate.value, n.rate.value * spec.fraction.value)
        assert line.timing_window is not None
        assert line.timing_window.label == spec.stage_label
        assert line.timing_window.status is ConstantStatus.PLACEHOLDER
        assert line.timing_window.citation is None
        assert spec.stage_label in line.explanation
        assert "PLACEHOLDER, not agronomist-validated" in line.explanation


def test_line_explanation_quotes_no_rate_so_an_edit_cannot_make_it_stale(make_input) -> None:
    # The concierge tool edits rates in a copy of this document (app planning.py).
    rec = recommend(make_input(target_yield_t_ha=5.3), load_pack(V0_PATH))
    for line in rec.nitrogen.splits:
        assert f"{line.rate.value:,.1f}" not in line.explanation
        assert "kg N" not in line.explanation


def test_cited_window_keeps_its_citation_and_basis() -> None:
    pack = load_pack(CA_ON_PATH)
    line = recommend(_ca_on_input(), pack).nitrogen.splits[0]
    spec = pack.crops["wheat"].nitrogen.splits[0]
    window = line.timing_window
    assert window is not None
    assert window.label == spec.stage_label
    assert window.status is ConstantStatus.PLACEHOLDER
    assert window.citation == spec.timing_citation
    assert window.citation is not None and window.citation.basis is CitationBasis.STATED
    assert "read from" in line.explanation
    assert "PLACEHOLDER, not agronomist-validated" in line.explanation


def test_window_of_a_validated_pack_is_not_called_placeholder(make_input, validated_pack) -> None:
    line = recommend(make_input(), validated_pack).nitrogen.splits[0]
    assert line.timing_window is not None
    assert line.timing_window.status is ConstantStatus.VALIDATED
    assert "PLACEHOLDER" not in line.explanation.replace(line.timing_window.label, "")


# --- rounding: no pack rule, so rates stay exact ----------------------------------


@pytest.mark.parametrize(
    ("fractions", "target"),
    [
        ((0.3333333333, 0.3333333333, 0.3333333334), 5.3),
        ((0.1, 0.2, 0.7), 4.7),
        ((0.15, 0.35, 0.5), 6.1),
    ],
)
def test_awkward_shares_sum_to_the_rate_without_rounding(
    make_input, fractions: tuple[float, ...], target: float
) -> None:
    n = recommend(make_input(target_yield_t_ha=target), _with_fractions(*fractions)).nitrogen
    assert math.isclose(sum(s.rate.value for s in n.splits), n.rate.value, rel_tol=1e-9)
    for line, fraction in zip(n.splits, fractions, strict=True):
        assert line.rate.value == n.rate.value * fraction  # exact: nothing rounded or moved


# --- pack without splits ----------------------------------------------------------


@pytest.mark.parametrize("pack_factory", [_without_splits, _with_empty_splits])
def test_no_splits_gives_one_full_rate_line_without_timing(
    make_input, pack_factory: Callable[[], Pack]
) -> None:
    n = recommend(make_input(), pack_factory()).nitrogen
    assert len(n.splits) == 1
    line = n.splits[0]
    assert line.rate.value == n.rate.value
    assert line.total.value == n.total.value
    assert line.fraction.value == 1
    assert line.timing_window is None
    for text in (line.explanation, line.fraction.explanation):
        assert "no split" in text.lower() and "pack" in text.lower()
    assert "no split" in line.stage_label.lower()
    assert "timing not set" in line.stage_label.lower()


def test_no_split_line_flags_follow_the_rate(make_input) -> None:
    n = recommend(make_input(), _without_splits()).nitrogen
    line = n.splits[0]
    assert line.rate.uses_placeholder is n.rate.uses_placeholder
    assert line.total.uses_placeholder is n.rate.uses_placeholder
    assert line.fraction.uses_placeholder is False  # structural 1, not a pack constant
    assert not any(".splits" in c.path for c in n.constants_used)


def test_absent_and_empty_splits_are_the_same_pack() -> None:
    assert pack_sha256(_without_splits()) == pack_sha256(_with_empty_splits())
    assert "splits" not in _without_splits().model_dump(mode="json")["crops"]["wheat"]["nitrogen"]


def test_splits_that_are_present_must_still_sum_to_one() -> None:
    data = _raw()
    data["crops"]["wheat"]["nitrogen"]["splits"][0]["fraction"]["value"] = 0.9
    with pytest.raises(ValueError, match="sum to 1"):
        parse_pack(data)


# --- what must not change ---------------------------------------------------------


def test_ca_on_fingerprint_is_unchanged() -> None:
    assert pack_sha256(load_pack(CA_ON_PATH)) == CA_ON_V1_SHA256


def test_placeholder_split_numbers_and_wording_are_unchanged(make_input) -> None:
    lines = recommend(make_input(), load_pack(V0_PATH)).nitrogen.splits
    assert lines[0].rate.value == pytest.approx(70.0)
    assert lines[0].rate.explanation == "Application 1 rate = 40% x 175.0 kg N/ha = 70.0 kg N/ha."
    assert lines[1].total.explanation == (
        "Application 2 total = 105.0 kg N/ha x 40.0 ha = 4,200.0 kg N."
    )


def test_documents_from_engine_0_3_0_still_load(make_input) -> None:
    doc = recommend(make_input(), load_pack(V0_PATH)).model_dump(mode="json")
    for line in doc["nitrogen"]["splits"]:
        del line["timing_window"]
        del line["explanation"]
    old = Recommendation.model_validate(doc)
    assert old.nitrogen.splits[0].timing_window is None


# --- golden cases -----------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id", ["sample_wheat_split_plan_lines", "sample_wheat_no_split_in_pack"]
)
def test_split_golden_cases_agree(case_id: str) -> None:
    case = load_golden_case(GOLDEN_DIR / f"{case_id}.yaml")
    assert isinstance(case, ExpectedCase)
    pack = load_pack(pack_path(PACKS_DIR, case.pack.id, case.pack.version))
    rows = compare(case, recommend(case.input, pack))
    assert any(r.field == "split_1_timing_window" for r in rows)
    assert [r.field for r in rows if not r.ok] == []
