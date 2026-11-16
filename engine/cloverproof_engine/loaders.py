"""File loaders: the only module in the engine that reads files.

Calculation code takes already-loaded objects; nothing here calculates.
"""

from pathlib import Path
from typing import Any

import yaml

from cloverproof_engine.golden import GoldenCase
from cloverproof_engine.pack import Pack, parse_pack


def read_yaml(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_pack(path: str | Path) -> Pack:
    data = read_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: pack must be a YAML mapping")
    return parse_pack(data)


def pack_path(packs_dir: str | Path, pack_id: str, version: str) -> Path:
    """Packs live at <packs_dir>/<id>/<version>.yaml."""
    return Path(packs_dir) / pack_id / f"{version}.yaml"


def golden_paths(golden_dir: str | Path) -> list[Path]:
    """Golden case files, sorted: <golden_dir>/*.yaml."""
    directory = Path(golden_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"golden directory not found: {directory}")
    return sorted(directory.glob("*.yaml"))


def load_golden_case(path: str | Path) -> GoldenCase:
    path = Path(path)
    data = read_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: golden case must be a YAML mapping")
    case = GoldenCase.model_validate(data)
    if case.id != path.stem:
        raise ValueError(f"{path}: id {case.id!r} must equal the file name {path.stem!r}")
    return case


def load_golden_cases(golden_dir: str | Path) -> list[tuple[Path, GoldenCase]]:
    return [(p, load_golden_case(p)) for p in golden_paths(golden_dir)]
