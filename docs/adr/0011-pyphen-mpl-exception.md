# ADR 0011 — Named licence exception: `pyphen` (used under MPL-1.1) for proof PDFs

- Status: **Accepted** by Farjad Iranmehr (2026-11-17), pending `ciso` review and lawyer review (same footing as psycopg / libvips / certifi). The named exception is in the licence job, pinned to pyphen's exact licence string.
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

## CISO review (2026-11-17): ACCEPT
- **Election:** MPL-1.1 is the right pick of the three. It is file-level copyleft and we use pyphen unmodified as an installed dependency. Its obligations (keep notices, offer source for modified MPL files) are met by the third-party notice in Decision §4. Do not vendor, patch or copy pyphen files.
- **CI:** the named exception is in `.github/workflows/security.yml`, pinned to pyphen's exact tri-licence string. The checker (`.github/scripts/check_licences.py`) matches a named exception only on that exact string and never evaluates its GPL/LGPL parts, so this does not open the allowlist. A licence-string change on upgrade fails the job, which is intended.
- **Dictionaries:** this is the real residual risk. Some bundled dictionaries are GPL/LGPL. Keep `hyphens: auto` out of proof CSS and keep PDFs English-only. Any PR that enables hyphenation or another PDF language must name the dictionary and its licence. `cp-pdf` checks this when reviewing proof templates.
- **Not covered by CI:** system libraries are installed by the OS/Docker image, not pip or npm, so the licence job does not see them. They are tracked by name in `docs/security/licence-exceptions.md`, and pango is on the lawyer list there.
- **Correction to Consequences:** HarfBuzz is "Old MIT" (permissive), not LGPL, per its COPYING. Pango is LGPL. It is listed for the lawyer anyway for completeness.
