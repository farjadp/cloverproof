# CLAUDE.md — proposed update (matrix REC-CL)

- **Status: DRAFT — needs Farjad Iranmehr's approval (needed by Dec 11, 2026, end of S2; blocks S4 weather work).** Nothing here is in force until Farjad Iranmehr approves it and `CLAUDE.md` is edited. This file does not change `CLAUDE.md`.
- Author: `cp-product-manager` for `product-manager` (CPO). Date: 2026-11-16.
- Sources: `CLAUDE.md` (current); `docs/plans/backend-plan-reconciliation.md` (D1–D4, R1–R9 — wins over the plan); `docs/plans/backend-plan.md` v1.0 (§1, §2, §4, §5, §10–§15); `docs/plans/backend-traceability.md` (rows REC-D1…REC-CL, GL-10, GL-11, HC-01, HC-09, PM-AP-sa, AC-02, JB-03, S04-1, S09-1, S18-1, U6c, NB-MOB-01…03, RK-X1, RK-X2); `docs/plans/webapp-v1.md` (§2, §3, §5, §8); ADR 0002, 0004, 0005; `docs/runbook-db-switch.md`; `docs/org.md`; `.claude/agents/cp-agronomist.md`.
- Repo evidence (migrations path): `git ls-tree -r --name-only origin/main | grep migrations` → `db/migrations/0001…0009` (root, Python runner, includes `0001_pilot_request.sql`) **and** a legacy `website/db/migrations/0001_pilot_request.sql` still run by the website's `npm run db:migrate`. `webapp-v1.md` §3 and runbook §4 make `db/migrations/` the single source; the website copy is deleted in a later PR once the website stops migrating (ask-before-delete applies). Proposed path: **`db/migrations/`**.
- Hard rules: all 10 kept; rules 4, 5, 7, 8, 9 strengthened; new rule 11 (AI agronomist) and rule 12 (AI agronomist data boundary, D-7). None weakened.

## 1. Change table

