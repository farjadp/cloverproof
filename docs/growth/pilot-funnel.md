# Pilot-request funnel: definition

Status: DRAFT for `cro`. Metric definitions need sign-off from `head-of-data` (last section). Schema changes are proposals for `cto`.
Author: `growth-marketer`, 2026-11-16. Skills used: `cro` and `analytics` (marketingskills).
Goal it serves: 5–10 wheat farms confirmed by **2027-01-15** for the Feb–Apr 2027 season (`docs/plans/website-v1.md`).

## 1. What is measured today (verified 2026-11-16)

| Check | Result |
|---|---|
| Analytics on the site | **None.** `grep -rniE "gtag\|analytics\|plausible\|umami\|posthog\|googletagmanager\|dataLayer\|utm" website/src website/package.json` returns nothing. No analytics dependency in `website/package.json`. |
| Field check (`website/src/components/FieldCheck.tsx`) | Pure client state. Answers and the result (`full` / `confirm` / `nOnly`) are never sent anywhere. The result CTA is a plain `#pilot` anchor, so the result is lost before the form. |
| Pilot form (`PilotForm.tsx` → `app/[lang]/actions.ts`) | Writes one row to `pilot_request` on success. Nothing records step progress, errors or the source of the visit. |
| Honeypot | A bot that fills the hidden `website` field gets `{status: "success"}` and **no row is written**. Any client-side "success" count will be higher than the DB count. |
| `pilot_request.status` | `new`, `contacted`, `accepted`, `declined`. **No code updates it**: no admin UI, no script. Today it only changes by hand-written SQL. |
| `pilot_request` ↔ web-app tables | No link. `farmer` has no reference to `pilot_request`. Also, `docs/runbook-db-switch.md` is **NOT RUN**, so `pilot_request` is still in the website's own Postgres, apart from `farmer` / `review`. |
| Railway HTTP logs | Exist for the service, but count every request (assets, bots, health checks). A rough sanity check, not a visit metric. |

So today only stage 3 (requests submitted) is measurable, plus `contacted` / `accepted` / `declined` if someone keeps the status up to date by hand.

## 2. Two things to fix in the brief's stage list

1. **"Confirmed by Jan 15" is not "onboarded".** "Onboarded = first plan approved" can only happen once plans are made (Feb–Apr 2027). The Jan 15 goal needs its own stage: **accepted** (the farm agreed to join). The funnel below keeps both: `accepted` is the recruiting outcome, `onboarded` is the delivery outcome.
2. **The funnel has two entry paths.** A visitor can go to the form without doing the field check (hero CTA, nav CTA). Conversion rates are reported per path; "check completed" is not a required step before "request submitted".

```
site visit ──► check started ──► check completed {full|confirm|nOnly} ──► check CTA click ─┐
     │                                                                                     ▼
     └───────────────── (hero / nav CTA, direct) ───────────────────────────────► form step 1 ─► 2 ─► 3 ─► request submitted
                                                                                                                │
                                                       qualified ◄── contacted ◄────────────────────────────────┘
                                                           │
                                                       accepted (confirmed for 2027)  ← Jan 15 goal
                                                           │
                                                       onboarded (first plan approved) ← Feb–Apr 2027
```

## 3. Stage definitions

Unit of analysis:
- Web stages (0–2): a **page view** (`view_id`, a random ID made in memory on each page load, never stored on the device; see `landing-tracking-brief.md`). The site is one page with anchor links, so one page load ≈ one visit. A returning visitor counts again: no cookies means no unique visitors. That is a deliberate privacy trade-off.
- Stages 3–6: a **pilot request**, deduplicated by `lower(email)` (the earliest non-test row per email counts; later rows are duplicates).

Exclusions everywhere: test traffic and test rows (see `is_test` in §4), known bots (user-agent filter in the event collector), rows from honeypot hits (never written).

