# Data dictionary (migrations 0001–0009)

Owner of this document: data-governance-specialist, for `head-of-data`. Status: DRAFT for review.
Source of truth is `db/migrations/`; this file describes it and never changes it. Classes (P0–P3) are defined in `docs/data/pii-and-retention.md`.

**Data ownership principle.** Farmers own their farm data (fields, soil tests, applications). CloverProof processes it on the farmer's behalf to produce plans. "Owner" below means the *business owner accountable for the table's quality*, not who owns the farm data. All farm-data tables are processed by CloverProof as a service provider to the farmer.

Conventions: every table has `id uuid` PK (`gen_random_uuid()`); every org-owned table has `organisation_id` and composite FKs `(organisation_id, id)`; timestamps are `timestamptz` (UTC). Business owners: `head-of-data` (HoD), `cto`, `ciso`, `cso`/`coo` (website, outreach), Farjad Iranmehr (agronomist = AGR). Mutability: **immutable** (trigger blocks UPDATE/DELETE/TRUNCATE, `cp_app` has SELECT+INSERT only), **insert-only** (no update path in practice, enforced by grants/convention), **mutable**.

Canonical units: nutrient application and N rate in **kg/ha** (of the stated form); soil concentrations in **mg/kg** (`ppm` accepted as recorded, numerically equal for soil mg/kg); yield t/ha; area ha; depth cm; time minutes.

## Table index

| Table / view | Migration | Mutability | Class (max) | Business owner |
|---|---|---|---|---|
| pilot_request | 0001 | mutable (status, deleted_at) | P2 | coo / cso (website) |
| organisation | 0003 | mutable | P1 | HoD |
| app_user | 0003 | mutable | P2 (secrets: P3) | ciso |
| user_session | 0003 | mutable | P2 (token hash) | ciso |
| membership | 0003 | mutable | P1 | ciso |
| farmer | 0004 | mutable | P2 | HoD |
| farm | 0004 | mutable | P2 | HoD |
| field | 0004 | mutable | P2 | HoD |
| season | 0004 | mutable | P1 | HoD |
| field_geometry_version | 0004 | mutable | P3 (geom) | HoD |
| soil_test | 0005 | mutable | P2 | AGR |
| soil_test_value | 0005 | mutable | P2 | AGR |
| crop_plan | 0006 | mutable (draft inputs) | P2 | AGR |
| recommendation | 0006 | **immutable** | P2 | AGR |
| review | 0007 | **immutable** | P2 | AGR |
| application_log | 0008 | mutable | P2 | AGR |
| proof_document | 0008 | **immutable** (+ object in bucket) | P2 | AGR |
| recommendation_diff (view) | 0009 | read-only view | P2 (P1 if `*_result` excluded) | HoD |

Not in the DB: `schema_migrations` (runner bookkeeping, P0). Proof PDF bytes live in the private Railway bucket (ADR 0005 B1).

---

## pilot_request (0001)
Purpose: pilot sign-up from the public website, written only by the website server. Not linked to any other table. Mutable: `status`, `deleted_at` only by convention. Owner: coo/cso with `cp-website`. Raw personal data from a prospect, not yet a farmer record.

| Column | Type | Meaning / unit | Null | PII | Rules |
|---|---|---|---|---|---|
| id | uuid | PK | no | P1 | |
| created_at | timestamptz | submission time | no | P1 | default now() |
| locale | text | website locale, 2–5 chars (e.g. `en`) | no | P1 | length 2–5 |
| full_name | text | name as typed | no | P2 | 1–200 chars |
| email | text | contact email | no | P2 | ≤320, regex; index on lower(email) |
| country | text | free-text country as typed | no | P1 | 1–100; NOT validated ISO code |
| farm_size_text | text | farm size WITH unit as typed (ha/acres/etc.) | no | P2 | free text, NOT a number; never use as engine input |
| main_crop | text | free-text crop | no | P1 | 1–100 |
| notes | text | free text | yes | P2 (may hold anything) | ≤2000; treat as personal |
| consent_at | timestamptz | when consent was given | no | P1 | evidence; must be ≤ created_at + skew |
| consent_text | text | exact wording shown | no | P1 | evidence; never edit |
| status | text | `new` / `contacted` / `accepted` / `declined` | no | P1 | check constraint |
| deleted_at | timestamptz | deletion request received; row purged later | yes | P1 | NULL = live. A later job is NOT yet built |

## organisation (0003)
Purpose: tenant (CloverProof itself in the pilot). Mutable. Owner HoD.

