# Agronomist workload model (pilot, Feb 1 – Apr 30, 2027)

- Purpose: know how many farms and fields the human agronomist plus one operator can run, how many hours to contract, when to stop taking farms, and when to name a backup reviewer.
- Owner: `coo` (Operator). Consumers: Farjad Iranmehr (founder/operator; not the reviewing agronomist), the hiring brief for `[HUMAN AGRONOMIST]`, `head-of-data` (metric), `cto` (logging proposals).
- Review date: after the S3 real cases (Dec 18, 2026), again at the end of S6 (first sprint of the season), then every sprint retro.
- Related: `docs/operations/pilot-sop.md` (steps, RACI, PROPOSED targets), `db/migrations/0007_review.sql` (`review.minutes_spent`), `db/migrations/0009_recommendation_diff_view.sql`.

Reviewer model (CPO decision D4, 2026-11-16): `cp-agronomist` (AI) pre-reviews every plan (`ai_reviewed`); a named human agronomist (`[HUMAN AGRONOMIST]`, not yet named, target before Jan 29, 2027) approves (`agronomist_approved`). Only the human's time is the key metric. Launch scope: Canada, Ontario winter wheat (Prairie wheat backup); no agronomic values appear here.

**Status of every number below: `ASSUMPTION — replace with measured minutes_spent from S3 real cases (Dec 18)`.** No measured data exists yet. No agronomic values appear here; only minutes and counts.

## 1. Definitions

- Plan = one `crop_plan` = one field in one season. "Minutes per plan" (key metric) = sum of `review.minutes_spent` over all HUMAN review rows in the plan's recommendation lineage (engine row, edit versions, approval). `minutes_spent` must be recorded on every human review (SOP gate G4).
- AI pre-review (SOP step 4a, `cp-agronomist`) is machine time. It is NOT agronomist time, NOT in `minutes_spent`, and does not enter the capacity math. Track it separately (run count, tokens or cost if available) for the hypothesis in section 2a. Intake, delivery and log time are ops time and are tracked in the ops sheet (section 5); they are not in `minutes_spent`.
- Person-hours here = Operator (today Farjad Iranmehr) plus human agronomist, counted separately. Human-agronomist-only work (cannot be delegated, G1): review and edit. Operator work (delegable to a helper later): everything else. Founder tasks such as deciding accept/decline are inside F1.
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
| D3 | Human review, approve path (4b) | Ag | 15 | 30 | 60 | Read each number and explanation; this is `minutes_spent` |
| D4 | Human edit with reason (4b), expected value | Ag | 3 | 10 | 32 | Edit probability 30 / 50 / 80% x extra minutes 10 / 20 / 40 (new version, reason text, re-check) |
| D5 | PDF generate + check (5) | Op/Ag | 8 | 12 | 20 | Generate from approved version, run the six-line pre-send checklist, sha256 match |
| D6 | Corrections, expected value (after delivery) | Ag/Op | 2 | 9 | 27 | Correction probability 5 / 15 / 30% x minutes 40 / 60 / 90 (new version, new PDF, supersede note) |
| D7 | Application-log entry (6) | Op | 5 | 10 | 20 | Enter actual vs planned per field |
| | **Field subtotal** | | **56** | **111** | **229** | |

Of which pre-delivery (D1–D5): L 49, M 92, H 182. Post-delivery (D6–D7): L 7, M 19, H 47.
Human-agronomist-only (D3+D4): L 18, M 40, H 92 per field (ASSUMPTION written before the AI pre-review existed; measured values may be lower, see 2a).

### 2a. AI pre-review and human minutes (hypothesis, not a claim)

- Hypothesis H1: with a `cp-agronomist` pre-review note (unit and form checks, missing inputs, explanation gaps), human D3 minutes per plan fall and D4 edit rate does not rise. Hypothesis H2: the pre-review catches intake errors before the human opens the case, lowering reject loops.
- Not evidence yet. The D3/D4 assumptions above are not discounted for AI help.
- How to test: record `minutes_spent` on every human review and flag whether an `ai_reviewed` note existed; compare median D3 for plans with and without the note (needs plans of both kinds, so run the first cases both ways if the human agronomist agrees; n will be small, say so). Also record how often the human overrode the AI suggested decision and the reason. A risk to watch: the human anchors on the AI note; track the agreement rate and spot-check a sample with the note hidden.
- AI time is logged apart: runs per plan and cost, owner `cto` via `coo`.

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

Assumptions: 70% of pre-delivery work (F1–F4, D1–D5) lands in a 4-week crunch window (ASSUMPTION: placeholder shape; `[HUMAN AGRONOMIST]` sets the real timing for Ontario winter wheat, winter wheat is fall-seeded so the Feb–Apr crunch may not match it). Post-delivery work (F5–F6, D6–D7) spreads over 13 weeks. Overhead 1 h/week. Conservative: assumes all farms intake in the season, although S4 onboards farms in Jan 4–15 and that flattens the peak.

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

