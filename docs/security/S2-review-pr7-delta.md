# S2 security review — PR #7 delta c720eec..85814b6 (branch `webapp-step5-app`)

- Reviewer: `security-engineer` (reports to `ciso`), 2026-11-16
- Scope: `git diff c720eec..85814b6` (7 commits, 39 files): `plan_web.py`, `planning.py`, `timer.py`, `account.py`, `repo/{plans,farms,admin_users}.py`, `auth.py`, `cli.py`, `config.py`, `main.py`, `web.py`, new templates, self-hosted fonts, `db/migrations/0010_password_change_required.sql`. Previous findings: `docs/security/S2-auth-review-step5.md` (S1–S8, N1–N10).
- Method: static read of a read-only checkout at 85814b6, plus the DB triggers the new routes rely on (`0006`, `0007`). `uv run pytest app/tests -q` without a DB: **46 passed, 125 skipped** (every DB test, including `test_plan_flow.py`, `test_admin_users.py`, `test_account.py`, was skipped, so none of them ran). Nothing was run against Railway or production.
- Line numbers refer to 85814b6.

## Verdict
The plan flow is built carefully. Every id taken from a URL or form is resolved through an org-scoped query. `reviewer_id` comes from the session. Approval goes through a role check in the service and a DB trigger. Edits are INSERT-only, with `parent_id` and a reason. I found no IDOR and no CSRF gap.

There is **one BLOCKER, tied to CPO decision D4**: no column or check separates human and AI/service accounts, so an AI account that holds the agronomist role passes the approval gate. There are four new SHOULD-FIX items: concurrency holes in the version/approval invariants, no durable audit of the actions that create approvers, minutes double-counted across edit and approve, and S5 now in conflict with the new web user management. Six of the earlier S1–S8 are still open; S3 is fixed.

## Findings

### BLOCKER

**B1. AI/service accounts are indistinguishable from humans, so `cp-agronomist` would satisfy the approval gate (D4 not enforced)**
- Evidence: `app_user` has no kind/type column (`db/migrations/0003_identity.sql:10-25`; 0010 adds only `password_change_required`). The approval trigger checks only `has_org_role(..., 'agronomist')` (`db/migrations/0007_review.sql:43-47`). The service checks only `"agronomist" in context.roles` (`app/cloverproof_app/plan_web.py:46-52`, used at `:492`). An owner can create any account with role `agronomist` from the web (`app/cloverproof_app/account.py:225-261`, `repo/admin_users.py:125-151`). The CLI can do the same (`cli.py` `user-create --role agronomist`). Nothing in the code, migrations or docs mentions `cp-agronomist` or `ai_reviewed`.
- Exploit path: an owner creates `cp-agronomist` with role agronomist, or an operator does it via the CLI. The AI agent logs in with its password, or drives the UI with an agronomist session, and POSTs `/plans/{id}/review decision=approve`. The trigger accepts it, and the plan shows "Approved" for a real farm. This breaks hard rule 8 and D4, and it pollutes the calibration dataset, because AI edits are recorded as agronomist decisions.
- Fix (one migration plus small code changes):
  1. `alter table app_user add column kind text not null default 'human' check (kind in ('human','service'));` Add a check that service accounts cannot log in: `check (kind = 'human' or (password_hash is null and auth_provider = 'local'))`.
  2. In `review_check_reviewer()`, raise when `new.decision = 'approve'` and `(select kind from app_user where id = new.reviewer_id) <> 'human'`. Do the same in `recommendation_check_author()` for `kind = 'agronomist'`, so AI output is never stored as an "agronomist" version.
  3. Store AI output separately: either a new `review_decision` value `ai_reviewed` (never counted as approval), or a separate `ai_review` table referencing `recommendation`. The CPO decides which. `_SUMMARY` and `load_plan` must not treat it as final.
  4. In the app, `login` rejects `kind <> 'human'` (with the same generic error). `/admin/users` and the CLI create humans only; service accounts are created by migration/admin login only.
  5. Tests: trigger rejects approve by a service account even when it has an agronomist membership. Login as a service account fails.
- Residual risk: this blocks a dedicated AI account, but not an AI agent driving a human agronomist's browser session. That residual has to be handled by policy, and TOTP on agronomist accounts (the `totp_secret` column already exists) makes credential sharing harder.
- Gate: this must land before any AI reviewer account exists and before the first real-farm plan. It is not exploitable by outsiders.

### SHOULD-FIX

