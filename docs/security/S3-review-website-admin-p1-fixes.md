# S3 re-review: website admin P1 fix PRs #67 to #70

- Reviewer: `security-engineer` for `ciso` · 2026-11-17 · static review of the stack top `693b1ba` (read-only checkout, untouched). Per-PR diffs use base `6d130d3` (merge-base with origin/main): #67 `178151f`, #68 `4308934`, #69 `6061e17`, #70 `693b1ba`.
- Original findings: [S3-review-website-admin-p1.md](S3-review-website-admin-p1.md) (A-S1, A-S2, D-S1, D-S2).
- Line numbers below refer to `693b1ba`.

## Verdicts
| PR | Finding | Verdict |
|---|---|---|
| #67 `178151f` | A-S1 password lockout DoS | **PASS WITH NOTES.** The hard lock is gone. A cheaper DoS remains, bounded to the 15-minute window (N1). |
| #68 `4308934` | A-S2 spoofable client IP | **PASS WITH NOTES.** Safe default. The X-Forwarded-For option is weaker than needed, and a bad env value is silently ignored (N2, N3). |
| #69 `6061e17` | D-S2 KEK ids | **PASS.** |
| #70 `693b1ba` | D-S1 TOTP secrets skipped by rotation | **PASS WITH NOTES.** Two test gaps and one runbook detail (N4, N5). |

No BLOCKER and no new SHOULD-FIX. No regressions found in the diff.

## #67 A-S1: wrong passwords throttle per e-mail only
Checked:
- `website/src/lib/admin/service.ts:316`: a wrong password returns `bad_credentials` before the lock check. It no longer calls `recordFailure`, so `failed_logins` and `locked_until` are untouched and sessions are not revoked.
- **Correct password during a storm.** The per-e-mail counter is bumped before the password is checked (`:300-306`). In a window that already holds 5 attempts, the right password is refused (`rate_limited`). It works again in the next fixed 15-minute window (`:169-178`). On success the attempt is un-bumped (`:320-321`). This matches the brief.
- **Online guessing bound.** Unchanged at 5 per 15 minutes per e-mail (`:29-30`). That is 480 a day per address, about 960 in a burst across a window boundary. Argon2, the password policy and mandatory TOTP still apply.
- **Second-factor lock path.** `recordFailure` (`:339-357`) is now called only from `completeMfa`, `redeemRecoveryCode` and `stepUp`. Lock, doubling to 24 h, revoke-all and the `account.lock` log are unchanged. Revoke-all is now unconditional, which is equivalent because every remaining caller passed `secondFactor = true`. `refuseIfLocked` is unchanged.
- **Enumeration.** All paths return the same `LOGIN_FAILED`. Unknown and unset accounts burn a password hash; known accounts verify one, the same cost as before. The `locked` and `disabled` outcomes are revealed only after a correct password, which is better than before, when a locked account could be told apart only by its log reason. The response is the same either way.
- **Tests.** `admin-service.test.ts` checks: no lock and `failed_logins = 0` after 5 wrong passwords; refusal for the rest of the window; success in the next window. A new 3-day test checks no lock, no doubling, no revoked sessions, no `account.lock`, and that the right password works when the window ends.

**N1 (NOTE, residual DoS).** The test shows the lock no longer grows. It does not show the DoS is gone. An attacker who sends 5 wrong passwords at the start of every 15-minute window (about 480 requests a day from anywhere) keeps the admin out continuously. The per-IP limit is off by default after #68, so nothing slows such an attacker. Before the fix, the same denial cost about 1 request a day, so this is a large improvement but not a full fix. This is what the CISO's chosen fix implies. Options for S4:
- a "known device" cookie, set after a successful MFA login, that exempts that browser from the per-e-mail throttle (OWASP device-cookie pattern);
- an operator unlock (`admin:reset` already exists as a last resort).

Monitoring: a rising count of `login`/`rate_limited` rows in `website_log` for one actor is the signal.

