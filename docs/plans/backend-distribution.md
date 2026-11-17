# Backend plan — S1–S3 distribution (now → Jan 1, 2027)

Owner: `cto` for `product-manager` (CPO). Date: 2026-11-16.
Source: `docs/plans/backend-traceability.md` (matrix IDs below). Each brief lists exactly the matrix IDs the group head owns in S1–S3 (status ≠ done), with exit criteria and tests. Rows shared between groups appear under the lead owner and are marked "with" in the other brief.

Window: **S1** Nov 16–27 · **S2** Nov 30–Dec 11 · **S3** Dec 14–Jan 1 (50 %; no deploys Dec 25–Jan 3, so S3 code merges by **Dec 23**).
Rules for every brief: CLAUDE.md hard rules; reconciliation D1–D4 / R1–R9; roadmap test gates + learning loop (sprint review, retro in `docs/sprints/S<n>-retro.md`, standard report to `documentation`); branches/worktrees only; `release-manager` alone pushes and merges; nothing to `main`, Railway, DNS, billing or outside people without Farjad Iranmehr's go.

---

## 0. Decisions needed from Farjad Iranmehr before or during S2 (IDs owned by FI)

| ID | Decision | Needed by | Blocks |
|---|---|---|---|
| OQ-04 | Who is the **human agronomist** (is it Farjad Iranmehr himself, as CLAUDE.md says?), hours Feb–Apr, credentials in Ontario | Dec 11 (latest Jan 15) | S02-DoD, S05-4, REC-D4 wording, calibration dataset |
| OQ-03 / SP-02 | Real weekly capacity for reviews/approvals; second developer? | Nov 27 | Sprint load (RK-X12) |
| AR-03 (with cto) | Create the Railway PostGIS service (agents are denied) per `docs/runbook-db-switch.md`; approve Railway Bucket, worker service and a `staging` environment (usage cost) | Dec 4 | EV-02, AR-05, AR-12, NB-WEB-04 |
| OQ-06 / SC-08 / AR-17 / REC-R4 | Data residency: Railway (US) acceptable for Ontario farm data, or not | Dec 23 | Real farm data in S5 |
| OQ-07 | Who drafts legal disclaimer + terms; lawyer yes/no | Dec 23 | PD-05, SC-07, S11-3 |
| REC-CL | Approve CLAUDE.md update (weather, farmer accounts, maps, extraction, payments, RLS, Railway, AI agronomist) — CPO drafts | Dec 11 | S04-1 (weather) and later |
| REC-R9 | Provide `05-mvp-build-brief.md`, `03-roadmap-and-validation.md` (or say they are retired) | Dec 11 | — |

---

## 1. `cto` — Engineering (web app, platform, website)

Run through `cloverproof-lead` for the cp-* chain and `cp-website` for `website/`. One worktree per workstream; file sets are disjoint as listed.

### 1A. Close S1 (cp-concierge-app + ciso) — by Nov 27
IDs: S01-G, S01-6, AR-01, AR-04, AR-20, AR-23, AR-24, AR-26, AR-30, EV-01, PM-OM-oa, PM-OM-ag, REC-R8 (with ciso), GL-01, GL-11, HC-01.
- Exit: #7 fixes every CISO MUST/SHOULD-FIX (R8: A1, S1–S8), CISO re-review "accept", then `release-manager` merges #7. Views stay in `web.py`/`plan_web.py`/`account.py` for now (AR-23/AR-24 restructure when `/api/v1` starts; record as decision).
- Tests: `make test` + `make db-test` green in CI; `API` tests for owner-only `/admin/users` (denied for agronomist); `SR` sign-off.

