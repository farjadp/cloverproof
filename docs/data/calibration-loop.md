# Calibration loop — how each reviewed plan becomes evidence

Owner: `data-scientist` (reports to `head-of-data`). Status: DRAFT spec, S2 (2026-11-16); updated 2026-11-16 for D4 + R2.
Applies to: engine `0.2.0`, pack `placeholder` `v0`, migrations `0001`–`0009` in `db/migrations/`.

This spec defines the calibration dataset (engine output vs agronomist final + reason), how it is
queried, tagged and analysed, and how a finding may turn into a pack change. It contains **no
agronomic constant values**. Every value in examples is a symbolic placeholder (`<CURRENT>`,
`<PROPOSED>`, `<TOLERANCE>`). The data team never edits `engine/` or `packs/`, and nothing in this
loop produces a number that reaches a farmer.

## Update 2026-11-16 — D4 (AI reviewer) and R2 (per-line storage)

Source: `docs/plans/backend-plan-reconciliation.md` (D4, R2) and `docs/plans/backend-plan.md` §6.4.
These rules override anything below that conflicts with them.

1. **Two kinds of sign-off.** Until a human agronomist is named, the reviewer is the AI agent
   `cp-agronomist`; its sign-off is **`ai_reviewed`**. A human user with the `agronomist` role gives
   **`agronomist_approved`**. The kind is stamped on each `review` row (`review.reviewer_kind`,
   proposed name; cp-database flag in migrations 0011+).
2. **Only human-approved units are calibration evidence.** `ai_reviewed` units never count toward:
   the 90 % agreement gate, the calibration baseline, Tier 1 flags, Tier 2 constant-change
   proposals (§4.1), or the approval / review-gate rates. They may be reported in a separate block
   "AI review diagnostics (not agronomist approval)" and are never pooled with human units
   (added to §5.2).
3. **No baseline without human cases** (traceability NB-DAT-03, OQ-04). Until human-approved
   units exist, the S3 deliverable is the baseline **method** plus the line "no human-approved
   cases yet" (§7).
4. **Per-line evidence (R2).** The engine-vs-final delta is computed per `recommendation_line`
   (nutrient + explicit form + split, with product and timing as attributes), not on P/K columns
   of `recommendation`. The view is specified in `docs/data/calibration-delta-spec.md` (DM-16).
   Old gap G1 ("no P/K numbers") is **SOLVED BY R2** once `recommendation_line` is migrated and the
   engine writes P/K lines (S3 per backend plan R5).
5. **The 90 % agreement gate is undefined.** The reconciliation names it; nothing defines unit
   (line or nutrient total), tolerance per nutrient (agronomist-todo #10), treatment of
   added/removed lines, or population. Data does not invent it (open question).
6. **Target schema.** Queries in §2 below are written against migrations 0001–0009
   (`recommendation_diff`, N only) and remain valid for today's data. The per-line replacement is
   the reference SQL in `calibration-delta-spec.md` §5 — **target schema (§6.4), not yet migrated**.
   Who the human agronomist is (Farjad Iranmehr, named in CLAUDE.md, or someone else) is open
   (OQ-04, risk RK-X1); this file's "Farjad Iranmehr" means "the human agronomist" until resolved.

---

## 0. What the dataset can and cannot tell us (read first)

- **Reference = one agronomist's judgement, not crop response.** Δ measures how far the engine is
  from Farjad Iranmehr's number. It does not measure yield or N-use outcomes; there is no harvest
  table (schema gap G6). "Calibrated" here means "agrees with the agronomist", nothing more.
- **Anchoring.** In the concierge tool the agronomist sees the engine number before he decides.
  Anchored finals pull Δ towards 0, so |Δ| from the tool underestimates disagreement. The
  Dec 18 golden cases are given blind (input → his rate). Blind and anchored evidence are never
  pooled (§5.4).
- **Placeholder pack.** While `pack_status = 'placeholder'`, every engine number is built on
  constants picked for easy arithmetic. Δ against `placeholder v0` measures distance from
  arbitrary numbers. It is still useful for bug finding and for "which component does he override",
  but it is not a measurement error of a real constant.
- **Confidence is degenerate in v0.** Rule C6 caps every plan that uses a PLACEHOLDER constant at
  `low`, so every v0 plan is `low`. Stratifying by confidence becomes informative only once a pack
  has validated constants.
- **One rate, many constants.** The N mass balance turns uptake, soil supply, previous-crop
  credit, efficiency and bounds into one rate. A Δ on the rate cannot identify which constant is
  off. Attribution comes from the reason code (§3) and from stratification (previous crop,
  bound applied, target yield), never from the rate alone.

---

## 1. Unit of evidence

### 1.1 Definition

**One evidence unit = one approved final recommendation compared with the engine row at the root
of its `parent_id` chain**, deduplicated to one unit per field × season × crop.

- Source: view `recommendation_diff` (migration 0009) filtered to `approved_at is not null`.
  It already joins every version to its engine root (`engine_recommendation_id`) and gives
  `n_rate_delta_kg_ha = final − engine`.
- **Sign convention:** Δ = final − engine. Positive Δ = the agronomist wants more N than the engine.
- **Approved without edits** (`edit_depth = 0`, Δ = 0) is evidence: agreement is data. Leaving
  these out would bias every statistic away from zero.
- Unapproved versions (drafts, edits not yet approved, superseded intermediates) are **not** units.
- **D4/R2 (target schema):** the unit becomes one *human-approved* final per season, read as a set
  of line pairs from `calibration_delta` (`counts_toward_calibration = true`). Line matching
  (key `nutrient` + `nutrient_form` + `split_no`; added/removed lines are separate signals, never a
  zero delta; product and timing changes are attributes) is defined in
  `calibration-delta-spec.md` §2. Statistics are computed per nutrient on matched lines and on the
  per-nutrient total (spec §6.2), with add and removal rates reported beside them. An
  `ai_reviewed` final is never a unit.

### 1.2 Multi-step edits

Chain `engine → A1 → A2 (approved)`:
- One unit: A2 vs engine root. A1 is not a separate unit (it was never approved).
- `edit_depth` is kept as a covariate (depth > 1 hints at hesitation or a self-correction).
- Every step's reason (`recommendation.reason` on A1 and A2, and `review.reason` on the `edit`
  reviews) is collected (query Q4) and each step is tagged. The unit's **primary code** is the code
  of the step with the largest |step Δ|. A step tagged `DATA_ENTRY` does not make the whole unit a
  data error unless it is the primary step.

