# CloverProof — Backend Project Plan

Version 1.0 · Nov 16, 2026 · Owner: Founder/CTO
Status: DRAFT for engineering. Read with `CLAUDE.md`, `05-mvp-build-brief.md`, `03-roadmap-and-validation.md`.

> **CPO note (2026-11-16).** Stored verbatim as supplied by Farjad Iranmehr, except the reviewing agronomist's
> name, which is written as "the agronomist" (repo naming rule). Where this plan conflicts with decisions already
> recorded (ADR 0004 Railway + Railway Postgres, ADR 0005 app-owned auth + Railway Bucket, no RLS), see
> `docs/plans/backend-plan-reconciliation.md` — that file says which side wins for each conflict.
> `05-mvp-build-brief.md` and `03-roadmap-and-validation.md` are not in the repo yet.

> Scope of this document: the backend (database, API, engine integration, jobs, admin) for both the
> **user side** (farmer, advisor/intermediary, agronomist) and the **admin side** (CloverProof staff).
> The farmer-facing frontend and marketing site are out of scope here, except where they need an API.

---

## 0. Table of contents

1. Goals and non-goals
2. Hard constraints and principles
3. Roles and permissions
4. Architecture
5. Module map (user side + admin side)
6. Data model
7. API design (user + admin)
8. Engine integration
9. Proof documents
10. Background jobs
11. External data and licences
12. Security, privacy, compliance
13. Observability and quality
14. Environments, CI/CD, releases
15. Sprint plan (S1 → S30)
16. Definition of Ready / Done
17. Risks
18. Open questions
19. Glossary

---

## 1. Goals and non-goals

### 1.1 Goals by phase

| Phase | Dates | Backend goal |
|---|---|---|
| 0–3 Foundation + Concierge prep | Nov 16, 2026 – Jan 29, 2027 | Internal tool so the agronomist can produce plans for 5–10 farms. Every plan stores engine output vs agronomist output. |
| 2 Concierge | Feb 1 – Apr 30, 2027 | Run real plans. Measure minutes per plan. Add P/K, no-test mode, timing windows. |
| 4 MVP / closed beta | Mar – May 2027 | Farmer + advisor accounts, intermediary dashboard, application log, proof export. 10–20 farms. |
| 5 Pilot season | May – Oct 2027 | Stability, timing updates, application logs from the field, outcome capture (yield). |
| 6 Launch v1 prep | Nov 2027 – Feb 2028 | Billing, second country pack, first lab integration, self-serve onboarding. |

### 1.2 Non-goals (until stated otherwise)

- Hardware, sensor ingestion, IoT.
- Variable-rate / zone maps.
- Carbon / CSRD reporting.
- Fertilizer price comparison or any sales commission.
- Native mobile apps (mobile-friendly web only).
- Automatic recommendations reaching a farmer without agronomist approval.

---

## 2. Hard constraints and principles

1. **Review gate.** No recommendation is visible to a farmer until an agronomist approves it.
2. **Immutability.** Recommendations, reviews and proof documents are append-only. Edits create new versions.
3. **Reproducibility.** Every recommendation stores: input snapshot (JSON), engine version, country-pack version, data-source versions.
4. **Confidence on every number.** Enum `high | medium | low`, rule-based.
5. **No-test rule.** Without a soil test: N only, max `medium`; P/K → "test recommended".
6. **Canonical units.** Store kg/ha, mg/kg, °C, mm. Track nutrient form (P vs P2O5, K vs K2O) and soil-test extraction method, depth, date. Convert only at display.
7. **Country pack = config + tests**, never forked code.
8. **Farmer owns farm data.** Advisors and organisations get access through memberships that the farmer can revoke.
9. **Minimal infrastructure.** One Postgres (Supabase), one Python service, one worker. No extra queue/cache service until measured need.
10. **Honest claims.** No API, PDF or email text says a bank/inspector "accepts" our proof until one has.

---

## 3. Roles and permissions

### 3.1 Roles

| Role | Side | Who | Main actions |
|---|---|---|---|
| `farmer` | User | Farm owner/manager | Own farms/fields, view approved plans, log applications, export proof, grant/revoke access |
| `advisor` | User | Agronomist consultant, co-op staff, dealer agronomist | Manage many farmers (with consent), enter data, request plans, view approved plans |
| `org_admin` | User | Admin of an organisation (co-op, advisory firm, lab) | Invite/remove members, view org dashboard, billing (later) |
| `agronomist` | User/Admin boundary | Reviewing agronomist (the agronomist in phase 2) | Review queue: approve / edit / reject with reason; minutes tracked |
| `lab_partner` | User (later, S25+) | Soil lab | Push results for a sample QR code |
| `staff` | Admin | CloverProof team | Support, read-only data access with audit, manage catalogs |
| `superadmin` | Admin | Founder/CTO | Everything incl. country-pack activation, feature flags, data deletion jobs |

### 3.2 Permission matrix (core)