| # | Stage | Exact definition | Source | Today? | Owner |
|---|---|---|---|---|---|
| 0 | Site visit | A `page_view` event on `/{locale}` (landing page) with a new `view_id`, not a bot. Locale and UTM fields are recorded on the event. | Analytics events (to build) | **No** | `cro` (traffic by channel) |
| 1 | Field check started | The first `check_answer` event with `question = soilTest` in a `view_id`. There is no "Start" button: the first answer is the start. Optional `check_view` (section ≥ 50% on screen) separates "never saw it" from "saw it, didn't start". | Analytics events | **No** | `growth-marketer` (check UX); built by `cp-website` |
| 2 | Field check completed | A `check_result` event in a `view_id`, with `type ∈ {full, confirm, nOnly}`. Count the first result per `view_id` (a restart doesn't double-count). | Analytics events | **No** | `growth-marketer` |
| 2a | Check CTA clicked | `check_cta_click` with `type`. | Analytics events | **No** | `growth-marketer` |
| 3 | Pilot request submitted | A row in `pilot_request` with `is_test = false`, first per `lower(email)`, counted by `created_at` (Toronto time; to confirm). Soft-deleted rows (`deleted_at` set) **still count** as submitted: they were real requests. Rows already purged are only kept in past weekly reports, so the report must be saved each week. Client-side `form_submit_success` is a secondary signal for per-visit conversion only; the DB is the source of truth. | `pilot_request` (DB) | **Yes** (count, locale, country, free-text crop) | `growth-marketer` (form); `revops-specialist` (pipeline data) |
| 3w | …of which wheat | Stage 3, where the farmer says they will grow wheat in 2027. Today only an `ILIKE '%wheat%'` match on free-text `main_crop` is possible (rough; misses "blé", "durum", typos). The proposed form field `grows_wheat_2027` fixes it. | DB | Rough only | `revops-specialist` |
| 4 | Contacted | We made first contact (email or call, logged). Status moved to `contacted`, with a timestamp. | DB status + history (proposed) | Status yes if kept by hand; **timestamp no** | `account-executive` / whoever does first contact (to name) |
| 5 | Qualified | We confirmed **all** qualification criteria in a conversation (criteria to agree, see §7, Q4): grows wheat in the 2027 season, inside a region the pilot serves, the agronomist can serve it, can send the field inputs by the intake deadline, agrees to the pilot terms in principle. Status `qualified`. | DB status (proposed) | **No** (status doesn't exist) | `account-executive`; criteria owned by `cro` + Farjad Iranmehr (agronomist capacity) |
| 5a | Accepted (confirmed) | Farm confirmed for the 2027 pilot: the farmer said yes in writing **and** we offered a place. Status `accepted`. **This is the Jan 15 goal metric.** | DB status | Status yes (if kept by hand); timestamp no | `cro` |
| 6 | Onboarded | The first `review` with `decision = 'approve'` on any `recommendation` belonging to a `crop_plan` → `field` → `farm` → `farmer` linked to this pilot request. Onboarded date = that review's `created_at`. Derived, **not** a status anyone sets by hand. | Web-app DB (`farmer`, `farm`, `field`, `crop_plan`, `recommendation`, `review`) | **No** (no link, separate DBs) | `coo` / `customer-onboarding-specialist`; approval by the agronomist |

Terminal outcomes (any stage from 3 on): `declined` (we said no) and `withdrawn` (proposed: the farmer said no or stopped replying), each with a reason code.

### Conversion metrics (stage to stage)

All rates are reported **for the week and cumulative from launch**, by path (via check / direct) and, once there is traffic, by `utm_source`. With pilot-scale numbers, report counts next to every rate; a rate on fewer than ~20 in the denominator is noise (estimate, rule of thumb), so mark it "n<20".

| Metric | Numerator / denominator | Level |
|---|---|---|
| Check start rate | views with stage 1 / views (stage 0) | view |
| Check completion rate | views with stage 2 / views with stage 1 | view |
| Result mix | count per `type` / stage 2 | view |
| Check → CTA | views with 2a / views with stage 2, per `type` | view |
| Form start rate | views with `form_step` n=1 / views | view |
| Form step drop-off | `form_step` n=2 / n=1; n=3 / n=2; `form_submit_success` / n=3 | view |
| Form error rate | `form_submit_error` / (`form_submit_success` + `form_submit_error`), by `reason` | view |
| Visit → request | stage 3 rows / stage 0 views (only as an aggregate ratio per week; the two sources are not joined per person) | aggregate |
| Request → wheat | 3w / 3 | request |
| Request → contacted | 4 / 3, plus **median hours from `created_at` to `contacted`** (speed to lead) | request |
| Contacted → qualified | 5 / 4 | request |
| Qualified → accepted | 5a / 5 | request |
| Accepted → onboarded | 6 / 5a, plus median days from `accepted` to first approval | request |
| Scope at request | stage 3 by `check_scope` (`full` / `confirm` / `nOnly` / none), from the proposed column | request |

Cohort rule for stages 3–6: a request belongs to the week of its `created_at`; later stages are counted against that cohort, so recent cohorts look worse until they mature. The weekly report shows both the cohort view and "events this week".

## 4. Proposed status model for `pilot_request` (PROPOSAL for `cto`)

Not a migration. `cto` / `cp-database` decide the design and write the migration and an ADR (CLAUDE.md: ADR for data-model decisions). `0001_pilot_request.sql` is already applied and is copied byte for byte into root `db/migrations/` (ADR 0002), so any change is a **new** migration in both places, not an edit of 0001.

### 4.1 Statuses

| Status | Meaning | Set by | From |
|---|---|---|---|
| `new` | Submitted, not yet touched (exists) | system | — |
| `contacted` | First contact made (exists) | person | `new` |
| `qualified` | **NEW.** All qualification criteria confirmed | person | `contacted` |
| `accepted` | Confirmed pilot farm for 2027 (exists; meaning tightened to "farmer agreed and we offered a place") | person | `qualified` |
| `declined` | We said no (exists); needs `close_reason` | person | any open status |
| `withdrawn` | **NEW.** Farmer said no or no reply after the agreed follow-ups; needs `close_reason` | person | any open status |

`onboarded` is **not** a status. It is derived from the web-app tables (§3, stage 6), so it can't drift from what actually happened. If `cto` prefers a stored flag for speed, it should be written by the app on first approval, never by hand.

`close_reason` (proposed enum, reasons to agree with `cro`): `not_wheat`, `out_of_region`, `no_capacity`, `no_data_in_time`, `no_reply`, `not_interested`, `duplicate`, `other` (+ free-text note).

### 4.2 Columns and tables (proposal)

| Change | Why |
|---|---|
| `pilot_request_status_change` table: `id`, `pilot_request_id`, `from_status`, `to_status`, `close_reason`, `note`, `changed_by`, `changed_at` (insert-only, like `review`) | Without history there are no stage timestamps, so no speed-to-lead and no time in stage, and back-dated corrections are invisible. If `cto` rejects a table, the minimum is `status_changed_at` + `contacted_at` / `qualified_at` / `accepted_at` / `closed_at` columns. |
| `is_test boolean not null default false` | Exclude team test submissions (the runbook itself tells people to submit test requests). |
| `check_scope text null check (check_scope in ('full','confirm','nOnly'))` | Ties the field-check result to the request without a cross-session tracker. Sent as a hidden form field. |
| `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` (`text null`, ≤ 100 chars each), `referrer_host text null` (host only, no path or query) | Channel attribution per request. Read from the URL when the page loads; nothing stored on the device. |
| `heard_from text null` (fixed options + other) | Self-reported source. Catches word of mouth, which UTMs miss; likely the main channel for farms. |
| `region text null` and `grows_wheat_2027 text null check in ('yes','no','unsure')` | Needed to qualify and to count stage 3w without guessing from free text. (Form change, see the tracking brief.) |
| Link to the web app: `farmer.pilot_request_id uuid null unique references pilot_request(id) on delete set null` (or a link table) | Required for stage 6. Only possible **after** `docs/runbook-db-switch.md` is run (both tables in one database). Until then, stage 6 is matched by hand in a sheet that `revops-specialist` keeps (request id ↔ farmer id), with no PII copied into it. |

Privacy notes for `cto` / `data-governance-specialist`: the UTM, referrer-host and check-scope columns sit on a row that already holds PII, so they become personal data; the privacy notice must say so. The anonymous event log stays separate and has no join key to `pilot_request` (no `view_id` on the row), on purpose.

### 4.3 Who updates statuses

Today nobody can do it without SQL. Until the web app has a screen, `revops-specialist` proposes the smallest safe process (e.g. a reviewed SQL snippet run by one named person, or a small internal-tool page). Ask `cro` to route that. Without it, stages 4–5a stay empty whatever schema we pick.

## 5. Queries possible today (stage 3 only)

```sql
-- Requests per week (Toronto time), excluding obvious duplicates by email.
with firsts as (
  select distinct on (lower(email)) *
  from pilot_request
  order by lower(email), created_at
)
select date_trunc('week', created_at at time zone 'America/Toronto') as week,
       count(*)                                          as requests,
       count(*) filter (where main_crop ilike '%wheat%') as wheat_rough,
       count(*) filter (where status = 'contacted')      as contacted_now,
       count(*) filter (where status = 'accepted')       as accepted_now,
       count(*) filter (where status = 'declined')       as declined_now
from firsts
group by 1 order by 1;
```

Caveats: test rows can't be excluded yet (no `is_test`); the status columns show the **current** status, not when it changed.

## 6. Weekly funnel report template

Owner: `revops-specialist` produces, `cro` reviews; definitions per `head-of-data`. Week = Monday 00:00 to Sunday 23:59 America/Toronto (to confirm). Saved as `docs/growth/reports/pilot-funnel-<YYYY>-W<ww>.md`, so history survives the deletion purge. No names or emails in the report.

```markdown
# Pilot funnel — <YYYY>-W<ww> (<Mon date> – <Sun date>)
Weeks left to 2027-01-15: <n>   Data gaps this week: <e.g. events down Tue 10:00–14:00>

## Headline
Accepted (confirmed) to date: <n> / goal 5–10    Qualified, open: <n>    New requests this week: <n>
One-line read: <what changed and why, evidence only>

## Web (views; this week | cumulative)
| Stage | Count | Rate vs previous stage |
|---|---|---|
| Views (landing) | | — |
| Check started | | % of views |
| Check completed | | % of started |
|   full / confirm / nOnly | / / | mix % |
| Check CTA click | | % of completed |
| Form step 1 → 2 → 3 | → → | % |
| form_submit_success / error (by reason) | / | error % |

## Pipeline (requests; cohort by submit week | events this week)
| Stage | Count | Rate | Median time from previous stage |
|---|---|---|---|
| Requests (deduped, non-test) | | — | — |
|   wheat | | % | — |
| Contacted | | % | hours |
| Qualified | | % | days |
| Accepted | | % | days |
| Onboarded (first plan approved) | | % | days |
| Declined / withdrawn, by close_reason | | | |

## By source (requests; mark n<20)
| utm_source / heard_from | Views | Requests | Qualified | Accepted |
|---|---|---|---|---|

## By check scope at request
| full | confirm | nOnly | no check |
|---|---|---|---|

## Reconciliation
form_submit_success (events) vs new pilot_request rows: <a> vs <b>; difference explained: <yes/no>
Requests with status `new` older than <agreed SLA>: <n>

## Actions (owner, due)
- 
```

## 7. To agree with `head-of-data`

`head-of-data` owns metric definitions. Each item needs a yes, a change, or a no before the first weekly report.

1. **Unit for web stages**: a page load (`view_id`, in memory only), not a person or cookie session. Accept that returning visitors count more than once.
2. **Bot and test exclusion**: the user-agent filter rule, `is_test` on `pilot_request`, and how team traffic is kept out of events (proposal: the team tests only on non-production environments; production events are not filtered by IP).
3. **Check started** = the first answer to `soilTest`; **check completed** = the first `check_result` per `view_id` (restarts ignored).
4. **Qualified**: the exact criteria list (§3, stage 5) and who decides each criterion. The region list and agronomist capacity are Farjad Iranmehr's decisions.
5. **Accepted / confirmed**: "farmer agreed in writing and we offered a place". Is a verbal yes enough? Which document or message counts as proof?
6. **Onboarded** = the first `review.decision = 'approve'` on any recommendation of a linked farmer. The alternative is "first `proof_document` delivered". Pick one; approval is earlier and already enforced by the schema.
7. **Dedup rule**: the first non-test row per `lower(email)`; later rows marked duplicate. What if one email registers two farms?
8. **Soft-deleted requests** count in stage 3 history; purged rows survive only in saved weekly reports.
9. **Week boundary and time zone** (proposal: ISO week, America/Toronto).
10. **Source of truth for submissions**: DB rows, not `form_submit_success`. Event-vs-DB reconciliation tolerance (proposal: any gap is investigated, not tolerated, at this volume).
11. **Cohort vs period reporting** for stages 3–6 (§3); both shown.
12. **Wheat** = `grows_wheat_2027 = 'yes'` once the field exists; until then the `ILIKE '%wheat%'` rough count, labelled "rough".
13. **Small-number rule**: show counts with every rate, and flag rates with a denominator under 20 (estimate).
14. **Attribution rule**: last-touch UTM on the visit that submitted, `heard_from` reported next to it, not merged. Which one wins when they disagree?

## 8. Targets

No stage targets are set here. There is no traffic or conversion data to justify any.

Working-backwards illustration (**estimate, invented rates, not a target**): if contacted→qualified, qualified→accepted and request→contacted were each about 70%, then 10 accepted farms would need about 10 / (0.7 × 0.7 × 0.7) ≈ 29 wheat requests by early January. Replace the rates with real ones after two weeks of data, then decide with `cro` whether outreach volume is enough.
