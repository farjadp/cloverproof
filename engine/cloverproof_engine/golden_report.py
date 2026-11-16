"""Golden report CLI. Prints expected vs actual per number; always exits 0.

    uv run python -m cloverproof_engine.golden_report \
        --golden-dir engine/tests/golden --packs-dir packs
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from cloverproof_engine import recommend
from cloverproof_engine.golden import compare, format_case, format_error
from cloverproof_engine.loaders import golden_paths, load_golden_case, load_pack, pack_path
from cloverproof_engine.version import ENGINE_VERSION

_CASE_ERRORS = (OSError, ValueError, KeyError, TypeError, yaml.YAMLError)


def run_report(golden_dir: str | Path, packs_dir: str | Path) -> str:
    paths = golden_paths(golden_dir)
    blocks: list[str] = [
        f"Golden report - engine {ENGINE_VERSION} - {len(paths)} case(s) in {golden_dir}",
        "Report only: differences never fail the build (yet).",
        "",
    ]
    errors = numbers_ok = numbers_total = labels_ok = labels_total = 0
    for path in paths:
        try:
            case = load_golden_case(path)
            pack = load_pack(pack_path(packs_dir, case.pack.id, case.pack.version))
            rec = recommend(case.input, pack)
        except _CASE_ERRORS as exc:
            errors += 1
            blocks += [format_error(path.name, f"{type(exc).__name__}: {exc}"), ""]
            continue
        rows = compare(case, rec)
        for r in rows:
            if r.kind == "number":
                numbers_total += 1
                numbers_ok += r.ok
            else:
                labels_total += 1
                labels_ok += r.ok
        blocks += [format_case(case, rows, rec), ""]
    blocks.append(
        f"Summary: {len(paths)} case(s), {errors} error(s), "
        f"{numbers_ok}/{numbers_total} numbers within tolerance, "
        f"{labels_ok}/{labels_total} labels match."
    )
    return "\n".join(blocks)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--golden-dir", default="engine/tests/golden")
    parser.add_argument("--packs-dir", default="packs")
    args = parser.parse_args(argv)
    try:
        print(run_report(args.golden_dir, args.packs_dir))
    except _CASE_ERRORS as exc:
        print(format_error(str(args.golden_dir), f"{type(exc).__name__}: {exc}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
