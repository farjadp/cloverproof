# CloverProof backlog: S2–S3 (Nov 30 → Jan 1, 2027)

Owner: `product-manager` (CPO), written by the Product Owner role (matrix AR-34 / NB-PRD-01; fulfils DoR items DR-01, DR-02, DR-03). Date: 2026-11-16. Status: v1 for CPO review.

## Purpose

One backlog of INVEST stories that covers every engineering matrix ID in sections 1A–1H of `docs/plans/backend-distribution.md` plus its "Standing" line. Each story names its data-model impact, permission/RLS impact and agronomic rules so it meets the Definition of Ready. Source rows: `docs/plans/backend-traceability.md`. Where documents disagree, `docs/plans/backend-plan-reconciliation.md` (D1–D4, R1–R9) wins, then `CLAUDE.md` hard rules.

Screens for the review queue and the engine-vs-edit diff are specified in `docs/design/review-queue.md` (being written in parallel by product-designer + cp-design). Stories A1 / RV-* (S2-APP-01 to S2-APP-05) reference it; no UI work starts before it exists.

## How to read

- **Story ID:** `<sprint>-<workstream>-<nn>`. Workstream: DB = 1B, ENG = 1C, APP = 1D, PDF = 1E, PLT = 1F, QA = 1G, WEB = 1H, `S1C` = S1-close items from 1A (tagged "S1 carry-over → S2" if not done by Nov 27), `STD` = standing.
- **Size:** S / M / L = about 1–2 hours / half a day / one agent day (nothing larger; larger work is already split into thin slices). Points: S=1, M=2, L=3.
- **Test codes:** UT unit · GT golden · DBT migration + DB test · RLS two-user policy test · API route test · E2E cp-qa walkthrough · GRD agronomy-guard review · SR security review · LR legal review · DEC decision recorded · DR document review · LIVE checked on staging/production · CI pipeline check · RST restore test.
- **RLS two-user convention:** every policy gets a pytest test where user A (allowed) and user B (different org or denied role) run against the same data through `cp_app` with `SET LOCAL app.user_id/app.org_id/app.platform_role`; the denied case must return zero rows or fail. Stories write "RLS two-user test" for this.
- **Migration numbers:** 0010 arrives with #7. Numbers 0011+ below are indicative, assigned in merge order. Forward-only; 0001–0010 are never edited (R1).
- **Blocked-by:** a pending decision from Farjad Iranmehr (FI) or the CPO. No story assumes the answer; the story states what stays open.
- **Agronomic rules:** "none" or `PLACEHOLDER` + `TODO(agronomist)`. `cp-agronomist` is an AI agent (D4): its sign-off is `ai_reviewed`, never `agronomist_approved`, never the review gate, never counted toward the 90 % agreement gate.

## Definition of Ready (backend plan §16, adapted to D1)

- Story and Given/When/Then acceptance criteria written (allowed and denied cases where permissions apply).
- Data-model impact known; migration sketched (0011+).
- Permissions defined: roles per §3.2 + reconciliation, RLS policy and its two-user test (RLS is Postgres RLS on Railway, ADR 0008, not a Supabase JWT).
- Agronomic rules confirmed by a human agronomist or marked `PLACEHOLDER` + `TODO(agronomist)`.
- Blocking decisions listed; no story starts on an assumed answer.

## Definition of Done (§16, adapted to D1)

- Code + tests merged by `release-manager` only; CI green (ruff, mypy, tests); golden report unchanged or explained.
- RLS tests for any new table or policy; audit events for any admin or sensitive action.
- Reviews attached where required: `GRD` on any PR that computes or displays a number, `SR` on auth/RLS/storage, `LR` on wording.
- API/route docs updated (OpenAPI once `/api/v1` exists, S9); ADR written for any decision (ADR 0008 first).
- "Deployed to staging and demoed" applies once AR-03 and staging exist (S3-PLT-01); before that, Done = verified on local PostGIS (`make db-up`).
- No new GPL/EUPL or unknown licence in production; no secrets in git.
- D-7 (CPO 2026-11-16): `cp-agronomist` never receives real pilot farmers' personal or identifiable farm data — published, synthetic or de-identified cases only.
- Acceptance criteria verified by `cp-qa`; PR description and sprint notes updated; standard report to `documentation`.

## Sprint goals and capacity

| Sprint | Dates | Goal | Stories | Points | Agent-days (S=0.25, M=0.5, L=1) |
|---|---|---|---|---|---|
| S1 carry-over | by Nov 27 (S1) | #7 merged with CISO fixes; layout decisions recorded; five sample plans proven | 4 | 6 | 1.5 |
| S2 | Nov 30–Dec 11 | **Agronomist-ready foundation:** RLS v0 on Railway-style Postgres (ADR 0008), the review queue with engine-vs-edit diff, human-only approval on real farms, the Ontario winter wheat pack (all constants PLACEHOLDER), per-line recommendations and a first proof PDF | 53 | 99 | 27 |
| S3 | Dec 14–Jan 1 (50 %, code merged by **Dec 23**, no deploys Dec 25–Jan 3) | **No-test and P/K paths on staging:** SoilGrids cache, N-only no-test plan, P/K with lab test, private proof storage, staging environment with demo | 16 | 30 | 8 |

Capacity assumption (stated, not measured): about five parallel agent lanes with disjoint file sets (DB, engine, app, PDF, platform/QA); FI reviews and decisions are the real limit (OQ-03 open, RK-X12). S2 is a two-week window of about 10 working days, i.e. roughly 50 lane-days; S2 holds 27 agent-days, so it is **loaded to about 54 % of the raw lane capacity before review time and rework**. S3 holds 8 agent-days against 50 % capacity (about 25 lane-days), i.e. 32 %. S3 is about 30 % of S2 by points, below the half asked for; the reason is that S3 depends on S2 outputs and on FI decisions, and the holiday freeze leaves no slack for more. Overflow rule: if S2 runs over, move in this order and never cut RLS, PDF or guard review (RK-X12): S2-ENG-05 (product matching) → S2-APP-12, S2-APP-11, S2-APP-09 → S2-DB-16. If S2 finishes early, pull S3-ENG-01 forward.

### Sprint order (value and dependency)

**S1 carry-over:** S1C-01 → S1C-02, S1C-03 → S1C-04.

**S2, wave 1 (days 1–3):** S2-DB-01, S2-DB-02, S2-PLT-01, S2-PLT-02, S2-PLT-03, S2-WEB-01, S2-WEB-02, S2-ENG-01, S2-ENG-03, S2-PDF-01, S2-QA-01 (plan). Decisions due Nov 27: RK-X4, RK-X5, RK-X7, RK-X11. AR-03 due Dec 4.

**S2, wave 2 (days 4–7):** S2-DB-03, S2-DB-04, S2-DB-05, S2-DB-14, S2-DB-08, S2-DB-09, S2-DB-10, S2-DB-06, S2-DB-07, S2-DB-11, S2-DB-12, S2-DB-13, S2-ENG-02, S2-ENG-04, S2-PLT-04, S2-QA-03, S2-DB-17, S2-DB-18, S2-DB-19, S2-DB-15, S2-DB-16.

**S2, wave 3 (days 6–10):** design doc ready → S2-APP-01, S2-APP-02, S2-APP-03, S2-APP-04, S2-APP-05, S2-APP-06, S2-APP-07, S2-APP-08, S2-APP-10, S2-ENG-05, S2-ENG-06, S2-PDF-02, S2-PDF-03, S2-PDF-04, S2-PDF-05, S2-APP-09, S2-APP-11, S2-APP-12, S2-WEB-03, STD-01, S2-QA-02.

**S3 (merge by Dec 23):** S3-DB-01 → S3-ENG-01 → S3-ENG-02 → S3-ENG-03 → S3-ENG-04, S3-DB-02, S3-APP-01, S3-APP-02, S3-PDF-01, S3-PLT-01 → S3-APP-03, S3-PLT-02, S3-QA-02, S3-QA-01, S3-WEB-01, S3-WEB-02. Freeze Dec 25–Jan 3 (RK-X9).

### Decisions that block stories (do not assume)

| Decision | Owner | Needed by | Blocks |
|---|---|---|---|
| RK-X4 status as derived view | CPO | Nov 27 | S2-DB-08 |
| RK-X5 season vs crop_plan | CPO | Nov 27 | S2-DB-17 |
| RK-X7 access_grant revoke model | CPO | Nov 27 | S2-DB-15 |
| RK-X11 role mapping; superadmin cannot approve unless human agronomist | CPO | Nov 27 | S2-DB-04, S2-DB-05, S2-DB-10 |
| AR-03 Railway PostGIS service (and bucket/worker/staging cost go) | FI | Dec 4 | S2-PLT-04, S2-WEB-03, S3-PDF-01, S3-PLT-01, S3-PLT-02, S3-QA-02, S3-APP-03 (LIVE part) |
| OQ-04 named human agronomist | FI | Dec 11 (latest Jan 15) | S2-QA-02 (human sign-off only), S2-DB-10 naming; real-farm plans stay `in_review` until named |
| OQ-06 data residency | FI | Dec 23 | real farm data (S5); not a blocker for S2/S3 code |
| OQ-07 legal disclaimer/terms owner | FI | Dec 23 | S2-PDF-05 (placeholder text only), S3-WEB-01 |
| PM-PX-ag confirmation (generate ✓ until S9, share link ✗) | CPO | Dec 4 | S2-PDF-03 |
| NB-WEB-06 funnel events proposal | CPO | Dec 14 | S3-WEB-02 |

## Stories

## S1 carry-over (1A, 1G)

### S1C-01 Merge #7 after CISO fixes (A1, S1–S8)

- **Sprint:** S1 carry-over → S2 · **Workstream:** 1A · **Owner:** cp-concierge-app + ciso + release-manager · **Size:** M (2 pt)
- **Story:** As a owner of CloverProof, I want the Step 5 concierge app merged with every CISO MUST/SHOULD-FIX closed so that the agronomist can run farm to review on a reviewed code base.
- **Acceptance criteria:**
  - Given #7 with fixes for A1 and S1–S8 in `docs/security/S2-auth-review-step5.md`, when ciso re-reviews, then the verdict is "accept" and release-manager merges #7.
  - Given a logged-in user with role `agronomist`, when they GET `/admin/users`, then the response is 403 (denied; test `test_admin_users.py`).
  - Given a user with role `owner`, when they GET `/admin/users`, then the list renders and a role change is stored (allowed).
  - Given `make test` and `make db-test`, when CI runs on the merge commit, then both are green.
- **Data-model impact:** none
- **Permission / RLS impact:** Existing roles only (`owner` ≈ org_admin, `agronomist`). `/admin/users` owner-only. No RLS change here.
- **Agronomic rules:** none
- **Matrix IDs:** S01-G, S01-6, REC-R8, AR-04, AR-26, PM-OM-oa, PM-OM-ag
- **Tests:** API, SR, E2E
- **Dependencies / Blocked-by:** CISO findings doc must be on a remote branch (RK-X10)
- **Out of scope:** restructuring views into `app/views/` (S9).

### S1C-02 Record layout decisions: paths, views, services

- **Sprint:** S1 carry-over → S2 · **Workstream:** 1A · **Owner:** cp-platform + cto · **Size:** S (1 pt)
- **Story:** As a maintainer, I want the equivalent paths and deferred restructures written down as decisions so that agents stop re-litigating `app/` and `db/migrations/` layout.
- **Acceptance criteria:**
  - Given `app/cloverproof_app/main.py`, `db/migrations/`, `make db-up` + `db/seeds/dev.sql`, when the decision log is updated, then AR-20, AR-30 and EV-01 are recorded as accepted equivalents (D1).
  - Given views in `web.py`, `plan_web.py`, `account.py`, when the decision is written, then AR-23/AR-24 restructure is deferred to the start of `/api/v1` (S9) and `recommendation_service.py` is created in S2-APP-06.
  - Given AR-01, when written, then it states: one FastAPI service, HTML views now, `/api/v1` + `/admin/v1` from S9.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** AR-01, AR-20, AR-23, AR-24, AR-30, EV-01
