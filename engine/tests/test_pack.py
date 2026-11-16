"""Country pack: schema, labelling of every constant, loader."""

import copy
import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from cloverproof_engine.loaders import load_pack
from cloverproof_engine.models import Crop
from cloverproof_engine.pack import ConstantStatus, Pack, pack_sha256, parse_pack

PACK_PATH = Path(__file__).resolve().parents[2] / "packs" / "placeholder" / "v0.yaml"


@pytest.fixture
def raw() -> dict[str, Any]:
    return yaml.safe_load(PACK_PATH.read_text(encoding="utf-8"))


def _constants(node: Any, path: str = "") -> list[tuple[str, dict[str, Any]]]:
    """Every mapping that carries a `value` is a constant."""
    found: list[tuple[str, dict[str, Any]]] = []
    if isinstance(node, dict):
        if "value" in node:
            found.append((path, node))
        for key, child in node.items():
            if key != "value":
                found.extend(_constants(child, f"{path}.{key}"))
    elif isinstance(node, list):
        for i, child in enumerate(node):
            found.extend(_constants(child, f"{path}[{i}]"))
    return found


def _bare_numbers(node: Any, path: str = "") -> list[str]:
    """Numbers that are not the `value` of a labelled constant."""
    bad: list[str] = []
    if isinstance(node, dict):
        for key, child in node.items():
            if key == "value" and isinstance(child, int | float):
                continue
            bad.extend(_bare_numbers(child, f"{path}.{key}"))
    elif isinstance(node, list):
        for i, child in enumerate(node):
            bad.extend(_bare_numbers(child, f"{path}[{i}]"))
    elif isinstance(node, int | float) and not isinstance(node, bool):
        bad.append(path)
    return bad


def test_loads_placeholder_pack() -> None:
    pack = load_pack(PACK_PATH)
    assert isinstance(pack, Pack)
    assert pack.id == "placeholder"
    assert pack.version == "v0"
    assert pack.status == "placeholder"
    assert Crop.WHEAT in pack.crops


def test_every_constant_is_labelled_placeholder(raw: dict[str, Any]) -> None:
    constants = _constants(raw)
    assert constants, "pack has no constants"
    for path, c in constants:
        assert c.get("status") == "PLACEHOLDER", path
        assert "source" in c and c["source"] is None, path
        assert isinstance(c.get("unit"), str) and c["unit"], path


def test_no_bare_numbers_in_pack(raw: dict[str, Any]) -> None:
    assert _bare_numbers(raw) == []


def test_one_todo_agronomist_per_constant(raw: dict[str, Any]) -> None:
    text = PACK_PATH.read_text(encoding="utf-8")
    assert text.count("TODO(agronomist)") >= len(_constants(raw))


def test_split_fractions_sum_to_one() -> None:
    pack = load_pack(PACK_PATH)
    splits = pack.crops[Crop.WHEAT].nitrogen.splits
    assert math.isclose(sum(s.fraction.value for s in splits), 1.0)
    assert all(s.stage_label.strip() for s in splits)


def test_rejects_splits_not_summing_to_one(raw: dict[str, Any]) -> None:
    bad = copy.deepcopy(raw)
    bad["crops"]["wheat"]["nitrogen"]["splits"][0]["fraction"]["value"] += 0.1
    with pytest.raises(ValidationError):
        parse_pack(bad)


def test_rejects_wrong_unit(raw: dict[str, Any]) -> None:
    bad = copy.deepcopy(raw)
    bad["crops"]["wheat"]["nitrogen"]["soil_n_supply"]["unit"] = "lb N/ac"
    with pytest.raises(ValidationError):
        parse_pack(bad)


def test_rejects_unlabelled_constant(raw: dict[str, Any]) -> None:
    bad = copy.deepcopy(raw)
    del bad["crops"]["wheat"]["nitrogen"]["soil_n_supply"]["status"]
    with pytest.raises(ValidationError):
        parse_pack(bad)


def test_placeholder_constant_must_not_claim_a_source(raw: dict[str, Any]) -> None:
    bad = copy.deepcopy(raw)
    bad["crops"]["wheat"]["nitrogen"]["soil_n_supply"]["source"] = "somewhere"
    with pytest.raises(ValidationError):
        parse_pack(bad)