| Resource | farmer | advisor | org_admin | agronomist | staff | superadmin |
|---|---|---|---|---|---|---|
| Own farms/fields | CRUD | CRUD if granted `edit` | R (org scope) | R (assigned) | R (audited) | CRUD |
| Soil tests | CRUD | CRUD if granted | R | R | R | CRUD |
| Request recommendation | ✓ | ✓ | – | ✓ | – | ✓ |
| See engine draft (unapproved) | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| Approve / edit / reject | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |
| See approved plan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Application log | CRUD | CRUD if granted | R | R | R | CRUD |
| Proof export / share link | ✓ | ✓ if granted | ✗ | ✗ | ✗ | ✓ |
| Members of org | – | – | CRUD | – | R | CRUD |
| Country packs, product catalog | R | R | R | R | CRUD (draft) | CRUD + activate |
| Audit log | own events | own events | org events | own events | R | R |
| Hard delete | request | ✗ | ✗ | ✗ | ✗ | execute |

Access grants between farmer and advisor/org: `view` or `edit`, with optional expiry. Stored in `membership` / `access_grant`.

---

## 4. Architecture

### 4.1 Components

```
                 ┌────────────────────────────┐
  Browser ──────▶│  FastAPI app (Python 3.12) │──┐
  (internal tool │  - /api/v1  (user)          │  │
   + later web)  │  - /admin/v1 (admin)        │  │  SQL (RLS via JWT claims)
                 │  - HTML views (Jinja+HTMX)  │  ▼
                 └────────────┬───────────────┘ ┌──────────────────────────┐
                              │ enqueue         │ Supabase                 │
                 ┌────────────▼───────────────┐ │ - Postgres + PostGIS     │
                 │ Worker (Procrastinate,     │ │ - Auth (JWT)             │
                 │ Postgres-backed queue)     │◀┤ - Storage (PDF, uploads) │
                 │ - PDF render               │ └──────────────────────────┘
                 │ - timing refresh           │
                 │ - notifications            │──▶ NASA POWER, forecast API (later)
                 │ - extraction (later)       │
                 └────────────────────────────┘
        engine/ (pure Python package, imported by app + worker, no I/O)
        data_sources/ (SoilGrids cache, etc.)
```

### 4.2 Stack decisions

| Area | Choice | Why | Revisit when |
|---|---|---|---|
| DB | Supabase Postgres + PostGIS | Geometry, RLS, Auth, Storage in one place | Cost or compliance issue |
| API | FastAPI + Pydantic v2 | Same language as engine; typed schemas; OpenAPI | – |
| DB access | SQLAlchemy 2 Core / asyncpg, migrations in `supabase/migrations` (SQL) | Explicit SQL + RLS | – |
| Auth | Supabase Auth JWT; FastAPI verifies JWT and sets `request.jwt.claims` + `SET LOCAL ROLE authenticated` per transaction | RLS is enforced in DB, not only in code | – |
| Queue | Procrastinate (Postgres) | No Redis to run | > 50 jobs/min sustained |
| PDF | Jinja2 HTML → WeasyPrint | Same templates as web views | – |
| Internal UI | Jinja2 + HTMX served by FastAPI | One deploy for Phase 0–3 | Phase 4 (Next.js farmer app may come) |
| Hosting | Railway (app + worker), Supabase cloud | Already in use | Data-residency need (EU region) |
| Errors | Sentry (free tier) | Fast setup | – |

Region note: if the launch country is in the EU, use a Supabase EU region and Railway EU region (ADR required).

### 4.3 Repo layout

```
engine/                 pure calculation library (see CLAUDE.md)
data_sources/           SoilGrids cache, weather clients, later WoSIS/FTW
app/
  main.py
  api/v1/               user endpoints
  admin/v1/             admin endpoints
  views/                Jinja+HTMX pages (internal tool)
  services/             business logic (no HTTP)
  repositories/         SQL access
  auth/                 JWT verify, role helpers
  jobs/                 Procrastinate tasks
  pdf/templates/
  schemas/              Pydantic request/response models
supabase/migrations/
packs/                  country packs (YAML) + golden tests
docs/adr/  docs/data-sources.md  docs/backlog.md
tests/                  api, service, rls, e2e
```

---

## 5. Module map

### 5.1 User side

