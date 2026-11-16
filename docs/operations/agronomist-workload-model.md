# Agronomist workload model (pilot, Feb 1 – Apr 30, 2027)

- Purpose: know how many farms and fields one person can run, when to stop taking farms, and when to ask for a backup reviewer.
- Owner: `coo` (Operator). Consumers: Farjad Iranmehr (founder, agronomist, operator), `head-of-data` (metric), `cto` (logging proposals).
- Review date: after the S3 real cases (Dec 18, 2026), again at the end of S6 (first sprint of the season), then every sprint retro.
- Related: `docs/operations/pilot-sop.md` (steps, RACI, PROPOSED targets), `db/migrations/0007_review.sql` (`review.minutes_spent`), `db/migrations/0009_recommendation_diff_view.sql`.

**Status of every number below: `ASSUMPTION — replace with measured minutes_spent from S3 real cases (Dec 18)`.** No measured data exists yet. No agronomic values appear here; only minutes and counts.

## 1. Definitions

- Plan = one `crop_plan` = one field in one season. "Minutes per plan" (key metric) = sum of `review.minutes_spent` over all review rows in the plan's recommendation lineage (engine row, edit versions, approval). Intake, delivery and log time are ops time and are tracked in the ops sheet (section 5); they are not in `minutes_spent`.
- Person-hours here = Farjad Iranmehr in any role. Agronomist-only work (cannot be delegated, G1): review and edit. Operator work (delegable to a helper later): everything else.
- Farm-level step = cost paid once per farm. Field-level step = cost paid per field.
- Edit and correction rows are expected values (probability x minutes), so they can be summed.

## 2. Per-step minutes (ASSUMPTION)

Minutes. L = low, M = likely, H = high. "Who": Op = operator, Ag = agronomist only.

### Farm-level (paid once per farm)