def test_validated_constant_needs_a_source(raw: dict[str, Any]) -> None:
    bad = copy.deepcopy(raw)
    bad["crops"]["wheat"]["nitrogen"]["soil_n_supply"]["status"] = "VALIDATED"
    with pytest.raises(ValidationError):
        parse_pack(bad)


def test_validated_pack_cannot_hold_placeholders(raw: dict[str, Any]) -> None:
    bad = copy.deepcopy(raw)
    bad["status"] = "validated"
    with pytest.raises(ValidationError):
        parse_pack(bad)


def test_min_rate_not_above_max_rate(raw: dict[str, Any]) -> None:
    bad = copy.deepcopy(raw)
    n = bad["crops"]["wheat"]["nitrogen"]
    n["min_rate"]["value"] = n["max_rate"]["value"] + 1
    with pytest.raises(ValidationError):
        parse_pack(bad)


def test_efficiency_must_be_in_unit_interval(raw: dict[str, Any]) -> None:
    bad = copy.deepcopy(raw)
    bad["crops"]["wheat"]["nitrogen"]["fertilizer_n_efficiency"]["value"] = 0
    with pytest.raises(ValidationError):
        parse_pack(bad)


def test_has_placeholders_flag() -> None:
    pack = load_pack(PACK_PATH)
    assert pack.has_placeholders
    statuses = {c.status for c in pack.iter_constants()}
    assert statuses == {ConstantStatus.PLACEHOLDER}


def test_previous_crop_options_come_from_pack() -> None:
    pack = load_pack(PACK_PATH)
    options = pack.crops[Crop.WHEAT].nitrogen.previous_crop_credits
    assert options, "pack lists no previous crops"
    assert all(key == key.strip().lower() for key in options)


# --- pack_sha256 ---------------------------------------------------------------


def test_pack_sha256_is_stable() -> None:
    first, second = load_pack(PACK_PATH), load_pack(PACK_PATH)
    digest = pack_sha256(first)
    assert digest == pack_sha256(second)
    assert len(digest) == 64
    assert all(ch in "0123456789abcdef" for ch in digest)


def test_pack_sha256_same_from_file_and_from_mapping(raw: dict[str, Any]) -> None:
    assert pack_sha256(parse_pack(raw)) == pack_sha256(load_pack(PACK_PATH))


def test_pack_sha256_ignores_yaml_layout_comments_and_key_order(
    raw: dict[str, Any], tmp_path: Path
) -> None:
    reordered = copy.deepcopy(raw)
    credits = reordered["crops"]["wheat"]["nitrogen"]["previous_crop_credits"]
    reordered["crops"]["wheat"]["nitrogen"]["previous_crop_credits"] = dict(
        reversed(list(credits.items()))
    )
    path = tmp_path / "v0.yaml"
    path.write_text(yaml.safe_dump(reordered, sort_keys=False), encoding="utf-8")
    assert pack_sha256(load_pack(path)) == pack_sha256(load_pack(PACK_PATH))


def test_pack_sha256_int_and_float_values_hash_the_same(raw: dict[str, Any]) -> None:
    as_float = copy.deepcopy(raw)
    supply = as_float["crops"]["wheat"]["nitrogen"]["soil_n_supply"]
    supply["value"] = float(supply["value"])
    assert pack_sha256(parse_pack(as_float)) == pack_sha256(parse_pack(raw))


def test_pack_sha256_changes_when_a_value_changes(raw: dict[str, Any]) -> None:
    changed = copy.deepcopy(raw)
    changed["crops"]["wheat"]["nitrogen"]["soil_n_supply"]["value"] += 1
    assert pack_sha256(parse_pack(changed)) != pack_sha256(parse_pack(raw))


def test_pack_sha256_changes_when_a_label_changes(raw: dict[str, Any]) -> None:
    changed = copy.deepcopy(raw)
    supply = changed["crops"]["wheat"]["nitrogen"]["soil_n_supply"]
    supply["status"], supply["source"] = "VALIDATED", "TEST FIXTURE ONLY"
    assert pack_sha256(parse_pack(changed)) != pack_sha256(parse_pack(raw))


def test_pack_sha256_changes_when_split_order_changes(raw: dict[str, Any]) -> None:
    changed = copy.deepcopy(raw)
    changed["crops"]["wheat"]["nitrogen"]["splits"].reverse()
    assert pack_sha256(parse_pack(changed)) != pack_sha256(parse_pack(raw))