| # | Module | Description | First sprint |
|---|---|---|---|
| U1 | Auth & onboarding | Email magic link / password via Supabase; invite acceptance; profile; language + unit preference | S1 (staff only), S9 (farmers) |
| U2 | Organisations & memberships | Org create, invite, roles, leave | S2 |
| U3 | Access grants | Farmer ↔ advisor/org consent, scope view/edit, expiry, revoke | S2 (model), S9 (UI/API) |
| U4 | Farms & fields | CRUD, area (manual, then from geometry), geometry versions per season | S2 |
| U5 | Seasons & crop plans | Season per field, crop, target yield, previous crop, management notes | S2 |
| U6 | Soil tests | Manual entry with method/depth/form/units; file upload; later extraction | S2 (manual), S4 (upload), S20+ (extraction) |
| U7 | No-test estimate | SoilGrids cached estimate (+ LUCAS in EU) with source metadata | S3 |
| U8 | Recommendation request | Run engine → draft → review queue | S2 |
| U9 | Approved plan view | Products, rates, splits, timing window, explanations, confidence | S3 |
| U10 | Application log | Planned vs actual: date, product, rate, area, method, weather note, photo | S10 |
| U11 | Proof export & sharing | PDF (plan + log history), SHA-256, signed share link with expiry, public verify page | S4 (PDF), S11 (share/verify) |
| U12 | Notifications | Email: plan approved, timing window update, reminder to log application | S12 |
| U13 | Outcomes | Yield at harvest, farmer feedback, "did you follow the plan?" | S17 |
| U14 | Data rights | Export my data (JSON/CSV/PDF zip), delete account request | S13 |
| U15 | Sampling kit (QR) | Register kit QR → field; lab result attaches to soil test | S25 |
| U16 | Billing | Subscription per farm/advisor, invoices | S26 |

### 5.2 Admin side

| # | Module | Description | First sprint |
|---|---|---|---|
| A1 | Review queue | List drafts by due date/priority; diff engine vs edit; approve/edit/reject + reason; minutes timer | S2 |
| A2 | Calibration dashboard | Engine vs agronomist delta per nutrient/crop/pack; minutes per plan; acceptance-without-edit rate | S5 |
| A3 | Country pack registry | Upload pack YAML → validate schema → run golden tests → status draft/active/retired; one active per country+crop | S4 |
| A4 | Product catalog | Fertilizer products per country (grade N-P-K-S, form, density), active flag | S4 |
| A5 | Orgs & users admin | Search, view, suspend, resend invite, change role (audited) | S6 |
| A6 | Support view | Read-only "view as" for a farm, every access logged with reason | S8 |
| A7 | Audit log viewer | Filter by actor, entity, action, date | S6 |
| A8 | Data source status | SoilGrids cache coverage, last weather refresh, job failures | S7 |
| A9 | Job monitor | Queue depth, failed jobs, retry | S7 |
| A10 | Feature flags | Per org / per country flags (e.g., `farmer_self_serve`) | S9 |
| A11 | Pilot metrics | Execution rate, fertilizer change vs last year, yield vs last year, proof used with third party | S16 |
| A12 | Deletion & export jobs | Execute GDPR/PIPEDA requests with approval | S13 |
| A13 | Billing admin | Plans, coupons, manual invoices | S26 |

---

## 6. Data model

All tables: `id uuid pk default gen_random_uuid()`, `created_at timestamptz default now()`, `created_by uuid`.
Mutable tables also have `updated_at`. Soft delete via `deleted_at` where noted. Immutable tables: no UPDATE/DELETE grants.

### 6.1 Identity and access

| Table | Key columns | Notes |
|---|---|---|
| `profile` | user_id (auth.users), full_name, locale, unit_system (`metric`/`imperial`), platform_role (`none`/`staff`/`superadmin`) | 1:1 with auth user |
| `organisation` | name, kind (`advisory`/`coop`/`dealer`/`lab`/`internal`), country_code | |
| `org_membership` | org_id, user_id, role (`org_admin`/`advisor`/`agronomist`), status | |
| `farmer` | owner_user_id (nullable in concierge), display_name, country_code, contact | Farmer may exist before having a login (concierge) |
| `access_grant` | farmer_id, grantee_org_id or grantee_user_id, scope (`view`/`edit`), granted_by, expires_at, revoked_at | Consent record — immutable history; revoke = new row state |

### 6.2 Farm structure

| Table | Key columns | Notes |
|---|---|---|
| `farm` | farmer_id, name, region_code | |
| `field` | farm_id, name, external_ref, deleted_at | |
| `field_geometry_version` | field_id, season_year, geom (MultiPolygon, 4326), area_ha (computed), area_source (`manual`/`geometry`), valid_from | Fields change between seasons |
| `season` | field_id, year, crop_code, variety, sowing_date, target_yield, target_yield_unit, previous_crop_code, notes | One active season per field+year |

### 6.3 Soil

| Table | Key columns | Notes |
|---|---|---|
| `soil_sample` | field_id, sampled_at, depth_top_cm, depth_bottom_cm, lab_name, kit_qr (later), file_ids | One sampling event |
| `soil_measurement` | sample_id, property (`ph_water`, `ph_cacl2`, `som`, `p`, `k`, `no3_n`, ...), value, unit, extraction_method (`olsen`/`bray1`/`mehlich3`/`ammonium_acetate`/...), nutrient_form (`elemental`/`oxide`), canonical_value, canonical_unit, entry_method (`manual`/`extracted`/`lab_api`), confirmed_by, confirmed_at | Never store P without method + form |
| `soil_estimate` | field_id, season_year, property, value, unit, source (`soilgrids`/`lucas`/`wosis`), source_version, resolution_m, depth, uncertainty, retrieved_at | Always confidence `low` |

