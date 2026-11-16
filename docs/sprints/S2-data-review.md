# S2 — Data & AI review + retro (head-of-data)

Sprint: S2, Nov 30 – Dec 11, 2026 (work done early, Nov 16). Branch: `myca/data-s2-693748`.

## What is now true (evidence)
- Metric catalogue M1–M6 with formulas, SQL, owners, minimum n → `docs/data/metrics.md`.
- Per-sprint CPO metrics report designed (one screen, n beside every number, n < 10 suppressed) → `docs/data/sprint-metrics-report.md`.
- Calibration loop spec: unit of evidence, queries, reason-code taxonomy, minimum samples (flag: ≥ 5 plans / ≥ 3 farms, ≥ 80% same direction; proposal: ≥ 20 plans / ≥ 10 farms + bootstrap CI), proposal memo → Farjad Iranmehr → golden test first → pack version bump → cp-agronomy-guard → `docs/data/calibration-loop.md`.
- Data dictionary for all tables/views; PII classes P0–P3; PROPOSED retention; deletion options for immutable tables → `docs/data/data-dictionary.md`, `docs/data/pii-and-retention.md`.
- Read-only analytics access design (`cp_analyst`, `analytics.*` views, per-sprint CSV export, no warehouse) → `docs/data/analytics-access.md`.
- All SQL executed on throwaway local PostGIS with fictional rows; nothing touched Railway, migrations, engine or packs.

## What changed after D4 / R2 (2026-11-16)
Source: `docs/plans/backend-plan-reconciliation.md` (D4, R2), `docs/plans/backend-plan.md` §6.4, `docs/plans/backend-traceability.md` (DM-16, A2, NB-DAT-01, NB-DAT-03).
- **D4 — three review kinds** (updated 2026-11-16 after the superadmin decision). `review_kind` on every review row: `agronomist_approved` (human with the agronomist role), `superadmin_approved` (human superadmin), `ai_reviewed` (`cp-agronomist`). Every metric M1–M6 (and M7's last stage) and the calibration dataset are segmented by `review_kind`; only `agronomist_approved` counts toward the calibration dataset, the 90 % agreement gate, the baseline, constant-change proposals and the approval / review-gate rates. `superadmin_approved` and `ai_reviewed` appear only as two separate diagnostics, never pooled (`metrics.md` D4 section, `calibration-loop.md` update items 1–2 and 8, report sections H and I). A superadmin approval is not agronomic validation; a plan whose numbers a superadmin set or edited is a diagnostic.
- **Baseline (NB-DAT-03) needs agronomist cases.** The S3 output is the baseline **method** plus "no agronomist-approved cases yet" unless a human agronomist supplies cases (OQ-04).
- **R2 — per-line delta.** Engine-vs-final is now defined per `recommendation_line` (key nutrient + explicit form + split; added/removed lines are separate signals, not zero deltas; product and timing changes are attributes). **SG1 (P/K) is SOLVED BY R2** (decision); the migration is cp-database's.
- **New spec for cp-database (DM-16):** `docs/data/calibration-delta-spec.md` — grain, columns, filters, reference SQL (target schema §6.4, not yet migrated; executed on a throwaway local stub), acceptance tests T1–T19 (T18: `superadmin_approved` and `ai_reviewed` rows excluded from `calibration_delta`; T19: superadmin/AI-edited chains excluded), materialized view + nightly refresh in S5 (JB-04).
- **New gaps:** SG13 `review_kind` (three values) on `review` + `recommendation.author_kind`, SG14 explicit form on `recommendation_line`, SG15 undefined 90 % agreement gate.

## Not done / blocked
- ~~SG1~~ solved by R2 (decision); blocked only on cp-database migrating `recommendation_line` + explicit form before Feb 1, 2027.
- SG13 (`review_kind`: agronomist_approved / superadmin_approved / ai_reviewed) blocks every headline metric: without it the report prints "review kind not recorded".
- Schema gaps SG2–SG12 (see `docs/data/README.md`) are proposals awaiting CPO routing.
- PROPOSED retention periods and the deletion option need Farjad Iranmehr's decision and legal review (coo → legal-compliance-specialist).

## Decisions needed (Farjad Iranmehr via CPO)
1. ~~Where P/K final numbers live (SG1)~~ — decided: R2 `recommendation_line`.
1a. Who is the human agronomist (OQ-04 / RK-X1) — until named, no calibration baseline or gate can be computed.
1b. Definition of the 90 % agreement gate (SG15).
2. Approve minimum-sample rule and n < 10 suppression convention.
3. Approve PROPOSED retention + pseudonymise-in-place (Option A) for erasure.
4. Agreement tolerance (agronomist-todo #10) — agronomist call, not data's.
5. Are the Dec-18 cases also entered in the tool (double-count risk, SG7)?

## S3 plan (Dec 14 – Dec 24)
- data-scientist: calibration baseline from the 5 real wheat cases (Dec 18) **only if they are `agronomist_approved`** — per-case table, direction, reason codes; explicitly "anecdote, no proposal". Otherwise: baseline method + "no agronomist-approved cases yet"; `cp-agronomist` reference cases only as a separate AI diagnostic.
- data-scientist / data-engineer: review cp-database's `calibration_delta` migration against `calibration-delta-spec.md` tests T1–T17.
- data-analyst: first funnel + freshness sections of the report from `pilot_request`.
- data-engineer: `cp_analyst` + views as a migration proposal handed to cto/cp-database (if CPO approves SG9).

## Retro
- **Went well:** four specialists in parallel on disjoint files; every SQL was executed, which caught two real permission bugs (security_invoker view chain, view-owner grant on `pilot_request`).
- **Slowed us:** the same gaps were found four times with four numberings — needed a consolidation pass. No messaging tool in this session for cross-session notes.
- **One change for S3:** one shared gap register (`docs/data/README.md`) that specialists append to, instead of each doc carrying its own list.
