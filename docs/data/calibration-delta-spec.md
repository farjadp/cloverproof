# `calibration_delta` view — specification for cp-database (DM-16)

Owner: `data-scientist` (for `head-of-data`). Consumer: `cto/cp-database` (builds it), `cp-concierge-app` (A2 dashboard, S5), `data-analyst` (M4), `data-scientist` (calibration loop).
Status: DRAFT spec, 2026-11-16; revised 2026-11-16 for the three-value `review_kind` (superadmin decision). Traceability: DM-16 (per line, S2), JB-04 (materialized + nightly, S5), A2, NB-DAT-01, NB-DAT-03.
Decisions applied: reconciliation **D4** (AI reviewer `cp-agronomist` → `ai_reviewed`; human `agronomist` → `agronomist_approved`), the **superadmin decision** (Farjad Iranmehr via CPO, 2026-11-16: a human superadmin may approve plans → `superadmin_approved`) and **R2** (`recommendation_line` replaces P/K columns on `recommendation`).

**Calibration rule:** only `review_kind = 'agronomist_approved'` is calibration evidence (dataset, baseline, constant-change proposals, the 90 % agreement gate). `superadmin_approved` and `ai_reviewed` are two separate diagnostics, each reported on its own, never pooled with each other or with agronomist rows.