### 1.3 Rejects

`review.decision = 'reject'` has no resulting numbers, so a reject is **never a numeric unit**.
- Counted per stratum as **reject rate** = rejects / (rejects + approvals) on engine roots,
  human reviews only (D4); AI rejects are a diagnostic.
- Its reason is tagged with the same taxonomy (§3). A reject tagged `ENGINE_BUG` goes to the bug
  list in the same sprint.
- If the crop plan is later re-run (a new engine root) and approved, the approved re-run is the
  unit; the reject is attached as context. If the re-run's `inputs_snapshot` differs from the
  rejected root's, the reject was an input problem, not a calibration signal.

### 1.4 Deduplication

1. **Several approved versions in one crop plan** (re-runs are new roots; each can be approved
   once): keep the **latest by `approved_at`**; earlier ones are reported as `superseded`.
2. **Several crop plans for the same field, season and crop** (`crop_plan_field_season_idx` is not
   unique): keep the latest approved; report duplicates.
3. **Same case entered twice** (e.g. a Dec 18 golden case also typed into the tool): it stays in
   the blind set only; the tool copy is excluded (needs a flag, gap G8; until then, a manual
   exclusion list kept by `data-scientist`).

### 1.5 Exclusions

| Excluded | How detected today | Reason |
|---|---|---|
| Dev seed organisation | `organisation.id = '00000000-0000-4000-8000-000000000001'` (`db/seeds/dev.sql`) or name contains `(dev seed)` | Fictional data |
| Test organisations | name `ilike 'test org %'` (pattern used in `app/tests/db/conftest.py`) | Test fixtures |
| Demo / training orgs | manual list held by `data-scientist`, reviewed each sprint | Not real decisions |
| Final with changed inputs | `final.inputs_snapshot <> engine.inputs_snapshot` | Input correction, not a constant signal; counted as data quality |
| Final on a different pack than its root | `final.pack_sha256 <> engine.pack_sha256` | Not comparable; flag as data-quality issue |
| Primary code `DATA_ENTRY`, `FARMER_CONSTRAINT`, `ROUNDING` (within tolerance) | reason tag (§3) | Not calibration signals |
| Primary code `ENGINE_BUG` | reason tag | Bug list; excluded from calibration until the fix ships, then re-evaluated by replay |

Name patterns are fragile; a real `organisation` flag is gap G3.

---

## 2. Queries

Postgres, real column names from migrations 0003–0009 only. Run with a read-only connection
(gap G7). `recommendation_diff` is `security_invoker`, so the role needs `select` on the
underlying tables. Do not select PII columns (`farmer.display_name`, `farmer.notes`,
`app_user.email`, `farm.name`, `field.name`); work with ids. Free-text reasons stay in the
database; reports quote codes or paraphrases, never raw text into git.

Tolerance for "agree" is TODO(agronomist) #10. In psql: `\set tol_kg_n_ha <TOLERANCE>`.

Checked 2026-11-16: every query below ran without error on a throwaway PostGIS 17 container with
migrations 0002–0009, `db/seeds/dev.sql` and fictional rows (two engine roots, two-step edit
chains, approvals, rejects). Q6 flagged the edited rows as inconsistent, which confirms gap G5.

### 2.1 Where each stratum lives