- **Tests:** DEC
- **Dependencies / Blocked-by:** —
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S1C-03 Review-gate and goal tracker stay true after merge

- **Sprint:** S1 carry-over → S2 · **Workstream:** 1A · **Owner:** cp-database + cp-concierge-app · **Size:** S (1 pt)
- **Story:** As a agronomist, I want the existing DB approve gate and engine-vs-final storage proven on merged `main` so that no number can reach a farmer without approval and the calibration delta is never lost.
- **Acceptance criteria:**
  - Given mig 0007 and `test_review_gate.py`, when `make db-test` runs on `main`, then approving as a non-agronomist membership fails (denied).
  - Given a plan reviewed with an edit, when the diff view is read, then engine output and final numbers + reason are both present (GL-01).
  - Given no farmer-facing read path exists yet, when listed, then the gap (S9 filter, RLS DM-R2 in S2-DB-08, human-only approval in S2-DB-10) is recorded as open, not closed.
- **Data-model impact:** none
- **Permission / RLS impact:** Unchanged; real closure of HC-01 is S2-DB-08 / S2-DB-10.
- **Agronomic rules:** none
- **Matrix IDs:** GL-01, GL-11, HC-01
- **Tests:** DBT, API, E2E
- **Dependencies / Blocked-by:** S1C-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S1C-04 S1 DoD: five sample plans end to end, delta and minutes recorded

- **Sprint:** S1 carry-over → S2 · **Workstream:** 1G · **Owner:** cp-qa · **Size:** M (2 pt)
- **Story:** As a QA owner, I want five sample plans run locally with delta and minutes recorded so that S1 is closed with evidence, not a feeling.
- **Acceptance criteria:**
  - Given five sample farms, when each is run farmer → field → season → soil (or none) → engine → review, then each has a stored engine-vs-final delta and a `minutes_spent` value.
  - Given the PDF is not built in S1, when the report is written, then the PDF item is listed as open and moved to S2-PDF-02.
  - Given the S1 go/no-go note, when filed, then it names every S1 item carried into S2.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** S01-DoD
- **Tests:** E2E
- **Dependencies / Blocked-by:** S1C-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

## S2

### S2-DB-01 Schema gap analysis with proposals for RK-X4/X5/X7/X11

- **Sprint:** S2 (S1 → S2, decisions due Nov 27) · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a CPO, I want one line per DM row comparing plan §6 with migrations 0001–0010 and a proposal for each open conflict so that decisions RK-X4, RK-X5, RK-X7, RK-X11 can be made by Nov 27 and migrations are written against a settled shape.
- **Acceptance criteria:**
  - Given plan §6 and mig 0001–0010, when `docs/engineering/schema-gap-analysis.md` is written, then every DM-01..DM-30 row has status, migration number sketch and RLS note.
  - Given RK-X4/X5/X7/X11, when the doc is read, then each has one recommended option plus the cost of the alternative, and none is assumed decided.
  - Given R1/R2, when read, then no step edits 0001–0010 and `recommendation_line` replaces the P/K-columns proposal.
- **Data-model impact:** Doc only; sketches migrations 0011+. Numbers indicative; assigned in merge order; 0010 lands with #7.
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** REC-R1, S01-3
- **Tests:** DBT (doc is DR)
- **Dependencies / Blocked-by:** —  Decisions out: RK-X4, RK-X5, RK-X7, RK-X11 (CPO)
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-02 ADR 0008: Postgres RLS on Railway

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database + system-architect; ciso review · **Size:** M (2 pt)
- **Story:** As a security reviewer, I want an accepted ADR for RLS driven by `SET LOCAL app.user_id/app.org_id/app.platform_role` with a non-bypass `cp_app` role so that RLS is defence in depth without a Supabase JWT.
- **Acceptance criteria:**
  - Given D1, when the ADR is written, then it defines the three settings, `cp_app` (NOBYPASSRLS, not table owner), `SET LOCAL` per transaction, and states psycopg + hand SQL stays (AR-10, RK-X15).
  - Given pooled connections, when ciso reviews, then the ADR shows settings cannot leak between requests (transaction-local only, reset on checkout) and names bypass paths (migrations role, superadmin, AI-agronomist account).
  - Given the ADR, when accepted, then "Supabase" appears nowhere except as superseded history and `docs/adr/` index is updated.
- **Data-model impact:** none
- **Permission / RLS impact:** Defines the policy model for all later RLS stories; ciso reviews bypass paths and the AI-agronomist account.
- **Agronomic rules:** none
- **Matrix IDs:** REC-D1, AR-10, SC-02
- **Tests:** DEC, SR
- **Dependencies / Blocked-by:** S2-DB-01 (role mapping proposal)
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-03 RLS foundation: `cp_app` role, `SET LOCAL` wrapper, two-user test fixture

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database + cp-concierge-app · **Size:** L (3 pt)
- **Story:** As a developer, I want every app transaction to run as `cp_app` with the session identity set locally and a reusable two-user test fixture so that each later policy can be proven in one test.
- **Acceptance criteria:**
  - Given a request with a server-side session, when the app opens a transaction, then `app.user_id`, `app.org_id`, `app.platform_role` are set with `SET LOCAL` and are empty after commit.
  - Given a connection as `cp_app`, when a query touches a table with RLS enabled and no settings are set, then it returns zero rows (deny by default).
  - Given the `tests/rls` fixture, when a test requests user A (org 1) and user B (org 2), then both run against the same DB with distinct settings.
- **Data-model impact:** Migration 0011: `cp_app` role, grants, helper functions `app.current_user_id()/org_id()/platform_role()`. No table policies yet.
- **Permission / RLS impact:** Deny by default for `cp_app`; migration/owner role is separate and never used by request handlers.
- **Agronomic rules:** none
- **Matrix IDs:** S01-4, AR-11
- **Tests:** DBT, RLS, SR
- **Dependencies / Blocked-by:** S2-DB-02
- **Out of scope:** table policies (S2-DB-06..08), MFA (S5).

### S2-DB-04 Identity: locale, unit system, platform role, human flag

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a platform admin, I want user profile fields and a platform role on `app_user` so that staff and superadmin are platform roles, not org roles.
- **Acceptance criteria:**
  - Given `app_user`, when migration 0012 applies, then `locale`, `unit_system` (metric/imperial) and `platform_role` (none/staff/superadmin, default none) exist; `app_user` name is kept (D1).
  - Given an existing user, when the migration runs, then values default safely and no row is lost.
  - Given user B with `platform_role=none`, when B reads another user's profile, then RLS returns nothing (denied); a `staff` user reads it (allowed, audited in S2-DB-13).
- **Data-model impact:** Migration 0012 on `app_user` (+ `is_human` boolean used by S2-DB-10).
- **Permission / RLS impact:** Roles: staff (read-only audited), superadmin (everything except approve unless human agronomist, per RK-X11 proposal). Policies on `app_user`; RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** DM-01, RO-06, RO-07
- **Tests:** DBT, RLS
- **Dependencies / Blocked-by:** S2-DB-03; Blocked-by RK-X11 (org `staff` → platform `staff` mapping)
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-05 Org kind/country and membership roles (org_admin, advisor, agronomist) with status

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a org admin, I want organisations with kind and country and memberships with the plan roles and a status so that roles match §3.1 and the permission matrix.
- **Acceptance criteria:**
  - Given the role mapping decided in RK-X11 (owner → org_admin; staff → platform), when migration 0013 applies, then `membership_role` has org_admin, advisor, agronomist (+ farmer kept) and `membership.status` exists; no 0001–0010 file is edited.
  - Given `organisation`, when applied, then `kind` (advisory/coop/dealer/lab/internal) and `country_code` exist.
  - Given an `advisor` membership, when they invite or remove a member, then RLS denies it; an `org_admin` can (allowed).
- **Data-model impact:** Migration 0013: enum extension (forward-only), `organisation.kind/country_code`, `membership.status`.
- **Permission / RLS impact:** org_admin CRUD members; advisor none; agronomist none; staff R. RLS two-user test (allowed user + denied user, per the convention in "How to read") on `membership`.
- **Agronomic rules:** none
- **Matrix IDs:** DM-02, DM-03, RO-02, RO-03
- **Tests:** DBT, RLS
- **Dependencies / Blocked-by:** S2-DB-03; Blocked-by RK-X11
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-06 RLS v0: farm structure (farmer, farm, field, season, geometry)

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a org member, I want rows visible only to the owning org (and platform staff/superadmin) at the DB level so that a bug in the data-access layer cannot leak another org's farms.
- **Acceptance criteria:**
  - Given user A (org 1) and user B (org 2), when B selects org 1's farm, then zero rows (denied).
  - Given an `org_admin` of org 1, when they read org 1 farms and fields, then rows return, read-only (§3.2 R org scope).
  - Given an `agronomist` of org 1, when they read farms, then rows return (assigned scoping deferred, recorded as decision); superadmin can CRUD, staff reads and the read is audited.
  - Given grants arrive later (S9), when this story is done, then the policy has a clearly marked hook for `access_grant` and does not use it yet.
- **Data-model impact:** Migration 0014: `ENABLE`/`FORCE ROW LEVEL SECURITY` + policies on those tables.
- **Permission / RLS impact:** Matrix row "Own farms/fields": org_admin R, agronomist R (assigned = org-wide for now, DEC), staff R audited, superadmin CRUD. RLS two-user test (allowed user + denied user, per the convention in "How to read") per table.
- **Agronomic rules:** none
- **Matrix IDs:** DM-R1, PM-FF-oa, PM-FF-ag, PM-FF-sa
- **Tests:** RLS, DBT
- **Dependencies / Blocked-by:** S2-DB-03, S2-DB-05
- **Out of scope:** `access_grant`-based visibility (S9), per-assigned-farm agronomist scoping.

### S2-DB-07 RLS v0: soil tests and approved-plan visibility

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a org member, I want soil tests and approved plans readable by the allowed roles only so that matrix rows "Soil tests" and "See approved plan" hold in the DB.
- **Acceptance criteria:**
  - Given an `org_admin` of org 1, when they read org 1 soil tests, then rows return; when they insert, then denied.
  - Given an `agronomist`, when they insert a soil test during concierge entry, then allowed (decision PM-ST-ag: write kept for concierge, recorded in DEC).
  - Given user B from org 2, when they read org 1 approved recommendations or soil tests, then zero rows (denied).
  - Given a superadmin, when they CRUD soil tests, then allowed; a staff user can only read.
- **Data-model impact:** Policies on `soil_test`, `soil_test_value`, approved-plan read path (migration 0015).
- **Permission / RLS impact:** Soil tests: org_admin R, agronomist R + concierge write (DEC), staff R, superadmin CRUD. Approved plan: org_admin/agronomist/staff/superadmin R.
- **Agronomic rules:** none
- **Matrix IDs:** PM-ST-oa, PM-ST-ag, PM-ST-sa, PM-VP-oa, PM-VP-sa
- **Tests:** RLS, DEC
- **Dependencies / Blocked-by:** S2-DB-06, S2-DB-08
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-08 Recommendation state derived from reviews; unapproved rows invisible to non-agronomists

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** L (3 pt)
- **Story:** As a reviewing agronomist, I want recommendation status derived from `review` rows and drafts hidden from everyone except agronomists and platform roles so that an immutable row never needs UPDATE and drafts cannot leak to farmers, advisors or org admins.
- **Acceptance criteria:**
  - Given a recommendation with no review, when read via view `recommendation_state`, then state = `in_review`; after an approve review, then `approved`; after an edit review, the parent is `superseded` and the child exists.
  - Given a recommendation not approved, when a `farmer`, `advisor` or `org_admin` selects it, then zero rows (denied).
  - Given the same row, when an org `agronomist`, `staff` or `superadmin` selects it, then it returns (allowed).
  - Given UPDATE or DELETE on `recommendation` as `cp_app`, then both fail (immutable).
