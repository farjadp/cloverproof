# Data backlog (Phase 3/4)

Owner: `head-of-data`. Licence details: `docs/data-sources.md` (last checked 2026-11-16).

Rules for every item below:
- None may produce a P or K rate without a soil test (CLAUDE.md hard rule 3). Without a test: N only, max `medium` confidence; for P/K recommend a test.
- Every estimated soil value stores: source, version, resolution, depth and retrieval date (plus `source = estimate`).
- Farmers own their farm data. Pre-filled values are suggestions the farmer or agronomist confirms; no number reaches a farmer without agronomist approval.
- No invented agronomic constants; use labelled `PLACEHOLDER` plus `TODO(agronomist)`.
- Every item needs a lawyer-review sign-off on its source before production use.

| item | goal | source | licence note | size | dependency | phase |
|---|---|---|---|---|---|---|
| FTW field-boundary pre-fill | Offer a suggested boundary when a farmer adds a field; Canada/Ontario subset first. Fields are remote-sensing units, not legal parcels; farmer confirms. Stores boundary source/version/date. | FTW Global (https://source.coop/ftw/global-data) | CC-BY-4.0 for the global set only; benchmark and Wherobots sets include non-commercial data: exclude. Exact attribution wording to copy at download | M | Farmer portal and field geometry model; lawyer review; hosting/storage decision for the subset | 4 |
| Previous-crop suggestion (AAFC Canada, EuroCrops EU) | Pre-suggest previous crop for rotation/N credit; farmer confirms. Canada first via AAFC ACI. | AAFC ACI (open.canada.ca); EuroCrops v2.0 | AAFC: OGL-Canada (confirm per year). EuroCrops: CC BY 4.0 per paper, per-agency licences unverified (unknown) | M (AAFC), L (EuroCrops) | Field geometry; FTW or farmer-drawn boundary; EU country pack for EuroCrops; per-agency licence check | 4 |
| Docling lab-report extraction spike | Test whether Docling extracts soil-test tables (value, unit, P/K form, method, depth, date) from lab PDFs. Output is a draft for human check, never auto-accepted. | Docling (https://github.com/docling-project/docling) | MIT code; model-weight licences unknown | M | About 30 real lab reports with farmer consent first. OCR/LLM reading is out of scope until CLAUDE.md allows it: do not start before that change | 3/4 |
| WoSIS import with mandatory licence filter | Offline reference set of profiles with P by extraction method, for sanity checks of estimates. Keep only rows with a commercially usable licence. | WoSIS (https://www.isric.org/explore/wosis) | Licence per profile: CC BY or CC BY-NC; drop CC BY-NC and unknown; store licence per row; add a test that fails if a non-allowed licence enters | M | Licence allowlist approved by lawyer; extraction-method mapping (Olsen/Bray-1/Mehlich-3/other) reviewed by agronomist | 4 |
| PCSE phenology validation notebook | Offline notebook comparing wheat phenology against PCSE/WOFOST. Never imported into production code. | PCSE (https://github.com/ajwdewit/pcse) | EUPL; redistribution and commercial terms unknown; lawyer before any production import. Notebook outside `engine/` | S | Agronomist chooses wheat cases; weather inputs are out of scope (no weather APIs) so use supplied test files only | 3 |

## Open questions
- Which SoilGrids layers and depth intervals feed no-test mode (agronomist decision; see `docs/data-sources.md` for caching rule).
- Where do cached grids live (repo is not the place; storage ADR needed).
