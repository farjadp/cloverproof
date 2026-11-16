# CloverProof roadmap — sprints, test gates and the learning loop

> **Dates superseded (2026-11-16):** the master calendar is now S1–S30 in `docs/plans/backend-plan.md` §15 (decision D3 in `docs/plans/backend-plan-reconciliation.md`). The test gates, learning loop and Definition of Done below still apply to every sprint.

Owner: `product-manager` (CPO). Approved direction: Farjad Iranmehr, 2026-11-16.
Cadence: **2-week sprints**, Monday → Friday of week 2. Every sprint ends with a review + retro (below).
Build order stays: website → web app → mobile. Other groups (growth, operations, data, security, strategy) run in parallel from Sprint 2.

## North-star for this phase
By **Feb 1, 2027** Farjad Iranmehr runs a real farm from intake to an approved plan + proof PDF in one sitting, and every plan feeds the calibration dataset (engine output vs agronomist final + reason). Field season **Feb–Apr 2027**: 5–10 pilot farms.

## Sprint calendar

| Sprint | Dates | Goal | Groups / owners |
|---|---|---|---|
| **S1** | Nov 16 – Nov 27 | Foundations: website v1 live; web app plan, scaffold, engine v0, DB schema; concierge app login + case path | cto (`cp-website`, `cloverproof-lead`) |
| **S2** | Nov 30 – Dec 11 | Concierge app end to end (local) + proof PDF v0; PostGIS on Railway; pilot recruitment launched; pilot SOP + intake; privacy/terms; threat model + auth review; metric definitions | cto, cro, coo, ciso, head-of-data |
| **S3** | Dec 14 – Dec 24 (short) | Staging deploy of the web app; QA end-to-end on staging; **5 real wheat cases in (Dec 18)** → golden tests replaced, constants status updated; calibration baseline; website SEO/a11y/Lighthouse | cto, head-of-data, cp-agronomy-guard, cp-website |
| — | Dec 25 – Jan 3 | Holiday freeze: no deploys, monitoring only | — |
| **S4** | Jan 4 – Jan 15 | Real cases through the tool; fixes from Farjad Iranmehr's walkthrough; pilot farms selected + onboarded; French website locale (native review); security fixes | cto, coo, cro, ciso |
| **S5** | Jan 18 – Jan 29 | **Go / no-go for Feb 1**: release gate, runbooks, backups tested, support macros, training; production deploy | cto (cp-qa), coo, ciso |
| **S6–S10** | Feb 1 – Apr 30 (5 sprints) | **Field season.** Run 5–10 farms; fixes only, no new features; every sprint: calibration review, minutes-per-plan trend, farmer feedback; Italian/Spanish locales | all groups, cadence below |
| **S11** | May 3 – May 14 | Season retrospective; Phase 4 decision (farmer portal, pricing, next country pack); mobile stack ADR | CPO, cso, head-of-mobile, head-of-data |
| **S12+** | from May 17 | Phase 4 per the S11 decision: farmer portal (Next.js), mobile app (offline field use, planned-vs-actual log), remaining locales (bg, fi, tr, ar RTL) | cto, head-of-mobile, cro |

## Sprint content by group (S2–S5)

### Engineering (`cto` → `cloverproof-lead`, `cp-website`)
- S2: Step 5 complete (case path, versioning, approve, timer) · Step 6 proof PDF v0 · PostGIS service healthy on Railway · `pilot_request` moved to the shared DB with the website (runbook `docs/runbook-db-switch.md`).
- S3: Step 7 staging deploy (app service, bucket, backups) · real cases replace golden samples · website SEO basics, Lighthouse ≥ 90 mobile, a11y pass.
- S4: fixes from real use · French locale · error monitoring + uptime alerts.
- S5: production deploy behind the release gate · rollback runbook rehearsed.

