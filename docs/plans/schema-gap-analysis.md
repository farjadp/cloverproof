# Schema gap analysis — backend plan §6 vs `db/migrations/0001`–`0011`

- Owner: `cp-database`. Date: 2026-11-16. Status: **CPO decisions recorded (2026-11-16)**; the body is updated to match. Still needed: ciso acceptance of ADR 0008 (RLS) before migration 0015.
- Base: branch `webapp-s2-security` @ `2aa26d7` (has 0010, 0011 and the db-privileges ADR, now numbered 0007), plus PR #7 (`webapp-step5-app`, migration 0012) and the site_event migration 0013.
- Inputs: `backend-plan.md` §6, §6.8, §12 (cpo-backend-plan); `backend-plan-reconciliation.md` (wins: D1, D4, R1, R2); `backend-traceability.md` DM-*, RO-*, PM-*, RK-X4/5/7/11; `backend-distribution.md` §1B; ADR 0002, ADR 0006; engine `models.py`, `results.py`.
- Rules this plan keeps: forward-only (never edit 0001–0011), no agronomic constants in SQL, enum labels = engine StrEnum values, immutable tables stay insert-only (grant + trigger).
- Renumbering vs §1B (decided Q7): ADR 0006 = SoilGrids offline cache, ADR 0007 = DB privileges, ADR 0008 = RLS, ADR 0009 = data residency, ADR 0010 = site_event. §1B says "ADR 0006 RLS" and "migrations 0011+": the RLS ADR is **ADR 0008**; migration 0012 is taken by PR #7 (review gate, `admin_event`, `actor_kind`, `platform_role`, `review_kind`), 0013 by site_event, so the gap migrations start at **0014**.

## Decisions (CPO, 2026-11-16)

