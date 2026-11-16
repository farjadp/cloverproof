# ADR 0002 — Core data model on Postgres + PostGIS (no Supabase, no RLS)

- Status: Proposed (2026-11-16) — needs Farjad Iranmehr's acceptance
- Decider: Farjad Iranmehr
- Related: CLAUDE.md (data model, hard rules), ADR 0004 (Railway), ADR 0005 (auth A1, bucket B1), `docs/plans/webapp-v1.md` Step 4 and §5

## Context
CLAUDE.md fixes the core data model and the hard rules (immutable versioned recommendations, review gate, confidence, input snapshot + engine/pack version, explicit P/K form and extraction method). ADR 0004 moved us from Supabase to Railway Postgres, so RLS, Supabase Auth and Storage are gone. The schema must hold the engine's models (`engine/cloverproof_engine/models.py`, `results.py`) exactly, and keep the engine-vs-agronomist difference as the calibration dataset.

## Decision

### Tables (`db/migrations/0002`–`0009`)
| Area | Tables |
|---|---|
| Identity (ADR 0005 A1) | `organisation`, `app_user` (argon2id hash nullable, `totp_secret`, `auth_provider` local/oidc, `external_subject`, `disabled_at`), `user_session` (SHA-256 of the cookie token only), `membership` (`organisation × user × role`, role ∈ owner/agronomist/staff/farmer; one user can hold several roles) |
| Farm structure | `farmer` → `farm` → `field`; `season`; `field_geometry_version` (one per field per season) |
| Soil | `soil_test` (sample_date, depth_top_cm, depth_bottom_cm, source lab/estimate, lab) and `soil_test_value` (form, derived nutrient, value, unit, extraction_method + detail required for `other`) |
| Planning | `crop_plan` (editable draft inputs), `recommendation` (immutable, versioned), `review` (insert-only), `application_log` (planned vs actual), `proof_document` (immutable) |
| Calibration | view `recommendation_diff` |

Enum labels are the engine's StrEnum values character for character (`bray-1`, `mehlich-3`, `NO3-N`, `mg/kg` …); a test compares them. The database stores no agronomic constants; units and forms are recorded as given.

### Organisation scoping without RLS
- Every org-owned table has `organisation_id`. Children reference parents by `(organisation_id, id)` composite foreign keys, so a row can never point into another organisation (farm → farmer, crop_plan → field/season/soil_test, recommendation parent → same crop plan, review → recommendation, …).
- `member_organisation_ids(user_id)` and `has_org_role(user_id, org_id, role)` are the SQL helpers for the Step 5 data-access layer (every query takes `org_id`) and for triggers. Disabled users have no organisations.
- A `farmer` is a client record of one organisation. CLAUDE.md's "organisation ↔ farmer via membership" is the Phase 4 farmer *login*: an `app_user` with a `farmer` membership, linked by `farmer.app_user_id`.

### Immutability via triggers + grants (instead of RLS)
- `recommendation`, `review`, `proof_document`: `BEFORE UPDATE OR DELETE` row trigger and `BEFORE TRUNCATE` statement trigger raise for every role, including the owner.
- Roles (created NOLOGIN, no password, in `0002`): `cp_migrator` owns every app object (migrations run `set local role cp_migrator`); `cp_app` has SELECT, INSERT on the three immutable tables, SELECT on the view, SELECT/INSERT/UPDATE/DELETE elsewhere. Two independent lines: the grant stops the app, the trigger stops everyone else.
- Edits are new `recommendation` rows: `kind = 'agronomist'`, `parent_id` (same organisation and crop plan) and a non-blank `reason`. Engine rows have no parent; a re-run is a new root.

### Review gate in the database (ADR 0005)
- Trigger on `review` insert: reviewer must be an active member of the recommendation's organisation; `decision = 'approve'` requires an `agronomist` membership there. A trigger on `recommendation` also requires `agronomist` for `kind = 'agronomist'` rows.
- `minutes_spent integer not null >= 0` on every review. `reason` required for edit and reject. At most one approval per recommendation. An `edit` review must name the new row, and a composite FK `(resulting_recommendation_id, recommendation_id) → recommendation(id, parent_id)` guarantees it is the child.
- `proof_document` insert requires an approval; `storage_key` must equal `proof/{org_id}/{recommendation_id}/{sha256}.pdf` (ADR 0005 B1); `sha256 char(64)` lowercase hex.

### jsonb document + typed columns
`recommendation.result` stores the full engine output (`Recommendation.model_dump(mode="json")`) and `inputs_snapshot` the exact inputs. Typed columns (`engine_version`, `pack_id`, `pack_version`, `pack_status`, `pack_sha256`, `confidence`) are what we filter and join on; CHECK constraints keep each equal to the document, and `n_rate_kg_ha` is a generated column from `result.nitrogen.rate.value` (unit must be `kg N/ha`). Agronomist rows store the same document shape with the final numbers, so engine and final compare field by field.

### Calibration dataset
`recommendation_diff` (security_invoker) walks each version's `parent_id` chain to its engine root and returns engine vs final N rate, delta, confidence, edit reason, approver, approval minutes and both documents. Unedited engine rows appear with depth 0 and delta 0. Dataset = `where approved_at is not null`.

### PostGIS geometry nullable
`field_geometry_version.geom geometry(MultiPolygon, 4326)`, NULL until map drawing (Phase 4); `area_ha` is entered by hand (`area_source = 'manual'`) and is what the engine uses. Valid, non-empty geometry when present; GiST index. Requires the PostGIS image (plan §5).

### One migrations folder shared with the website
- Root `db/migrations/` is the single source. `0001_pilot_request.sql` is the website's file copied byte for byte (a test checks it); our files start at `0002`.
- The Python runner (`app/cloverproof_app/db/migrate.py`) uses the website runner's exact `schema_migrations (name text primary key, applied_at timestamptz not null default now())`, keyed by file name (no checksum), sorted by name, one transaction per file. Verified both ways against `website/scripts/migrate.mjs`. Added: an advisory lock, a strict `NNNN_snake_case.sql` pattern, a warning for recorded-but-missing files.
- `db/seeds/dev.sql` is fictional data for local use; the runner refuses to seed non-local hosts.

## Consequences
- One missed `organisation_id` filter in the app leaks data; mitigated by the single data-access layer, the composite FKs, and per-query two-org tests (Step 5).
- Nothing in the three immutable tables can be corrected or erased without a migration that drops the trigger. A deletion request (privacy) on recommendation data needs a documented procedure before real farmer data arrives.
- `crop_plan`, soil tests, fields and geometry stay editable; each recommendation's `inputs_snapshot` is the record of what was used.
- Adding a crop needs no migration (`crop` is text, validated by the engine/pack); adding a nutrient form or extraction method needs an enum migration together with the engine change.
- `totp_secret` must be encrypted by the app (key from env) before storage — Step 5.
- The app must connect as a LOGIN role that is a member of `cp_app` (created outside git); migrations run as the deploy user, which must be able to `set role cp_migrator`.
- The diff view uses a recursive CTE over all recommendations; fine for the pilot volume, revisit with an index-backed root column if it grows.
- Railway: needs the PostGIS service before `0002` can run there (`create extension postgis`).