### Revenue & Growth (`cro`)
- S2: pilot ICP (crop, region, farm size, soil-test habit) · pilot recruitment plan (channels: agronomists, co-ops, labs, farm communities) · pilot-request funnel tracking from `pilot_request`.
- S3–S4: outreach drafts (never sent without Farjad Iranmehr) · partner shortlist (labs, agronomy firms) · 5–10 farms confirmed by Jan 15.

### Operations (`coo`)
- S2: pilot SOP (request → intake → plan → review → delivery) · intake checklist (`customer-onboarding-specialist`) · privacy notice + terms + consent wording reviewed (`legal-compliance-specialist`) · support FAQ.
- S3–S5: agronomist workload model (minutes per plan) · onboarding messages · grants radar for agri-tech programs (`grants-specialist`).

### Data & AI (`head-of-data`)
- S2: metric definitions (minutes per plan, edit rate, approval rate, engine-vs-final difference per nutrient, pilot funnel) · data dictionary + PII classes (`data-governance-specialist`).
- S3: calibration baseline from the 5 real cases (`data-scientist`) · weekly metrics report design.
- S6–S10: calibration review every sprint (learning loop below).

### Security (`ciso`)
- S2: threat model for the web app (auth, sessions, org scoping, proof integrity, public repo) · auth + CSRF review of Step 5.
- S3–S5: dependency + secret scans in CI · backup/restore test · pre-release security gate.

### Strategy (`cso`) — light until S11
- S3: positioning one-pager and competitor scan (vendor-neutral, proof-backed).
- S11: business model, pricing hypotheses, next country pack.

### Mobile (`head-of-mobile`) — plan only until S11
- S11: stack ADR (React Native/Expo vs Flutter vs native) and offline/sync architecture.

## Test gates (no sprint closes without them)
Every change: lint + unit tests green in CI; new behaviour has a test written first (engine: golden case first).
| Gate | Owner | When |
|---|---|---|
| Unit + integration tests, DB tests against PostGIS | each engineer, verified by `cp-qa` | every PR |
| Golden report (engine vs expected, per number) | `cp-engine`, `cp-agronomy-guard` | every engine/pack PR |
| Agronomy guard review (no invented constants, N-only without soil test, explanations, confidence) | `cp-agronomy-guard` | every PR that shows or computes a number |
| End-to-end walkthrough of the concierge flow | `cp-qa` (+ Farjad Iranmehr from S3) | end of S2, S3, S4, S5 |
| Security review | `security-engineer` via `ciso` | S2 (auth), S5 (release) |
| Website: build, mobile 375 px, Lighthouse ≥ 90, a11y | `cp-website` | every website deploy |
| Release gate go/no-go | `cp-qa` + `ciso` + CPO | S5, then every production release |

## The learning loop (every sprint)
1. **Sprint review (Friday, week 2):** each head shows what is now true, with evidence (PR, URL, screenshot). CPO summarises for Farjad Iranmehr in 10 lines.
2. **Retro:** what slowed us (blocked permissions, waiting on decisions, rework), one change for next sprint. Written to `docs/sprints/S<n>-retro.md`.
3. **Calibration loop (from S3, mandatory S6–S10):** every reviewed plan stores engine output + agronomist final + reason → `data-scientist` analyses differences per nutrient/crop/soil-test method/confidence → proposes constant changes with evidence → Farjad Iranmehr approves → `cp-engine` adds a golden case first, then changes the pack version → `cp-agronomy-guard` reviews. Never silently.
4. **Product metrics review:** minutes per plan, edit rate, approval rate, pilot funnel — trend vs last sprint (`data-analyst`).
5. **Farmer & agronomist feedback (S6+):** support digest (`customer-support-specialist`) + onboarding friction (`customer-onboarding-specialist`) → backlog items with evidence (`agile-manager`).
6. **Records:** every head sends the standard report to `documentation` → Notion work log, decision log, open items.

## Definition of Done (every story)
Acceptance criteria met · tests written and green in CI · reviewed (and guard-reviewed if it touches numbers) · no secrets · docs/ADR updated if a decision changed · deployed where relevant and checked live · standard report sent.