- **Data-model impact:** Migration 0016: `version_no`, view `recommendation_state`, policy on `recommendation`.
- **Permission / RLS impact:** Matrix "See engine draft": farmer/advisor/org_admin denied; agronomist/staff/superadmin allowed. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** DM-13, DM-R2, PM-DR-fa, PM-DR-ad, PM-DR-oa, PM-DR-sa, GL-11, HC-01
- **Tests:** DBT, RLS (denied cases)
- **Dependencies / Blocked-by:** S2-DB-03; Blocked-by RK-X4 (status as derived view)
- **Out of scope:** farmer-facing read path (S9).

### S2-DB-09 `recommendation_line` table (per nutrient, explicit form, splits, timing)

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a agronomist, I want one immutable row per nutrient/split with form, rate, product, timing window and explanation so that P/K and splits are stored per line, not as columns on `recommendation` (R2).
- **Acceptance criteria:**
  - Given migration 0017, when applied, then `recommendation_line` has recommendation_id, nutrient, nutrient_form (elemental/oxide), rate_kg_ha, product_id (nullable), split_no, timing window start/end, timing_basis, explanation, confidence (high/medium/low).
  - Given a P or K line, when inserted without form, then the DB rejects it (hard rule 7).
  - Given UPDATE/DELETE on a line, then fails; user B from another org cannot read lines (denied).
  - Given the migration, then no `p_rate_kg_ha`/`k_rate_kg_ha` is added to `recommendation`.
- **Data-model impact:** Migration 0017 `recommendation_line` (+ backfill of `result` jsonb splits for existing rows is NOT done; old rows keep jsonb, recorded).
- **Permission / RLS impact:** Inherits `recommendation` visibility (drafts hidden to non-agronomists). RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** No constants; `timing_basis` allows gdd/calendar/manual, GDD logic is S4.
- **Matrix IDs:** REC-R2, DM-14
- **Tests:** DBT, RLS
- **Dependencies / Blocked-by:** S2-DB-08
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-10 Human-only approval on real farms; `ai_reviewed` as a separate review kind

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database + cp-concierge-app · **Size:** L (3 pt)
- **Story:** As a founder, I want the DB to refuse approval of a real farm's plan unless the reviewer is a human `agronomist`, with AI sign-off stored as `ai_reviewed` so that D4 holds even if an app bug or the AI account tries to approve.
- **Acceptance criteria:**
  - Given `farm.data_class` (real/synthetic; default real) and `review.review_kind` (agronomist_approved/ai_reviewed), when migration 0018 applies, then both exist.
  - Given the AI agent account (`app_user.is_human=false`), when it inserts an approve review on a real farm's recommendation, then the DB rejects it (denied, test).
  - Given the AI account, when it inserts an `ai_reviewed` review, then it is stored, does not change derived state to `approved`, and does not count as the review gate.
  - Given a human user with `agronomist` membership, when they approve a real farm's recommendation, then it is allowed (state `approved`); a superadmin without a human-agronomist membership is denied.
  - Given no human agronomist is named yet (OQ-04), real-farm plans stay `in_review` (no AI review is possible on them, D-7).
  - Given D-7 (CPO 2026-11-16), when the AI account (`is_human=false`) selects farmer/farm/field/soil/recommendation rows of a `real` farm, then RLS returns none (denied, test); `synthetic` rows are visible (allowed, test). AI never approves or rejects any plan (review-queue spec §1a P1–P2).
- **Data-model impact:** Migration 0018: `farm.data_class`, `review.review_kind`, trigger on approve, uses `app_user.is_human` (S2-DB-04). Gate counts in calibration views must filter `review_kind` (spec to head-of-data).
- **Permission / RLS impact:** Approve/edit/reject: agronomist (human only for real farms), superadmin only if human agronomist, all others denied. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** REC-D4, PM-AP-ag, PM-AP-sa
- **Tests:** DBT, API, RLS (denied)
- **Dependencies / Blocked-by:** S2-DB-04, S2-DB-08; Blocked-by RK-X11 (superadmin cannot approve unless human agronomist), OQ-04 (name of the human; does not block the schema)
- **Out of scope:** naming the human agronomist (OQ-04); MFA (S5).

### S2-DB-11 Persist review start/finish times

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** S (1 pt)
- **Story:** As a CPO, I want `started_at` and `finished_at` stored on every review so that minutes per plan is auditable, not just a number.
- **Acceptance criteria:**
  - Given migration 0019, when applied, then `review.started_at` and `finished_at` exist and `finished_at >= started_at` is checked.
  - Given a review without start time (legacy rows), when read, then nulls are allowed on old rows only.
  - Given UPDATE on `review`, then fails (immutable).
- **Data-model impact:** Migration 0019 columns on `review`.
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** DM-15
- **Tests:** DBT
- **Dependencies / Blocked-by:** S2-DB-10
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-12 `proof_document` kind and template version

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** S (1 pt)
- **Story:** As a auditor, I want `kind` (plan/plan_with_log) and `template_version` on every proof so that a proof can be reproduced from its template.
- **Acceptance criteria:**
  - Given migration 0020, when applied, then `kind` and `template_version` exist; the ADR 0005 key check and approved-only trigger (mig 0008) still pass.
  - Given a proof for an unapproved recommendation, when inserted, then it fails (existing trigger).
  - Given user B from another org, when they read the proof row, then zero rows (denied).
- **Data-model impact:** Migration 0020 columns on `proof_document`.
- **Permission / RLS impact:** Read follows approved-plan visibility; export/generate by agronomist (concierge) and superadmin only. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** DM-19
- **Tests:** DBT, RLS
- **Dependencies / Blocked-by:** S2-DB-08
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-13 `audit_event` append-only with triggers and RLS

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** L (3 pt)
- **Story:** As a auditor, I want an append-only audit table fed by triggers and app calls for admin, grant, approval, export and deletion actions so that every sensitive action leaves a trace from the first admin action.
- **Acceptance criteria:**
  - Given migration 0021, when applied, then `audit_event` has actor_id, actor_role, action, entity_type, entity_id, reason, ip_hash, at, diff.
  - Given an approval, a role change, a grant change, then an audit row exists for each.
  - Given `cp_app`, when it INSERTs directly, then denied except via the trigger/service function; UPDATE/DELETE always denied.
  - Given a `farmer`/`advisor`, when they read audit, then only own events; org_admin org events; staff/superadmin all (RLS test per role).
- **Data-model impact:** Migration 0021 `audit_event` + triggers on review, membership, access_grant, proof_document.
- **Permission / RLS impact:** Audit log row of §3.2: own events / org events / R. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** DM-27, DM-R4, SC-06, DD-03
- **Tests:** DBT, RLS
- **Dependencies / Blocked-by:** S2-DB-03, S2-DB-04
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-14 Column hygiene: `created_by`, `updated_at`, `deleted_at`, farm region, field external ref

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a maintainer, I want the missing standard columns added with safe defaults so that every mutable table is attributable and soft-deletable where the plan says so.
- **Acceptance criteria:**
  - Given the tables missing `created_by` (organisation, farmer, farm, field, season, membership, soil_test_value), when migration 0022 applies, then the column exists, nullable for legacy rows, required on new inserts.
  - Given mutable tables, when applied, then `updated_at` exists with a trigger; immutable tables are excluded.
  - Given `field`, when applied, then `deleted_at` and `external_ref` exist and default queries exclude deleted rows; `farm.region_code` exists beside the free-text region.
- **Data-model impact:** Migration 0022 (forward-only, additive).
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** DM-C3, DM-C4, DM-C5, DM-06, DM-07
- **Tests:** DBT
- **Dependencies / Blocked-by:** S2-DB-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-15 `access_grant` model (insert-only history) with RLS

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a farmer, I want a grant of view/edit access to an advisor or org with optional expiry and a revoke that keeps history so that a farmer can revoke consent without losing the audit trail (UI is S9).
- **Acceptance criteria:**
  - Given migration 0023, when applied, then `access_grant` has farmer_id, grantee_org_id or grantee_user_id, scope view/edit, granted_by, expires_at and revoke represented per the RK-X7 decision.
  - Given a revoke, when read, then the original grant row is unchanged and history is preserved.
  - Given user B with no grant, when they read another farmer's grants, then zero rows (denied); the grantor and the grantee can read (allowed).
  - Given the model, when S2 ends, then no policy depends on grants yet except the documented hook in S2-DB-06.
- **Data-model impact:** Migration 0023 `access_grant`.
- **Permission / RLS impact:** farmer grants/revokes; advisor/org read own grants; staff R audited; superadmin CRUD. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** DM-05, S02-2, U3a, PM-GR
- **Tests:** DBT, RLS
- **Dependencies / Blocked-by:** S2-DB-06; Blocked-by RK-X7 (insert-only revoke row vs one-time `revoked_at`)
- **Out of scope:** grant UI and grant-based policies (S9).

### S2-DB-16 Farmer ownership model and contact fields

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a farmer, I want a farmer record that can be owned by the farmer's own login and carries country and contact so that the farmer owns farm data and can later revoke access (HC-08).
- **Acceptance criteria:**
  - Given `farmer`, when migration 0024 applies, then `owner_user_id` (nullable), `country_code`, contact fields exist; org-created farmers still work with no owner.
  - Given a farmer with `owner_user_id`, when the org reads them, then access still works via org scope until grants replace it (S9), recorded as decision.
  - Given user B (other org, not owner), when they read the farmer, then zero rows (denied).
- **Data-model impact:** Migration 0024 columns on `farmer`.
- **Permission / RLS impact:** Owner read/write own; org per S2-DB-06. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** DM-04, HC-08
- **Tests:** DBT, RLS
- **Dependencies / Blocked-by:** S2-DB-06, S2-DB-15
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-DB-17 Season / crop plan shape and geometry version fields

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a agronomist, I want crop, variety, sowing date, target yield and previous crop attached once per field and year, and geometry versions keyed by season year so that the CLAUDE.md chain season → crop_plan → recommendation and the §6 model agree.
- **Acceptance criteria:**
  - Given the RK-X5 decision (proposal: keep `crop_plan` as the §6 "season" equivalent), when migration 0025 applies, then one active crop plan per field+year is enforced and no data is lost.
  - Given `field_geometry_version`, when applied, then `season_year`, `valid_from` exist and `area_ha` is computed when a geometry is present, else manual (`area_source`).
  - Given a duplicate active plan for the same field and year, when inserted, then rejected.
- **Data-model impact:** Migration 0025: unique partial index, new columns, computed area.
- **Permission / RLS impact:** none
- **Agronomic rules:** Crop code list is configuration from the pack; no agronomic value invented.
- **Matrix IDs:** DM-09, U5, DM-08
- **Tests:** DBT
- **Dependencies / Blocked-by:** S2-DB-14; Blocked-by RK-X5
- **Out of scope:** geometry upload and map drawing (S18).

### S2-DB-18 Soil sample and measurement gaps (property, canonical value, entry method, confirmation)

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database + cp-engine · **Size:** M (2 pt)
- **Story:** As a agronomist, I want soil measurements that carry property, canonical value/unit, entry method and who confirmed them so that the engine reads only confirmed inputs and the extraction method and P/K form are never missing.
- **Acceptance criteria:**
  - Given `soil_test_value`, when migration 0026 applies, then `property` (incl. ph_water, ph_cacl2, som), `canonical_value`, `canonical_unit`, `entry_method` (manual/extracted/lab_api) and `confirmed_by/at` exist.
  - Given a P or K value without extraction method or form, when inserted, then rejected (rule 7, unchanged).
  - Given `ammonium_acetate` as a method, when proposed, then it is NOT added until an ADR and an agronomist answer exist (listed in `docs/agronomist-todo.md`).
  - Given a sampling with depth, date and lab, when read by user B of another org, then zero rows (denied).
- **Data-model impact:** Migration 0026 on `soil_test`/`soil_test_value`; `kit_qr`/`file_ids` deferred (S4/S25).
- **Permission / RLS impact:** none
- **Agronomic rules:** PLACEHOLDER + TODO(agronomist): which additional extraction methods are allowed for Ontario. No new method added without agronomist input.
- **Matrix IDs:** DM-10, DM-11
- **Tests:** DBT, RLS
- **Dependencies / Blocked-by:** S2-DB-07
- **Out of scope:** kit QR, file ids (S4/S25); new extraction methods.