| Column | Type | Meaning | Null | PII |
|---|---|---|---|---|
| id | uuid | PK | no | P1 |
| name | text | org name, 1–200 non-blank | no | P1 |
| created_at | timestamptz | | no | P1 |

## app_user (0003)
Purpose: internal tool users (agronomist, staff; later farmer logins). Mutable. Owner ciso. Created by CLI only.

| Column | Type | Meaning | Null | PII | Rules |
|---|---|---|---|---|---|
| id | uuid | PK; referenced by every `created_by` / `reviewer_id` | no | P1 | |
| email | text | login/contact email | no | P2 | regex, unique on lower(email) |
| display_name | text | person name | no | P2 | 1–200 non-blank |
| password_hash | text | argon2id PHC string; NULL = no local login | yes | P3 | must start `$argon2id$` |
| totp_secret | text | TOTP secret, app must encrypt before insert | yes | P3 | no plaintext; no DB check possible, add app test |
| auth_provider | text | `local` / `oidc` | no | P1 | |
| external_subject | text | IdP subject (Phase 4) | yes | P2 | required when `oidc`; unique with provider |
| disabled_at | timestamptz | account disabled | yes | P1 | disabled users have no organisations |
| created_at | timestamptz | | no | P1 | |

## user_session (0003)
Purpose: server-side sessions. Mutable. Owner ciso. FK `user_id` ON DELETE CASCADE.

| Column | Type | Meaning | Null | PII |
|---|---|---|---|---|
| id | uuid | PK | no | P1 |
| user_id | uuid | → app_user | no | P1 |
| token_sha256 | char(64) | SHA-256 hex of cookie token; token never stored | no | P3 |
| created_at / last_seen_at | timestamptz | | no | P1 |
| expires_at | timestamptz | absolute expiry, > created_at | no | P1 |
| revoked_at | timestamptz | | yes | P1 |

## membership (0003)
Purpose: user role in an organisation. Enum `membership_role`: owner, agronomist, staff, farmer. Mutable. FKs cascade on org/user delete. Unique (organisation_id, user_id, role).

| Column | Type | Meaning | Null | PII |
|---|---|---|---|---|
| id | uuid | PK | no | P1 |
| organisation_id, user_id | uuid | FKs | no | P1 |
| role | membership_role | gates approval (agronomist) | no | P1 |
| created_at | timestamptz | | no | P1 |

Functions: `member_organisation_ids(user_id)`, `has_org_role(user_id, org, role)`, `forbid_change()` (immutability trigger).

## farmer (0004)
Purpose: client record of an organisation. The farmer owns the farm data; the organisation processes it. Mutable. Owner HoD.

| Column | Type | Meaning | Null | PII | Rules |
|---|---|---|---|---|---|
| id | uuid | PK | no | P1 | |
| organisation_id | uuid | → organisation | no | P1 | |
| display_name | text | farmer / business name | no | P2 | 1–200 |
| app_user_id | uuid | login link (Phase 4) | yes | P1 | |
| notes | text | free notes | yes | P2 (free text) | ≤4000 |
| created_at | timestamptz | | no | P1 | |

No phone, email or address columns exist (by design, not yet). If added they are P2.

## farm (0004)

| Column | Type | Meaning | Null | PII | Rules |
|---|---|---|---|---|---|
| id, organisation_id, farmer_id | uuid | PK / composite FK to farmer | no | P1 | |
| name | text | farm name (often a family/place name) | no | P2 | 1–200 |
| country_code | char(2) | ISO 3166-1 alpha-2, upper case; selects country pack | yes | P1 | `^[A-Z]{2}$` |
| region | text | admin region, free text | yes | P2 (coarse location) | ≤200 |
| created_at | timestamptz | | no | P1 | |

## field (0004)

| Column | Type | Meaning | Null | PII |
|---|---|---|---|---|
| id, organisation_id, farm_id | uuid | PK / composite FK to farm | no | P1 |
| name | text | field name, 1–200 | no | P2 |
| created_at | timestamptz | | no | P1 |

## season (0004)

| Column | Type | Meaning | Null | PII | Rules |
|---|---|---|---|---|---|
| id, organisation_id | uuid | | no | P1 | |
| label | text | e.g. `2027`, unique per org | no | P1 | 1–50 |
| starts_on, ends_on | date | period | yes | P1 | ends_on > starts_on if both set |
| created_at | timestamptz | | no | P1 | |

## field_geometry_version (0004)
Purpose: one field boundary / area per field per season. Mutable (the data is a farmer-owned location record). Owner HoD.