### 6.4 Recommendation and review

| Table | Key columns | Notes |
|---|---|---|
| `recommendation` | season_id, parent_id, version_no, status (`draft`/`in_review`/`approved`/`rejected`/`superseded`), origin (`engine`/`agronomist_edit`), engine_version, pack_id + pack_version, input_snapshot jsonb, output jsonb, confidence_overall, created_by | **Immutable.** Edit = new row with parent_id |
| `recommendation_line` | recommendation_id, nutrient, rate_kg_ha, product_id, product_rate, product_unit, split_no, timing_window_start, timing_window_end, timing_basis (`gdd`/`calendar`/`manual`), explanation, confidence | Immutable |
| `review` | recommendation_id, reviewer_id, decision (`approve`/`edit`/`reject`), reason, minutes_spent, started_at, finished_at | Immutable |
| `calibration_delta` (view) | per line: engine value vs final approved value, abs/rel diff | Materialized view refreshed nightly |

### 6.5 Execution and proof

| Table | Key columns | Notes |
|---|---|---|
| `application_log` | season_id, recommendation_line_id (nullable), applied_on, product_id or free_text, rate, rate_unit, area_ha, method, operator, weather_note, photo_ids, entered_by | Editable for 24h, then locked (correction = new row with `corrects_id`) |
| `proof_document` | season_id, recommendation_id, kind (`plan`/`plan_with_log`), storage_path, sha256, generated_at, generated_by, template_version | Immutable |
| `share_link` | proof_document_id, token_hash, expires_at, revoked_at, view_count | Token shown once |
| `outcome` | season_id, harvest_date, yield_value, yield_unit, followed_plan (`yes`/`partly`/`no`), farmer_comment, third_party_used (`bank`/`buyer`/`inspector`/`subsidy`/`none`), third_party_result | Pilot metrics |

### 6.6 Catalogs and config

| Table | Key columns | Notes |
|---|---|---|
| `crop` | code, name_i18n, gdd_base_c | |
| `country_pack` | country_code, crop_code, version (semver), status (`draft`/`active`/`retired`), yaml_blob, yaml_sha256, golden_report jsonb, activated_by, activated_at | One `active` per country+crop (partial unique index) |
| `fertilizer_product` | country_code, name, n, p2o5, k2o, s, form (`granular`/`liquid`), density, active | Vendor-neutral: no prices from vendors, no affiliate fields |
| `feature_flag` | key, scope (`global`/`org`/`country`), scope_id, enabled | |

### 6.7 Platform

| Table | Key columns | Notes |
|---|---|---|
| `file_object` | bucket, path, mime, size, sha256, uploaded_by | Storage metadata |
| `audit_event` | actor_id, actor_role, action, entity_type, entity_id, reason, ip_hash, at, diff jsonb | Append-only. Written by DB triggers + app |
| `notification` | user_id, kind, payload, sent_at, channel | |
| `data_request` | user_id, kind (`export`/`delete`), status, approved_by, completed_at | |
| `weather_daily` | cell_id, date, tmin, tmax, precip, source, retrieved_at | Cache of NASA POWER by grid cell |

### 6.8 RLS summary

- `farmer`, `farm`, `field`, `season`, `soil_*`, `application_log`, `outcome`: visible if user is owner OR has active `access_grant` (direct or via org membership) OR platform_role in (`staff`,`superadmin`).
- `recommendation` with status ≠ `approved`: visible only to `agronomist` members of the reviewing org and platform roles.
- Immutable tables: INSERT allowed by policy; UPDATE/DELETE revoked from `authenticated`.
- `audit_event`: INSERT only via trigger/service role; SELECT by policy above.
- Every policy has a pytest RLS test with at least two users (allowed / denied).

---

## 7. API design

Conventions: REST, JSON, `/api/v1` (user) and `/admin/v1` (admin). Auth: `Authorization: Bearer <supabase JWT>`.
Pagination: cursor (`?cursor=&limit=`). Errors: RFC 9457 problem+json. IDs: UUID. Times: ISO 8601 UTC.
Idempotency: `Idempotency-Key` header on POSTs that create recommendations, proofs, logs.
Units: request/response can carry `unit_system`; server stores canonical.

### 7.1 User API (`/api/v1`)

**Me & access**
| Method | Path | Purpose |
|---|---|---|
| GET | `/me` | Profile, roles, memberships |
| PATCH | `/me` | Name, locale, unit system |
| GET | `/orgs` | My orgs |
| POST | `/orgs/{id}/invites` | Invite member (org_admin) |
| POST | `/invites/{token}/accept` | Accept invite |
| GET | `/farmers` | Farmers I can access |
| POST | `/farmers` | Create farmer (advisor/concierge) |
| POST | `/farmers/{id}/grants` | Grant access to org/user |
| DELETE | `/grants/{id}` | Revoke (farmer only) |