| Stratum | Column / path | Note |
|---|---|---|
| Nutrient N | `recommendation.n_rate_kg_ha` (generated from `result.nitrogen.rate.value`) | Only nutrient with a number in v0 |
| P / K | Today: `result -> 'phosphorus_potassium'` is a `Note {code, text}` only. Target (R2): `recommendation_line` rows with `nutrient` + explicit form | Gap G1 **SOLVED BY R2** once migrated; use `calibration_delta` |
| Crop | `result ->> 'crop'` (immutable) | `crop_plan.crop` is mutable; do not use |
| Previous crop, target yield, area, plan date | `inputs_snapshot ->> 'previous_crop'`, `'target_yield_t_ha'`, `'area_ha'`, `'plan_date'` | Snapshot, not `crop_plan` (mutable) |
| Soil test present / source | `inputs_snapshot -> 'soil_test'` (JSON `null` when none), `->> 'source'` | |
| Extraction method per nutrient | `inputs_snapshot -> 'soil_test' -> 'values'[*] ->> 'extraction_method'`, `'form'`, `'extraction_method_detail'` | No `nutrient` key in the snapshot; derive from `form`. No link back to the `soil_test` row id (gap G4) |
| Confidence | `recommendation_diff.engine_confidence`, `final_confidence`; rules in `result -> 'confidence_reasons'` | All `low` in v0 (C6) |
| Pack / engine | `pack_id`, `pack_version`, `pack_status`, `pack_sha256`, `engine_version` | Use `pack_sha256` as the identity |
| Bound hit | `result #>> '{nitrogen,bound_applied}'` (`min` / `max` / null) | |
| Farm, region, season | `crop_plan.field_id → field.farm_id → farm.country_code, farm.region`; `crop_plan.season_id → season.label` | Through mutable `crop_plan` (gap G4) |

### 2.2 Q1 — evidence units (base CTE, reused by Q2–Q6)

```sql
with excluded_org as (
  select o.id
  from organisation o
  where o.id = '00000000-0000-4000-8000-000000000001'   -- db/seeds/dev.sql
     or o.name ilike '%(dev seed)%'
     or o.name ilike 'test org %'
     -- or o.id in (<manual exclusion list>)
),
approved as (
  select d.*,
         row_number() over (partition by d.crop_plan_id
                            order by d.approved_at desc, d.final_recommendation_id) as rn_plan,
         count(*)     over (partition by d.crop_plan_id) as approvals_in_plan
  from recommendation_diff d
  where d.approved_at is not null
    and d.organisation_id not in (select id from excluded_org)
),
joined as (
  select a.*,
         cp.field_id, cp.season_id, s.label as season_label,
         f.farm_id, fm.country_code, fm.region,
         e.inputs_snapshot  as engine_inputs,
         fr.inputs_snapshot as final_inputs,
         fr.pack_sha256     as final_pack_sha256,
         a.engine_result ->> 'crop' as crop,
         row_number() over (partition by cp.field_id, cp.season_id, a.engine_result ->> 'crop'
                            order by a.approved_at desc, a.final_recommendation_id) as rn_field
  from approved a
  join recommendation e  on e.id  = a.engine_recommendation_id
  join recommendation fr on fr.id = a.final_recommendation_id
  join crop_plan cp on cp.organisation_id = a.organisation_id and cp.id = a.crop_plan_id
  join season s     on s.organisation_id  = cp.organisation_id and s.id = cp.season_id
  join field f      on f.organisation_id  = cp.organisation_id and f.id = cp.field_id
  join farm fm      on fm.organisation_id = f.organisation_id  and fm.id = f.farm_id
  where a.rn_plan = 1
),
units as (
  select j.*,
         j.engine_inputs ->> 'previous_crop'                 as previous_crop,
         (j.engine_inputs ->> 'target_yield_t_ha')::numeric  as target_yield_t_ha,
         case
           when jsonb_typeof(j.engine_inputs -> 'soil_test') <> 'object' then 'none'
           else j.engine_inputs -> 'soil_test' ->> 'source'          -- 'lab' | 'estimate'
         end                                                 as soil_test_source,
         j.engine_result #>> '{nitrogen,bound_applied}'      as engine_bound_applied,
         (j.final_inputs <> j.engine_inputs)                 as inputs_changed,
         (j.final_pack_sha256 <> j.pack_sha256)              as pack_changed,
         case when j.engine_n_rate_kg_ha > 0
              then j.n_rate_delta_kg_ha / j.engine_n_rate_kg_ha end as n_rate_delta_rel
  from joined j
  where j.rn_field = 1
)
select * from units;
```

Units with `inputs_changed` or `pack_changed` are kept in the extract but excluded from the
statistics (§1.5). The superseded counts come from `approvals_in_plan > 1` and `rn_field > 1`.

### 2.3 Q2 — N statistics per stratum (one pack fingerprint at a time)

```sql
-- <Q1 CTEs here>
select pack_id, pack_version, pack_sha256, pack_status, engine_version,
       season_label, crop, soil_test_source, engine_confidence,
       count(*)                                  as n_plans,
       count(distinct farm_id)                   as n_farms,
       avg(n_rate_delta_kg_ha)                   as bias_kg_ha,
       avg(abs(n_rate_delta_kg_ha))              as mae_kg_ha,
       stddev_samp(n_rate_delta_kg_ha)           as sd_kg_ha,
       percentile_cont(0.5)  within group (order by n_rate_delta_kg_ha) as median_kg_ha,
       percentile_cont(0.25) within group (order by n_rate_delta_kg_ha) as q1_kg_ha,
       percentile_cont(0.75) within group (order by n_rate_delta_kg_ha) as q3_kg_ha,
       min(n_rate_delta_kg_ha) as min_kg_ha, max(n_rate_delta_kg_ha) as max_kg_ha,
       count(*) filter (where n_rate_delta_kg_ha >  :tol_kg_n_ha)     as n_up,
       count(*) filter (where n_rate_delta_kg_ha < -:tol_kg_n_ha)     as n_down,
       count(*) filter (where abs(n_rate_delta_kg_ha) <= :tol_kg_n_ha) as n_agree,
       avg(edit_depth)                           as mean_edit_depth
from units
where not inputs_changed and not pack_changed
group by grouping sets (
  (pack_id, pack_version, pack_sha256, pack_status, engine_version, season_label, crop),
  (pack_id, pack_version, pack_sha256, pack_status, engine_version, season_label, crop, soil_test_source),
  (pack_id, pack_version, pack_sha256, pack_status, engine_version, season_label, crop, engine_confidence)
)
order by pack_sha256, season_label, crop, soil_test_source nulls first, engine_confidence nulls first;
```