Human-agronomist-only share at peak (review + edit, likely, no AI discount): 0.175 x 40 min x total fields / 60 = 0.117 h per field. 10 x 6 = 60 fields = 7.0 h/week. The non-delegable part is a minority; most of the load is operator work.

### Capacity line

Two capacities, kept apart. The table in this section totals Operator plus human-agronomist hours; the non-delegable human share is the line above (0.117 h per field at peak).

- Operator (Farjad Iranmehr today; ASSUMPTION, he confirms): sustainable 12 h/week, hard ceiling 20 h/week for no more than 2 consecutive weeks (he also has engineering coordination, grants, sales).
- Human agronomist (to be contracted; hours/week is an ASSUMPTION for the hiring brief, not an offer): needed hours/week = 0.117 h x fields at peak (likely, no AI discount) plus a buffer. Examples: 20 fields = 2.3 h, 60 fields = 7.0 h per peak week, high case about 2x. Proposed brief range: 4-8 h/week in the 4-week crunch, 1-3 h/week outside it (ASSUMPTION). Review needs daily short slots (see latency check), so the contract needs availability within 1 business day, not just weekly hours.
- Contract terms, rate and hiring: outside this document (flag to Farjad Iranmehr).

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

Name a backup human agronomist (decision for Farjad Iranmehr, SOP open decision 5; the primary human agronomist itself is not named yet, target before Jan 29, 2027):

| # | Trigger |
|---|---|
| B1 | C2 fires for 2 consecutive weeks |
| B2 | Human-agronomist hours (review + edit) above the contracted hours/week for 2 weeks (placeholder 8 h/week until the contract exists) |
| B3 | Planned absence of more than 3 business days in the crunch window |
| B4 | Any week above 20 h (C5) twice in a season |

Constraints on a backup: `cp-agronomist` cannot be the backup, since its sign-off is `ai_reviewed` and never counts as the gate. The database only lets a member with the `agronomist` role approve (trigger `review_check_reviewer` in 0007), so the person needs that membership; their `minutes_spent` is logged under their own `reviewer_id`, which also lets us compare reviewers. Alternative to a second reviewer: operator help for F1–F2, D1, D7, F5 (delegable, roughly 60% of likely farm and field minutes; likely cheaper than a second agronomist; no price evidence gathered). Hiring and contracts: flagged to Farjad Iranmehr, out of scope here.

## 5. How we measure

### From the database (exists today, no change)

| Measure | Source | Note |
|---|---|---|
| Human minutes per plan | `review.minutes_spent` summed over human review rows in the lineage of a `crop_plan` (AI pre-review rows excluded) | Weekly check lists rows with 0 (SOP gate G4) |
| Review wait | `review.created_at` minus engine `recommendation.created_at` (root row in `recommendation_diff`) | Includes queue wait, not working time |
| Edit depth and rate | `recommendation_diff.edit_depth`, `review.decision` | Edit minutes can be compared with approve-only minutes |
| Plan drafted to approved | `recommendation_diff.final_created_at`, `approved_at` | Cycle time for SOP step 4 target |
| Reviewer | `review.reviewer_id` | Distinguishes human from `cp-agronomist`; needed if a backup is added |
| AI pre-review present, agreement with human | `ai_reviewed` marker and suggested decision vs final `review.decision` | For hypothesis H1; field names to confirm with `head-of-data` / `cto` (not in migrations 0003-0009 as read here) |
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
| role | operator / human_agronomist (AI pre-review is not logged here) |
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

Hours this week (ops sheet)      total | human-agronomist-only | operator | vs 12 h line
Human minutes per plan           this week median | season median | assumed review+edit M = 40 | n plans | with / without ai_reviewed note
Review queue                     plans awaiting AI pre-review | awaiting human | oldest age (business days) | reviews with minutes_spent = 0
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
| 1 | Confirm operator sustainable (12 h) and ceiling (20 h) weekly hours; crunch window dates and the 70% / 4-week shape are set by `[HUMAN AGRONOMIST]` for Ontario winter wheat (no dates invented here) | Farjad Iranmehr, `[HUMAN AGRONOMIST]` |
| 2 | Edit-review row semantics (one row or two) so lineage minutes sum correctly | `head-of-data` |
| 3 | Where the ops sheet lives and who sees farm ids | `coo`, `data-governance-specialist` |
| 4 | Name human agronomist (target before Jan 29, 2027) and backup; contract hours from section 3 as ASSUMPTION; operator help (SOP open decision 5) | Farjad Iranmehr |
| 6 | Test hypothesis H1 (AI pre-review vs human minutes); define how AI pre-review is flagged in data | `head-of-data`, `cto` |
| 5 | Replace all assumptions after Dec 18 and after first two season weeks | Operator |