**Farm structure**
| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/farmers/{id}/farms` | List/create |
| GET/PATCH | `/farms/{id}` | |
| GET/POST | `/farms/{id}/fields` | |
| GET/PATCH/DELETE | `/fields/{id}` | Soft delete |
| POST | `/fields/{id}/geometry` | New geometry version (GeoJSON) |
| GET/POST | `/fields/{id}/seasons` | |
| GET/PATCH | `/seasons/{id}` | |

**Soil**
| Method | Path | Purpose |
|---|---|---|
| POST | `/fields/{id}/soil-samples` | Create sample + measurements |
| GET | `/fields/{id}/soil-samples` | History |
| POST | `/soil-samples/{id}/files` | Upload report (PDF/image) |
| POST | `/soil-samples/{id}/confirm` | Human confirms values (required before use) |
| GET | `/fields/{id}/soil-estimate` | Cached no-test estimate with source + confidence |

**Recommendations**
| Method | Path | Purpose |
|---|---|---|
| POST | `/seasons/{id}/recommendations` | Run engine → draft → review queue (advisor/agronomist) |
| GET | `/seasons/{id}/recommendations` | Approved versions (farmer) / all (agronomist) |
| GET | `/recommendations/{id}` | Detail with lines, explanations, confidence |
| GET | `/recommendations/{id}/timing` | Current timing window + last refresh |

**Execution & proof**
| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/seasons/{id}/applications` | Application log |
| POST | `/applications/{id}/corrections` | Correction after lock |
| POST | `/seasons/{id}/proofs` | Generate proof PDF (async job) |
| GET | `/proofs/{id}` | Metadata + signed download URL |
| POST | `/proofs/{id}/share-links` | Create expiring link |
| DELETE | `/share-links/{id}` | Revoke |
| GET | `/public/verify/{sha256}` | **No auth.** Returns: exists, generated_at, template_version. No personal data |
| GET | `/public/share/{token}` | **No auth.** Renders shared PDF if valid |
| POST | `/seasons/{id}/outcome` | Yield + feedback |

**Data rights**
| Method | Path | Purpose |
|---|---|---|
| POST | `/me/data-requests` | Export or delete request |
| GET | `/me/data-requests` | Status |

### 7.2 Agronomist endpoints (`/api/v1/review`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/review/queue` | Drafts assigned to my org, sorted by due date |
| POST | `/review/{rec_id}/start` | Start timer |
| POST | `/review/{rec_id}/approve` | Approve as is |
| POST | `/review/{rec_id}/edit` | Body = changed lines + reason → creates new version + approves |
| POST | `/review/{rec_id}/reject` | Reason required |

### 7.3 Admin API (`/admin/v1`) — `staff` / `superadmin` only

| Method | Path | Purpose | Role |
|---|---|---|---|
| GET | `/users` `/orgs` | Search | staff |
| PATCH | `/users/{id}` | Suspend, platform role | superadmin |
| POST | `/support/sessions` | Start read-only "view as" (reason required, 30-min expiry) | staff |
| GET | `/audit` | Audit search | staff |
| GET/POST | `/packs` | List / upload draft pack | staff |
| POST | `/packs/{id}/validate` | Schema + golden tests | staff |
| POST | `/packs/{id}/activate` | Activate (retires previous) | superadmin |
| GET/POST/PATCH | `/products` | Product catalog | staff |
| GET | `/metrics/calibration` | Engine vs agronomist deltas | staff |
| GET | `/metrics/review-time` | Minutes per plan | staff |
| GET | `/metrics/pilot` | Pilot KPIs | staff |
| GET | `/jobs` · POST `/jobs/{id}/retry` | Job monitor | staff |
| GET | `/data-sources/status` | Cache coverage, last refresh | staff |
| GET/PATCH | `/flags` | Feature flags | superadmin |
| GET | `/data-requests` · POST `/data-requests/{id}/execute` | GDPR/PIPEDA | superadmin |

### 7.4 HTML views (internal tool, Phase 0–3)

Same services as the API. Pages: login, farmer list, farmer detail, field detail, new plan wizard,
review queue, review detail (side-by-side engine vs edit), PDF preview, calibration dashboard, packs, products.

---

## 8. Engine integration

- `engine` is imported as a library: `run(EngineInput, Pack) -> EngineOutput`. No DB, no network.
- `services/recommendation_service.py` builds `EngineInput` from DB (season, confirmed soil measurements or estimates, crop, region), loads the active pack, calls the engine, stores the result as `recommendation(status=in_review)` with full `input_snapshot`.
- Engine output includes per-line `explanation` and `confidence`; service never rewrites them silently.
- Pack resolution: country of farm + crop → active pack. If none → 422 with clear message.
- Golden tests run in CI for every pack change (`kind: agronomist_approved | external_reference`).
- Engine version = package version (semver) + git SHA stored on every recommendation.

---

## 9. Proof documents

