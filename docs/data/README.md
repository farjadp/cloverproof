# Data & AI — docs index (owner: head-of-data)

S2 (Nov 30 – Dec 11, 2026) deliverables. Proposals only: no migration, engine or pack file was changed.

| Doc | What it answers | Author |
|---|---|---|
| [metrics.md](metrics.md) | M1–M6: minutes per plan, approve/edit/reject rates, engine-vs-final N, zero-minute check, pilot funnel — formula, SQL, owner, min n | data-analyst |
| [sprint-metrics-report.md](sprint-metrics-report.md) | The one-screen report the CPO receives every sprint (design + EXAMPLE) | data-analyst |
| [calibration-loop.md](calibration-loop.md) | How a reviewed plan becomes evidence; queries; reason codes; minimum samples; proposal → golden test → pack bump → guard | data-scientist |
| [data-dictionary.md](data-dictionary.md) | Every table/view/column, units, mutability, PII class, quality rules | data-governance-specialist |
| [pii-and-retention.md](pii-and-retention.md) | PII classes P0–P3, access, PROPOSED retention, deletion vs immutability | data-governance-specialist |
| [analytics-access.md](analytics-access.md) | Read-only `cp_analyst` role, `analytics.*` views, per-sprint export | data-engineer |

All SQL was executed against throwaway local PostGIS containers (migrations 0001–0009 + fictional rows) and rolled back. Nothing ran against Railway.

## Honesty rule
With 5–10 farms every number here is a descriptive count. Constant changes need ≥ 20 plans from ≥ 10 farms per stratum (calibration-loop.md). For the 2027 season "no proposal: below minimum sample" is the expected output. Segments with n < 10 are suppressed in the CPO report.

## Consolidated schema-gap register (for the CPO → cto / cp-database)
Each specialist found gaps independently; this is the de-duplicated list. Specialist docs keep their own local numbering.

| # | Gap | Impact | Priority |
|---|---|---|---|
| SG1 | Engine v0 emits P/K only as a note; agronomist's P/K numbers have **no structured home** | P/K calibration data is lost from day one of the season | **Decide before Feb 1, 2027** |
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