Direction consistency = `greatest(n_up, n_down) / nullif(n_up + n_down, 0)` (ties within tolerance
excluded). Swap the grouping set for `previous_crop`, `engine_bound_applied`, `country_code, region`
as needed. Interval estimates (§4) are computed offline from the Q1 extract, not in SQL.

### 2.4 Q3 — soil-test extraction method per nutrient (jsonb)

```sql
-- <Q1 CTEs here>
select u.final_recommendation_id, u.farm_id, u.pack_sha256,
       v ->> 'form' as form,
       case v ->> 'form'
         when 'N' then 'N' when 'NO3-N' then 'N'
         when 'P' then 'P' when 'P2O5'  then 'P'
         when 'K' then 'K' when 'K2O'   then 'K'
       end                                  as nutrient,
       v ->> 'extraction_method'            as extraction_method,   -- olsen | bray-1 | mehlich-3 | other
       v ->> 'extraction_method_detail'     as extraction_method_detail,
       (v ->> 'value')::numeric             as value,
       v ->> 'unit'                         as unit,
       (u.engine_inputs -> 'soil_test' ->> 'depth_top_cm')::numeric    as depth_top_cm,
       (u.engine_inputs -> 'soil_test' ->> 'depth_bottom_cm')::numeric as depth_bottom_cm,
       (u.engine_inputs -> 'soil_test' ->> 'sample_date')::date        as sample_date,
       u.n_rate_delta_kg_ha
from units u
cross join lateral jsonb_array_elements(
  case when jsonb_typeof(u.engine_inputs -> 'soil_test') = 'object'
       then u.engine_inputs -> 'soil_test' -> 'values'
       else '[]'::jsonb end) as v;
```

In engine v0 the soil test does not change the N rate (only confidence and the P/K note), so this
stratum matters for P/K once P/K lines exist (gap G1, SOLVED BY R2: `recommendation_line`).

### 2.5 Q4 — reasons along each chain (for tagging)

```sql
-- <Q1 CTEs here>
, chain as (
  select u.final_recommendation_id as unit_id, r.id, r.parent_id, r.kind, r.reason,
         r.n_rate_kg_ha, 0 as steps_back
  from units u
  join recommendation r on r.id = u.final_recommendation_id
  union all
  select c.unit_id, p.id, p.parent_id, p.kind, p.reason, p.n_rate_kg_ha, c.steps_back + 1
  from chain c
  join recommendation p on p.id = c.parent_id
)
select c.unit_id, c.id as recommendation_id, c.steps_back, c.kind,
       c.n_rate_kg_ha - p.n_rate_kg_ha as step_delta_kg_ha,
       c.reason                        as version_reason,
       rv.reason                       as edit_review_reason,
       rv.minutes_spent
from chain c
left join recommendation p on p.id = c.parent_id
left join review rv on rv.resulting_recommendation_id = c.id and rv.decision = 'edit'
where c.kind = 'agronomist'
order by c.unit_id, c.steps_back desc;
```

(`with recursive` is required at the top of the combined statement.)

### 2.6 Q5 — rejects

```sql
-- <excluded_org CTE>
select rv.organisation_id, rec.crop_plan_id, rv.recommendation_id, rec.kind,
       rec.pack_sha256, rec.engine_version, rv.reason, rv.minutes_spent, rv.created_at,
       exists (
         select 1 from review a
         join recommendation r2 on r2.id = a.recommendation_id
         where a.decision = 'approve' and r2.crop_plan_id = rec.crop_plan_id
           and a.created_at > rv.created_at
       ) as later_approved_in_plan
from review rv
join recommendation rec on rec.organisation_id = rv.organisation_id and rec.id = rv.recommendation_id
where rv.decision = 'reject'
  and rv.organisation_id not in (select id from excluded_org);
```

### 2.7 Q6 — data-quality checks (run before any statistic)

```sql
-- <Q1 CTEs here>; tol_total_kg is the per-field total tolerance (TODO(agronomist) #10)
select u.final_recommendation_id,
       u.inputs_changed, u.pack_changed, u.approvals_in_plan,
       u.final_n_rate_kg_ha,
       (select sum((s #>> '{rate,value}')::numeric)
          from jsonb_array_elements(u.final_result #> '{nitrogen,splits}') s) as final_split_sum_kg_ha,
       (u.final_result #>> '{nitrogen,total,value}')::numeric               as final_total_kg,
       (u.final_inputs ->> 'area_ha')::numeric                               as area_ha
from units u
where u.inputs_changed or u.pack_changed or u.approvals_in_plan > 1
   or abs(coalesce((select sum((s #>> '{rate,value}')::numeric)
                      from jsonb_array_elements(u.final_result #> '{nitrogen,splits}') s), 0)
          - u.final_n_rate_kg_ha) > :tol_kg_n_ha
   or abs((u.final_result #>> '{nitrogen,total,value}')::numeric
          - u.final_n_rate_kg_ha * (u.final_inputs ->> 'area_ha')::numeric) > :tol_total_kg;
```