### S2-DB-19 `fertilizer_product` table (catalog, no prices, no affiliate fields)

- **Sprint:** S2 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a agronomist, I want a per-country catalog of products with grade and form so that product matching and the plan view use facts, not vendor data.
- **Acceptance criteria:**
  - Given migration 0027, when applied, then `fertilizer_product` has country_code, name, n, p2o5, k2o, s, form (granular/liquid), density, active; there is no price, vendor or affiliate column (checked by a DB test, GL-09).
  - Given a `staff` user, when they insert a draft product, then allowed; an `org_admin` insert is denied; all org roles can read.
  - Given grades, then they are facts from the product label and are labelled with their source.
- **Data-model impact:** Migration 0027.
- **Permission / RLS impact:** Catalog: R for all roles; staff CRUD draft; superadmin CRUD + activate. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** Grades are label facts. Product choice rules are agronomy and live in S2-ENG-05 behind guard review.
- **Matrix IDs:** DM-24, A4, GL-09
- **Tests:** DBT, GRD, RLS
- **Dependencies / Blocked-by:** S2-DB-03
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-ENG-01 Ontario winter wheat pack `packs/ca-on/` v1 (structure, all constants PLACEHOLDER)

- **Sprint:** S2 · **Workstream:** 1C · **Owner:** cp-engine + cp-agronomist (ai_reviewed) + cp-agronomy-guard · **Size:** L (3 pt)
- **Story:** As a agronomist, I want the method structure for Ontario winter wheat in a versioned pack so that the engine runs a real method shape while every number waits for a human.
- **Acceptance criteria:**
  - Given published Ontario sources entered by hand, when `packs/ca-on/v1.yaml` is written, then each constant is `PLACEHOLDER` with a source reference and `TODO(agronomist)` (and listed in `docs/agronomist-todo.md`).
  - Given the pack, when loaded, then pack id, version, status and sha are stored per recommendation; no country code branches exist in engine code (rule 6).
  - Given the guard reviews the PR, when any number is computed from the pack, then the guard sign-off is attached (GRD).
  - Given the golden location `engine/tests/golden/`, then it is kept and recorded as the accepted equivalent of `packs/**/golden` (AR-31, DEC).
- **Data-model impact:** none (pack is config).
- **Permission / RLS impact:** none
- **Agronomic rules:** PLACEHOLDER + TODO(agronomist) for every constant, with source; nothing invented. Prairie wheat stays the backup (R4).
- **Matrix IDs:** S02-1, HC-07, AR-31
- **Tests:** GT, GRD, DEC
- **Dependencies / Blocked-by:** OQ-04 (human validation later, not blocking)
- **Out of scope:** validating any constant (needs the human agronomist); Prairie pack.

### S2-ENG-02 Golden cases carry `kind` and reviewer label

- **Sprint:** S2 · **Workstream:** 1C · **Owner:** cp-engine + cp-agronomist · **Size:** M (2 pt)
- **Story:** As a QA owner, I want each golden case labelled `agronomist_approved` or `external_reference` and by reviewer type so that AI-drafted cases can never be mistaken for human-approved ones.
- **Acceptance criteria:**
  - Given golden YAML, when a case lacks `kind`, then the loader fails the build.
  - Given a case authored by `cp-agronomist`, when loaded, then `kind=external_reference` and reviewer label `ai_reviewed`; `agronomist_approved` is rejected for it (denied).
  - Given the golden report in CI, when run, then it counts approved vs reference cases separately.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** Reference cases come from published documents entered by hand, never scraped; expected values stay PLACEHOLDER until validated.
- **Matrix IDs:** EN-05
- **Tests:** GT, UT
- **Dependencies / Blocked-by:** S2-ENG-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-ENG-03 Engine version = semver + git SHA stored on each recommendation

- **Sprint:** S2 · **Workstream:** 1C · **Owner:** cp-engine + cp-platform · **Size:** S (1 pt)
- **Story:** As a auditor, I want the git SHA stored with the engine version so that any plan can be tied to the exact code.
- **Acceptance criteria:**
  - Given a build, when the engine runs, then `engine_version` is semver and the git SHA is in the snapshot.
  - Given a build with no git info, when run, then it fails in CI (not silently empty).
- **Data-model impact:** One snapshot field (jsonb) or small column on `recommendation`; no history rewrite.
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** EN-06
- **Tests:** UT
- **Dependencies / Blocked-by:** —
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-ENG-04 Split plan per line from the pack

- **Sprint:** S2 · **Workstream:** 1C · **Owner:** cp-engine · **Size:** M (2 pt)
- **Story:** As a agronomist, I want splits generated from the pack and emitted as `recommendation_line` rows so that each split has its own rate, timing window and explanation.
- **Acceptance criteria:**
  - Given a pack with `splits`, when the engine runs, then lines sum to the total rate and each has window + explanation.
  - Given a pack with no splits for the crop, when run, then one line is produced.
  - Given a rounding case, when lines are summed, then the total matches within the pack rounding rule.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** Split shares are pack values: PLACEHOLDER + TODO(agronomist).
- **Matrix IDs:** S02-5
- **Tests:** UT, GT
- **Dependencies / Blocked-by:** S2-DB-09, S2-ENG-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-ENG-05 Product matching: need → product → quantity

- **Sprint:** S2 (overflow candidate to S3 per RK-X12) · **Workstream:** 1C · **Owner:** cp-engine + cp-database + cp-agronomy-guard · **Size:** L (3 pt)
- **Story:** As a agronomist, I want a nutrient need matched to catalog products and quantities so that the plan says what to buy, not only kg of nutrient.
- **Acceptance criteria:**
  - Given a need of N kg/ha and a catalog, when matched, then the product quantity = need / grade with unit conversion tests.
  - Given no product fits, when run, then the line stays nutrient-only and says so (no invented product).
  - Given choice rules (which product when several), when written, then they are pack config reviewed by the guard.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** Product choice rules: PLACEHOLDER + TODO(agronomist). Never cut guard review.
- **Matrix IDs:** S02-4, A4
- **Tests:** UT, GT, GRD
- **Dependencies / Blocked-by:** S2-DB-19, S2-DB-09
- **Out of scope:** prices, vendors, affiliate data (GL-09).

### S2-ENG-06 Enum labels stay equal between engine and DB

- **Sprint:** S2 · **Workstream:** 1C · **Owner:** cp-engine + cp-database · **Size:** S (1 pt)
- **Story:** As a developer, I want a test that DB enums and engine StrEnums match so that a rename cannot break soil data silently.
- **Acceptance criteria:**
  - Given the DB soil enums (method, form, property) and engine StrEnums, when the test runs, then labels are equal.
  - Given a mismatch, when CI runs, then it fails with the label names.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** DM-11
- **Tests:** UT, DBT
- **Dependencies / Blocked-by:** S2-DB-18
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-01 Review queue page (sort by due date, filter)

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app + product-designer · **Size:** M (2 pt)
- **Story:** As a agronomist, I want a queue of recommendations awaiting my review sorted by due date and filterable so that I always know what to review next.
- **Acceptance criteria:**
  - Given three `in_review` recommendations in my org, when I open `/review/queue`, then they list by due date ascending with farm, field, crop, age.
  - Given a filter on status or farmer, when applied, then only matches show.
  - Given a user of org 2, when they open org 1 items, then none appear (denied; RLS test).
  - Given a `farmer`/`advisor`/`org_admin`, when they request the page, then 403.
- **Data-model impact:** Due date/priority: column proposal in `recommendation` is NOT allowed (immutable); store on a mutable `review_task` or on `crop_plan` (decision in gap analysis).
- **Permission / RLS impact:** agronomist, staff, superadmin allowed; other roles denied. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** A1, HV-06, RV-01
- **Tests:** API, RLS, E2E
- **Dependencies / Blocked-by:** S2-DB-08; Screens: `docs/design/review-queue.md` (being written by product-designer + cp-design); stories do not start UI until it exists.
- **Out of scope:** farmer/advisor queues; assigned-farm filtering.

### S2-APP-02 Side-by-side diff: engine output vs agronomist edit

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app + product-designer · **Size:** M (2 pt)
- **Story:** As a agronomist, I want engine numbers and my numbers next to each other with the reason so that the calibration delta is visible while I work.
- **Acceptance criteria:**
  - Given a plan with an edit child, when I open review detail, then engine and edited lines show side by side with delta and reason per line.
  - Given no edit yet, when I open it, then the right side is empty and approving is possible as-is.
  - Given the diff is read from `recommendation_diff` (mig 0009) and `recommendation_line`, then no number is recomputed in the view.
- **Data-model impact:** none
- **Permission / RLS impact:** Same roles as the queue; denied for others.
- **Agronomic rules:** none
- **Matrix IDs:** HV-07, S02-3
- **Tests:** API, E2E, GRD
- **Dependencies / Blocked-by:** S2-APP-01, S2-DB-09; Screens: `docs/design/review-queue.md` (being written by product-designer + cp-design); stories do not start UI until it exists.
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-03 Persist review start; reject with required reason

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app · **Size:** M (2 pt)
- **Story:** As a agronomist, I want my review start time stored and rejection requiring a reason so that minutes per plan is real and rejections are explained.
- **Acceptance criteria:**
  - Given I open a plan and press start, when saved, then `review.started_at` is stored once; a second start does not overwrite.
  - Given I reject without reason, when submitted, then 422 and nothing stored (denied).
  - Given I reject with reason, when submitted, then a reject review row exists and derived state is `rejected`.
- **Data-model impact:** none
- **Permission / RLS impact:** agronomist only.
- **Agronomic rules:** none
- **Matrix IDs:** RV-02, RV-05
- **Tests:** API, DBT
- **Dependencies / Blocked-by:** S2-DB-11
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-04 Approve as-is with human-only guard on real farms

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app + cp-database · **Size:** M (2 pt)
- **Story:** As a human agronomist, I want to approve a plan unchanged so that the approval is mine and counted.
- **Acceptance criteria:**
  - Given a real farm's plan and I am a human `agronomist`, when I approve, then a review `agronomist_approved` is stored with minutes.
  - Given the AI agent account or a superadmin without human-agronomist membership, when approving a real farm's plan, then 403 and the DB also rejects (denied).
  - Given a synthetic farm, when the AI account records `ai_reviewed`, then it is stored and the plan is not `approved`.
  - Given no human agronomist exists, when listing real-farm plans, then they stay `in_review`.
- **Data-model impact:** none
- **Permission / RLS impact:** Approve: human agronomist only (D4); superadmin per RK-X11; others denied.
- **Agronomic rules:** none
- **Matrix IDs:** RV-03, PM-AP-ag
- **Tests:** API, DBT, E2E
- **Dependencies / Blocked-by:** S2-DB-10
- **Note:** Wording of buttons shows "Approve (human agronomist)" vs "AI review" per design doc.
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-05 Edit: changed lines + reason → new version + approve

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app · **Size:** L (3 pt)
- **Story:** As a human agronomist, I want to change lines, give a reason and approve in one action so that the edit and the approval are one reviewed step.
- **Acceptance criteria:**
  - Given I change a P line and give a reason, when I submit, then a child `recommendation` with changed lines and `parent_id` exists plus an approve review on the child.
  - Given no reason, when submitted, then rejected (rule 4).
  - Given the parent, then it is unchanged and derived as `superseded`.
  - Given the AI agent account, then edit-and-approve on a real farm is denied (as S2-APP-04).
