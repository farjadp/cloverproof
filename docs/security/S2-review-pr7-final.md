# S2 security review: PR #7 final re-review at d6fc7b8 (`webapp-s2-security`, main merged in)

Reviewer: security-engineer for the CISO. Static review plus local DB tests against a throwaway PostGIS container. Read-only checkout, nothing edited there.
Criteria: CLAUDE.md rules 8, 11 and 12 (binding), and `docs/security/adr-0008-rls-review-criteria.md` §5.4 and §7 on `origin/security-superadmin-approval`.

## Verdict: REJECT (one blocker, a small fix)

All S1–S8, B1 and F1–F4 fixes are in, and the DB review gate itself is sound: `review_kind` is derived in the DB, a value sent by the app is only checked against it, service accounts never approve, and `ai_reviewed` never unlocks a proof. One new path breaks "owner/staff cannot approve": an org owner can reset a superadmin's password from the web page, sign in as that superadmin and approve (NB1). The fix is two lines in the app plus one DB guard. After that fix and a test for it, the verdict becomes ACCEPT WITH NOTES.

## Prior findings at d6fc7b8

| ID | Status | Evidence (path:line at d6fc7b8) |
|---|---|---|
| S1 login limits / XFF | FIXED (code) | `ratelimit.py:141-153`: per-IP, pair, account and global windows checked before argon2. `web.py:80-93`: TCP peer by default, one configured header, rightmost entry. Spoofing aside, see NS1 for the default on Railway. |
| S2 unbounded argon2 | FIXED | `security.py:31-49`: BoundedSemaphore (default 2), 5 s acquire timeout, then 503. Global budget at `config.py:83`. See NS2. |
| S3 reset does not revoke sessions | FIXED | `sessions.revoke_all_for_user` plus `cli user-revoke-sessions` (6c0d069); `admin_users.set_disabled` revokes sessions (`repo/admin_users.py:242+`). |
| S4 superuser / BYPASSRLS check | FIXED | `db/pool.py` `check_least_privilege`: refuses superuser, BYPASSRLS, non-cp_app and cp_admin members. Tests pass (`test_security_startup.py`). |
| S5 cp_app writes membership | FIXED | `0011_least_privilege_roles.sql:40-49`: membership and organisation writes revoked from cp_app. The web grants and removes only staff/farmer, through SECURITY DEFINER functions (`:55-117`). Residual: cp_app still has UPDATE on `app_user.password_hash` for every row (`:45-46`). See NB1. |
| S6 absolute URLs | FIXED (per commit c6cddd2; not re-read line by line) | Path-only asset URLs; TrustedHostMiddleware with ALLOWED_HOSTS required when deployed (`config.py:109-116`). |
| S7 DB tests not in CI | FIXED | `.github/workflows/ci.yml:39-70`: `db` job on postgis/postgis:18-3.7 runs `make db-test` with `CP_DB_TESTS_REQUIRED=1`. |
| S8 HSTS | FIXED | `main.py:152`: HSTS in deployed environments. |
| B1 AI/service accounts | FIXED | `0012:33-38`: `actor_kind`, and service accounts may not have a password. `auth.py`/`repo/users.py:23-28`: `can_sign_in` requires a human. `repo/sessions.py:49`: a session is only loaded for a human. `0012:152-205`: a service account cannot approve, edit, reject or author. |
| F1 version/approval races | FIXED | `0012:321-383`: one-child index, one-final and one-approval indexes, and triggers under advisory locks. `repo/plans.py:172`: plan row `for update`. 409 on conflict (2b4aa6c). `test_review_integrity.py` passes. |
| F2 audit of approver changes | FIXED, with notes | `0012:438-606`: append-only `admin_event`, written only by SECURITY DEFINER triggers on membership and app_user. cp_app has SELECT only, and update, delete and truncate raise. See N-A1 and N-A2. |
| F3 structural S5 | FIXED | Same as S5. |
| F4 minutes_spent | FIXED (per commit 2b4aa6c) | Minutes counted since the previous review, with a cap. `review.started_at` added (`0012:390`). |
| N1 cookie prefixes / login CSRF | NOT ADDRESSED in this PR (no fix commit) | Still a note. |
| N2 Origin / Sec-Fetch-Site | NOT ADDRESSED | Still a note. |
| N3 422 echoes input | FIXED (2aa26d7) | Invalid input re-renders the login page. |
| N4 persistent session cookie | NOT ADDRESSED | Still a note. |
| N5 session purge | NOT ADDRESSED | Still a note. |
| N6 htmx history cache | FIXED (c6cddd2) | |
| N7 ENV default | FIXED (3df79f9) | A remote DB requires ENV to be set. |
| N8 500 bypasses headers | NOT ADDRESSED | Still a note. |
| N9 CLI non-TTY password | NOT ADDRESSED | Documentation only. |
| N10 access logs | NOT ADDRESSED | Privacy-notice item. |
| N11 temp passwords never expire | FIXED | `0012:400-432`: 72 h expiry set by trigger. `repo/users.py:43`: an expired temporary password counts as a failed login. |
| N12 cross-org email enumeration | NOT ADDRESSED | Owner-only; still a note. |
| N13 password-change limiter key | FIXED (64ecf5f) | Separate keys. |
| N14 timer cookies | FIXED per 2b4aa6c (not re-read) | |
| N15 LIKE wildcards | FIXED (64ecf5f) | |
| N16 reject/edit not gated in DB | FIXED | `0012:152-180`: every human review needs an agronomist of the org or a human superadmin who is a member. |

