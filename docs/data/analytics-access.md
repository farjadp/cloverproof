# Analytics access — S2 metrics and calibration loop

- Status: PROPOSAL (2026-11-16). Nothing here is applied. Owner: `head-of-data`; author: `data-engineer`.
- Needs: Farjad Iranmehr's go for the role and the connection pattern; `cp-database` turns §3 into a migration if accepted.
- Scope: migrations `0001`–`0009`, ADR 0002, ADR 0004, `docs/runbook-db-switch.md`. Railway Postgres + PostGIS. No GA4 / Search Console / warehouse.

## 1. Decision in one paragraph
A NOLOGIN role `cp_analyst` that can SELECT four views in a new `analytics` schema (plus `recommendation`, `review` and `recommendation_diff`, which hold no direct identifiers). No access to `pilot_request` names, emails, notes or consent text, `app_user`, `user_session`, `farmer`, farm or field names. Once per sprint, Farjad Iranmehr (or `cp-platform`) exports the views to CSV with a read-only login. No warehouse, no replica, nothing paid.

## 2. Read-only role

| Item | Proposal |
|---|---|
| Group role | `cp_analyst` NOLOGIN (created in the migration, like `cp_app`). |
| Login | Created outside git by an operator, same pattern as `cp_app_login`: `create role cp_analyst_login login password '<secret store>' in role cp_analyst connection limit 2;` |
| Session defaults | `alter role cp_analyst_login set default_transaction_read_only = on;` `... set statement_timeout = '30s';` `... set idle_in_transaction_session_timeout = '60s';` |
| Grants | `usage` on schema `analytics`; `select` on all its views; `select` on `public.recommendation`, `public.review`, `public.recommendation_diff`. Nothing else. |
| Writes | None. No INSERT/UPDATE/DELETE grant anywhere, and read-only sessions on top. The immutable-table triggers are a third line. |
| PII | Direct identifiers never exposed. `recommendation.reason`, `review.reason` and `edit_reason` are free text from the agronomist: classified **indirect** (could name a farm or person). Accepted because the reason is the calibration signal; the agronomist should be told not to put names there. |

Why the three public grants: `recommendation_diff` (0009) is `security_invoker = true`. Postgres checks a security-invoker view's base tables as the *querying* user even when it is reached through another view, so a definer-rights `analytics` view on top of it is not enough. Verified locally: without the grant, `cp_analyst` gets `permission denied for table recommendation`. Alternative: inline the lineage CTE in the analytics view and skip the public grants; rejected for now (two copies of the lineage logic drift).

`pilot_request` (0001) is owned by the deploy user, not `cp_migrator`, so the migration must also `grant select on public.pilot_request to cp_migrator` (the owner of the analytics views). Found during validation.

Hashing: no hashed email in analytics. An unsalted SHA-256 of an email is reversible by dictionary; a keyed hash needs a secret in the database. The funnel does not need it. When a pilot request must be joined to a farmer, use a foreign key on `pilot_request.id` (see gap G1), not the email.

## 3. Connection pattern

