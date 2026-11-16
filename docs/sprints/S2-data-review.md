# S2 — Data & AI review + retro (head-of-data)

Sprint: S2, Nov 30 – Dec 11, 2026 (work done early, Nov 16). Branch: `myca/data-s2-693748`.

## What is now true (evidence)
- Metric catalogue M1–M6 with formulas, SQL, owners, minimum n → `docs/data/metrics.md`.
- Per-sprint CPO metrics report designed (one screen, n beside every number, n < 10 suppressed) → `docs/data/sprint-metrics-report.md`.
- Calibration loop spec: unit of evidence, queries, reason-code taxonomy, minimum samples (flag: ≥ 5 plans / ≥ 3 farms, ≥ 80% same direction; proposal: ≥ 20 plans / ≥ 10 farms + bootstrap CI), proposal memo → Farjad Iranmehr → golden test first → pack version bump → cp-agronomy-guard → `docs/data/calibration-loop.md`.
- Data dictionary for all tables/views; PII classes P0–P3; PROPOSED retention; deletion options for immutable tables → `docs/data/data-dictionary.md`, `docs/data/pii-and-retention.md`.
- Read-only analytics access design (`cp_analyst`, `analytics.*` views, per-sprint CSV export, no warehouse) → `docs/data/analytics-access.md`.
- All SQL executed on throwaway local PostGIS with fictional rows; nothing touched Railway, migrations, engine or packs.

## Not done / blocked
- **SG1 (blocking for calibration):** no structured place for the agronomist's P/K numbers. Needs a product decision + cto migration before Feb 1, 2027.
- Schema gaps SG2–SG12 (see `docs/data/README.md`) are proposals awaiting CPO routing.
- PROPOSED retention periods and the deletion option need Farjad Iranmehr's decision and legal review (coo → legal-compliance-specialist).

## Decisions needed (Farjad Iranmehr via CPO)
1. Where P/K final numbers live (SG1).
2. Approve minimum-sample rule and n < 10 suppression convention.
3. Approve PROPOSED retention + pseudonymise-in-place (Option A) for erasure.
4. Agreement tolerance (agronomist-todo #10) — agronomist call, not data's.
5. Are the Dec-18 cases also entered in the tool (double-count risk, SG7)?

## S3 plan (Dec 14 – Dec 24)
- data-scientist: calibration baseline from the 5 real wheat cases (Dec 18) — per-case table, direction, reason codes; explicitly "anecdote, no proposal".
- data-analyst: first funnel + freshness sections of the report from `pilot_request`.
- data-engineer: `cp_analyst` + views as a migration proposal handed to cto/cp-database (if CPO approves SG9).

## Retro
- **Went well:** four specialists in parallel on disjoint files; every SQL was executed, which caught two real permission bugs (security_invoker view chain, view-owner grant on `pilot_request`).
- **Slowed us:** the same gaps were found four times with four numberings — needed a consolidation pass. No messaging tool in this session for cross-session notes.
- **One change for S3:** one shared gap register (`docs/data/README.md`) that specialists append to, instead of each doc carrying its own list.
