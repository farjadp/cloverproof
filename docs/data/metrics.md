# CloverProof metric catalogue

Owner: `head-of-data`. Written by `data-analyst`. Status: DRAFT v0, 2026-11-16 (Sprint 2). Single catalogue: a metric without an entry here is not reported.

## Read this first

- **Descriptive counts, not statistics.** The pilot is 5-10 farms in Feb-Apr 2027. Every metric below is a count, a share or a percentile of a handful of plans. No confidence interval, significance test or "trend" is valid at this size. Do not use these numbers to change an agronomic constant; the calibration review (`data-scientist`) reads the plan-by-plan rows, not the aggregates.
- **No agronomic numbers here.** Deltas are differences between two numbers already stored (engine vs agronomist). This file defines no constant, threshold or target for N, P or K.
- **No farmer data.** Reports contain counts and aggregates only. A segment (crop, method, confidence...) with fewer than 10 plans is shown as a count only (see `docs/data/sprint-metrics-report.md`). Do not copy `pilot_request` names or emails, `farmer.display_name`, `notes` or `reason` free text into any report.
- **"n at which it starts to mean anything"** below is a reporting convention proposed by data, not a statistical power calculation. At n below that, report the raw count and the plain rows. CPO to confirm (open question 3 in the hand-off).
- Source: Postgres schema `db/migrations/0001`-`0009` and `engine/cloverproof_engine/results.py` as of branch `myca/data-s2-693748`, 2026-11-16. Queries were run against a throwaway local PostGIS (migrations 0001-0009 applied, 5 invented plans) to check that they execute and return the expected shape. They have NOT been run on real data (none exists yet).

## Conventions shared by all queries

- Run with `psql` against a **read replica or a dev copy**, never as a writer. Variables: `\set sprint_start '2027-02-01 00:00 America/Toronto'`, `\set sprint_end '2027-02-15 00:00 America/Toronto'` (end exclusive), `\set excluded_orgs '{}'` (uuid array of test/demo organisations, e.g. the dev seed org `00000000-0000-4000-8000-000000000001`; see gap G5).
- **Crop plan = the unit of work.** `crop_plan` is one field, one season, one crop. A plan can have several engine recommendations (re-runs are new roots, `parent_id` null) and agronomist versions (edits, `parent_id` set). A plan is **approved** when any of its recommendations has a `review` with `decision = 'approve'`. If a plan has more than one approval, the latest is its final version.
- **Final version of an approved plan** = the recommendation with the latest approval. Engine version of that plan = the root of its `parent_id` chain (the `recommendation_diff` view already resolves this: `engine_*` vs `final_*`).
- Plan-level metrics are attributed to the sprint where the event happens: minutes and engine-vs-final to the sprint of the (latest) approval; first-pass cohort to the sprint of the first review; review-level metrics to `review.created_at`. Sprint windows are Monday to Monday in `America/Toronto`.
- Shared CTE (`plan_reviews`) is repeated at the top of each query so each query runs on its own.

---

## M1. Agronomist minutes per plan

- **Question:** how much agronomist time does it take to take one plan from engine output to an approved plan? (Key metric of the internal tool, CLAUDE.md.)
- **Decision (justified):** minutes per plan = **sum of `review.minutes_spent` over every review of every recommendation of that crop plan** (all engine roots, all edit versions, all decisions incl. reject and edit), for plans approved in the sprint. Why: the cost the business bears is the total agronomist effort to deliver one approved plan. The approving review alone undercounts plans that needed an edit or a reject first; a mean per review rewards splitting work into many short reviews. Also reported, so the choice can be audited: minutes of the approving review alone (read from `recommendation_diff.approval_minutes_spent`) and the review count per plan.
- **Formula:** `minutes_plan = SUM(review.minutes_spent)` per `crop_plan_id`. Reported as **median and p90** across plans approved in the window, plus min, max, n. Never the mean alone: one outlier plan (a first-time farm) moves a mean of 5-10 plans by tens of percent.
- **Numerator / denominator:** none (a distribution). Population = approved plans (approval timestamp in the window).
- **Unit:** minutes (integer per review, as stored).
- **Source:** `review.minutes_spent`, `review.recommendation_id`, `review.decision`, `review.created_at`; `recommendation.crop_plan_id`.
- **Grain:** per plan, summarised per sprint.
- **Owner:** `head-of-data`; produced by `data-analyst`.
- **Caveats:**
  - Plans still open (reviewed but not approved) are excluded from the headline; report their count and their minutes so far separately. Excluding them biases toward quick plans.
  - We do not know how the app's timer works (does it reset per review? does it run while the page is open but idle?). `minutes_spent` is whatever the app wrote. Open question 1.
  - Review is only one part of agronomist time: intake, soil-report reading and the farmer conversation are not in the schema (gap G4). Do not call this "total time per plan".
  - `minutes_spent = 0` means either instant or the timer did not run; see M5.
  - First plans per farm and first plans overall are slower (learning); report cohort by order if n allows, not as an average.
