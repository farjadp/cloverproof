"""Guard: no agronomic numbers hard-coded in engine code.

Only 0 and 1 may appear as numeric literals outside units.py (which holds
chemistry and unit-definition facts and is covered by its own tests).
"""

import ast
from pathlib import Path

import cloverproof_engine

PACKAGE_DIR = Path(cloverproof_engine.__file__).resolve().parent
ALLOWED = {0, 1}
EXEMPT = {"units.py"}


def test_no_numeric_literals_outside_units() -> None:
    offenders: list[str] = []
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        if path.name in EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, int | float)
                and not isinstance(node.value, bool)
                and node.value not in ALLOWED
            ):
                offenders.append(f"{path.relative_to(PACKAGE_DIR)}:{node.lineno} {node.value!r}")
    assert offenders == []