- **Data-model impact:** none
- **Permission / RLS impact:** Same as approve.
- **Agronomic rules:** No constant touched; edited numbers are the agronomist's, stored with reason.
- **Matrix IDs:** RV-04, DM-17
- **Tests:** API, DBT
- **Dependencies / Blocked-by:** S2-DB-09, S2-DB-10, S2-APP-04
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-06 `recommendation_service`: inputs from confirmed DB rows and the active pack

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app · **Size:** L (3 pt)
- **Story:** As a agronomist, I want a plan generated from confirmed soil rows, crop and region with the active pack so that the stored snapshot is the data actually used.
- **Acceptance criteria:**
  - Given a field with a confirmed soil test, when I request a plan, then the service builds input from DB rows, loads the active pack, stores `recommendation` (+ lines) with full input snapshot, engine and pack versions.
  - Given unconfirmed soil values, when requested, then refused with the missing item named.
  - Given no soil test, then N-only per S3-ENG-02 once it ships; until then the existing no-test golden holds.
  - Given the HTTP layer, then the service has no HTTP imports (UT).
- **Data-model impact:** Uses 0017/0026; no new table.
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** EN-02, AR-24
- **Tests:** UT, DBT
- **Dependencies / Blocked-by:** S2-DB-09, S2-DB-18, S2-ENG-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-07 Per-line explanation and confidence never rewritten silently

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app + cp-agronomy-guard · **Size:** S (1 pt)
- **Story:** As a agronomist, I want engine explanation and confidence kept intact unless I change them with a reason so that farmers see what the engine said.
- **Acceptance criteria:**
  - Given an edit changes a rate, when saved, then the line's explanation shows "edited by agronomist: <reason>" and the engine text is preserved in the parent.
  - Given the edit recomputes split shares, then the marker from commit c5bfdbc remains and is tested.
  - Given confidence, then it is only changed by an explicit field with reason.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** EN-03
- **Tests:** GRD, UT
- **Dependencies / Blocked-by:** S2-APP-05
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-08 Double-submit guard on creating POSTs

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app · **Size:** S (1 pt)
- **Story:** As a user, I want a repeated click to not create a second recommendation or proof so that no duplicate immutable rows.
- **Acceptance criteria:**
  - Given a form token, when the same POST arrives twice, then one row is created and the second returns the first result.
  - Given a different token, then a new row is created.
  - Given proofs (S2-PDF-03), then the same guard applies.
- **Data-model impact:** Token store (table or unique key); decide in implementation, no new RLS-exposed data.
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** AC-07
- **Tests:** API
- **Dependencies / Blocked-by:** —
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-09 Product catalog v0 page

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app · **Size:** S (1 pt)
- **Story:** As a agronomist, I want to browse the catalog so that I can see which products the plan can use.
- **Acceptance criteria:**
  - Given the catalog, when I open Products, then name, grade, form, density show with no price column.
  - Given a `staff` user, when they add a draft product, then it shows as draft; an `org_admin` cannot (denied).
- **Data-model impact:** none
- **Permission / RLS impact:** All org roles read; staff/superadmin edit.
- **Agronomic rules:** none
- **Matrix IDs:** HV-11
- **Tests:** API
- **Dependencies / Blocked-by:** S2-DB-19
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-10 Request-recommendation permissions: staff denied, superadmin allowed

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app + cp-database · **Size:** S (1 pt)
- **Story:** As a owner, I want only roles in the matrix to request a recommendation so that support staff cannot create plans.
- **Acceptance criteria:**
  - Given a `staff` user, when POSTing a plan request, then 403 (denied; RLS test).
  - Given a `superadmin`, when they request, then allowed and audited.
  - Given an `agronomist`, then allowed (concierge).
- **Data-model impact:** none
- **Permission / RLS impact:** Request: agronomist, advisor, farmer, superadmin yes; org_admin, staff no. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** PM-RQ-sf, PM-RQ-sa
- **Tests:** API, RLS
- **Dependencies / Blocked-by:** S2-DB-04
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-11 Organisations: create, invite, roles, leave

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app · **Size:** M (2 pt)
- **Story:** As a org admin, I want to create an organisation, invite members, set roles and leave so that a second agronomist or advisor can join without a DB edit.
- **Acceptance criteria:**
  - Given I am `org_admin`, when I invite by email with role `advisor`, then a pending membership exists.
  - Given I am an `advisor`, when I invite, then 403 (denied).
  - Given I am the last `org_admin`, when I leave, then refused.
- **Data-model impact:** none
- **Permission / RLS impact:** org_admin CRUD members; others denied. Audited. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** U2
- **Tests:** API, RLS
- **Dependencies / Blocked-by:** S2-DB-05
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-APP-12 Farms and fields: edit and soft delete

- **Sprint:** S2 · **Workstream:** 1D · **Owner:** cp-concierge-app · **Size:** M (2 pt)
- **Story:** As a agronomist, I want to edit and soft delete farms and fields with manual area now so that typos can be fixed without losing history.
- **Acceptance criteria:**
  - Given a field, when I edit name or area, then saved and an audit row is written.
  - Given I soft delete a field with recommendations, then it is hidden but all its recommendations and proofs remain.
  - Given user B of another org, then edit/delete is denied.
- **Data-model impact:** Uses `deleted_at` (S2-DB-14); geometry upload not in scope.
- **Permission / RLS impact:** agronomist and superadmin; org_admin R. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** U4
- **Tests:** API, DBT
- **Dependencies / Blocked-by:** S2-DB-14, S2-DB-17
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-PDF-01 `ProofStore` interface: filesystem now, bucket later; ADR 0005 key

- **Sprint:** S2 · **Workstream:** 1E · **Owner:** cp-pdf + devops-engineer · **Size:** M (2 pt)
- **Story:** As a developer, I want a storage interface with a local implementation and the DB-enforced key so that the Railway Bucket can be swapped in without changing callers.
- **Acceptance criteria:**
  - Given `ProofStore`, when saving bytes, then the key is `proof/{org_id}/{recommendation_id}/{sha256}.pdf` and the DB check (mig 0008) accepts it.
  - Given the filesystem store, when run locally, then files land under a configured path from env (no hardcoding).
  - Given the sync render in S2, then the worker (PD-01 worker part) is recorded as S4.
- **Data-model impact:** none
- **Permission / RLS impact:** Bucket private; access only through the app.
- **Agronomic rules:** none
- **Matrix IDs:** PD-01, AR-05
- **Tests:** UT, DBT
- **Dependencies / Blocked-by:** —
- **Note:** Bucket implementation: S3-PDF-01, Blocked-by FI go for Railway Bucket (AR-03 family).
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-PDF-02 Proof PDF v0 content and template

- **Sprint:** S2 · **Workstream:** 1E · **Owner:** cp-pdf + cp-agronomy-guard · **Size:** L (3 pt)
- **Story:** As a agronomist, I want an English brand-colour PDF of an approved plan so that the farmer gets a proof with inputs, lines, explanations and versions.
- **Acceptance criteria:**
  - Given an approved recommendation, when rendered by WeasyPrint from Jinja2 templates in `app/pdf/templates/`, then it shows farm/field/season, inputs with sources + confidence, lines, explanations, reviewer + date, engine/pack/template versions, document ID.
  - Given an unapproved recommendation, when requested, then refused (denied).
  - Given the verify URL (UA-40, S11), when absent, then it is omitted.
  - Given brand colours #4C610B, #A7B58A, #FAF6EB, #273125, then used; strings are English (PD-06).
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** No constants; numbers come from approved lines only.
- **Matrix IDs:** S01-7, AR-13, AR-28, U11a, PD-02, PD-06
- **Tests:** UT, GRD, E2E
- **Dependencies / Blocked-by:** S2-DB-09, S2-DB-12, S2-PDF-01
- **Out of scope:** application-log section (S10), verify URL (S11), non-English strings (S27).

### S2-PDF-03 Generate route, SHA-256, metadata; regeneration creates a new row

- **Sprint:** S2 · **Workstream:** 1E · **Owner:** cp-pdf + cp-concierge-app · **Size:** M (2 pt)
- **Story:** As a agronomist, I want to generate a proof and see its hash and metadata so that each document is verifiable and never overwritten.
- **Acceptance criteria:**
  - Given an approved recommendation, when I POST `/seasons/{id}/proofs` (sync), then bytes are stored, SHA-256 of final bytes saved in `proof_document`.
  - Given the same recommendation generated again, then a new row is created; the old row is untouched.
  - Given GET `/proofs/{id}`, then metadata returns (signed URL arrives in S3-PDF-01).
  - Given a `farmer`, `advisor`, `org_admin` or `staff`, when generating, then 403 (denied); share link is not offered.
  - Given a double-submit, then S2-APP-08 guard applies.
- **Data-model impact:** none
- **Permission / RLS impact:** Generate: agronomist, superadmin; others denied. RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** PD-03, UA-36, UA-37, PM-PX-ag
- **Tests:** UT, API, SR
- **Dependencies / Blocked-by:** S2-PDF-02, S2-APP-08; Blocked-by CPO confirmation of PM-PX-ag (generate ✓ until S9, share link ✗)
- **Out of scope:** async worker (S4), share links (S11).

### S2-PDF-04 PDF preview page

- **Sprint:** S2 · **Workstream:** 1E · **Owner:** cp-pdf · **Size:** S (1 pt)
- **Story:** As a agronomist, I want to preview the PDF before handing it over so that I catch layout and wording problems.
- **Acceptance criteria:**
  - Given an approved plan, when I open the preview, then the PDF renders inline.
  - Given an unapproved plan, then the preview is denied.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** HV-08
- **Tests:** API
- **Dependencies / Blocked-by:** S2-PDF-02
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-PDF-05 PDF wording: no acceptance claims; AI vs human review

- **Sprint:** S2 · **Workstream:** 1E · **Owner:** cp-pdf + coo/legal + cp-agronomy-guard · **Size:** S (1 pt)
- **Story:** As a CPO, I want wording that is honest about who reviewed so that we make no claim a bank or inspector accepts the proof.
- **Acceptance criteria:**
  - Given a plan with only an `ai_reviewed` sign-off, when rendered, then the text does not say "reviewed by an agronomist" (denied wording, GRD).
  - Given a human approval, then the text says "prepared with CloverProof and reviewed by an agronomist".
  - Given any text, then no phrase claims third-party acceptance (HC-10); the legal disclaimer is a labelled placeholder.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** PD-05, HC-10
- **Tests:** GRD, LR
- **Dependencies / Blocked-by:** Blocked-by OQ-07 (who drafts legal disclaimer/terms)
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-PLT-01 CI: mypy, coverage gate, pip-audit, ciso security workflow

- **Sprint:** S2 · **Workstream:** 1F · **Owner:** cp-platform · **Size:** M (2 pt)
- **Story:** As a maintainer, I want type checks, coverage thresholds and dependency audit in CI so that regressions show up before review.
- **Acceptance criteria:**
  - Given CI, when a PR runs, then mypy (engine + services), coverage report (engine ≥ 90 %, services ≥ 75 %) and pip-audit run.
  - Given coverage below target, when CI runs, then it fails.
  - Given ciso's `security.yml` and Dependabot config, when merged by release-manager, then they run on `main`.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** EV-04, OB-06
- **Tests:** CI
- **Dependencies / Blocked-by:** SC-11 (ciso)
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-PLT-02 CI licence check (no GPL/EUPL)

- **Sprint:** S2 · **Workstream:** 1F · **Owner:** cp-platform + ciso · **Size:** S (1 pt)
- **Story:** As a maintainer, I want a licence scan failing the build on GPL/EUPL or unknown licences so that no licence surprise reaches production.
- **Acceptance criteria:**
  - Given a new dependency with GPL, when CI runs, then it fails unless an ADR exception exists.
  - Given an "unknown" licence, then fails (DD-06).
  - Given an LGPL dependency, when CI runs, then it passes only if it is on the named allow-list (`psycopg`; libvips via Next.js `sharp`, pending ADR + lawyer review — CPO 2026-11-16); any other LGPL dependency fails (denied).
  - Given a data source with an unknown licence (NASA POWER), then it is flagged "internal only — not farmer-facing until S8 lawyer review".
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** XD-07, DD-06
- **Tests:** CI
- **Dependencies / Blocked-by:** —
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-PLT-03 Secret rotation procedure