The schema does not force an agronomist row's splits and total to match its rate (gap G5); the
DB tests build edits by replacing only `nitrogen.rate.value`. Until the app recomputes them, split
and total comparisons are unreliable and only the rate is analysed.

### 2.8 P/K

**Status: SOLVED BY R2 (target).** With `recommendation_line` (§6.4) P and K are ordinary lines with
an explicit form; the P/K engine-vs-final delta comes from `calibration_delta` exactly like N
(`calibration-delta-spec.md`). P/K numbers appear only when the engine emits P/K with a soil test
(S3 per R5) and stay N-only without a test (hard rule 3). The text below describes v0 / migrations
0001–0009 and applies only to plans created before the migration.

There is no P/K dataset in v0: `result.phosphorus_potassium` holds only a code
(`PK_NOT_CALCULATED_V0` or `PK_SOIL_TEST_RECOMMENDED`). The only query possible is a count of
codes. The agronomist's own P/K numbers have no column and would be lost except as free text
(gap G1 — now SOLVED BY R2 for plans created after `recommendation_line` is migrated).

```sql
-- <Q1 CTEs here>
select engine_result #>> '{phosphorus_potassium,code}' as engine_pk_code,
       final_result  #>> '{phosphorus_potassium,code}' as final_pk_code,
       soil_test_source, count(*)
from units group by 1, 2, 3;
```

---

## 3. Edit-reason taxonomy

Every edit step and every reject gets **one primary code** (and optionally one secondary).
Free text stays as written; the code is added alongside it.