| # | CLAUDE.md section | Current text (quote) | Proposed text (summary; full text in §2) | Reason / decision ID | Takes effect |
|---|---|---|---|---|---|
| 1 | Current goal | "Phase 0–3, until Feb 1, 2027 … He must produce plans for 5–10 farms in Feb–Apr 2027. The farmer-facing app is NOT in scope yet." | Master calendar = backend plan S1–S30 (Nov 16, 2026 → Jan 28, 2028). Phase A concierge readiness S1–S5, **concierge gate S5 (Jan 29, 2027)**; Phase B concierge in operation + MVP build S6–S12, **MVP gate S12 (May 7, 2027)**; Phase C pilot S13–S24; Phase D launch prep S25–S30. Farmer-facing accounts from S9, not before. | D3; REC-D3; backend-plan §1.1, §15 | Now (S2) |
| 2 | Current goal | "Build the INTERNAL concierge tool for our agronomist (Farjad Iranmehr)." | "…for the reviewing agronomist. **Until a human agronomist is named, the reviewer is the AI agent `cp-agronomist`, whose sign-off is `ai_reviewed` only (rule 11). No plan reaches a real farmer without approval by a human agronomist (rule 8).** A human must be named before the S5 concierge gate." Whether Farjad Iranmehr is that human is an open question (Q1). (CPO instruction, 2026-11-16.) | D4; RK-X1; OQ-04 | Now |
| 3 | Hard rule 4 | "Recommendations are IMMUTABLE. An edit creates a new version (`parent_id` + `reason`)." | Adds: reviews and proof documents are append-only too; enforced by DB grants + triggers, not only app code. | Strengthen. backend-plan §2.2; ADR 0002 (immutability triggers + grants) | Now (already true in migrations 0006–0008) |
| 4 | Hard rule 5 | "Every recommendation stores: input snapshot, engine version, country-pack version." | Adds: data-source versions (SoilGrids cache version, weather retrieval date) for any estimate or timing window used. | Strengthen. backend-plan §2.3, §11 | S3 (SoilGrids), S4 (weather) |
| 5 | Hard rule 7 | "Internal canonical units: kg/ha, mg/kg, elemental form tracked explicitly…" | Adds °C and mm (weather); nutrient rates stored per line (`recommendation_line`) with explicit form; convert only at display. | Strengthen. backend-plan §2.6; R2 | S2 (`recommendation_line`), S4 (°C, mm) |
| 6 | Hard rule 8 | "No number goes to a farmer without agronomist approval (review gate)." | "…without approval by a **human** user holding the `agronomist` role in that recommendation's organisation, enforced in the service layer and the database. No other role (incl. `superadmin`) can approve unless that user is also a human agronomist. Any farm not flagged as synthetic test data counts as a real farm." | Strengthen. D4; HC-01; GL-11; PM-AP-sa (CPO to confirm, Q2); ADR 0005 | S2 (REC-D4 schema + app) |
| 7 | Hard rule 9 | "Never invent agronomic constants. If a value is missing, use a clearly labelled `PLACEHOLDER` and add a `TODO(agronomist)` to validate." | Adds: a constant from a published source or proposed by `cp-agronomist` stays `PLACEHOLDER` (with its citation) until a human agronomist validates it. Applies to the Ontario winter wheat pack, P/K critical values and GDD thresholds. | Strengthen. D4; R5; S04-1 | Now |
| 8 | Hard rules (new 11) | — (none) | **New rule 11 — AI agronomist.** `cp-agronomist` is AI. Its sign-off is `ai_reviewed` only; never `agronomist_approved`, never the review gate, never counted toward the 90 % agreement gate or the calibration dataset. Real-farm plans stay `in_review` until a human agronomist approves. | D4 (reconciliation "AI agronomist rule"); REC-D4; EN-05 | Now (rule); S2 (`ai_reviewed` label in DB/app) |
| 9 | Stack — Hosting + database | "Railway (ADR 0004). Railway Postgres; server-only DB access. Auth/storage for the web app decided in its own ADR. (Supabase was the original choice.)" | Railway (ADR 0004) with a Postgres service from the official `postgis/postgis` image (PostGIS available); server-only DB access. Remove the Supabase sentence; any "Supabase" in older docs reads as Railway Postgres + PostGIS / app-owned sessions / Railway Bucket. | ADR 0004; D1; webapp-v1 §5, §9.3; runbook-db-switch | Now (PostGIS service: runbook, S1–S2) |
| 10 | Stack — Auth + files (new line) | — ("decided in its own ADR") | App-owned auth in FastAPI (argon2id, server-side sessions, CSRF, CLI-created accounts) + Railway Bucket for proof PDFs and uploads (ADR 0005). **MFA required** for `agronomist`, `staff`, `superadmin` by S5. | ADR 0005 (A1 + B1); R3; SC-01; REC-R3 | Now; MFA by S5 |
| 11 | Stack — Access control (new line) | — (ADR 0004: "Access control is enforced in application code … not by RLS") | Org scoping in the data-access layer **plus Postgres RLS on Railway** as defence in depth: per transaction the app sets `SET LOCAL app.user_id / app.org_id / app.platform_role` from the server-side session; the app connects as a non-bypass role (`cp_app`, no `BYPASSRLS`, not owner). ADR 0006 pending; partly supersedes ADR 0002/0004 "no RLS". | D1; REC-D1; AR-11; DM-R1; NB-SEC-02 | S2 (ADR 0006 + RLS v0), S9 (grants) |
| 12 | Stack — Migrations (new line) + Repo layout | "`website/db/migrations/  SQL migrations (moves to a shared location when the web app arrives)`" | `db/migrations/` at repo root: plain SQL, **forward-only**, one runner, one `schema_migrations`; never edit an applied migration. `website/db/migrations/` is legacy, removed after the website switch (runbook §4). | ADR 0004 consequence; webapp-v1 §3; R1; backend-plan §14; `origin/main` tree | Now |
| 13 | Stack — Engine | "pure Python package (`engine/`), no I/O, no DB calls. Fully unit-tested." | Same purity rule, plus scope: real Ontario winter wheat pack + products + splits (S2), P/K with soil test, method-aware (S3), no-test estimate from an offline SoilGrids cache, N only (S3), GDD timing windows (S4). External data enters as inputs via `data_sources/`; the engine never fetches. All constants `PLACEHOLDER` until a human agronomist validates. | R5; REC-R5; R4 (Ontario winter wheat, Prairie wheat backup); backend-plan §8, §11 | S2–S4 |
| 14 | Stack — Background jobs (new line) | — | Procrastinate (Postgres-backed queue) worker from S4: proof render, NASA POWER fetch, timing refresh. A second Railway service adds cost → needs Farjad Iranmehr's go (Q5). | backend-plan §10, S4; HC-09 | S4 |
| 15 | Stack — Out of scope now | "Out of scope now: OCR/LLM report reading, Sentinel-2, map drawing, weather APIs, payments." | Replaced by a **scope-by-sprint** table: weather (NASA POWER daily fetch + GDD) **S4**; forecast provider decision S8 (commercial licence first); soil-report upload + manual "confirm values" S4 (no OCR); farmer & advisor accounts **S9**; map drawing / boundary upload **S18**; OCR/LLM extraction spike **S20**, v1 S21 only if it meets the accuracy target, human confirm mandatory; billing/payments **S26**. Still out: Sentinel-2, hardware/sensors, variable-rate maps, carbon reporting, price comparison/commissions. | REC-CL; RK-X2; JB-03; S04-1; S09-1; S18-1; U6c; backend-plan §1.2, §5, §15 | Now (table); each item at its sprint |
| 16 | Stack — Next.js farmer app | "Next.js farmer app: LATER (Phase 4). Do not create it now." | "Farmer & advisor accounts from S9 (MVP build). Front-end stack for farmer/advisor pages **not decided** — see open question Q3. Do not create a Next.js app until that decision." | backend-plan §4.2, §7, S9–S10; webapp-v1 §8; ADR 0005 A1 note | Decision by S8 |
| 17 | Stack — Mobile (new line) | — (only build order: "→ mobile app") | Phases B/C: mobile-friendly web (application log S10). `head-of-mobile` plans the native app from S11 (stack ADR, offline sync, API auth); build starts after the MVP gate S12 (S13+), scheduled by the CPO. | D2; REC-D2; GL-10; NB-MOB-01…03; AC-02 | S10, S11, S13+ |
| 18 | Stack — Observability (new line) | — | Sentry free tier allowed; any paid tier needs Farjad Iranmehr's go. | R7; REC-R7 | S5 |
| 19 | Stack — Data residency (new line) | — | Launch: Canada, Ontario winter wheat (Prairie wheat backup). Railway has no Canadian region; residency decision (Canada vs US region) is **open** and needed before real farmer data. | R4; Q6; ADR 0004; REC-R4 | Decision before real farmer data (Q4) |
| 20 | Stack — language line | "Multi-language applies to the public website only (ADR 0003); the internal tool stays English." | Unchanged; adds that farmer-facing language/unit preferences arrive with S9 and are decided with Q3. | ADR 0003; backend-plan S9, S27 | Unchanged now |
| 21 | Build order | "Website (`website/`…) → web app portal (internal concierge tool, then farmer portal) → mobile app. One step at a time… Plan: `docs/plans/website-v1.md`." | Order unchanged. Adds dates (concierge gate S5, farmer portal S9–S12, native app planning S11, build after S12) and the plan files: `website-v1.md`, `webapp-v1.md`, `backend-plan.md` read through `backend-plan-reconciliation.md` (reconciliation wins). | D2; D3 | Now |
| 22 | Repo layout | (tree without `db/`, `data_sources/`, jobs) | Adds `db/migrations/`, `db/seeds/`, `data_sources/` (SoilGrids cache, weather clients), `app/jobs/`, `packs/<pack-id>/` (real pack from S2, still PLACEHOLDER constants); drops `website/db/migrations/` as canonical. | backend-plan §4.3; `origin/main` tree; R5 | Now / as created |
| 23 | Data model | "recommendation → review (approve / edit / reject + reason, reviewer, `minutes_spent`)" etc. | Keeps the core list; adds: target model = backend-plan §6, gaps closed by forward-only migrations (R1); `recommendation_line` per nutrient with explicit form (R2); `access_grant` (farmer-revocable), `audit_event`, `soil_estimate`, `weather_daily`; review records `review_kind` (`agronomist_approved` vs `ai_reviewed`). | R1; R2; REC-D4; DM-05, DM-14 | S2–S4 |
| 24 | Key metric | "Agronomist minutes per plan. Record it on every review." | Adds: report human-approved and `ai_reviewed` separately; only human reviews feed the calibration dataset and the agreement gate. | D4; backend-distribution (metric split) | S2 (record), S5 (calibration dashboard) |
| 25 | How to work | "Ask before: deleting files, changing migrations already applied, adding a paid service." | "Never edit an applied migration (forward-only). Ask before: deleting files, adding a paid service or paid tier (incl. a new Railway service, Bucket usage growth, Sentry paid, Stripe)." | Strengthen. R1; R7; ADR 0005 B1; HC-09 | Now |
| 26 | Agent team | "…heads brief specialists; every head reports to `documentation-manager`…" | Adds one line: `cp-agronomist` is the AI agronomy specialist (`ai_reviewed` only, rule 11); `head-of-mobile` plans native app from S11. | D2; D4; `docs/org.md` | Now |
| 27 | Hard rules — new rule 12 (D-7) | — | "**AI agronomist data boundary (D-7).** `cp-agronomist` never receives real pilot farmers' personal data or identifiable farm data — only published sources, synthetic cases or de-identified cases. Changing this needs a DPA with the AI provider and a privacy-notice disclosure, both approved by Farjad Iranmehr." | D-7 (CPO, 2026-11-16); D4; R4/Q6 | Now |
| 28 | How to work — licences (new line) | — | "Licences: no GPL/AGPL/EUPL dependencies. LGPL is allowed **only by name** — `psycopg` and libvips (via Next.js `sharp`) — pending an ADR and lawyer review; any other LGPL dependency needs that ADR first. NASA POWER's licence is unknown: it may feed internal timing work but nothing farmer-facing until the lawyer review in S8." | CPO, 2026-11-16; EV-05 (licence check); backend-plan §11 | Now (NASA POWER farmer-facing gate: S8) |