- **Starts to mean something at:** n >= 10 approved plans for the median; n >= 10 for p90 (at n < 10 the p90 is essentially the maximum). Below that: list per-plan minutes.

```sql
with
params as (
  select :'sprint_start'::timestamptz as t0,          -- inclusive
         :'sprint_end'::timestamptz   as t1           -- exclusive
),
plan_reviews as (                                       -- one row per crop plan that has >= 1 review
  select cp.id                                          as crop_plan_id,
         cp.organisation_id,
         cp.crop,
         count(rv.id)                                   as n_reviews,
         sum(rv.minutes_spent)                          as minutes_total,
         count(*) filter (where rv.decision = 'approve') as n_approve,
         count(*) filter (where rv.decision = 'edit')    as n_edit,
         count(*) filter (where rv.decision = 'reject')  as n_reject,
         min(rv.created_at)                             as first_review_at,
         (array_agg(rv.decision order by rv.created_at, rv.id))[1] as first_decision,
         max(rv.created_at) filter (where rv.decision = 'approve') as approved_at
  from crop_plan cp
  join recommendation r on r.crop_plan_id = cp.id
  join review rv        on rv.recommendation_id = r.id
  where cp.organisation_id <> all (:'excluded_orgs'::uuid[])
  group by cp.id
)
select count(*)                                                        as n_plans,
       percentile_cont(0.5) within group (order by minutes_total)      as median_min,
       percentile_cont(0.9) within group (order by minutes_total)      as p90_min,
       min(minutes_total)                                              as min_min,
       max(minutes_total)                                              as max_min,
       sum(minutes_total)                                              as sum_min,
       count(*) filter (where minutes_total = 0)                       as n_plans_zero_minutes
from plan_reviews, params
where approved_at >= t0 and approved_at < t1;      -- plans approved in the sprint
```

## M2. Review outcome shares (review-level approval, edit, reject rate)

- **Question:** of the reviews the agronomist performed, what share ended in approve / edit / reject?
- **Denominator (decision):** **reviews** (`review` rows) created in the window. Each review is one agronomist decision on one recommendation version; `decision` has exactly three values, so the three shares add to 100%.
- **Formula:** `approve_rate = reviews(decision='approve') / reviews`; same for `edit_rate`, `reject_rate`.
- **Unit:** percent, always shown with the counts.
- **Source:** `review.decision`, `review.created_at`, `review.organisation_id`.
- **Grain:** per review, summarised per sprint.
- **Owner:** `head-of-data`.
- **Caveats:**
  - Not "share of engine outputs approved as is". An edited plan produces two reviews (edit on the engine version, then approve on the agronomist version), so edits inflate the approve count too. Use M3 for the plan-level answer. This metric is only a workload-shape indicator.
  - "Edit" means the agronomist changed something stored in the document, not necessarily the N rate (see M4, `n_rate_changed`).
  - A reject is followed by a re-run (a new engine root); the rejected recommendation stays.
- **Starts to mean something at:** n >= 10 reviews, and no rate is quoted as a percentage below that (say "2 of 6").