> **TARGET SCHEMA (backend-plan §6.4), NOT YET MIGRATED.** Every table and column below is the §6.4 target name. Today's database (migrations 0001–0009) has `recommendation_diff` (N only). Four columns are **proposed by data**, not in §6.4, and are cp-database's to name in migrations 0011+:
> - `review.review_kind` (`agronomist_approved` / `superadmin_approved` / `ai_reviewed`) — the D4 flag, extended to three values (replaces data's earlier `review.reviewer_kind` `ai` / `human`, which is withdrawn). Stamped on **every** immutable `review` row at insert (approve, edit and reject alike; the value names the kind of reviewer, the `decision` column names the outcome), from the reviewer's role at that moment, never read live from the user account, so a later role change cannot rewrite history. A person who holds both roles is stamped `agronomist_approved` (CLAUDE.md rule 8; OQ-D6 resolved).
> - `recommendation.author_kind` (`engine` / `agronomist` / `superadmin` / `ai`) — who set the numbers of each version, stamped at insert. Needed because a final whose numbers a superadmin (or the AI) set or edited is a diagnostic even if an agronomist later approves it (calibration-loop.md, update item 8). §6.4 has `created_by` only, which points at a mutable account.
> - `recommendation_line.nutrient_form` (`elemental` / `oxide`, same enum as §6.3 `soil_measurement.nutrient_form`) — R2 says "explicit form"; §6.4 lists no form column. Without it P vs P2O5 and K vs K2O are ambiguous (CLAUDE.md hard rule 7).
> - `farmer.is_test` — test/demo exclusion (gap SG5). §6.1 has no such flag; `organisation.kind = 'internal'` is not a test flag (the concierge org holding real farms may be internal).

This file sets no agronomic constant, tolerance or threshold. Examples use symbols (`e`, `f`, `a`).

---

## 1. Purpose

Two views, one definition:
- **`signoff_delta`** (analytics only): one row per **recommendation line pair** — what the engine proposed on a line vs what the reviewer finally signed — for every signed-off final of every `review_kind`. Source for the two diagnostics.
- **`calibration_delta`** = `signoff_delta` filtered to **`review_kind = 'agronomist_approved'`** and no non-agronomist edit in the chain. It is the calibration dataset (CLAUDE.md: "engine output AND the agronomist's final numbers + reason ... never lose it") in a form that works for every nutrient, form, split and product — not just the N rate.

## 2. Grain and line matching

**Grain:** one row per (`season_id`, `review_kind`, `nutrient`, `nutrient_form`, `split_no`) for the final signed version of that season, compared with the engine root of its `parent_id` chain. This tuple is unique in `signoff_delta`; in `calibration_delta` `review_kind` is constant, so (`season_id`, `nutrient`, `nutrient_form`, `split_no`) is unique (acceptance test T13).

**Engine root:** walk `parent_id` up from the final version to the row with `parent_id is null` and `origin = 'engine'`. Intermediate versions (`engine → v2 → v3`) are not compared; `chain_depth` records how many edits sit between root and final.

**Line key:** `nutrient` + `nutrient_form` + `split_no`. Engine-root lines are FULL OUTER JOINed to final lines on that key.

| Case | `match_status` | Engine side | Final side | `diff_kg_ha` / `abs_diff_kg_ha` / `rel_diff` |
|---|---|---|---|---|
| Key on both sides | `matched` | set | set | computed (may be 0) |
| Reviewer added a line (new split, new nutrient) | `added` | NULL | set | **NULL** |
| Reviewer removed a line | `removed` | set | NULL | **NULL** |

- **Added / removed lines are their own signal, never a zero delta and never ±the rate.** Counting an added line as `final − 0` would make "the engine forgot a split" look like a large rate error; counting a removed line as 0 would hide it. They are reported as **add rate** and **removal rate** per nutrient (lines added / final lines; lines removed / engine lines), next to the matched-line deltas.
- **Split restructuring** (engine has splits 1–2, reviewer 1–3) shows as two matched rows plus one `added`. Because moving N between splits changes per-split deltas while the total may agree, the analysis also reads the **per-nutrient total** (sum over splits, §6.2), which cp-database may expose as a companion view `calibration_delta_nutrient` (optional, S5).
- **Form change** (engine line P `oxide`, final line P `elemental`) shows as one `removed` + one `added`. This is deliberate: the view never converts units, and comparing an oxide number with an elemental number is wrong (hard rule 7). The data-quality check (§7, DQ3) lists such pairs. Better fix: cp-database / cp-engine store `rate_kg_ha` in **one canonical form per nutrient** (CLAUDE.md: "elemental form tracked explicitly"), and the app converts display units; then form changes cannot occur. Open question OQ-D2.
- **Product change** is not part of the key. A matched line whose `product_id` differs has `product_changed = true`; the nutrient delta is still computed on `rate_kg_ha`. `product_rate_diff` is filled only when product and unit are the same on both sides (otherwise the two product rates are not comparable).
- **Timing change** is not part of the key. `window_start_shift_days` / `window_end_shift_days` = final − engine (days), plus both `timing_basis` values.
- **Uniqueness requirement on the table:** (`recommendation_id`, `nutrient`, `nutrient_form`, `split_no`) must be unique in `recommendation_line`, and `split_no` must be NOT NULL and ≥ 1 (a single application is split 1). FULL JOIN cannot match on `IS NOT DISTINCT FROM`, and a NULL `split_no` would silently break the match.

## 3. Which finals are in the view (filters)

| Filter | Rule | Why |
|---|---|---|
| Signed-off final only | A version with a `review` where `decision = 'approve'` | Drafts, open edits, rejects have no final numbers |
| Agronomist final | `review_kind = 'agronomist_approved'` **and** `recommendation.status = 'approved'` | The only kind that can be calibration evidence |
| Superadmin final | `review_kind = 'superadmin_approved'` and `status in ('in_review','approved')` | Diagnostic only. Whether a superadmin approval moves the version to `approved` is not settled here (CLAUDE.md rule 8 vs the superadmin decision is with the CPO); the filter accepts either so the view does not depend on that outcome |
| AI final | `review_kind = 'ai_reviewed'` and `status in ('in_review','approved')` | D4: an AI sign-off cannot move a real-farm plan to `approved`; the version stays `in_review`. Diagnostic only |
| Superseded chains excluded | `status = 'superseded'` excluded; then one final per (`season_id`, `review_kind`): latest sign-off wins | A re-run or later edit replaces the earlier decision; it must not count twice |
| **Calibration dataset** (`calibration_delta` only) | `review_kind = 'agronomist_approved'` **and** `non_agronomist_edit_in_chain = false` | Only agronomist judgement is evidence. A superadmin approval is not agronomic validation, and a final whose numbers a superadmin or the AI set/edited is a diagnostic even if an agronomist signs it afterwards |
| Rejected excluded | `status = 'rejected'` never qualifies | No final numbers |
| Test / demo data excluded | `farmer.is_test` (proposed, SG5) via season → field → farm → farmer | Seed, rehearsal and QA rows must not enter calibration |

How an AI sign-off is stored (a `review` row with `decision = 'approve'` and `review_kind = 'ai_reviewed'`, leaving `status = 'in_review'`) is this spec's **assumption**; cp-database confirms (OQ-D1). If the AI sign-off becomes its own status or decision value, only the `signoff`/`final` CTEs change.

A version can carry more than one kind of sign-off (e.g. AI reviewed it, a superadmin approved it, then an agronomist approved it). `signoff_delta` then has one row set per `review_kind` for that season; `calibration_delta` keeps only the agronomist set. Consumers never mix the sets.

## 4. Columns

| Column | Type | Meaning |
|---|---|---|
| `season_id` | uuid | Season (§6.2); the evidence unit is one season's final |
| `engine_recommendation_id` | uuid | Engine root of the chain |
| `final_recommendation_id`, `final_version_no` | uuid, int | The signed version |
| `chain_depth` | int | Edits between root and final (0 = signed as the engine produced it) |
| `engine_line_id`, `final_line_id` | uuid | Either is NULL for `added` / `removed` |
| `nutrient`, `nutrient_form`, `split_no` | text, text, int | Line key |
| `match_status` | text | `matched` / `added` / `removed` |
| `review_kind` | text | `agronomist_approved` / `superadmin_approved` / `ai_reviewed` (from the sign-off review row). Replaces the earlier `reviewer_kind` (`ai` / `human`) and `signoff_label` columns, both withdrawn |
| `non_agronomist_edit_in_chain` | bool | `true` if any version between root and final (inclusive) has `author_kind` other than `engine` / `agronomist` |
| `counts_toward_calibration` | bool | `review_kind = 'agronomist_approved' and not non_agronomist_edit_in_chain`. Always `true` in `calibration_delta`; kept so `signoff_delta` consumers can see why a row is diagnostic |
| `signoff_review_id`, `signed_at`, `final_status` | uuid, timestamptz, text | `signed_at` = `review.finished_at` (fallback `created_at`) |
| `engine_rate_kg_ha`, `final_rate_kg_ha` | numeric | kg/ha of `nutrient` in `nutrient_form` |
| `diff_kg_ha` | numeric | `final − engine`; NULL unless `matched`. Positive = reviewer wants more |
| `abs_diff_kg_ha` | numeric | `|diff|`; NULL unless `matched` |
| `rel_diff` | numeric | `diff / engine` as a fraction; **NULL when the engine value is 0** or the line is unmatched |
| `rel_diff_status` | text | `ok` / `engine_zero` / `unmatched` — explains every NULL in `rel_diff` |
| `engine_product_id`, `final_product_id`, `product_changed` | uuid, uuid, bool | `product_changed` NULL unless `matched` |
| `engine_product_rate`, `final_product_rate`, `engine_product_unit`, `final_product_unit`, `product_rate_diff` | | `product_rate_diff` only for same product + same unit |
| `window_start_shift_days`, `window_end_shift_days`, `engine_timing_basis`, `final_timing_basis` | int, int, text, text | Timing changes |
| `engine_line_confidence`, `final_line_confidence`, `engine_confidence_overall` | text | Confidence (hard rule 2) |
| `engine_version`, `pack_id`, `pack_version` | text | From the engine root — the stratum identity |
| `pack_changed`, `inputs_changed` | bool | Final differs from root in pack or input snapshot → excluded from statistics (calibration-loop §1.5) |
| `crop_code` | text | From the root's `input_snapshot` (fallback `season.crop_code`, which is mutable) |
| `soil_source` | text | `lab` / `estimate` / `none`, from the root snapshot |
| `soil_test_method` | text | Extraction method(s) of the soil measurement for this line's nutrient, from the root snapshot; `n/a` for N, `none` if absent |

**Relative-diff rule (divide by zero):** `rel_diff = (final − engine) / engine` only when `engine > 0`. When `engine = 0`: `rel_diff` is NULL and `rel_diff_status = 'engine_zero'`; the absolute diff still carries the signal. Summaries report `n_with_relative` beside every relative statistic. No epsilon, no capping.

**Deliberately not in the view:** free-text `reason` (P2, may name a farm; join on `final_recommendation_id` when tagging), reviewer identity, farmer/farm/field names, geometry, minutes (M1 has its own query).

**Snapshot paths are assumptions.** `input_snapshot -> 'crop_code'`, `-> 'soil' ->> 'source'` and `-> 'soil' -> 'measurements'[*] {property, extraction_method}` are placeholders until cp-engine fixes the §6.4 `input_snapshot` contract (OQ-D4). They live in the final SELECT only.

## 5. Reference SQL (target schema §6.4, not yet migrated)

First version (two-value `reviewer_kind`) checked 2026-11-16 on a throwaway local PostGIS 17 container: the view built; assertions for T2–T11, T13, T14 and the grant part of T17 passed. This three-kind revision was re-checked 2026-11-16 on a fresh throwaway PostGIS 17 container with a minimal stub (the tables and columns the views read, plus `review.review_kind` and `recommendation.author_kind`) and 8 fictional seasons: both views build; T11, T12, T18 and T19 behave as specified (calibration rows only for agronomist-only seasons; zero rows with another `review_kind`; superadmin- and AI-edited chains excluded); the container was removed. T1–T10, T13–T17 were not re-run on this revision. It did **not** run against Railway or the current migrations.

```sql
-- TARGET SCHEMA (backend-plan §6.4 + D4 flag), NOT YET MIGRATED.
-- Proposed names used here (cp-database decides the final ones, migrations 0011+):
--   review.review_kind ('agronomist_approved' | 'superadmin_approved' | 'ai_reviewed')
--                                                 D4 + superadmin decision, stamped on the immutable review row
--   recommendation.author_kind ('engine' | 'agronomist' | 'superadmin' | 'ai')  stamped at insert
--   recommendation_line.nutrient_form             R2 "explicit form" ('elemental' | 'oxide', as §6.3)
--   farmer.is_test                                SG5 test/demo flag
create view signoff_delta
with (security_invoker = true) as
with recursive
excluded_season as (                                   -- test / demo data (SG5)
  select s.id as season_id
  from season s
  join field  fl on fl.id = s.field_id
  join farm   fm on fm.id = fl.farm_id
  join farmer fr on fr.id = fm.farmer_id
  where fr.is_test
),
chain as (                                             -- every version with its engine root
  select r.id as rec_id, r.id as root_id, 0 as depth,
         false as non_agronomist_edit                  -- root is engine output
  from recommendation r
  where r.parent_id is null and r.origin = 'engine'
  union all
  select c.id, ch.root_id, ch.depth + 1,
         ch.non_agronomist_edit
           or c.author_kind is distinct from 'agronomist'   -- NULL author counts as non-agronomist
  from chain ch
  join recommendation c on c.parent_id = ch.rec_id
),
signoff as (                                           -- latest sign-off per version and review kind
  select distinct on (rv.recommendation_id, rv.review_kind)
         rv.recommendation_id, rv.id as review_id, rv.review_kind,
         coalesce(rv.finished_at, rv.created_at) as signed_at
  from review rv
  where rv.decision = 'approve'
  order by rv.recommendation_id, rv.review_kind,
           coalesce(rv.finished_at, rv.created_at) desc, rv.id desc
),
final as (                                             -- one final version per season and review kind
  select distinct on (r.season_id, so.review_kind)
         ch.root_id, ch.rec_id as final_id, ch.depth as chain_depth,
         ch.non_agronomist_edit as non_agronomist_edit_in_chain,
         r.season_id, r.version_no as final_version_no, r.status as final_status,
         r.pack_id as final_pack_id, r.pack_version as final_pack_version,
         r.input_snapshot as final_input_snapshot,
         so.review_id, so.review_kind, so.signed_at
  from chain ch
  join recommendation r on r.id = ch.rec_id
  join signoff so       on so.recommendation_id = r.id
  where r.season_id not in (select season_id from excluded_season)
    and (   (so.review_kind = 'agronomist_approved' and r.status = 'approved')
         or (so.review_kind in ('superadmin_approved', 'ai_reviewed')
             and r.status in ('in_review', 'approved')))
  order by r.season_id, so.review_kind, so.signed_at desc, r.id desc
),
pairs as (                                             -- engine-root lines FULL JOIN final lines
  select f.*, x.*
  from final f
  cross join lateral (
    select el.id as engine_line_id, fl.id as final_line_id,
           coalesce(el.nutrient, fl.nutrient)           as nutrient,
           coalesce(el.nutrient_form, fl.nutrient_form) as nutrient_form,
           coalesce(el.split_no, fl.split_no)           as split_no,
           el.rate_kg_ha   as engine_rate_kg_ha,   fl.rate_kg_ha   as final_rate_kg_ha,
           el.product_id   as engine_product_id,   fl.product_id   as final_product_id,
           el.product_rate as engine_product_rate, fl.product_rate as final_product_rate,
           el.product_unit as engine_product_unit, fl.product_unit as final_product_unit,
           el.timing_window_start as engine_window_start, fl.timing_window_start as final_window_start,
           el.timing_window_end   as engine_window_end,   fl.timing_window_end   as final_window_end,
           el.timing_basis as engine_timing_basis, fl.timing_basis as final_timing_basis,
           el.confidence   as engine_line_confidence, fl.confidence as final_line_confidence
    from (select * from recommendation_line where recommendation_id = f.root_id)  el
    full join
         (select * from recommendation_line where recommendation_id = f.final_id) fl
      on  fl.nutrient      = el.nutrient
      and fl.nutrient_form = el.nutrient_form
      and fl.split_no      = el.split_no
  ) x
)
select
  -- keys
  p.season_id, p.root_id as engine_recommendation_id, p.final_id as final_recommendation_id,
  p.final_version_no, p.chain_depth, p.engine_line_id, p.final_line_id,
  p.nutrient, p.nutrient_form, p.split_no,
  case when p.engine_line_id is null then 'added'
       when p.final_line_id  is null then 'removed'
       else 'matched' end                                         as match_status,
  -- review kind (D4 + superadmin decision)
  p.review_kind,
  p.non_agronomist_edit_in_chain,
  (p.review_kind = 'agronomist_approved' and not p.non_agronomist_edit_in_chain) as counts_toward_calibration,
  p.review_id as signoff_review_id, p.signed_at, p.final_status,
  -- rates (kg/ha of nutrient in nutrient_form); diff = final - engine
  p.engine_rate_kg_ha, p.final_rate_kg_ha,
  p.final_rate_kg_ha - p.engine_rate_kg_ha                         as diff_kg_ha,
  abs(p.final_rate_kg_ha - p.engine_rate_kg_ha)                    as abs_diff_kg_ha,
  case when p.engine_rate_kg_ha > 0
       then (p.final_rate_kg_ha - p.engine_rate_kg_ha) / p.engine_rate_kg_ha end as rel_diff,
  case when p.engine_line_id is null or p.final_line_id is null then 'unmatched'
       when p.engine_rate_kg_ha = 0 then 'engine_zero'
       else 'ok' end                                               as rel_diff_status,
  -- product and timing
  p.engine_product_id, p.final_product_id,
  case when p.engine_line_id is not null and p.final_line_id is not null
       then p.engine_product_id is distinct from p.final_product_id end as product_changed,
  p.engine_product_rate, p.final_product_rate, p.engine_product_unit, p.final_product_unit,
  case when p.engine_product_id = p.final_product_id and p.engine_product_unit = p.final_product_unit
       then p.final_product_rate - p.engine_product_rate end       as product_rate_diff,
  p.final_window_start - p.engine_window_start                     as window_start_shift_days,
  p.final_window_end   - p.engine_window_end                       as window_end_shift_days,
  p.engine_timing_basis, p.final_timing_basis,
  -- confidence
  p.engine_line_confidence, p.final_line_confidence,
  e.confidence_overall                                             as engine_confidence_overall,
  -- provenance (strata)
  e.engine_version, e.pack_id, e.pack_version,
  ((p.final_pack_id, p.final_pack_version) is distinct from (e.pack_id, e.pack_version)) as pack_changed,
  (p.final_input_snapshot is distinct from e.input_snapshot)       as inputs_changed,
  coalesce(e.input_snapshot ->> 'crop_code', s.crop_code)          as crop_code,
  case when jsonb_typeof(e.input_snapshot -> 'soil') = 'object'
       then e.input_snapshot -> 'soil' ->> 'source' else 'none' end as soil_source,
  case when p.nutrient = 'N' then 'n/a'
       else coalesce((select string_agg(distinct m ->> 'extraction_method', '+')
                        from jsonb_array_elements(
                               case when jsonb_typeof(e.input_snapshot #> '{soil,measurements}') = 'array'
                                    then e.input_snapshot #> '{soil,measurements}' else '[]'::jsonb end) m
                       where lower(m ->> 'property') = lower(p.nutrient)), 'none') end as soil_test_method
from pairs p
join recommendation e on e.id = p.root_id
join season s         on s.id = p.season_id;

-- The calibration dataset: agronomist approvals only, no superadmin/AI-set numbers in the chain.
create view calibration_delta
with (security_invoker = true) as
select *
from signoff_delta
where review_kind = 'agronomist_approved'
  and not non_agronomist_edit_in_chain;
```

**Grants (verified):** the view is `security_invoker`, so a reader such as `cp_analyst` needs SELECT on `recommendation`, `recommendation_line`, `review`, `season`, `field`, `farm` and — because of the test-flag join — `farmer`. Grant `farmer` **column-level** (`grant select (id, is_test) on farmer`), so the analyst cannot read `display_name` (verified: the view works and `select display_name from farmer` is denied). RLS on the base tables (D1) applies to the querying user.

## 6. How consumers use it (D4 rules)

### 6.1 Segment rule
**Calibration statistics, the agreement gate, the baseline and any constant-change proposal read `calibration_delta` only** (= `review_kind = 'agronomist_approved'`, no non-agronomist edit in the chain). The two diagnostics read `signoff_delta`, one `review_kind` per query, each in its own block:
- "Superadmin approval diagnostics (not agronomist approval)": `review_kind = 'superadmin_approved'`.
- "AI review diagnostics (not agronomist approval)": `review_kind = 'ai_reviewed'`.
- Agronomist-approved finals excluded because a superadmin or the AI set/edited numbers in the chain (`review_kind = 'agronomist_approved' and non_agronomist_edit_in_chain`) are counted and listed under the superadmin (or AI) diagnostic, never in calibration.

Diagnostic rows never enter an agronomist denominator, and the two diagnostics are never added to each other.

### 6.2 Per-nutrient summary (companion, optional)
```sql
-- per final, per nutrient and form: totals over splits (matched + added + removed)
-- calibration: from calibration_delta; a diagnostic: from signoff_delta where review_kind = :'review_kind'
select season_id, review_kind, nutrient, nutrient_form, pack_id, pack_version,
       sum(engine_rate_kg_ha)                                         as engine_total_kg_ha,
       sum(final_rate_kg_ha)                                          as final_total_kg_ha,
       coalesce(sum(final_rate_kg_ha),0) - coalesce(sum(engine_rate_kg_ha),0) as total_diff_kg_ha,
       count(*) filter (where match_status = 'added')                 as n_lines_added,
       count(*) filter (where match_status = 'removed')               as n_lines_removed,
       bool_or(product_changed)                                       as any_product_changed
from calibration_delta
group by 1, 2, 3, 4, 5, 6;
```
At nutrient-total level a missing side **is** 0 kg/ha (the plan applies none of that nutrient), so `coalesce(…, 0)` is correct here and only here. A nutrient that exists on one side only is still flagged (`n_lines_added` / `n_lines_removed`) and reported separately.

### 6.3 The 90 % agreement gate is not defined yet
The reconciliation (D4) refers to "the 90 % agreement gate"; neither it nor the backend plan (v1.0) defines it, and the current roadmap does not either: agreement per line or per nutrient total? per nutrient tolerance in kg/ha or relative? do added/removed lines count as disagreement? which population (agronomist-approved only — `superadmin_approved` and `ai_reviewed` never count)? The tolerance is agronomist-todo #10. **This spec does not invent it.** The view supplies `abs_diff_kg_ha`, `rel_diff`, `match_status` so any definition can be computed once decided (OQ-D3).

## 7. Acceptance tests cp-database should write (DBT, local PostGIS)

| # | Fixture | Expected |
|---|---|---|
| T1 | Engine root signed without edit | All rows `matched`, `diff_kg_ha = 0`, `chain_depth = 0`; `rel_diff = 0` where engine > 0 |
| T2 | Edit raises split 1 of N by `a` | That row `diff_kg_ha = a`, sign = final − engine, `rel_diff = a / e`; other rows unchanged |
| T3 | Edit adds split 3 | Row `added`, engine side NULL, `diff`/`abs`/`rel` NULL, `rel_diff_status = 'unmatched'` |
| T4 | Edit removes the P line | Row `removed`, final side NULL, diffs NULL |
| T5 | Engine line with rate 0, final 0 or `f` | `rel_diff` NULL, `rel_diff_status = 'engine_zero'`, `abs_diff` = `|f|` |
| T6 | Same nutrient/split, different `product_id` | `matched`, `product_changed = true`, `product_rate_diff` NULL |
| T7 | Engine P `oxide`, final P `elemental` | One `removed` + one `added`; DQ3 lists the pair (or the insert fails if a canonical-form constraint is adopted) |
| T8 | Chain engine → v2 → v3 approved | Rows compare v3 with the root; `chain_depth = 2`; v2 absent |
| T9 | Two engine roots in one season, older `superseded` | Only the latest signed final appears |
| T10 | Rejected only / in_review without sign-off | No rows |
| T11 | Farmer with `is_test = true` | No rows in either view |
| T12 | AI sign-off, then superadmin approval, then agronomist approval of the same version | `signoff_delta`: three row sets, `ai_reviewed` / `superadmin_approved` (`counts_toward_calibration = false`) and `agronomist_approved` (`true`); `calibration_delta`: the agronomist set only |
| T13 | Any fixture | `signoff_delta`: (`season_id`, `review_kind`, `nutrient`, `nutrient_form`, `split_no`) unique; `calibration_delta`: (`season_id`, `nutrient`, `nutrient_form`, `split_no`) unique; rows per final = |engine keys ∪ final keys| |
| T14 | Duplicate line key; `split_no` 0 or NULL | Insert rejected by constraint |
| T15 | Change the reviewer's role (e.g. remove superadmin, add agronomist) after a review | View output unchanged (`review_kind` and `author_kind` are stamped at insert) |
| T16 | `agronomist_approved` review inserted by an AI account, or by a human without the agronomist role, on a real farm | Rejected by the REC-D4 trigger (cp-database's test; listed here because the view relies on it) |
| T17 | Role `cp_analyst` | Can read the view with the grants in §5; denied on `farmer.display_name`. RLS: a second user without access sees no rows of another org (two-user test, §6.8) |
| **T18** | **Exclusion of non-agronomist sign-offs.** Seasons whose only sign-off is `superadmin_approved` (status `approved` and, separately, `in_review`) and seasons whose only sign-off is `ai_reviewed` | `calibration_delta` has **no** row for those seasons and `select count(*) from calibration_delta where review_kind <> 'agronomist_approved'` = 0; `signoff_delta` has their rows with `counts_toward_calibration = false` |
| **T19** | **Superadmin-set numbers.** Chain engine → v2 (`author_kind = 'superadmin'`) → `agronomist_approved`; same with v2 by `ai` | No row in `calibration_delta`; `signoff_delta` row has `review_kind = 'agronomist_approved'`, `non_agronomist_edit_in_chain = true`, `counts_toward_calibration = false` |

Data-quality checks run before every calibration review (not view tests):
- **DQ1** `inputs_changed or pack_changed` rows — excluded from statistics, counted.
- **DQ2** Per final, sum of split rates vs any stored nutrient total in `output` (if the output keeps one) — mismatch = gap SG6.
- **DQ3** Same `season_id`, `review_kind`, `nutrient`, `split_no` with one `removed` and one `added` in different forms — form change, see §2.

## 8. Phasing

| Part | Sprint | Owner | Trace |
|---|---|---|---|
| `recommendation_line` (+ `nutrient_form`, unique key), `review.review_kind`, `recommendation.author_kind`, `farmer.is_test` | S2 (migrations 0011+) | cp-database | R2, REC-D4, SG5 |
| Plain views `signoff_delta` + `calibration_delta` (this spec), tests T1–T19 | S2 | cp-database (+ data-engineer review) | DM-16 |
| **Materialized view + nightly `refresh_calibration_view` job** | **S5** | cp-database | JB-04 |
| A2 dashboard and `GET /metrics/calibration` on top | S5 | cp-concierge-app + data-analyst | A2, AD-13 |

Materialized-view notes for S5: `REFRESH MATERIALIZED VIEW CONCURRENTLY` needs a unique index — use (`season_id`, `review_kind`, `nutrient`, `nutrient_form`, `split_no`) on `signoff_delta`; `calibration_delta` stays a plain filter over it. A materialized view has **no RLS and no `security_invoker`**: it must live in a restricted schema (e.g. `analytics`) readable only by `cp_analyst` / staff roles, never by `authenticated`. Until S5 the plain view is fast enough (tens of rows in 2027; the fixture query ran in about 11 ms locally).

The old `recommendation_diff` (0009, N only) stays until the app writes `recommendation_line`; then it is retired by a forward-only migration (cp-database decides). Data docs switch from `recommendation_diff` to `calibration_delta` at that point.

## 9. Open questions

| # | Question | Owner |
|---|---|---|
| OQ-D1 | How is an AI sign-off stored: `review(decision='approve', review_kind='ai_reviewed')` with status left `in_review` (assumed here), or a separate status/decision value? | cp-database (REC-D4) |
| OQ-D2 | `recommendation_line.nutrient_form`: add the column, or store `rate_kg_ha` in one canonical form per nutrient (preferred by data)? | cp-database + cp-engine |
| OQ-D3 | Define the 90 % agreement gate: unit (line / nutrient total), tolerance per nutrient (agronomist-todo #10), treatment of added/removed lines, population (`agronomist_approved` only) | human agronomist via CPO |
| OQ-D4 | `input_snapshot` contract for crop, soil source and per-nutrient extraction method | cp-engine |
| OQ-D5 | Test flag on `farmer` or `organisation` (SG5)? §6.1 has no org link on `farmer` except via `access_grant` | cp-database |
| OQ-D6 | RESOLVED by CLAUDE.md rule 8 (PR #26): a `superadmin_approved` approval is a real approval (`status = 'approved'`, may reach the farmer); `superadmin_approved` means a human superadmin **without** the agronomist role, so a person holding both is stamped `agronomist_approved`. Still excluded from calibration; reported as its own diagnostic | — |
| OQ-04 | Who is the human agronomist (is it Farjad Iranmehr)? Until named, `calibration_delta` has no rows for real farms | Farjad Iranmehr |