- **Sprint:** S2 · **Workstream:** 1F · **Owner:** cp-platform + ciso · **Size:** S (1 pt)
- **Story:** As a operator, I want a written rotation procedure in `docs/runbook-webapp.md` so that a team change does not leave live secrets.
- **Acceptance criteria:**
  - Given the runbook, when read, then it lists each secret, where it lives (env only), how to rotate and who approves.
  - Given `.env.example`, then it has empty values only (rule 10).
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** SC-03
- **Tests:** SR
- **Dependencies / Blocked-by:** —
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-PLT-04 Railway PostGIS service live; migrations applied

- **Sprint:** S2 · **Workstream:** 1F · **Owner:** devops-engineer + FI · **Size:** S (1 pt)
- **Story:** As a founder, I want the Railway PostGIS service created by me and migrations applied with a least-privilege role so that the DB switch and staging can start.
- **Acceptance criteria:**
  - Given FI created the service per `docs/runbook-db-switch.md` (agents are denied), when `make migrate` runs against it, then 0001–latest apply cleanly.
  - Given `cp_app`, when it connects, then it is non-bypass and cannot DDL.
  - Given no FI action by Dec 4, then S2-WEB-03, S3-PLT-01, S3-PDF-01 move to the risk list.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** AR-03, AR-08
- **Tests:** LIVE, DBT
- **Dependencies / Blocked-by:** Blocked-by AR-03 (FI action, due Dec 4)
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-QA-01 S2 test plan and `tests/` layout (api, service, rls, e2e)

- **Sprint:** S2 · **Workstream:** 1G · **Owner:** cp-qa + cp-database · **Size:** M (2 pt)
- **Story:** As a QA owner, I want a written S2 test plan and a repo layout for RLS and e2e suites so that each exit criterion has a named test.
- **Acceptance criteria:**
  - Given exit criteria in the distribution, when the plan is written, then each maps to a test code and an owner.
  - Given `tests/rls` and `tests/e2e`, when added, then CI runs them (AR-35).
  - Given the plan, then RLS policy tests use two users each (DM-R5).
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** AR-35, DM-R5
- **Tests:** RLS, E2E
- **Dependencies / Blocked-by:** S2-DB-03
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-QA-02 S2 DoD: five reference cases and one full PDF; human sign-off stays open

- **Sprint:** S2 · **Workstream:** 1G · **Owner:** cp-qa + FI · **Size:** M (2 pt)
- **Story:** As a founder, I want five published-reference cases run by cp-agronomist (`ai_reviewed`) and one full PDF so that S2 is demonstrated without pretending a human signed.
- **Acceptance criteria:**
  - Given five reference cases, when run end to end, then each has a stored result labelled `ai_reviewed`.
  - Given one case, when the PDF is generated, then it has the SHA-256 and the AI-review wording (S2-PDF-05).
  - Given the human sign-off item, when the report is filed, then it is open until OQ-04 is answered.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** S02-DoD
- **Tests:** E2E
- **Dependencies / Blocked-by:** S2-ENG-01, S2-PDF-02, S2-APP-06; Blocked-by OQ-04 (human sign-off only)
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-QA-03 RLS test coverage gate for every new table

- **Sprint:** S2 · **Workstream:** 1G · **Owner:** cp-qa + cp-database · **Size:** S (1 pt)
- **Story:** As a maintainer, I want CI to fail when a table with RLS has no allowed/denied test so that no policy ships untested.
- **Acceptance criteria:**
  - Given a migration adding a table with RLS, when no matching test exists, then CI fails.
  - Given all current tables, then each has two-user tests.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** DD-02
- **Tests:** RLS, CI
- **Dependencies / Blocked-by:** S2-DB-03
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-WEB-01 SEO, Lighthouse ≥ 90 mobile, a11y merged to `main`

- **Sprint:** S2 · **Workstream:** 1H · **Owner:** cp-website + release-manager · **Size:** M (2 pt)
- **Story:** As a visitor, I want a fast, accessible, indexable website so that farmers and partners can find and use it on a phone.
- **Acceptance criteria:**
  - Given `website-v1` commits (62310a5, bdeb4a6), when merged, then Lighthouse mobile ≥ 90 and a11y pass.
  - Given 375 px width, then no horizontal scroll.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** NB-WEB-02
- **Tests:** LIVE
- **Dependencies / Blocked-by:** release-manager; FI go before `main`
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-WEB-02 Stop logging raw pg errors with PII

- **Sprint:** S2 · **Workstream:** 1H · **Owner:** cp-website · **Size:** S (1 pt)
- **Story:** As a ciso, I want pilot-request errors logged without personal data so that no PII in logs.
- **Acceptance criteria:**
  - Given a DB error on submit, when logged, then only a code and request id are logged.
  - Given the response, then the user sees a generic message.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** NB-WEB-03
- **Tests:** SR
- **Dependencies / Blocked-by:** —
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S2-WEB-03 Move `pilot_request` to the shared PostGIS DB with a least-privilege role

- **Sprint:** S2 · **Workstream:** 1H · **Owner:** cp-website + cp-database · **Size:** M (2 pt)
- **Story:** As a maintainer, I want the website to write only `pilot_request` in the shared DB so that one DB, one migration path.
- **Acceptance criteria:**
  - Given the website role, when it writes `pilot_request`, then allowed; when it selects `farmer`, then denied.
  - Given the website's own migrate, then removed.
  - Given restore test plan, then drafted (RST in S5).
- **Data-model impact:** Role + grants on `pilot_request` only; existing table 0001.
- **Permission / RLS impact:** Website role: INSERT/SELECT own table only; denied elsewhere (RLS/grant test).
- **Agronomic rules:** none
- **Matrix IDs:** NB-WEB-04
- **Tests:** LIVE, RST (plan)
- **Dependencies / Blocked-by:** Blocked-by AR-03; ciso role spec
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### STD-01 Standing guards on every PR (S2 and S3)

- **Sprint:** S2 + S3 · **Workstream:** Standing · **Owner:** all agents + cp-agronomy-guard + release-manager · **Size:** S (1 pt)
- **Story:** As a CPO, I want non-goals and quality rules checked on every PR so that the product does not drift.
- **Acceptance criteria:**
  - Given any PR, when reviewed, then no hardware or sensor code (GL-06), no variable-rate/zone maps (GL-07), no carbon reporting (GL-08), no price or commission fields (GL-09).
  - Given any PR, then CI is green and the golden report is unchanged or explained (DD-01).
  - Given any text a farmer can see, then no acceptance claim (HC-10).
  - Given any soil data path, then method, form, depth, date are mandatory (RK-06).
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** GL-06, GL-07, GL-08, GL-09, DD-01, RK-06, HC-10
- **Tests:** GRD, CI, GT
- **Dependencies / Blocked-by:** —
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

## S3

### S3-DB-01 Soil estimate table with full source metadata

- **Sprint:** S3 · **Workstream:** 1B · **Owner:** cp-database · **Size:** M (2 pt)
- **Story:** As a agronomist, I want estimates stored apart from lab tests with source, version, resolution, depth and retrieval time so that a no-test plan always shows where its soil numbers came from and is capped at `low`.
- **Acceptance criteria:**
  - Given migration 00xx, when applied, then `soil_estimate` has field_id, season_year, property, value, unit, source (soilgrids/lucas/wosis), source_version, resolution_m, depth, uncertainty, retrieved_at.
  - Given an estimate row, when any metadata field is null, then the insert is rejected (XD-08).
  - Given `soil_test.source=estimate` rows from before, when migrated, then a documented path moves or keeps them without losing data (DEC).
  - Given user B of another org, when they read the estimate, then zero rows (denied).
- **Data-model impact:** Migration 00xx `soil_estimate` (number after S2 migrations).
- **Permission / RLS impact:** RLS two-user test (allowed user + denied user, per the convention in "How to read") on `soil_estimate`.
- **Agronomic rules:** Estimates always `low` confidence (rule enforced by engine, not a DB constant).
- **Matrix IDs:** DM-12, XD-08
- **Tests:** DBT, GT, RLS
- **Dependencies / Blocked-by:** S3-ENG-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-DB-02 Data-source versions and git SHA stored for reproducibility

- **Sprint:** S3 · **Workstream:** 1B · **Owner:** cp-database + cp-engine · **Size:** S (1 pt)
- **Story:** As a auditor, I want data-source versions and the engine git SHA in the recommendation input snapshot so that a plan can be reproduced exactly.
- **Acceptance criteria:**
  - Given a recommendation using a SoilGrids estimate, when stored, then the snapshot includes source name, version and retrieved_at and the engine git SHA (S2-ENG-03).
  - Given a recommendation without estimates, then the field is explicitly empty, not absent.
  - Given an old recommendation, then it is not rewritten (immutable).
- **Data-model impact:** Snapshot schema change + optional column; no change to old rows.
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** HC-03
- **Tests:** DBT, UT
- **Dependencies / Blocked-by:** S3-DB-01, S2-ENG-03
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-ENG-01 SoilGrids offline cache for the Ontario bbox, no runtime calls

- **Sprint:** S3 · **Workstream:** 1C · **Owner:** cp-engine + data-engineer · **Size:** L (3 pt)
- **Story:** As a engine, I want a local cache of SoilGrids values for the Ontario bounding box with licence and version so that no-test plans never depend on a live API.
- **Acceptance criteria:**
  - Given the cache files and `docs/data-sources.md`, when built, then each value has source, version, resolution and depth.
  - Given network disabled in a test, when an estimate is requested, then it succeeds from cache (XD-02, no-network test).
  - Given a point outside the bbox, when requested, then "no estimate" is returned, not a guess.
- **Data-model impact:** Cache location + metadata files; table in S3-DB-01.
- **Permission / RLS impact:** none
- **Agronomic rules:** none; data only.
- **Matrix IDs:** U7, XD-02, AR-19, RK-04
- **Tests:** UT (no network), GT, GRD
- **Dependencies / Blocked-by:** head-of-data licence note (S2); S3-DB-01
- **Out of scope:** LUCAS/EU data, WoSIS, weather clients.

### S3-ENG-02 No-test path: N only, `medium` max, estimate shown as `low`

- **Sprint:** S3 · **Workstream:** 1C · **Owner:** cp-engine + cp-agronomy-guard · **Size:** M (2 pt)
- **Story:** As a agronomist, I want a plan without a soil test recommending N only so that hard rule 3 holds with real estimates.
- **Acceptance criteria:**
  - Given a field with no soil test, when run, then only N is recommended with confidence ≤ `medium` and P/K lines say "soil test recommended".
  - Given an estimate in the input, when shown, then its confidence is `low` with source.
  - Given the same field with a lab test, then confidence is computed from the pack (see S3-ENG-03).
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** Confidence thresholds are pack values: PLACEHOLDER + TODO(agronomist).
- **Matrix IDs:** S03-1
- **Tests:** UT, GT, GRD
- **Dependencies / Blocked-by:** S3-ENG-01, S3-DB-01
- **Out of scope:** GDD timing (S4).

### S3-ENG-03 P/K with a lab test, method-aware, PLACEHOLDER critical values

- **Sprint:** S3 · **Workstream:** 1C · **Owner:** cp-engine + cp-agronomy-guard + cp-agronomist · **Size:** M (2 pt)
- **Story:** As a agronomist, I want P and K recommended only from a lab test using the extraction method so that no P/K is ever computed without method, form, depth and date.
- **Acceptance criteria:**
  - Given a lab P value with method Olsen, when run, then the correct critical-value table for that method is used.
  - Given a P value with no method, when run, then the engine refuses and says what is missing (RK-06).
  - Given the test result in oxide form, when converted, then both elemental and oxide are shown and tests pass.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** All critical values and rates PLACEHOLDER + TODO(agronomist) with sources.
- **Matrix IDs:** S03-2, RK-06
- **Tests:** UT, GT, GRD
- **Dependencies / Blocked-by:** S2-ENG-01, S2-DB-18
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-ENG-04 Unit conversions and canonical units used on display