Count: **28 changes.**

---

## 2. Full proposed CLAUDE.md (ready to paste after approval)

~~~~markdown
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
8. No number goes to a farmer without approval by a **human** user holding the `agronomist` role in that recommendation's organisation (review gate), checked in the service layer AND the database. No other role (including `superadmin`) can approve unless that user is also a human agronomist. Any farm not flagged as synthetic test data is a real farm.
9. Never invent agronomic constants. If a value is missing, use a clearly labelled `PLACEHOLDER` and add a `TODO(agronomist)` to validate. A constant taken from a published source or proposed by `cp-agronomist` stays `PLACEHOLDER` (with its citation) until a human agronomist validates it.
10. No secrets in git. Use `.env` (and `.env.example` with empty values).
11. **AI agronomist.** `cp-agronomist` is an AI agent. Its sign-off is `ai_reviewed` only — never `agronomist_approved`, never the review gate (rule 8), never counted toward the 90 % agreement gate or the calibration dataset. It may review engine logic and wording, research published methods, draft `external_reference` golden cases entered by hand from official documents (never scraped), and propose cited constants (rule 9). Real-farm plans stay `in_review` until a human agronomist approves them.
12. **AI agronomist data boundary (D-7).** `cp-agronomist` never receives real pilot farmers' personal data or identifiable farm data — only published sources, synthetic cases or de-identified cases. Changing this needs a DPA with the AI provider and a privacy-notice disclosure, both approved by Farjad Iranmehr.