**F1. Version/approval invariants rely on check-then-insert without locks; the DB does not enforce "latest only" or "no fork"**
- Evidence: `plan_web.py:456-460` (`check_version` compares with `view.latest`, read without lock in `load_plan`, `:322-350`), then `:480-485` / `:508-510` insert. No `select ... for update` anywhere in `repo/plans.py`. The DB has a unique approval index (`0007_review.sql:30`). It has no unique index on `recommendation(parent_id)` and no trigger that blocks (a) approving or rejecting a recommendation that already has a child, (b) inserting a child under a recommendation that already has an approve/reject, or (c) both an approve and a reject on the same recommendation.
- Exploit path: two tabs, or the agronomist plus a second agronomist, on the same plan. One submits Edit and the other Approve within the same window. Both pass `check_version` and both commit: v1 is approved and v2 (unreviewed) exists. `load_plan` then shows v2 "In review", while any query for "approved recommendations" returns v1 even though the agronomist's final numbers differ. Concurrent Edit+Edit forks v1 into two children; `by_lineage` then picks one arbitrarily (`plan_web.py:331-332`). Concurrent Approve+Reject stores both, and the UI (`:334-336`, first by time) and `_SUMMARY` (`repo/plans.py:275-279`, approve wins) disagree.
- Impact: hard rules 4 and 8 (which numbers were approved) and the calibration dataset become ambiguous. No outside attacker is needed; a double click across tabs is enough.
- Fix: (1) in the edit/review POSTs, lock the plan first: `select id from crop_plan where organisation_id=%s and id=%s for update`. (2) New migration: `create unique index recommendation_one_child_idx on recommendation (parent_id) where parent_id is not null;`, `create unique index review_one_final_idx on review (recommendation_id) where decision in ('approve','reject');`, plus triggers that reject a final review on a recommendation with children and reject a child of a recommendation with a final review. (3) Map the resulting unique violation to the existing 409 `STALE_VERSION`/`ALREADY_REVIEWED` instead of a 500. Add a DB test for each case.

**F2. No durable audit of role grants, password resets and account creation (the actions that create approvers)**
- Evidence: `account.py:259` and `:360` only `log.info` (stdout). `set_roles` (`repo/admin_users.py:171-194`) and enable/disable (`:215-230`) log nothing. An owner can grant themselves `agronomist` (`account.py:322-338`, no self check). An owner can also reset an agronomist's password, read the temporary password on screen (`account.py:341-361`), sign in as them and approve. The review row then names the agronomist.
- Impact: the review gate's root of trust (who holds `agronomist`) can change without a record a reviewer could later inspect. The PDF/proof story ("approved by the agronomist") cannot be defended.
- Fix: an append-only `admin_event` table (actor, target, org, action, old/new roles, at), written in the same transaction by each admin action. It needs the same `forbid_change` triggers, and cp_app gets `insert, select` only. Better still, an AFTER trigger on `membership` and on `app_user.password_hash` writes it, so the CLI is covered too. Optionally refuse self-grant of `agronomist` from the web.

**F3. S5 has become structural: the web app now needs `cp_app` write access to `membership`/`app_user`, so the earlier fix (revoke) no longer applies**
- Evidence: `repo/admin_users.py:141-150, 184-194, 224-230` write `app_user` and `membership` as `cp_app`. The grant is still `0003_identity.sql:84`.
- Impact: as in S5, an injection or logic bug in any route can insert an agronomist membership and then approve. With B1 and F2 in place this is detectable, but not prevented.
- Fix: move the admin writes into `SECURITY DEFINER` functions (owner: a dedicated role; `set search_path = pg_catalog, public`) that take `actor_id`, check `has_org_role(actor_id, org, 'owner')` inside, and write the audit row. Then revoke direct `insert/update/delete` on `membership` and `organisation`, and `update` on `app_user` except `(password_hash, password_change_required, display_name)`, from `cp_app`.

**F4. `minutes_spent` is cumulative per review event and can be inflated or reset by the client (metric integrity; not a security boundary)**
- Evidence: `plan_web.py:477` and `:507` both compute minutes from the same plan start. `plan_edit_save` does not reset the timer cookie, so Edit at minute 10 and then Approve at minute 15 store 10 and 15. Summing per plan gives 25 instead of 15. Clearing the cookie or using a new session restarts the count at the next GET (`plan_web.py:372-375`; the purpose is bound to `session_id`, `timer.py:45-46`), which deflates the count. Leaving the tab open inflates it up to `MAX_AGE` = 7 days (`timer.py:23`), with no cap.
- Fix: define the metric as `max(minutes_spent)` per plan, or reset the start after each recorded review (store `minutes since previous review`). Cap minutes per review (e.g. 240) and flag capped values. Recording the signed start in a column (`review.started_at`) lets analysts recompute later. Forgery of the start time itself is prevented (HMAC, bound to session and plan, future stamps rejected, `timer.py:34-42`), which I verified.

