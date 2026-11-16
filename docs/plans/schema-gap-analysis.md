# Schema gap analysis — backend plan §6 vs `db/migrations/0001`–`0011`

- Owner: `cp-database`. Date: 2026-11-16. Status: **proposal, needs CPO decision by Nov 27** (RK-X4, RK-X5, RK-X7, RK-X11).
- Base: branch `webapp-s2-security` @ `2aa26d7` (has 0010, 0011 and ADR 0006 db-privileges).
- Inputs: `backend-plan.md` §6, §6.8, §12 (cpo-backend-plan); `backend-plan-reconciliation.md` (wins: D1, D4, R1, R2); `backend-traceability.md` DM-*, RO-*, PM-*, RK-X4/5/7/11; `backend-distribution.md` §1B; ADR 0002, ADR 0006; engine `models.py`, `results.py`.
- Rules this plan keeps: forward-only (never edit 0001–0011), no agronomic constants in SQL, enum labels = engine StrEnum values, immutable tables stay insert-only (grant + trigger).
- Renumbering vs §1B: §1B says "ADR 0006 RLS" and "migrations 0011+". Both numbers are taken, so the RLS ADR is **ADR 0007** and migrations start at **0012**. Note: `origin/data/open-data` also has `docs/adr/0006-soilgrids-offline-cache.md`, so ADR 0006 is already a collision on two branches (see open question Q7).

## 1. Entity-by-entity gap table

Status: **same** (nothing to do) · **rename-only** (§6 name differs; we keep the current name and record the mapping) · **missing** · **conflict** (needs a decision). Migration numbers refer to §6 of this document.