### 1B. Data model gap + RLS (cp-database; system-architect for the ADR) — S1 → S2
IDs: REC-R1, REC-D1, REC-R2, REC-D4 (DB part), S01-3, S01-4, S02-2, AR-08, AR-10, AR-11, HC-08, RO-02, RO-03, RO-06, RO-07, U3a, U5, DM-C3, DM-C4, DM-C5, DM-01, DM-02, DM-03, DM-04, DM-05, DM-06, DM-07, DM-08, DM-09, DM-10, DM-11 (with cp-engine), DM-13, DM-14, DM-15, DM-17 (with app), DM-19, DM-24 (with 1C), DM-27, DM-R1, DM-R2, DM-R4, DM-R5, SC-02 (with ciso), SC-06, DD-02, DD-03, PM-GR, PM-FF-oa, PM-FF-ag, PM-FF-sa, PM-ST-oa, PM-ST-ag, PM-ST-sa, PM-RQ-sa, PM-DR-fa, PM-DR-ad, PM-DR-oa, PM-DR-sa, PM-AP-ag, PM-AP-sa, PM-VP-oa, PM-VP-sa; S3: DM-12, XD-08, HC-03 (data-source versions).
- Order: (1) `docs/engineering/schema-gap-analysis.md` — §6 vs mig 0001–0010, one line per DM row, with the proposals for RK-X4 (status as a derived view), RK-X5 (season vs crop_plan), RK-X7 (grant history), RK-X11 (role mapping, superadmin cannot approve unless human agronomist) → CPO decision by **Nov 27**. (2) ADR 0008 "Postgres RLS on Railway" (SET LOCAL `app.user_id`/`app.org_id`/`app.platform_role`, non-bypass `cp_app`, psycopg kept — AR-10) → ciso review. (3) Forward-only migrations 0011+ (never edit 0001–0010): identity fields + platform role, `access_grant`, `recommendation_line` (replaces the P/K-columns proposal, R2), review `started_at`/`finished_at`, proof `kind`/`template_version`, `audit_event` + triggers, `created_by`/`updated_at`/`deleted_at` gaps, `ai_reviewed` + human-agronomist flag (D4), `fertilizer_product`. (4) RLS v0 on every org-owned table + derived recommendation state.
- Exit (S2, Dec 11): gap analysis approved; ADR 0008 accepted; migrations apply on local PostGIS and (once AR-03 exists) on staging; every new table has an RLS test with an allowed and a denied user; unapproved recommendations invisible to non-agronomists; AI-only reviewer cannot approve (test).
- Tests: `DBT`, `RLS` (two users per policy), `SR` on ADR 0008.

### 1C. Engine + pack (cp-engine + cp-agronomist research, `ai_reviewed` only + cp-agronomy-guard) — S2 → S3
IDs: S02-1, S02-4 (engine matching; catalog table in 1B), S02-5, EN-05, EN-06, HC-07, AR-31, A4 (with 1B, 1D), DM-11 (enum labels), S03-1, S03-2, S03-3, S03-DoD (with QA), U7, XD-02, AR-19, RK-04, RK-06, HC-06.
- Exit S2: Ontario winter wheat pack `packs/ca-on/` v1 — method structure from published Ontario sources entered by hand, **every constant PLACEHOLDER with source + `TODO(agronomist)`**; golden cases gain `kind: agronomist_approved | external_reference` and a reviewer label (`ai_reviewed` for cp-agronomist cases); git SHA stored with engine version; splits per line; product matching need → product → quantity behind guard review.
- Exit S3: SoilGrids offline cache (Ontario bbox, no runtime calls) + no-test path N-only `medium` max; P/K only with a lab test, method-aware, PLACEHOLDER critical values; conversions used on display.
- Tests: `UT`, `GT` (golden report in CI), `GRD` sign-off on every PR that computes a number; a no-network test for the cache.
- If S2 runs over: product matching (S02-4 engine part) moves to S3 (RK-X12). Never cut guard review.

### 1D. Concierge app (cp-concierge-app + CPO/product-designer for screens) — S2 → S3
IDs: A1, HV-06, HV-07, HV-11, RV-01, RV-02, RV-03, RV-04, RV-05, EN-02, EN-03, DM-17, AC-07, U2, U4, U9, PM-RQ-sf, PM-AP-ag (app part), S02-3, UA-28 (S3), SC-04, OB-03.
- Exit S2: review queue page (sort by due date, filter) + side-by-side engine vs edit diff; persisted review start/finish; edit → new version (+ approve per RV-04); approve on a real farm blocked unless the user is a human agronomist (D4); double-submit guard on create POSTs; recommendation service reads confirmed DB inputs and the active pack (EN-02); product catalog v0 page; staff role denied plan creation.
- Exit S3: HSTS + `/readyz`; soil-estimate shown with source + `low` confidence.
- Tests: `API` route tests (allowed/denied), `E2E` by cp-qa, `GRD` on number display.