```sql
with
params as (
  select :'sprint_start'::timestamptz as t0,          -- inclusive
         :'sprint_end'::timestamptz   as t1           -- exclusive
),
plan_reviews as (                                       -- one row per crop plan that has >= 1 review
  select cp.id                                          as crop_plan_id,
         cp.organisation_id,
         cp.crop,
         count(rv.id)                                   as n_reviews,
         sum(rv.minutes_spent)                          as minutes_total,
         count(*) filter (where rv.decision = 'approve') as n_approve,
         count(*) filter (where rv.decision = 'edit')    as n_edit,
         count(*) filter (where rv.decision = 'reject')  as n_reject,
         min(rv.created_at)                             as first_review_at,
         (array_agg(rv.decision order by rv.created_at, rv.id))[1] as first_decision,
         max(rv.created_at) filter (where rv.decision = 'approve') as approved_at
  from crop_plan cp
  join recommendation r on r.crop_plan_id = cp.id
  join review rv        on rv.recommendation_id = r.id
  where cp.organisation_id <> all (:'excluded_orgs'::uuid[])
  group by cp.id
)
select count(*)                                          as n_reviews,
       count(*) filter (where rv.decision = 'approve')   as n_approve,
       count(*) filter (where rv.decision = 'edit')      as n_edit,
       count(*) filter (where rv.decision = 'reject')    as n_reject,
       round(100.0 * count(*) filter (where rv.decision = 'approve') / nullif(count(*), 0), 1) as approve_pct,
       round(100.0 * count(*) filter (where rv.decision = 'edit')    / nullif(count(*), 0), 1) as edit_pct,
       round(100.0 * count(*) filter (where rv.decision = 'reject')  / nullif(count(*), 0), 1) as reject_pct
from review rv
cross join params
where rv.created_at >= t0 and rv.created_at < t1
  and rv.organisation_id <> all (:'excluded_orgs'::uuid[]);
```

## M3. Plan-level approval, edit and reject rates; first-pass approval rate

- **Question:** what share of plans does the agronomist accept as the engine produced them, and what share needs changes?
- **Cohort (decision):** plans whose **first review** falls in the window. Denominator = **plans with at least one review**. Plans with no review yet are not in the denominator (they are "not yet reviewed", reported as a count in the sprint report). Cohorting by first review avoids the survivorship bias of counting only plans that reached approval.
- **Definitions:**
  - **First-pass approval rate** = plans whose first review (earliest `review.created_at`, tie-break `id`) has `decision = 'approve'` / plans first reviewed in window. The agronomist accepted the engine's first output unchanged.
  - **First-pass edit rate** and **first-pass reject rate**: same, for `edit` / `reject`. The three add to 100%.
  - **Approved-after-edit** = plans with at least one `edit` review and an approval. **Plans with a reject** = plans with at least one `reject` review.
  - **Plans approved so far** = plans in the cohort with any approval at query time (the cohort is still moving until its plans close; re-run later and say so).
- **Unit:** percent with counts; plans.
- **Source:** `review` joined to `recommendation.crop_plan_id`; `crop_plan`.
- **Grain:** per plan, per sprint cohort.
- **Owner:** `head-of-data`.
- **Caveats:**
  - First-pass approval is not "the engine was right". It may mean the agronomist trusted it, was rushed, or the pack is PLACEHOLDER and the case simple. Always read with M4 and with `pack_status`.
  - Plans that are approved without any edit are the same set as first-pass approvals only if no reject/re-run happened; a plan approved after a reject-and-re-run is not first-pass.
  - A plan's cohort sprint is fixed by its first review; counts of "approved so far" change after the sprint closes.
- **Starts to mean something at:** n >= 10 plans for a percentage. With 5-10 farms and several fields each this may be reached only in S8 or later; before that quote counts.

```sql
with
params as (
  select :'sprint_start'::timestamptz as t0,          -- inclusive
         :'sprint_end'::timestamptz   as t1           -- exclusive
),
plan_reviews as (                                       -- one row per crop plan that has >= 1 review
  select cp.id                                          as crop_plan_id,
         cp.organisation_id,
         cp.crop,
         count(rv.id)                                   as n_reviews,
         sum(rv.minutes_spent)                          as minutes_total,
         count(*) filter (where rv.decision = 'approve') as n_approve,
         count(*) filter (where rv.decision = 'edit')    as n_edit,
         count(*) filter (where rv.decision = 'reject')  as n_reject,
         min(rv.created_at)                             as first_review_at,
         (array_agg(rv.decision order by rv.created_at, rv.id))[1] as first_decision,
         max(rv.created_at) filter (where rv.decision = 'approve') as approved_at
  from crop_plan cp
  join recommendation r on r.crop_plan_id = cp.id
  join review rv        on rv.recommendation_id = r.id
  where cp.organisation_id <> all (:'excluded_orgs'::uuid[])
  group by cp.id
)
select count(*)                                                        as n_plans_first_reviewed,
       count(*) filter (where first_decision = 'approve')              as n_first_pass_approved,
       count(*) filter (where first_decision = 'edit')                 as n_first_edit,
       count(*) filter (where first_decision = 'reject')               as n_first_reject,
       count(*) filter (where n_approve > 0)                           as n_plans_approved_so_far,
       count(*) filter (where n_approve > 0 and n_edit > 0)            as n_approved_after_edit,
       count(*) filter (where n_reject > 0)                            as n_plans_with_reject,
       round(100.0 * count(*) filter (where first_decision = 'approve') / nullif(count(*), 0), 1) as first_pass_approval_pct
from plan_reviews, params
where first_review_at >= t0 and first_review_at < t1;   -- cohort: plans first reviewed in the sprint
```

