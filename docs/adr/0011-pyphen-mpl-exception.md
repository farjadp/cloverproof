# ADR 0011 — Named licence exception: `pyphen` (used under MPL-1.1) for proof PDFs

- Status: **Proposed** (2026-11-17). Not in force: the licence check stays red until Farjad Iranmehr and `ciso` accept this ADR and a lawyer has reviewed it.
- Decider: Farjad Iranmehr. Author: `cloverproof-lead`. Review: `ciso`, lawyer.
- Related: ADR 0005 (proof PDF), CLAUDE.md "Licences" (no GPL/AGPL/EUPL; LGPL only by name; any other exception needs an ADR first), `.github/workflows/security.yml` (licence job).

## Context
Proof PDF v0 (PR #40, merged) renders with WeasyPrint (BSD-3-Clause). WeasyPrint lists `Pyphen>=0.9.1` as a required dependency and imports it at module load (`weasyprint/text/line_break.py: import pyphen`); it is used for CSS `hyphens: auto`. WeasyPrint cannot be installed or imported without it, so excluding it is not possible without patching or stubbing a third-party package (rejected: fragile and hides a real dependency).

`pyphen` 0.18.1 is distributed under a choice of **GPL-2.0-or-later OR LGPL-2.1-or-later OR MPL-1.1** (its wheel ships COPYING.GPL, COPYING.LGPL, COPYING.MPL). A recipient may pick one. It also bundles ~80 hyphenation dictionaries (from LibreOffice) with their own per-file licences (e.g. `hyph_en_US`: BSD-style; others vary, some LGPL/GPL/MPL).

## Decision (proposed)
1. Use `pyphen` **under MPL-1.1**, unmodified, as an installed dependency of WeasyPrint. MPL-1.1 is file-level copyleft: obligations apply only to modified MPL files; we do not modify or vendor them.
2. Add a named exception in the licence job pinned to the exact package and licence string (like `certifi`), not a general allowlist entry. Any version bump re-checks the string.
3. Proof PDFs are English only and our CSS does not use `hyphens: auto`, so no dictionary is loaded at run time. If hyphenation or another language is enabled later, check the licence of each dictionary used first.
4. Record the choice in the third-party notices with the MPL-1.1 text and the source URL.

## Alternatives
- **Exclude pyphen:** not possible (hard import). 
- **Another PDF engine:** ReportLab (BSD) means rewriting templates in Python drawing code; headless Chromium adds a large binary and service. Both cost more than this exception.
- **Patch/stub pyphen:** rejected (fragile, misleading licence picture).

## Consequences
- Licence job: `--exception "pyphen=<exact string from pip-licenses>"` added only after acceptance (ciso owns the checker).
- System libraries pango/harfbuzz (LGPL) used at run time by WeasyPrint fall under the same review as libvips (CLAUDE.md "LGPL only by name") — to be named in the same lawyer review.

## Needs
1. Farjad Iranmehr: accept or reject. 2. `ciso`: review and add the exception. 3. Lawyer: confirm the MPL-1.1 election for unmodified use and the pango/harfbuzz runtime use.
