# Web app v1 — internal concierge tool on Railway

- Status: Approved by Farjad Iranmehr (2026-11-16)
- Owner: `cloverproof-lead`
- Replaces the hosting assumptions in `docs/sprints/sprint-1.md` (Supabase) with ADR 0004 (Railway + Railway Postgres).

## 1. Goal
By **Feb 1, 2027**, Farjad Iranmehr can produce a reviewed, versioned fertilizer plan and its proof PDF for one farm in a single sitting, so that he can do 5–10 farms in the **Feb–Apr 2027** field season. Every plan keeps the engine output, his final numbers and his reason (the calibration dataset).

## 2. Scope
In v1 (Phase 0–3):
- `engine/` v0: wheat, nitrogen only, mass balance, PLACEHOLDER constants until Farjad Iranmehr supplies real ones.
- Internal concierge tool (`app/`, FastAPI + Jinja2 + HTMX, English only) on Railway.
- Railway Postgres (with PostGIS — see §5), access control in application code + database grants.
- Auth and proof-PDF storage per ADR 0005.
- Proof PDF v0 (WeasyPrint, SHA-256 stored).

Not in v1: farmer portal (Phase 4, planned only — §8), map drawing, OCR/LLM, Sentinel-2, weather, payments, mobile, multi-language in the tool.

> **Scope note (2026-11-16, reconciliation R5 — supersedes the engine line above).** The engine scope is now the backend plan's (`docs/plans/backend-plan.md` §15, read through `docs/plans/backend-plan-reconciliation.md`), on the S1–S30 calendar (D3):
> - **S2 (Dec 11):** real Ontario winter wheat pack `packs/ca-on/` v1 (R4) with golden cases `kind: agronomist_approved | external_reference`; product catalog v0 + product matching (need → product → quantity); pack-driven split plan; review queue + side-by-side diff (`docs/design/review-queue.md`).
> - **S3 (merge by Dec 23):** P/K **with a lab soil test only**, method-aware (Olsen / Bray-1 / Mehlich-3), form tracked; no-test mode from an offline SoilGrids cache — **N only, confidence `medium` at most**, P/K "test recommended"; unit conversions on display.
> - **S4:** weather (NASA POWER daily fetch) + GDD timing windows per split; soil-report upload with manual "confirm values" (no OCR).
> - **Every agronomic constant stays `PLACEHOLDER` + `TODO(agronomist)` until a human agronomist validates it.** Values proposed by the AI agronomist `cp-agronomist` are `ai_reviewed` only (D4) and never count as validation.
> - Storage/auth/DB stay as in §3 (D1), now with Postgres RLS on Railway as defence in depth (ADR 0006, pending). Weather moves into scope from S4; the rest of the "Not in v1" list stands until `CLAUDE.md` is updated (draft: `docs/product/claude-md-draft.md`, awaiting Farjad Iranmehr).
> - Story-level detail: `docs/backlog.md`.

## 3. What changes vs Sprint 1 (Supabase → Railway)
| Sprint 1 assumed | v1 does instead | Where decided |
|---|---|---|
| `supabase/migrations/`, local Supabase | `db/migrations/` plain SQL at repo root, one runner; local Postgres+PostGIS in Docker (`make db-up`) | ADR 0004, ADR 0002 (Step 4) |
| RLS by organisation | Org scoping in a single data-access layer (every query takes `org_id`), plus DB roles: `cp_migrator` owns schema, `cp_app` has no UPDATE/DELETE on `recommendation`, `review`, `proof_document` | ADR 0002 |
| Supabase Auth | App-owned auth (see ADR 0005 draft) | ADR 0005 |
| Supabase Storage | Railway Bucket for PDFs (see ADR 0005 draft) | ADR 0005 |
| PostGIS built in | Railway's default Postgres has **no** PostGIS → PostGIS image service | §5, ADR 0002 |
| Website migrates its own DB | Migrations move to `db/migrations/`; the app's pre-deploy runs them; website stops running its own migrate (coordinated with the `cp-website` session) | ADR 0004 consequence |

Immutability, review gate, confidence, input snapshot, engine/pack version and the engine-vs-agronomist diff are unchanged from CLAUDE.md.

## 4. Steps
Run in order; Steps 1 and 2 can run in parallel (disjoint files). Plan mode first for each step.

| # | Step | Owner(s) | Files | Exit criteria |
|---|------|----------|-------|---------------|
| 1 | Audit old Rootwise MVP (read-only) | `cp-auditor` | `docs/audit-existing-mvp.md`, `docs/adr/0001-repo-and-stack.md` | Audit done; Farjad Iranmehr decides reuse vs port → ADR 0001. **Skipped if there is no old code** (ADR 0001 then records "start fresh"). |
| 2 | Scaffold Python monorepo | `cp-platform` | `pyproject.toml`, `engine/`, `app/` skeletons, `Makefile`, `.env.example`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `docker-compose.yml` (local PostGIS) | `make test`, `make lint` green locally and in CI; `make db-up` starts PostGIS locally; update `cp-*` agent files that still say Supabase |
| 3 | Engine v0, test-first | `cp-engine` → `cp-agronomy-guard` review | `engine/`, `packs/placeholder/v0.yaml`, `engine/tests/golden/` | Unit tests pass; golden report runs; every constant `PLACEHOLDER` + `TODO(agronomist)`; no P/K without soil test; guard sign-off |
| 4 | Database schema on Railway Postgres | `cp-database` | `db/migrations/`, `db/seeds/`, `docs/adr/0002-data-model.md` | Migrations apply on local PostGIS and on a Railway staging DB; `cp_app` cannot UPDATE/DELETE immutable tables (tested); org-scoping tested with two users in two orgs; reviewer-must-be-agronomist enforced in DB; seed: 1 org, 1 farmer, 2 fields |
| 5 | Concierge tool + auth | `cp-concierge-app` (+ `cp-design` for screens from Stitch) | `app/` (not `app/pdf/`) | Login (ADR 0005); farmer/field list → plan form → engine run → suggestion with explanations + confidence → edit with reason = new version → approve; only `agronomist` approves; minutes-per-plan recorded on every review; Farjad Iranmehr enters one case end to end without help |
| 6 | Proof PDF v0 | `cp-pdf` | `app/pdf/` | PDF from approved recommendation only; SHA-256 stored in `proof_document`; file in Railway Bucket (write-once key); brand colours; no third-party-acceptance claims |
| 7 | Deploy + release gate | `cp-platform`, `cp-qa` | `railway.json`/service config, `docs/runbook-webapp.md` | `app` service live on Railway (staging + production envs); health check; DB backups confirmed; `cp-qa` go/no-go on the full flow with Farjad Iranmehr's 5 real cases; avg minutes/plan measured |