## M4. Engine vs final difference (calibration signal)

- **Question:** where, and in which direction, does the agronomist's approved number differ from the engine's number, per nutrient, crop, soil-test method and confidence?
- **Nutrients the schema exposes today (honest status):**
  - **N: yes.** `recommendation.n_rate_kg_ha` (generated from `result.nitrogen.rate.value`, unit kg N/ha, CHECK-enforced) and the view `recommendation_diff` (`engine_n_rate_kg_ha`, `final_n_rate_kg_ha`, `n_rate_delta_kg_ha`). Also in `result` jsonb: `nitrogen.total` (= rate x area, kg N), `nitrogen.splits[]` (stage fractions and rates), `nitrogen.components[]`, `nitrogen.bound_applied`, `nitrogen.constants_used[]` (with PLACEHOLDER status).
  - **P and K: no number exists.** `Recommendation.phosphorus_potassium` is a `Note` (a code and text, e.g. `PK_NOT_CALCULATED_V0`, `PK_SOIL_TEST_RECOMMENDED`). The engine returns no P or K rate and the document model (`extra="forbid"`) has no field for the agronomist to enter one. So **there is no P/K engine-vs-final delta to compute, in SQL or otherwise.** This is schema gap G1. `application_log` has P/K-capable `form` and rates but records what was applied, not the engine-vs-final difference.
  - So the metric is **N rate only** until G1 is closed. Query `q_diff_pk` shows what is stored for P/K so the report can state "P/K: no numeric output" with a count instead of silence.
- **Population:** approved plans (final = latest approved version) with approval in the window. One row per plan.
- **Formulas** (per plan, then summarised; `delta` = final minus engine, kg N/ha):
  - Signed delta = `final_n_rate - engine_n_rate`. **Signed bias** = mean of signed deltas over the group (negative = agronomist lowers on average). Also the median signed delta.
  - Absolute delta = `|delta|`; **mean absolute delta** over the group.
  - Relative delta = `delta / engine_n_rate`, only where `engine_n_rate > 0`; summarised as the **median relative delta**. Plans with engine rate 0 are excluded from the relative columns and counted in `n_with_relative` (denominator of those columns). Mean relative delta is not reported (one small engine rate dominates).
  - **Share of plans edited** = plans whose final version is `kind = 'agronomist'` / approved plans. **Share with N rate changed** = plans with delta not 0 / approved plans. They differ when an edit changed something other than the N rate (e.g. reason, split, confidence).
- **Cuts** (one row per value): overall; `crop` (from `crop_plan.crop`; wheat is the only engine crop today); `engine_confidence` (`recommendation.confidence` of the engine row); `soil_test_methods`; `pack_version` and `pack_status` (so differences are never pooled across pack changes).
- **Soil-test method:** read from the engine row's input snapshot (`result.input_snapshot.soil_test.values[].extraction_method`), not from the live `soil_test_value` table, because `soil_test` rows are updatable by the app (`cp_app` has UPDATE/DELETE) and the snapshot is what the engine actually used. Value = the distinct methods in that test joined with `+` (e.g. `olsen`, `mehlich-3+olsen`), or `no_soil_test` when the snapshot has no soil test.
- **Unit:** kg N/ha (absolute, signed), percent (relative).
- **Source:** view `recommendation_diff` (all columns above, `approved_at`, `final_kind`, `edit_depth`), `crop_plan.crop`, `engine_result` jsonb.
- **Grain:** per approved plan; summarised per dimension value per sprint, and cumulatively (run with a wide window) for the calibration review.
- **Owner:** `head-of-data`; analysis by `data-scientist`.
- **Caveats:**
  - Descriptive. A signed bias over 3-9 plans is a list of 3-9 differences. It is not evidence for changing a pack constant; any constant change goes through the calibration loop and Farjad Iranmehr's approval (roadmap).
  - The soil-test method only matters for P/K tests; for an N-only plan it is a proxy label for "which test was available", not a cause. Segments will be empty or n=1 for most of the pilot.
  - Plans from different pack versions or `pack_status` (placeholder vs validated) must not be pooled; the cuts exist for that reason. Before the S3 real cases the pack is a placeholder: deltas against a placeholder engine measure the placeholder, not the agronomy.
  - A sequence of edits (`edit_depth` > 1) is collapsed to engine vs final. Intermediate versions are not in this metric.
  - Rates are per hectare; plan totals depend on area. Not area-weighted.
  - Filter out demo/test plans (G5).