| Option | Writes risk | PII leaves prod | Cost | Effort | Verdict |
|---|---|---|---|---|---|
| A. Read replica + `cp_analyst_login` | none | only view output | Extra Railway service (paid, and I don't know of a managed replica on the Railway Postgres template; it would be self-built) | High | No. Load is ~10 plans; a replica solves a problem we do not have. |
| B. `cp_analyst_login` against prod, per-sprint `\copy` of the analytics views to CSV | none (role + read-only session) | only view output | 0 | Low | **Recommended.** |
| C. Nightly / per-sprint `pg_dump` to a local analysis DB | none on prod | **everything**: emails, names, password hashes, encrypted TOTP secrets, farmer notes | 0 | Medium | No. Moves full PII to a laptop; `--exclude-table` lists rot as tables are added. |

Why no warehouse: at 5–10 farms the whole calibration dataset is tens of rows (Feb–Apr 2027). Every metric is one SQL view over Postgres. A warehouse adds a second copy of farm data to secure and a retention rule to enforce, for no query that Postgres cannot answer in under a millisecond (`calibration_dataset` measured at 0.7 ms on the test fixtures). Revisit when a query is slow on prod, when the farmer portal (Phase 4) brings hundreds of plans, or when data from another source must be joined.

### Option B in practice
Runbook (per sprint, run by Farjad Iranmehr or `cp-platform`; agents do not connect to Railway):
1. Reach the database through the Railway CLI or the temporary TCP proxy from `docs/runbook-db-switch.md` §1; remove the proxy afterwards.
2. Export, with `DATABASE_URL` set to the `cp_analyst_login` URL from the secret store:
   ```sh
   for v in plan_review_summary calibration_dataset pilot_funnel pilot_request_clean; do
     psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
       -c "\copy (select * from analytics.$v) to 'exports/$(date +%F)/$v.csv' csv header"
   done
   ```
   `exports/` is outside git (local folder, not the repo). One sprint's folder is kept until the next sprint report is out, then deleted (retention: 1 sprint locally; prod stays the source of truth).
3. Analyst/data-scientist work on the CSVs (spreadsheet, DuckDB, pandas). No PII columns exist in them except free-text `edit_reason`.

## 4. Proposed analytics views (DDL — proposal, not a migration)

| View | Grain | Key | Use |
|---|---|---|---|
| `analytics.plan_review_summary` | one row per `crop_plan` | `crop_plan_id` | minutes per plan, edit/approve/reject counts, plan state, latest approved N engine vs final |
| `analytics.calibration_dataset` | one row per **approved** recommendation version | `final_recommendation_id` | engine vs agronomist N, inputs snapshot (crop, yield, previous crop, area), soil test source/depth/date, P and K form/value/unit/extraction method, P/K note code, placeholder flag, confidence rule ids, chain minutes |
| `analytics.pilot_request_clean` | one row per non-deleted `pilot_request` | `pilot_request_id` | row-level funnel without name, email, notes, consent text |
| `analytics.pilot_funnel` | week × locale × country | (week_start, locale, country) | requests → contacted-or-later → accepted / declined |

Design notes:
- `calibration_dataset` reads plan inputs and the soil test from `engine_result.input_snapshot`, not from `crop_plan` / `soil_test`. Those tables stay editable after a run; the snapshot is what the engine actually used.
- "Minutes per plan" = `review_minutes_total` (sum of `minutes_spent` over every review of every version of the plan). `approval_minutes_spent` alone undercounts edited plans (fixture: 3 vs 15 minutes). `chain_review_minutes` is the same sum for one engine root.
- `elapsed_plan_to_approval` is wall-clock time, not effort. Do not report it as minutes per plan.
- Deleted pilot requests (`deleted_at` set) are excluded from both pilot views.
- With ≤10 farms, any slice by country/crop can identify a farm. The CSVs are internal only; never publish a slice with fewer than 5 rows.

```sql
-- PROPOSAL ONLY. Not a migration. Runs as the deploy user (needs CREATE on the database).
-- 1. Schema and read-only role ------------------------------------------------------------
create schema if not exists analytics authorization cp_migrator;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'cp_analyst') then
    create role cp_analyst nologin;
  end if;
end
$$;

-- cp_analyst reads the analytics schema; in public only recommendation, review and the diff (end of file).
grant usage on schema analytics to cp_analyst;

-- pilot_request (0001) is owned by the deploy user, not cp_migrator. The analytics views are
-- owned by cp_migrator, so cp_migrator needs SELECT on it (and nothing more).
grant select on public.pilot_request to cp_migrator;

set local role cp_migrator;

-- 2. analytics.plan_review_summary ---------------------------------------------------------
-- Grain: one row per crop_plan. Effort = sum of review.minutes_spent over every review of
-- every recommendation of the plan (approve + edit + reject).
create view analytics.plan_review_summary as
with recs as (
  select r.crop_plan_id,
         count(*)                                    as recommendation_versions,
         count(*) filter (where r.kind = 'engine')     as engine_runs,
         count(*) filter (where r.kind = 'agronomist') as agronomist_versions,
         min(r.created_at)                           as first_recommendation_at
  from public.recommendation r
  group by r.crop_plan_id
), revs as (
  select r.crop_plan_id,
         count(*)                                      as reviews,
         count(*) filter (where v.decision = 'approve') as approvals,
         count(*) filter (where v.decision = 'edit')    as edits,
         count(*) filter (where v.decision = 'reject')  as rejects,
         sum(v.minutes_spent)                          as review_minutes_total,
         min(v.created_at)                             as first_review_at,
         min(v.created_at) filter (where v.decision = 'approve') as first_approved_at
  from public.review v
  join public.recommendation r on r.id = v.recommendation_id
  group by r.crop_plan_id
)
select
  p.organisation_id,
  p.id                                   as crop_plan_id,
  s.label                                as season_label,
  p.field_id,
  f.farm_id,
  p.crop,
  p.target_yield_t_ha,
  p.previous_crop,
  p.plan_date,
  (p.soil_test_id is not null)           as has_soil_test,
  p.created_at                           as plan_created_at,
  coalesce(recs.recommendation_versions, 0) as recommendation_versions,
  coalesce(recs.engine_runs, 0)          as engine_runs,
  coalesce(recs.agronomist_versions, 0)  as agronomist_versions,
  coalesce(revs.reviews, 0)              as reviews,
  coalesce(revs.approvals, 0)            as approvals,
  coalesce(revs.edits, 0)                as edits,
  coalesce(revs.rejects, 0)              as rejects,
  coalesce(revs.review_minutes_total, 0) as review_minutes_total,
  recs.first_recommendation_at,
  revs.first_review_at,
  revs.first_approved_at,
  -- Wall-clock time, not effort: includes waiting time between sessions.
  revs.first_approved_at - p.created_at  as elapsed_plan_to_approval,
  case
    when recs.crop_plan_id is null          then 'no_recommendation'
    when coalesce(revs.approvals, 0) > 0    then 'approved'
    when coalesce(revs.reviews, 0) = 0      then 'awaiting_review'
    when revs.rejects = revs.reviews        then 'rejected'
    else 'in_review'
  end                                    as plan_state,
  la.final_recommendation_id             as latest_approved_recommendation_id,
  la.final_kind                          as latest_approved_kind,
  la.engine_n_rate_kg_ha                 as latest_approved_engine_n_rate_kg_ha,
  la.final_n_rate_kg_ha                  as latest_approved_final_n_rate_kg_ha,
  la.n_rate_delta_kg_ha                  as latest_approved_n_rate_delta_kg_ha,
  la.final_confidence                    as latest_approved_confidence
from public.crop_plan p
join public.season s on s.id = p.season_id
join public.field f  on f.id = p.field_id
left join recs on recs.crop_plan_id = p.id
left join revs on revs.crop_plan_id = p.id
left join lateral (
  select d.final_recommendation_id, d.final_kind, d.engine_n_rate_kg_ha, d.final_n_rate_kg_ha,
         d.n_rate_delta_kg_ha, d.final_confidence
  from public.recommendation_diff d
  where d.crop_plan_id = p.id and d.approved_at is not null
  order by d.approved_at desc
  limit 1
) la on true;

comment on view analytics.plan_review_summary is
  'One row per crop_plan: versions, reviews, agronomist minutes, approval state. No PII.';

-- 3. analytics.calibration_dataset ---------------------------------------------------------
-- Grain: one row per APPROVED recommendation version (recommendation_diff where approved_at
-- is not null). Engine inputs come from the immutable snapshot, not from crop_plan /
-- soil_test (those tables stay editable after the recommendation was made).
create view analytics.calibration_dataset as
with base as (
  select
    d.*,
    jsonb_path_query_first(d.engine_result,
      '$.input_snapshot.soil_test.values[*] ? (@.form == "P" || @.form == "P2O5")') as p_value,
    jsonb_path_query_first(d.engine_result,
      '$.input_snapshot.soil_test.values[*] ? (@.form == "K" || @.form == "K2O")')  as k_value
  from public.recommendation_diff d
  where d.approved_at is not null
)
select
  b.organisation_id,
  b.crop_plan_id,
  b.engine_recommendation_id,
  b.final_recommendation_id,
  b.final_kind,
  b.edit_depth,
  b.engine_version,
  b.pack_id,
  b.pack_version,
  b.pack_status,
  b.pack_sha256,
  -- Plan context (as snapshotted at engine run time)
  b.engine_result ->> 'crop'                                          as crop,
  (b.engine_result #>> '{input_snapshot,target_yield_t_ha}')::numeric as target_yield_t_ha,
  b.engine_result #>> '{input_snapshot,previous_crop}'                as previous_crop,
  (b.engine_result #>> '{input_snapshot,area_ha}')::numeric           as area_ha,
  (b.engine_result #>> '{input_snapshot,plan_date}')::date            as plan_date,
  s.label                                                             as season_label,
  -- Soil test as snapshotted
  coalesce(jsonb_typeof(b.engine_result #> '{input_snapshot,soil_test}') = 'object', false)
                                                                      as has_soil_test,
  b.engine_result #>> '{input_snapshot,soil_test,source}'             as soil_test_source,
  (b.engine_result #>> '{input_snapshot,soil_test,sample_date}')::date as soil_sample_date,
  (b.engine_result #>> '{input_snapshot,soil_test,depth_top_cm}')::numeric    as soil_depth_top_cm,
  (b.engine_result #>> '{input_snapshot,soil_test,depth_bottom_cm}')::numeric as soil_depth_bottom_cm,
  b.p_value ->> 'form'                           as soil_p_form,
  (b.p_value ->> 'value')::numeric               as soil_p_value,
  b.p_value ->> 'unit'                           as soil_p_unit,
  b.p_value ->> 'extraction_method'              as soil_p_extraction_method,
  b.p_value ->> 'extraction_method_detail'       as soil_p_extraction_method_detail,
  b.k_value ->> 'form'                           as soil_k_form,
  (b.k_value ->> 'value')::numeric               as soil_k_value,
  b.k_value ->> 'unit'                           as soil_k_unit,
  b.k_value ->> 'extraction_method'              as soil_k_extraction_method,
  b.k_value ->> 'extraction_method_detail'       as soil_k_extraction_method_detail,
  -- N: engine vs final
  b.engine_result #>> '{nitrogen,method_id}'     as n_method_id,
  b.engine_n_rate_kg_ha,
  b.final_n_rate_kg_ha,
  b.n_rate_delta_kg_ha,
  case when b.engine_n_rate_kg_ha > 0
       then round(b.n_rate_delta_kg_ha / b.engine_n_rate_kg_ha * 100, 1) end as n_rate_delta_pct,
  (b.engine_result #>> '{nitrogen,rate,uses_placeholder}')::boolean as engine_n_uses_placeholder,
  b.engine_result #>> '{nitrogen,bound_applied}' as engine_n_bound_applied,
  -- P/K: engine v0 emits a note only, no rates (see Schema gaps)
  b.engine_result #>> '{phosphorus_potassium,code}' as engine_pk_note_code,
  b.final_result  #>> '{phosphorus_potassium,code}' as final_pk_note_code,
  -- Confidence
  b.engine_confidence,
  b.final_confidence,
  array(select jsonb_array_elements(b.engine_result -> 'confidence_reasons') ->> 'rule_id')
                                                 as engine_confidence_rule_ids,
  -- Did the agronomist change inputs, not only numbers?
  (b.engine_result -> 'input_snapshot') is distinct from (b.final_result -> 'input_snapshot')
                                                 as inputs_changed,
  -- Free text by the agronomist. Classified indirect PII risk: may name a farm or person.
  b.edit_reason,
  b.approved_by,
  b.approved_at,
  b.approval_minutes_spent,
  (select coalesce(sum(v.minutes_spent), 0)
     from public.recommendation_diff d2
     join public.review v on v.recommendation_id = d2.final_recommendation_id
    where d2.engine_recommendation_id = b.engine_recommendation_id) as chain_review_minutes
from base b
join public.crop_plan p on p.id = b.crop_plan_id
join public.season s    on s.id = p.season_id;

comment on view analytics.calibration_dataset is
  'Approved recommendation versions: engine vs final N, inputs snapshot, soil P/K method. No PII columns except free-text edit_reason.';

-- 4. analytics.pilot_request_clean + analytics.pilot_funnel -------------------------------
-- full_name, email, notes, consent_text are dropped. Rows with a deletion request are excluded.
create view analytics.pilot_request_clean as
select
  pr.id                              as pilot_request_id,
  pr.created_at,
  pr.locale,
  pr.country,
  lower(btrim(pr.main_crop))         as main_crop,
  pr.farm_size_text,
  (pr.notes is not null)             as has_notes,
  pr.status
from public.pilot_request pr
where pr.deleted_at is null;

comment on view analytics.pilot_request_clean is
  'pilot_request without name, email, notes, consent text; deleted rows excluded.';

create view analytics.pilot_funnel as
select
  date_trunc('week', c.created_at)::date                                   as week_start,
  c.locale,
  c.country,
  count(*)                                                                 as requests,
  count(*) filter (where c.status in ('contacted', 'accepted', 'declined')) as contacted_or_later,
  count(*) filter (where c.status = 'accepted')                            as accepted,
  count(*) filter (where c.status = 'declined')                            as declined,
  count(*) filter (where c.status = 'new')                                 as still_new
from analytics.pilot_request_clean c
group by 1, 2, 3;

comment on view analytics.pilot_funnel is
  'Weekly pilot requests by locale/country and current status. Status is current state only.';

reset role;

grant select on all tables in schema analytics to cp_analyst;

-- public.recommendation_diff is security_invoker (0009). Postgres checks a security_invoker
-- view's base tables as the querying user even when it is reached through another view, so
-- cp_analyst needs SELECT on the diff and its two base tables. Neither table holds a direct
-- identifier; `reason` columns are free text (indirect). Every other public table stays hidden.
grant select on public.recommendation, public.review, public.recommendation_diff to cp_analyst;
```

## 5. Local validation (done 2026-11-16)
- Throwaway container `postgis/postgis:17-3.5` on 127.0.0.1:55499 (own container, not the compose one, so no other worktree's database was touched); migrations `0001`–`0009` applied with `make db-migrate`'s runner, then `db/seeds/dev.sql`.
- In one transaction: fictional fixtures (example.org only; recommendation `result` documents generated by the real engine from the two sample golden cases, one edited to 160 kg N/ha), the §4 DDL, queries, then `ROLLBACK`. Container removed afterwards. No remote database contacted.
- Results: all four views created and returned the expected rows (engine 187.5 → final 160.0, delta −27.5 / −14.7 %, P Olsen 14 mg/kg, K "other", `PK_NOT_CALCULATED_V0`; no-test plan → `PK_SOIL_TEST_RECOMMENDED`, rules `C1_NO_SOIL_TEST`, `C6_PLACEHOLDER_CONSTANT_USED`; plan minutes 15 vs approval minutes 3; deleted pilot request excluded).
- As `cp_analyst`: views readable; `pilot_request`, `app_user`, `membership` → permission denied; INSERT into a view → permission denied. After rollback: 0 analytics views, no `cp_analyst` role left.

## 6. Schema gaps (proposals for the CPO; no migration written)

| # | S2 need | Gap today | Proposal |
|---|---|---|---|
| G1 | Pilot funnel past "accepted" (request → farm onboarded → first plan → approved plan) | No link from `pilot_request` to `organisation` / `farmer` | Nullable `farmer.pilot_request_id uuid references pilot_request(id) on delete set null` |
| G2 | Funnel timing (time to contact, to accept) and honest "declined after contact" | `status` holds the current state only; no transition timestamps | `pilot_request_status_event (pilot_request_id, status, at)` insert-only, or `contacted_at` / `decided_at` columns |
| G3 | Minutes per plan that are trustworthy | `minutes_spent` is typed by hand per review; no plan start/end | App records `review.started_at` (timer start) next to `created_at`; keep `minutes_spent` as the agronomist's figure and compare |
| G4 | **P/K calibration — SOLVED BY R2** | Was: engine v0 emits only a note; P/K finals had no structured place | Reconciliation R2: `recommendation_line` (§6.4) per nutrient with explicit form; no `p_rate_kg_ha` / `k_rate_kg_ha` columns. `analytics.calibration_dataset` is replaced by the per-line `calibration_delta` view (`calibration-delta-spec.md`) once migrated; grant `cp_analyst` the base tables it needs and `farmer (id, is_test)` column-level only |
| G5 | Soil test that a recommendation used, as a key | Only in `inputs_snapshot` (values, no `soil_test.id`); `crop_plan.soil_test_id` is editable after the run | `recommendation.soil_test_id` (immutable with the row), or the id inside the snapshot |
| G6 | Why the agronomist edited, countable | `reason` is free text only | `review.reason_code` enum (e.g. `yield_expectation`, `previous_crop_credit`, `soil_test`, `local_practice`, `pack_constant`, `other`) + free text; codes agreed with the agronomist |
| G7 | Planned vs applied rate vs approved rate | `application_log.recommendation_id` is optional, so a log row may not name the approved version | Make it required once a plan is approved (app rule or CHECK via trigger); not blocking for S2 |

## 7. Freshness and schedule
- Manual export once per sprint, the day before the sprint report. Freshness target: data ≤ 1 day old at report time.
- Why manual: ≤10 farms, plans entered Feb–Apr 2027, decisions taken per sprint. A scheduled job means a stored analyst credential in a running service, a place to put the output, and alerting — more attack surface and upkeep than the four `\copy` commands it replaces. Every view is idempotent and re-runnable (pure SELECT over immutable rows + current state), so a missed or repeated export loses nothing.
- During the field season (Feb–Apr 2027) switch to weekly if the agronomist asks for a calibration review mid-sprint.
- Automate (Railway cron service exporting to the private bucket of ADR 0005, alerting via the agent-reports channel) when: exports are needed more than weekly, or the farmer portal (Phase 4) starts. Needs Farjad Iranmehr's go (it adds a service).

Data-quality checks to run with each export (SQL, results pasted into the sprint report):
- every approved plan has `review_minutes_total > 0`;
- `calibration_dataset` row count = count of `review` rows with `decision = 'approve'`;
- `has_soil_test` and `soil_test_source` consistent (no source without a test);
- no `edit_reason` containing an `@` (email leak check).

## 8. Open questions
1. `minutes_spent`: per review session (additive) or cumulative for the plan? The sum in `plan_review_summary` assumes additive. `cp-concierge-app` must confirm.
2. OK to grant `cp_analyst` SELECT on `recommendation` / `review` (free-text reasons), or should `recommendation_diff` become `security_invoker = false` / the lineage be inlined?
3. Who runs the per-sprint export: Farjad Iranmehr or `cp-platform`?
4. Is a farm's *country/crop* slice with <5 rows acceptable inside the team (it is identifying at this scale)?
5. ~~G4 (P/K) needs a product decision~~ Decided by R2 (2026-11-16): `recommendation_line`. Remaining: cp-database migrates it before Feb 1, 2027.
6. D4: every analytics view must carry `reviewer_kind`; exports for calibration filter to human approvals (`counts_toward_calibration`).