## Stack
- **Hosting + database:** Railway (ADR 0004). Postgres service from the official `postgis/postgis` image (PostGIS available); server-only DB access. Older docs that say "Supabase" read as: Railway Postgres + PostGIS / app-owned sessions / Railway Bucket.
- **Auth + files:** app-owned auth in FastAPI (argon2id, server-side sessions, CSRF on every POST, accounts created by CLI, no self sign-up) and a private Railway Bucket for proof PDFs and uploads (ADR 0005). MFA **required** for `agronomist`, `staff`, `superadmin` by S5.
- **Access control:** org scoping in one data-access layer **plus Postgres RLS** as defence in depth. Per transaction the app sets `SET LOCAL app.user_id`, `app.org_id`, `app.platform_role` from the server-side session; the app connects as a non-bypass role (`cp_app`: no `BYPASSRLS`, not table owner). Deny by default. ADR 0006 (pending).
- **Migrations:** plain SQL in `db/migrations/`, forward-only, one runner, one `schema_migrations`. Never edit an applied migration.
- **Engine:** pure Python package (`engine/`), no I/O, no DB calls, no network. Fully unit-tested. Scope: real Ontario winter wheat pack + product matching + splits (S2); P/K with soil test, extraction-method-aware (S3); no-test estimate from an offline SoilGrids cache, N only, max `medium` (S3); GDD-based timing windows (S4). External data reaches the engine as inputs prepared by `data_sources/`. All constants `PLACEHOLDER` until a human agronomist validates them.
- **Internal tool:** one Python service — FastAPI + Jinja2 + HTMX (`app/`). English only.
- **Background jobs:** Procrastinate worker (Postgres-backed queue, no Redis) from S4: proof render, weather fetch, timing refresh.
- **PDF:** HTML templates → WeasyPrint (`app/pdf/`), SHA-256 hash stored per document; stored write-once in the Bucket.
- **Weather + timing (from S4):** NASA POWER daily fetch job cached by grid cell in `weather_daily` (retrieval date recorded); GDD timing windows shown with basis and last refresh. NASA POWER's licence is unknown: internal use only, nothing farmer-facing until the lawyer review in S8. Forecast provider: decision + licence in S8 before any farmer-facing forecast.
- **Observability:** Sentry free tier allowed; any paid tier needs Farjad Iranmehr's go.
- **Launch market + residency:** Canada — Ontario winter wheat (Prairie wheat backup). Railway has no Canadian region; data residency (Canada vs US region) is OPEN and must be decided before real farmer data.
- **Farmer & advisor accounts:** from S9 (feature-flagged); farmers see only approved plans. Front-end stack for farmer/advisor pages is NOT decided (Next.js vs FastAPI-served pages + API) — do not create a Next.js app until an ADR decides it.
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
~~~~

