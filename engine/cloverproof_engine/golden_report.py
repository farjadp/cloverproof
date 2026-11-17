"""Golden report CLI. Prints expected vs actual per number; always exits 0.

    uv run python -m cloverproof_engine.golden_report \
        --golden-dir engine/tests/golden --packs-dir packs [--agreement-target 0.9]

One section per kind, in a fixed order:
- `sample`, `agronomist_approved`: expected vs actual with an ok column (they assert).
- `external_reference`, `ai_reviewed`: engine vs reference difference only, no
  pass/fail (information only; the reference is not ground truth).
- `errors`: files that failed to load or run (only when there are any).

The agreement line counts `agronomist_approved` cases only. The gate is not
enforced: the target, if any, comes from `--agreement-target`, never from code.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from cloverproof_engine import recommend
from cloverproof_engine.golden import (
    AI_AGRONOMIST,
    ExpectedCase,
    ExternalReferenceCase,
    GoldenKind,
    case_agrees,
    compare,
    compare_external,
    format_case,
    format_error,
    format_external,
)
from cloverproof_engine.loaders import golden_paths, load_golden_case, load_pack, pack_path
from cloverproof_engine.version import ENGINE_VERSION

_CASE_ERRORS = (OSError, ValueError, KeyError, TypeError, yaml.YAMLError)

_SECTION_ORDER = (
    GoldenKind.SAMPLE,
    GoldenKind.AGRONOMIST_APPROVED,
    GoldenKind.EXTERNAL_REFERENCE,
    GoldenKind.AI_REVIEWED,
)

_SECTION_NOTE = {
    GoldenKind.SAMPLE: "derived from a pack by hand to exercise the report; never counts",
    GoldenKind.AGRONOMIST_APPROVED: "the agronomist's decisions; the only kind that counts",
    GoldenKind.EXTERNAL_REFERENCE: "information only — reference is not ground truth",
    GoldenKind.AI_REVIEWED: (
        f"information only — drafted by {AI_AGRONOMIST} (AI), not agronomist validation; "
        "never counts"
    ),
}


def _agreement_line(agreed: int, total: int, target: float | None) -> str:
    share = "n/a" if total == 0 else f"{agreed / total:.1%}"
    line = f"agreement gate (agronomist_approved only): {agreed}/{total} = {share}"
    if target is not None:
        met = total > 0 and agreed / total >= target
        line += f" — target {target:.1%} (from --agreement-target), {'met' if met else 'not met'}"
    return line + " — gate not enforced yet"


def run_report(
    golden_dir: str | Path, packs_dir: str | Path, agreement_target: float | None = None
) -> str:
    paths = golden_paths(golden_dir)
    sections: dict[GoldenKind, list[str]] = {kind: [] for kind in _SECTION_ORDER}
    errors: list[str] = []
    numbers_ok = numbers_total = labels_ok = labels_total = 0
    approved_total = approved_agree = 0

    for path in paths:
        try:
            case = load_golden_case(path)
            pack = load_pack(pack_path(packs_dir, case.pack.id, case.pack.version))
            rec = recommend(case.input, pack)
        except _CASE_ERRORS as exc:
            errors.append(format_error(path.name, f"{type(exc).__name__}: {exc}"))
            continue
        kind = GoldenKind(case.kind)
        if isinstance(case, ExternalReferenceCase):
            sections[kind].append(format_external(case, compare_external(case, rec), rec))
            continue
        assert isinstance(case, ExpectedCase)
        rows = compare(case, rec)
        for r in rows:
            if r.kind == "number":
                numbers_total += 1
                numbers_ok += r.ok
            else:
                labels_total += 1
                labels_ok += r.ok
        if kind is GoldenKind.AGRONOMIST_APPROVED:
            approved_total += 1
            approved_agree += case_agrees(rows)
        sections[kind].append(format_case(case, rows, rec))

    blocks: list[str] = [
        f"Golden report - engine {ENGINE_VERSION} - {len(paths)} case(s) in {golden_dir}",
        "Report only: differences never fail the build (yet).",
        "",
    ]
    for kind in _SECTION_ORDER:
        cases = sections[kind]
        blocks += [f"## {kind.value} ({len(cases)}) — {_SECTION_NOTE[kind]}", ""]
        if not cases:
            blocks += ["(none)", ""]
        for block in cases:
            blocks += [block, ""]
    if errors:
        blocks += [f"## errors ({len(errors)})", ""]
        for block in errors:
            blocks += [block, ""]
    blocks.append(
        f"Summary: {len(paths)} case(s), {len(errors)} error(s), "
        f"{numbers_ok}/{numbers_total} numbers within tolerance, "
        f"{labels_ok}/{labels_total} labels match (sample + agronomist_approved)."
    )
    blocks.append(_agreement_line(approved_agree, approved_total, agreement_target))
    return "\n".join(blocks)


def _fraction(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not 0 < value <= 1:
        raise argparse.ArgumentTypeError("must be a fraction in (0, 1], e.g. 0.9")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--golden-dir", default="engine/tests/golden")
    parser.add_argument("--packs-dir", default="packs")
    parser.add_argument(
        "--agreement-target",
        type=_fraction,
        default=None,
        help="optional agreement share to compare against (0-1); not enforced",
    )
    args = parser.parse_args(argv)
    try:
        print(run_report(args.golden_dir, args.packs_dir, args.agreement_target))
    except _CASE_ERRORS as exc:
        print(format_error(str(args.golden_dir), f"{type(exc).__name__}: {exc}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