## New findings

### BLOCKER

**NB1. An org owner can take over a superadmin account and approve as `superadmin_approved`**
- Evidence: `app/cloverproof_app/repo/admin_users.py:227-238` (`reset_password`) only refuses targets with `owner`/`agronomist` membership (`CLI_ONLY_ROLES`, `:26`) or a membership in another org. It never checks `app_user.platform_role`. The same gap is in `set_disabled` (`:242`). The route is `account.py:348-367`. In the DB, cp_app holds `UPDATE (password_hash, password_change_required, …)` on every `app_user` row (`0011_least_privilege_roles.sql:45-46`), so the database does not stop it either.
- Exploit: a superadmin is a member of exactly one org with only the `staff` or `farmer` role. Membership in the org is required to approve (`0012:155`), so this is the expected setup. That org's owner opens the member page and clicks Reset password, and the temporary password is shown on screen. The owner signs in as the superadmin, sets a new password, and approves any plan in the org as `superadmin_approved`: `plan_web.py:82-84` allows it and the DB trigger accepts it, because the reviewer really is a human superadmin.
- Impact: this breaks rule 8 and the criterion "owner/staff cannot approve". A farmer-facing number gets approved by someone who is neither an agronomist nor the superadmin. The reset is audited (`admin_event` `password_reset` with the owner as actor), but nothing prevents it. This is the F2 takeover path, closed for agronomists but reopened for the new approver class added in 05c21b0. It also lets an owner disable a superadmin.
- Fix:
  1. App: in `reset_password` and `set_disabled`, refuse when the target's `platform_role is not null`, with a CLI-only message. Add `platform_role` to `_MEMBER_SELECT`/`Member`.
  2. DB (new migration 0013, forward-only): add a BEFORE UPDATE trigger on `app_user` that raises `42501` when `session_user` is a cp_app login and `password_hash`, `password_change_required` or `disabled_at` changes on a row with `platform_role is not null`, or with an `agronomist`/`owner` membership. This puts the existing "CLI only" rule into the DB as well.
  3. Tests: an owner resetting or disabling a staff-only superadmin gets refused; the direct cp_app `update app_user set password_hash` on a superadmin raises `42501`.
- Status: not fixed (review only).

### SHOULD-FIX