- **Starts to mean something at:** n >= 10 plans per cell to show a number. A cell below 10 is suppressed in the CPO report (privacy rule: no segment under 10, and with 5-10 farms a segment can identify one farm); the `overall` row below 10 is shown as the bare list of signed deltas with no ids. `data-scientist` may read small cells in the calibration review, internally. Expect only the `overall` row to reach 10 in the pilot.

```sql
with
params as (
  select :'sprint_start'::timestamptz as t0,          -- inclusive
         :'sprint_end'::timestamptz   as t1           -- exclusive
),
plan_reviews as (                                       -- one row per crop plan that has >= 1 review
  select cp.id                                          as crop_plan_id,
         cp.organisation_id,
         cp.crop,
         count(rv.id)                                   as n_reviews,
         sum(rv.minutes_spent)                          as minutes_total,
         count(*) filter (where rv.decision = 'approve') as n_approve,
         count(*) filter (where rv.decision = 'edit')    as n_edit,
         count(*) filter (where rv.decision = 'reject')  as n_reject,
         min(rv.created_at)                             as first_review_at,
         (array_agg(rv.decision order by rv.created_at, rv.id))[1] as first_decision,
         max(rv.created_at) filter (where rv.decision = 'approve') as approved_at
  from crop_plan cp
  join recommendation r on r.crop_plan_id = cp.id
  join review rv        on rv.recommendation_id = r.id
  where cp.organisation_id <> all (:'excluded_orgs'::uuid[])
  group by cp.id
),
final as (                                              -- one row per approved plan: latest approved version
  select distinct on (d.crop_plan_id)
         d.crop_plan_id, d.final_kind, d.edit_depth, d.pack_version, d.pack_status,
         d.engine_confidence, d.final_confidence,
         d.engine_n_rate_kg_ha, d.final_n_rate_kg_ha, d.n_rate_delta_kg_ha,
         d.approved_at, d.engine_result, d.final_result, cp.crop
  from recommendation_diff d
  join crop_plan cp on cp.id = d.crop_plan_id
  where d.approved_at is not null
    and d.organisation_id <> all (:'excluded_orgs'::uuid[])
  order by d.crop_plan_id, d.approved_at desc
),
final_win as (
  select f.* from final f, params where f.approved_at >= t0 and f.approved_at < t1
),
methods as (                                            -- extraction methods in the soil test snapshot used
  select f.crop_plan_id,
         coalesce(string_agg(distinct v ->> 'extraction_method', '+' order by v ->> 'extraction_method'),
                  'no_soil_test') as soil_test_methods
  from final_win f
  left join lateral jsonb_array_elements(
         case when jsonb_typeof(f.engine_result #> '{input_snapshot,soil_test,values}') = 'array'
              then f.engine_result #> '{input_snapshot,soil_test,values}' else '[]'::jsonb end) v on true
  group by f.crop_plan_id
),
cut as (                                                -- one row per (dimension, value, plan)
  select 'overall' as dim, 'all' as val, f.* from final_win f
  union all select 'crop',              f.crop,                f.* from final_win f
  union all select 'engine_confidence', f.engine_confidence::text, f.* from final_win f
  union all select 'soil_test_methods', m.soil_test_methods, f.* from final_win f join methods m using (crop_plan_id)
  union all select 'pack_version',      f.pack_version,        f.* from final_win f
  union all select 'pack_status',       f.pack_status,         f.* from final_win f
)
select dim, val,
       count(*)                                                        as n_plans,
       count(*) filter (where final_kind = 'agronomist')               as n_edited,           -- final is an agronomist version
       count(*) filter (where n_rate_delta_kg_ha <> 0)                 as n_rate_changed,     -- N rate actually differs
       round(avg(n_rate_delta_kg_ha), 2)                               as signed_bias_kg_n_ha, -- mean(final - engine)
       percentile_cont(0.5) within group (order by n_rate_delta_kg_ha) as median_delta_kg_n_ha,
       round(avg(abs(n_rate_delta_kg_ha)), 2)                          as mean_abs_delta_kg_n_ha,
       min(n_rate_delta_kg_ha)                                         as min_delta,
       max(n_rate_delta_kg_ha)                                         as max_delta,
       count(*) filter (where engine_n_rate_kg_ha > 0)                 as n_with_relative,    -- denominator of the relative columns
       round(100 * (percentile_cont(0.5) within group (
             order by n_rate_delta_kg_ha / engine_n_rate_kg_ha)
             filter (where engine_n_rate_kg_ha > 0))::numeric, 1)      as median_rel_delta_pct
from cut
group by dim, val
order by dim, val;
```