---

## 3. Open questions for Farjad Iranmehr

1. **Are you the human agronomist of record?** Current CLAUDE.md names you as "our agronomist"; D4 says AI until a human is named. If yes, your account (human, `agronomist` role) can approve real-farm plans now and your reviews feed the calibration dataset. If no, who is named, and by when (latest S4, before the S5 gate)? (RK-X1, OQ-04)
2. **Superadmin approvals.** Proposed rule 8 says `superadmin` can approve only if that user is also a human agronomist (the plan's permission matrix lets superadmin approve). Confirm. (PM-AP-sa)
3. **Farmer/advisor front-end stack (S9).** CLAUDE.md and ADR 0005 assume a Next.js farmer app; the backend plan builds farmer/advisor features as FastAPI API + mobile-friendly pages (S9–S10) and only says "Next.js may come". Which one — and do farmer-facing pages get multiple languages? Needed by S8 (API-auth ADR, AC-02). The draft leaves it undecided.
4. **Data residency.** Canada vs US region for real farmer data (Railway has no Canadian region). Needed before the first real farmer's data enters production. (R4, Q6)
5. **S4 worker service cost.** The Procrastinate worker is a second Railway service (extra monthly cost). Go for S4? (HC-09)
6. **New rule 11 vs folding into rules 8–9.** The draft adds a separate rule 11 and also strengthens 8 and 9. Keep it as a separate rule (recommended: clearer for every agent), or fold it into 8–9?
