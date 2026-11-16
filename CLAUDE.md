# CLAUDE.md — CloverProof (formerly Rootwise)

## What this repo is
CloverProof turns farm data (field + soil test, or no test) into a complete, field-specific fertilizer decision (what, how much, when, why) plus a proof PDF. Vendor-neutral. Software only. Global core + country packs.

## Current goal (master calendar S1–S30, Nov 16, 2026 → Jan 28, 2028)
The backend plan's 30 two-week sprints are the master calendar (`docs/plans/backend-plan.md` §15, decision D3).

- **Phase A — Concierge readiness, S1–S5 (Nov 16, 2026 → Jan 29, 2027).** Build the INTERNAL concierge tool for the reviewing agronomist. Until a human agronomist is named, the reviewer is the AI agent `cp-agronomist` (`ai_reviewed` only, rule 11); no plan reaches a real farmer without approval by a human agronomist (rule 8). **Concierge gate: end of S5, Jan 29, 2027.**
- **Phase B — Concierge in operation + MVP build, S6–S12 (Feb 1 → May 7, 2027).** Plans for 5–10 real farms in Feb–Apr 2027; farmer & advisor accounts from S9. **MVP gate: end of S12, May 7, 2027.**
- **Phase C — Pilot season, S13–S24 (May 10 → Oct 29, 2027).** Stability over features.
- **Phase D — Launch v1 prep, S25–S30 (Nov 1, 2027 → Jan 28, 2028).**

Reviewing agronomist: `cp-agronomist` (AI) stands in for review work until a human agronomist is named (rule 11). A human agronomist must be named before the S5 concierge gate; until then, real-farm plans stay `in_review`.

Every plan must record: the engine output AND the human agronomist's final numbers + reason. That difference is our calibration dataset. Never lose it.

## Hard rules (do not break)
1. Software only. No hardware, no sensor code.
2. Every recommendation shows a confidence level: `high` / `medium` / `low` (enum, rule-based).
3. Without a soil test: recommend N only (max `medium` confidence). For P/K, recommend a test.
4. Recommendations are IMMUTABLE. An edit creates a new version (`parent_id` + `reason`). Reviews and proof documents are append-only too. Immutability is enforced in the database (grants + triggers), not only in app code.
5. Every recommendation stores: input snapshot, engine version, country-pack version, and the version/retrieval date of every data source used (e.g. soil-estimate cache, weather).
6. Country pack = versioned config + golden tests. Never fork code per country.
7. Internal canonical units: kg/ha, mg/kg, °C, mm; elemental form tracked explicitly. Always store P/K form (P vs P2O5, K vs K2O) on every nutrient line and the soil-test extraction method (Olsen / Bray-1 / Mehlich-3 / other), sampling depth and date. Convert only at display.
8. No number goes to a farmer without approval by a **human** user who either holds the `agronomist` role in that recommendation's organisation or is `superadmin` (decision 2026-11-16), checked in the service layer AND the database. AI/service accounts can never approve (rule 11). Approvals are labelled by kind: `agronomist_approved` (human agronomist) or `superadmin_approved` (human superadmin without the agronomist role); only `agronomist_approved` feeds the calibration dataset and the agreement gate. Any farm not flagged as synthetic test data is a real farm.
9. Never invent agronomic constants. If a value is missing, use a clearly labelled `PLACEHOLDER` and add a `TODO(agronomist)` to validate. A constant taken from a published source or proposed by `cp-agronomist` stays `PLACEHOLDER` (with its citation) until a human agronomist validates it.
10. No secrets in git. Use `.env` (and `.env.example` with empty values).
11. **AI agronomist.** `cp-agronomist` is an AI agent. Its sign-off is `ai_reviewed` only — never `agronomist_approved`, never the review gate (rule 8), never counted toward the 90 % agreement gate or the calibration dataset. It may review engine logic and wording, research published methods, draft `external_reference` golden cases entered by hand from official documents (never scraped), and propose cited constants (rule 9). Real-farm plans stay `in_review` until a human agronomist approves them.
12. **AI agronomist data boundary (D-7).** `cp-agronomist` never receives real pilot farmers' personal data or identifiable farm data — only published sources, synthetic cases or de-identified cases. Changing this needs a DPA with the AI provider and a privacy-notice disclosure, both approved by Farjad Iranmehr.