**NS1. On Railway the default `TRUSTED_PROXY_HEADER=""` makes the per-IP limit global**
- Evidence: `config.py:78` (default empty), `web.py:88-90` (`request.client.host`). Nothing in `config.py:109-118` requires the header in staging/production.
- Exploit: behind Railway's edge, the TCP peer is the proxy, so every user shares one IP key. 30 failed logins from anyone within the IP window (`login_ip_max_failures`, `config.py:73`) return 429 to every user, including the agronomist with the right password, until the window ends. If the header is set instead, Railway's behaviour is disputed. Staff say the edge overwrites `X-Real-IP`, but March 2026 forum reports show Fastly or edge IPs in `X-Real-IP` and requests over `*.railway.internal` skip the edge entirely. The value must be checked on staging, as S1(b) already asked.
- Fix: in staging/production, refuse to start unless `TRUSTED_PROXY_HEADER` is set (or an explicit `TRUSTED_PROXY_HEADER=none` is given). Record the header verified on staging in the runbook, and add a startup log line with the chosen mode.

**NS2. The global failed-login budget lets anyone stop all logins**
- Evidence: `ratelimit.py:151-152`. The global window is checked before the password is verified, and every login gets 503 while it is full. Default 30 per minute (`config.py:83`).
- Exploit: about 30 failed POSTs per minute, spread over a few IPs (or one IP, given NS1), keep `/login` at 503 for everyone for as long as they continue. Existing sessions still work (12 h absolute).
- Impact: availability only. For 4 internal users during the Feb–Apr pilot, an attacker can stop the agronomist signing in.
- Fix: when the budget is exceeded, make each attempt wait (queue on the argon2 semaphore, which S2 already bounds) instead of refusing it. Or exempt `(email, ip)` pairs that succeeded within the last N days. Also log an alert line when the budget trips. If the 503 stays as it is, record the trade-off in the ADR.

**NS3. ADR 0008 §5.4/§5.3/§7.1 gaps in the superadmin and actor-kind design**
- `0012:33-38`: `actor_kind` has `default 'human'` and is not immutable. cp_admin can switch service to human and back; the switch is audited (`0012:560-563`) but not refused. §7.1 asks for no default and an immutability trigger.
- §5.4: a superadmin approval writes no `audit_event` row with a reason in the same transaction. The immutable `review` row (reviewer_id, review_kind) is the only record, and `reason` is optional on approve.
- §5.3/§5.4: no MFA, yet superadmin approval is live. CLAUDE.md says MFA is required by S5. Until then, a stolen superadmin password can approve in every org where that account is a member.
- §7.3: no trigger stops a service account from holding an `agronomist` membership. It cannot sign in (B1), so the impact today is low.
- Fix: in 0013, add an immutability trigger on `actor_kind` (after insert) and require a non-empty reason for `superadmin_approved`. Gate operations: do not grant `platform_role` in production until MFA (S5) is in.

### NOTE

- **N-A1.** `admin_event.actor_user_id` comes from `app.user_id`, which any DB login can set (`0012:476-490`). It is asserted by the app, not authenticated. CLI changes record only `actor_db_role = cp_admin_login`, a shared login, so they do not name the operator. Consider one cp_admin login per operator.
- **N-A2.** `set_actor` (`repo/users.py:49-51`) uses `set_config('app.user_id', %s, true)` with a bind parameter, inside the pool transaction (`db/pool.py`; psycopg pool connections are non-autocommit). The value is transaction-local, so it does not leak across the pool. ADR §3.3 (reset callback) and §3.5 are not implemented yet. That belongs to the RLS ADR, not this PR.
- **N-A3.** `app_user_temp_password_expiry` (`0012:414-432`) restarts the 72 h clock on any `password_hash` change while the flag is set. That includes the argon2 rehash on a successful temporary-password login (`web.py`, after `can_sign_in`). Low impact: the user still has to change the password.
- **N-A4.** The migration runner keys migrations by file name only, with no checksum (`app/cloverproof_app/db/migrate.py:5`). Commits 27c00f6 and 05c21b0 edited 0012 after b76c186. That is fine if 0012 was never applied to a shared DB, but the runner cannot detect it. Consider storing a sha256 per migration. `git diff origin/main...HEAD -- db/migrations` shows only added files (0010, 0011, 0012), so 0001–0009 are untouched.
- **N-A5.** Trigger order relies on name sorting (`review_check_kind` < `review_check_no_child` < `review_check_reviewer`). It is correct today. A future BEFORE INSERT trigger on `review` whose name sorts before `review_check_kind` would see `review_kind` as NULL. The tests cover this indirectly.
- **N-A6.** Rule 12 / ADR §7.7 (a non-human context reads no identifiable data) is not enforced in the DB. It waits for RLS (ADR 0008). Today service accounts cannot sign in, so nothing exposes it.
- **N-A7.** §5.4 asks that the proof PDF show the review kind. The PDF is not built yet, so this is not checked.