| §6 entity | Current table / columns | Status | Proposed migration and content | Risk |
|---|---|---|---|---|
| common `id`, `created_at` | every table | same | — | — |
| common `created_by` | missing on organisation, membership, farmer, farm, field, season, soil_test_value | missing | 0013/0016: add nullable `created_by uuid references app_user` (NULL for old rows; NOT NULL only for new tables) | low |
| common `updated_at` | none | missing | 0016: `updated_at` + shared `set_updated_at()` trigger on mutable tables only | low |
| `profile` | `app_user` (email, display_name, hash, totp, provider, disabled_at, password_change_required) | rename-only + missing cols | 0013: keep `app_user` (D1). Add `locale`, `unit_system` (`metric`/`imperial`), `platform_role` (`none`/`staff`/`superadmin`), `actor_kind` (`human`/`ai`), `agronomist_verified_at`, `agronomist_verified_by`. cp_app gets **no** UPDATE on the last four (column grants, like 0011) | med: backfill of `actor_kind` for existing rows (Q2) |
| `organisation` | `organisation(name)` | missing cols | 0013: `kind` (`advisory`/`coop`/`dealer`/`lab`/`internal`, default `internal`), `country_code`, `updated_at` | low |
| `org_membership` | `membership(organisation_id, user_id, role owner/agronomist/staff/farmer)` | conflict (roles, RK-X11) | 0012: enum changes per RK-X11; 0013: `status` (`active`/`suspended`), `created_by`; 0014: rewrite 0011 web functions for the new labels | **high**: enum rename must ship with app code in one release |
| `farmer` | `farmer` (org-owned, `app_user_id`, display_name, notes) | conflict (ownership HC-08) | 0016: `country_code`, `contact jsonb` (PII), `record_kind` (`real`/`demo`/`reference`, default `real`). Org keeps owning the record in Phase 0–3; `farmer.app_user_id` = §6 `owner_user_id` (rename-only); cross-org access via `access_grant` (0019) | med: default `real` makes every existing row "real" → seed/CLI must mark demo rows |
| `access_grant` | none | missing (RK-X7) | 0019: table + one-time revoke trigger + RLS | low (no data) |
| `farm` | `farm(farmer_id, name, country_code, region)` | rename-only (`region` ≈ `region_code`) | 0016: add `region_code` (ISO 3166-2, nullable) next to free-text `region`; `updated_at`, `created_by` | low |
| `field` | `field(farm_id, name)` | missing cols | 0016: `external_ref`, `deleted_at` (soft delete; RLS hides deleted rows from non-platform users), `updated_at`, `created_by` | low |
| `field_geometry_version` | keyed by `season_id`, geom nullable, manual `area_ha` | rename-only + missing | 0016: `valid_from date`, `geom_area_ha` generated from `st_area(geom::geography)/10000` (verify immutability on PostGIS 3.6); keep `area_ha` as the engine value. `season_year` comes from `season.year` (RK-X5) | low |
| `season` | org `season(label, dates)` + `crop_plan(field, season, crop, target_yield, previous_crop, plan_date, soil_test_id)` | conflict (RK-X5) | 0016: `season.year int`; `crop_plan` gets `variety`, `sowing_date`, `target_yield_unit` (fixed `t/ha`, check), `notes`, `updated_at`; unique `(field_id, season_id)` | med: unique fails if duplicate crop plans exist on a DB → pre-check query in the migration raises with a list |
| `soil_sample` | `soil_test(field, sample_date, depths, source lab/estimate, lab)` | rename-only + missing | keep `soil_test`. 0017: lock rule (no UPDATE/DELETE once referenced by a recommendation or line). S4: `kit_qr`, `file_ids` via `file_object` | med: lock changes current edit behaviour |
| `soil_measurement` | `soil_test_value(form, nutrient generated, value, unit, method + detail)` | rename-only + missing; conflict on properties | 0017: `canonical_value`, `canonical_unit` (mg/kg, written by app from `units.py`, never computed in SQL), `entry_method` (`manual`/`extracted`/`lab_api`), `confirmed_by`, `confirmed_at`. pH/SOM/`ammonium_acetate` need engine enums first (DM-11) → S3/S4 with cp-engine | med: enum additions must land with engine StrEnum change |
| `soil_estimate` | `soil_test.source = 'estimate'` | conflict (DM-12) | S3 (0022+): separate cache table with provenance; `soil_test.source='estimate'` stays valid for the hand-entered case. Never a source for P/K lines (trigger, §3) | low |
| `recommendation` | `recommendation` (crop_plan_id, parent_id, kind, reason, inputs_snapshot, result, versions, pack sha, confidence, n_rate) | rename-only (`origin`=`kind`, `output`=`result`, `confidence_overall`=`confidence`, `input_snapshot`=`inputs_snapshot`, `season_id`=`crop_plan_id`) + conflict (`status`, RK-X4) | 0018: `recommendation_state` view gives `status` and `version_no`; no status column. 0017: CHECK-trigger "no lab test ⇒ confidence ≠ high" (hard rule 3) on new rows | low |
| `recommendation_line` | none (`n_rate_kg_ha` generated column only) | missing (R2) | 0017: table, triggers, backfill N lines from existing `result` (§3) | med: backfill must match `n_rate_kg_ha` exactly (test) |
| `review` | `review(decision approve/edit/reject, reason, reviewer_id, minutes_spent, resulting_recommendation_id)` | missing cols + D4 | 0012: enum `ai_reviewed`; 0015: `started_at`, `finished_at` (check `finished_at >= started_at`; `minutes_spent` stays the stored metric), `reviewer_kind` snapshot, new gate trigger (§4). New columns nullable for old rows (immutable table: `ADD COLUMN` with no/constant default does not fire UPDATE triggers) | med: gate change blocks approvals until an agronomist is verified (intended, D4) |
| `calibration_delta` (MV) | `recommendation_diff` view (N only, security_invoker) | partial | 0018: `recommendation_line_diff` view (per line); S5: materialized `calibration_delta` + nightly refresh (needs jobs) | low |
| `application_log` | `application_log` (crop_plan, form, product text, planned/actual date+rate) | partial | S10 (later): `recommendation_line_id`, `rate_unit`, `area_ha`, `method`, `operator`, `weather_note`, `corrects_id`, 24 h lock trigger | low now |
| `proof_document` | `proof_document(recommendation_id, sha256, storage_key, created_by)` | rename-only (`storage_path`=`storage_key`, `generated_*`=`created_*`) + missing | 0020: `kind` (`plan`/`plan_with_log`, default `plan`), `template_version` (default `'unknown'` for old rows, required by check for new rows via trigger) | low |
| `share_link` | none | missing | S11 | — |
| `outcome` | none | missing | S17 | — |
| `crop` | `crop_plan.crop` text validated by pack | missing | S4 with pack registry; `gdd_base_c` = PLACEHOLDER + `TODO(agronomist)` | low |
| `country_pack` | packs are files; `pack_sha256` on recommendation | missing | S4: table + partial unique index one `active` per country+crop | low |
| `fertilizer_product` | none | missing | 0021: table, N/P2O5/K2O/S as % of product (label values, not constants), no price/affiliate columns (DBT pins column list, GL-09) | low |
| `feature_flag` | none | missing | S9 | — |
| `file_object` | none | missing | S4 | — |
| `audit_event` | none | missing | 0020: append-only table, triggers on membership, app_user privilege columns, review, access_grant, recommendation insert; cp_app INSERT only via SECURITY DEFINER `audit_log()` | med: trigger volume is small; PII in `diff` must be minimised (hash email) |
| `notification` / `data_request` / `weather_daily` | none | missing | S12 / S13 / S4 | — |
| §6.8 RLS | none (ADR 0002 "no RLS"; scoping in app layer + composite FKs) | missing (D1 reverses ADR 0002 on this point) | 0014: helpers + RLS v0 on existing tables; every later table ships with its policies (§5) | **high**: policy recursion and trigger visibility (§5) |