- Generated by worker from HTML template → WeasyPrint → Storage `proofs/{season_id}/{uuid}.pdf`.
- Content: farm/field/season, inputs (with sources + confidence), approved lines, explanations, reviewer + date, application log (for `plan_with_log`), engine/pack/template versions, document ID, SHA-256, verify URL.
- SHA-256 computed on final bytes; stored in `proof_document`. Never regenerate into the same row.
- Public verify endpoint confirms a hash exists and when it was generated — nothing else.
- Wording rule: "This plan was prepared with CloverProof and reviewed by an agronomist." No claim that any third party accepts it. Legal disclaimer text from lawyer (open question).
- Language: English first; pack-provided strings later.

---

## 10. Background jobs (Procrastinate)

| Job | Trigger | Notes |
|---|---|---|
| `render_proof` | POST proofs | Retry 3×; notify when done |
| `refresh_timing_windows` | Nightly 02:00 local per country | Recompute GDD from cached weather; flag windows that moved > 3 days |
| `fetch_weather` | Nightly | NASA POWER by grid cell for active seasons; cache in `weather_daily` |
| `refresh_calibration_view` | Nightly | Materialized view |
| `send_notifications` | Event-driven | Email via provider (Resend/Postmark — pick in S12) |
| `execute_data_request` | Admin action | Export zip / cascade delete with audit |
| `extract_soil_report` | Upload (S20+) | Docling → candidate values → requires human confirm |
| `cleanup_share_links` | Daily | Expire tokens |

---

## 11. External data and licences

Source of truth: `docs/data-sources.md`. Rules:
- SoilGrids: offline cache only, no live API calls at runtime.
- LUCAS: raw values never leave the backend.
- WoSIS: licence filter mandatory.
- NASA POWER: cache by grid cell; record retrieval date.
- Forecast provider: commercial licence required before any farmer-facing forecast (decide in S8).
- No GPL/EUPL code in production without ADR + lawyer approval (PCSE, farmOS).
- Every estimate stores source, version, resolution, depth, retrieved_at.

---

## 12. Security, privacy, compliance

| Area | Requirement |
|---|---|
| AuthN | Supabase Auth; MFA required for `agronomist`, `staff`, `superadmin` |
| AuthZ | RLS in DB + role checks in services; deny by default |
| Secrets | Env vars only; `.env.example`; rotate on team change |
| Transport | HTTPS only; HSTS |
| Storage | Private buckets; signed URLs ≤ 15 min |
| Audit | All admin actions, grants, approvals, exports, deletions, support sessions |
| Privacy law | PIPEDA (+ Ontario/Quebec specifics if Canada); GDPR if EU — DPA template, records of processing, data export/delete within 30 days |
| Data residency | Decide with launch country (ADR) |
| Backups | Supabase daily backups + weekly logical dump to separate storage; restore test each quarter |
| Rate limits | Public endpoints (`/public/*`) rate limited per IP |
| Dependency security | Dependabot + `pip-audit` in CI |
| Pen test | Self-run checklist before closed beta (S11); external before paid launch |
| Liability | Terms: advice, not guarantee; agronomist licensing in target jurisdiction verified (open question) |

---

## 13. Observability and quality

- Structured JSON logs with request_id, user_id (hashed), org_id.
- Sentry for app + worker.
- Health endpoints: `/healthz` (liveness), `/readyz` (DB + storage).
- Key metrics: request latency p95, job failures, review minutes per plan, approval-without-edit rate.
- Tests: unit (engine, services), RLS tests, API tests (httpx), e2e smoke on staging after deploy.
- Coverage target: engine ≥ 90%, services ≥ 75%.
- Performance target: engine run < 500 ms; proof PDF < 10 s; API p95 < 300 ms (excluding PDF).

---

## 14. Environments, CI/CD, releases

| Env | Purpose | Data |
|---|---|---|
| local | `supabase start` + `make dev` | Seed data |
| staging | Railway + Supabase project #2 | Synthetic + anonymised |
| production | Railway + Supabase project #1 | Real |

- CI (GitHub Actions): lint (ruff), type check (mypy on engine + services), tests, golden report, pip-audit.
- Migrations: forward-only; applied by CI to staging, manual approve for production.
- Release: tag `vYYYY.MM.N`; changelog; production deploy only Mon–Thu.
- Freeze: no risky releases during the first two weeks of concierge (Feb 1–14) and peak N application windows.

---

## 15. Sprint plan

Two-week sprints. Capacity assumption: Founder/CTO part-time (≈ 20 h/week — **confirm**), Claude Code assisted.
S3 is a holiday sprint (≈ 50% capacity). Each sprint ends with a demo to the agronomist and/or the team.

### Phase A — Concierge readiness (Nov 16, 2026 → Jan 29, 2027)