| Column | Type | Meaning / unit | Null | PII | Rules |
|---|---|---|---|---|---|
| id, organisation_id, field_id, season_id | uuid | | no | P1 | unique (field_id, season_id) |
| geom | geometry(MultiPolygon, 4326) | WGS84 boundary | yes | **P3** | valid and non-empty; NULL until Phase 4 |
| area_ha | numeric | hectares; engine input | no | P2 | > 0; if `geometry`, should match ST_Area (not enforced) |
| area_source | text | `manual` / `geometry` | no | P1 | `geometry` requires geom |
| created_by | uuid | → app_user | no | P1 | |
| created_at | timestamptz | | no | P1 | |

## soil_test (0005)
Purpose: one sampling event per field. Mutable (but see gap: edits after a recommendation used it). Owner AGR.

| Column | Type | Meaning / unit | Null | PII | Rules |
|---|---|---|---|---|---|
| id, organisation_id, field_id | uuid | | no | P1 | |
| sample_date | date | date sampled (not report date) | no | P2 | required; QC: not in future, not > 5 years old (engine/pack decides use) |
| depth_top_cm | numeric | cm, ≥ 0 | no | P2 | |
| depth_bottom_cm | numeric | cm, > top | no | P2 | |
| source | soil_test_source | `lab` / `estimate` | no | P1 | `estimate` must not carry `lab` (QC, not enforced) |
| lab | text | lab name | yes | P1 | 1–200; QC: required when source=lab (not enforced) |
| created_by, created_at | | | no | P1 | |

## soil_test_value (0005)
Purpose: one measured nutrient value; extraction method belongs to the value. Mutable. FK cascade from soil_test.

| Column | Type | Meaning / unit | Null | PII | Rules |
|---|---|---|---|---|---|
| id, organisation_id, soil_test_id | uuid | | no | P1 | |
| form | nutrient_form | `N`, `NO3-N`, `P`, `P2O5`, `K`, `K2O` — elemental vs oxide explicit | no | P2 | |
| nutrient | text (generated, stored) | N / P / K derived from form | no | P1 | never entered |
| value | numeric | measured value in `unit` | no | P2 | ≥ 0; QC plausibility ranges are agronomist-owned |
| unit | concentration_unit | `mg/kg` or `ppm` | no | P1 | canonical mg/kg; ppm treated as equal, normalise on read |
| extraction_method | extraction_method | `olsen`, `bray-1`, `mehlich-3`, `other` | no | P1 | |
| extraction_method_detail | text | free text | yes | P1 | required when `other` |
| created_at | timestamptz | | no | P1 | |

Unique (soil_test_id, nutrient): one form per nutrient per test. QC: P and K values need a method other than defaults; N from `NO3-N` uses no P/K method semantics (gap: enum has no "n/a").

## crop_plan (0006)
Purpose: editable draft inputs for a field and season. Mutable. Owner AGR.

| Column | Type | Meaning / unit | Null | PII | Rules |
|---|---|---|---|---|---|
| id, organisation_id, field_id, season_id | uuid | | no | P1 | |
| crop | text | pack crop id e.g. `wheat` | no | P1 | `^[a-z][a-z0-9_-]*$`; validated by engine |
| target_yield_t_ha | numeric | t/ha | no | P2 | > 0; QC upper bound per crop is agronomist-owned |
| previous_crop | text | lower-case trimmed | no | P1 | non-empty |
| plan_date | date | | no | P2 | |
| soil_test_id | uuid | optional; NULL = no test (N only, max `medium`) | yes | P1 | same-org FK; QC: soil test belongs to same field |
| created_by, created_at | | | no | P1 | |

## recommendation (0006) — IMMUTABLE
Purpose: engine output or agronomist final numbers; edits are new rows (`parent_id` + `reason`). Calibration core. Owner AGR. cp_app: SELECT, INSERT.

| Column | Type | Meaning / unit | Null | PII | Rules |
|---|---|---|---|---|---|
| id, organisation_id, crop_plan_id | uuid | | no | P1 | |
| parent_id | uuid | edited version; NULL for engine rows | yes | P1 | same org and crop plan |
| kind | recommendation_kind | `engine` / `agronomist` | no | P1 | engine ⇔ no parent |
| reason | text | why the agronomist changed it | yes | P2 (free text, may mention farm) | required when parent_id set |
| inputs_snapshot | jsonb | exact engine inputs (crop, target yield t/ha, previous crop, area ha, plan date, soil test with values/forms/units/methods/depth/date/lab) | no | P2 | object; equals `result.input_snapshot`. Contains no farmer, farm or field name or coordinates (engine model) |
| result | jsonb | full engine document incl. explanations | no | P2 | object; explanations are engine text, verify they never embed names |
| engine_version, pack_id, pack_version, pack_status, pack_sha256 | text / char(64) | provenance (hard rule 5) | no | P1 | equal to document; sha lower hex |
| confidence | confidence_level | `low` < `medium` < `high` | no | P1 | equals document; no soil test ⇒ ≤ medium (engine rule; add SQL check, see below) |
| n_rate_kg_ha | numeric (generated) | N rate, kg N/ha | no | P1 | ≥ 0; document unit must be `kg N/ha` |
| created_by | uuid | → app_user | no | P2 (identity of person) | active org member; `agronomist` kind requires agronomist role |
| created_at | timestamptz | | no | P1 | |