## 2. Decision proposals

### RK-X4 — status on an immutable recommendation
- **A. Derived view (recommended).** `recommendation_state` (security_invoker): `status` = `approved` if an approve review exists; else `rejected` if a reject review exists; else `superseded` if a child row exists (edit) or a later approved root exists on the same crop plan; else `in_review`. `draft` is not used in Phase 0–3 (an engine row enters the queue on insert). Also exposes `version_no` (depth in the parent chain), `approved_by`, `approved_at`, `ai_reviewed_at`. RLS uses a SECURITY DEFINER `recommendation_is_approved(id)` (no policy recursion).
- **B. Append-only `recommendation_status_event` table.** Current status = latest event. Explicit, supports `draft → in_review` submission, but two sources of truth (event vs review) that can disagree.
- Recommendation: **A**. Review rows already are the events; one source of truth; nothing to keep in sync. If a "submit for review" step is needed later, it becomes a review-like row, not a status column.

### RK-X5 — season vs crop_plan
- **A. Keep `season` (org planning period) + `crop_plan` (field × season × crop) (recommended).** `crop_plan` is §6 `season` under its current name; add `season.year`, the missing crop_plan columns and unique `(field_id, season_id)`. Docs and API use "season plan". No data move; FKs from recommendation/application_log stay.
- **B. Reshape to §6.** Rename org `season` → `planning_period`, rename `crop_plan` → `season`, rename FKs (`crop_plan_id` → `season_id`) on four tables. Matches the plan's words but touches every query, the diff view, immutable-table columns, and the 0006/0008 composite FKs.
- Recommendation: **A**. Same information, no rename of columns on immutable tables. Open: does one field ever carry two crops in one season (cover/double crop)? If yes, drop the unique and add `crop_plan.sequence_no` instead (Q3).

### RK-X7 — `access_grant` immutable history vs `revoked_at`
- **A. One row per grant, one-time revoke (recommended).** Columns: `farmer_id`, `owner_organisation_id`, `grantee_organisation_id` xor `grantee_user_id`, `scope` (`view`/`edit`), `granted_by`, `granted_at`, `expires_at`, `revoked_at`, `revoked_by`, `revoke_reason`. Trigger allows exactly one UPDATE: `revoked_at/by/reason` from NULL to a value, nothing else; DELETE/TRUNCATE forbidden. Changing scope = revoke + new row. Active = `revoked_at is null and (expires_at is null or expires_at > now())`. Every change also lands in `audit_event`.
- **B. Insert-only event rows** (`action grant|revoke`, revoke references the grant). Purest history, but every RLS check needs "grant exists and no revoke row" — an anti-join inside policies on every farm-data read.
- Recommendation: **A**. History is complete (the only mutation is a one-way, audited stamp), RLS predicate stays a simple index lookup. Test: second revoke, un-revoke, scope change, delete all raise.