`cp-qa` writes the test plan for each step from these exit criteria before the step closes. `cp-agronomy-guard` reviews Steps 3, 5 (numbers shown) and 6 (PDF content).

## 5. PostGIS on Railway
Railway's default Postgres template is the official Postgres image plus SSL; Railway states it does not plan to add extensions to it and points to marketplace templates (PostGIS, Timescale, pgvector). Source: https://docs.railway.com/databases/postgresql. A PostGIS template exists (`postgis/postgis:17-3.5`, community-maintained): https://railway.com/deploy/postgis-postgres. A Railway forum thread reports `extension "postgis" is not available` on the standard service: https://station.railway.com/questions/how-do-i-connect-the-postgis-template-wi-a95023c5.

Not yet verified against our live database (a read-only `pg_available_extensions` query needs Farjad Iranmehr's permission).

**Recommendation:** in Step 4, add one Postgres service from the official `postgis/postgis:17-3.5` image (our own service with a volume, not the community template), move the website's small `pilot_requests` table into it with `pg_dump`/`pg_restore`, and point both services at it. Do it now, while the database is nearly empty. Fallback if Farjad Iranmehr prefers not to: store field geometry as GeoJSON `jsonb` + manual `area_ha` until Phase 4 (no map drawing or spatial queries are in scope before then).

## 6. Timeline (to Feb 1, 2027 ready; field season Feb–Apr 2027)
| Window | Work | Gate |
|---|---|---|
| Nov 16–20 | Approve this plan + ADR 0005; Step 1 (if old code exists) ∥ Step 2 | Plan approved |
| Nov 23–Dec 4 | Step 3 engine v0; Step 4 schema + PostGIS DB | Guard sign-off; migrations green |
| Dec 7–Dec 18 | Step 5 concierge tool + auth | One case end to end (staging) |
| Dec 21–Jan 8 | Holiday-light: Step 6 PDF v0; Step 7 deploy | PDF + hash on staging |
| Jan 11–29 | Real cases through the tool; replace golden samples; fixes; QA go/no-go | **Go for Feb 1** |
| Feb–Apr 2027 | Field season: 5–10 farms; fixes only, no new features | Minutes/plan + diff per plan |
| May 2027+ | Phase 4 decision (farmer portal, §8) | CLAUDE.md change by Farjad Iranmehr |

Critical path: Farjad Iranmehr's 5 real wheat cases and constants (`docs/agronomist-todo.md` #1–#5). Needed by **Dec 18** to replace samples in January; without them the tool ships with PLACEHOLDER numbers and every plan is hand-entered by him.

## 7. Risks
| Risk | Mitigation |
|---|---|
| No RLS → one missed `org_id` filter leaks data | Single data-access module; tests per query with two orgs; DB grants as second line |
| Auth is ours to secure (ADR 0005 option A) | argon2 hashes, server-side sessions, CSRF on HTMX posts, login rate limit, accounts created by CLI only, optional TOTP; security review in Step 7 |
| PostGIS image is self-managed | Railway volume backups; documented restore in runbook |
| Railway has no Canadian region | Recorded in ADR 0004; revisit before real farmer data from Canada if residency is required |
| Real cases late | Ship with placeholders clearly labelled; agronomist overrides every number (diff still recorded) |
| Shared migrations with website | One runner, one `schema_migrations`; coordinate the switch with the `cp-website` session in Step 4 |

## 8. Farmer portal (Phase 4 — plan only)
Not built in v1. CLAUDE.md says a Next.js farmer app later. Minimum shape when it opens: farmer signs in, sees only approved recommendations for their farms, downloads the proof PDF (SHA-256 shown), logs application (planned vs actual). Reuses the same database, org/membership model and auth identities (ADR 0005 keeps identity in our `app_user` table so a later OIDC provider can be added). Owners then: global `cto` + `product-designer`.

## 9. Decisions (Farjad Iranmehr, 2026-11-16)
1. Plan approved.
2. ADR 0005 accepted: A1 (app-owned auth) + B1 (Railway Bucket).
3. PostGIS: create a Postgres service from the official `postgis/postgis` image with a volume now; move the website's pilot-request table into it; coordinate with the `cp-website` session first. Ask before deleting the old Postgres service.
4. No old Rootwise MVP code → Step 1 audit skipped; ADR 0001 records "start fresh".
5. Date for the 5 real wheat cases: open — ask at Step 3.