| Item | Decision | Effect on this plan |
|---|---|---|
| RK-X4 | **A**: derived `recommendation_state` view, no status column | 0019 view; no `status` column |
| RK-X5 | **A**: keep `season` + `crop_plan` ("season plan" in docs/API). **No** unique on `(field_id, season_id)`; add `crop_plan.sequence_no` (double-cropping, e.g. winter wheat then soybeans) | unique dropped; `sequence_no` added in 0017 |
| RK-X7 | **A**: one row per grant, one-time audited revoke, delete forbidden | 0020 as proposed |
| RK-X11 | **A, corrected**: rename `owner`->`org_admin`, `staff`->`advisor`; platform roles on `app_user`; one coordinated S2 release before RLS. A **human** superadmin may approve without agronomist membership: review kind `superadmin_approved` (already on PR #7, migration 0012). Only `agronomist_approved` feeds calibration. AI accounts write `ai_reviewed` only, never approve or edit. Platform `staff` never approves. Platform roles, `actor_kind` and verification are writable only by `cp_admin` (CLI). Accepted consequence: advisors do not see unapproved drafts under RLS | sections 2, 4, 5, 6 |
| `actor_kind` values | PR #7 (0012) implemented `app_user.actor_kind` as `human` or `service` (ciso B1 wording). AI agents are **service accounts**. The CPO wrote `ai`; we keep `human`/`service`. If a separate `ai` value is wanted it is a forward migration | old text "`ai`" now reads `service` |
| Q2 | Backfill `actor_kind='human'` for all existing users (0012 already defaults to `human`). The local demo account is a human test account marked synthetic/demo | no extra migration |
| Q3 | Closed by RK-X5 (double-cropping allowed) | `sequence_no` |
| Q4 | `agronomist_verified_at` is set **only by superadmin via CLI with recorded evidence** (credential type + number e.g. P.Ag./CCA, verifier, date). Nobody is verified until a human agronomist is named. Farjad Iranmehr's account is **superadmin, not agronomist**. Until then real-farm approvals go only through `superadmin_approved` | 0014 adds evidence columns; section 4 |
| Q5 | `farmer.record_kind` default `real`. Only superadmin may change it, and only while the farmer has no recommendations; frozen once a plan exists (no real<->demo). Create a new farmer instead | 0017 trigger |
| Q6 | Soil tests lock once used; correction = new soil-test row | 0018 as proposed |
| Q7 | ADRs: 0006 SoilGrids, 0007 DB privileges, 0008 RLS, 0009 data residency, 0010 site_event | every "ADR 0007 (RLS)" mention now says ADR 0008; the db-privileges ADR is 0007 |
| Q8 | Real farmer data must be stored in Canada (ADR 0009) | gates real data in `farmer.contact` |
| Numbering | 0012 (PR #7) and 0013 (site_event) are taken; gap migrations start at **0014**. Items delivered by 0012 are marked "done in 0012" | sections 1, 4, 6 |

## 1. Entity-by-entity gap table

Status: **same** (nothing to do) · **rename-only** (§6 name differs; we keep the current name and record the mapping) · **missing** · **conflict** (needs a decision). Migration numbers refer to §6 of this document.

| §6 entity | Current table / columns | Status | Proposed migration and content | Risk |
|---|---|---|---|---|
| common `id`, `created_at` | every table | same | — | — |
| common `created_by` | missing on organisation, membership, farmer, farm, field, season, soil_test_value | missing | 0014/0017: add nullable `created_by uuid references app_user` (NULL for old rows; NOT NULL only for new tables) | low |
| common `updated_at` | none | missing | 0017: `updated_at` + shared `set_updated_at()` trigger on mutable tables only | low |
| `profile` | `app_user` (email, display_name, hash, totp, provider, disabled_at, password_change_required) | rename-only + missing cols | Keep `app_user` (D1). **Done in 0012**: `actor_kind` (`human`/`service`, default `human`, existing rows backfilled `human`), `platform_role` (null/`superadmin`), no cp_app write on them. 0014: add `locale`, `unit_system` (`metric`/`imperial`), the `staff` value for `platform_role`, `agronomist_verified_at`, `agronomist_verified_by` plus evidence (`agronomist_credential_type`, `agronomist_credential_no`, `agronomist_verified_on`), all CLI-only (column grants, like 0011) | low: backfill done (Q2) |
| `organisation` | `organisation(name)` | missing cols | 0014: `kind` (`advisory`/`coop`/`dealer`/`lab`/`internal`, default `internal`), `country_code`, `updated_at` | low |
| `org_membership` | `membership(organisation_id, user_id, role owner/agronomist/staff/farmer)` | conflict (roles, RK-X11, decided A) | 0014: rename `owner`->`org_admin`, `staff`->`advisor`; `status` (`active`/`suspended`), `created_by`; 0015: rewrite 0011 web functions for the new labels | **high**: enum rename must ship with app code in one release |
| `farmer` | `farmer` (org-owned, `app_user_id`, display_name, notes) | conflict (ownership HC-08) | 0017: `country_code`, `contact jsonb` (PII; real data only in Canada, ADR 0009), `record_kind` (`real`/`demo`/`reference`, default `real`; superadmin-only change, frozen once the farmer has a recommendation, Q5). Org keeps owning the record in Phase 0–3; `farmer.app_user_id` = §6 `owner_user_id` (rename-only); cross-org access via `access_grant` (0020) | med: default `real` makes every existing row "real"; seed/CLI marks demo rows (the local demo farmer is marked `demo` before the freeze trigger lands) |
| `access_grant` | none | missing (RK-X7, decided A) | 0020: table + one-time revoke trigger + RLS | low (no data) |
| `farm` | `farm(farmer_id, name, country_code, region)` | rename-only (`region` ≈ `region_code`) | 0017: add `region_code` (ISO 3166-2, nullable) next to free-text `region`; `updated_at`, `created_by` | low |
| `field` | `field(farm_id, name)` | missing cols | 0017: `external_ref`, `deleted_at` (soft delete; RLS hides deleted rows from non-platform users), `updated_at`, `created_by` | low |
| `field_geometry_version` | keyed by `season_id`, geom nullable, manual `area_ha` | rename-only + missing | 0017: `valid_from date`, `geom_area_ha` generated from `st_area(geom::geography)/10000` (verify immutability on PostGIS 3.6); keep `area_ha` as the engine value. `season_year` comes from `season.year` (RK-X5) | low |
| `season` | org `season(label, dates)` + `crop_plan(field, season, crop, target_yield, previous_crop, plan_date, soil_test_id)` | conflict (RK-X5, decided A) | 0017: `season.year int`; `crop_plan` gets `sequence_no smallint not null default 1` (double-cropping: winter wheat = 1, soybeans = 2), `variety`, `sowing_date`, `target_yield_unit` (fixed `t/ha`, check), `notes`, `updated_at`. **No** unique on `(field_id, season_id)`; unique `(field_id, season_id, sequence_no)` instead | low: existing rows get `sequence_no = 1` |
| `soil_sample` | `soil_test(field, sample_date, depths, source lab/estimate, lab)` | rename-only + missing | keep `soil_test`. 0018: lock rule (no UPDATE/DELETE once referenced by a recommendation or line). S4: `kit_qr`, `file_ids` via `file_object` | med: lock changes current edit behaviour (accepted, Q6) |
| `soil_measurement` | `soil_test_value(form, nutrient generated, value, unit, method + detail)` | rename-only + missing; conflict on properties | 0018: `canonical_value`, `canonical_unit` (mg/kg, written by app from `units.py`, never computed in SQL), `entry_method` (`manual`/`extracted`/`lab_api`), `confirmed_by`, `confirmed_at`. pH/SOM/`ammonium_acetate` need engine enums first (DM-11) → S3/S4 with cp-engine | med: enum additions must land with engine StrEnum change |
| `soil_estimate` | `soil_test.source = 'estimate'` | conflict (DM-12) | S3 (0022+): separate cache table with provenance; `soil_test.source='estimate'` stays valid for the hand-entered case. Never a source for P/K lines (trigger, §3) | low |
| `recommendation` | `recommendation` (crop_plan_id, parent_id, kind, reason, inputs_snapshot, result, versions, pack sha, confidence, n_rate) | rename-only (`origin`=`kind`, `output`=`result`, `confidence_overall`=`confidence`, `input_snapshot`=`inputs_snapshot`, `season_id`=`crop_plan_id`) + conflict (`status`, RK-X4, decided A) | 0019: `recommendation_state` view gives `status` and `version_no`; no status column. 0018: CHECK-trigger "no lab test ⇒ confidence ≠ high" (hard rule 3) on new rows | low |
| `recommendation_line` | none (`n_rate_kg_ha` generated column only) | missing (R2) | 0018: table, triggers, backfill N lines from existing `result` (§3) | med: backfill must match `n_rate_kg_ha` exactly (test) |
| `review` | `review(decision approve/edit/reject, reason, reviewer_id, minutes_spent, resulting_recommendation_id)` | missing cols + D4 | **Done in 0012**: `review_kind` (`agronomist_approved`/`superadmin_approved`/`ai_reviewed`, set by trigger), `started_at`, gate triggers (`review_check_reviewer`, `recommendation_check_author`), one-final-review constraints, `proof_document_check_approved`, `recommendation_diff` limited to agronomist approvals. 0016: only `finished_at` (check `finished_at >= started_at`; `minutes_spent` stays the stored metric) and the verified-agronomist rule for real farms (section 4). New columns nullable for old rows | med: until a human agronomist is named and verified (Q4), real-farm approvals only via `superadmin_approved` |
| `calibration_delta` (MV) | `recommendation_diff` view (N only, security_invoker) | partial | 0019: `recommendation_line_diff` view (per line); S5: materialized `calibration_delta` + nightly refresh (needs jobs) | low |
| `application_log` | `application_log` (crop_plan, form, product text, planned/actual date+rate) | partial | S10 (later): `recommendation_line_id`, `rate_unit`, `area_ha`, `method`, `operator`, `weather_note`, `corrects_id`, 24 h lock trigger | low now |
| `proof_document` | `proof_document(recommendation_id, sha256, storage_key, created_by)` | rename-only (`storage_path`=`storage_key`, `generated_*`=`created_*`) + missing | 0021: `kind` (`plan`/`plan_with_log`, default `plan`), `template_version` (default `'unknown'` for old rows, required by check for new rows via trigger) | low |
| `share_link` | none | missing | S11 | — |
| `outcome` | none | missing | S17 | — |
| `crop` | `crop_plan.crop` text validated by pack | missing | S4 with pack registry; `gdd_base_c` = PLACEHOLDER + `TODO(agronomist)` | low |
| `country_pack` | packs are files; `pack_sha256` on recommendation | missing | S4: table + partial unique index one `active` per country+crop | low |
| `fertilizer_product` | none | missing | 0022: table, N/P2O5/K2O/S as % of product (label values, not constants), no price/affiliate columns (DBT pins column list, GL-09) | low |
| `feature_flag` | none | missing | S9 | — |
| `file_object` | none | missing | S4 | — |
| `audit_event` | none | partial: `admin_event` **done in 0012** (triggers on membership and app_user) | 0021: generalise to append-only `audit_event` (or extend `admin_event`; decide in 0021) with triggers on review, access_grant, recommendation insert; cp_app INSERT only via SECURITY DEFINER `audit_log()` | med: trigger volume is small; PII in `diff` must be minimised (hash email) |
| `notification` / `data_request` / `weather_daily` | none | missing | S12 / S13 / S4 | — |
| §6.8 RLS | none (ADR 0002 "no RLS"; scoping in app layer + composite FKs) | missing (D1 reverses ADR 0002 on this point) | 0015: helpers + RLS v0 on existing tables; every later table ships with its policies (§5) | **high**: policy recursion and trigger visibility (§5) |

## 2. Decision proposals

### RK-X4 — status on an immutable recommendation
- **A. Derived view (decided A).** `recommendation_state` (security_invoker): `status` = `approved` if an approve review exists; else `rejected` if a reject review exists; else `superseded` if a child row exists (edit) or a later approved root exists on the same crop plan; else `in_review`. `draft` is not used in Phase 0–3 (an engine row enters the queue on insert). Also exposes `version_no` (depth in the parent chain), `approved_by`, `approved_at`, `ai_reviewed_at`. RLS uses a SECURITY DEFINER `recommendation_is_approved(id)` (no policy recursion).
- **B. Append-only `recommendation_status_event` table.** Current status = latest event. Explicit, supports `draft → in_review` submission, but two sources of truth (event vs review) that can disagree.
- **Decided: A (CPO).** Review rows already are the events; one source of truth; nothing to keep in sync. If a "submit for review" step is needed later, it becomes a review-like row, not a status column.

### RK-X5 — season vs crop_plan
- **A. Keep `season` (org planning period) + `crop_plan` (field × season × crop) (recommended).** `crop_plan` is §6 `season` under its current name; add `season.year`, `crop_plan.sequence_no` and the missing crop_plan columns (no unique on `(field_id, season_id)`). Docs and API use "season plan". No data move; FKs from recommendation/application_log stay.
- **B. Reshape to §6.** Rename org `season` → `planning_period`, rename `crop_plan` → `season`, rename FKs (`crop_plan_id` → `season_id`) on four tables. Matches the plan's words but touches every query, the diff view, immutable-table columns, and the 0006/0008 composite FKs.
- **Decided: A (CPO).** Same information, no rename of columns on immutable tables. Double-cropping is allowed (winter wheat then soybeans in one season), so there is **no** unique on `(field_id, season_id)`; `crop_plan.sequence_no` orders the crops of one field in one season, unique on `(field_id, season_id, sequence_no)`.

### RK-X7 — `access_grant` immutable history vs `revoked_at`
- **A. One row per grant, one-time revoke (decided A).** Columns: `farmer_id`, `owner_organisation_id`, `grantee_organisation_id` xor `grantee_user_id`, `scope` (`view`/`edit`), `granted_by`, `granted_at`, `expires_at`, `revoked_at`, `revoked_by`, `revoke_reason`. Trigger allows exactly one UPDATE: `revoked_at/by/reason` from NULL to a value, nothing else; DELETE/TRUNCATE forbidden. Changing scope = revoke + new row. Active = `revoked_at is null and (expires_at is null or expires_at > now())`. Every change also lands in `audit_event`.
- **B. Insert-only event rows** (`action grant|revoke`, revoke references the grant). Purest history, but every RLS check needs "grant exists and no revoke row" — an anti-join inside policies on every farm-data read.
- **Decided: A (CPO).** History is complete (the only mutation is a one-way, audited stamp), RLS predicate stays a simple index lookup. Test: second revoke, un-revoke, scope change, delete all raise.

### RK-X11 — role model mapping (incl. platform roles and D4)
| Plan role | Today | Proposal |
|---|---|---|
| `org_admin` | org `owner` | rename value `owner` → `org_admin` (A) |
| `advisor` | — (org `staff` is closest: enters data) | rename org `staff` → `advisor` (A) |
| `agronomist` | org `agronomist` | same; approval (`agronomist_approved`) needs `actor_kind='human'` (+ verified for real farms, section 4); the only kind that feeds calibration |
| `farmer` | org `farmer` (unused) | same |
| `staff` (platform) | — | `app_user.platform_role='staff'` (value added in 0014; 0012 has null/`superadmin`): read with audit, catalogs; **never approves** |
| `superadmin` (platform) | `platform_role='superadmin'` (**done in 0012**) | a **human** superadmin may approve without agronomist membership: review kind `superadmin_approved` (**done in 0012**, PR #7). Final for status and proof, never calibration. Farjad Iranmehr's account is superadmin, not agronomist (supersedes PM-AP-sa) |
| AI agent (`cp-agronomist`) | `actor_kind='service'` (**done in 0012**) | service account (the CPO's "ai"; a separate `ai` value would be a forward migration); writes `ai_reviewed` only; never approves or edits numbers |
| `lab_partner` | — | later (S25), new enum value then |
- **A. Rename enum values to the plan's names (decided A).** `alter type membership_role rename value 'owner' to 'org_admin'` and `'staff' to 'advisor'` (catalog-only, no row rewrite), plus platform roles on `app_user`. One vocabulary in code, docs, policies. Cost: one coordinated release (app literals, 0011 functions recreated in 0015, tests).
- **B. Keep labels, map in docs.** Add only `advisor` and the platform columns; `owner` means org_admin, org `staff` stays as a third non-approver role. Zero app churn now; permanent confusion between org `staff` and platform `staff` in policies and the permission matrix.
- **Decided: A (CPO)**, shipped as one coordinated S2 release (migration 0014 + app) before RLS policies are written (policies would otherwise hard-code the old labels). Platform roles, `actor_kind` and verification are writable only by `cp_admin` (CLI), never by `cp_app`. Consequence accepted: `advisor` users do not see unapproved drafts (PM-DR-ad) once RLS is on.

## 3. `recommendation_line` design (migration 0018)

```
recommendation_line
  id, organisation_id, recommendation_id          -- FK (organisation_id, recommendation_id)
  nutrient        text  check in ('N','P','K')
  form            nutrient_form  -- N lines: 'N'; P lines: 'P'|'P2O5'; K lines: 'K'|'K2O'; never 'NO3-N'
  rate_kg_ha      numeric null check (rate_kg_ha >= 0)   -- kg/ha of `form`; NULL = no number given
  no_rate_reason  text null      -- required iff rate is NULL, e.g. 'soil_test_required'
  split_no        smallint not null default 0            -- 0 = season total, 1..n = splits
  stage_label, timing_window_start, timing_window_end, timing_basis ('gdd'|'calendar'|'manual')
  product_id (FK added with fertilizer_product), product_rate, product_unit
  explanation     text not null, uses_placeholder boolean not null, confidence confidence_level not null
  soil_test_value_id uuid null   -- evidence for P/K; FK (organisation_id, soil_test_value_id)
  created_by, created_at
  unique (recommendation_id, nutrient, split_no)
```
- **Immutable**: `forbid_change` on UPDATE/DELETE/TRUNCATE; cp_app SELECT, INSERT only. Inserted in the same transaction as its recommendation.
- **Form rule**: CHECK pairs nutrient↔form; unit is always kg/ha of the stated form (column name says so; no free unit). The DB never converts P↔P2O5 (that is `units.py`).
- **P/K only with a lab test containing that nutrient** (trigger `recommendation_line_check_evidence`, BEFORE INSERT): if `nutrient in ('P','K') and rate_kg_ha is not null` then `soil_test_value_id` must be set, the value's `nutrient` must equal the line's, its `soil_test.source` must be `lab`, the test must be the one in the parent recommendation's `inputs_snapshot` (match on `crop_plan.soil_test_id` at insert time and on sample_date/depth in the snapshot), and the value must exist in the snapshot's `values` with the same form and extraction method. Otherwise raise `check_violation`. P/K lines with `rate_kg_ha is null` (the "test recommended" case) are always allowed.
- **No-test confidence cap** (same migration, trigger on `recommendation` and line): no lab soil test in `inputs_snapshot` ⇒ `confidence <> 'high'` (hard rule 3). Engine-side rule stays primary; this is the backstop.
- **Soil-test lock** (decided Q6): `soil_test`/`soil_test_value` rows referenced by a line or by a crop plan with a recommendation can no longer be updated/deleted (trigger) — evidence cannot change under an approved number. Correction = new soil test + new recommendation.
- **Engine vs final**: an agronomist edit is a new `recommendation` row (kind `agronomist`, `parent_id`, `reason`) with its own complete set of lines. Edit lines must keep the engine line's `form` for the same nutrient (trigger), so the diff never compares P with P2O5.
- **Completeness**: DEFERRABLE INITIALLY DEFERRED constraint trigger on `recommendation` insert: at commit, the row has ≥ 1 line and its N total line (`split_no = 0`) equals `n_rate_kg_ha`. The `result` jsonb stays the full document; lines are the typed, queryable projection.
- **Backfill** (in 0018, as cp_migrator): one N total line per existing recommendation from `n_rate_kg_ha` + one per `result.nitrogen.splits[]`; explanation copied from the document.
- **Engine gap**: `results.py` only has `nitrogen: NutrientResult` (`nutrient: Literal["N"]`) and a P/K `Note`. P/K lines only appear once cp-engine adds P/K results (S3); the table is ready before that.
- **`recommendation_diff` changes**: kept unchanged for compatibility (`create or replace view` cannot drop columns). New `recommendation_line_diff` (security_invoker): per final version × `(nutrient, split_no)`, joined to the engine root's line via the same lineage CTE: `form`, `engine_rate_kg_ha`, `final_rate_kg_ha`, `abs_delta`, `rel_delta = abs_delta / nullif(engine_rate, 0)`, `line_change` (`same`/`changed`/`added`/`removed`/`number_added` when engine was NULL), edit reason, approver, minutes. Calibration filter = `review_kind='agronomist_approved'` only; `ai_reviewed` and `superadmin_approved` rows never count (D4, CLAUDE.md rule 11). S5 materializes it as `calibration_delta`.

## 4. D4 in the database

- **Done in 0012 (PR #7)**: `app_user.actor_kind` (`human` | `service`, default `human`; the CPO's "ai" = `service`, a separate `ai` value would be a forward migration), `app_user.platform_role` (null | `superadmin`, human only, `cp_admin` only), `review.review_kind` (`agronomist_approved` | `superadmin_approved` | `ai_reviewed`, set by trigger `review_check_kind`, never by the app), `review.started_at`, gate triggers `review_check_reviewer` and `recommendation_check_author`, `proof_document_check_approved`, `recommendation_diff` restricted to agronomist approvals, `admin_event`. `decision` stays `approve | edit | reject`; an `ai_reviewed` row is the AI's opinion (approve or reject, reason required, never edit), never final, never an approval, never unlocks a proof, never enters calibration. A `superadmin_approved` review by a **human** superadmin who is a member of the organisation is final for status and proof but is **never** calibration data. This replaces the earlier proposal of a new `review_decision` value `ai_reviewed` and of "superadmin approves only with agronomist membership".
- **Still to add (0014, 0016, 0017)**: `agronomist_verified_at/by` plus evidence (credential type, credential number such as P.Ag. or CCA, verifier, date), set **only by superadmin via the CLI** (`cp_admin`); nobody is verified until a human agronomist is named, and Farjad Iranmehr's account is superadmin, not agronomist (Q4). `farmer.record_kind` (`real` | `demo` | `reference`, default `real`); only superadmin may change it and only while the farmer has no recommendation (trigger, 0017); frozen once a plan exists, no real<->demo (Q5); create a new farmer instead. The local demo account is a human test account marked synthetic/demo (Q2).
- **Gate rules (0012 plus 0016)**:
  1. reviewer is an active member of the organisation (done in 0012; a human superadmin counts only as a member of it);
  2. `actor_kind='service'` => `review_kind='ai_reviewed'`, never edit, never an agronomist recommendation (done in 0012);
  3. human, `agronomist` membership => `agronomist_approved` (even if also superadmin) (done in 0012);
  4. human superadmin without agronomist membership => `superadmin_approved` (done in 0012); platform `staff` never approves (0014 adds the value, the gate refuses it);
  5. 0016: `agronomist_approved` on a farmer with `record_kind='real'` additionally requires `agronomist_verified_at is not null`. Until an agronomist is verified, real-farm approvals are only possible as `superadmin_approved`.
- **Tests**: 0012 tests already cover service accounts, superadmin and review_kind (`app/tests/db/`). Still to add: unverified agronomist cannot give `agronomist_approved` on a real farm but can on a demo farm; verified human agronomist can; platform `staff` cannot approve; `agronomist_verified_*`, `platform_role`, `actor_kind` and `farmer.record_kind` are not writable by `cp_app` (column grants test in `test_grants.py`); `record_kind` change refused once the farmer has a recommendation and refused to non-superadmin; calibration views contain `agronomist_approved` rows only.
- Residual risk (T-R2, ADR 0007): a compromised app can still put a real agronomist's id in `reviewer_id`. RLS `WITH CHECK (reviewer_id = cp_current_user_id())` narrows this to "app sets the wrong session user", not solved. MFA for agronomist (R3) is the real control.

## 5. RLS v0 plan (ADR 0008 "Postgres RLS on Railway")

- **Session context** (D1): the app runs, as the first statement of every pooled transaction, `select set_config('app.user_id', $1, true), set_config('app.org_id', $2, true), set_config('app.platform_role', $3, true)` (`is_local=true` = `SET LOCAL`, parameterisable). `PooledDatabase.connection()` already yields one non-autocommit transaction per checkout and commits on exit, so the settings die with the transaction and never leak to the next checkout. Missing settings read as NULL via `current_setting('app.user_id', true)` => zero rows (fail closed); code that commits mid-checkout loses its scope and sees nothing. Pool `reset` callback runs `RESET ALL` as a second line.
- **Helpers** (0015, owned by `cp_migrator`, SECURITY DEFINER, `stable`, `search_path=''`): `cp_user_id()`, `cp_org_id()` (NULL unless the user is an **active member** of that org, checked in the DB, not trusted), `cp_has_role(role)`, `cp_platform_role()` = the DB column `app_user.platform_role` **only if** the setting names the same role (the setting can narrow, never elevate: the app sets it only on `/admin` routes after MFA), `recommendation_is_approved(id)`. SECURITY DEFINER avoids policy recursion (membership <-> membership, recommendation <-> review) and keeps the gate triggers seeing the rows they need. Existing `member_organisation_ids`/`has_org_role` are recreated SECURITY DEFINER for the same reason.
- **Policies** (deny by default, `ENABLE ROW LEVEL SECURITY` on every table):
  - Org-owned farm data (`farmer`, `farm`, `field`, `season`, `field_geometry_version`, `soil_test`, `soil_test_value`, `crop_plan`, `application_log`): SELECT/INSERT/UPDATE/DELETE `to cp_app using (organisation_id = cp_org_id()) with check (same)`; plus SELECT for `cp_platform_role() in ('staff','superadmin')`; `field.deleted_at is not null` hidden from non-platform users. Access-grant reads added in S9 (DM-R1).
  - `recommendation`, `recommendation_line`, `review`, `recommendation_state`/diff views (security_invoker): SELECT if org matches **and** (`recommendation_is_approved(id)` or `cp_has_role('agronomist')` or platform role). Drafts are invisible to `org_admin`, `advisor` and `farmer` (DM-R2, PM-DR-*); the CPO accepted that advisors do not see unapproved drafts. INSERT policies only (no UPDATE/DELETE policies; grants already absent).
  - `proof_document`: SELECT/INSERT in org; approved-only trigger unchanged.
  - Identity: `app_user` own row + rows of users sharing an org; `membership` rows of my orgs; `organisation` my orgs; `user_session` own rows (login runs before a user is known, so login lookup goes through a SECURITY DEFINER `auth_find_user(email)` / `auth_session(token_sha256)` pair; this is the biggest app change).
  - `access_grant`, `audit_event`/`admin_event`, `fertilizer_product`: in their own migrations (audit: SELECT own events / org events for org_admin / all for platform; INSERT only via the SECURITY DEFINER writer).
- **ADR 0007 roles (DB privileges)**: `cp_app` is subject to RLS (not owner, no BYPASSRLS; app startup already refuses superuser/BYPASSRLS/`cp_admin` members). `cp_admin` is a member of `cp_app`, so cp_app policies apply to it too; it gets explicit permissive `to cp_admin using (true) with check (true)` policies on identity tables and SELECT on farm data, in git and tested, **not** the BYPASSRLS attribute (that would live outside git on the login role). `cp_migrator` owns the tables and is exempt. `cp_website`: RLS on `pilot_request` with an INSERT-only policy; that table is owned by the deploy user (0001), so the `ALTER TABLE` runs before `set local role cp_migrator`.
- **FORCE RLS: no (v0).** FORCE would subject the owner `cp_migrator` and therefore every SECURITY DEFINER helper and gate trigger to the policies, recreating the recursion and making backfills in migrations see nothing. `cp_migrator` is NOLOGIN; the guard is a test that no login role owns a table or has BYPASSRLS except the deploy superuser.
- **Scope of protection**: RLS stops a missing `organisation_id` filter or a wrong join (app bug). It does not stop a compromised app, which sets `app.user_id` itself; state this in ADR 0008.
- **Test strategy** (`app/tests/rls/`, DM-R5): fixture creates two orgs and users (org A agronomist human verified, org A org_admin, org A advisor, org B agronomist, platform staff, human superadmin, service account), connects through a test LOGIN role `in role cp_app`, sets context per test. Per policy: one allowed and one denied case (row count 0 for SELECT, `42501` for INSERT/UPDATE `WITH CHECK`). Plus meta-tests: (1) every table in `public` except `schema_migrations`, `spatial_ref_sys` has `relrowsecurity`; (2) every `pg_policies` row is referenced by a test id (registry); (3) no context => every table returns 0 rows; (4) `app.platform_role='superadmin'` without the DB column grants nothing; (5) existing two-org tests (`test_org_scoping.py`) pass unchanged.

## 6. Ordered migrations 0014+ (S2 unless noted)

0012 (PR #7: review gate, `admin_event`, `actor_kind`, `platform_role`, `review_kind`) and 0013 (site_event) are taken. Dropped from this list as **done in 0012**: `ai_reviewed` review kind, `actor_kind`, `platform_role` (null/`superadmin`), `review_kind` and `started_at`, the D4 gate triggers, `admin_event` for membership and app_user.

| # | File | Depends on | Content | Test proves |
|---|---|---|---|---|
| 0014 | `0014_identity_platform_roles.sql` | RK-X11 decided, 0012 | `membership_role` rename `owner`->`org_admin`, `staff`->`advisor` (catalog-only; ships with the app release); `platform_role` gains `staff`; `app_user` locale/unit_system, `agronomist_verified_at/by` + credential evidence; `organisation` kind/country_code/updated_at; `membership` status/created_by; column grants (cp_admin only for platform, actor and verification columns) | enum labels = app/engine constants; old labels gone; cp_app cannot write privilege columns; cp_admin can; app tests green on new labels |
| 0015 | `0015_rls_helpers_and_v0.sql` | 0014, **ADR 0008 accepted (ciso)** | SECURITY DEFINER helpers; recreate `member_organisation_ids`, `has_org_role`, 0011 web functions (new labels); auth lookup functions; enable RLS + policies on all existing tables | section 5 RLS suite allowed/denied; meta-tests; gate triggers still work under RLS |
| 0016 | `0016_review_gate_verified_agronomist.sql` | 0014, 0015 | `review.finished_at`; extend `review_check_reviewer` with the verified-agronomist rule for real farms and the platform `staff` refusal | section 4 tests; existing 0012 and `test_review_gate.py` tests green |
| 0017 | `0017_farm_structure_gaps.sql` | 0015 | created_by/updated_at/deleted_at; farmer country/contact/`record_kind` (+ freeze trigger, superadmin only); farm region_code; field external_ref; `season.year`; crop_plan `sequence_no` + cols (no unique on field+season); fgv valid_from/geom_area_ha | `record_kind` frozen once a recommendation exists; two crop plans per field+season with different `sequence_no` accepted, same `sequence_no` refused; soft-deleted field hidden; geom area generated |
| 0018 | `0018_recommendation_line.sql` | 0016, 0017 | table + RLS, evidence/form/completeness/confidence-cap triggers, soil-test lock, soil_test_value canonical/entry/confirmed cols, backfill | P/K with no test, estimate test, or test without that nutrient refused; NULL-rate P/K allowed; lines immutable; backfill = `n_rate_kg_ha`; locked soil test refuses UPDATE (correction = new row) |
| 0019 | `0019_recommendation_state_and_line_diff.sql` | 0018 | `recommendation_state`, `recommendation_line_diff` (security_invoker); RLS draft rule switched to `recommendation_is_approved` | each status reachable; `ai_reviewed` and `superadmin_approved` never in calibration; drafts hidden from org_admin/advisor |
| 0020 | `0020_access_grant.sql` | 0015 | table, one-time revoke trigger (delete forbidden), RLS (grant owner org reads/writes; grantee sees own grants) | revoke once; no scope change; no delete; cross-org grantee can read its grant only |
| 0021 | `0021_audit_event_and_proof_gaps.sql` | 0014, 0016, 0020 | extend `admin_event`/`audit_event` + writer + triggers (review, grant, role change); `proof_document` kind/template_version | approve/grant/role change each write one event; cp_app cannot UPDATE/DELETE audit; proof new rows need template_version |
| 0022 | `0022_fertilizer_product.sql` | 0015 | catalog (platform staff CRUD draft, everyone R), no price columns | column-list pin (GL-09); RLS read for all, write only platform |
| 0023+ | S3-S17 | engine/pack work | `soil_estimate` (S3), soil properties/`ammonium_acetate` (S3-S4, with engine), `crop`/`country_pack`/`file_object`/`weather_daily` (S4), `feature_flag` (S9), application_log rework (S10), `share_link` (S11), `notification` (S12), `data_request` + erasure design (S13), `outcome` (S17) | each ships with RLS + allowed/denied test |

Every file: `set local role cp_migrator`, explicit grants per role (ADR 0007), runs on local PostGIS (`make db-up`) and, once AR-03 exists, on staging via CI. ADR updates: ADR 0008 (RLS), ADR 0002 addendum (status view, recommendation_line, crop_plan = season plan with `sequence_no`, role names, review kinds).

## 7. Open questions

Decided by the CPO on 2026-11-16 (see the Decisions table): Q1 (RK-X4 A, RK-X5 A, RK-X7 A, RK-X11 A corrected), Q2, Q3, Q4, Q5, Q6, Q7, Q8.

- **Open**: a named human agronomist, with credential type and number, to receive `agronomist_verified_at` (Q4). Until then no verified agronomist exists and real-farm approvals go through `superadmin_approved` only.
- **Open**: ciso acceptance of ADR 0008 (RLS) before migration 0015.
- **Open**: whether a separate `actor_kind='ai'` value is wanted next to `service` (forward migration if yes).
- **Open**: ADR 0009 provider choice (data residency in Canada) before any real farmer data is stored.