### RK-X11 — role model mapping (incl. platform roles and D4)
| Plan role | Today | Proposal |
|---|---|---|
| `org_admin` | org `owner` | rename value `owner` → `org_admin` (A) |
| `advisor` | — (org `staff` is closest: enters data) | rename org `staff` → `advisor` (A) |
| `agronomist` | org `agronomist` | same; approval also needs `actor_kind='human'` (+ verified for real farms, §4) |
| `farmer` | org `farmer` (unused) | same |
| `staff` (platform) | — | `app_user.platform_role='staff'`: read with audit, catalogs; **never approves** |
| `superadmin` (platform) | — | `app_user.platform_role='superadmin'`; approves **only** if it also holds a human, verified `agronomist` membership in that org (supersedes PM-AP-sa) |
| AI agent (`cp-agronomist`) | — | `app_user.actor_kind='ai'`; may write `ai_reviewed` only; never approve/edit numbers |
| `lab_partner` | — | later (S25), new enum value then |
- **A. Rename enum values to the plan's names (recommended).** `alter type membership_role rename value 'owner' to 'org_admin'` and `'staff' to 'advisor'` (catalog-only, no row rewrite), plus platform roles on `app_user`. One vocabulary in code, docs, policies. Cost: one coordinated release (app literals, 0011 functions recreated in 0014, tests).
- **B. Keep labels, map in docs.** Add only `advisor` and the platform columns; `owner` means org_admin, org `staff` stays as a third non-approver role. Zero app churn now; permanent confusion between org `staff` and platform `staff` in policies and the permission matrix.
- Recommendation: **A**, shipped in S2 before RLS policies are written (policies would otherwise hard-code the old labels). Platform roles and `actor_kind`/verification are writable only by `cp_admin` (CLI), never by `cp_app`. Consequence to confirm: renamed `advisor` users lose sight of unapproved drafts (PM-DR-ad ✗) once RLS is on.

## 3. `recommendation_line` design (migration 0017)

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
- **Soil-test lock**: `soil_test`/`soil_test_value` rows referenced by a line or by a crop plan with a recommendation can no longer be updated/deleted (trigger) — evidence cannot change under an approved number. Correction = new soil test + new recommendation.
- **Engine vs final**: an agronomist edit is a new `recommendation` row (kind `agronomist`, `parent_id`, `reason`) with its own complete set of lines. Edit lines must keep the engine line's `form` for the same nutrient (trigger), so the diff never compares P with P2O5.
- **Completeness**: DEFERRABLE INITIALLY DEFERRED constraint trigger on `recommendation` insert: at commit, the row has ≥ 1 line and its N total line (`split_no = 0`) equals `n_rate_kg_ha`. The `result` jsonb stays the full document; lines are the typed, queryable projection.
- **Backfill** (in 0017, as cp_migrator): one N total line per existing recommendation from `n_rate_kg_ha` + one per `result.nitrogen.splits[]`; explanation copied from the document.
- **Engine gap**: `results.py` only has `nitrogen: NutrientResult` (`nutrient: Literal["N"]`) and a P/K `Note`. P/K lines only appear once cp-engine adds P/K results (S3); the table is ready before that.
- **`recommendation_diff` changes**: kept unchanged for compatibility (`create or replace view` cannot drop columns). New `recommendation_line_diff` (security_invoker): per final version × `(nutrient, split_no)`, joined to the engine root's line via the same lineage CTE: `form`, `engine_rate_kg_ha`, `final_rate_kg_ha`, `abs_delta`, `rel_delta = abs_delta / nullif(engine_rate, 0)`, `line_change` (`same`/`changed`/`added`/`removed`/`number_added` when engine was NULL), edit reason, approver, minutes. Calibration filter = approved by a **human** agronomist (`reviewer_kind='human'`); `ai_reviewed` rows never count (D4). S5 materializes it as `calibration_delta`.

## 4. D4 in the database