## Stack
- **Hosting + database:** Railway (ADR 0004). Postgres service from the official `postgis/postgis` image (PostGIS available); server-only DB access. Older docs that say "Supabase" read as: Railway Postgres + PostGIS / app-owned sessions / Railway Bucket.
- **Auth + files:** app-owned auth in FastAPI (argon2id, server-side sessions, CSRF on every POST, accounts created by CLI, no self sign-up) and a private Railway Bucket for proof PDFs and uploads (ADR 0005). MFA **required** for `agronomist`, `staff`, `superadmin` by S5.
- **Access control:** org scoping in one data-access layer **plus Postgres RLS** as defence in depth. Per transaction the app sets `SET LOCAL app.user_id`, `app.org_id`, `app.platform_role` from the server-side session; the app connects as a non-bypass role (`cp_app`: no `BYPASSRLS`, not table owner). Deny by default. ADR 0008 (pending). (ADR 0006 = SoilGrids offline cache; ADR 0007 = DB privileges.)
- **Migrations:** plain SQL in `db/migrations/`, forward-only, one runner, one `schema_migrations`. Never edit an applied migration.
- **Engine:** pure Python package (`engine/`), no I/O, no DB calls, no network. Fully unit-tested. Scope: real Ontario winter wheat pack + product matching + splits (S2); P/K with soil test, extraction-method-aware (S3); no-test estimate from an offline SoilGrids cache, N only, max `medium` (S3); GDD-based timing windows (S4). External data reaches the engine as inputs prepared by `data_sources/`. All constants `PLACEHOLDER` until a human agronomist validates them.
- **Internal tool:** one Python service — FastAPI + Jinja2 + HTMX (`app/`). English only.
- **Background jobs:** Procrastinate worker (Postgres-backed queue, no Redis) from S4: proof render, weather fetch, timing refresh.
- **PDF:** HTML templates → WeasyPrint (`app/pdf/`), SHA-256 hash stored per document; stored write-once in the Bucket.
- **Weather + timing (from S4):** NASA POWER daily fetch job cached by grid cell in `weather_daily` (retrieval date recorded); GDD timing windows shown with basis and last refresh. NASA POWER's licence is unknown: internal use only, nothing farmer-facing until the lawyer review in S8. Forecast provider: decision + licence in S8 before any farmer-facing forecast.
- **Observability:** Sentry free tier allowed; any paid tier needs Farjad Iranmehr's go.
- **Launch market + residency:** Canada — Ontario winter wheat (Prairie wheat backup). **Real farmer data must be stored in Canada** (decision 2026-11-16). Railway has no Canadian region, so production hosting for farmer data needs a Canadian-region option decided in an ADR before any real farmer data (owner: `cto` + `devops-engineer`, with `ciso`). Until then only synthetic or de-identified data in hosted environments.
- **Farmer & advisor accounts:** from S9 (feature-flagged); farmers see only approved plans. Front end: **FastAPI-served pages + the `/api/v1` API** (decision 2026-11-16) — no separate Next.js farmer app. Mobile-friendly; language/unit preferences arrive with S9.
- **Mobile:** Phases B/C use mobile-friendly web (application log S10). `head-of-mobile` plans the native app from S11 (stack ADR, offline sync, API auth); build starts after the MVP gate (S12), scheduled by the CPO.
- **Languages:** multi-language applies to the public website (ADR 0003); the internal tool stays English. Farmer-facing language/unit preferences arrive with S9, decided with the farmer-portal ADR.

### Scope by sprint (nothing before its sprint)
| Capability | From | Notes |
|---|---|---|
| Weather (NASA POWER daily) + GDD timing | S4 | Thresholds `PLACEHOLDER` until validated |
| Soil-report file upload + manual "confirm values" | S4 | No OCR; human transcription |
| Forecast provider | S8 (decision) | Commercial licence + ADR first |
| Farmer & advisor accounts, access grants | S9 | Behind feature flags |
| Application log (mobile-friendly web) | S10 | |
| Proof share links + public verify | S11 | |
| Map drawing / boundary upload | S18 | Boundary pre-fill spike S19, behind flag |
| OCR/LLM soil-report extraction | S20 (spike), S21 (v1 only if accuracy target met) | Human confirm mandatory |
| Billing / payments | S26 | Paid service → Farjad Iranmehr's go |
| Native mobile app | Plan S11, build S13+ | `head-of-mobile` |

**Out of scope (no sprint):** hardware, sensors, IoT; Sentinel-2; variable-rate / zone maps; carbon reporting; fertilizer price comparison or commissions.

## Data rules (approved by Farjad Iranmehr, 2026-11-16; source of truth: `docs/data-sources.md`)
- No live SoilGrids REST calls at runtime; use the cached layer only (ADR 0006).
- No GPL/EUPL code copied or imported into production without an ADR + lawyer approval (e.g. PCSE/WOFOST, farmOS — concepts only).
- WoSIS: the per-profile licence filter is mandatory (commercially usable profiles only).
- LUCAS raw values never leave the backend: no export, no PDF table of raw LUCAS points. EU only.
- Every estimated soil value stores: source, source version, resolution, depth, retrieval date.
- External tools (e.g. Ontario AgriSuite) are references only, never scraped; reference cases are entered by hand by a human.
- Unknown licences are never assumed; anything "unknown" in `docs/data-sources.md` stays out of production.