P/K content today (expect a note code only, no number):

```sql
with
params as (
  select :'sprint_start'::timestamptz as t0,          -- inclusive
         :'sprint_end'::timestamptz   as t1           -- exclusive
),
plan_reviews as (                                       -- one row per crop plan that has >= 1 review
  select cp.id                                          as crop_plan_id,
         cp.organisation_id,
         cp.crop,
         count(rv.id)                                   as n_reviews,
         sum(rv.minutes_spent)                          as minutes_total,
         count(*) filter (where rv.decision = 'approve') as n_approve,
         count(*) filter (where rv.decision = 'edit')    as n_edit,
         count(*) filter (where rv.decision = 'reject')  as n_reject,
         min(rv.created_at)                             as first_review_at,
         (array_agg(rv.decision order by rv.created_at, rv.id))[1] as first_decision,
         max(rv.created_at) filter (where rv.decision = 'approve') as approved_at
  from crop_plan cp
  join recommendation r on r.crop_plan_id = cp.id
  join review rv        on rv.recommendation_id = r.id
  where cp.organisation_id <> all (:'excluded_orgs'::uuid[])
  group by cp.id
),
final as (                                              -- one row per approved plan: latest approved version
  select distinct on (d.crop_plan_id)
         d.crop_plan_id, d.final_kind, d.edit_depth, d.pack_version, d.pack_status,
         d.engine_confidence, d.final_confidence,
         d.engine_n_rate_kg_ha, d.final_n_rate_kg_ha, d.n_rate_delta_kg_ha,
         d.approved_at, d.engine_result, d.final_result, cp.crop
  from recommendation_diff d
  join crop_plan cp on cp.id = d.crop_plan_id
  where d.approved_at is not null
    and d.organisation_id <> all (:'excluded_orgs'::uuid[])
  order by d.crop_plan_id, d.approved_at desc
),
final_win as (
  select f.* from final f, params where f.approved_at >= t0 and f.approved_at < t1
),
methods as (                                            -- extraction methods in the soil test snapshot used
  select f.crop_plan_id,
         coalesce(string_agg(distinct v ->> 'extraction_method', '+' order by v ->> 'extraction_method'),
                  'no_soil_test') as soil_test_methods
  from final_win f
  left join lateral jsonb_array_elements(
         case when jsonb_typeof(f.engine_result #> '{input_snapshot,soil_test,values}') = 'array'
              then f.engine_result #> '{input_snapshot,soil_test,values}' else '[]'::jsonb end) v on true
  group by f.crop_plan_id
),
cut as (                                                -- one row per (dimension, value, plan)
  select 'overall' as dim, 'all' as val, f.* from final_win f
  union all select 'crop',              f.crop,                f.* from final_win f
  union all select 'engine_confidence', f.engine_confidence::text, f.* from final_win f
  union all select 'soil_test_methods', m.soil_test_methods, f.* from final_win f join methods m using (crop_plan_id)
  union all select 'pack_version',      f.pack_version,        f.* from final_win f
  union all select 'pack_status',       f.pack_status,         f.* from final_win f
)
-- What the stored document says about P and K today: a note, never a number.
select f.final_result #>> '{phosphorus_potassium,code}' as pk_note_code,
       count(*)                                           as n_plans
from final_win f
group by 1
order by 1;
```

Jsonb paths for later use (N splits are the only other numeric nitrogen detail): rate `result #>> '{nitrogen,rate,value}'`; total `result #>> '{nitrogen,total,value}'`; confidence `result ->> 'confidence'`; placeholder flag `(result #>> '{nitrogen,rate,uses_placeholder}')::boolean`; splits `jsonb_array_elements(result #> '{nitrogen,splits}')`, each with `stage_label`, `fraction.value`, `rate.value`.

## M5. Minutes data quality (zero-minute reviews)