### 1E. Proof PDF (cp-pdf + devops-engineer for the bucket) — S2 (slipped from S1)
IDs: S01-7, AR-13, AR-28, U11a, UA-36, UA-37, HV-08, PD-01, PD-02, PD-03, PD-05 (with coo), PD-06, PM-PX-ag, HC-10, AR-05, SC-05 (S3).
- Exit S2: PDF v0 from approved recommendations only; WeasyPrint, brand colours, English; SHA-256 of final bytes in `proof_document`; storage key per ADR 0005 (DB-enforced) via `ProofStore` (filesystem locally, Railway Bucket once approved); preview page; wording has no third-party acceptance and does **not** say "reviewed by an agronomist" for AI-only reviews.
- Exit S3: bucket private, signed URLs ≤ 15 min, re-hash on download.
- Tests: `UT` (hash stable, re-generation creates a new row), `GRD` + `LR` on wording, `E2E`.

### 1F. Platform + environments (cp-platform, devops-engineer) — S2 → S3
IDs: AR-03 (with FI), AR-15, EV-02, EV-04, EV-05, OB-06, XD-07, DD-05, DD-06, SC-03 (with ciso).
- Exit S2: CI adds mypy (engine + services), coverage report (targets engine ≥ 90 %, services ≥ 75 %), licence check (no GPL/EUPL), merges ciso's `security.yml`/Dependabot; secret-rotation procedure in `docs/runbook-webapp.md`.
- Exit S3 (by Dec 23): Railway `staging` with app + PostGIS + bucket, migrations applied by CI to staging, manual approval for production; app deployed to staging; demo on staging.
- Tests: `CI`, `LIVE`, `RST` plan drafted (restore test is S5).

### 1G. QA (cp-qa) — every sprint end
IDs: S01-DoD, S02-DoD (with FI), S03-DoD, AR-35, OB-05, DM-R5 (with 1B), DD-02 (with 1B).
- Exit: written test plan per sprint from the exit criteria above; S1: 5 sample plans end to end (local) with delta + minutes recorded; S2: 5 published-reference cases run by cp-agronomist (`ai_reviewed`) + 1 full PDF; human-sign-off item stays open until OQ-04; S3: same field with/without soil test shows correct confidence and P/K "test recommended", on staging. `tests/rls` and a staging smoke test exist.
- Tests: `E2E`, `RLS`, `LIVE`; go/no-go note per sprint.