### NOTE

- **N11. Temporary passwords never expire.** `repo/admin_users.py:98-104` sets the flag only. The forced change makes a leaked temporary password still usable for full takeover of a not-yet-activated account. Add `temp_password_expires_at` (e.g. 72 h) and treat it as invalid after that (the generic login error). Entropy is fine: 20 symbols from 56 (the alphabet at `account.py:49` has 56 characters; the comment says 55) ≈ 116 bits from `secrets.choice`.
- **N12. Cross-org email enumeration.** `create_member` reports "An account with this email already exists" for accounts in other orgs (`repo/admin_users.py:136-140`). An owner learns that an address has an account somewhere. This is low-impact with a single org today. The check-then-insert also races to a unique violation, which surfaces as a 500 (`main.py:148-155`, nothing saved).
- **N13. The password-change counter shares the login limiter key `(email, ip)`** (`account.py:163-175`). Five mistyped current passwords also lock login from that IP. Use a separate key prefix. Argon2 work on `/account/password` and `/admin/users` is authenticated, but it is not covered by the S2 semaphore either (`account.py:170,190,254,356`).
- **N14. One timer cookie per opened plan** (`timer.py:69-79`, Max-Age 7 days). Browsers cap cookies per domain (Chrome: about 180) and evict when over the cap, so a heavy review season could evict `cp_session`. Delete the timer cookie after approve/reject, or keep one cookie holding a small signed map.
- **N15. LIKE wildcards in `q`** are not escaped (`repo/farms.py:74`). `%`/`_` widen the match within the user's own org only. Escape them for correctness.
- **N16. DB trigger does not require an agronomist for `reject`/`edit` reviews** (`0007_review.sql:43-47`; only approve is checked). The service checks all three (`plan_web.py:435,466,492`). `recommendation_check_author` does require an agronomist for `kind='agronomist'` (`0006`:~98), so DB-level edits are covered indirectly. Extend the trigger to `reject` for symmetry.
- **N6 (prior) now relevant:** pages with farmer data exist, and `historyCacheSize` is still default (`templates/base.html:6`). No `hx-push-url`/`hx-boost` is used, so nothing is cached today. Set it to 0 before anyone adds push-url.

## S1–S8 status at 85814b6

| ID | Status | Where now |
|---|---|---|
| S1 login rate-limit key / XFF spoofing / no per-account ceiling | **Open** (now also used by password change) | `web.py:79-82`, `ratelimit.py:30`, `account.py:165` |
| S2 unbounded concurrent argon2 | **Open** | `security.py:28-32` (no semaphore); new callers `account.py:170,190,254,356` |
| S3 reset does not revoke sessions | **Fixed** | CLI `cli.py:92-95` → `admin_users.set_temporary_password` revokes all (`repo/admin_users.py:98-104`); web reset `:205-212`; disable revokes (`:228`); own change revokes others (`:87-95`). No stand-alone "revoke all" CLI; web disable covers it. |
| S4 no check that app is not superuser | **Open** | no `rolsuper`/`pg_has_role` check in `main.py`/`db/pool.py` |
| S5 cp_app writes membership/app_user | **Open, worse** (now required by the app) | `0003_identity.sql:84`; see F3 |
| S6 absolute `url_for` URLs behind TLS proxy | **Open**, grew: font preloads also absolute, while CSS `@font-face` uses path-only `/static/...`, so preload and fetch URLs differ | `templates/base.html:8-12`; no `TrustedHostMiddleware` |
| S7 DB tests not in CI | **Open** (125 DB tests skipped, incl. new plan/admin/account tests) | `.github/workflows/ci.yml:37` |
| S8 no HSTS | **Open** | `main.py:53-60` |

