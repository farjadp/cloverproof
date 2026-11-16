# Backend plan — reconciliation with decisions already made

Owner: `product-manager` (CPO). Date: 2026-11-16. Applies to `docs/plans/backend-plan.md` (v1.0).
Rule: where this file and the backend plan disagree, **this file wins**. Where this file is silent, the backend plan wins.

## Decisions by Farjad Iranmehr (2026-11-16)

| # | Topic | Backend plan says | Decision | Effect |
|---|---|---|---|---|
| D1 | Platform | Supabase Postgres, Supabase Auth (JWT), Supabase Storage, RLS via JWT claims, `supabase/migrations/` | **Keep Railway** (ADR 0004) + **app-owned auth** (ADR 0005) + **Railway Bucket** for files. **Add Postgres RLS on Railway** as defence in depth. | Every "Supabase" in the plan reads as: Railway Postgres + PostGIS / app-owned sessions / Railway Bucket. §6.8 RLS is implemented with Postgres RLS policies keyed on a per-transaction setting (e.g. `SET LOCAL app.user_id`, `app.org_id`, `app.platform_role`) set by the app from the server-side session, not a Supabase JWT. Migrations live in `db/migrations/`. A new ADR records RLS-on-Railway. |
| D2 | Mobile | Native mobile apps are a non-goal (mobile-friendly web only) | **Native app stays in the plan.** | Phase B/C deliver mobile-friendly web as the plan says (application log S10). `head-of-mobile` plans the native app (stack ADR, offline sync) from S11 and builds after the MVP gate (S12), scheduled by the CPO. §1.2 "Native mobile apps" non-goal is removed. |
| D3 | Sprint calendar | S1–S30 (Nov 16, 2026 → Jan 28, 2028) | **Backend plan's 30 sprints are the master calendar.** | `docs/sprints/roadmap.md` is superseded for dates; its test gates, learning loop and per-group content are merged into the S1–S30 calendar. Website, growth, operations, data, security and mobile work is mapped onto the same sprints. |
| D4 | Reviewing agronomist | A named human agronomist | **For now an AI specialist agent (`cp-agronomist`); later a human.** | See "AI agronomist rule" below. |

## AI agronomist rule (non-negotiable, from CLAUDE.md hard rules 8–9)
- `cp-agronomist` is an AI agent. It may: review engine logic and explanations, research published methods, draft `external_reference` golden cases from published sources (entered by hand from official documents; never scraped), propose constants with sources, review proof wording, prepare questions for the human agronomist.
- Its sign-off is labelled **`ai_reviewed`**. It is never `agronomist_approved`, never counts toward the 90 % agreement gate, and never counts as the review gate.
- **No recommendation reaches a real farmer on an AI review alone.** In the app, the approve action for a real farm's plan requires a human user with the `agronomist` role. Until a human agronomist is named, real-farm plans stay in `in_review`.
- Constants it proposes stay `PLACEHOLDER` until a human agronomist validates them.
- Open item: name the human agronomist before the S5 concierge gate (Jan 29, 2027).

## Other conflicts resolved by the CPO (engineering-level)

| # | Topic | Resolution |
|---|---|---|
| R1 | Data model (§6) vs current schema (PR #3) | §6 is the target model. Gaps (`profile` vs `app_user`, `org_membership` vs `membership`, `soil_sample` + `soil_measurement` vs current soil table, `recommendation_line`, `access_grant`, `audit_event`, catalogs, platform tables) are closed with **forward-only migrations**; never edit an applied one. `cp-database` writes the gap analysis first. |
| R2 | P/K columns proposed as migration 0011 on `recommendation` | Superseded by §6.4 `recommendation_line` (per-nutrient rows with explicit form). Do not add `p_rate_kg_ha`/`k_rate_kg_ha` to `recommendation`; implement `recommendation_line` instead. |
| R3 | MFA | §12: MFA **required** for `agronomist`, `staff`, `superadmin` (ADR 0005 said optional TOTP) — target S5. |
| R4 | Launch country (§18 Q2, S2 gate) | Canada: Ontario winter wheat primary, Prairie wheat backup (decided 2026-11-16). Data residency (§12, Q6): Railway has no Canadian region (ADR 0004) — needs a decision before real farmer data (open). |
| R5 | Engine scope | Plan's engine scope (real pack S2, products + splits S2, P/K with soil test S3, no-test SoilGrids S3, GDD timing S4) replaces the narrower `webapp-v1.md` scope. All constants stay PLACEHOLDER until a human agronomist validates them. |
| R6 | Existing MVP (§18 Q1) | None — ADR 0001 "start fresh". S1 audit item is closed. |
| R7 | Sentry (free tier) | Allowed (no cost). Any paid tier needs Farjad Iranmehr's go. |
| R8 | Security review findings (S2 auth review) | Carry into S2/S3 regardless of D1 (A1, S1–S8 in `docs/security/S2-auth-review-step5.md` on the ciso branch). |
| R9 | Referenced docs `05-mvp-build-brief.md`, `03-roadmap-and-validation.md` | Not in the repo — requested from Farjad Iranmehr. |

## Open questions still for Farjad Iranmehr (from §18)
Q3 CTO weekly capacity / second developer · Q4 human agronomist name, hours, credentials · Q5 email provider + sender domain · Q6 data residency (Canada vs US region) · Q7 who drafts legal disclaimer/terms · Q8 forecast provider + budget · Q9 billing model (S26).