| Code | Meaning | Points to | Calibration signal? |
|---|---|---|---|
| `YIELD_GOAL` | Agronomist uses a different realistic target yield than the input | Intake / `target_yield_t_ha`; C4 range | No for constants (input issue); yes for intake guidance |
| `PREV_CROP_CREDIT` | Disagrees with the previous-crop credit | `crops.<crop>.nitrogen.previous_crop_credits.<crop>.credit` | Yes |
| `SOIL_N_SUPPLY` | Soil supplies more/less N (soil type, OM, measured nitrate) | `soil_n_supply`; agronomist-todo #9 | Yes |
| `N_EFFICIENCY` | Loss risk, product, placement, timing affects recovery | `fertilizer_n_efficiency` | Yes |
| `UPTAKE_QUALITY` | Protein target, variety, uptake per tonne | `n_uptake_per_t_grain`; method form #6 | Yes |
| `RATE_BOUND` | Engine rate hit min/max and he disagrees with the bound | `min_rate`, `max_rate` | Yes |
| `SPLIT_TIMING` | Changes split fractions or timing, not the total | `splits[*]` | Yes (splits only) |
| `MANURE_ORGANIC` | Manure / organic amendment not modelled | Method gap (#6c), not a constant | No for constants; yes for method |
| `SOIL_TEST_PK` | P/K decision or soil-test interpretation | P/K lines (R2), pack P/K critical values | Yes, once P/K lines exist |
| `LOCAL_PRACTICE` | Regional norm, experience, no specific component named | Unattributed | Weak: question to agronomist, never a constant change alone |
| `FARMER_CONSTRAINT` | Budget, product availability, equipment, farmer preference | — | No |
| `ROUNDING` | Rounded to product / spreader rate | — | No if within tolerance |
| `ENGINE_BUG` | Engine did something wrong (wrong component, wrong rule fired, explanation mismatch) | `cp-engine` bug list | No (bug) |
| `DATA_ENTRY` | Wrong input or typo (area, previous crop, yield, his own number) | Data quality | **No — never a calibration signal** |
| `OTHER` | Requires a short note | Reviewed each sprint; recode or extend list | No until recoded |

Rules:
- **Who tags.** Target state: the agronomist picks the code in the edit/reject form at review time
  (needs a column, gap G2). Interim: `data-scientist` proposes a code from the free text; the
  agronomist confirms or changes it at the sprint calibration review. **His code wins.** Once
  there are ≥ 20 tagged edits, `data-analyst` tags a copy blind and Cohen's κ is reported; if
  κ is low, the definitions are rewritten before any analysis uses the codes.
- **Interim storage.** Tags live outside the immutable tables, in a session temp table loaded from
  a data-team CSV (`recommendation_id, step, primary_code, secondary_code, tagged_by,
  confirmed_by_agronomist, tagged_on`). The CSV contains ids and codes only, no free text, no PII.
  ```sql
  create temp table reason_tag (
    recommendation_id uuid, primary_code text, secondary_code text,
    tagged_by text, confirmed_by_agronomist boolean, tagged_on date);
  \copy reason_tag from '<path to tag csv>' csv header
  ```
- A `DATA_ENTRY` edit is a data-quality metric (per sprint count, by field). It is excluded from
  bias/MAE. The right fix is a corrected crop plan and an engine re-run, not an edit; the
  concierge SOP should say so.
- Changes to the code list are versioned in this file; old tags are mapped, never silently
  rewritten.

---

## 4. Statistics

All computed per stratum (§5) on units that pass §1.5, from the Q1 extract.

| Statistic | Definition | Interval / test |
|---|---|---|
| Signed bias | mean Δ (kg N/ha); also median Δ | n_farms ≥ 10: farm-cluster bootstrap 95% CI (resample farms, 2,000 reps, percentile). Below: report every case and the range, no CI |
| MAE | mean \|Δ\| | Same bootstrap |
| Spread | SD of Δ, IQR, min–max | Report always; SD only with n ≥ 5 |
| Relative Δ | Δ / engine rate (engine > 0) | Descriptive only |
| Agreement rate | share with \|Δ\| ≤ tolerance | Wilson 95% interval |
| Direction consistency | share of non-agreeing units with the majority sign | Wilson 95% interval; exact sign test as a descriptive check |
| Reject rate | rejects / (rejects + approvals) | Wilson 95% interval |
| Edit rate | share of units with `edit_depth > 0` | Wilson 95% interval |

Notes:
- **Fields within a farm are not independent** (same farmer, same agronomist reasoning, same
  soils). The effective sample is between the number of farms and the number of plans; the
  number of farms is the conservative count and is always reported next to `n_plans`.
- Each plan counts once; no area weighting (a decision is the unit, not a hectare).
- p-values are never a decision rule on their own; they are reported to show how little small
  samples can say.
- Yield-slope analysis (regress Δ on `target_yield_t_ha` to separate a per-tonne effect from a
  fixed offset) only at n_plans ≥ 30 with a yield range the agronomist agrees is wide enough.

### 4.1 Minimum sample before proposing any constant change

| Tier | Allowed output | Minimum per stratum | Why this number |
|---|---|---|---|
| **0 — Anecdote** | Bug reports, data-entry findings, questions to the agronomist | n ≥ 1 | One clear engine error is enough to fix a bug; it says nothing about a constant |
| **1 — Direction flag** | "Consistent direction" flag + a question to the agronomist; **no value** | n_plans ≥ 5 from ≥ 3 farms, ≥ 80% of non-agreeing units in one direction | Five same-sign cases are the smallest set that is even suggestive; exact two-sided sign test with 5/5 is p = 0.0625, so it **cannot** exclude chance. A flag, not evidence |
| **2 — Constant-change proposal** | Evidence memo with an estimate and interval | **n_plans ≥ 20 from ≥ 10 farms**, one `pack_sha256`, one crop, one nutrient, one season/region stratum; AND farm-bootstrap 95% CI of mean Δ excludes 0 and \|mean Δ\| > tolerance; AND direction consistency ≥ 15/20 (Wilson lower bound > 0.5); AND ≥ 60% of edits carry a primary code pointing at the same constant, confirmed by the agronomist | t-interval half-width on the mean is 1.24 SD at n = 5, 0.72 SD at n = 10, 0.47 SD at n = 20. If fields cluster fully by farm, n_eff = farms, so ≥ 10 farms keeps the worst case near 0.72 SD; below 10 clusters a cluster bootstrap is unreliable. 15/20 is the smallest count whose Wilson lower bound is above 0.5 (0.531; 14/20 gives 0.481). The code rule is needed because the rate cannot identify which constant is off |

**Human-only (D4).** Every tier counts only `agronomist_approved` units. `ai_reviewed` units can
feed Tier 0 (a bug report is a bug whoever finds it) but never Tier 1 or Tier 2, and never appear in
a proposal memo's evidence numbers.

**Plainly:** the 5 Dec 18 wheat cases and a 5–10-farm season are **anecdotes**. They can support
bug finding, consistent-direction flags (Tier 1) and a list of questions for the agronomist. They
**cannot** support re-fitting or re-estimating any constant. With at most 10 farms in the whole
season, spread over strata, Tier 2 is unlikely to be reached in 2027; the expected sprint output
is "no proposal: below minimum sample", and that is a correct result.

Constants still get replaced in 2027 — by the agronomist, with a source (agronomist-todo #2–#8).
That is his decision, not a data result. The calibration data then checks his pack against his
own later decisions.

### 4.2 In-sample warning

Any proposed value fitted on the same plans will always look better on those plans. A proposal is
evaluated **prospectively**: on plans approved after the decision, under the new pack. Replay
(§5.3) of historical plans under a candidate pack is shown as "in-sample, not validation".

---

## 5. Strata and pooling rules

### 5.1 Strata
`pack_sha256` (identity of `pack_id` + `pack_version`) → `engine_version` → season → crop →
nutrient → then one of: soil-test source / extraction method, previous crop, bound applied,
engine confidence, country/region.

### 5.2 Never pool silently
- **Pack versions:** never pool across `pack_sha256`. Δ is relative to the engine number, which
  changes with the pack. Any pooled figure states "pooled across packs X, Y" in its title.
- **Engine versions:** pool only if the golden report shows identical outputs for those inputs,
  or after replay.
- **Pack status:** `placeholder` and validated packs are never pooled.
- **Crops, nutrients:** never pooled.
- **Blind (golden cases) vs anchored (tool reviews):** never pooled.
- **`ai_reviewed` vs `agronomist_approved` (D4):** never pooled; AI units are excluded from every
  calibration statistic and shown only as diagnostics.
- **Seasons / regions:** stratify; pooled totals are descriptive only.

### 5.3 Replay (the legitimate way to pool across versions)
Re-run the engine under one fixed pack on each unit's `inputs_snapshot` and compare with the
agronomist final. This gives one common reference. Replay is run by `cp-engine` (or by the data
team with the released engine, read-only, offline); results never go to a farmer and are labelled
`replayed under <pack_id> <pack_version>`.

### 5.4 Mid-season pack changes
Every pack bump during S6–S10 splits the season into separate strata and shrinks each. Bumps
mid-season should be limited to bug fixes and agronomist-approved constant replacements; the
calibration review states which units fall before and after.

---

## 6. Proposal workflow

1. **Evidence memo** — `data-scientist` writes `docs/data/proposals/<YYYY-MM-DD>-<constant>.md`
   from the template below. Only for Tier 2 (or a Tier 0 bug, which goes straight to step 5 as a
   bug, not a constant change).
2. **`head-of-data`** reviews method and sample rule; may send back.
3. **CPO (`product-manager`)** reviews scope and timing (season freeze, release gate).
4. **The human agronomist (Farjad Iranmehr unless OQ-04 names someone else) approves or
   rejects.** A `cp-agronomist` (AI) opinion may be attached as context, labelled `ai_reviewed`;
   it never approves (D4) and the constant stays PLACEHOLDER until the human decides. The decision, date, his value and **source** are
   recorded in the memo's Decision section and in the Notion decision log via
   `documentation-manager`. A rejection is recorded with its reason and closes the memo.
   The data team never chooses the final value.
5. **`cp-engine` writes the golden case first** (`engine/tests/golden/`, `status:
   AGRONOMIST_APPROVED`, `reviewer`, `reviewed_on`, `expected.reason`), pinned to the new pack
   version.
6. **Pack version bump** — new file `packs/<id>/v<n+1>.yaml`; the released version is never
   edited. Changed constant gets the approved value, `status: VALIDATED` and its source.
   Existing golden cases stay pinned to their old version as regression checks.
7. **`cp-agronomy-guard` review** — no invented constants, labels and sources correct, N-only
   without soil test, confidence rules, explanations.
8. **Re-run the golden report** and attach it to the memo; then replay the evidence set under
   the new pack (in-sample, labelled) and schedule the prospective check (§4.2) for the next
   calibration reviews.

The data team never edits `engine/` or `packs/` and never commits to them.

### 6.1 Proposal memo template

```markdown
# Proposal: <constant path>  (<pack_id> <pack_version>)

Status: DRAFT | WITH head-of-data | WITH CPO | APPROVED | REJECTED
Author: data-scientist   Date: <YYYY-MM-DD>   Data snapshot: <timestamp, migration level>

## Question
One sentence: what the engine does and how the agronomist differs.

## Proposed change (proposal only — the agronomist decides)
| Constant (path) | Current | Proposed | Evidence | Confidence |
|---|---|---|---|---|
| crops.<crop>.nitrogen.<name> | <CURRENT> (PLACEHOLDER, source: null) | <PROPOSED> ± <CI> | n_plans, n_farms, bias, CI, direction, codes | low / medium / high |

## Evidence
- Stratum: pack_sha256 <...>, engine <...>, season <...>, crop, nutrient, other filters.
- Units: n_plans <n>, n_farms <n>; excluded <n> (by reason).
- Bias <x> kg N/ha [95% CI], MAE <x>, SD <x>, IQR <x>, range <x..y>.
- Direction <k>/<n> (Wilson 95% <a..b>); agreement rate <x> (tolerance <TOLERANCE>).
- Reason codes: <code>: <k> of <n> edits (agronomist-confirmed: <k>).
- Minimum-sample rule (§4.1): MET / NOT MET (which condition).

## Limits
Anchoring, single rater, placeholder reference, farm clustering, in-sample.

## What would change our mind
Prospective check: on the next <n> approved plans under the new pack, expect <metric> within <range>.

## Decision (filled by Farjad Iranmehr's decision, recorded by documentation-manager)
Decision: APPROVED / REJECTED   Date:   Value: <VALUE>   Source: <SOURCE>
Reason:
Follow-up: golden case <id> (cp-engine), pack <id> <new version>, guard review <link>, golden report <link>.
```

---

## 7. S3 plan — calibration baseline from the 5 real wheat cases (due Dec 18)

**Revised after D4 (2026-11-16).** A baseline number is produced **only from human-approved cases**.
If no human agronomist has supplied cases by the S3 cut-off, the S3 output is:
(a) this baseline **method** (items 1–8 below, applied per `recommendation_line` once R2 is
migrated), and (b) the line **"no human-approved cases yet — no baseline produced"**. Reference
cases drafted by `cp-agronomist` from published sources (`external_reference`, `ai_reviewed`) may be
tabulated in a separate appendix "AI review diagnostics" for bug finding only; they are not a
baseline, not agronomist judgement, and not pooled.

The plan below applies when the human cases arrive.

Input: 5 cases from Farjad Iranmehr (agronomist-todo #1), given **blind** (input → his rate,
splits, confidence, reason). Expected mix: ≥ 1 without soil test, ≥ 1 after a legume.

Output: `docs/data/calibration-baseline-S3.md`, delivered to `head-of-data` by Dec 23:

1. **Case table** (5 rows, ids only, no farm names): inputs summary (crop, previous crop, target
   yield, soil test source/method/depth/date), engine `0.2.0` under `placeholder v0` (rate,
   components, bound, splits, confidence, P/K code), his rate/splits/confidence, Δ, relative Δ,
   his reason, proposed primary code (for his confirmation).
2. **Descriptive summary only:** signed Δ per case, mean and median, range, sign count
   (k of 5 up/down). Stated in the file: *n = 5, one agronomist, cases chosen by him, not a random
   sample; a 5/5 sign split cannot reach p < 0.05; no constant is re-estimated.*
3. **Component view per case:** which engine component (demand, soil supply, credit, efficiency,
   bound) the stated reason points at. No "implied constant" is back-solved: with every constant
   PLACEHOLDER, any back-solved value is confounded and would amount to fitting.
4. **Bug and data-capture list:** engine behaviour that contradicts its rules or explanations;
   any input the case needed that the schema/engine cannot hold (manure, measured nitrate,
   P/K numbers, protein target, previous crop not in the pack list).
5. **Confidence comparison:** his confidence vs engine (expected all `low` from C6) — input to
   agronomist-todo #5.
6. **Tolerance proposal request:** the Δ distribution shown to him as context for agronomist-todo
   #10 (he sets the tolerance; we do not).
7. **Questions for the agronomist** (≤ 10), each tied to a case.
8. **Second run** once his first validated pack exists: the same 5 cases replayed under it,
   labelled separately. Caveat stated: if the constants and the cases come from the same person,
   agreement is expected and is not validation.

Not produced in S3: CIs on bias, any proposal table with values, any number for a farmer.

---

## 8. S6–S10 per-sprint calibration review checklist

Run in week 2 of each field-season sprint; output `docs/data/calibration-review-S<n>.md` to
`head-of-data` before the Friday review.

- [ ] Freeze the snapshot: query timestamp, migration level, row counts per table.
- [ ] Split every unit by `reviewer_kind` (D4); statistics below use human-approved units only;
      AI units go to a separate "AI review diagnostics" block (counts, add/remove rates).
- [ ] Apply exclusions (§1.5); list excluded units by reason (counts only).
- [ ] Run Q6 data-quality checks; open tickets for inconsistent splits/totals, changed inputs,
      pack mismatch, duplicate approvals.
- [ ] Tag new edit and reject reasons (Q4, Q5); agronomist confirms tags at the review.
- [ ] Update per-stratum tables (Q2, Q3) **separately per `pack_sha256`**, with n_plans and n_farms.
- [ ] Bias, MAE, spread, agreement, direction, edit rate, reject rate (§4), with intervals only
      where §4 allows.
- [ ] Tier check (§4.1) per stratum; list Tier 1 flags; state "no proposal: below minimum
      sample" where true.
- [ ] Bug list (`ENGINE_BUG` tags, rejects, Q6 findings) to `cp-engine` via `head-of-data`.
- [ ] Questions for the agronomist (≤ 5 per sprint).
- [ ] Status of earlier proposals: decision recorded? prospective check on new plans?
- [ ] Note any pack/engine version change in the sprint and which units fall either side.
- [ ] Hand minutes-per-plan vs edit depth to `data-analyst` for the product metrics review.
- [ ] Standard report to `documentation-manager`.

S11 (season retrospective): full-season tables per stratum, Tier status per constant, schema
gaps still open, recommendation for the 2028 sample size.

---

## 9. Schema gaps (for `head-of-data` → `cto` / `cp-database`; data team does not change schema)

| # | Gap | Impact | Suggested direction (needs ADR) |
|---|---|---|---|
| G1 | ~~No P/K numbers in `result`~~ **SOLVED BY R2**: `recommendation_line` per nutrient with explicit form (§6.4) | Closed once cp-database migrates `recommendation_line` and the engine writes P/K lines; verify before Feb 1 | Track in `calibration-delta-spec.md` (DM-16) |
| G11 | No reviewer kind (D4): cannot separate `ai_reviewed` from `agronomist_approved` | AI sign-offs would contaminate calibration and gates | `review.reviewer_kind` stamped at insert (cp-database, migrations 0011+, REC-D4) |
| G2 | No reason code; two free-text reasons (`recommendation.reason`, `review.reason`) | Tagging is manual and after the fact | Coded `reason_code` on edits/rejects, picked at review time |
| G3 | No test/demo flag on `organisation` | Exclusion by name pattern is fragile | Boolean flag or org kind |
| G4 | `recommendation` has no `field_id` / `soil_test_id`; `crop_plan` is mutable | Farm/region join goes through a mutable row; snapshot soil test has no id | Store field/soil-test ids at insert time |
| G5 | Agronomist rows: splits/total not forced to match rate; inputs/pack not forced equal to parent | Only the rate is reliable | App recomputes, or constraints |
| G6 | No yield / outcome record | Calibration is to judgement, not crop response | Post-harvest yield on `crop_plan` or a new table |
| G7 | No read-only analytics role (`cp_app` can insert) | Analysis runs with write rights | Read-only role with select on the diff view and its tables |
| G8 | No marker for blind vs anchored or golden-derived plans | Risk of double counting and pooling the two | Source flag on crop plan or recommendation |
| G9 | Unclear whether the agronomist sets `final_confidence` | Confidence Δ may be a copy | Decide in the edit UI |
| G10 | No component-level override (which constant he disagrees with) | Rate Δ cannot be attributed | Optional component field in the edit form |