### Checked, no issue
- `review_kind` trigger (`0012:89-137`). An app-supplied value is only compared with the derived one; a mismatch raises `42501`. A NULL value is filled in from the derived kind. A human with neither the agronomist role nor superadmin gets `agronomist_approved` and is then refused by `review_check_reviewer` (`0012:174-176`). A service account always gets `ai_reviewed`, and a service account can never be superadmin (`0012:52-53`). A disabled superadmin is refused (`is_human_superadmin` checks `disabled_at`). `review` is insert-only (0007).
- `ai_reviewed` is excluded from: the proof trigger (`0012:214-228`), `recommendation_diff` (`:233-282`), the final and approval indexes (`:327-332`), the edit lock (`:362-383`) and plan status (`repo/plans.py:282-293`).
- `platform_role`: column on `app_user`, CHECK `superadmin` only and human only. Only cp_admin can write it (cp_app column grants exclude it, `0011:43-46`). Changes are audited (`0012:564-566`). It is read live from the DB on each request (`repo/sessions.py:45`), so revoking it takes effect at once.
- 0011 grants: cp_app has no INSERT/UPDATE/DELETE on membership or organisation. The SECURITY DEFINER functions pin `search_path = ''`, check that the actor is an enabled owner, accept only staff/farmer, and have execute revoked from PUBLIC.
- `admin_event`: cp_app has SELECT only, no INSERT grant to anyone except the owner, the trigger functions are SECURITY DEFINER with `search_path = ''` and PUBLIC execute revoked, and UPDATE/DELETE/TRUNCATE raise.

## Test evidence
- `make db-test` on a throwaway local container `postgis/postgis:18-3.7` (amd64 emulation, port 55499; never Railway). Result: **264 passed, 0 skipped, 0 failed** (43.6 s), including `test_superadmin.py` (25), `test_review_integrity.py` (15), `test_actor_kind.py`, `test_admin_event.py` and `test_grants.py`. The container was stopped and removed.
- `uv run pytest -q` without a DB: 318 passed, 261 skipped (DB tests opt-in).
- No test covers an owner resetting or disabling a superadmin (NB1).

## Not verified
- Live Railway header behaviour (NS1). Needs a staging probe.
- S6, F4 and N14 code, line by line (accepted on commit, plus tests passing).
- MFA: not implemented. RLS: not in this PR.
- Whether 0012 was ever applied to a shared DB before the later edits (N-A4).

Sources: [Railway: Edge Proxy X-Forwarded-For and X-Real-Ip can't be trusted](https://station.railway.com/questions/edge-proxy-x-forwarded-for-and-x-real-ip-c5a50049), [Railway: Which client-address headers does the edge set](https://station.railway.com/questions/which-client-address-headers-does-the-ra-fb9e36d7), [Railway: Fastly edge stopped delivering real client IP](https://station.railway.com/questions/fastly-wasm-edge-stopped-delivering-real-043fbc50)