| Code | Step (SOP #) | Who | L | M | H | What it covers |
|---|---|---|---|---|---|---|
| F1 | Triage, replies, accept/decline (1) | Op | 20 | 40 | 75 | Read `pilot_request`, scope check, first reply, accept or decline reply |
| F2 | Intake checklist send + chases (2) | Op | 30 | 60 | 120 | Send checklist, up to 3 chases per SOP, read replies |
| F3 | Farm + season setup in tool (2) | Op | 10 | 15 | 25 | Create farm, season |
| F4 | Delivery (5) | Op/Ag | 10 | 20 | 35 | Cover note draft and approval, one email with all PDFs |
| F5 | Application-log follow-up (6) | Op | 30 | 60 | 120 | First ask, reminders every 14 days, farmer replies |
| F6 | Feedback and close (7) | Op | 20 | 30 | 45 | 15-minute call or 5-question email, notes |
| | **Farm subtotal** | | **120** | **225** | **420** | |

Of which pre-delivery (F1–F4): L 70, M 135, H 255. Post-delivery (F5–F6): L 50, M 90, H 165.

### Field-level (paid per field)

| Code | Step (SOP #) | Who | L | M | H | What it covers |
|---|---|---|---|---|---|---|
| D1 | Data entry (2) | Op | 20 | 35 | 60 | Field, crop plan, previous crop, soil test fields (method, depth, date, P/K form), or "none" |
| D2 | Engine run + sanity read (3) | Op | 3 | 5 | 10 | Run, check snapshot and pack version shown |
| D3 | Review, approve path (4) | Ag | 15 | 30 | 60 | Read each number and explanation; this is `minutes_spent` |
| D4 | Edit with reason (4), expected value | Ag | 3 | 10 | 32 | Edit probability 30 / 50 / 80% x extra minutes 10 / 20 / 40 (new version, reason text, re-check) |
| D5 | PDF generate + check (5) | Op/Ag | 8 | 12 | 20 | Generate from approved version, run the six-line pre-send checklist, sha256 match |
| D6 | Corrections, expected value (after delivery) | Ag/Op | 2 | 9 | 27 | Correction probability 5 / 15 / 30% x minutes 40 / 60 / 90 (new version, new PDF, supersede note) |
| D7 | Application-log entry (6) | Op | 5 | 10 | 20 | Enter actual vs planned per field |
| | **Field subtotal** | | **56** | **111** | **229** | |

Of which pre-delivery (D1–D5): L 49, M 92, H 182. Post-delivery (D6–D7): L 7, M 19, H 47.
Agronomist-only (D3+D4): L 18, M 40, H 92 per field.

Not modelled: reject-and-rerun loops (SOP step 4 rejection path) beyond what D4/D6 absorb; escalations and disputes; data deletion requests; weekly 45-minute ops cadence (added as 1 h/week overhead in section 3). Add them if the first two weeks show them.

Known weak spots: (1) F2 and F5 depend on farmer responsiveness, the least predictable cost; S3 real cases will not measure them. (2) Fields 2+ on the same farm probably cost less than field 1 (shared farmer, shared soil-test lab); the model does not discount them, so multi-field results are conservative. Measure it.

## 3. Capacity math

Per farm total minutes = F + n x D, with F = 120 / 225 / 420 and D = 56 / 111 / 229 (L / M / H).

### Season totals (hours, whole season, 13 calendar weeks Feb 1 – Apr 30; final log entries May 7)

| Farms x fields per farm | Low | Likely | High |
|---|---|---|---|
| 5 x 1 | 14.7 | 28.0 | 54.1 |
| 5 x 3 | 24.0 | 46.5 | 92.3 |
| 5 x 6 | 38.0 | 74.3 | 149.5 |
| 10 x 1 | 29.3 | 56.0 | 108.2 |
| 10 x 3 | 48.0 | 93.0 | 184.5 |
| 10 x 6 | 76.0 | 148.5 | 299.0 |

Likely season average per week, including 1 h/week overhead for the Monday ops note and sprint retro: 5x1 3.2 h, 5x3 4.6 h, 5x6 6.7 h, 10x1 5.3 h, 10x3 8.2 h, 10x6 12.4 h. Averages hide the peak.

### Peak week (pre-seeding crunch)

Assumptions: 70% of pre-delivery work (F1–F4, D1–D5) lands in a 4-week crunch window (ASSUMPTION: planning for the seeding window; Farjad Iranmehr sets the real dates per country pack and crop). Post-delivery work (F5–F6, D6–D7) spreads over 13 weeks. Overhead 1 h/week. Conservative: assumes all farms intake in the season, although S4 onboards farms in Jan 4–15 and that flattens the peak.

Peak hours per week = 1 + a x farms + b x fields (total fields, all farms), with a, b in hours:

| Case | a (per farm) | b (per field) |
|---|---|---|
| Low | 0.268 | 0.152 |
| Likely | 0.509 | 0.293 |
| High | 0.955 | 0.592 |

(Derivation, likely: a = (0.175 x 135 + 90/13) / 60; b = (0.175 x 92 + 19/13) / 60; 0.175 = 0.70 / 4 weeks.)

| Farms x fields per farm | Low | Likely | High |
|---|---|---|---|
| 5 x 1 | 3.1 | 5.0 | 8.7 |
| 5 x 3 | 4.6 | 7.9 | 14.6 |
| 5 x 6 | 6.9 | 12.3 | 23.5 |
| 10 x 1 | 5.2 | 9.0 | 16.5 |
| 10 x 3 | 8.2 | 14.9 | 28.3 |
| 10 x 6 | 12.8 | 23.7 | 46.0 |

Agronomist-only share at peak (review + edit, likely): 0.175 x 40 min x total fields / 60 = 0.117 h per field. 10 x 6 = 60 fields = 7.0 h/week. The non-delegable part is a minority; most of the load is operator work.

### Capacity line (ASSUMPTION — Farjad Iranmehr to confirm)

- Sustainable: 12 h/week for CloverProof pilot work (founder also has engineering coordination, grants, sales).
- Hard ceiling: 20 h/week, no more than 2 consecutive weeks.

### Break point (where one person is not enough)

Solve 1 + a x farms + b x fields = capacity.

| Case | Capacity | 5 farms: max total fields | 10 farms: max total fields |
|---|---|---|---|
| Low | 12 h | 63 (about 12 per farm) | 54 (about 5 per farm) |
| Likely | 12 h | 28 (about 5 per farm) | 20 (2 per farm) |
| Likely | 20 h | 56 (about 11 per farm) | 47 (about 4.7 per farm) |
| High | 12 h | 10 (2 per farm) | 2 (cannot run 10 farms at all) |
| High | 20 h | 28 | 19 |

Reading it (likely case): 5 farms of 1–3 fields fit. 5 x 6 is at the sustainable line. 10 farms break the 12 h line at about 2 fields per farm, so 10 x 3 needs the hard ceiling for a few weeks, and 10 x 6 does not fit one person. If real minutes land near High, even 10 x 1 is over. The decision between "10 farms" and "5 farms with more fields" depends on measured D1/D3/D4 and F2/F5, not on this table.

Review latency check: SOP target is review within 3 business days and escalation at a backlog above 3 plans. At the likely peak, 60 fields (10 x 6) means about 10 plans reach `plan_drafted` per week (0.175 x 60 = 10.5, assuming even spread), above the SOP backlog limit of 3 unless reviews run several times a week. Review needs daily slots, not one weekly block, once multi-field farms are in.

## 4. Triggers (PROPOSED; thresholds are assumptions until measured)

Cap intake (Operator stops moving farms from `accepted` to `intake_open`; Founder informed; SOP escalation row "Review backlog"):

| # | Trigger | Check on |
|---|---|---|
| C1 | Projected peak hours for the next 4 weeks (formula above, using measured a and b once available) exceed 12 h | Monday ops note |
| C2 | Review queue above 3 plans, or oldest `plan_drafted` older than 3 business days (SOP rule) | Monday, and daily during crunch |
| C3 | Measured median minutes per plan (section 5) above 1.5 x the likely assumption for 2 consecutive weeks | Weekly trend report |
| C4 | Operator tasks overdue by more than 3 business days on 3 or more farms (checklist not sent, chase missed, delivery late) | Per-farm status table |
| C5 | Any week above 20 h | Weekly trend report |

Lift the cap when queue is at 3 or fewer and projected peak is back under 12 h for 2 weeks.

Ask for a backup reviewer (decision for Farjad Iranmehr, SOP open decision 5):

| # | Trigger |
|---|---|
| B1 | C2 fires for 2 consecutive weeks |
| B2 | Agronomist-only hours (review + edit) above 8 h/week for 2 weeks |
| B3 | Planned absence of more than 3 business days in the crunch window |
| B4 | Any week above 20 h (C5) twice in a season |

Constraints on a backup: the database only lets a member with the `agronomist` role approve (trigger `review_check_reviewer` in 0007), so the person needs that membership; their `minutes_spent` is logged under their own `reviewer_id`, which also lets us compare reviewers. Alternative to a second reviewer: hire operator help for F1–F2, D1, D7, F5 (delegable, roughly 60% of likely farm and field minutes), which is cheaper than a second agronomist. Hiring and contracts: flagged to Farjad Iranmehr, out of scope here.

## 5. How we measure

### From the database (exists today, no change)

| Measure | Source | Note |
|---|---|---|
| Minutes per plan | `review.minutes_spent` summed over the lineage of a `crop_plan` | Weekly check lists rows with 0 (SOP gate G4) |
| Review wait | `review.created_at` minus engine `recommendation.created_at` (root row in `recommendation_diff`) | Includes queue wait, not working time |
| Edit depth and rate | `recommendation_diff.edit_depth`, `review.decision` | Edit minutes can be compared with approve-only minutes |
| Plan drafted to approved | `recommendation_diff.final_created_at`, `approved_at` | Cycle time for SOP step 4 target |
| Reviewer | `review.reviewer_id` | Needed if a backup is added |
| Request to accepted | `pilot_request` timestamps and status | Step 1 target |

Caveat to confirm with `head-of-data`: whether an edit produces a second review row (approve of the new version) or one row. The model needs the sum over all rows of the lineage.

### Ops sheet (proposed, outside git because of farmer PII; farm ids only; weekly summary goes to `docs/operations/weekly/<yyyy-mm-dd>.md`)

One row per work session, entered the same day, minutes rounded to 5.

| Column | Example / values |
|---|---|
| date | 2027-02-09 |
| farm_id, field_id (blank if farm-level) | uuid or short id |
| step_code | F1–F6, D1–D7 from section 2, or `OH` (overhead), `ESC` (escalation), `DEL` (deletion request) |
| minutes | integer |
| role | operator / agronomist |
| touch_count | chases sent, reminders sent (for F2, F5) |
| note | one line: why it ran long |

Also per farm, once: fields_count, soil-test present (y/n per field), date accepted, date intake_complete, date delivered, date log complete, date closed. Needed to compute a and b per farm.

### Proposals for `head-of-data` / `cto` (no schema changes made here)

1. Add the ops-sheet dates above to the weekly metrics report design (S3) so intake duration and delivery latency are computed from one place.
2. If the concierge tool later gets a `pilot_farm` status column (SOP open decision 1), also store `status_changed_at`, so "days in status" is not typed by hand.
3. Optional, post-season: an `ops_time_log` table (farm_id, field_id, step_code, minutes, role, logged_at) replacing the sheet. Not before S11; a sheet is enough for 10 farms.
4. Review timer: confirm it covers edit time and starts when the case opens, so D3 and D4 are comparable with the sheet.

### Replacing the assumptions

- Dec 18 (S3): 5 real cases give measured D1, D2, D3, D4, D5. Replace those rows with median and range; keep L/M/H as P10 / median / P90 once n is 5 or more (state n; with n = 5 this is rough).
- S3 cannot measure F1–F6, D6, D7. Keep them as assumptions and replace after the first two season weeks, then at each sprint retro.
- Re-run section 3 with the new a and b each time; update the break-point table.

## 6. Weekly trend report (add to the Monday ops note)

`docs/operations/weekly/<yyyy-mm-dd>.md`, farm ids only. One screen.

```
Week of <date> | farms active / 10 cap | fields active | plans approved to date

Hours this week (ops sheet)      total | agronomist-only | operator | vs 12 h line
Minutes per plan (reviews)       this week median | season median | assumed review+edit M = 40 | n plans
Review queue                     plans in plan_drafted | oldest age (business days) | reviews with minutes_spent = 0
Edit rate / reject rate          this week | season | top 3 reasons (from review.reason)
Cycle times                      accept -> intake_complete | plan_drafted -> approved | approved -> delivered (days, median)
Operator load                    chases sent | farms paused | logs complete / delivered
Assumption vs measured           table: step code | assumed M | measured median | n | delta %
Projection                       next 4 weeks peak hours (formula, measured a and b) | trigger status C1-C5, B1-B4
Decision needed                  cap intake? backup reviewer? (yes / no + trigger id)
```

Metric numbers come from `data-analyst` via `coo`; the Operator fills only the ops-sheet items.

## 7. Open items

| # | Item | Owner |
|---|---|---|
| 1 | Confirm sustainable (12 h) and ceiling (20 h) weekly hours; confirm crunch window dates and the 70% / 4-week shape | Farjad Iranmehr |
| 2 | Edit-review row semantics (one row or two) so lineage minutes sum correctly | `head-of-data` |
| 3 | Where the ops sheet lives and who sees farm ids | `coo`, `data-governance-specialist` |
| 4 | Backup reviewer and operator help (SOP open decision 5) | Farjad Iranmehr |
| 5 | Replace all assumptions after Dec 18 and after first two season weeks | Operator |