#### S1 · Nov 16 – Nov 27 · Foundation
Goal: audit + skeleton + engine v0 + first plan end to end.
- Audit existing MVP → ADR-0001 (repo & stack)
- Monorepo scaffold, CI, Makefile, pre-commit
- Migrations v0: profile, organisation, org_membership, farmer, farm, field, field_geometry_version, season, soil_sample, soil_measurement, recommendation, recommendation_line, review, proof_document, audit_event
- RLS v0 + tests (two users)
- Engine v0: wheat, N only, placeholder pack, explanations, confidence
- Internal tool v0: farmer → field → season → soil (manual) → run engine → review (approve/edit/reject + reason + timer)
- PDF v0 (English, brand colours, SHA-256)
**DoD:** 5 sample plans end to end; delta stored; minutes measured.

#### S2 · Nov 30 – Dec 11 · Real pack + review quality
Goal: launch country decided (business gate); first real pack.
- Country pack v1 (real method, chosen country, crop 1) + golden tests (agronomist + external_reference)
- `access_grant` model + RLS
- Review queue page: sort, filter, side-by-side diff
- Product catalog (A4) v0 + product matching in engine (need → product → quantity)
- Split plan logic (pack-driven)
- `docs/data-sources.md` + open-data prompt tasks
**DoD:** the agronomist runs 5 real-format cases; ≥ 1 full PDF he would sign.

#### S3 · Dec 14 – Jan 1 · No-test mode + P/K (holiday, 50%)
- SoilGrids offline cache for launch-country bbox; `soil_estimate` table; no-test path in engine (N only, medium max)
- P/K with soil test (pack-driven critical values, method-aware)
- Unit conversions everywhere (P/P2O5, K/K2O, lb/ac ↔ kg/ha)
**DoD:** same field run with/without test shows correct confidence + P/K "test recommended".

#### S4 · Jan 4 – Jan 15 · Timing + uploads + pack registry
- `weather_daily` + NASA POWER fetch job; GDD-based timing window per split
- Soil report file upload + "confirm values" step (manual transcription; no OCR)
- Country pack registry (A3): upload, validate, golden report, activate
- Procrastinate worker running (proof render async, weather fetch)
**DoD:** timing window shown with basis + date of last refresh; pack activation audited.

#### S5 · Jan 18 – Jan 29 · Hardening + rehearsal
- Calibration dashboard (A2): delta per nutrient, minutes per plan, approve-without-edit rate
- Backups verified (restore test), Sentry, health checks, staging = production config
- MFA for agronomist/staff; audit coverage review
- Full rehearsal: 3 real farms from Phase 1 entered end to end by the agronomist without help
- Bug bash; freeze list
**DoD (Concierge gate):** rehearsal done; median minutes per plan known; no P1 bugs open.

### Phase B — Concierge in operation + MVP build (Feb 1 → May 7, 2027)

#### S6 · Feb 1 – Feb 12 · Concierge support (stability first)
- On-call fixes only + small UX fixes from the agronomist
- Orgs & users admin (A5), audit log viewer (A7)
- Second crop in pack (if decided)

#### S7 · Feb 15 – Feb 26 · Ops visibility
- Job monitor (A9), data source status (A8)
- Timing refresh nightly + "window moved" flag to agronomist
- Plan revision flow (new version after approval, e.g., weather change)

#### S8 · Mar 1 – Mar 12 · Support + forecast decision
- Support "view as" read-only with reason + audit (A6)
- Forecast provider decision (licence) — ADR; implement rain check if licensed
- Performance pass on review queue

#### S9 · Mar 15 – Mar 26 · Farmer & advisor accounts
- Farmer invite + login; farmer sees ONLY approved plans
- Advisor accounts; access grants UI/API (grant/revoke/expire)
- Feature flags (A10): `farmer_portal`, `advisor_portal`
- Units + locale preferences honoured in API

#### S10 · Mar 29 – Apr 9 · Application log
- Application log API + mobile-friendly pages (planned vs actual, photo upload, 24h lock + corrections)
- Link log entries to recommendation lines
- Proof kind `plan_with_log`

#### S11 · Apr 12 – Apr 23 · Proof sharing + security review
- Share links (expiring, revocable) + public verify endpoint + rate limits
- Self-run security checklist (OWASP ASVS L1 subset), dependency audit
- Terms + privacy notice wired into onboarding (text from lawyer)

#### S12 · Apr 26 – May 7 · Closed beta readiness
- Notifications (plan approved, window update, log reminder) — email provider chosen
- Intermediary dashboard API: org-level list of farmers, fields, plan status, pending logs
- Beta onboarding of 2–3 intermediaries; seed 10–20 farms
**DoD (MVP gate):** 10–20 farms live; farmer can view plan, log application, export proof.

### Phase C — Pilot season (May 10 → Oct 29, 2027)

Rule: stability over features. Every sprint keeps 40% capacity for pilot support.