- **Columns**: `app_user.actor_kind ('human'|'ai') not null`; `app_user.agronomist_verified_at/by` (human agronomist named and credentials checked, Q4; set by CLI/`cp_admin` only); `farmer.record_kind ('real'|'demo'|'reference')` default `real`; `review.reviewer_kind` snapshot written by trigger from `app_user` (never by the app).
- **Decision label**: `review_decision` gains `ai_reviewed` (0012, own file: a value added by `ALTER TYPE … ADD VALUE` cannot be used in the same transaction, and the runner runs one transaction per file). `ai_reviewed` never satisfies `proof_document_check_approved`, never sets status `approved`, never enters calibration.
- **Gate trigger** (`review_check_reviewer` replaced in 0015, SECURITY DEFINER, `search_path=''`):
  1. reviewer is an active member of the organisation (unchanged);
  2. `actor_kind='ai'` ⇒ decision must be `ai_reviewed` (no approve/edit/reject);
  3. `decision='ai_reviewed'` ⇒ `actor_kind='ai'`;
  4. `decision='approve'` ⇒ human **and** `agronomist` membership in the org; platform role is irrelevant (a superadmin without that membership is refused);
  5. `decision='approve'` on a farmer with `record_kind='real'` ⇒ additionally `agronomist_verified_at is not null`.
  `recommendation_check_author` gets rule 2 too: an AI user cannot insert a `kind='agronomist'` row.
- **Tests** (`app/tests/db/test_review_gate_d4.py`, all as `cp_app`): `test_ai_cannot_approve_real_farm`, `test_ai_cannot_approve_demo_farm`, `test_ai_cannot_edit_or_reject`, `test_ai_can_write_ai_reviewed`, `test_human_cannot_write_ai_reviewed`, `test_ai_reviewed_is_not_approved` (state view `in_review`, proof insert refused, absent from line diff calibration), `test_superadmin_without_agronomist_membership_cannot_approve`, `test_unverified_agronomist_cannot_approve_real_farm_but_can_demo`, `test_verified_human_agronomist_approves_real_farm`, `test_ai_cannot_insert_agronomist_recommendation`, `test_reviewer_kind_snapshot_matches_user`; in `test_grants.py`: `cp_app` has no UPDATE on `actor_kind`, `platform_role`, `agronomist_verified_*` or `farmer.record_kind` (CLI only, Q5).
- Residual risk (T-R2, ADR 0006): a compromised app can still put a real agronomist's id in `reviewer_id`. RLS `WITH CHECK (reviewer_id = cp_current_user_id())` narrows this to "app sets the wrong session user", not solved. MFA for agronomist (R3) is the real control.

## 5. RLS v0 plan (ADR 0007 "Postgres RLS on Railway")

- **Session context** (D1): the app runs, as the first statement of every pooled transaction, `select set_config('app.user_id', $1, true), set_config('app.org_id', $2, true), set_config('app.platform_role', $3, true)` (`is_local=true` ≡ `SET LOCAL`, parameterisable). `PooledDatabase.connection()` already yields one non-autocommit transaction per checkout and commits on exit, so the settings die with the transaction and never leak to the next checkout. Missing settings read as NULL via `current_setting('app.user_id', true)` ⇒ zero rows (fail closed); code that commits mid-checkout loses its scope and sees nothing. Pool `reset` callback runs `RESET ALL` as a second line.
- **Helpers** (0014, owned by `cp_migrator`, SECURITY DEFINER, `stable`, `search_path=''`): `cp_user_id()`, `cp_org_id()` (NULL unless the user is an **active member** of that org — checked in the DB, not trusted), `cp_has_role(role)`, `cp_platform_role()` = the DB column `app_user.platform_role` **only if** the setting names the same role (the setting can narrow, never elevate: the app sets it only on `/admin` routes after MFA), `recommendation_is_approved(id)`. SECURITY DEFINER avoids policy recursion (membership ↔ membership, recommendation ↔ review) and keeps the 0007 gate triggers seeing the rows they need. Existing `member_organisation_ids`/`has_org_role` are recreated SECURITY DEFINER for the same reason.
- **Policies** (deny by default, `ENABLE ROW LEVEL SECURITY` on every table):
  - Org-owned farm data (`farmer`, `farm`, `field`, `season`, `field_geometry_version`, `soil_test`, `soil_test_value`, `crop_plan`, `application_log`): SELECT/INSERT/UPDATE/DELETE `to cp_app using (organisation_id = cp_org_id()) with check (same)`; plus SELECT for `cp_platform_role() in ('staff','superadmin')`; `field.deleted_at is not null` hidden from non-platform users. Access-grant reads added in S9 (DM-R1).
  - `recommendation`, `recommendation_line`, `review`, `recommendation_state`/diff views (security_invoker): SELECT if org matches **and** (`recommendation_is_approved(id)` or `cp_has_role('agronomist')` or platform role) — drafts invisible to org_admin/advisor/farmer (DM-R2, PM-DR-*). INSERT policies only (no UPDATE/DELETE policies; grants already absent).
  - `proof_document`: SELECT/INSERT in org; approved-only trigger unchanged.
  - Identity: `app_user` own row + rows of users sharing an org; `membership` rows of my orgs; `organisation` my orgs; `user_session` own rows (login runs before a user is known → login lookup goes through a SECURITY DEFINER `auth_find_user(email)` / `auth_session(token_sha256)` pair; this is the biggest app change).
  - `access_grant`, `audit_event`, `fertilizer_product`: in their own migrations (audit: SELECT own events / org events for org_admin / all for platform; INSERT only via the SECURITY DEFINER writer).