### 1H. Website (cp-website)
IDs: NB-WEB-02, NB-WEB-03, NB-WEB-04 (with cp-database + FI), NB-WEB-05 (with coo), NB-WEB-06 (with cp-database; needs CPO decision on cro's proposal).
- Exit S2: SEO/Lighthouse/a11y work merged to `main` via release-manager; raw pg error no longer logged; DB switch done after AR-03 + least-privilege website role. Exit S3: privacy page copy (after FI approval of legal entity/contact) and first-party funnel events if approved.
- Tests: build, 375 px, Lighthouse ≥ 90, a11y; `LIVE`.

### Standing (all sprints)
GL-06..GL-09 held (no hardware, VRA, carbon, price/commission), DD-01, RK-06, HC-10 — every PR.

---

## 2. `ciso` — Security
IDs: REC-R8, NB-SEC-01, SC-11, NB-SEC-02, NB-SEC-04; with cto: SC-02, SC-03, REC-D1, XD-07, DD-06.
- Exit S2: S2 security branch pushed + PR (release-manager); #7 re-reviewed after fixes; least-privilege website DB role spec for the DB switch; ADR 0008 RLS reviewed (bypass paths, `SET LOCAL` leakage across pooled connections, superadmin, AI-agronomist account).
- Exit S3: RLS test suite reviewed; residency + Railway DPA recommendation to FI (with coo); backup/restore test plan for S5.
- Tests: `SR`, CI security jobs green on `main`.

## 3. `coo` — Operations, legal, privacy
IDs: NB-OPS-01, NB-OPS-02, NB-OPS-03, SC-07; with cto: PD-05 (PDF wording), NB-WEB-05; with ciso: NB-SEC-04.
- Exit S2: S2 ops drafts pushed + PR; privacy notice/terms/consent ready for FI + lawyer decision (OQ-07); PDF wording reviewed (no acceptance claims, AI vs human review wording).
- Exit S3: agronomist credentials/liability note for Ontario (OQ-04); workload model in minutes per plan; erasure-vs-immutability requirements to cp-database (NB-OPS-06, design due S4).
- Tests: `LR`, `DR`. Nothing sent, signed or filed.

## 4. `head-of-data` — Data & calibration
IDs: NB-DAT-01, NB-DAT-02, AR-33, XD-01, XD-04, S02-6, RK-05, NB-DAT-03; with cto: DM-16 (per-line calibration view), U7/XD-02 (data-engineer for the SoilGrids cache).
- Exit S2: #5 merged after CPO review; `docs/data-sources.md` (SoilGrids, NASA POWER, WoSIS licence filter, LUCAS later) with licences and attribution; per-line calibration delta spec handed to cp-database; metric definitions include `ai_reviewed` vs human-approved split (D4: AI reviews never count toward the 90 % agreement gate).
- Exit S3: calibration baseline method ready; baseline numbers only when human-approved cases exist (OQ-04).
- Tests: `DR`, `LR` on licences.

## 5. `cro` — Growth
IDs: NB-GRO-01, NB-GRO-02 (prep for NB-GRO-03 in S4).
- Exit S2: S2 growth drafts pushed + PR; funnel-tracking proposal decided by CPO.
- Exit S3: outreach drafts + partner shortlist (labs, agronomy firms, co-ops in Ontario), not sent; plan to confirm 5–10 farms by Jan 15.
- Tests: `DR`; no claims of third-party acceptance (`GRD` on copy).

## 6. `cso` — Strategy
IDs: NB-STR-01, RK-08.
- Exit S3: positioning one-pager + competitor scan including free Ontario tools (e.g. AgriSuite) and why proof/log/workflow wins; no endorsement claims.
- Tests: `DR`.

## 7. `head-of-mobile` — Mobile
IDs: none open in S1–S3 (NB-MOB-01 held: no build until D2 schedule).
- Optional, read-only: comment on AC-02 (API auth for a native client) when ADR 0008 is drafted. First real work S11 (NB-MOB-02).

## 8. CPO product team (`product-manager` directly)
IDs: REC-D3, REC-R5, REC-CL (draft for FI), DR-01, DR-02, DR-03, AR-34, NB-PRD-01, NB-PRD-02, RK-02 (with coo + head-of-data).
- Exit S2: `docs/backlog.md` with S2–S3 stories (Given/When/Then, data-model + permission impact per DoR) by `agile-manager`; review-queue + diff screens by `product-designer` + `cp-design`; `webapp-v1.md` §2 scope note updated per R5; CLAUDE.md change drafted for FI.
- Decisions the CPO owes cto by Nov 27: RK-X4, RK-X5, RK-X7, RK-X11 (from the gap analysis), RK-X8/RK-X9 (season and holiday freeze rules).

## 9. `documentation-manager`
IDs: NB-DOC-01 (S1), NB-DOC-02 (every sprint).
- Exit S1: D1–D4, R1–R9, the matrix and this distribution in Notion (decision log + open items). Every sprint: standard reports filed.

---

## Coverage check
Every non-done matrix row with a target in S1–S3 appears above: cto 153 IDs (sections 1A–1H + standing), FI 10, CPO 9, head-of-data 8, ciso 5, coo 4, cro 2, cso 2, documentation-manager 1 — total **194**. head-of-mobile 0.
