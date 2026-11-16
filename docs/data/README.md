# Data & AI — docs index (owner: head-of-data)

S2 (Nov 30 – Dec 11, 2026) deliverables. Proposals only: no migration, engine or pack file was changed.
Updated 2026-11-16 for reconciliation **D4** (reviewer is the AI agent `cp-agronomist` → `ai_reviewed` until a human agronomist gives `agronomist_approved`; AI reviews never count toward gates, baseline or proposals) and **R2** (per-line `recommendation_line` replaces P/K columns). SQL against §6.4 names is marked "target schema, not yet migrated".

| Doc | What it answers | Author |
|---|---|---|
| [metrics.md](metrics.md) | M1–M7: minutes per plan, approve/edit/reject rates, engine-vs-final (per line after R2), zero-minute check, pilot funnel, website funnel from first-party `site_event` (M7, views not people, target schema) — formula, SQL, owner, min n; human vs AI segmentation (D4) | data-analyst |
| [sprint-metrics-report.md](sprint-metrics-report.md) | The one-screen report the CPO receives every sprint (design + EXAMPLE) | data-analyst |
| [calibration-loop.md](calibration-loop.md) | How a reviewed plan becomes evidence; queries; reason codes; minimum samples; proposal → golden test → pack bump → guard; human-only evidence (D4) | data-scientist |
| [calibration-delta-spec.md](calibration-delta-spec.md) | Per-line `calibration_delta` view handed to cp-database (DM-16): grain, line matching, columns, filters, reference SQL, acceptance tests, S5 materialization (JB-04) | data-scientist |
| [data-dictionary.md](data-dictionary.md) | Every table/view/column, units, mutability, PII class, quality rules | data-governance-specialist |
| [pii-and-retention.md](pii-and-retention.md) | PII classes P0–P3, access, PROPOSED retention, deletion vs immutability | data-governance-specialist |
| [analytics-access.md](analytics-access.md) | Read-only `cp_analyst` role, `analytics.*` views, per-sprint export | data-engineer |

All SQL was executed against throwaway local PostGIS containers (migrations 0001–0009 + fictional rows) and rolled back. Nothing ran against Railway.

## Honesty rule
With 5–10 farms every number here is a descriptive count. Constant changes need ≥ 20 plans from ≥ 10 farms per stratum (calibration-loop.md). For the 2027 season "no proposal: below minimum sample" is the expected output. Segments with n < 10 are suppressed in the CPO report. Only human-approved (`agronomist_approved`) cases count; until a human agronomist is named (OQ-04) the honest calibration output is "no human-approved cases yet".

## Consolidated schema-gap register (for the CPO → cto / cp-database)
Each specialist found gaps independently; this is the de-duplicated list. Specialist docs keep their own local numbering.

| # | Gap | Impact | Priority |
|---|---|---|---|
| SG1 | ~~Engine v0 emits P/K only as a note; agronomist's P/K numbers have no structured home~~ **SOLVED BY R2** (`recommendation_line`, per nutrient with explicit form) | Closed when cp-database migrates `recommendation_line` (+ explicit form, SG14) before Feb 1, 2027 | Done (decision); verify migration |
| SG2 | `recommendation` has no immutable `field_id` / `soil_test_id`; soil-test method only via jsonb snapshot | Stratifying by method/field is fragile | High |
| SG3 | No edit-reason code (free text in `recommendation.reason` and `review.reason`) | Can't count why he edits | High |
| SG4 | `minutes_spent` semantics unclear (additive per review? timer or typed?); time outside review not recorded | M1 may mis-measure the key metric | High — confirm with cto |
| SG5 | No test/demo flag on `organisation` / `pilot_request` | Seed/demo rows can pollute metrics | Medium |
| SG6 | Agronomist edit: splits/total not forced to match the rate | Inconsistent final numbers | Medium (data quality) |
| SG7 | No marker for blind (golden) vs anchored (reviewed in tool) cases | Dec-18 cases may be double-counted | Medium |
| SG8 | `pilot_request` has no link to farmer/org, no status history, no channel, free-text country/crop | Funnel stops at "accepted"; no time-in-stage | Medium |
| SG9 | No read-only analytics role / views | Analysts would need app credentials | Medium (S3) |
| SG10 | Deletion vs immutability: no pseudonymisation path, no `pilot_request` purge job, no proof-PDF erasure record, no farm-data agreement fields | Can't honour an erasure request cleanly | Medium — legal via coo |
| SG11 | `application_log` need not reference the approved recommendation | Planned-vs-actual can't be tied to a version | Low (Phase 4) |
| SG12 | No yield/outcome record | No ground truth for calibration | Later (Phase 4) |
| SG13 | No reviewer kind on `review` (D4): `ai_reviewed` vs `agronomist_approved` not separable | AI sign-offs would contaminate every metric, gate and the calibration set | **High — S2**, cp-database migrations 0011+ (REC-D4); stamp on the review row |
| SG14 | §6.4 `recommendation_line` has no form column; R2 requires explicit form | P vs P2O5 / K vs K2O ambiguous; per-line delta unsafe | **High — S2**: `nutrient_form` column or one canonical form per nutrient (`calibration-delta-spec.md` OQ-D2) |
| SG15 | The 90 % agreement gate (reconciliation D4) has no definition: unit, tolerance per nutrient (agronomist-todo #10), added/removed lines, population | Gate cannot be computed or audited | Human agronomist via CPO; data supplies the columns only |
| SG16 | `site_event` (first-party web events, CPO decision 2026-11-16) and the `pilot_request` attribution columns (`check_scope`, `utm_*`, `referrer_host`, `is_test`) are not migrated; `site_event` has no PII class or retention in `pii-and-retention.md`; success event may lack `view_id` | Website funnel (M7) is `no data`; no per-channel request counts | `cto` / `cp-database` migration + ADR; governance adds `site_event` as P1 (conditional, forbidden-field list) with PROPOSED retention 12 months raw (see metrics.md M7); the data dictionary needs a `site_event` entry |

SG5 note: §6.1 has no test flag either; the per-line spec assumes `farmer.is_test` (OQ-D5).