- **Sprint:** S3 · **Workstream:** 1C · **Owner:** cp-engine + cp-concierge-app · **Size:** M (2 pt)
- **Story:** As a user, I want values shown in the user's unit preference while stored canonically so that display conversion never changes stored data.
- **Acceptance criteria:**
  - Given `unit_system=imperial`, when a plan is shown, then lb/ac and P2O5/K2O display with a visible conversion note.
  - Given storage, then canonical kg/ha and mg/kg are unchanged (round-trip test).
  - Given P vs P2O5 and K vs K2O, then the form is always labelled.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** Conversion factors already in `units.py`; no new constants.
- **Matrix IDs:** S03-3, HC-06
- **Tests:** UT, DBT
- **Dependencies / Blocked-by:** S2-DB-04, S2-DB-18
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-APP-01 Approved plan view: products and rates

- **Sprint:** S3 · **Workstream:** 1D · **Owner:** cp-concierge-app · **Size:** M (2 pt)
- **Story:** As a agronomist, I want the approved plan with products, rates, splits, explanations and confidence so that what I hand over matches the PDF.
- **Acceptance criteria:**
  - Given an approved plan with matched products, when viewed, then products, rates and splits show.
  - Given an unapproved plan, when a non-agronomist requests the view, then denied (RLS).
  - Given GDD timing (S4), then shown as manual/calendar window only; no GDD logic here.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** U9
- **Tests:** API, GRD
- **Dependencies / Blocked-by:** S2-ENG-05 (or nutrient-only if moved), S2-DB-08
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-APP-02 Soil estimate view with source and `low` confidence

- **Sprint:** S3 · **Workstream:** 1D · **Owner:** cp-concierge-app · **Size:** S (1 pt)
- **Story:** As a agronomist, I want a field's cached estimate with source and confidence so that I never mistake an estimate for a lab value.
- **Acceptance criteria:**
  - Given a field with an estimate, when I open `/fields/{id}/soil-estimate`, then it shows source, version, depth, retrieved_at and `low`.
  - Given user B of another org, then denied.
- **Data-model impact:** none
- **Permission / RLS impact:** RLS two-user test (allowed user + denied user, per the convention in "How to read").
- **Agronomic rules:** none
- **Matrix IDs:** UA-28
- **Tests:** API, RLS
- **Dependencies / Blocked-by:** S3-DB-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-APP-03 HSTS header and `/readyz`

- **Sprint:** S3 · **Workstream:** 1D · **Owner:** cp-concierge-app · **Size:** S (1 pt)
- **Story:** As a operator, I want HSTS and a readiness probe checking DB and storage so that the host knows when the app is not ready.
- **Acceptance criteria:**
  - Given a response over HTTPS, then `Strict-Transport-Security` is present (checked LIVE on staging).
  - Given the DB is down, when `/readyz` is called, then 503; when up, 200.
  - Given `/healthz`, then it stays liveness-only.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** SC-04, OB-03
- **Tests:** API, LIVE
- **Dependencies / Blocked-by:** S3-PLT-01 (for LIVE)
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-PDF-01 Private bucket, signed URLs ≤ 15 min, re-hash on download

- **Sprint:** S3 · **Workstream:** 1E · **Owner:** cp-pdf + devops-engineer · **Size:** M (2 pt)
- **Story:** As a agronomist, I want proofs stored in a private Railway Bucket with short-lived URLs so that nobody can fetch a proof by guessing a link.
- **Acceptance criteria:**
  - Given the bucket, when a proof is requested, then a signed URL of ≤ 15 min is returned only to allowed roles.
  - Given the file is downloaded, when re-hashed, then it equals the stored SHA-256; a mismatch is an error and an audit event.
  - Given an expired URL, then 403.
  - Given a user of another org, then no URL (denied).
- **Data-model impact:** none
- **Permission / RLS impact:** RLS two-user test (allowed user + denied user, per the convention in "How to read") on `proof_document`.
- **Agronomic rules:** none
- **Matrix IDs:** SC-05, AR-05
- **Tests:** API, SR, LIVE
- **Dependencies / Blocked-by:** Blocked-by AR-03 / FI go for Railway Bucket; S2-PDF-01
- **Out of scope:** share links and verify endpoint (S11).

### S3-PLT-01 Railway staging with app, PostGIS and bucket; demo

- **Sprint:** S3 (merge by Dec 23) · **Workstream:** 1F · **Owner:** devops-engineer + cp-platform · **Size:** L (3 pt)
- **Story:** As a founder, I want a staging environment with the app deployed and demoed so that "deployed to staging" in DoD becomes real.
- **Acceptance criteria:**
  - Given staging has app + PostGIS + bucket, when the app is deployed, then `/healthz` and `/readyz` pass.
  - Given synthetic data only, then no real farm data is on staging.
  - Given a demo on staging, then notes are filed (DD-05).
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** EV-02, AR-15, DD-05
- **Tests:** LIVE
- **Dependencies / Blocked-by:** Blocked-by AR-03, FI go on staging/bucket/worker cost
- **Out of scope:** production deploy; real farm data.

### S3-PLT-02 CI applies migrations to staging; manual approval for production

- **Sprint:** S3 · **Workstream:** 1F · **Owner:** cp-platform + devops-engineer · **Size:** M (2 pt)
- **Story:** As a maintainer, I want CI-driven forward-only migrations to staging and a manual gate for production so that migrations are applied the same way every time.
- **Acceptance criteria:**
  - Given a merge to `main`, when CI passes, then migrations apply to staging.
  - Given production, then the job waits for manual approval.
  - Given a migration edit of 0001–0010, then CI fails (forward-only check).
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** EV-05
- **Tests:** LIVE, CI
- **Dependencies / Blocked-by:** S3-PLT-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-QA-01 S3 DoD: same field with/without soil test on staging

- **Sprint:** S3 · **Workstream:** 1G · **Owner:** cp-qa + cp-agronomy-guard · **Size:** M (2 pt)
- **Story:** As a QA owner, I want proof that the same field gives correct confidence with and without a test so that hard rules 2 and 3 hold with P/K.
- **Acceptance criteria:**
  - Given a field with no test, when run on staging, then N only, ≤ `medium`, P/K "test recommended".
  - Given the same field with a lab test, then P/K appear with method-aware lines.
  - Given the go/no-go note, then it is filed.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** S03-DoD
- **Tests:** GT, E2E
- **Dependencies / Blocked-by:** S3-ENG-02, S3-ENG-03, S3-PLT-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-QA-02 Staging smoke test and RLS in CI

- **Sprint:** S3 · **Workstream:** 1G · **Owner:** cp-qa · **Size:** M (2 pt)
- **Story:** As a maintainer, I want a smoke test after each deploy so that a broken deploy is seen in minutes.
- **Acceptance criteria:**
  - Given a deploy, when the smoke runs, then login, create plan, review, PDF succeed on synthetic data.
  - Given RLS tests, then they run in CI against local PostGIS and staging read-only.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** OB-05
- **Tests:** E2E, RLS, LIVE
- **Dependencies / Blocked-by:** S3-PLT-01
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-WEB-01 Privacy page copy (after approval)

- **Sprint:** S3 · **Workstream:** 1H · **Owner:** cp-website + coo · **Size:** S (1 pt)
- **Story:** As a visitor, I want a privacy page naming the entity and contact so that consent is informed.
- **Acceptance criteria:**
  - Given approved copy, when published, then entity and contact appear.
  - Given unapproved copy, then not published.
- **Data-model impact:** none
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** NB-WEB-05
- **Tests:** LR
- **Dependencies / Blocked-by:** Blocked-by OQ-07; FI approval of legal entity/contact
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

### S3-WEB-02 First-party pilot funnel events (cro proposal) and `pilot_request` status columns

- **Sprint:** S3 · **Workstream:** 1H · **Owner:** cp-website + cp-database · **Size:** M (2 pt)
- **Story:** As a CRO, I want funnel events and a request status so that we see where pilot requests drop.
- **Acceptance criteria:**
  - Given an approved proposal, when a visitor submits, then a first-party event is stored without third-party trackers.
  - Given `pilot_request.status`, then migration is forward-only.
- **Data-model impact:** Forward-only migration on `pilot_request` (status columns) and an events table.
- **Permission / RLS impact:** none
- **Agronomic rules:** none
- **Matrix IDs:** NB-WEB-06
- **Tests:** DBT
- **Dependencies / Blocked-by:** Blocked-by CPO decision on cro's proposal
- **Out of scope:** anything not in the criteria above; later-sprint rows of the same matrix ID are separate stories.

## S4 (items recorded early)

### S4-PLT-01 Migrate production to the Canadian host

- **Sprint:** S4 · **Workstream:** 1F · **Owner:** cp-platform + cp-database (devops-engineer, ciso review) · **Size:** L (3 pt)
- **Story:** As Farjad Iranmehr, I want production running in a Canadian region before the first real farmer's data so that real farmer data is stored in Canada (CLAUDE.md, ADR 0009).
- **Acceptance criteria:**
  - Given the host chosen by 2027-01-04 (ADR 0009: D recommended, C runner-up), when staging and production are built there, then app, worker, website, Postgres + PostGIS and the proof bucket all run in a Canadian region, configured by env vars only, from the same Dockerfiles used on Railway.
  - Given `make db-migrate` run with a non-superuser deploy role, then all migrations apply and the RLS and privilege tests pass on the new host.
  - Given a restore drill, then a backup restores in Canada and the offsite Object Lock copy is in a Canadian region.
  - Given the cutover window, then `pilot_request` row counts match on both sides and a test submission lands in the new DB.
  - Given the date, then cutover is done by 2027-01-15 (S5 rehearsal enters real farms Jan 18); no real farmer data is ever written to Railway.