## Verified OK
- **IDOR, every id**: farmer (`plan_web.py:118,139,155`), farm (`:160-162`, must belong to that farmer in the org), field (`:186-190`, used before every plan create/new), plan (`load_plan` `:324`), recommendation (the review/edit uses server-side `view.latest.id`; the form `recommendation_id` is only compared, `:459`), soil test (`repo/plans.py:100-117` org-filtered), user (`account.py:264-268`, `get_member` requires membership in the current org, `repo/admin_users.py:60-66`). All repo queries take `org_id` from the session context. Composite FKs `(organisation_id, id)` stop cross-org links at the DB (`0007_review.sql:24-25`, `0006`:71-78).
- **reviewer_id / created_by** always `context.user.id` (`plan_web.py:481,484,509`), never from the form.
- **Agronomist check**: service `require_agronomist` on GET/POST edit and POST review (`:435,466,492`); DB trigger on approve (`0007:43-47`) and on agronomist recommendations (`0006` `recommendation_check_author`). Membership is resolved in the recommendation's org (`review.organisation_id` + composite FK).
- **Approve only the latest version** (absent races, see F1): `check_version` (`:456-460`) plus `read_only` once a final review exists. One approval per recommendation (unique index).
- **Immutability**: `repo/plans.py` has only INSERTs for recommendation/review; an edit is a new row with `parent_id` + reason (`:167-182`), and the DB checks enforce the reason and that the kind matches the parent. The UPDATE/DELETE/TRUNCATE triggers are unchanged.
- **Admin authz**: all `/admin/users*` routes use `require_org_role("owner")` in the current org (`account.py:42`). Staff and agronomists get 403. An owner can only create members in their own org (`org_id=context.org.id`). Only owner/agronomist/staff can be assigned (`MANAGED_ROLES`, validated in route and repo). The last enabled owner is protected with `FOR UPDATE` (`repo/admin_users.py:154-162`). Account-wide actions refuse multi-org users (`:197-202`). Self-reset is refused (`account.py:346-348`).
- **Temporary passwords**: `secrets.choice`, about 116 bits. Stored only as argon2id. Shown once, in the POST response, with `Cache-Control: no-store` (`main.py:114`). Autoescaped, never logged. All sessions are revoked on reset.
- **Forced change**: enforced in `current_user` (`auth.py:111-120`), which every authenticated route depends on (`UserDep` → `current_org` → `require_org_role`), including `/orgs/choose`. Exempt paths are exact matches: `/account/password` and `/logout` only. HTMX requests get 403 + `HX-Redirect`, non-GET requests get 403 (`account.py:77-85`). The change itself requires the current (temporary) password. No bypass route found.
- **Password change**: requires the current password (rate-limited), at least 12 characters, must differ, needs confirmation. It clears the flag and revokes all other sessions, keeping the current one (`repo/admin_users.py:87-95`).
- **CSRF**: the app-wide `csrf_guard` covers every new POST (`/farmers`, `/farmers/{id}/farms|fields`, `/fields/{id}/plans`, `/plans/{id}/edit|review`, `/account/name|password`, `/admin/users*`). Forms read the cached form; there are no state-changing GETs (`/plans/{id}/timer` and `/plans/value-row` only render).
- **Templates**: Starlette autoescape; no `|safe`/`Markup` in the delta. Temporary password and user data are escaped.
- **CSP**: unchanged and strict. Fonts are self-hosted under `/static/fonts` and covered by `default-src 'self'` (no `font-src` needed); no external origins; no inline style/script added.
- **Input validation**: lengths bounded (`text()` limits, `Form(max_length)`), area finite and > 0, `i` clamped 0..50. Engine inputs go through `planning.validate_plan_form`. Unhandled errors give a generic 500 page with a timestamp only (`main.py:148-155`); the transaction rolls back.
- **Migration 0010**: additive, `not null default false`, runs as `cp_migrator`. No grant change (inherits the existing `cp_app` update on `app_user`).
- **PACK_PATH**: read from env only, fail-fast with the class name only (`main.py:42-48`).

## Not verified
- All DB-backed behaviour: 125 tests skipped (no `TEST_DATABASE_URL`). That includes `test_plan_flow.py`, `test_admin_users.py` and `test_account.py`, so the trigger behaviour and the forced-change flow were read, not executed.
- The race in F1 was derived from code (READ COMMITTED default, no locks), not reproduced.
- `planning.py` engine-input validation was not read line by line beyond the boundary checks in `plan_web.py`; `test_planning_edit.py` passes.
- Railway proxy behaviour (S1/S6/S8) remains unverified, as before.
- Where D4 is recorded (no ADR or doc in the repo mentions it). B1 is based on the brief.