## #68 A-S2: client IP only from a trusted header
Checked:
- `website/src/lib/admin/request-meta.ts:42-49`. The header name comes from env `TRUSTED_PROXY_HEADER`, is trimmed and lower-cased, and must match `^[a-z0-9-]{1,64}$`. When the env is empty or invalid, or the header is absent, the result is `null`. Then there is no `ipPrefix`, no per-IP bucket (`service.ts:301-302`) and no IP in the log.
- **Value validation.** `isIP()` must pass. A list in a single-value header gives `null`. Only a prefix is stored (`ipPrefix`, unchanged).
- **X-Forwarded-For.** Only the last element is used. `Headers.get` joins repeated XFF headers with `, `, so the last element is still the one the proxy appended. If the proxy passes the client's XFF through without appending, the last element is attacker-controlled. The runbook probe (§5, spoofed `X-Forwarded-For: 6.6.6.6`) is designed to catch this.
- **Single source.** `requestMeta()` (`server.ts:46-50`) is the only consumer, used by the login, MFA, setup and logout actions and by `requireRole`. Rate limiting and logging therefore use the same value. No other code reads `x-forwarded-for` or `x-real-ip`.
- **Env set but header absent:** `null`, so the per-IP limit is silently off (see N3).
- **Tests.** `admin-policy.test.ts` covers an unset env, invalid names (CRLF, comma, length), header-name case, a list in X-Real-IP, a non-IP value, a non-named header ignored, and spoofed first XFF entry ignored. A DB test in `admin-service.test.ts` checks that with no prefix, 25 failures don't block others and no IP is logged.