## Build order (Farjad Iranmehr, 2026-11-16)
Website (`website/`, Next.js, 8 locales, en first) → web app portal (internal concierge tool to the S5 gate, then farmer & advisor portal S9–S12) → mobile app (native planning S11, build after S12). One step at a time; each step is planned and approved before code. Plans: `docs/plans/website-v1.md`, `docs/plans/webapp-v1.md`, `docs/plans/backend-plan.md` read through `docs/plans/backend-plan-reconciliation.md` (the reconciliation wins on conflict).

## Repo layout
```
engine/                 pure calculation library
  cloverproof_engine/
    models.py           input/output dataclasses (pydantic)
    methods/            pluggable nutrient methods (interface + implementations)
    confidence.py       rule-based confidence
    explain.py          plain-language reason for every number
    units.py            conversions (P<->P2O5, K<->K2O, lb/ac<->kg/ha)
  tests/
    golden/             golden cases (YAML: input -> expected), kind: agronomist_approved | external_reference
packs/
  placeholder/v0.yaml   NOT real agronomy; labelled placeholder
  <pack-id>/vN.yaml     real packs (Ontario winter wheat from S2), constants PLACEHOLDER until validated
data_sources/           SoilGrids offline cache, weather clients (I/O lives here, never in engine/)
db/
  migrations/           SQL migrations, forward-only (single source; website/db/migrations/ is legacy)
  seeds/
app/                    FastAPI internal tool (+ jobs/, pdf/ templates)
docs/
  adr/                  architecture decision records (one file per decision)
  plans/                website, web app, backend plan + reconciliation + traceability
  sprints/              sprint plans and kickoff prompts
  product/              PRDs and drafts
```

## Data model (core)
- organisation ↔ farmer (many-to-many via `membership` with role); farmer-revocable `access_grant` for advisors/orgs (S2 model, S9 UI)
- farmer → farm → field → field_geometry_version (per season)
- field → soil_test (date, depth, method, units, form, lab, source: `lab` | `estimate`); estimates keep source, version, resolution, depth, retrieved_at
- season → crop_plan → recommendation (immutable, `parent_id`, versions, inputs snapshot) → `recommendation_line` (per nutrient, explicit form, product, split, timing window)
- recommendation → review (approve / edit / reject + reason, reviewer, `minutes_spent`, `review_kind`: `agronomist_approved` | `ai_reviewed`)
- crop_plan → application_log (planned vs actual)
- recommendation → proof_document (pdf path, sha256, created_at)
- `audit_event` for approvals, grants, exports, deletions, admin and support actions
- Target model: `docs/plans/backend-plan.md` §6; gaps are closed with forward-only migrations after `cp-database`'s gap analysis.

## Key metric for the internal tool
Agronomist minutes per plan. Record it on every review. Report human-approved and `ai_reviewed` reviews separately; only human reviews feed the calibration dataset and the agreement gate.

## How to work in this repo
- Start every non-trivial task in plan mode. Show the plan before writing code.
- Small commits, one concern each. Run tests before every commit.
- Engine changes: write/extend a golden test first, then code.
- Write an ADR in `docs/adr/` for any stack or data-model decision.
- Never edit an applied migration; add a new forward-only one.
- Ask before: deleting files, adding a paid service or paid tier (including a new Railway service, Sentry paid, Stripe).
- Licences: no GPL/AGPL/EUPL dependencies. LGPL is allowed only by name — `psycopg` and libvips (via Next.js `sharp`) — pending an ADR and lawyer review; any other LGPL dependency needs that ADR first. NASA POWER: not farmer-facing until the lawyer review in S8.
- Keep code and comments in English.

## Design
UI source: Google Stitch project https://stitch.google.com/projects/16684636636144399285. Brand: #4C610B, #A7B58A, #FAF6EB, #273125.

## Agent team
Farjad Iranmehr talks to **`product-manager`** (CPO / VP Product) in a Claude desktop chat. The CPO briefs the group heads (`cto`, `head-of-mobile`, `cro`, `coo`, `head-of-data`, `cso`, `ciso`); heads brief specialists; every head reports to `documentation-manager` (Notion). `cp-agronomist` is the AI agronomy specialist (`ai_reviewed` only, rule 11). `head-of-mobile` plans the native app from S11. Full roster and cascade: `docs/org.md`. Project agents in `.claude/agents/` override global ones with the same name.