| Sprint | Dates | Focus |
|---|---|---|
| S13 | May 10 – May 21 | Data rights: export/delete requests (U14, A12); incident runbook |
| S14 | May 24 – Jun 4 | Second/third split timing updates; in-season plan revisions at scale |
| S15 | Jun 7 – Jun 18 | Advisor bulk actions (multi-field plan request, bulk approve view for agronomist with per-plan sign-off) |
| S16 | Jun 21 – Jul 2 | Pilot metrics (A11): execution rate, fertilizer change vs last year, proof used with third party |
| S17 | Jul 5 – Jul 16 | Outcomes (U13): yield capture, "followed plan?" feedback |
| S18 | Jul 19 – Jul 30 | Field geometry: draw/upload boundary (GeoJSON/Shapefile/KML), area from geometry |
| S19 | Aug 2 – Aug 13 | Field boundary pre-fill spike (Fields of The World, country subset) — behind flag |
| S20 | Aug 16 – Aug 27 | Soil report extraction spike (Docling) on the 30+ collected reports; human confirm mandatory |
| S21 | Aug 30 – Sep 10 | Extraction v1 if spike ≥ target accuracy (define in S20); else drop |
| S22 | Sep 13 – Sep 24 | Previous-crop suggestion (AAFC ACI / EuroCrops) — suggestion only |
| S23 | Sep 27 – Oct 8 | Harvest data import (CSV), season close, archive |
| S24 | Oct 11 – Oct 22 | Pilot report data pack: calibration, outcomes, minutes per plan → decision memo |
| — | Oct 25 – Oct 29 | Buffer / retro |

### Phase D — Launch v1 prep (Nov 1, 2027 → Feb 2028)

| Sprint | Dates | Focus |
|---|---|---|
| S25 | Nov 1 – Nov 12 | Sampling kit QR → lab result flow (U15); lab partner role |
| S26 | Nov 15 – Nov 26 | Billing (U16, A13): plans per farm/advisor, Stripe, invoices, tax |
| S27 | Nov 29 – Dec 10 | Second country pack (config only) + i18n strings in PDF |
| S28 | Dec 13 – Dec 31 | First lab API integration (holiday 50%) |
| S29 | Jan 3 – Jan 14, 2028 | Self-serve onboarding (behind flag), external pen test fixes |
| S30 | Jan 17 – Jan 28, 2028 | Launch hardening, load test, runbooks, v1 release |

---

## 16. Definition of Ready / Done

**Ready (a story can start when):**
- User story + acceptance criteria written.
- Data model impact known; migration sketched.
- Permissions defined (which roles, RLS impact).
- Agronomic rules (if any) confirmed by the agronomist or marked PLACEHOLDER.

**Done:**
- Code + tests merged; CI green; golden report unchanged or explained.
- RLS tests for any new table.
- Audit events for any admin/sensitive action.
- OpenAPI updated; ADR written if a decision was made.
- Deployed to staging and demoed.
- No new "unknown" licence used in production.

---

## 17. Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Launch country not decided by Dec 11 | Engine/pack rework; concierge slips | Medium | Pack is config; placeholder clearly labelled; escalate on Dec 11 |
| Agronomist time is the bottleneck | Plans late in peak season | High | Measure minutes/plan from S1; optimise review UI; second reviewer plan |
| CTO capacity (part-time) | Sprints slip | High | Strict scope; cut Phase C features first, never Phase A |
| SoilGrids API instability | No-test mode down | Medium | Offline cache (no runtime calls) |
| Licence problems (forecast, GPL) | Legal exposure | Medium | `data-sources.md`, ADRs, lawyer before beta |
| Unit/method errors in soil data | Wrong rates → farmer harm | Medium | Mandatory method/form/depth fields; conversion tests; agronomist gate |
| Liability for advice | Legal | Medium | Review gate, terms, agronomist credentials checked in target jurisdiction |
| Free official tools (e.g., Ontario AgriSuite) | Weak willingness to pay | Medium–High | Value = proof, log, workflow, intermediaries — measure in pilot |

---

## 18. Open questions

1. Existing MVP: stack, what works, keep or rewrite? (S1 audit)
2. Launch country + first crop(s)? (needed by Dec 11)
3. Real weekly capacity of the CTO? Any second developer?
4. The agronomist: hours/week Feb–Apr; credentials valid in target jurisdiction?
5. Email provider and sender domain (cloverproof.com status)?
6. Data residency requirement (EU vs Canada)?
7. Legal disclaimer + terms text — who drafts, by when?
8. Forecast data provider and licence budget?
9. Billing model to implement in S26 (per farm, per advisor seat, per plan)?

---

## 19. Glossary

| Term | Meaning |
|---|---|
| Pack / country pack | Versioned YAML with method parameters, crop tables, products, units, strings for one country (+ crop) |
| Golden test | Input → expected output case, approved by agronomist or taken from an external reference |
| Draft | Engine output not yet reviewed |
| Review gate | Rule that only approved recommendations reach farmers |
| Proof document | Immutable PDF with SHA-256 and verify URL |
| GDD | Growing degree days (temperature sum above crop base) |
| Concierge | Phase where the agronomist produces plans with internal tools for 5–10 farms |