**N2 (NOTE).** Prefer X-Real-IP and drop X-Forwarded-For support. Railway's public guidance names X-Real-IP as the client IP set by the edge. Its staff and users disagree on whether XFF is stripped, appended or carries CDN (Fastly) addresses. A CDN address as the last XFF entry would put all users in one bucket. The probe catches this only if the operator reads the prefix carefully. The webapp's equivalent (`app/cloverproof_app/ratelimit.py:14`) never uses XFF. Matching that removes the ambiguity. Sources: [Railway Station: which header for real client IP](https://station.railway.com/questions/which-header-should-i-rely-on-for-real-c-d78a6f96), [XFF edge overwrite vs append](https://station.railway.com/questions/x-forwarded-for-behavior-edge-overwrit-e3663b39), [XFF contains Fastly IPs](https://station.railway.com/questions/x-forwarded-for-contains-fastly-cdn-i-ps-f3039f98). These are forum threads, not the official spec, so not verified against the docs.

**N3 (NOTE).** A mistyped `TRUSTED_PROXY_HEADER` (for example `X_Real_IP`) silently disables the per-IP limit. The webapp fails fast on the same variable (`app/cloverproof_app/config.py:139`). Validate the name once at config load: fail, or log one warning naming the variable but not the value.

## #69 D-S2: required, distinct KEK ids; rewrap post-check
Checked:
- `website/src/lib/admin/kek-env.ts:12-37`:
  - `WEBSITE_SECRETS_KEK_ID` is required, with no default.
  - The format `^[A-Za-z0-9_.-]{1,40}$` matches the DB check `db/migrations/0025_website_secret.sql:18`.
  - If either `_PREVIOUS` variable is set, both are required (`:25` then `:27-28`).
  - The two ids must differ (`:30`) and the two keys must differ (`:33`).
  - Keys must be exactly 32 bytes after base64 (`crypto.ts:24-29`).
  - Errors name the variable, never the value.
- `server.ts:31-39`, `admin-create.mts` and `secrets-rewrap.mts` all use `kekRingFromEnv`. A config error disables the admin ("Admin not configured"), which fails closed.
- `secrets-rewrap.mts:14-17` refuses to run with one KEK. It uses one `begin`/`commit` and rolls back on any throw (`:20-32`).
- `keys.ts` `assertAllUnderCurrent`:
  - no active `website_secret` row may have `kek_id` ≠ current;
  - every active row must open with `[current]` alone.

  Otherwise it throws `RotationIncomplete`, and the caller rolls back. Rows are selected `for update`.
- **Tests.** `admin-kek-env.test.ts` checks the required id, ring of one, previous needs its own id, and that ids and keys differ. `admin-keys.test.ts` checks the rollback when a key is not openable by the new KEK, and that nothing stays under the old id.

Hardening only:
- `Buffer.from(…, "base64")` accepts some non-canonical input. Length is checked, so this is not a defect.
- The `adminConfig()` catch at `server.ts:36` swallows the reason. A one-line log naming the failing variable (not the value) would help the operator.

## #70 D-S1: rotation re-seals TOTP secrets
Checked:
- `rotation.ts:9-14` `rotateMasterKey` runs `rewrapKeys` and then `rewrapMfaSecrets` on the same client, inside the script's single transaction, then writes one log row.
- `service.ts:389-413` `rewrapMfaSecrets`:
  - It selects **every** `website_user` row with `mfa_secret_enc is not null … for update`. There is no filter on `mfa_enabled_at`, `deleted_at` or `disabled_at`, so users mid-enrolment, deleted users and disabled users are all covered.
  - It re-seals with AAD `mfaAad(row.id)`, the same AAD used by `pendingMfaSecret` (`:377`) and `checkCode` (`:396` in `open`).
  - The post-check re-selects all such rows and requires that the sealed KEK id equals current and that the secret opens with `[current]`. It throws a generic error with no value, and the script rolls back.
- **How the KEK is known.** There is no `kek_id` column on `website_user`. The envelope is JSON carrying `kek` (`envelope.ts:37-52`), and the DEK wrap is authenticated with `dek|${kek.id}|${aad}` (`:35`). Relabelling the id therefore fails at `open`. `sealedKekId` reads the id without trial decryption. The post-check then trial-opens with the current KEK only.
- The `server-only` import in `rotation.ts` is satisfied: `secrets:rewrap` and `npm test` both run with `--conditions=react-server` (`website/package.json:11,14`).
- **Log whitelist.** `log-detail.ts` adds `mfa_count`, an integer count. This is harmless.
- **Other KEK users.** `grep seal(` finds only `keys.ts:93,233` and `service.ts:377,397`. Recovery codes are HMACs, not KEK-sealed. Nothing else needs re-sealing.
- **Tests.** `admin-rotation.test.ts` checks:
  - one enrolled user plus one mid-enrolment user plus an API key are re-sealed together (`{keys:1, mfa:2}`), and a second run is idempotent;
  - after the old KEK is removed, step-up TOTP and API-key decrypt both work;
  - the log detail is `{count, mfa_count, via}`;
  - a new key under the old id is refused (rollback).

**N4 (NOTE, test gap).** No test covers a deleted or disabled user with a sealed secret. The code covers them (no filter at `service.ts:392`), but a future `deleted_at is null` filter would regress silently. Add one row of each to the first rotation test. A mid-enrolment user is not tested completing enrolment with the new KEK alone. The id is asserted, and `open` is the same path, so the risk is low.

**N5 (NOTE, runbook).** Rotation step 2 (`docs/runbook-website-admin.md:66`) should say to wait until the **old deployment has fully stopped** before running `secrets:rewrap`. Until then, an old replica still seals new TOTP enrolments and API keys under the old KEK. The post-check catches anything sealed before commit, but not a write that lands after commit, from a replica that is still draining. Deleting the old KEK would then lose that value.

## Tests run
- Scratch copy of `693b1ba` (`rsync` without `.git`/`node_modules`; `$F` not modified, `git status` clean).
- `cd website && npm ci --ignore-scripts && npm test`: **77 tests, 47 pass, 30 skipped** (DB tests opt-in), 0 fail.
- Throwaway `postgis/postgis:17-3.5` on `127.0.0.1:55512`. Root `db/migrations` 0001–0025 were applied with `website/scripts/migrate.mjs`, pointed at the root directory in a temporary copy. `WEBSITE_TEST_DATABASE_URL` set: **77/77 pass, 0 skipped**, including the new A-S1, A-S2, D-S2 and D-S1 tests. The container was removed afterwards. No Railway and no live site were touched.

## Not verified
- Tests at each intermediate commit (#67, #68, #69 alone). Only the stack top was run.
- `make db-test` (Python DB suite). It is not affected by the diff, which only touches `website/` and docs.
- `npm audit`. There were no dependency changes in the diff.
- Railway header behaviour (N2). This needs the staging probe in runbook §5.
- A real end-to-end `npm run secrets:rewrap` run in a shell. The library path is covered by the DB tests, but the CLI wrapper was not run.

## PR #71 (D-S3 privacy-page section), reviewed by CISO: PASS
The "Security log of our staff area" section matches ADR 0012/0014 and the code:
- Fields: time, action, outcome, `ip_prefix` (/24 or /48) and `ua_family`; no passwords, codes or form input.
- The log is deleted after 60 days (`0024_website_admin_p1.sql:192`).
- The login counters are HMAC-keyed ("scrambled"). They are purged once their window is a day old, by a job that runs about daily (`:198`), so "within two days" is accurate.
- No public-page code writes `website_log`.
- US/Railway storage is disclosed, and the "Who sees it" and "How long we keep it" sections are updated.

## Gate status for "ciso go" (first admin, `/admin` enabled)
| # | Condition | Status |
|---|---|---|
| 1 | A-S1 fixed and tested | **met** by #67, on merge. Residual N1: an attacker sending 5 wrong passwords per 15 min (≈480 requests/day) can still keep the admin out. This is accepted as an availability risk only, with no data exposure; the S4 fix is a known-device exemption after MFA. |
| 2 | A-S2 trusted-header env shipped; empty in production until the staging probe | **met** by #68, on merge. Keep `TRUSTED_PROXY_HEADER` empty in production; prefer X-Real-IP only (N2); S4: fail fast on unknown header names (N3). |
| 3 | D-S2 `WEBSITE_SECRETS_KEK_ID` required | **met** by #69, on merge |
| 4 | D-S3 privacy notice sentence live **and** ADRs 0012–0014 accepted by Farjad Iranmehr | **open**: #71 passes but must be merged and deployed; all three ADRs are still `Proposed` |
| 5 | Headers/CSP checked on the first deploy of `/admin/login` | **open**, at deploy time (CISO checks with a read-only GET) |
| — | D-S1 before the first KEK rotation | **met** by #70, on merge. Runbook to add N5 (wait for old replicas to stop before rewrap). |

**ciso go** = merge #67–#71 in order, deploy, Farjad Iranmehr marks ADRs 0012–0014 Accepted, then the CISO header check (5) passes. No first admin and no `ADMIN_DATABASE_URL`/`WEBSITE_SECRETS_KEK` in production before that.

## Gate 4 and 5 check (2026-11-17, live commit ddc76bc, read-only GETs, no login)
- **Gate 4:** ADRs 0012–0014 are `Accepted` on `main` (#73), and `/en/privacy` shows "Security log of our staff area". **Met.**
- **Gate 5:** `/admin/login` returns 200 "Admin not configured". **Met.** Headers:
  - CSP: `default-src 'self'`, `script-src` with a per-request nonce (it differs on each request) plus `'strict-dynamic'`, `object-src 'none'`, `base-uri 'none'`, `form-action 'self'` and `frame-ancestors 'none'`.
  - HSTS: `max-age=31536000; includeSubDomains`.
  - `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` and `Cache-Control: no-store`.
  - The pre-session cookie is `__Host-cp_admin_pre` with Secure, HttpOnly and SameSite=Strict. There is no `x-powered-by` header.
- `/admin`, `/admin/keys`, `/admin/users` and `/admin/log/export` all 307 to `/admin/login`. `/admin/setup` without a link only says "not configured".

## ciso go: first admin (2026-11-17)
**GO** to apply migrations 0024/0025, set the admin env vars and create the first admin, under these conditions:
1. Migrations 0024/0025 are applied by the migrator credential, never one the running website can read. `ADMIN_DATABASE_URL` uses the `cp_website_admin` login, never the superuser or `cp_migrator`. The public site keeps `cp_website`.
2. `WEBSITE_SECRETS_KEK` is 32 random bytes (e.g. `openssl rand -base64 32`), set as a sealed Railway variable on the website service only. `WEBSITE_SECRETS_KEK_ID` is set explicitly. An offline copy of the KEK is kept in Farjad Iranmehr's password manager, because losing it loses every stored key and every admin's MFA.
3. `TRUSTED_PROXY_HEADER` stays empty until the staging probe.
4. The first admin is created by the CLI only. The one-time setup link is used at once (it lasts 72 h at most), and MFA is enrolled in the same sitting. Recovery codes go into the password manager.
5. After it is enabled, the CISO repeats this header check and confirms `/admin/setup` no longer accepts the used link. Any failure there → disable by unsetting `ADMIN_DATABASE_URL`.
Open S4 items, not blocking: lockout residual N1 (known-device exemption), X-Real-IP only and fail-fast on unknown header (N2/N3), the rotation test for deleted/disabled users (N4), the runbook replica note (N5), A-S3 pool limits, and the earlier notes.