- **Data-model impact:** none (same migrations); 0002 no-superuser path if the host needs it.
- **Permission / RLS impact:** re-run all RLS and privilege tests on the new host.
- **Agronomic rules:** none
- **Matrix IDs:** AR-17, SC-08, OQ-06
- **Tests:** DBT, RLS, restore drill
- **Dependencies / Blocked-by:** Farjad Iranmehr's host choice + spend approval by 2027-01-04; DPA accepted after counsel review.
- **Out of scope:** Railway-only features (none to be used before S4, ADR 0009 Decision §4); deleting Railway services (needs Farjad's OK).

## Coverage table

Every ID in sections 1A–1H and the Standing line of `docs/plans/backend-distribution.md` maps to at least one story. IDs shared between sections appear once.

| ID | Workstream(s) in distribution | Story ID(s) |
|---|---|---|
| S01-G | 1A | S1C-01 |
| S01-6 | 1A | S1C-01 |
| AR-01 | 1A | S1C-02 |
| AR-04 | 1A | S1C-01 |
| AR-20 | 1A | S1C-02 |
| AR-23 | 1A | S1C-02 |
| AR-24 | 1A | S1C-02, S2-APP-06 |
| AR-26 | 1A | S1C-01 |
| AR-30 | 1A | S1C-02 |
| EV-01 | 1A | S1C-02 |
| PM-OM-oa | 1A | S1C-01 |
| PM-OM-ag | 1A | S1C-01 |
| REC-R8 | 1A | S1C-01 |
| GL-01 | 1A | S1C-03 |
| GL-11 | 1A | S1C-03, S2-DB-08 |
| HC-01 | 1A | S1C-03, S2-DB-08 |
| REC-R1 | 1B | S2-DB-01 |
| REC-D1 | 1B | S2-DB-02 |
| REC-R2 | 1B | S2-DB-09 |
| REC-D4 | 1B | S2-DB-10 |
| S01-3 | 1B | S2-DB-01 |
| S01-4 | 1B | S2-DB-03 |
| S02-2 | 1B | S2-DB-15 |
| AR-08 | 1B | S2-PLT-04 |
| AR-10 | 1B | S2-DB-02 |
| AR-11 | 1B | S2-DB-03 |
| HC-08 | 1B | S2-DB-16 |
| RO-02 | 1B | S2-DB-05 |
| RO-03 | 1B | S2-DB-05 |
| RO-06 | 1B | S2-DB-04 |
| RO-07 | 1B | S2-DB-04 |
| U3a | 1B | S2-DB-15 |
| U5 | 1B | S2-DB-17 |
| DM-C3 | 1B | S2-DB-14 |
| DM-C4 | 1B | S2-DB-14 |
| DM-C5 | 1B | S2-DB-14 |
| DM-01 | 1B | S2-DB-04 |
| DM-02 | 1B | S2-DB-05 |
| DM-03 | 1B | S2-DB-05 |
| DM-04 | 1B | S2-DB-16 |
| DM-05 | 1B | S2-DB-15 |
| DM-06 | 1B | S2-DB-14 |
| DM-07 | 1B | S2-DB-14 |
| DM-08 | 1B | S2-DB-17 |
| DM-09 | 1B | S2-DB-17 |
| DM-10 | 1B | S2-DB-18 |
| DM-11 | 1B, 1C | S2-DB-18, S2-ENG-06 |
| DM-13 | 1B | S2-DB-08 |
| DM-14 | 1B | S2-DB-09 |
| DM-15 | 1B | S2-DB-11 |
| DM-17 | 1B, 1D | S2-APP-05 |
| DM-19 | 1B | S2-DB-12 |
| DM-24 | 1B | S2-DB-19 |
| DM-27 | 1B | S2-DB-13 |
| DM-R1 | 1B | S2-DB-06 |
| DM-R2 | 1B | S2-DB-08 |
| DM-R4 | 1B | S2-DB-13 |
| DM-R5 | 1B, 1G | S2-QA-01 |
| SC-02 | 1B | S2-DB-02 |
| SC-06 | 1B | S2-DB-13 |
| DD-02 | 1B, 1G | S2-QA-03 |
| DD-03 | 1B | S2-DB-13 |
| PM-GR | 1B | S2-DB-15 |
| PM-FF-oa | 1B | S2-DB-06 |
| PM-FF-ag | 1B | S2-DB-06 |
| PM-FF-sa | 1B | S2-DB-06 |
| PM-ST-oa | 1B | S2-DB-07 |
| PM-ST-ag | 1B | S2-DB-07 |
| PM-ST-sa | 1B | S2-DB-07 |
| PM-RQ-sa | 1B | S2-APP-10 |
| PM-DR-fa | 1B | S2-DB-08 |
| PM-DR-ad | 1B | S2-DB-08 |
| PM-DR-oa | 1B | S2-DB-08 |
| PM-DR-sa | 1B | S2-DB-08 |
| PM-AP-ag | 1B, 1D | S2-DB-10, S2-APP-04 |
| PM-AP-sa | 1B | S2-DB-10 |
| PM-VP-oa | 1B | S2-DB-07 |
| PM-VP-sa | 1B | S2-DB-07 |
| DM-12 | 1B | S3-DB-01 |
| XD-08 | 1B | S3-DB-01 |
| HC-03 | 1B | S3-DB-02 |
| S02-1 | 1C | S2-ENG-01 |
| S02-4 | 1C | S2-ENG-05 |
| S02-5 | 1C | S2-ENG-04 |
| EN-05 | 1C | S2-ENG-02 |
| EN-06 | 1C | S2-ENG-03 |
| HC-07 | 1C | S2-ENG-01 |
| AR-31 | 1C | S2-ENG-01 |
| A4 | 1C | S2-DB-19, S2-ENG-05 |
| S03-1 | 1C | S3-ENG-02 |
| S03-2 | 1C | S3-ENG-03 |
| S03-3 | 1C | S3-ENG-04 |
| S03-DoD | 1C, 1G | S3-QA-01 |
| U7 | 1C | S3-ENG-01 |
| XD-02 | 1C | S3-ENG-01 |
| AR-19 | 1C | S3-ENG-01 |
| RK-04 | 1C | S3-ENG-01 |
| RK-06 | 1C, Standing | S3-ENG-03, STD-01 |
| HC-06 | 1C | S3-ENG-04 |
| A1 | 1D | S2-APP-01 |
| HV-06 | 1D | S2-APP-01 |
| HV-07 | 1D | S2-APP-02 |
| HV-11 | 1D | S2-APP-09 |
| RV-01 | 1D | S2-APP-01 |
| RV-02 | 1D | S2-APP-03 |
| RV-03 | 1D | S2-APP-04 |
| RV-04 | 1D | S2-APP-05 |
| RV-05 | 1D | S2-APP-03 |
| EN-02 | 1D | S2-APP-06 |
| EN-03 | 1D | S2-APP-07 |
| AC-07 | 1D | S2-APP-08 |
| U2 | 1D | S2-APP-11 |
| U4 | 1D | S2-APP-12 |
| U9 | 1D | S3-APP-01 |
| PM-RQ-sf | 1D | S2-APP-10 |
| S02-3 | 1D | S2-APP-02 |
| UA-28 | 1D | S3-APP-02 |
| SC-04 | 1D | S3-APP-03 |
| OB-03 | 1D | S3-APP-03 |
| S01-7 | 1E | S2-PDF-02 |
| AR-13 | 1E | S2-PDF-02 |
| AR-28 | 1E | S2-PDF-02 |
| U11a | 1E | S2-PDF-02 |
| UA-36 | 1E | S2-PDF-03 |
| UA-37 | 1E | S2-PDF-03 |
| HV-08 | 1E | S2-PDF-04 |
| PD-01 | 1E | S2-PDF-01 |
| PD-02 | 1E | S2-PDF-02 |
| PD-03 | 1E | S2-PDF-03 |
| PD-05 | 1E | S2-PDF-05 |
| PD-06 | 1E | S2-PDF-02 |
| PM-PX-ag | 1E | S2-PDF-03 |
| HC-10 | 1E, Standing | S2-PDF-05, STD-01 |
| AR-05 | 1E | S2-PDF-01, S3-PDF-01 |
| SC-05 | 1E | S3-PDF-01 |
| AR-03 | 1F | S2-PLT-04 |
| AR-15 | 1F | S3-PLT-01 |
| EV-02 | 1F | S3-PLT-01 |
| EV-04 | 1F | S2-PLT-01 |
| EV-05 | 1F | S3-PLT-02 |
| OB-06 | 1F | S2-PLT-01 |
| XD-07 | 1F | S2-PLT-02 |
| DD-05 | 1F | S3-PLT-01 |
| DD-06 | 1F | S2-PLT-02 |
| SC-03 | 1F | S2-PLT-03 |
| S01-DoD | 1G | S1C-04 |
| S02-DoD | 1G | S2-QA-02 |
| AR-35 | 1G | S2-QA-01 |
| OB-05 | 1G | S3-QA-02 |
| NB-WEB-02 | 1H | S2-WEB-01 |
| NB-WEB-03 | 1H | S2-WEB-02 |
| NB-WEB-04 | 1H | S2-WEB-03 |
| NB-WEB-05 | 1H | S3-WEB-01 |
| NB-WEB-06 | 1H | S3-WEB-02 |
| GL-06 | Standing | STD-01 |
| GL-07 | Standing | STD-01 |
| GL-08 | Standing | STD-01 |
| GL-09 | Standing | S2-DB-19, STD-01 |
| DD-01 | Standing | STD-01 |

### Count and reconciliation

- Unique IDs in 1A–1H plus Standing, all covered: **159** (checked by script against the distribution text; 0 missing, 0 extra).
- Raw ID mentions in 1A–1H: 160 (1A 16, 1B 65, 1C 19, 1D 22, 1E 16, 1F 10, 1G 7, 1H 5). IDs listed in more than one section (counted once): DD-02, DM-11, DM-17, DM-R5, PM-AP-ag, S03-DoD. Unique in 1A–1H: 154.
- The Standing line "GL-06..GL-09" expands to four IDs (GL-06, GL-07, GL-08, GL-09). Standing IDs not already in 1A–1H: GL-06, GL-07, GL-08, GL-09, DD-01 (5). Unique total: 154 + 5 = 159.
- The distribution's coverage check says "cto 153 IDs". **This backlog finds 159, a difference of 6.** The distribution lists the IDs by name, so the named IDs are the authority; the 153 figure could not be reproduced by any counting rule tried (raw mentions 160 + standing, unique, or excluding standing). The distribution total (194) should be corrected by +6 for cto, or the 153 explained by cto.
- Several IDs are covered by more than one story because the matrix row has parts in different sprints or workstreams (for example AR-05: filesystem store S2, bucket S3; DM-11: DB S2 and enum parity S2; HC-10: wording and standing guard).

## Contradiction check (D1–D4, R1–R9)

Result: no story contradicts D1–D4 or R1–R9. Stories that touch each:

| Decision | Held how | Stories |
|---|---|---|
| D1 Railway Postgres + app-owned auth + Railway Bucket + Postgres RLS via `SET LOCAL`; migrations in `db/migrations/`, forward-only, 0001–0010 never edited; no Supabase | Every RLS story keys on `app.*` settings; storage is `ProofStore` then Railway Bucket; "Supabase" is not used | S1C-01, S1C-02, S2-DB-02, S2-DB-03, S2-DB-04, S2-DB-06, S2-DB-07, S2-DB-08, S2-PDF-01, S2-PLT-04, S3-PDF-01, S3-PLT-01, S3-PLT-02 |
| D2 native app stays | Nothing built; `head-of-mobile` has no S1–S3 IDs; AC-02 comment optional | none touched (explicitly no story) |
| D3 S1–S30 calendar | Dates from the distribution; S3 merges by Dec 23 | Sprint goals table, S3-* stories |
| D4 AI agronomist is `ai_reviewed`, never the gate, never counts toward 90 %; real-farm approve needs a human `agronomist`; plans stay `in_review` until named | DB trigger + app guard + wording + labelled golden cases | S2-DB-10, S2-APP-04, S2-APP-05, S2-ENG-01, S2-ENG-02, S2-PDF-05, S2-QA-02, S1C-03 |
| R1 forward-only gap migrations | Gap analysis first; no edits to 0001–0010 | S2-DB-01, S2-DB-05, S2-DB-14, S2-DB-17, S2-DB-18, S3-PLT-02 |
| R2 `recommendation_line` replaces P/K columns | No `p_rate_kg_ha`/`k_rate_kg_ha` | S2-DB-09, S2-ENG-04, S2-APP-02, S2-APP-05 |
| R3 MFA S5 | Out of scope in S2/S3 | stated in S2-DB-03, S2-DB-10 |
| R4 Ontario winter wheat; residency open | Pack is `ca-on`; OQ-06 not assumed | S2-ENG-01, S3-ENG-01, deps table |
| R5 plan engine scope | Pack, splits, products in S2; P/K and no-test in S3; all constants PLACEHOLDER | S2-ENG-01, S2-ENG-04, S2-ENG-05, S3-ENG-01..03 |
| R6 no existing MVP | not referenced | none |
| R7 Sentry free tier only | not used here | none |
| R8 CISO findings A1, S1–S8 | S1C-01 closes before merge | S1C-01 |
| R9 missing referenced docs | not relied on | none |
| CLAUDE.md hard rules 1–10 | Rule 3: S3-ENG-02; rule 4: S2-DB-08, S2-APP-05; rule 7: S2-DB-09, S2-DB-18, S3-ENG-03; rule 8: S2-DB-10, S2-APP-04; rule 9: all agronomic stories; rule 1: STD-01; rule 10: S2-PLT-03 | as listed |

### Points that need a CPO eye (not contradictions)

- The due date/priority for the queue (S2-APP-01) cannot sit on the immutable `recommendation`; the gap analysis must choose where it lives.
- PM-ST-ag: the plan says agronomists read soil tests; the concierge needs them to write. S2-DB-07 keeps write for the concierge and records it as a decision.
- The agronomist "assigned" scoping (PM-FF-ag) is org-wide until grants exist (S9); recorded as a decision in S2-DB-06.
- S2 load is above comfortable capacity (see sprint goals); RK-X12 overflow order is given there.

## Phase 3/4 open-data items
Tracked separately in [`docs/data/open-data-backlog.md`](data/open-data-backlog.md) (owner: head-of-data). Licences: [`docs/data-sources.md`](data-sources.md) is the single source of truth.
