"""File loaders: the only module in the engine that reads files.

Calculation code takes already-loaded objects; nothing here calculates.
"""

from pathlib import Path
from typing import Any

import yaml

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
