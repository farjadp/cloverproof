# Backend plan — traceability matrix

Owner: `cto`. Date: 2026-11-16. Status: v1 for CPO review.
Sources: `docs/plans/backend-plan.md` v1.0 (the **plan**) read through `docs/plans/backend-plan-reconciliation.md` (the **reconciliation**, wins on conflict: D1–D4, R1–R9), `CLAUDE.md`, `docs/org.md`, `docs/sprints/roadmap.md` (test gates + learning loop still apply), `docs/plans/webapp-v1.md`, ADR 0001–0005.
Code state checked on 2026-11-16: `origin/main` @ `1881d78` and open PRs farjadp/cloverproof#5 (data docs), #6 (this plan), #7 (Step 5 app, branch `webapp-step5-app`). Unpushed local branches mentioned in the shared notes (`myca/security-s2-bb8ef7`, `myca/ops-s2-f4aad3`, `myca/growth-s2-a73813`) are **not** on the remote and are not counted as done.

Companion: `docs/plans/backend-distribution.md` (S1–S3 briefs per group head, by matrix ID).

## How to read this

**Columns:** ID · § (plan section) · Requirement (short) · Status · Evidence / gap · Owner (group head / agent) · Sprint (target, S1–S30) · Test required · Depends on.

**Status:** `done` (evidence on `main` or an open PR named) · `partial` (some of it exists; the gap is stated) · `missing` · `superseded` (by the reconciliation; the replacement is stated and tracked in the same row) · for §18 questions `done` = answered, `missing` = still open.
For a non-goal, `done` means "held: nothing of it exists and nothing is planned".

**Evidence shorthands:** `main` = `origin/main` @ `1881d78`. `#7` = farjadp/cloverproof#7 (Step 5 concierge app, open). `#5` = farjadp/cloverproof#5 (data docs, open). `mig 000N` = `db/migrations/000N_*.sql`.

**Owners** (from `docs/org.md`): `cto/cp-engine` (+ `cp-agronomy-guard` review, `cp-agronomist` research, `ai_reviewed` only — D4) · `cto/cp-database` · `cto/cp-concierge-app` · `cto/cp-pdf` · `cto/cp-platform` · `cto/devops-engineer` · `cto/cp-qa` · `cto/cp-website` · `ciso/security-engineer` · `head-of-data/<specialist>` · `coo/<specialist>` · `cro/<specialist>` · `cso/business-strategist` · `head-of-mobile/<specialist>` · `CPO/<agent>` · `documentation-manager` · `release-manager` · **FI** = decision by Farjad Iranmehr.

**Test codes:** `UT` unit · `GT` golden test/report · `DBT` migration + DB test on local PostGIS · `RLS` pytest RLS test, two users (allowed + denied) · `API` httpx route test · `E2E` `cp-qa` walkthrough · `GRD` `cp-agronomy-guard` review · `SR` security review (`ciso`) · `LR` legal review (`coo/legal-compliance-specialist`, not a lawyer) · `DEC` decision recorded (ADR or decision log) · `DR` document review by the CPO · `PERF` measured against a target · `RST` restore test · `LIVE` checked on staging/production.

**Calendar** (D3 — master): S1 Nov 16–27 · S2 Nov 30–Dec 11 · S3 Dec 14–Jan 1 (50 %) · S4 Jan 4–15 · S5 Jan 18–29 (**concierge gate**) · S6 Feb 1–12 · S7 Feb 15–26 · S8 Mar 1–12 · S9 Mar 15–26 · S10 Mar 29–Apr 9 · S11 Apr 12–23 · S12 Apr 26–May 7 (**MVP gate**) · S13–S24 May 10–Oct 22 (pilot, 40 % support) · S25 Nov 1–12 · S26 Nov 15–26 · S27 Nov 29–Dec 10 · S28 Dec 13–31 (50 %) · S29 Jan 3–14 2028 · S30 Jan 17–28 2028.

---

