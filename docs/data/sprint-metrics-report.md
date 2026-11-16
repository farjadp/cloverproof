# Per-sprint metrics report (design)

Audience: `product-manager` (CPO), who forwards 10 lines to Farjad Iranmehr at the sprint review. Producer: `data-analyst`, reviewed by `head-of-data`. Status: DRAFT v0, 2026-11-16. Metric definitions: `docs/data/metrics.md` (every row below cites its metric id; no metric outside the catalogue appears).

## When and who

- **Produced:** Friday of week 2 of each sprint, before the sprint review. Data cut-off: Thursday 23:59 America/Toronto of that week (so Friday's own reviews belong to the next report; say so in the header). Delivered to the CPO by the end of Friday morning; a late report is sent late, never completed with guessed numbers.
- **Where it lives:** `docs/data/reports/sprint-<n>.md`, one file per sprint, copied once into the CPO session. Not edited after sending; a correction is a new dated file section.
- **Starts:** the first report is S6 (Feb 1, 2027, first real plans). Before that, S3-S5 reports show only sections A (pilot funnel) and F (freshness), and the first real-case baseline from S3 as a count list. Engineering test plans are excluded via `excluded_orgs`.
- **Inputs:** queries in `metrics.md` run on a read replica or dev copy; the stage counts of M6 are stored in the report file each time (history is not reproducible otherwise, see M6).

## Rules that apply to every number

1. **n beside every number**, in the form `value (n=..)` or `k of n`. A rate without its n is not allowed.
2. **"Too small to read" flag** (`TSR`):
   - n < 10 (plans, reviews or requests, whichever is the denominator of that metric): show `k of n` or the bare list of values. No percentage, no median, no p90, no bias. Mark `TSR`.
   - n < 3: also no list for per-plan values that could identify a farm; show `n=..` and `TSR`.
   - n >= 10: show the statistic. Still labelled descriptive; it is never called a trend or "significant".
   - Segments (crop, method, confidence, pack): shown only if n >= 10 in that cell, otherwise "suppressed (n<10)". With 5-10 farms most segments will be suppressed; that is the correct output.
3. **Comparison with last sprint** only when both sprints have n >= 10 for that metric: show last value and the difference. Otherwise `no comparison (n<10)`, and both counts are still shown. Arrows and words like "improved" are banned for any metric flagged TSR.
4. **Estimates and proxies are labelled** (`proxy`, `estimate`). Unknowns are written `no data` plus the reason, never filled in.
5. **No personal or farm-identifying data**: no names, emails, farm or field names, free-text reasons. Plan counts only.
6. **No agronomic targets.** The report states what happened, not whether a kg N/ha value is good.
7. **Human vs AI reviews (D4, 2026-11-16).** Sections B-F count **human (`agronomist_approved`) reviews only**. AI sign-offs by `cp-agronomist` (`ai_reviewed`) appear only in section H and are never added to a human count, rate, gate or baseline. If reviewer kind is not yet recorded in the database (G9), sections C-E print "reviewer kind not recorded" instead of numbers. Until a human agronomist is named, expect "0 human-approved plans" — that is the correct output.

## Sections (one screen: at most 45 lines, no charts; a table plus one line of reading each)

| Section | Content | Metric |
|---|---|---|
| Header | Sprint n, dates, cut-off, run date, who produced | - |
| A. Pilot funnel | Requests by status this sprint and cumulative; accepted requests; farms with an approved plan. Printed side by side, labelled "not a conversion" while G2 is open | M6 |
| B. Plans | Plans created, plans not yet reviewed, plans approved this sprint, plans open (reviewed, not approved) | M1, M3 counts |
| C. Agronomist time | Median and p90 minutes per approved plan; minutes of open plans so far (count and sum only) | M1 |
| D. Review outcomes | First-pass approval, first-pass edit, first-pass reject (plan-level cohort); plans with a reject; approved after edit; review-level shares as secondary line | M3, M2 |
| E. Engine vs final | Per nutrient and form from `calibration_delta` (R2, human only): signed bias, median relative delta, lines changed / added / removed, product changes; cuts only if n >= 10 per cell. Before `recommendation_line` is migrated: N rate only, with the fixed line "P/K: no numeric engine output (G1, solved by R2 once migrated)" | M4 |
| F. Data freshness | Query run time, last review timestamp, last pilot request timestamp, plans not yet reviewed, share of zero-minute reviews (M5), open schema gaps that affected this report | M5, q_fresh |
| G. Flags (max 3 lines) | Anomalies and data gaps, each with a source; "what would change this reading" in one clause | - |
| H. AI review diagnostics (not agronomist approval) | Counts only: plans signed `ai_reviewed`, AI approve/edit/reject, AI lines added/removed vs engine. Titled so it cannot be read as approval | M2-M4 (ai) |

Layout per metric row: `metric | this sprint value (n) | last sprint value (n) | flag | note (<= 12 words)`.

## Length limit

One screen = 45 lines of markdown at 100 columns, tables included. If a section does not fit, drop detail (cuts first), never the n or the flag. Detail goes to an appendix file `docs/data/reports/sprint-<n>-appendix.md`, linked, not read in the review.

## Data freshness (section F)

```sql
select now()                                                  as queried_at,
       (select max(created_at) from review)                   as last_review_at,
       (select max(created_at) from recommendation)           as last_recommendation_at,
       (select max(created_at) from pilot_request)            as last_pilot_request_at,
       (select count(*) from crop_plan where organisation_id <> all (:'excluded_orgs'::uuid[])) as n_plans_total,
       (select count(*) from crop_plan cp where organisation_id <> all (:'excluded_orgs'::uuid[])
          and not exists (select 1 from recommendation r join review rv on rv.recommendation_id = r.id
                          where r.crop_plan_id = cp.id))      as n_plans_not_yet_reviewed,
       (select max(name) from schema_migrations)          as latest_migration;
```

Freshness rule: if `last_review_at` is more than 3 days before the cut-off while plans are open, say "no recent reviews; metrics reflect older work". If the replica lag is unknown say so; do not assume it is zero.

## Example (EXAMPLE: all numbers are invented to show the layout; none comes from the database)

```
SPRINT METRICS S7 (Feb 15 - Feb 26, 2027)  EXAMPLE - FAKE NUMBERS
Cut-off Thu Feb 25 23:59 Toronto | run Fri Feb 26 08:10 | db: read replica | by data-analyst

A. Pilot funnel (M6)               this sprint (n)   last sprint (n)   flag
 Requests new/contacted/acc/decl   2 / 1 / 1 / 0     3 / 2 / 1 / 1     TSR  (counts only)
 Accepted requests, cumulative     4                 3                 -
 Farms with approved plan, cum.    3                 1                 not a conversion of accepted (G2)

B. Plans
 Created 6 | not yet reviewed 1 | approved this sprint 4 | open (reviewed, not approved) 2

C. Agronomist time (M1)
 Minutes/plan, approved plans      4 plans: 14, 21, 25, 41    last: 3 plans  TSR  no median (n<10)
 Open plans, minutes so far        2 plans, 18 min total

D. Review outcomes (M3, M2)
 First-pass approval               2 of 6 first-reviewed plans    last: 1 of 3     TSR
 First-pass edit / reject          3 / 1                          last: 2 / 0      TSR
 Approved after edit               2 plans                        last: 1          TSR
 Plans with a reject               1 plan                         last: 0          TSR
 Review-level (approve/edit/rej)   5 / 4 / 1 of 10 reviews        last: 3/2/0 of 5 n=10 shown, last n=5: no comparison

E. Engine vs final (M4), human-approved plans only, descriptive
 N total signed delta (final-engine)   n=4: -15, -10, 0, +5   TSR  no bias or median shown
 Share edited / N rate changed        3 of 4 / 3 of 4        TSR
 By crop, confidence, method          suppressed (n<10)
 P and K lines (R2, per line)         P: 2 matched, 1 added, 0 removed | K: 1 matched   TSR  counts only

F. Freshness (M5)
 Last review Thu Feb 25 16:42 | last request Wed Feb 24 09:03 | 1 plan not yet reviewed
 Zero-minute reviews: 1 of 10 (M5)
 Gaps affecting this report: G2 (no request-to-farm link)

G. Flags
 1. Minutes are review minutes only; intake time not recorded (G4).
 2. Plan 4 of 6 took 41 min; cannot say if first-farm learning or complexity (n too small).

H. AI review diagnostics (cp-agronomist, ai_reviewed - NOT agronomist approval)
 Plans signed ai_reviewed 5 | AI approve/edit/reject 3 / 2 / 0 | lines added 1, removed 0   counts only
```

Reading note for the CPO (printed under every report): "With 5-10 farms these are counts of what happened, not statistics. Do not draw a trend or change an agronomic constant from them."