- **ADR 0006 roles**: `cp_app` is subject to RLS (not owner, no BYPASSRLS; app startup already refuses superuser/BYPASSRLS/`cp_admin` members). `cp_admin` is a member of `cp_app`, so cp_app policies apply to it too; it gets explicit permissive `to cp_admin using (true) with check (true)` policies on identity tables and SELECT on farm data, in git and tested — **not** the BYPASSRLS attribute (that would live outside git on the login role). `cp_migrator` owns the tables and is exempt. `cp_website`: RLS on `pilot_request` with an INSERT-only policy; that table is owned by the deploy user (0001), so the `ALTER TABLE` runs before `set local role cp_migrator`.
- **FORCE RLS: no (v0).** FORCE would subject the owner `cp_migrator` and therefore every SECURITY DEFINER helper and gate trigger to the policies, recreating the recursion and making backfills in migrations see nothing. `cp_migrator` is NOLOGIN; the guard is a test that no login role owns a table or has BYPASSRLS except the deploy superuser.
- **Scope of protection**: RLS stops a missing `organisation_id` filter or a wrong join (app bug). It does not stop a compromised app, which sets `app.user_id` itself — state this in ADR 0007.
- **Test strategy** (`app/tests/rls/`, DM-R5): fixture creates two orgs and users (org A agronomist human verified, org A org_admin, org A advisor, org B agronomist, platform staff, superadmin, AI agronomist), connects through a test LOGIN role `in role cp_app`, sets context per test. Per policy: one allowed and one denied case (row count 0 for SELECT, `42501` for INSERT/UPDATE `WITH CHECK`). Plus meta-tests: (1) every table in `public` except `schema_migrations`, `spatial_ref_sys` has `relrowsecurity`; (2) every `pg_policies` row is referenced by a test id (registry); (3) no context ⇒ every table returns 0 rows; (4) `app.platform_role='superadmin'` without the DB column grants nothing; (5) existing two-org tests (`test_org_scoping.py`) pass unchanged.

## 6. Ordered migrations 0012+ (S2 unless noted)