- **Question:** can we trust M1? What share of reviews carry `minutes_spent = 0`?
- **Formula:** reviews with `minutes_spent = 0` / reviews in the window.
- **Unit:** percent with counts. **Source:** `review.minutes_spent`, `review.created_at`. **Grain:** per review, per sprint. **Owner:** `head-of-data`.
- **Caveats:** zero can be legitimate (re-approval in seconds). The CPO should treat M1 as unreliable when this share is large; "large" is not defined by data. Open question 2.
- **Starts to mean something at:** any n; it is a check, shown as a count.

```sql
with
params as (
  select :'sprint_start'::timestamptz as t0,          -- inclusive
         :'sprint_end'::timestamptz   as t1           -- exclusive
),
plan_reviews as (                                       -- one row per crop plan that has >= 1 review
  select cp.id                                          as crop_plan_id,
         cp.organisation_id,
         cp.crop,
         count(rv.id)                                   as n_reviews,
         sum(rv.minutes_spent)                          as minutes_total,
         count(*) filter (where rv.decision = 'approve') as n_approve,
         count(*) filter (where rv.decision = 'edit')    as n_edit,
         count(*) filter (where rv.decision = 'reject')  as n_reject,
         min(rv.created_at)                             as first_review_at,
         (array_agg(rv.decision order by rv.created_at, rv.id))[1] as first_decision,
         max(rv.created_at) filter (where rv.decision = 'approve') as approved_at
  from crop_plan cp
  join recommendation r on r.crop_plan_id = cp.id
  join review rv        on rv.recommendation_id = r.id
  where cp.organisation_id <> all (:'excluded_orgs'::uuid[])
  group by cp.id
)
select count(*)                                                as n_reviews,
       count(*) filter (where rv.minutes_spent = 0)            as n_zero_minute_reviews,
       round(100.0 * count(*) filter (where rv.minutes_spent = 0) / nullif(count(*), 0), 1) as zero_minute_pct
from review rv, params
where rv.created_at >= t0 and rv.created_at < t1
  and rv.organisation_id <> all (:'excluded_orgs'::uuid[]);
```

## M6. Pilot funnel (request to first approved plan)

- **Question:** how many pilot requests become accepted farms, and how many of those reach a first approved plan?
- **Stages and definitions:**
  1. **Requests** = `pilot_request` rows with `deleted_at is null`, by **current** `status` (`new`, `contacted`, `accepted`, `declined`), windowed on `created_at`.
  2. **Contacted-or-later** = `contacted + accepted + declined` (assumes a request cannot reach `accepted` or `declined` without having been contacted; the schema does not enforce the order, so this is an assumption). **Accepted** = `status = 'accepted'`. **Decline rate** = declined / (accepted + declined) among decided requests; do not divide by `new`.
  3. **Farms with an approved plan** = distinct `farm.id` whose plans have an approving review (`review -> recommendation -> crop_plan -> field -> farm`), windowed on the first approval, plus the median days from `farm.created_at` to first approval.
- **The funnel is not joinable end to end.** `pilot_request` has no column linking to `organisation`, `farmer` or `farm` (gap G2). Stage 3 cannot be stated as a conversion of stage 2: the report shows the two counts side by side ("12 accepted requests; 4 farms with an approved plan") and labels it NOT a conversion rate, unless a person matches them by hand and records it (still not in the database).
- **Deleted rows:** a deletion request sets `deleted_at` and a later job purges the row. All queries exclude `deleted_at is not null`. Consequence: history shrinks silently when someone asks to be deleted or the purge runs; a past sprint's counts re-computed later can be lower. Snapshot the stage counts at each sprint report (see the report design) so a report is reproducible.
- **Unit:** requests, farms, days (median).
- **Source:** `pilot_request.status`, `created_at`, `deleted_at`; `farm`, `field`, `crop_plan`, `recommendation`, `review`.
- **Grain:** per request (stage 1), per farm (stage 3); per sprint.
- **Owner:** `cro` for stages 1-2 meaning, `head-of-data` for the query.
- **Caveats:**
  - `status` is a current value only. There are no timestamps per status change (gap G3): we cannot compute time-to-contact, time-to-accept, or "contacted in sprint X"; a request that moved from `new` to `accepted` in S4 is simply `accepted` and keeps its `created_at`.
  - Requests are self-selected website submissions; no source/channel column, so "which channel works" is not answerable from the database (gap G6).
  - Spam and test submissions are not flagged (G5).
  - Requests from outside the pilot ICP (country, crop) are counted unless filtered on `country` / `main_crop` (free text, unnormalised: `farm_size_text` cannot be summed).
- **Starts to mean something at:** n >= 10 decided requests for a decline rate; stage counts are always shown as counts.