## §1 Goals and non-goals

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| GL-01 | 1.1 | Phase 0–3: internal tool so the agronomist produces plans for 5–10 farms; every plan stores engine output vs agronomist output | partial | Engine v0 (`main` `engine/`), schema + `recommendation_diff` (`main` mig 0006–0009), app flow (#7). No deploy, no PDF, no real pack | cto/cloverproof-lead | S1–S5 | E2E, GT | S01-*, S05-DoD |
| GL-02 | 1.1 | Phase 2 concierge: run real plans, measure minutes/plan, add P/K, no-test mode, timing windows | missing | Minutes recorded per review (`main` mig 0007 `minutes_spent`); real plans need a human agronomist (D4) | cto + head-of-data | S6–S10 | E2E, PERF | OQ-04, S03-*, S04-* |
| GL-03 | 1.1 | Phase 4 MVP/closed beta: farmer + advisor accounts, intermediary dashboard, application log, proof export; 10–20 farms | missing | — | cto | S9–S12 | E2E | S12-DoD |
| GL-04 | 1.1 | Phase 5 pilot season: stability, timing updates, field application logs, outcome capture | missing | — | cto + head-of-data | S13–S24 | E2E | GL-03 |
| GL-05 | 1.1 | Phase 6 launch v1 prep: billing, second country pack, first lab integration, self-serve onboarding | missing | — | cto + cso | S25–S30 | E2E | GL-04 |
| GL-06 | 1.2 | Non-goal: hardware, sensor ingestion, IoT | done | Held; CLAUDE.md rule 1 | cto/cp-agronomy-guard | all | GRD | — |
| GL-07 | 1.2 | Non-goal: variable-rate / zone maps | done | Held | cto | all | DR | — |
| GL-08 | 1.2 | Non-goal: carbon / CSRD reporting | done | Held | cto | all | DR | — |
| GL-09 | 1.2 | Non-goal: fertilizer price comparison or sales commission | done | Held; `fertilizer_product` must have no price/affiliate fields (DM-24) | cto/cp-database | all | DBT | DM-24 |
| GL-10 | 1.2 | Non-goal: native mobile apps | superseded | **D2:** native app stays. Mobile-friendly web in Phase B/C; `head-of-mobile` plans from S11, builds after S12 (NB-MOB-*) | head-of-mobile | S11+ | DEC | REC-D2 |
| GL-11 | 1.2 | Non-goal: automatic recommendations reaching a farmer without agronomist approval | partial | DB trigger: approve needs `agronomist` membership (`main` mig 0007); farmer view not built yet. D4: approval of a real farm must be a **human** agronomist | cto/cp-database + cp-concierge-app | S1, S9 | DBT, API, E2E | HC-01, REC-D4 |

## §2 Hard constraints

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| HC-01 | 2.1 | Review gate: no recommendation visible to a farmer until an agronomist approves | partial | DB approve gate (`main` mig 0007, tests `app/tests/db/test_review_gate.py`). Missing: farmer-facing read path filter (S9), RLS on unapproved rows (DM-R2), human-only approval for real farms (D4) | cto/cp-database + cp-concierge-app | S1→S9 | DBT, RLS, API | DM-R2, REC-D4 |
| HC-02 | 2.2 | Immutability: recommendations, reviews, proof documents append-only; edit = new version | done | Triggers + grants (`main` mig 0006–0008, `test_immutability.py`). Gap: `recommendation_line`, `audit_event`, `access_grant` history not built yet (rows DM-14, DM-27, DM-05) | cto/cp-database | S1 | DBT | — |
| HC-03 | 2.3 | Reproducibility: input snapshot, engine version, pack version, **data-source versions** | partial | `inputs_snapshot`, `engine_version`, `pack_id/version/status/sha256` (`main` mig 0006). Missing: data-source versions (SoilGrids/NASA POWER) and git SHA (EN-06) | cto/cp-database + cp-engine | S3–S4 | DBT, UT | EN-06, XD-08 |
| HC-04 | 2.4 | Confidence on every number, enum high/medium/low, rule-based | done | `engine/cloverproof_engine/confidence.py`, enum `confidence_level` (mig 0006); rules C1–C6 PLACEHOLDER (agronomist-todo #5) | cto/cp-engine | S1 | UT, GT, GRD | — |
| HC-05 | 2.5 | No-test rule: N only, max `medium`; P/K → "test recommended" | done | `engine.py` `_pk_note` `PK_SOIL_TEST_RECOMMENDED`; confidence cap. Must be re-proved when P/K lands (S03-2) | cto/cp-engine + cp-agronomy-guard | S1, S3 | UT, GT, GRD | — |
| HC-06 | 2.6 | Canonical units kg/ha, mg/kg, °C, mm; track P/P2O5, K/K2O, method, depth, date; convert only at display | partial | `units.py`, soil enums (mig 0005). Missing: `canonical_value/unit` on measurements (DM-11), °C/mm (weather), display conversion by unit preference (S09-4) | cto/cp-engine + cp-database | S3, S9 | UT, DBT | DM-11 |
| HC-07 | 2.7 | Country pack = config + tests, never forked code | partial | `packs/placeholder/v0.yaml` + golden. Missing: real pack (S02-1), pack registry (A3) | cto/cp-engine | S2, S4 | GT | — |
| HC-08 | 2.8 | Farmer owns farm data; access via memberships the farmer can revoke | missing | Today a farmer is an org client record (ADR 0002). Needs `access_grant` + farmer-owner model (DM-04, DM-05) | cto/cp-database | S2 (model), S9 (UI) | DBT, RLS | REC-R1 |
| HC-09 | 2.9 | Minimal infra: one Postgres, one Python service, one worker; no extra queue/cache | superseded | **D1:** Railway Postgres + PostGIS (not Supabase). Worker = second Railway service → cost, needs FI go (ST rule "no paid service") | cto/devops-engineer | S4 | DEC, LIVE | REC-D1, AR-12 |
| HC-10 | 2.10 | Honest claims: no text says a bank/inspector "accepts" our proof | partial | Website copy reviewed for this; PDF/email/API text not built yet | cto/cp-pdf + cp-agronomy-guard; coo/legal | S1+ every text | GRD, LR | PD-05 |

## §3 Roles and permissions

### 3.1 Roles

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| RO-01 | 3.1 | Role `farmer` (own farms, approved plans, log, proof, grant/revoke) | partial | `membership_role` has `farmer` (unused, mig 0003); `farmer.app_user_id` link. No farmer login | cto/cp-database + cp-concierge-app | S9 | RLS, API | DM-03, DM-05 |
| RO-02 | 3.1 | Role `advisor` (many farmers with consent, enter data, request plans) | missing | Not in `membership_role` | cto/cp-database | S2 (model), S9 | RLS, API | REC-R1 |
| RO-03 | 3.1 | Role `org_admin` (invite/remove members, org dashboard, billing later) | partial | `owner` role ≈ org_admin; owner user management in #7 (`/admin/users`). Rename/map in R1 gap analysis | cto/cp-database | S2 | RLS, API | REC-R1 |
| RO-04 | 3.1 | Role `agronomist` (review queue, approve/edit/reject + reason, minutes) | done | `membership_role.agronomist`, approve trigger (mig 0007), review flow (#7). D4: real-farm approvals need a human | cto/cp-database | S1 | DBT, API | REC-D4 |
| RO-05 | 3.1 | Role `lab_partner` (push results for a sample QR) | missing | Later | cto | S25 | RLS, API | U15 |
| RO-06 | 3.1 | Role `staff` (platform: support, read-only audited, catalogs) | partial | `staff` exists as an **org** role (mig 0003); plan wants a **platform** role on `profile.platform_role` | cto/cp-database | S2 | RLS | DM-01 |
| RO-07 | 3.1 | Role `superadmin` (pack activation, flags, deletion jobs) | missing | No platform role column | cto/cp-database | S2 | RLS | DM-01 |

### 3.2 Permission matrix — one row per cell

Enforcement for every cell: service-layer check **and** Postgres RLS (D1, DM-R1..R5). Test for every cell: `RLS` (allowed + denied user) + `API` once the endpoint exists. Status today: the only enforced cells are agronomist approve (DB trigger) and org scoping by `organisation_id` (composite FKs, `main` mig 0004, `test_org_scoping.py`); no RLS exists yet.

| ID | § | Requirement (resource · role · access) | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| PM-FF-fa | 3.2 | Own farms/fields · farmer · CRUD | missing | No farmer login | cto/cp-database + cp-concierge-app | S9 | RLS, API | RO-01, DM-R1 |
| PM-FF-ad | 3.2 | Own farms/fields · advisor · CRUD if granted `edit` | missing | No `access_grant` | cto/cp-database + cp-concierge-app | S9 | RLS, API | DM-05 |
| PM-FF-oa | 3.2 | Own farms/fields · org_admin · R (org scope) | partial | Org members read org farms (#7 data-access layer); no RLS, no org_admin role | cto/cp-database | S2 | RLS | RO-03 |
| PM-FF-ag | 3.2 | Own farms/fields · agronomist · R (assigned) | partial | Agronomist reads all org farms (#7); "assigned" not modelled | cto/cp-database | S2 | RLS | DM-R1 |
| PM-FF-sf | 3.2 | Own farms/fields · staff · R (audited) | missing | No platform staff, no audit | cto/cp-database | S6 | RLS, DBT (audit row) | DM-27 |
| PM-FF-sa | 3.2 | Own farms/fields · superadmin · CRUD | missing | | cto/cp-database | S2 | RLS | RO-07 |
| PM-ST-fa | 3.2 | Soil tests · farmer · CRUD | missing | | cto/cp-database + cp-concierge-app | S9 | RLS, API | RO-01 |
| PM-ST-ad | 3.2 | Soil tests · advisor · CRUD if granted | missing | | cto/cp-database | S9 | RLS, API | DM-05 |
| PM-ST-oa | 3.2 | Soil tests · org_admin · R | partial | Org-scoped read (#7) | cto/cp-database | S2 | RLS | RO-03 |
| PM-ST-ag | 3.2 | Soil tests · agronomist · R | partial | Agronomist currently also writes them (concierge entry, #7). Plan says R only → in concierge the agronomist enters data; keep write for concierge, record as decision | cto/cp-database | S2 | RLS, DEC | — |
| PM-ST-sf | 3.2 | Soil tests · staff · R | missing | | cto/cp-database | S6 | RLS | RO-06 |
| PM-ST-sa | 3.2 | Soil tests · superadmin · CRUD | missing | | cto/cp-database | S2 | RLS | RO-07 |
| PM-RQ-fa | 3.2 | Request recommendation · farmer · ✓ | missing | | cto/cp-concierge-app | S9 | RLS, API | U8 |
| PM-RQ-ad | 3.2 | Request recommendation · advisor · ✓ | missing | | cto/cp-concierge-app | S9 | RLS, API | RO-02 |
| PM-RQ-oa | 3.2 | Request recommendation · org_admin · – (none) | missing | Must be denied | cto/cp-concierge-app | S9 | RLS (denied) | RO-03 |
| PM-RQ-ag | 3.2 | Request recommendation · agronomist · ✓ | done | Engine run creates engine row (#7 `POST /fields/{id}/plans`) | cto/cp-concierge-app | S1 | API | — |
| PM-RQ-sf | 3.2 | Request recommendation · staff · – | missing | Today org `staff` may create (check #7); must be denied | cto/cp-concierge-app | S2 | RLS (denied) | RO-06 |
| PM-RQ-sa | 3.2 | Request recommendation · superadmin · ✓ | missing | | cto/cp-concierge-app | S2 | RLS | RO-07 |
| PM-DR-fa | 3.2 | See engine draft · farmer · ✗ | missing | No farmer access yet; must be denied by RLS on status ≠ approved | cto/cp-database | S2 (policy), S9 | RLS (denied) | DM-R2 |
| PM-DR-ad | 3.2 | See engine draft · advisor · ✗ | missing | | cto/cp-database | S2, S9 | RLS (denied) | DM-R2 |
| PM-DR-oa | 3.2 | See engine draft · org_admin · ✗ | missing | Today `owner` sees drafts (#7) → conflict to resolve in R1 role mapping | cto/cp-database | S2 | RLS (denied) | DM-R2, RO-03 |
| PM-DR-ag | 3.2 | See engine draft · agronomist · ✓ | done | #7 plan view | cto/cp-concierge-app | S1 | API | — |
| PM-DR-sf | 3.2 | See engine draft · staff · ✓ | missing | Platform staff not modelled | cto/cp-database | S6 | RLS | RO-06 |
| PM-DR-sa | 3.2 | See engine draft · superadmin · ✓ | missing | | cto/cp-database | S2 | RLS | RO-07 |
| PM-AP-fa | 3.2 | Approve/edit/reject · farmer · ✗ | done | DB trigger rejects non-agronomist approve (mig 0007) | cto/cp-database | S1 | DBT | — |
| PM-AP-ad | 3.2 | Approve/edit/reject · advisor · ✗ | done | Same trigger (role not agronomist) | cto/cp-database | S1 | DBT | — |
| PM-AP-oa | 3.2 | Approve/edit/reject · org_admin · ✗ | done | Same trigger (owner ≠ agronomist) | cto/cp-database | S1 | DBT | — |
| PM-AP-ag | 3.2 | Approve/edit/reject · agronomist · ✓ (human only for real farms, D4) | partial | Works (#7). Missing: `ai_reviewed` label path and "human" flag on user so an AI-run account can never approve a real farm | cto/cp-database + cp-concierge-app | S2 | DBT, API | REC-D4 |
| PM-AP-sf | 3.2 | Approve/edit/reject · staff · ✗ | done | Trigger requires agronomist | cto/cp-database | S1 | DBT | — |
| PM-AP-sa | 3.2 | Approve/edit/reject · superadmin · ✓ | superseded | Conflicts with D4 + CLAUDE.md rule 8: approval must be a human **agronomist**. Superadmin may approve only if also holding a human agronomist role. CPO to confirm | cto/cp-database | S2 | DBT, DEC | REC-D4 |
| PM-VP-fa | 3.2 | See approved plan · farmer · ✓ | missing | | cto/cp-concierge-app | S9 | RLS, API | U9 |
| PM-VP-ad | 3.2 | See approved plan · advisor · ✓ | missing | | cto/cp-concierge-app | S9 | RLS, API | DM-05 |
| PM-VP-oa | 3.2 | See approved plan · org_admin · ✓ | partial | Owner sees plans (#7) | cto/cp-database | S2 | RLS | — |
| PM-VP-ag | 3.2 | See approved plan · agronomist · ✓ | done | #7 | cto/cp-concierge-app | S1 | API | — |
| PM-VP-sf | 3.2 | See approved plan · staff · ✓ | missing | | cto/cp-database | S6 | RLS | RO-06 |
| PM-VP-sa | 3.2 | See approved plan · superadmin · ✓ | missing | | cto/cp-database | S2 | RLS | RO-07 |
| PM-AL-fa | 3.2 | Application log · farmer · CRUD | missing | | cto/cp-concierge-app | S10 | RLS, API | U10 |
| PM-AL-ad | 3.2 | Application log · advisor · CRUD if granted | missing | | cto/cp-concierge-app | S10 | RLS, API | DM-05 |
| PM-AL-oa | 3.2 | Application log · org_admin · R | missing | | cto/cp-database | S10 | RLS | U10 |
| PM-AL-ag | 3.2 | Application log · agronomist · R | missing | | cto/cp-database | S10 | RLS | U10 |
| PM-AL-sf | 3.2 | Application log · staff · R | missing | | cto/cp-database | S10 | RLS | RO-06 |
| PM-AL-sa | 3.2 | Application log · superadmin · CRUD | missing | | cto/cp-database | S10 | RLS | RO-07 |
| PM-PX-fa | 3.2 | Proof export / share link · farmer · ✓ | missing | | cto/cp-pdf + cp-concierge-app | S11 | RLS, API | U11b |
| PM-PX-ad | 3.2 | Proof export / share link · advisor · ✓ if granted | missing | | cto/cp-concierge-app | S11 | RLS, API | DM-05 |
| PM-PX-oa | 3.2 | Proof export / share link · org_admin · ✗ | missing | | cto/cp-concierge-app | S11 | RLS (denied) | — |
| PM-PX-ag | 3.2 | Proof export / share link · agronomist · ✗ | superseded | In concierge (Phase 0–3) the agronomist generates the PDF for the farmer (webapp-v1 Step 6). Keep ✓ for **generate** until S9; ✗ for share link. CPO to confirm | cto/cp-pdf | S1, S11 | API, DEC | — |
| PM-PX-sf | 3.2 | Proof export / share link · staff · ✗ | missing | | cto/cp-concierge-app | S11 | RLS (denied) | — |
| PM-PX-sa | 3.2 | Proof export / share link · superadmin · ✓ | missing | | cto/cp-concierge-app | S11 | RLS | — |
| PM-OM-fa | 3.2 | Members of org · farmer · – | missing | Must be denied | cto/cp-database | S9 | RLS (denied) | — |
| PM-OM-ad | 3.2 | Members of org · advisor · – | missing | Must be denied | cto/cp-database | S9 | RLS (denied) | — |
| PM-OM-oa | 3.2 | Members of org · org_admin · CRUD | partial | Owner user management (#7 `/admin/users`, roles, reset, disable) | cto/cp-concierge-app | S1–S2 | API, RLS | RO-03 |
| PM-OM-ag | 3.2 | Members of org · agronomist · – | partial | Check #7 denies non-owner on `/admin/users` (test exists `test_admin_users.py`) | cto/cp-concierge-app | S1 | API (denied) | — |
| PM-OM-sf | 3.2 | Members of org · staff · R | missing | Platform staff | cto/cp-database | S6 | RLS | RO-06 |
| PM-OM-sa | 3.2 | Members of org · superadmin · CRUD | missing | | cto/cp-database | S6 | RLS | RO-07 |
| PM-CP-fa | 3.2 | Country packs, product catalog · farmer · R | missing | Packs are files today | cto/cp-database | S4 | RLS | DM-23, DM-24 |
| PM-CP-ad | 3.2 | Country packs, product catalog · advisor · R | missing | | cto/cp-database | S4 | RLS | DM-23 |
| PM-CP-oa | 3.2 | Country packs, product catalog · org_admin · R | missing | | cto/cp-database | S4 | RLS | DM-23 |
| PM-CP-ag | 3.2 | Country packs, product catalog · agronomist · R | missing | | cto/cp-database | S4 | RLS | DM-23 |
| PM-CP-sf | 3.2 | Country packs, product catalog · staff · CRUD (draft) | missing | | cto/cp-database | S4 | RLS | A3, A4 |
| PM-CP-sa | 3.2 | Country packs, product catalog · superadmin · CRUD + activate | missing | | cto/cp-database | S4 | RLS, DBT (audit) | A3 |
| PM-AU-fa | 3.2 | Audit log · farmer · own events | missing | No `audit_event` | cto/cp-database | S9 | RLS | DM-27 |
| PM-AU-ad | 3.2 | Audit log · advisor · own events | missing | | cto/cp-database | S9 | RLS | DM-27 |
| PM-AU-oa | 3.2 | Audit log · org_admin · org events | missing | | cto/cp-database | S6 | RLS | DM-27 |
| PM-AU-ag | 3.2 | Audit log · agronomist · own events | missing | | cto/cp-database | S6 | RLS | DM-27 |
| PM-AU-sf | 3.2 | Audit log · staff · R | missing | | cto/cp-database | S6 | RLS | DM-27 |
| PM-AU-sa | 3.2 | Audit log · superadmin · R | missing | | cto/cp-database | S6 | RLS | DM-27 |
| PM-HD-fa | 3.2 | Hard delete · farmer · request | missing | | cto/cp-concierge-app | S13 | API | U14 |
| PM-HD-ad | 3.2 | Hard delete · advisor · ✗ | missing | | cto/cp-database | S13 | RLS (denied) | U14 |
| PM-HD-oa | 3.2 | Hard delete · org_admin · ✗ | missing | | cto/cp-database | S13 | RLS (denied) | U14 |
| PM-HD-ag | 3.2 | Hard delete · agronomist · ✗ | missing | | cto/cp-database | S13 | RLS (denied) | U14 |
| PM-HD-sf | 3.2 | Hard delete · staff · ✗ | missing | | cto/cp-database | S13 | RLS (denied) | U14 |
| PM-HD-sa | 3.2 | Hard delete · superadmin · execute | missing | Conflicts with immutable tables (ADR 0002 consequence) → erasure design needed (RK-X3) | cto/cp-database + ciso + coo/legal | S13 | DBT, SR, LR | A12 |
| PM-GR | 3.2 | Access grants farmer → advisor/org: scope `view`/`edit`, optional expiry, in `membership`/`access_grant` | missing | | cto/cp-database | S2 (model), S9 | RLS, DBT | DM-05 |

## §4 Architecture

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| AR-01 | 4.1 | One FastAPI service (Python 3.12) serving `/api/v1`, `/admin/v1` and HTML views | partial | FastAPI app with `/healthz` (`main`), HTML views (#7). No `/api/v1`, `/admin/v1` | cto/cp-concierge-app | S1→S9 | API | — |
| AR-02 | 4.1 | Worker process (Procrastinate, Postgres-backed queue) for PDF, timing, notifications, extraction | missing | | cto/cp-concierge-app + cp-platform | S4 | UT, LIVE | HC-09 |
| AR-03 | 4.1 | Postgres + PostGIS | superseded | **D1:** Railway Postgres from the `postgis/postgis` image (webapp-v1 §5). Local PostGIS works (`docker-compose.yml`); **Railway PostGIS service not created** (agents denied; FI must create, `docs/runbook-db-switch.md`) | cto/devops-engineer + FI | S2 | LIVE, DBT | FI action |
| AR-04 | 4.1 | Auth (Supabase JWT) | superseded | **D1:** app-owned auth (ADR 0005 A1), sessions + CSRF + argon2id (#7) | cto/cp-concierge-app | S1 | API, SR | — |
| AR-05 | 4.1 | Storage (Supabase) for PDFs, uploads | superseded | **D1:** Railway Bucket (ADR 0005 B1); not created yet; `ProofStore` interface planned | cto/cp-pdf + devops-engineer | S2–S3 | UT, LIVE | FI go (bucket cost) |
| AR-06 | 4.1 | `engine/` imported by app + worker, no I/O | done | `engine/` pure; file I/O only in `loaders.py`; imported in #7 `planning.py` | cto/cp-engine | S1 | UT | — |
| AR-07 | 4.1 | External calls only from worker: NASA POWER, forecast API (later) | missing | | cto/cp-concierge-app | S4, S8 | UT | XD-05, XD-06 |
| AR-08 | 4.2 | DB: Supabase Postgres + PostGIS | superseded | **D1** → Railway Postgres + PostGIS (AR-03) | cto/cp-database | S2 | — | AR-03 |
| AR-09 | 4.2 | API: FastAPI + Pydantic v2, OpenAPI | partial | FastAPI + Pydantic in engine; no API schemas/OpenAPI contract yet | cto/cp-concierge-app | S9 | API | — |
| AR-10 | 4.2 | DB access: SQLAlchemy 2 Core / asyncpg; migrations in `supabase/migrations` (SQL) | partial | Migrations SQL in `db/migrations/` (D1 ✓). DB access is **psycopg pool + hand SQL** (#7 `db/pool.py`, `repo/`), not SQLAlchemy/asyncpg → decide: keep psycopg (record in ADR 0008) or migrate | cto/system-architect | S2 | DEC | REC-D1 |
| AR-11 | 4.2 | Auth: Supabase JWT, `request.jwt.claims` + `SET LOCAL ROLE authenticated` per transaction | superseded | **D1:** app session → `SET LOCAL app.user_id/app.org_id/app.platform_role` per transaction for RLS. Not built | cto/cp-database + cp-concierge-app | S2 | RLS, SR | REC-D1 |
| AR-12 | 4.2 | Queue: Procrastinate (Postgres), revisit > 50 jobs/min | missing | Second Railway service = cost → FI go | cto/cp-platform | S4 | UT | HC-09 |
| AR-13 | 4.2 | PDF: Jinja2 HTML → WeasyPrint | missing | `app/pdf/` not started (webapp Step 6) | cto/cp-pdf | S1–S2 | UT, E2E | — |
| AR-14 | 4.2 | Internal UI: Jinja2 + HTMX by FastAPI, one deploy | done | #7 (templates, vendored htmx 2.0.11) | cto/cp-concierge-app | S1 | API, E2E | — |
| AR-15 | 4.2 | Hosting: Railway app + worker (+ Supabase cloud) | partial | Website on Railway (ADR 0004). App + worker services not deployed; Supabase part superseded by D1 | cto/devops-engineer | S3–S4 | LIVE | AR-03 |
| AR-16 | 4.2 | Errors: Sentry free tier | missing | R7: free allowed, paid needs FI | cto/cp-platform | S5 | LIVE | — |
| AR-17 | 4.2 | Region: EU launch → EU regions (ADR) | superseded | R4: launch = Canada (Ontario). Railway has no Canadian region; decided 2026-11-16 (ADR 0009): Railway interim (synthetic data only), Canadian host chosen by 2027-01-04, production migration in S4 (`S4-PLT-01`) | FI + ciso + coo/legal | S4 | DEC | OQ-06 |
| AR-18 | 4.3 | `engine/` | done | `main` | cto/cp-engine | S1 | UT | — |
| AR-19 | 4.3 | `data_sources/` (SoilGrids cache, weather clients, WoSIS/FTW) | missing | | cto/cp-engine (cache) + head-of-data/data-engineer | S3 | UT | XD-01 |
| AR-20 | 4.3 | `app/main.py` | partial | Actual path `app/cloverproof_app/main.py` (uv package layout) — accept as equivalent (DEC) | cto/cp-platform | S1 | DEC | — |
| AR-21 | 4.3 | `app/api/v1/` user endpoints | missing | | cto/cp-concierge-app | S9 | API | — |
| AR-22 | 4.3 | `app/admin/v1/` admin endpoints | missing | | cto/cp-concierge-app | S4 | API | — |
| AR-23 | 4.3 | `app/views/` Jinja+HTMX pages | partial | Views live in `web.py`, `plan_web.py`, `account.py` (#7). Restructure when API arrives | cto/cp-concierge-app | S2 | DEC | — |
| AR-24 | 4.3 | `app/services/` business logic (no HTTP) | partial | `planning.py`, `timer.py` (#7); `recommendation_service.py` missing (EN-02) | cto/cp-concierge-app | S2 | UT | EN-02 |
| AR-25 | 4.3 | `app/repositories/` SQL access | done | `app/cloverproof_app/repo/` (#7) | cto/cp-concierge-app | S1 | DBT | — |
| AR-26 | 4.3 | `app/auth/` JWT verify, role helpers | superseded | D1: `auth.py`, `security.py` (sessions, CSRF) (#7) | cto/cp-concierge-app | S1 | API | — |
| AR-27 | 4.3 | `app/jobs/` Procrastinate tasks | missing | | cto/cp-concierge-app | S4 | UT | AR-02 |
| AR-28 | 4.3 | `app/pdf/templates/` | missing | | cto/cp-pdf | S1–S2 | UT | — |
| AR-29 | 4.3 | `app/schemas/` Pydantic request/response models | missing | | cto/cp-concierge-app | S9 | API | — |
| AR-30 | 4.3 | `supabase/migrations/` | superseded | D1: `db/migrations/` (`main`, 0001–0009; 0010 in #7) | cto/cp-database | S1 | DBT | — |
| AR-31 | 4.3 | `packs/` country packs (YAML) + golden tests | partial | `packs/placeholder/v0.yaml`; golden tests live in `engine/tests/golden/` (keep; DEC) | cto/cp-engine | S2 | GT | — |
| AR-32 | 4.3 | `docs/adr/` | done | ADR 0001–0005 | cto | S1 | DR | — |
| AR-33 | 4.3 | `docs/data-sources.md` | missing | | head-of-data/data-governance-specialist + cto/cp-engine | S2 | DR, LR | XD-01 |
| AR-34 | 4.3 | `docs/backlog.md` | missing | | CPO/agile-manager | S2 | DR | — |
| AR-35 | 4.3 | `tests/` (api, service, rls, e2e) | partial | Tests are per package (`engine/tests`, `app/tests`, `app/tests/db`). No rls/e2e suites | cto/cp-qa | S2 | — | DM-R5 |

## §5 Module map

### 5.1 User side (U1–U16; multi-sprint modules split a/b/c)

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| U1a | 5.1 | Auth & onboarding — staff only: login, profile | done | Login, sessions, CSRF, rate limit, account page, password change, CLI user-create (#7); D1 replaces Supabase magic link | cto/cp-concierge-app | S1 | API, SR | — |
| U1b | 5.1 | Auth & onboarding — farmers: email magic link/password, invite acceptance, language + unit preference | missing | Needs email provider (OQ-05) for magic link/invites | cto/cp-concierge-app | S9 | API, SR, E2E | OQ-05, DM-01 |
| U2 | 5.1 | Organisations & memberships: create, invite, roles, leave | partial | Org + membership tables (mig 0003); owner manages users + roles (#7). Missing: invite flow, leave, org create in UI | cto/cp-concierge-app | S2 | API, RLS | DM-02, DM-03 |
| U3a | 5.1 | Access grants — model | missing | | cto/cp-database | S2 | DBT, RLS | DM-05 |
| U3b | 5.1 | Access grants — UI/API (grant/revoke/expiry) | missing | | cto/cp-concierge-app | S9 | API, RLS | U3a |
| U4 | 5.1 | Farms & fields: CRUD, area manual then geometry, geometry versions per season | partial | Create farmer/farm/field + manual area (#7, mig 0004). Missing: edit/soft delete, geometry upload | cto/cp-concierge-app | S2 | API, DBT | DM-07, DM-08 |
| U5 | 5.1 | Seasons & crop plans: crop, target yield, previous crop, notes | partial | `crop_plan` (mig 0006) holds crop/target/previous crop; `season` is an org label. Plan §6.2 merges these into `season` per field → R1 decision | cto/cp-database | S2 | DBT | DM-09, RK-X5 |
| U6a | 5.1 | Soil tests — manual entry with method/depth/form/units | done | `soil_test` + `soil_test_value` (mig 0005), entry form (#7) | cto/cp-concierge-app | S1 | DBT, API | — |
| U6b | 5.1 | Soil tests — file upload | missing | Needs bucket | cto/cp-concierge-app | S4 | API | AR-05, DM-26 |
| U6c | 5.1 | Soil tests — extraction (Docling) | missing | CLAUDE.md: OCR/LLM out of scope → needs CLAUDE.md change by FI | head-of-data/llm-engineer + cto | S20–S21 | GT-style accuracy set | REC-CL |
| U7 | 5.1 | No-test estimate: SoilGrids cache (+LUCAS EU) with source metadata | missing | | cto/cp-engine + head-of-data/data-engineer | S3 | UT, GT, GRD | XD-02, DM-12 |
| U8 | 5.1 | Recommendation request: run engine → draft → review queue | done | `POST /fields/{id}/plans` runs engine, stores engine row (#7) | cto/cp-concierge-app | S1 | API, E2E | — |
| U9 | 5.1 | Approved plan view: products, rates, splits, timing window, explanations, confidence | partial | Rates, splits, explanations, confidence shown (#7). Missing: products (A4), GDD timing (S04-1) | cto/cp-concierge-app | S3 | API, GRD | A4, S04-1 |
| U10 | 5.1 | Application log: planned vs actual, date, product, rate, area, method, weather note, photo | partial | Table exists with planned/actual (mig 0008); no UI, no photo, no lock | cto/cp-concierge-app | S10 | API, DBT | DM-18 |
| U11a | 5.1 | Proof export — PDF (plan + log history), SHA-256 | missing | Step 6 not started | cto/cp-pdf | S1–S2 (v0), S4 | UT, E2E, GRD | PD-* |
| U11b | 5.1 | Proof sharing — signed share link with expiry, public verify page | missing | | cto/cp-concierge-app | S11 | API, SR | DM-20 |
| U12 | 5.1 | Notifications by email: plan approved, timing update, log reminder | missing | Email provider undecided (OQ-05) | cto/cp-concierge-app | S12 | UT, LIVE | OQ-05 |
| U13 | 5.1 | Outcomes: yield, feedback, "did you follow the plan?" | missing | | cto/cp-concierge-app | S17 | API | DM-21 |
| U14 | 5.1 | Data rights: export my data, delete account request | missing | Erasure vs immutability unresolved (RK-X3) | cto + coo/legal | S13 | API, LR | A12 |
| U15 | 5.1 | Sampling kit QR → field; lab result attaches to soil test | missing | | cto | S25 | API | RO-05 |
| U16 | 5.1 | Billing: subscription per farm/advisor, invoices | missing | Model undecided (OQ-09, cso) | cto + cso | S26 | API | OQ-09 |

### 5.2 Admin side (A1–A13)

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| A1 | 5.2 | Review queue: list by due date/priority; diff engine vs edit; approve/edit/reject + reason; minutes timer | partial | Approve/edit/reject + reason + timer per plan (#7). Missing: queue page sorted/filtered, side-by-side diff, due date/priority | cto/cp-concierge-app + CPO/product-designer | S2 | API, E2E | S02-3 |
| A2 | 5.2 | Calibration dashboard: delta per nutrient/crop/pack; minutes per plan; approve-without-edit rate | partial | `recommendation_diff` view (N only, mig 0009); metric definitions (#5). No UI | cto/cp-concierge-app + head-of-data/data-analyst | S5 | API, E2E | DM-16 |
| A3 | 5.2 | Country pack registry: upload YAML → schema → golden → draft/active/retired, one active per country+crop | missing | Packs are files loaded by `loaders.py` | cto/cp-engine + cp-database | S4 | GT, DBT, API | DM-23 |
| A4 | 5.2 | Product catalog per country (grade N-P-K-S, form, density, active) | missing | | cto/cp-database + cp-engine | S2 | DBT, GRD | DM-24 |
| A5 | 5.2 | Orgs & users admin: search, view, suspend, resend invite, change role (audited) | partial | Org-level user admin (#7): roles, reset, disable/enable. Missing: platform-wide search, invites, audit | cto/cp-concierge-app | S6 | API, DBT | DM-27 |
| A6 | 5.2 | Support "view as" read-only, every access logged with reason | missing | | cto/cp-concierge-app + ciso | S8 | API, SR | DM-27 |
| A7 | 5.2 | Audit log viewer: filter actor/entity/action/date | missing | | cto/cp-concierge-app | S6 | API | DM-27 |
| A8 | 5.2 | Data source status: SoilGrids coverage, weather refresh, job failures | missing | | cto/cp-concierge-app | S7 | API | JB-03 |
| A9 | 5.2 | Job monitor: queue depth, failed, retry | missing | | cto/cp-concierge-app | S7 | API | AR-02 |
| A10 | 5.2 | Feature flags per org/country | missing | | cto/cp-database + cp-concierge-app | S9 | DBT, API | DM-25 |
| A11 | 5.2 | Pilot metrics: execution rate, fertilizer change vs last year, yield vs last year, proof used with third party | missing | Definitions drafted (#5 `docs/data/metrics.md`) | head-of-data/data-analyst + cto | S16 | API, DR | DM-21 |
| A12 | 5.2 | Deletion & export jobs with approval (GDPR/PIPEDA) | missing | | cto + coo/legal + ciso | S13 | DBT, LR, SR | U14 |
| A13 | 5.2 | Billing admin: plans, coupons, manual invoices | missing | | cto + cso | S26 | API | U16 |

## §6 Data model

R1: §6 is the target; gaps close with **forward-only** migrations after a `cp-database` gap analysis; never edit an applied migration (0001–0009 on `main`, 0010 in #7). D1: RLS on Railway Postgres via `SET LOCAL app.*` settings.

### 6.0 Conventions

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| DM-C1 | 6 | `id uuid pk default gen_random_uuid()` on all tables | done | Every table in mig 0001–0009 | cto/cp-database | S1 | DBT | — |
| DM-C2 | 6 | `created_at timestamptz default now()` on all tables | done | Every table | cto/cp-database | S1 | DBT | — |
| DM-C3 | 6 | `created_by uuid` on all tables | partial | Present on field_geometry_version, soil_test, crop_plan, recommendation, application_log, proof_document; missing on organisation, farmer, farm, field, season, membership, soil_test_value, review (has reviewer_id) | cto/cp-database | S2 | DBT | REC-R1 |
| DM-C4 | 6 | `updated_at` on mutable tables | missing | Not on any table | cto/cp-database | S2 | DBT | REC-R1 |
| DM-C5 | 6 | Soft delete via `deleted_at` where noted | partial | Only `pilot_request.deleted_at`; `field.deleted_at` missing | cto/cp-database | S2 | DBT | DM-07 |
| DM-C6 | 6 | Immutable tables: no UPDATE/DELETE grants | done | Grants + triggers on recommendation/review/proof_document (mig 0002, 0006–0008). Extend to every new immutable table (DM-14, DM-27, DM-05 history) | cto/cp-database | S1 | DBT | — |

### 6.1–6.7 Tables (one row per table; key columns listed; column gaps in Evidence)

| ID | § | Requirement (table: key columns · rule) | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| DM-01 | 6.1 | `profile`: user_id, full_name, locale, unit_system metric/imperial, platform_role none/staff/superadmin · 1:1 with user | partial | `app_user` (mig 0003): email, display_name, hash, totp, provider, disabled. Missing locale, unit_system, platform_role. Name differs (keep `app_user`, D1) | cto/cp-database | S2 | DBT | REC-R1 |
| DM-02 | 6.1 | `organisation`: name, kind advisory/coop/dealer/lab/internal, country_code | partial | name only (mig 0003) | cto/cp-database | S2 | DBT | REC-R1 |
| DM-03 | 6.1 | `org_membership`: org_id, user_id, role org_admin/advisor/agronomist, status | partial | `membership` role owner/agronomist/staff/farmer, no status (mig 0003). Role mapping decision | cto/cp-database | S2 | DBT, RLS | RO-02, RO-03, RO-06 |
| DM-04 | 6.1 | `farmer`: owner_user_id (nullable), display_name, country_code, contact · may exist before login | partial | `farmer` org-owned, `app_user_id` nullable, display_name, notes (mig 0004). Missing country_code, contact; ownership model differs (org vs farmer owns, HC-08) | cto/cp-database | S2 | DBT | HC-08 |
| DM-05 | 6.1 | `access_grant`: farmer_id, grantee_org_id/user_id, scope view/edit, granted_by, expires_at, revoked_at · immutable history | missing | Note: "immutable history" vs `revoked_at` column — resolve as insert-only with a revoke row or a one-time revoked_at set (RK-X7) | cto/cp-database | S2 | DBT, RLS | REC-R1 |
| DM-06 | 6.2 | `farm`: farmer_id, name, region_code | partial | farm (mig 0004) has region (text), country_code (on farm, not farmer) | cto/cp-database | S2 | DBT | — |
| DM-07 | 6.2 | `field`: farm_id, name, external_ref, deleted_at | partial | Missing external_ref, deleted_at | cto/cp-database | S2 | DBT | — |
| DM-08 | 6.2 | `field_geometry_version`: field_id, season_year, geom MultiPolygon 4326, area_ha computed, area_source manual/geometry, valid_from | partial | Exists keyed by season_id, nullable geom, manual area (mig 0004). Missing season_year, valid_from, computed area | cto/cp-database | S2, S18 | DBT | DM-09 |
| DM-09 | 6.2 | `season`: field_id, year, crop_code, variety, sowing_date, target_yield(+unit), previous_crop_code, notes · one active per field+year | partial | `season` = org label + dates; crop/target/previous crop in `crop_plan` (mig 0006). **Conflict:** CLAUDE.md model has `season → crop_plan → recommendation` (RK-X5) | cto/cp-database + CPO | S2 | DBT | RK-X5 |
| DM-10 | 6.3 | `soil_sample`: field_id, sampled_at, depth top/bottom, lab_name, kit_qr (later), file_ids · one sampling event | partial | `soil_test` (mig 0005): field, sample_date, depths, lab, source lab/estimate. Missing kit_qr, file_ids | cto/cp-database | S2, S4, S25 | DBT | DM-26 |
| DM-11 | 6.3 | `soil_measurement`: sample_id, property (ph_water, ph_cacl2, som, p, k, no3_n…), value, unit, extraction_method (olsen/bray1/mehlich3/ammonium_acetate…), nutrient_form elemental/oxide, canonical_value/unit, entry_method manual/extracted/lab_api, confirmed_by/at · never P without method + form | partial | `soil_test_value`: form N/NO3-N/P/P2O5/K/K2O, unit mg/kg/ppm, method olsen/bray-1/mehlich-3/other + detail (mig 0005; method/form enforced). Missing: pH/SOM properties, ammonium_acetate (agronomist-todo, ADR needed), canonical value, entry_method, confirmation. Enum labels must stay equal to engine StrEnums | cto/cp-database + cp-engine | S2–S4 | DBT, UT | S04-2 |
| DM-12 | 6.3 | `soil_estimate`: field_id, season_year, property, value, unit, source soilgrids/lucas/wosis, source_version, resolution_m, depth, uncertainty, retrieved_at · always `low` | missing | Today `soil_test.source = estimate` exists — decide migration path | cto/cp-database | S3 | DBT, GT | U7 |
| DM-13 | 6.4 | `recommendation`: season_id, parent_id, version_no, status draft/in_review/approved/rejected/superseded, origin engine/agronomist_edit, engine_version, pack_id+version, input_snapshot, output, confidence_overall, created_by · immutable | partial | Exists (mig 0006): crop_plan_id, parent_id, kind engine/agronomist, reason, inputs_snapshot, result, versions, pack sha, confidence, n_rate. Missing version_no, status. **Conflict:** a status column on an immutable row cannot change → derive status from `review` rows/a view (RK-X4) | cto/cp-database | S2 | DBT | RK-X4 |
| DM-14 | 6.4 | `recommendation_line`: recommendation_id, nutrient, rate_kg_ha, product_id, product_rate/unit, split_no, timing window start/end, timing_basis gdd/calendar/manual, explanation, confidence · immutable | missing | R2: replaces P/K columns proposal (0011). Splits live in `result` jsonb only | cto/cp-database | S2 | DBT | REC-R2 |
| DM-15 | 6.4 | `review`: recommendation_id, reviewer_id, decision approve/edit/reject, reason, minutes_spent, started_at, finished_at · immutable | partial | Exists (mig 0007) with resulting_recommendation_id. Missing started_at, finished_at (timer in #7 computes minutes; persist times) | cto/cp-database | S2 | DBT | — |
| DM-16 | 6.4 | `calibration_delta` view, per line engine vs final approved, abs/rel diff · materialized, nightly | partial | `recommendation_diff` (security_invoker view, N only, mig 0009). Missing per-line, rel diff, MV + nightly job | cto/cp-database + head-of-data/data-engineer | S2 (per line), S5 (MV) | DBT | DM-14, JB-04 |
| DM-17 | 6.4 | (rule) review `edit` = changed lines + reason → new version + approve | partial | Edit creates child row + edit review (mig 0007, #7); approval of the child is a separate step — align with RV-04 | cto/cp-concierge-app | S2 | API, DBT | RV-04 |
| DM-18 | 6.5 | `application_log`: season_id, recommendation_line_id, applied_on, product_id/free_text, rate, rate_unit, area_ha, method, operator, weather_note, photo_ids, entered_by · editable 24 h then locked; correction row `corrects_id` | partial | Table with planned/actual date+rate, product text (mig 0008). Missing line link, unit, area, method, operator, weather, photos, 24 h lock, corrects_id | cto/cp-database | S10 | DBT | DM-14 |
| DM-19 | 6.5 | `proof_document`: season_id, recommendation_id, kind plan/plan_with_log, storage_path, sha256, generated_at/by, template_version · immutable | partial | Exists (mig 0008): recommendation_id, storage_key, sha256, approved-only trigger. Missing kind, template_version | cto/cp-database | S2 | DBT | — |
| DM-20 | 6.5 | `share_link`: proof_document_id, token_hash, expires_at, revoked_at, view_count · token shown once | missing | | cto/cp-database | S11 | DBT, SR | — |
| DM-21 | 6.5 | `outcome`: season_id, harvest_date, yield value/unit, followed_plan yes/partly/no, farmer_comment, third_party_used bank/buyer/inspector/subsidy/none, third_party_result | missing | | cto/cp-database | S17 | DBT | — |
| DM-22 | 6.6 | `crop`: code, name_i18n, gdd_base_c | missing | Crop is text validated by pack (ADR 0002). `gdd_base_c` is an agronomic constant → PLACEHOLDER until validated | cto/cp-database + cp-engine | S4 | DBT, GRD | — |
| DM-23 | 6.6 | `country_pack`: country_code, crop_code, version semver, status draft/active/retired, yaml_blob, yaml_sha256, golden_report, activated_by/at · one active per country+crop (partial unique index) | missing | `pack_sha256` already computed by engine | cto/cp-database | S4 | DBT | A3 |
| DM-24 | 6.6 | `fertilizer_product`: country_code, name, n, p2o5, k2o, s, form granular/liquid, density, active · no vendor prices, no affiliate fields | missing | | cto/cp-database | S2 | DBT, GRD | A4 |
| DM-25 | 6.6 | `feature_flag`: key, scope global/org/country, scope_id, enabled | missing | | cto/cp-database | S9 | DBT | A10 |
| DM-26 | 6.7 | `file_object`: bucket, path, mime, size, sha256, uploaded_by | missing | | cto/cp-database | S4 | DBT | AR-05 |
| DM-27 | 6.7 | `audit_event`: actor_id, actor_role, action, entity_type, entity_id, reason, ip_hash, at, diff · append-only, by triggers + app | missing | Required by DoD (DD-03) from the first admin action | cto/cp-database | S2 | DBT | — |
| DM-28 | 6.7 | `notification`: user_id, kind, payload, sent_at, channel | missing | | cto/cp-database | S12 | DBT | U12 |
| DM-29 | 6.7 | `data_request`: user_id, kind export/delete, status, approved_by, completed_at | missing | | cto/cp-database | S13 | DBT | U14 |
| DM-30 | 6.7 | `weather_daily`: cell_id, date, tmin, tmax, precip, source, retrieved_at | missing | | cto/cp-database | S4 | DBT | JB-03 |

### 6.8 RLS (D1: Postgres RLS on Railway keyed on `SET LOCAL app.user_id / app.org_id / app.platform_role`; new ADR 0008)

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| DM-R1 | 6.8 | farmer, farm, field, season, soil_*, application_log, outcome visible if owner OR active access_grant (direct/org) OR platform staff/superadmin | missing | Only org scoping via composite FKs + data-access layer (ADR 0002) | cto/cp-database | S1–S2 (v0), S9 (grants) | RLS | REC-D1, DM-05 |
| DM-R2 | 6.8 | recommendation with status ≠ approved visible only to org agronomists + platform roles | missing | | cto/cp-database | S2 | RLS | DM-13 |
| DM-R3 | 6.8 | Immutable tables: INSERT by policy; UPDATE/DELETE revoked from the app role | done | `cp_app` has no UPDATE/DELETE (mig 0002) + triggers; add policies when RLS is enabled | cto/cp-database | S1 | DBT, RLS | — |
| DM-R4 | 6.8 | `audit_event`: INSERT only via trigger/service role; SELECT by policy | missing | | cto/cp-database | S2 | RLS | DM-27 |
| DM-R5 | 6.8 | Every policy has a pytest RLS test with ≥ 2 users (allowed/denied) | missing | Two-org tests exist for scoping (`test_org_scoping.py`) — pattern to reuse | cto/cp-database + cp-qa | S1→ | RLS | DM-R1 |

## §7 API design

### 7.0 Conventions

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| AC-01 | 7 | REST + JSON; prefixes `/api/v1` (user), `/admin/v1` (admin) | missing | Only HTML routes (#7) | cto/cp-concierge-app | S4 (admin), S9 (user) | API | — |
| AC-02 | 7 | Auth `Authorization: Bearer <supabase JWT>` | superseded | D1: app sessions. Cookie session for HTML; API auth for non-browser clients (native app, D2) needs its own ADR (token type, expiry, revocation) | cto/system-architect + ciso | S9 (ADR S8) | SR, DEC | REC-D1, REC-D2 |
| AC-03 | 7 | Cursor pagination `?cursor=&limit=` | missing | | cto/cp-concierge-app | S9 | API | — |
| AC-04 | 7 | Errors RFC 9457 problem+json | missing | | cto/cp-concierge-app | S4 | API | — |
| AC-05 | 7 | IDs UUID | done | All PKs uuid | cto/cp-database | S1 | DBT | — |
| AC-06 | 7 | Times ISO 8601 UTC | partial | `timestamptz` in DB; API serialisation not built | cto/cp-concierge-app | S9 | API | — |
| AC-07 | 7 | `Idempotency-Key` on POSTs that create recommendations, proofs, logs | missing | HTML form double-submit not guarded either | cto/cp-concierge-app | S2 (HTML), S9 (API) | API | — |
| AC-08 | 7 | `unit_system` in request/response; server stores canonical | missing | | cto/cp-concierge-app + cp-engine | S9 | API, UT | DM-01 |

### 7.1 User API `/api/v1` — one row per method + path

For every row: owner `cto/cp-concierge-app` (DB parts `cp-database`), test `API` + `RLS` (allowed + denied role from §3.2). HTML equivalents in #7 are noted; the JSON endpoint itself is missing unless stated.

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| UA-01 | 7.1 | GET `/me` — profile, roles, memberships | partial | HTML `/account` (#7) | cto/cp-concierge-app | S9 | API | DM-01 |
| UA-02 | 7.1 | PATCH `/me` — name, locale, unit system | partial | HTML `POST /account/name` (#7); no locale/unit | cto/cp-concierge-app | S9 | API | DM-01 |
| UA-03 | 7.1 | GET `/orgs` — my orgs | partial | HTML `/orgs/choose` (#7) | cto/cp-concierge-app | S9 | API | — |
| UA-04 | 7.1 | POST `/orgs/{id}/invites` — invite member (org_admin) | missing | Today: owner creates user + temp password (#7) | cto/cp-concierge-app | S9 | API, RLS | OQ-05 |
| UA-05 | 7.1 | POST `/invites/{token}/accept` | missing | | cto/cp-concierge-app | S9 | API, SR | UA-04 |
| UA-06 | 7.1 | GET `/farmers` — farmers I can access | partial | HTML `/farmers` (#7) | cto/cp-concierge-app | S9 | API, RLS | DM-R1 |
| UA-07 | 7.1 | POST `/farmers` — create farmer (advisor/concierge) | partial | HTML `POST /farmers` (#7) | cto/cp-concierge-app | S9 | API, RLS | — |
| UA-08 | 7.1 | POST `/farmers/{id}/grants` — grant access to org/user | missing | | cto/cp-concierge-app | S9 | API, RLS | DM-05 |
| UA-09 | 7.1 | DELETE `/grants/{id}` — revoke (farmer only) | missing | | cto/cp-concierge-app | S9 | API, RLS (non-farmer denied) | DM-05 |
| UA-10 | 7.1 | GET `/farmers/{id}/farms` | partial | Farms shown on HTML farmer page (#7) | cto/cp-concierge-app | S9 | API, RLS | — |
| UA-11 | 7.1 | POST `/farmers/{id}/farms` | partial | HTML `POST /farmers/{id}/farms` (#7) | cto/cp-concierge-app | S9 | API, RLS | — |
| UA-12 | 7.1 | GET `/farms/{id}` | missing | | cto/cp-concierge-app | S9 | API, RLS | — |
| UA-13 | 7.1 | PATCH `/farms/{id}` | missing | No edit in #7 | cto/cp-concierge-app | S9 | API, RLS | DM-C4 |
| UA-14 | 7.1 | GET `/farms/{id}/fields` | partial | Fields listed on HTML farmer page (#7) | cto/cp-concierge-app | S9 | API, RLS | — |
| UA-15 | 7.1 | POST `/farms/{id}/fields` | partial | HTML `POST /farmers/{id}/fields` (#7, path differs) | cto/cp-concierge-app | S9 | API, RLS | — |
| UA-16 | 7.1 | GET `/fields/{id}` | partial | HTML `/fields/{id}` (#7) | cto/cp-concierge-app | S9 | API, RLS | — |
| UA-17 | 7.1 | PATCH `/fields/{id}` | missing | | cto/cp-concierge-app | S9 | API, RLS | — |
| UA-18 | 7.1 | DELETE `/fields/{id}` — soft delete | missing | `field.deleted_at` missing | cto/cp-concierge-app | S9 | API, RLS, DBT | DM-07 |
| UA-19 | 7.1 | POST `/fields/{id}/geometry` — new geometry version (GeoJSON) | missing | | cto/cp-concierge-app | S18 | API, DBT | DM-08 |
| UA-20 | 7.1 | GET `/fields/{id}/seasons` | missing | | cto/cp-concierge-app | S9 | API, RLS | DM-09 |
| UA-21 | 7.1 | POST `/fields/{id}/seasons` | partial | Season implied by `POST /fields/{id}/plans` (crop_plan) (#7) | cto/cp-concierge-app | S9 | API, RLS | DM-09 |
| UA-22 | 7.1 | GET `/seasons/{id}` | partial | HTML `/plans/{id}` (#7) | cto/cp-concierge-app | S9 | API, RLS | DM-09 |
| UA-23 | 7.1 | PATCH `/seasons/{id}` | missing | | cto/cp-concierge-app | S9 | API, RLS | DM-09 |
| UA-24 | 7.1 | POST `/fields/{id}/soil-samples` — sample + measurements | partial | Soil test entered inside the plan form (#7) | cto/cp-concierge-app | S9 | API, RLS | DM-10, DM-11 |
| UA-25 | 7.1 | GET `/fields/{id}/soil-samples` — history | partial | Soil values on HTML field page (#7) | cto/cp-concierge-app | S9 | API, RLS | — |
| UA-26 | 7.1 | POST `/soil-samples/{id}/files` — upload report | missing | | cto/cp-concierge-app | S4 | API, SR (file type/size) | AR-05, DM-26 |
| UA-27 | 7.1 | POST `/soil-samples/{id}/confirm` — human confirms values (required before use) | missing | | cto/cp-concierge-app | S4 | API, DBT | DM-11 |
| UA-28 | 7.1 | GET `/fields/{id}/soil-estimate` — cached estimate + source + confidence | missing | | cto/cp-concierge-app | S3 | API | DM-12 |
| UA-29 | 7.1 | POST `/seasons/{id}/recommendations` — run engine → draft → queue | partial | HTML `POST /fields/{id}/plans` (#7) | cto/cp-concierge-app | S9 | API, RLS | EN-02 |
| UA-30 | 7.1 | GET `/seasons/{id}/recommendations` — approved (farmer) / all (agronomist) | missing | Role-filtered list = review-gate test | cto/cp-concierge-app | S9 | API, RLS | DM-R2 |
| UA-31 | 7.1 | GET `/recommendations/{id}` — lines, explanations, confidence | partial | HTML plan view (#7) | cto/cp-concierge-app | S9 | API, RLS | DM-14 |
| UA-32 | 7.1 | GET `/recommendations/{id}/timing` — current window + last refresh | missing | | cto/cp-concierge-app | S4 (HTML), S9 | API | S04-1 |
| UA-33 | 7.1 | GET `/seasons/{id}/applications` | missing | | cto/cp-concierge-app | S10 | API, RLS | DM-18 |
| UA-34 | 7.1 | POST `/seasons/{id}/applications` | missing | | cto/cp-concierge-app | S10 | API, RLS | DM-18 |
| UA-35 | 7.1 | POST `/applications/{id}/corrections` — after lock | missing | | cto/cp-concierge-app | S10 | API, DBT | DM-18 |
| UA-36 | 7.1 | POST `/seasons/{id}/proofs` — generate PDF (async) | missing | Step 6 | cto/cp-pdf + cp-concierge-app | S2 (sync), S4 (async) | API, UT | AR-02 |
| UA-37 | 7.1 | GET `/proofs/{id}` — metadata + signed URL | missing | | cto/cp-pdf | S2 | API, SR | SC-05 |
| UA-38 | 7.1 | POST `/proofs/{id}/share-links` — expiring link | missing | | cto/cp-concierge-app | S11 | API, SR | DM-20 |
| UA-39 | 7.1 | DELETE `/share-links/{id}` — revoke | missing | | cto/cp-concierge-app | S11 | API | DM-20 |
| UA-40 | 7.1 | GET `/public/verify/{sha256}` — no auth; exists, generated_at, template_version; no personal data | missing | | cto/cp-concierge-app + ciso | S11 | API, SR | SC-10 |
| UA-41 | 7.1 | GET `/public/share/{token}` — no auth; render shared PDF if valid | missing | | cto/cp-concierge-app + ciso | S11 | API, SR | DM-20 |
| UA-42 | 7.1 | POST `/seasons/{id}/outcome` — yield + feedback | missing | | cto/cp-concierge-app | S17 | API | DM-21 |
| UA-43 | 7.1 | POST `/me/data-requests` — export or delete | missing | | cto/cp-concierge-app | S13 | API | DM-29 |
| UA-44 | 7.1 | GET `/me/data-requests` — status | missing | | cto/cp-concierge-app | S13 | API | DM-29 |

### 7.2 Agronomist endpoints `/api/v1/review`

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| RV-01 | 7.2 | GET `/review/queue` — drafts for my org, by due date | missing | No queue page; plans reached via farmer/field (#7) | cto/cp-concierge-app | S2 (HTML) | API, RLS | A1 |
| RV-02 | 7.2 | POST `/review/{rec_id}/start` — start timer | partial | Timer per plan (#7 `timer.py`, `/plans/{id}/timer`); `started_at` not persisted | cto/cp-concierge-app | S2 | API, DBT | DM-15 |
| RV-03 | 7.2 | POST `/review/{rec_id}/approve` — approve as is | partial | HTML `POST /plans/{id}/review` (#7); D4 human-only for real farms | cto/cp-concierge-app | S2 | API, DBT | REC-D4 |
| RV-04 | 7.2 | POST `/review/{rec_id}/edit` — changed lines + reason → new version + approve | partial | HTML edit creates child + reason (#7); "+ approve" in one step not confirmed; per-line edit needs DM-14 | cto/cp-concierge-app | S2 | API, DBT | DM-14 |
| RV-05 | 7.2 | POST `/review/{rec_id}/reject` — reason required | partial | Reject with reason via review route (#7; DB requires reason, mig 0007) | cto/cp-concierge-app | S2 | API, DBT | — |

### 7.3 Admin API `/admin/v1` (staff / superadmin only)

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| AD-01 | 7.3 | GET `/users` — search (staff) | partial | Org-scoped HTML `/admin/users` (#7); platform-wide missing | cto/cp-concierge-app | S6 | API, RLS | RO-06 |
| AD-02 | 7.3 | GET `/orgs` — search (staff) | missing | | cto/cp-concierge-app | S6 | API, RLS | RO-06 |
| AD-03 | 7.3 | PATCH `/users/{id}` — suspend, platform role (superadmin) | partial | Disable/enable/roles in org (#7); platform role missing; not audited | cto/cp-concierge-app | S6 | API, RLS, DBT (audit) | DM-01, DM-27 |
| AD-04 | 7.3 | POST `/support/sessions` — read-only view-as, reason, 30-min expiry (staff) | missing | | cto/cp-concierge-app + ciso | S8 | API, SR | A6 |
| AD-05 | 7.3 | GET `/audit` — audit search (staff) | missing | | cto/cp-concierge-app | S6 | API | DM-27 |
| AD-06 | 7.3 | GET `/packs` — list (staff) | missing | | cto/cp-concierge-app | S4 | API | DM-23 |
| AD-07 | 7.3 | POST `/packs` — upload draft pack (staff) | missing | | cto/cp-concierge-app | S4 | API, SR (YAML safe load) | DM-23 |
| AD-08 | 7.3 | POST `/packs/{id}/validate` — schema + golden (staff) | missing | Engine golden runner exists (`golden_report.py`) | cto/cp-engine + cp-concierge-app | S4 | API, GT | A3 |
| AD-09 | 7.3 | POST `/packs/{id}/activate` — retires previous (superadmin) | missing | Must be audited (S04-DoD) | cto/cp-concierge-app | S4 | API, DBT | DM-23, DM-27 |
| AD-10 | 7.3 | GET `/products` (staff) | missing | | cto/cp-concierge-app | S4 | API | DM-24 |
| AD-11 | 7.3 | POST `/products` (staff) | missing | | cto/cp-concierge-app | S4 | API, GRD | DM-24 |
| AD-12 | 7.3 | PATCH `/products` (staff) | missing | | cto/cp-concierge-app | S4 | API | DM-24 |
| AD-13 | 7.3 | GET `/metrics/calibration` — engine vs agronomist deltas | missing | View exists (mig 0009) | cto/cp-concierge-app + head-of-data | S5 | API | DM-16 |
| AD-14 | 7.3 | GET `/metrics/review-time` — minutes per plan | missing | `review.minutes_spent` stored | cto/cp-concierge-app + head-of-data | S5 | API | — |
| AD-15 | 7.3 | GET `/metrics/pilot` — pilot KPIs | missing | | cto/cp-concierge-app + head-of-data | S16 | API | A11 |
| AD-16 | 7.3 | GET `/jobs` — job monitor | missing | | cto/cp-concierge-app | S7 | API | AR-02 |
| AD-17 | 7.3 | POST `/jobs/{id}/retry` | missing | | cto/cp-concierge-app | S7 | API | AR-02 |
| AD-18 | 7.3 | GET `/data-sources/status` — coverage, last refresh | missing | | cto/cp-concierge-app | S7 | API | A8 |
| AD-19 | 7.3 | GET `/flags` (superadmin) | missing | | cto/cp-concierge-app | S9 | API | DM-25 |
| AD-20 | 7.3 | PATCH `/flags` (superadmin) | missing | | cto/cp-concierge-app | S9 | API, DBT (audit) | DM-25 |
| AD-21 | 7.3 | GET `/data-requests` (superadmin) | missing | | cto/cp-concierge-app | S13 | API | DM-29 |
| AD-22 | 7.3 | POST `/data-requests/{id}/execute` (superadmin) | missing | | cto/cp-concierge-app + ciso | S13 | API, SR, LR | A12 |

### 7.4 HTML views (internal tool)

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| HV-01 | 7.4 | Login | done | `/login` (#7) | cto/cp-concierge-app | S1 | API, SR | — |
| HV-02 | 7.4 | Farmer list | done | `/farmers` (#7) | cto/cp-concierge-app | S1 | API | — |
| HV-03 | 7.4 | Farmer detail | done | `/farmers/{id}` (#7) | cto/cp-concierge-app | S1 | API | — |
| HV-04 | 7.4 | Field detail | done | `/fields/{id}` (#7) | cto/cp-concierge-app | S1 | API | — |
| HV-05 | 7.4 | New plan wizard | done | `/fields/{id}/plans/new` (#7) | cto/cp-concierge-app | S1 | API, GRD | — |
| HV-06 | 7.4 | Review queue | missing | | cto/cp-concierge-app | S2 | API, E2E | A1 |
| HV-07 | 7.4 | Review detail, side-by-side engine vs edit | partial | Plan page + versions by lineage (#7); no side-by-side diff | cto/cp-concierge-app + CPO/product-designer | S2 | API, E2E | A1 |
| HV-08 | 7.4 | PDF preview | missing | | cto/cp-pdf | S2 | API | AR-13 |
| HV-09 | 7.4 | Calibration dashboard | missing | | cto/cp-concierge-app | S5 | API | A2 |
| HV-10 | 7.4 | Packs | missing | | cto/cp-concierge-app | S4 | API | A3 |
| HV-11 | 7.4 | Products | missing | | cto/cp-concierge-app | S2 (v0), S4 | API | A4 |

## §8 Engine integration

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| EN-01 | 8 | Engine as library `run(EngineInput, Pack) -> EngineOutput`; no DB, no network | done | `recommend(RecommendationInput, Pack) -> Recommendation` (`engine/cloverproof_engine/engine.py`); name differs only | cto/cp-engine | S1 | UT | — |
| EN-02 | 8 | `services/recommendation_service.py` builds input from DB (season, **confirmed** soil or estimate, crop, region), loads active pack, stores `recommendation(status=in_review)` + full snapshot | partial | `planning.run_engine` + `repo/plans.py` (#7) build from the form, not from confirmed DB rows; no active-pack lookup; no status | cto/cp-concierge-app | S2 | UT, DBT | DM-13, UA-27 |
| EN-03 | 8 | Per-line explanation + confidence from engine; service never rewrites them silently | partial | Engine emits both per number (`results.py`); #7 edit recomputes split shares and marks them (commit c5bfdbc) — guard to confirm "not silent" | cto/cp-concierge-app + cp-agronomy-guard | S2 | GRD, UT | — |
| EN-04 | 8 | Pack resolution: farm country + crop → active pack; none → 422 with clear message | missing | Always the placeholder pack | cto/cp-concierge-app | S4 | API | DM-23 |
| EN-05 | 8 | Golden tests in CI on every pack change, `kind: agronomist_approved \| external_reference` | partial | Golden runs in `make test` (CI). No `kind` field; cases are `sample_*` (agronomist-todo #1). D4: `cp-agronomist` cases are `external_reference` + `ai_reviewed`, never `agronomist_approved` | cto/cp-engine + cp-agronomist | S2 | GT | REC-D4 |
| EN-06 | 8 | Engine version = semver + git SHA on every recommendation | partial | `ENGINE_VERSION = "0.2.0"` stored; git SHA not | cto/cp-engine + cp-platform | S2 | UT | — |

## §9 Proof documents

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| PD-01 | 9 | Worker renders HTML → WeasyPrint → storage `proofs/{season_id}/{uuid}.pdf` | superseded | ADR 0005 key `proof/{org_id}/{recommendation_id}/{sha256}.pdf` (DB check, mig 0008). Keep ADR 0005 key (DB-enforced); sync render in S2, worker in S4 | cto/cp-pdf | S2, S4 | UT, DBT | AR-02, AR-05 |
| PD-02 | 9 | Content: farm/field/season, inputs with sources + confidence, approved lines, explanations, reviewer + date, log (plan_with_log), engine/pack/template versions, document ID, SHA-256, verify URL | missing | Verify URL needs UA-40 (S11): print the URL from S2 only if the endpoint exists, else omit | cto/cp-pdf + cp-agronomy-guard | S2 (v0), S10 (log), S11 (URL) | UT, GRD, E2E | — |
| PD-03 | 9 | SHA-256 on final bytes, stored in `proof_document`; never regenerate into same row | partial | Column + immutability (mig 0008); generator missing | cto/cp-pdf | S2 | UT, DBT | — |
| PD-04 | 9 | Public verify confirms hash exists + when generated, nothing else | missing | | cto/cp-concierge-app | S11 | API, SR | UA-40 |
| PD-05 | 9 | Wording: "prepared with CloverProof and reviewed by an agronomist"; no third-party acceptance; legal disclaimer from lawyer | missing | D4: until a human agronomist reviews, wording must not say "reviewed by an agronomist" for AI-only reviews (`ai_reviewed`) | cto/cp-pdf + coo/legal + cp-agronomy-guard | S2 | GRD, LR | OQ-07 |
| PD-06 | 9 | English first; pack-provided strings later | partial | English only (CLAUDE.md); pack strings S27 | cto/cp-pdf | S2, S27 | UT | — |

## §10 Background jobs

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| JB-01 | 10 | `render_proof` on POST proofs; retry 3×; notify when done | missing | | cto/cp-pdf + cp-concierge-app | S4 | UT | AR-02 |
| JB-02 | 10 | `refresh_timing_windows` nightly 02:00 local per country; flag moves > 3 days | missing | ">3 days" is a product threshold, not agronomy — still confirm | cto/cp-concierge-app + cp-engine | S7 | UT | JB-03 |
| JB-03 | 10 | `fetch_weather` nightly, NASA POWER by grid cell for active seasons → `weather_daily` | missing | CLAUDE.md lists weather APIs as out of scope → CLAUDE.md change (REC-CL) | cto/cp-concierge-app + head-of-data/data-engineer | S4 | UT | DM-30, REC-CL |
| JB-04 | 10 | `refresh_calibration_view` nightly | missing | | cto/cp-database | S5 | DBT | DM-16 |
| JB-05 | 10 | `send_notifications` event-driven via Resend/Postmark (pick in S12) | missing | | cto/cp-concierge-app | S12 | UT | OQ-05 |
| JB-06 | 10 | `execute_data_request` export zip / cascade delete with audit | missing | | cto/cp-concierge-app + cp-database | S13 | DBT, SR | A12 |
| JB-07 | 10 | `extract_soil_report` (S20+) Docling → candidates → human confirm | missing | | head-of-data/llm-engineer | S20 | accuracy set | U6c |
| JB-08 | 10 | `cleanup_share_links` daily | missing | | cto/cp-concierge-app | S11 | UT | DM-20 |

## §11 External data and licences

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| XD-01 | 11 | `docs/data-sources.md` is the source of truth | missing | | head-of-data/data-governance-specialist | S2 | DR, LR | — |
| XD-02 | 11 | SoilGrids: offline cache only, no runtime API calls | missing | | cto/cp-engine + head-of-data/data-engineer | S3 | UT (no network) | AR-19 |
| XD-03 | 11 | LUCAS: raw values never leave the backend | missing | EU only; Canada launch (R4) → not needed until S27 | head-of-data/data-governance-specialist | S27 | SR | — |
| XD-04 | 11 | WoSIS: licence filter mandatory | missing | | head-of-data/data-engineer | S3 (if used) | UT | XD-01 |
| XD-05 | 11 | NASA POWER: cache by grid cell, record retrieval date | missing | | cto/cp-concierge-app | S4 | UT | DM-30 |
| XD-06 | 11 | Forecast provider: commercial licence before any farmer-facing forecast (decide S8) | missing | | FI + cso + coo/legal | S8 | DEC, LR | OQ-08 |
| XD-07 | 11 | No GPL/EUPL code in production without ADR + lawyer (PCSE, farmOS) | partial | No such deps today; no licence check in CI | cto/cp-platform + ciso | S2 | CI licence check | — |
| XD-08 | 11 | Every estimate stores source, version, resolution, depth, retrieved_at | missing | | cto/cp-database | S3 | DBT | DM-12 |

## §12 Security, privacy, compliance

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| SC-01 | 12 | AuthN; MFA required for agronomist, staff, superadmin | partial | D1: app auth (#7). `totp_secret` column (mig 0003), no TOTP flow. R3: MFA required, target S5 | cto/cp-concierge-app + ciso | S5 | API, SR | REC-R3 |
| SC-02 | 12 | AuthZ: RLS in DB + role checks in services; deny by default | partial | Role dependencies + org scoping (#7, mig 0004); no RLS (D1 adds it) | cto/cp-database + ciso | S2 | RLS, SR | DM-R1 |
| SC-03 | 12 | Secrets in env only; `.env.example`; rotate on team change | partial | `.env.example`, fail-fast settings (#7 `config.py`); rotation procedure missing | cto/cp-platform + ciso | S2 (procedure) | SR | — |
| SC-04 | 12 | HTTPS only; HSTS | missing | Railway gives HTTPS; HSTS header not set in app | cto/cp-concierge-app | S3 | LIVE | — |
| SC-05 | 12 | Private buckets; signed URLs ≤ 15 min | missing | | cto/cp-pdf + devops-engineer | S3 | API, SR | AR-05 |
| SC-06 | 12 | Audit all admin actions, grants, approvals, exports, deletions, support sessions | missing | Reviews are rows (approvals traceable); no `audit_event` | cto/cp-database | S2→ | DBT | DM-27 |
| SC-07 | 12 | Privacy law: PIPEDA (+ Ontario/Quebec); GDPR if EU — DPA template, records of processing, export/delete ≤ 30 days | partial | COO drafts on unpushed branch (privacy notice, terms, consent). Not lawyer-reviewed | coo/legal-compliance-specialist | S2–S4 | LR | OQ-07 |
| SC-08 | 12 | Data residency decided with launch country (ADR) | missing | R4: Canada; Railway has no Canadian region (ADR 0004). Decided 2026-11-16 (ADR 0009): Railway now, Canada later; host choice due 2027-01-04; migration S4 (`S4-PLT-01`), done before real farm data (Jan 18) | FI + ciso + coo/legal | S4 | DEC | OQ-06 |
| SC-09 | 12 | Backups: daily + weekly logical dump to separate storage; quarterly restore test | missing | D1: Railway volume backups instead of Supabase; dump destination undecided (ciso note) | cto/devops-engineer + ciso | S5 | RST | AR-03 |
| SC-10 | 12 | Rate limit `/public/*` per IP | partial | Login rate limiter exists (#7 `ratelimit.py`, in-process); public endpoints S11 | cto/cp-concierge-app | S11 | API | UA-40 |
| SC-11 | 12 | Dependabot + `pip-audit` in CI | partial | Done on unpushed ciso branch (`security.yml`, `dependabot.yml`); not on `main` | ciso/security-engineer + release-manager | S2 | CI | — |
| SC-12 | 12 | Pen test: self-run checklist before beta (S11); external before paid launch | missing | | ciso | S11, S29 | SR | — |
| SC-13 | 12 | Liability: terms "advice, not guarantee"; agronomist licensing verified in jurisdiction | missing | Ontario: CCA/agrologist question open (OQ-04) | coo/legal-compliance-specialist | S4 | LR | OQ-04, OQ-07 |

## §13 Observability and quality

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| OB-01 | 13 | Structured JSON logs with request_id, hashed user_id, org_id | missing | | cto/cp-concierge-app | S4 | UT | — |
| OB-02 | 13 | Sentry for app + worker (free tier, R7) | missing | | cto/cp-platform | S5 | LIVE | — |
| OB-03 | 13 | `/healthz` liveness, `/readyz` (DB + storage) | partial | `/healthz` (`main`); `/readyz` missing | cto/cp-concierge-app | S3 | API | — |
| OB-04 | 13 | Metrics: p95 latency, job failures, review minutes per plan, approve-without-edit rate | partial | Minutes stored; metric definitions (#5) | head-of-data/data-analyst + cto | S5 | DR | — |
| OB-05 | 13 | Tests: unit, RLS, API (httpx), e2e smoke on staging after deploy | partial | Unit + DB tests (`main`, #7: route tests with TestClient). No RLS, no staging smoke | cto/cp-qa | S3 | — | DM-R5 |
| OB-06 | 13 | Coverage: engine ≥ 90 %, services ≥ 75 % | missing | Not measured; add `pytest-cov` gate | cto/cp-platform + cp-qa | S2 | CI | — |
| OB-07 | 13 | Performance: engine < 500 ms; PDF < 10 s; API p95 < 300 ms | missing | | cto/cp-qa | S5 | PERF | — |

## §14 Environments, CI/CD, releases

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| EV-01 | 14 | local: `supabase start` + `make dev`, seed data | superseded | D1: `make db-up` (local PostGIS) + `make dev` + `db/seeds/dev.sql` (`main`) | cto/cp-platform | S1 | — | — |
| EV-02 | 14 | staging: Railway + Supabase #2; synthetic + anonymised data | superseded | D1: Railway `staging` environment (app, PostGIS, bucket). Not created; cost → FI go | cto/devops-engineer | S3 | LIVE | AR-03 |
| EV-03 | 14 | production: Railway + Supabase #1; real data | superseded | D1: Railway `production` environment. App not deployed | cto/devops-engineer | S5 | LIVE | EV-02 |
| EV-04 | 14 | CI: ruff, mypy (engine + services), tests, golden report, pip-audit | partial | CI runs `make lint` + `make test` incl. golden (`.github/workflows/ci.yml`). mypy, pip-audit missing on `main` | cto/cp-platform | S2 | CI | SC-11 |
| EV-05 | 14 | Migrations forward-only; CI applies to staging; manual approve for production | partial | Forward-only rule + runner (`migrate.py`); no CI apply, no approval step | cto/cp-platform + devops-engineer | S3 | LIVE | EV-02 |
| EV-06 | 14 | Release tag `vYYYY.MM.N`, changelog, prod deploys Mon–Thu | missing | | release-manager | S5 | DR | — |
| EV-07 | 14 | Freeze: no risky releases Feb 1–14 and peak N application windows | missing | Peak N window dates for Ontario wheat = agronomist input | release-manager + CPO | S5 | DEC | OQ-04 |

## §15 Sprint plan (S1–S30), every bullet + DoD

### 15.0 Cadence

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| SP-01 | 15 | Two-week sprints | done | D3 calendar adopted | CPO/project-manager | all | — | REC-D3 |
| SP-02 | 15 | Capacity: Founder/CTO part-time ≈ 20 h/week — **confirm**; Claude Code assisted | missing | OQ-03 open; delivery today is agent-run, Farjad Iranmehr's review time is the real bottleneck | FI | S1 | DEC | OQ-03 |
| SP-03 | 15 | S3 holiday sprint ≈ 50 % capacity | done | Recorded in calendar; roadmap's Dec 25–Jan 3 no-deploy freeze kept inside S3 (RK-X9) | CPO | S3 | — | — |
| SP-04 | 15 | Every sprint ends with a demo to the agronomist and/or team | partial | Roadmap learning loop (sprint review + retro) applies; demo to a **human** agronomist impossible until one is named (D4) | CPO + every head | all | DR | OQ-04 |

### Phase A — S1–S5

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| S01-G | 15 S1 | Goal: audit + skeleton + engine v0 + first plan end to end | partial | Skeleton + engine v0 + plan flow (#7); PDF + deploy missing | cto | S1 | E2E | — |
| S01-1 | 15 S1 | Audit existing MVP → ADR-0001 | done | ADR 0001 "start fresh" (R6) | cto | S1 | DEC | — |
| S01-2 | 15 S1 | Monorepo scaffold, CI, Makefile, pre-commit | done | `pyproject.toml`, `Makefile`, `.pre-commit-config.yaml`, `ci.yml` (`main`, PR #1) | cto/cp-platform | S1 | CI | — |
| S01-3 | 15 S1 | Migrations v0: profile, organisation, org_membership, farmer, farm, field, field_geometry_version, season, soil_sample, soil_measurement, recommendation, recommendation_line, review, proof_document, audit_event | partial | 0001–0009 cover 11 of 15 under other names; missing `recommendation_line`, `audit_event`, `profile` fields, season shape (R1 gap analysis) | cto/cp-database | S1–S2 | DBT | REC-R1 |
| S01-4 | 15 S1 | RLS v0 + tests (two users) | missing | D1 reinstated RLS; ADR 0008 first | cto/cp-database | S2 (slips from S1) | RLS | REC-D1 |
| S01-5 | 15 S1 | Engine v0: wheat, N only, placeholder pack, explanations, confidence | done | Engine 0.2.0 (`main`, PR #2), guard ACCEPT | cto/cp-engine | S1 | UT, GT, GRD | — |
| S01-6 | 15 S1 | Internal tool v0: farmer → field → season → soil (manual) → run engine → review (approve/edit/reject + reason + timer) | partial | All in #7 (open, under CISO fixes); not merged | cto/cp-concierge-app | S1 | API, E2E, SR | R8 |
| S01-7 | 15 S1 | PDF v0 (English, brand colours, SHA-256) | missing | Step 6 not started | cto/cp-pdf | S1→S2 | UT, GRD | AR-05 |
| S01-DoD | 15 S1 | DoD: 5 sample plans end to end; delta stored; minutes measured | partial | Delta (view) + minutes (column) exist; no 5-plan run recorded; PDF missing | cto/cp-qa | S1 (end Nov 27) | E2E | S01-6, S01-7 |
| S02-G | 15 S2 | Goal/business gate: launch country decided; first real pack | done (gate) | R4: Canada — Ontario winter wheat; Prairie wheat backup | FI | S2 | DEC | — |
| S02-1 | 15 S2 | Country pack v1 (real method, chosen country, crop 1) + golden tests (agronomist + external_reference) | missing | R5 + D4: method + structure from published Ontario sources by `cp-agronomist` (`ai_reviewed`); every constant stays PLACEHOLDER until a human validates | cto/cp-engine + cp-agronomist + cp-agronomy-guard | S2 | GT, GRD | REC-D4, OQ-04 |
| S02-2 | 15 S2 | `access_grant` model + RLS | missing | | cto/cp-database | S2 | DBT, RLS | DM-05, S01-4 |
| S02-3 | 15 S2 | Review queue page: sort, filter, side-by-side diff | missing | | cto/cp-concierge-app + CPO/product-designer | S2 | API, E2E | A1 |
| S02-4 | 15 S2 | Product catalog (A4) v0 + product matching in engine (need → product → quantity) | missing | Product grades are facts, not agronomy constants, but product choice rules are → guard | cto/cp-database + cp-engine | S2 | DBT, UT, GT, GRD | DM-24, DM-14 |
| S02-5 | 15 S2 | Split plan logic (pack-driven) | partial | Splits from pack (`packs/placeholder/v0.yaml` `splits`, PLACEHOLDER); per-line rows missing | cto/cp-engine | S2 | UT, GT | DM-14 |
| S02-6 | 15 S2 | `docs/data-sources.md` + open-data prompt tasks | missing | | head-of-data/data-governance-specialist + cto/cp-engine | S2 | DR, LR | XD-01 |
| S02-DoD | 15 S2 | DoD: the agronomist runs 5 real-format cases; ≥ 1 full PDF he would sign | missing | D4: "the agronomist" = human; `cp-agronomist` may run 5 published-reference cases (`ai_reviewed`) but cannot sign. Human sign-off → open | cto/cp-qa + FI | S2 | E2E | OQ-04 |
| S03-1 | 15 S3 | SoilGrids offline cache (launch-country bbox), `soil_estimate`, no-test path (N only, medium max) | missing | | cto/cp-engine + cp-database + head-of-data/data-engineer | S3 | UT, GT, GRD | DM-12, XD-02 |
| S03-2 | 15 S3 | P/K with soil test (pack-driven critical values, method-aware) | missing | Critical values = PLACEHOLDER (no invention); P/K never without lab test | cto/cp-engine + cp-agronomy-guard + cp-agronomist | S3 | UT, GT, GRD | S02-1 |
| S03-3 | 15 S3 | Unit conversions everywhere (P/P2O5, K/K2O, lb/ac ↔ kg/ha) | partial | `units.py` has all; display-side use missing | cto/cp-engine + cp-concierge-app | S3 | UT | — |
| S03-DoD | 15 S3 | DoD: same field with/without test → correct confidence + P/K "test recommended" | partial | True for N today (golden `sample_wheat_no_soil_test`); must re-prove with P/K | cto/cp-qa + cp-agronomy-guard | S3 | GT, E2E | S03-1, S03-2 |
| S04-1 | 15 S4 | `weather_daily` + NASA POWER fetch; GDD timing window per split | missing | GDD thresholds = PLACEHOLDER until validated; CLAUDE.md weather change | cto/cp-engine + cp-concierge-app | S4 | UT, GT, GRD | JB-03, DM-22 |
| S04-2 | 15 S4 | Soil report upload + "confirm values" (manual transcription; no OCR) | missing | | cto/cp-concierge-app | S4 | API, DBT | UA-26, UA-27 |
| S04-3 | 15 S4 | Pack registry (A3): upload, validate, golden report, activate | missing | | cto/cp-engine + cp-database + cp-concierge-app | S4 | GT, DBT, API | A3 |
| S04-4 | 15 S4 | Procrastinate worker (proof render async, weather fetch) | missing | Needs FI go on second Railway service | cto/cp-platform | S4 | UT, LIVE | AR-02 |
| S04-DoD | 15 S4 | DoD: timing window shown with basis + last refresh; pack activation audited | missing | | cto/cp-qa | S4 | E2E, DBT | S04-1, DM-27 |
| S05-1 | 15 S5 | Calibration dashboard (A2): delta per nutrient, minutes/plan, approve-without-edit | missing | | cto/cp-concierge-app + head-of-data/data-analyst | S5 | API, DR | A2 |
| S05-2 | 15 S5 | Backups verified (restore test), Sentry, health checks, staging = production config | missing | | cto/devops-engineer + ciso | S5 | RST, LIVE | SC-09, OB-02, OB-03 |
| S05-3 | 15 S5 | MFA for agronomist/staff; audit coverage review | missing | R3 | cto/cp-concierge-app + ciso | S5 | API, SR | SC-01, DM-27 |
| S05-4 | 15 S5 | Full rehearsal: 3 real farms entered end to end by the agronomist without help | missing | Needs a named human agronomist (D4: name before Jan 29) | cto/cp-qa + coo + FI | S5 | E2E | OQ-04 |
| S05-5 | 15 S5 | Bug bash; freeze list | missing | | cto/cp-qa + release-manager | S5 | E2E | — |
| S05-DoD | 15 S5 | **Concierge gate:** rehearsal done; median minutes/plan known; no P1 bugs open | missing | Release gate go/no-go = cp-qa + ciso + CPO (roadmap) | cto/cp-qa + ciso + CPO | S5 | E2E, SR | S05-1..5 |

### Phase B — S6–S12

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| S06-1 | 15 S6 | On-call fixes only + small UX fixes from the agronomist | missing | | cto/cp-concierge-app | S6 | E2E | S05-DoD |
| S06-2 | 15 S6 | Orgs & users admin (A5), audit log viewer (A7) | missing | Conflicts with "fixes only" field-season rule (roadmap) + Feb 1–14 freeze → ship behind flag after Feb 14 (RK-X8) | cto/cp-concierge-app | S6 | API | A5, A7 |
| S06-3 | 15 S6 | Second crop in pack (if decided) | missing | Decision owner FI | cto/cp-engine + cp-agronomist | S6 | GT, GRD | FI decision |
| S07-1 | 15 S7 | Job monitor (A9), data source status (A8) | missing | | cto/cp-concierge-app | S7 | API | A8, A9 |
| S07-2 | 15 S7 | Nightly timing refresh + "window moved" flag to agronomist | missing | | cto/cp-concierge-app | S7 | UT | JB-02 |
| S07-3 | 15 S7 | Plan revision flow (new version after approval, e.g. weather) | partial | Versioning via `parent_id` exists; revision after approval not tested | cto/cp-concierge-app + cp-database | S7 | DBT, API | DM-13 |
| S08-1 | 15 S8 | Support "view as" read-only + reason + audit (A6) | missing | | cto/cp-concierge-app + ciso | S8 | API, SR | A6 |
| S08-2 | 15 S8 | Forecast provider decision (licence) ADR; rain check if licensed | missing | | FI + cto/system-architect + coo/legal | S8 | DEC | OQ-08 |
| S08-3 | 15 S8 | Performance pass on review queue | missing | | cto/cp-qa | S8 | PERF | — |
| S09-1 | 15 S9 | Farmer invite + login; farmer sees ONLY approved plans | missing | CLAUDE.md: farmer-facing app out of scope → CLAUDE.md change by FI (REC-CL) | cto/cp-concierge-app | S9 | API, RLS, E2E | U1b, DM-R2, REC-CL |
| S09-2 | 15 S9 | Advisor accounts; access grants UI/API (grant/revoke/expire) | missing | | cto/cp-concierge-app | S9 | API, RLS | U3b |
| S09-3 | 15 S9 | Feature flags (A10): `farmer_portal`, `advisor_portal` | missing | | cto/cp-concierge-app | S9 | API | A10 |
| S09-4 | 15 S9 | Units + locale preferences honoured in API | missing | | cto/cp-concierge-app | S9 | API | AC-08 |
| S10-1 | 15 S10 | Application log API + mobile-friendly pages (planned vs actual, photo, 24 h lock + corrections) | missing | D2: web stays mobile-friendly; native app later | cto/cp-concierge-app | S10 | API, DBT, E2E (375 px) | DM-18 |
| S10-2 | 15 S10 | Link log entries to recommendation lines | missing | | cto/cp-database | S10 | DBT | DM-14 |
| S10-3 | 15 S10 | Proof kind `plan_with_log` | missing | | cto/cp-pdf | S10 | UT, GRD | DM-19 |
| S11-1 | 15 S11 | Share links + public verify + rate limits | missing | | cto/cp-concierge-app + ciso | S11 | API, SR | U11b |
| S11-2 | 15 S11 | Self-run security checklist (OWASP ASVS L1 subset), dependency audit | missing | | ciso/security-engineer | S11 | SR | — |
| S11-3 | 15 S11 | Terms + privacy wired into onboarding (lawyer text) | missing | | cto/cp-concierge-app + coo/legal | S11 | LR, E2E | OQ-07 |
| S12-1 | 15 S12 | Notifications (approved, window update, log reminder); email provider chosen | missing | | cto/cp-concierge-app | S12 | UT, LIVE | OQ-05 |
| S12-2 | 15 S12 | Intermediary dashboard API: org list of farmers, fields, plan status, pending logs | missing | | cto/cp-concierge-app | S12 | API, RLS | — |
| S12-3 | 15 S12 | Beta onboarding 2–3 intermediaries; seed 10–20 farms | missing | | coo/customer-onboarding-specialist + cro/partnerships-manager | S12 | E2E | — |
| S12-DoD | 15 S12 | **MVP gate:** 10–20 farms live; farmer can view plan, log application, export proof | missing | | cto/cp-qa + CPO | S12 | E2E | S09–S12 |

### Phase C — S13–S24 (pilot season)

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| SPC-0 | 15 C | Rule: stability over features; 40 % capacity for pilot support every sprint | missing | | CPO + cto | S13–S24 | DR | — |
| S13-1 | 15 S13 | Data rights: export/delete requests (U14, A12) | missing | | cto + coo/legal + ciso | S13 | API, DBT, LR | U14, A12 |
| S13-2 | 15 S13 | Incident runbook | missing | | ciso + cto/devops-engineer | S13 (draft by S5) | DR | — |
| S14-1 | 15 S14 | Second/third split timing updates | missing | | cto/cp-engine + cp-concierge-app | S14 | UT, GRD | S04-1 |
| S14-2 | 15 S14 | In-season plan revisions at scale | missing | | cto/cp-concierge-app | S14 | API, PERF | S07-3 |
| S15-1 | 15 S15 | Advisor bulk actions (multi-field request; bulk approve view with per-plan sign-off) | missing | Per-plan sign-off keeps rule 8 | cto/cp-concierge-app | S15 | API, DBT | — |
| S16-1 | 15 S16 | Pilot metrics (A11) | missing | | head-of-data/data-analyst + cto | S16 | API, DR | A11 |
| S17-1 | 15 S17 | Outcomes (U13): yield, "followed plan?" | missing | | cto/cp-concierge-app | S17 | API | U13 |
| S18-1 | 15 S18 | Field geometry: draw/upload boundary (GeoJSON/Shapefile/KML) | missing | CLAUDE.md: map drawing out of scope → REC-CL | cto/cp-concierge-app | S18 | API, DBT, SR (file parsing) | UA-19 |
| S18-2 | 15 S18 | Area from geometry | missing | | cto/cp-database | S18 | DBT | DM-08 |
| S19-1 | 15 S19 | Field boundary pre-fill spike (Fields of The World, country subset), behind flag | missing | Licence check first | head-of-data/ml-engineer + cto | S19 | DR, LR | XD-01 |
| S20-1 | 15 S20 | Soil report extraction spike (Docling) on 30+ reports; human confirm mandatory; define target accuracy | missing | | head-of-data/llm-engineer | S20 | accuracy set | U6c |
| S21-1 | 15 S21 | Extraction v1 if spike ≥ target; else drop | missing | | head-of-data/llm-engineer + cto | S21 | accuracy set, API | S20-1 |
| S22-1 | 15 S22 | Previous-crop suggestion (AAFC ACI / EuroCrops) — suggestion only | missing | | head-of-data/data-engineer | S22 | UT | XD-01 |
| S23-1 | 15 S23 | Harvest data import (CSV) | missing | | cto/cp-concierge-app | S23 | API | DM-21 |
| S23-2 | 15 S23 | Season close | missing | | cto/cp-concierge-app | S23 | API | — |
| S23-3 | 15 S23 | Archive | missing | | cto/cp-database | S23 | DBT | — |
| S24-1 | 15 S24 | Pilot report data pack: calibration, outcomes, minutes/plan → decision memo | missing | | head-of-data + CPO | S24 | DR | A2, A11 |
| S24-B | 15 S24 | Oct 25–29 buffer / retro | missing | | CPO | S24+ | — | — |

### Phase D — S25–S30

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| S25-1 | 15 S25 | Sampling kit QR → lab result flow (U15) | missing | | cto | S25 | API | U15 |
| S25-2 | 15 S25 | Lab partner role | missing | | cto/cp-database | S25 | RLS | RO-05 |
| S26-1 | 15 S26 | Billing plans per farm/advisor (U16, A13) | missing | | cto + cso | S26 | API | OQ-09 |
| S26-2 | 15 S26 | Stripe | missing | Paid service → FI go | cto + FI | S26 | API, SR | OQ-09 |
| S26-3 | 15 S26 | Invoices | missing | | cto + coo/finance-accounting-specialist | S26 | API | S26-2 |
| S26-4 | 15 S26 | Tax | missing | | coo/finance-accounting-specialist | S26 | LR | S26-2 |
| S27-1 | 15 S27 | Second country pack (config only) | missing | | cto/cp-engine + cso | S27 | GT, GRD | A3 |
| S27-2 | 15 S27 | i18n strings in PDF | missing | | cto/cp-pdf | S27 | UT | PD-06 |
| S28-1 | 15 S28 | First lab API integration (holiday 50 %) | missing | | cto + cso/partnerships-manager | S28 | API | U15 |
| S29-1 | 15 S29 | Self-serve onboarding (behind flag) | missing | | cto/cp-concierge-app | S29 | E2E | A10 |
| S29-2 | 15 S29 | External pen test fixes | missing | External pen test = paid → FI go | ciso | S29 | SR | SC-12 |
| S30-1 | 15 S30 | Launch hardening | missing | | cto | S30 | E2E | — |
| S30-2 | 15 S30 | Load test | missing | | cto/cp-qa | S30 | PERF | — |
| S30-3 | 15 S30 | Runbooks | missing | | cto/devops-engineer + coo | S30 | DR | — |
| S30-4 | 15 S30 | v1 release | missing | | release-manager | S30 | LIVE | — |

## §16 Definition of Ready / Done

| ID | § | Requirement | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| DR-01 | 16 DoR | User story + acceptance criteria written | partial | Webapp steps have exit criteria (webapp-v1 §4); no story backlog (`docs/backlog.md`) | CPO/agile-manager | S2 | DR | AR-34 |
| DR-02 | 16 DoR | Data model impact known; migration sketched | partial | Done for Step 4/5; make it a template field | CPO/agile-manager + cto/cp-database | S2 | DR | — |
| DR-03 | 16 DoR | Permissions defined (roles, RLS impact) | missing | §3.2 rows give the target per cell | CPO/agile-manager + cto | S2 | DR | DM-R1 |
| DR-04 | 16 DoR | Agronomic rules confirmed by the agronomist or marked PLACEHOLDER | done | Enforced: PLACEHOLDER + `TODO(agronomist)`, `test_no_agronomy_literals.py`, guard | cto/cp-agronomy-guard | S1 | GRD, UT | — |
| DD-01 | 16 DoD | Code + tests merged; CI green; golden report unchanged or explained | partial | CI green on `main`; merges via release-manager only | cto + release-manager | all | CI, GT | — |
| DD-02 | 16 DoD | RLS tests for any new table | missing | No RLS yet | cto/cp-database + cp-qa | S2→ | RLS | DM-R5 |
| DD-03 | 16 DoD | Audit events for any admin/sensitive action | missing | No `audit_event` | cto/cp-database | S2→ | DBT | DM-27 |
| DD-04 | 16 DoD | OpenAPI updated; ADR written if a decision was made | partial | ADRs yes; no API → no OpenAPI yet | cto | S4→ | DR | AC-01 |
| DD-05 | 16 DoD | Deployed to staging and demoed | missing | No staging | cto/devops-engineer | S3→ | LIVE | EV-02 |
| DD-06 | 16 DoD | No new "unknown" licence in production | partial | No licence scan in CI (XD-07) | cto/cp-platform + ciso | S2 | CI | XD-07 |

## §17 Risks (plan) — mitigation owner

| ID | § | Risk → mitigation | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| RK-01 | 17 | Launch country not decided by Dec 11 → pack is config; placeholder labelled; escalate Dec 11 | done | R4 decided Canada/Ontario on Nov 16 | FI / CPO | S2 | DEC | — |
| RK-02 | 17 | Agronomist time bottleneck → measure minutes from S1; optimise review UI; second reviewer plan | partial | Minutes recorded; **no human agronomist named** (D4) — worse than the plan assumed | CPO + coo/operations-manager + head-of-data | S1→S5 | PERF | OQ-04 |
| RK-03 | 17 | CTO capacity → strict scope; cut Phase C first, never Phase A | partial | S1 already overruns (RLS, PDF → S2) | CPO + cto | every sprint | DR | OQ-03 |
| RK-04 | 17 | SoilGrids API instability → offline cache | missing | | cto/cp-engine + head-of-data/data-engineer | S3 | UT | XD-02 |
| RK-05 | 17 | Licence problems (forecast, GPL) → `data-sources.md`, ADRs, lawyer before beta | missing | | head-of-data/data-governance-specialist + coo/legal | S2, S8 | LR | XD-01 |
| RK-06 | 17 | Unit/method errors in soil data → mandatory method/form/depth; conversion tests; agronomist gate | partial | DB + engine enforce method/form/depth; conversion tests in `test_units.py` | cto/cp-engine + cp-database + cp-agronomy-guard | S1→ | UT, DBT, GRD | — |
| RK-07 | 17 | Liability for advice → review gate, terms, credentials checked | partial | Gate in DB; terms/credentials open | coo/legal-compliance-specialist | S4 | LR | OQ-04, OQ-07 |
| RK-08 | 17 | Free official tools (e.g. Ontario AgriSuite) → value = proof, log, workflow, intermediaries; measure in pilot | missing | Ontario launch makes this risk sharper | cso/business-strategist + head-of-data | S3 (positioning), S24 | DR | — |

## §18 Open questions

| ID | § | Question | Status | Evidence / answer | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| OQ-01 | 18 | Existing MVP: keep or rewrite? | done | R6: none; ADR 0001 start fresh | — | S1 | DEC | — |
| OQ-02 | 18 | Launch country + first crop (by Dec 11) | done | R4: Canada — Ontario winter wheat; Prairie wheat backup | — | S2 | DEC | — |
| OQ-03 | 18 | CTO weekly capacity; second developer? | missing | Open | FI | S1 | DEC | — |
| OQ-04 | 18 | The agronomist: hours/week Feb–Apr; credentials valid in jurisdiction | missing | Open; D4: name the human before Jan 29 (S5). Also: is Farjad Iranmehr (named agronomist in CLAUDE.md) that human? | FI | S2 (latest S4) | DEC | — |
| OQ-05 | 18 | Email provider + sender domain | missing | Open; needed S9 (invites) / S12 | FI | S8 | DEC | — |
| OQ-06 | 18 | Data residency (EU vs Canada) | missing | Open; Canada launch + Railway US-only → decide before real farm data (S5) | FI | S3 | DEC | — |
| OQ-07 | 18 | Legal disclaimer + terms — who drafts, by when | missing | Open; COO drafts exist (unpushed, not lawyer-reviewed) | FI | S3 | DEC, LR | — |
| OQ-08 | 18 | Forecast provider + licence budget | missing | Open; decide S8 | FI | S8 | DEC | — |
| OQ-09 | 18 | Billing model (per farm / advisor seat / plan) for S26 | missing | Open; `cso` prepares options | FI (cso prepares) | S24 | DEC | — |

## Reconciliation actions (D1–D4, R1–R9) and CLAUDE.md alignment

| ID | Source | Action created | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| REC-D1 | D1 | ADR 0008 "Postgres RLS on Railway" (SET LOCAL app.* from server session; `cp_app` non-bypass role); bucket; read every Supabase mention as Railway | missing | No ADR 0008 yet | cto/cp-database + system-architect + ciso | S2 | DEC, RLS, SR | — |
| REC-D2 | D2 | Native app planned by `head-of-mobile` from S11 (stack ADR, offline sync), build after S12 | missing | | head-of-mobile | S11 | DEC | AC-02 |
| REC-D3 | D3 | S1–S30 master calendar; roadmap gates + learning loop merged | partial | Roadmap header updated (`main`); per-group mapping = section below | CPO | S1 | DR | — |
| REC-D4 | D4 | `ai_reviewed` label; approve on a real farm requires a **human** agronomist; real-farm plans stay `in_review` until one is named | missing | Needs: `app_user.is_human`/`kind` (or separate role), `review.review_kind`, golden `kind`, PDF wording | cto/cp-database + cp-concierge-app + cp-engine | S2 | DBT, API, GT | — |
| REC-R1 | R1 | `cp-database` gap analysis §6 vs schema, then forward-only migrations | missing | Inputs: rows DM-01..DM-30 | cto/cp-database | S1–S2 | DBT | — |
| REC-R2 | R2 | Implement `recommendation_line`; drop P/K-columns proposal (0011) | missing | Proposal in shared notes superseded | cto/cp-database | S2 | DBT | DM-14 |
| REC-R3 | R3 | MFA required for agronomist/staff/superadmin by S5 | missing | | cto/cp-concierge-app + ciso | S5 | SR | SC-01 |
| REC-R4 | R4 | Canada/Ontario pack; residency decision open | partial | Country decided; residency open | FI + ciso | S3 | DEC | OQ-06 |
| REC-R5 | R5 | Plan's engine scope replaces webapp-v1 scope; all constants PLACEHOLDER until human validation | partial | `webapp-v1.md` §2 still says N only — update text | CPO + cto | S2 | DR | — |
| REC-R6 | R6 | No MVP → S1 audit closed | done | ADR 0001 | — | S1 | — | — |
| REC-R7 | R7 | Sentry free tier allowed; paid needs FI | done | Recorded | cto/cp-platform | S5 | — | — |
| REC-R8 | R8 | Carry auth-review findings (A1, S1–S8) into S2/S3 | partial | Findings doc on **unpushed** ciso branch; #7 open | ciso + cto/cp-concierge-app + release-manager | S2 | SR | — |
| REC-R9 | R9 | Get `05-mvp-build-brief.md`, `03-roadmap-and-validation.md` | missing | Requested from FI | FI | S2 | — | — |
| REC-CL | CLAUDE.md | Update CLAUDE.md scope: weather APIs (S4), farmer accounts (S9), map drawing (S18), OCR/extraction (S20), payments (S26), RLS (D1), Railway (ADR 0004), AI agronomist (D4) | missing | CLAUDE.md still lists these as out of scope / Supabase | FI (CPO drafts) | S2 (before S4 work) | DR | — |

## Non-backend work on the same S1–S30 calendar (D2, D3)

Source: `docs/sprints/roadmap.md` group content (dates re-mapped to S1–S30), plan §15 items owned by other groups, and the shared session notes. Test gates from the roadmap apply unchanged.

| ID | Group | Work | Status | Evidence / gap | Owner | Sprint | Test | Depends on |
|---|---|---|---|---|---|---|---|---|
| NB-WEB-01 | Website | Website v1 live, 8-locale scaffold, en enabled | done | Live on Railway (ADR 0003/0004) | cto/cp-website | S1 | LIVE, Lighthouse | — |
| NB-WEB-02 | Website | SEO basics, Lighthouse ≥ 90 mobile, a11y pass | partial | Commits on `website-v1` (62310a5, bdeb4a6); not on `main` | cto/cp-website + release-manager | S2 | LIVE | — |
| NB-WEB-03 | Website | Stop logging raw pg error with PII (`actions.ts`) | missing | ciso finding | cto/cp-website | S2 | SR | — |
| NB-WEB-04 | Website | Move `pilot_request` to shared PostGIS DB; drop website's own migrate | missing | Blocked: Railway PostGIS service + least-privilege website role (ciso blocker) | cto/cp-website + cp-database + FI | S2 | LIVE, RST | AR-03 |
| NB-WEB-05 | Website | Privacy page copy (from coo) after approval; legal entity + contact | missing | Draft in shared notes | cto/cp-website + coo/legal | S3 | LR | OQ-07 |
| NB-WEB-06 | Website | First-party pilot funnel events (cro proposal, $0) + `pilot_request` status columns | missing | Needs CPO→cto decision | cto/cp-website + cp-database | S3 | DBT | — |
| NB-WEB-07 | Website | French locale (native review) | missing | | cto/cp-website | S4 | LIVE | native reviewer |
| NB-WEB-08 | Website | Italian + Spanish locales | missing | | cto/cp-website | S6–S10 | LIVE | — |
| NB-WEB-09 | Website | Bulgarian, Finnish, Turkish, Arabic (RTL) | missing | | cto/cp-website | S13+ | LIVE | — |
| NB-WEB-10 | Website | Link to public proof verify page; farmer sign-in link | missing | | cto/cp-website | S11 | LIVE | UA-40 |
| NB-GRO-01 | Growth | Pilot ICP, recruitment plan, funnel tracking spec | partial | Drafts on unpushed `myca/growth-s2-a73813` | cro | S2 | DR | — |
| NB-GRO-02 | Growth | Outreach drafts (never sent without FI), partner shortlist (labs, agronomy firms, co-ops) | missing | | cro/sales-development-rep + partnerships-manager | S3–S4 | DR | — |
| NB-GRO-03 | Growth | 5–10 pilot farms confirmed (Ontario) by Jan 15 | missing | | cro + coo | S4 | DR | NB-GRO-02 |
| NB-GRO-04 | Growth | 2–3 beta intermediaries recruited | missing | | cro/partnerships-manager | S11–S12 | DR | — |
| NB-GRO-05 | Growth | Pilot stories/case material — no third-party acceptance claims | missing | | cro/content-seo-strategist | S16–S24 | GRD | — |
| NB-GRO-06 | Growth | Launch v1 marketing, SEO content, email channel | missing | | cro | S27–S30 | DR | — |
| NB-OPS-01 | Operations | Pilot SOP, intake checklist, privacy notice + terms + consent, support FAQ | partial | Drafts on unpushed `myca/ops-s2-f4aad3`; not lawyer-reviewed | coo | S2 | LR | — |
| NB-OPS-02 | Operations | Agronomist workload model, onboarding messages, grants radar | partial | Drafts (same branch) | coo | S3–S5 | DR | — |
| NB-OPS-03 | Operations | Agronomist credentials + liability (Ontario) | missing | | coo/legal-compliance-specialist | S3–S4 | LR | OQ-04 |
| NB-OPS-04 | Operations | Support macros + training for concierge; go/no-go input | missing | | coo/customer-support-specialist | S5 | DR | — |
| NB-OPS-05 | Operations | Concierge operations: intake → plan → delivery; support digest every sprint | missing | Learning loop step 5 | coo | S6–S10 | DR | S05-DoD |
| NB-OPS-06 | Operations | Erasure procedure vs immutable tables; consent records; purge job design | missing | With cp-database + ciso | coo/legal + cto/cp-database + ciso | S4 (design), S13 (build) | LR, SR | U14 |
| NB-OPS-07 | Operations | Beta onboarding of intermediaries + 10–20 farms | missing | | coo/customer-onboarding-specialist | S12 | E2E | — |
| NB-OPS-08 | Operations | Finance/tax for billing; invoices | missing | | coo/finance-accounting-specialist | S26 | LR | OQ-09 |
| NB-OPS-09 | Operations | Runbooks for launch (support, incident comms) | missing | | coo + ciso | S30 | DR | — |
| NB-DAT-01 | Data | Metric definitions, data dictionary, PII + retention, calibration loop | partial | #5 (open) | head-of-data | S2 | DR | — |
| NB-DAT-02 | Data | `docs/data-sources.md` (licences, SoilGrids/NASA POWER/WoSIS) | missing | = XD-01 | head-of-data/data-governance-specialist | S2 | LR | — |
| NB-DAT-03 | Data | Calibration baseline from first real cases | missing | Needs human-agronomist cases (D4) | head-of-data/data-scientist | S3–S5 | DR | OQ-04 |
| NB-DAT-04 | Data | Dashboard definitions for A2 (with cp-concierge-app) | missing | | head-of-data/data-analyst | S5 | DR | A2 |
| NB-DAT-05 | Data | Calibration review every sprint (learning loop step 3) | missing | Mandatory S6–S10, continues S13–S24 | head-of-data/data-scientist | S6–S24 | DR | A2 |
| NB-DAT-06 | Data | Pilot metrics (A11) definitions + analysis | missing | | head-of-data/data-analyst | S16 | DR | A11 |
| NB-DAT-07 | Data | Extraction spike, boundary pre-fill, previous-crop suggestion | missing | = S19-1, S20-1, S22-1 | head-of-data | S19–S22 | accuracy set | REC-CL |
| NB-DAT-08 | Data | Pilot report data pack → decision memo | missing | = S24-1 | head-of-data | S24 | DR | — |
| NB-SEC-01 | Security | Threat model, Step 5 auth review, secret/dependency scan, CI security | partial | Unpushed `myca/security-s2-bb8ef7` (a49da95) | ciso + release-manager | S2 | SR | — |
| NB-SEC-02 | Security | Review ADR 0008 RLS-on-Railway + RLS test suite | missing | | ciso/security-engineer | S2–S3 | SR | REC-D1 |
| NB-SEC-03 | Security | Backup/restore test; pre-release gate (with cp-qa + CPO) | missing | | ciso + devops-engineer | S5 | RST, SR | SC-09 |
| NB-SEC-04 | Security | Data residency + Railway DPA recommendation | missing | | ciso + coo/legal | S3 | DEC | OQ-06 |
| NB-SEC-05 | Security | View-as review (S8), ASVS L1 (S11), incident runbook (S13), external pen test (S29) | missing | | ciso | S8, S11, S13, S29 | SR | — |
| NB-MOB-01 | Mobile | No build S1–S10 (D2): mobile-friendly web covers field use | done | Held | head-of-mobile | S1–S10 | — | — |
| NB-MOB-02 | Mobile | Stack ADR (Expo vs Flutter vs native) + offline/sync architecture; API auth needs (AC-02) | missing | | head-of-mobile/mobile-architect | S11 | DEC | REC-D2 |
| NB-MOB-03 | Mobile | Build native app (application log offline first) after MVP gate, scheduled by CPO | missing | | head-of-mobile | S13+ | mobile QA | NB-MOB-02 |
| NB-STR-01 | Strategy | Positioning one-pager + competitor scan (incl. Ontario AgriSuite) | missing | | cso | S3 | DR | RK-08 |
| NB-STR-02 | Strategy | Billing model options → FI decision (OQ-09) | missing | | cso/business-strategist | S24–S25 | DEC | — |
| NB-STR-03 | Strategy | Second country choice + lab partnerships | missing | | cso | S25–S27 | DEC | — |
| NB-PRD-01 | Product | `docs/backlog.md` with stories (DoR) | missing | | CPO/agile-manager | S2 | DR | AR-34 |
| NB-PRD-02 | Product | Review queue + side-by-side diff design (Stitch) | missing | | CPO/product-designer + cp-design | S2 | DR | A1 |
| NB-PRD-03 | Product | Farmer/advisor portal PRD + JTBD research | missing | | CPO/cp-product-manager + ux-researcher | S7–S8 | DR | — |
| NB-DOC-01 | Docs | Record D1–D4, R1–R9, this matrix and distribution in Notion | missing | | documentation-manager | S1 | DR | — |
| NB-DOC-02 | Docs | Standard report per head per sprint → Notion work/decision log | partial | Reports exist in shared notes; Notion sync by `documentation` session | documentation-manager | every sprint | DR | — |

## Conflicts and risks found while building this matrix (CTO)

| ID | Conflict / risk | Rows | Proposed resolution | Decider |
|---|---|---|---|---|
| RK-X1 | **No human agronomist.** D4 makes every real-farm approval, S2 DoD ("he would sign"), S5 rehearsal and the calibration dataset depend on a named human. CLAUDE.md names Farjad Iranmehr as the agronomist; D4 says AI until a human is named — which is it? | OQ-04, S02-DoD, S05-4, REC-D4 | Confirm whether Farjad Iranmehr counts as the human agronomist; if not, name one by S4 | FI |
| RK-X2 | **CLAUDE.md scope vs plan.** Weather APIs (S4), farmer accounts (S9), map drawing (S18), OCR/extraction (S20), payments (S26) are out of scope in CLAUDE.md; Supabase still named there | REC-CL | CPO drafts CLAUDE.md update; FI approves before S4 | FI |
| RK-X3 | **Erasure vs immutability.** Hard delete / data rights vs triggers that block DELETE on recommendation/review/proof | PM-HD-sa, U14, A12, NB-OPS-06 | Design in S4 (crypto-shredding or de-identification of snapshot + documented migration), build S13 | cto + coo + ciso |
| RK-X4 | **`recommendation.status` on an immutable row.** Status cannot change without UPDATE | DM-13, DM-R2 | Status derived from `review` rows in a view (`recommendation_state`); RLS uses the view/function | cto/cp-database |
| RK-X5 | **Season vs crop_plan.** §6 puts crop/yield on `season` per field; CLAUDE.md + current schema use org `season` → `crop_plan` | DM-09, U5 | Gap analysis: keep `crop_plan` as §6 "season" equivalent (rename in docs), add field/year uniqueness; no data loss | cto/cp-database → CPO |
| RK-X6 | **Railway infra not provisioned.** PostGIS service (agents denied), bucket, worker service, staging env all need FI action or go (cost) | AR-03, AR-05, AR-12, EV-02 | FI creates PostGIS service now (runbook), approves bucket + worker + staging budget | FI |
| RK-X7 | **access_grant "immutable history" vs `revoked_at`.** | DM-05 | Insert-only rows; revoke = new row (`action = revoke`) or one-time set enforced by trigger | cto/cp-database |
| RK-X8 | **Feature work during the concierge season.** Plan builds A5/A7 (S6), farmer accounts (S9), app log (S10) during Feb–Apr; roadmap said "fixes only", §14 freeze Feb 1–14 | S06-2, S09-*, S10-* | Build behind flags, deploy outside freeze, never touch the review path during Feb 1–14 | CPO |
| RK-X9 | **Holiday:** S3 runs to Jan 1 but roadmap freezes deploys Dec 25–Jan 3 | SP-03 | Keep freeze; S3 code merges by Dec 23 | CPO |
| RK-X10 | **Unpushed work.** ciso, coo, cro S2 outputs exist only on local branches; R8 findings not on remote; #7 open with CISO SHOULD-FIX items | REC-R8, NB-SEC-01, NB-OPS-01, NB-GRO-01 | release-manager pushes + opens PRs; #7 merges only after R8 fixes | CPO / release-manager |
| RK-X11 | **Role model mismatch.** Current org roles owner/agronomist/staff/farmer vs plan org_admin/advisor/agronomist + platform staff/superadmin; superadmin "approve" vs D4 | RO-*, PM-AP-sa, PM-DR-oa | Map in ADR 0008: owner→org_admin; staff→platform role; superadmin cannot approve unless human agronomist | cto → CPO |
| RK-X12 | **S1 overrun / S2 overload.** RLS v0 and PDF v0 slip to S2, which also carries pack v1, access_grant, queue, catalog, product matching, splits, line table | S01-4, S01-7, S02-* | Product matching (S02-4 engine part) can move to S3 if needed; never cut RLS or PDF | CPO + cto |
| RK-X13 | **API auth for native app** undefined after D1 (no JWT) | AC-02, NB-MOB-02 | ADR by S8, before S9 API | cto + ciso + head-of-mobile |
| RK-X14 | **Data residency** before real farm data (S5) with US-only Railway | SC-08, OQ-06 | Decide by S3; consent text names the US (coo draft already does) | FI |
| RK-X15 | **DB access library** psycopg vs plan's SQLAlchemy/asyncpg | AR-10 | Keep psycopg + hand SQL (works, tested); record in ADR 0008 | cto |

## Self-check — plan items vs matrix rows

Counted by section from `backend-plan.md` v1.0 (atomic items as defined in the column "Plan items"), then by ID prefix in this file.

| Section | Plan items | Matrix rows | Gap |
|---|---|---|---|
| §1 goals (5) + non-goals (6) | 11 | 11 (GL-01..11) | 0 |
| §2 constraints | 10 | 10 (HC-01..10) | 0 |
| §3.1 roles | 7 | 7 (RO-01..07) | 0 |
| §3.2 matrix cells (12 resources × 6 roles) + grant note | 73 | 73 (PM-*) | 0 |
| §4.1 components (7) + §4.2 stack rows (9) + region note (1) + §4.3 layout entries (18) | 35 | 35 (AR-01..35) | 0 |
| §5 modules U1–U16 + A1–A13 | 29 | 34 (U1a/b, U3a/b, U6a/b/c, U11a/b split by sprint) | 0 (+5 splits) |
| §6 conventions (6) + tables (29) + RLS bullets (5) | 40 | 41 (DM-C1..C6, DM-01..30 incl. rule row DM-17, DM-R1..R5) | 0 (+1 rule row) |
| §7 conventions (8) + user endpoints (44) + review (5) + admin (22) + views (11) | 90 | 90 (AC, UA, RV, AD, HV) | 0 |
| §8 engine integration | 6 | 6 (EN) | 0 |
| §9 proof documents | 6 | 6 (PD) | 0 |
| §10 jobs | 8 | 8 (JB) | 0 |
| §11 external data | 8 | 8 (XD) | 0 |
| §12 security rows | 13 | 13 (SC) | 0 |
| §13 observability | 7 | 7 (OB) | 0 |
| §14 environments (3) + bullets (4) | 7 | 7 (EV) | 0 |
| §15 cadence (4) + S1–S30 bullets, goals and DoDs (89) | 93 | 93 (SP, S01..S30, SPC, S24-B) | 0 |
| §16 DoR (4) + DoD (6) | 10 | 10 (DR, DD) | 0 |
| §17 risks | 8 | 8 (RK-01..08) | 0 |
| §18 open questions | 9 | 9 (OQ) | 0 |
| **Plan total** | **470** | **476** | **0 missing** |
| Reconciliation + CLAUDE.md actions | 14 | 14 (REC) | — |
| Non-backend calendar | — | 49 (NB) | — |
| CTO conflicts | — | 15 (RK-X) | — |

§19 (glossary) defines terms only; no requirements.
