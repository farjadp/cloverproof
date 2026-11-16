"""Licence allowlist check with SPDX expression support (XD-07 / DD-06).

Reads `pip-licenses --format=json` output and fails if any package licence is not allowed.
- SPDX expressions are evaluated: AND binds tighter than OR; parentheses supported.
  `A AND B` passes only if both are allowed; `A OR B` passes if either is.
  `X WITH exception` is judged on X (an exception only adds permissions).
- Classifier lists joined by "; " (pip-licenses --from=mixed) are treated as AND (conservative).
- A whole string that is itself on the allowlist (e.g. "MIT License") passes.
- Anything unparsable or UNKNOWN fails.

Named exceptions (--exception NAME=LICENCE) pass only while that package keeps exactly that
licence string; each one needs an ADR + lawyer review. --ignore-prefix skips our own
workspace packages (no licence metadata).

Usage: check_licences.py --allow "MIT;BSD-3-Clause" [--ignore-prefix cloverproof-]
                         [--exception "certifi=<exact licence>"] pip-licenses.json
       check_licences.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import sys

OPERATORS = {"AND", "OR", "WITH"}
TOKEN_RE = re.compile(
    r"\(|\)|\bAND\b|\bOR\b|\bWITH\b|[^()\s]+(?:\s+(?!(?:AND|OR|WITH)\b)[^()\s]+)*"
)


class ParseError(ValueError):
    pass


def _tokens(expr: str) -> list[str]:
    return TOKEN_RE.findall(expr)


def _evaluate(tokens: list[str], allowed: set[str]) -> bool:
    pos = 0

    def peek() -> str | None:
        return tokens[pos] if pos < len(tokens) else None

    def take() -> str:
        nonlocal pos
        if pos >= len(tokens):
            raise ParseError("unexpected end of expression")
        tok = tokens[pos]
        pos += 1
        return tok

    def parse_or() -> bool:
        result = parse_and()
        while peek() == "OR":
            take()
            rhs = parse_and()
            result = result or rhs
        return result

    def parse_and() -> bool:
        result = parse_factor()
        while peek() == "AND":
            take()
            rhs = parse_factor()
            result = result and rhs
        return result

    def parse_factor() -> bool:
        tok = take()
        if tok == "(":
            value = parse_or()
            if take() != ")":
                raise ParseError("missing ')'")
        elif tok in OPERATORS or tok == ")":
            raise ParseError(f"unexpected token {tok!r}")
        else:
            value = tok in allowed
        if peek() == "WITH":
            take()
            exc = take()
            if exc in OPERATORS or exc in "()":
                raise ParseError("WITH needs an exception id")
        return value

    result = parse_or()
    if pos != len(tokens):
        raise ParseError(f"trailing tokens: {tokens[pos:]}")
    return result


def licence_allowed(licence: str, allowed: set[str]) -> bool:
    licence = (licence or "").strip()
    if not licence or licence.upper() == "UNKNOWN":
        return False
    if licence in allowed:
        return True
    parts = [p.strip() for p in licence.split(";") if p.strip()]
    try:
        return all(p in allowed or _evaluate(_tokens(p), allowed) for p in parts)
    except ParseError:
        return False


def self_test() -> int:
    allowed = {
        "MIT",
        "MIT License",
        "BSD-3-Clause",
        "0BSD",
        "Zlib",
        "CC0-1.0",
        "Apache-2.0",
        "Apache Software License",
    }
    cases = [
        ("BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0", True),  # numpy 2.5.5
        ("Apache Software License; MIT License", True),
        ("(MIT OR GPL-3.0-only)", True),
        ("Apache-2.0 WITH LLVM-exception", True),
        ("GPL-3.0-only", False),
        ("MIT AND GPL-2.0-or-later", False),
        ("AGPL-3.0-only OR EUPL-1.2", False),
        ("LGPL-3.0-only", False),
        ("UNKNOWN", False),
        ("", False),
        ("MIT AND (", False),
    ]
    failed = [(lic, exp) for lic, exp in cases if licence_allowed(lic, allowed) != exp]
    for lic, exp in failed:
        print(f"SELF-TEST FAIL: {lic!r} expected {'allowed' if exp else 'rejected'}")
    print(f"self-test: {len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow", help="semicolon-separated allowlist (exact names)")
    parser.add_argument(
        "--ignore-prefix",
        action="append",
        default=[],
        help="skip packages whose name starts with this (our own code)",
    )
    parser.add_argument(
        "--exception",
        action="append",
        default=[],
        help="NAME=LICENCE: allow this package only with exactly this licence",
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("report", nargs="?", help="pip-licenses JSON file")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.allow or not args.report:
        parser.error("--allow and report are required")
    allowed = {a.strip() for a in args.allow.split(";") if a.strip()}
    with open(args.report, encoding="utf-8") as fh:
        packages = json.load(fh)
    exceptions = dict(e.split("=", 1) for e in args.exception)
    packages = [
        p
        for p in packages
        if not any(p.get("Name", "").startswith(pre) for pre in args.ignore_prefix)
    ]

    def ok(p: dict) -> bool:
        name, lic = p.get("Name", ""), p.get("License", "")
        if name in exceptions:
            return lic == exceptions[name]
        return licence_allowed(lic, allowed)

    bad = [p for p in packages if not ok(p)]
    for p in packages:
        mark = "FAIL" if p in bad else "ok  "
        print(f"{mark} {p.get('Name')} {p.get('Version')}: {p.get('License')}")
    if bad:
        print(
            f"\n{len(bad)} package(s) with a licence outside the allowlist "
            "(copyleft/unknown needs an ADR + lawyer before it may ship)."
        )
        return 1
    print(f"\nall {len(packages)} packages allowed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