```sql
-- Stage 1: pilot requests by current status (deleted_at rows excluded). Window = created_at.
select status,
       count(*) as n_requests
from pilot_request, (select :'sprint_start'::timestamptz t0, :'sprint_end'::timestamptz t1) p
where deleted_at is null
  and created_at >= t0 and created_at < t1
group by status
order by array_position(array['new','contacted','accepted','declined'], status);

-- Stage 2 (separate, NOT a conversion): farms with at least one approved plan, and days from farm creation.
with first_approval as (
  select f.id as farm_id, f.created_at as farm_created_at, min(rv.created_at) as first_approved_at
  from review rv
  join recommendation r on r.id = rv.recommendation_id
  join crop_plan cp     on cp.id = r.crop_plan_id
  join field fl         on fl.id = cp.field_id
  join farm f           on f.id = fl.farm_id
  where rv.decision = 'approve'
    and rv.organisation_id <> all (:'excluded_orgs'::uuid[])
  group by f.id
)
select count(*)                                                          as n_farms_with_approved_plan,
       percentile_cont(0.5) within group (order by extract(epoch from first_approved_at - farm_created_at) / 86400) as median_days_farm_to_first_approval
from first_approval
where first_approved_at >= :'sprint_start'::timestamptz and first_approved_at < :'sprint_end'::timestamptz;

-- Cumulative counts (all time), for the funnel picture.
select (select count(*) from pilot_request where deleted_at is null)                          as requests_live,
       (select count(*) from pilot_request where deleted_at is null and status = 'accepted')  as requests_accepted,
       (select count(*) from farm where organisation_id <> all (:'excluded_orgs'::uuid[]))    as farms,
       (select count(distinct fl.farm_id) from review rv
          join recommendation r on r.id = rv.recommendation_id
          join crop_plan cp on cp.id = r.crop_plan_id
          join field fl on fl.id = cp.field_id
         where rv.decision = 'approve' and rv.organisation_id <> all (:'excluded_orgs'::uuid[])) as farms_with_approved_plan;
```

---

## Schema gaps (proposals only; migrations are not edited here)

| # | Gap | Effect today | Proposal (owner: `cp-database` / `cto`, decision: CPO) |
|---|---|---|---|
| G1 | No P or K number in the engine document or anywhere in the schema; `phosphorus_potassium` is a Note | No P/K engine-vs-final delta, ever, until the engine emits P/K numbers | When the engine adds P/K, add typed generated columns like `n_rate_kg_ha` (`p_rate_kg_ha`, `k_rate_kg_ha`) with the explicit form (P vs P2O5, K vs K2O) stored beside each, and extend `recommendation_diff`. Until then M4 is N-only and the report says so. |
| G2 | `pilot_request` has no link to `organisation` / `farmer` / `farm` | Funnel stops at "accepted"; request to first approved plan is not a measurable conversion | Add nullable `pilot_request.farmer_id` (or `organisation_id` + `farmer_id`), set by the concierge when a request is accepted and a farmer record is created. |
| G3 | `pilot_request.status` has no history | No time in stage, no "moved in this sprint", past sprint counts not reproducible | Append-only `pilot_request_status_event(pilot_request_id, status, at, by)`; or at least `contacted_at`, `decided_at`. Interim: snapshot counts at each report. |
| G4 | Agronomist time outside review is not recorded | M1 covers review minutes only | Optional `minutes_intake` per `crop_plan`, or a `work_log`. CPO decides whether the extra data-entry burden is worth it. |
| G5 | No test/demo marker on `organisation` (and none on `pilot_request`) | Dev seed or rehearsal plans can enter the metrics | `organisation.is_test boolean not null default false`; `pilot_request.is_spam`. Interim: `excluded_orgs` query variable. |
| G6 | No acquisition channel on `pilot_request`; `country`, `main_crop`, `farm_size_text` are free text | No funnel by channel, region or size | Optional `source` (utm or referrer); normalised crop and country; numeric `farm_size_ha` entered by the concierge. Needs `legal-compliance-specialist` check for any new personal-data field. |
| G7 | Timer semantics and `minutes_spent` provenance not stored | Cannot tell a measured from a typed-in value | Add `minutes_source` (`timer` / `manual`) to `review`, or document the app behaviour in an ADR. |
| G8 | `recommendation_diff` collapses an edit chain to engine vs final and exposes only N rate | Intermediate edits and split changes are only in jsonb | Optional second view with N splits flattened (`nitrogen.splits[]`) per stage, once calibration needs it. |