## review (0007) — IMMUTABLE
Purpose: the agronomist gate. Owner AGR. cp_app: SELECT, INSERT.

| Column | Type | Meaning / unit | Null | PII | Rules |
|---|---|---|---|---|---|
| id, organisation_id, recommendation_id | uuid | | no | P1 | |
| decision | review_decision | `approve` / `edit` / `reject` | no | P1 | one approval per recommendation |
| reason | text | required unless approve | yes | P2 (free text) | |
| reviewer_id | uuid | → app_user, from session | no | P2 | approve needs agronomist |
| minutes_spent | integer | agronomist minutes (key metric) | no | P1 | ≥ 0; QC: flag 0 and > 480 |
| resulting_recommendation_id | uuid | child row for `edit` | yes | P1 | set ⇔ decision=edit |
| created_at | timestamptz | | no | P1 | |

## application_log (0008)
Purpose: planned vs actual application. Mutable. Owner AGR.

| Column | Type | Meaning / unit | Null | PII | Rules |
|---|---|---|---|---|---|
| id, organisation_id, crop_plan_id | uuid | | no | P1 | |
| recommendation_id | uuid | approved rec being followed | yes | P1 | same crop plan; QC: must be approved (not enforced) |
| form | nutrient_form | form of the rate | no | P2 | N/P/K elemental vs oxide explicit |
| product | text | product name | yes | P1 | ≤200 |
| planned_date, actual_date | date | | yes | P2 | QC: actual_date not in future |
| planned_rate_kg_ha, actual_rate_kg_ha | numeric | kg/ha of `form` | yes | P2 | ≥ 0; at least one set |
| notes | text | | yes | P2 (free text) | ≤4000 |
| created_by, created_at | | | no | P1 | |

## proof_document (0008) — IMMUTABLE
Purpose: pointer + hash of a proof PDF for an approved recommendation. Owner AGR. The PDF itself (P2: farmer/farm/field names, numbers) is in the bucket.

| Column | Type | Meaning | Null | PII | Rules |
|---|---|---|---|---|---|
| id, organisation_id, recommendation_id | uuid | | no | P1 | requires an approve review |
| sha256 | char(64) | hash of the PDF | no | P1 | lower hex |
| storage_key | text | `proof/{org}/{rec}/{sha256}.pdf`, unique | no | P1 | equals format() of the other columns |
| created_by, created_at | | | no | P1 / P2 | |

## recommendation_diff (view, 0009)
> **To be replaced (R2, DM-16):** per-line view `calibration_delta` over §6.4 `recommendation_line`, with `reviewer_kind` (D4). Target schema, not yet migrated; spec and column list in `docs/data/calibration-delta-spec.md`.

Purpose: calibration dataset, engine vs final per version. `security_invoker`. Dataset = `where approved_at is not null`. Columns: organisation_id, crop_plan_id, engine_recommendation_id, final_recommendation_id, edited_from_id, final_kind, edit_depth, engine_version, pack_id, pack_version, pack_status, pack_sha256, engine_n_rate_kg_ha, final_n_rate_kg_ha, n_rate_delta_kg_ha (kg N/ha), engine_confidence, final_confidence, edit_reason (P2 free text), final_created_by (P2), final_created_at, approved_by (P2), approved_at, approval_minutes_spent, engine_result, final_result (jsonb, P2). Data-science exports should drop `*_created_by`, `approved_by`, `edit_reason` and use pseudonymous ids.

---

## Data-quality rules (summary)
Enforced in DB today: units fixed to kg/ha (rates) and mg/kg|ppm (soil); form enum with generated nutrient; extraction method enum, `other` needs detail; depth bottom > top; sample_date, source required; confidence enum equal to document; pack/engine provenance non-empty and equal to document; N unit `kg N/ha`; immutability; org-scoped composite FKs; approval-gated proof; one approval per recommendation.
Not enforced (see "Data-quality checks to automate" in `docs/data/pii-and-retention.md`).