| # | File | Depends on | Content | Test proves |
|---|---|---|---|---|
| 0012 | `0012_enum_values.sql` | RK-X11, D4 decided | `review_decision` + `ai_reviewed`; `membership_role` rename `owner→org_admin`, `staff→advisor` (if A) | enum labels = app/engine constants; old labels gone; app tests green on new labels |
| 0013 | `0013_identity_platform.sql` | 0012 | `app_user` locale/unit_system/platform_role/actor_kind/verified_*; `organisation` kind/country_code/updated_at; `membership` status/created_by; column grants | cp_app cannot write privilege columns; cp_admin can; backfill `actor_kind` correct |
| 0014 | `0014_rls_helpers_and_v0.sql` | 0013, **ADR 0007 accepted (ciso)** | SECURITY DEFINER helpers; recreate `member_organisation_ids`, `has_org_role`, 0011 web functions (new labels); auth lookup functions; enable RLS + policies on all existing tables | §5 RLS suite allowed/denied; meta-tests; gate triggers still work under RLS |
| 0015 | `0015_review_gate_d4.sql` | 0012–0014 | `review` started_at/finished_at/reviewer_kind; replace `review_check_reviewer`, `recommendation_check_author` | §4 D4 tests; existing `test_review_gate.py` green |
| 0016 | `0016_farm_structure_gaps.sql` | 0014 | created_by/updated_at/deleted_at; farmer country/contact/record_kind; farm region_code; field external_ref; season.year; crop_plan cols + unique; fgv valid_from/geom_area_ha | uniqueness pre-check; soft-deleted field hidden; geom area generated |
| 0017 | `0017_recommendation_line.sql` | 0015, 0016 | table + RLS, evidence/form/completeness/confidence-cap triggers, soil-test lock, soil_test_value canonical/entry/confirmed cols, backfill | P/K with no test, estimate test, or test without that nutrient refused; NULL-rate P/K allowed; lines immutable; backfill = `n_rate_kg_ha`; locked soil test refuses UPDATE |
| 0018 | `0018_recommendation_state_and_line_diff.sql` | 0017 | `recommendation_state`, `recommendation_line_diff` (security_invoker); RLS draft rule switched to `recommendation_is_approved` | each status reachable; ai_reviewed ≠ approved; diff excludes AI; drafts hidden from org_admin/advisor |
| 0019 | `0019_access_grant.sql` | 0014 | table, one-time revoke trigger, RLS (grant owner org reads/writes; grantee sees own grants) | revoke once; no scope change; no delete; cross-org grantee can read its grant only |
| 0020 | `0020_audit_event_and_proof_gaps.sql` | 0013, 0015, 0019 | `audit_event` append-only + writer + triggers; `proof_document` kind/template_version | approve/grant/role change each write one event; cp_app cannot UPDATE/DELETE audit; proof new rows need template_version |
| 0021 | `0021_fertilizer_product.sql` | 0014 | catalog (platform staff CRUD draft, everyone R), no price columns | column-list pin (GL-09); RLS read for all, write only platform |
| 0022+ | S3–S17 | engine/pack work | `soil_estimate` (S3), soil properties/`ammonium_acetate` (S3–S4, with engine), `crop`/`country_pack`/`file_object`/`weather_daily` (S4), `feature_flag` (S9), application_log rework (S10), `share_link` (S11), `notification` (S12), `data_request` + erasure design (S13), `outcome` (S17) | each ships with RLS + allowed/denied test |

Every file: `set local role cp_migrator`, explicit grants per role (ADR 0006), runs on local PostGIS (`make db-up`) and, once AR-03 exists, on staging via CI. ADR updates: ADR 0007 (RLS), ADR 0002 addendum (status view, recommendation_line, crop_plan = season, role names).

## 7. Open questions for the CPO / Farjad Iranmehr
- **Q1** Accept RK-X4 A, RK-X5 A, RK-X7 A, RK-X11 A (enum rename in one coordinated S2 release)?
- **Q2** Backfill `actor_kind='human'` for every existing `app_user`? Is any existing account used by an AI agent?
- **Q3** Can one field carry two crops in one season (cover/double crop)? Decides the crop_plan unique key.
- **Q4** CLAUDE.md names Farjad Iranmehr as the agronomist; the reconciliation says a human agronomist is still to be named (Q4 there). Who gets `agronomist_verified_at`, on what evidence, and before S5?
- **Q5** `farmer.record_kind` default `real` (fail safe: unverified approvals blocked everywhere until marked `demo`). Who may change it, and is `demo→real` allowed after plans exist?
- **Q6** Soil-test lock after use (0017) changes today's editing: OK for the concierge flow?
- **Q7** ADR numbering: `0006-db-privileges` (webapp-s2-security) and `0006-soilgrids-offline-cache` (data/open-data) collide; release-manager must renumber one before merge, and ADR 0007 (RLS) must be reserved now.
- **Q8** Data residency (R4/Q6) is still open; RLS does not change it, but it gates real farmer data in `farmer.contact`.
