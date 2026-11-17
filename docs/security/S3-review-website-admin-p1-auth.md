# S3 review — website admin P1: auth core (PR #60) + users (PR #62) — part file

- Reviewer: `security-engineer` for `ciso` · 2026-11-17 · static review of origin/main `b508e2a` (read-only checkout), plus the test suite run on a local disposable PostGIS container.
- Scope: ADR 0012; PR #60 (merge `4c04bac`) and PR #62 (merge `a93384c`): `website/src/lib/admin/{service,server,password,crypto,totp,permissions,request-meta,users}.ts`, `website/src/app/admin/{login,mfa,setup,users}/*`, `website/src/app/admin/{actions,step-up}.ts`, `website/src/proxy.ts`, `website/scripts/admin-{create,reset}.mts`, `db/migrations/0024_website_admin_p1.sql` (auth parts). Keys (PR #64) and the log (PR #63) were only checked for a guard on each entry point.
- Paths below are relative to the repo root, line numbers at `b508e2a`.

## Verdict

**ADR 0012: PASS with findings. Nothing is a BLOCKER.** The design is implemented as written, with two deviations (S2 and N3). Two SHOULD-FIX items are availability problems, not confidentiality problems: an attacker who knows only an admin's e-mail address can keep that account locked out, and the per-IP limit depends on an unverified Railway header. Both should be fixed or accepted by Farjad Iranmehr before the P1 go (plan §8).

Counts: BLOCKER 0 · SHOULD-FIX 3 · NOTE 6.

## Findings

### SHOULD-FIX

**S1. Anyone who knows an admin's e-mail can lock that admin out, and the lock escalates to 24 h and never decays** (reproduced locally)
- Evidence: `website/src/lib/admin/service.ts:313-318`. A wrong password calls `recordFailure` (`:339-356`). The lock starts at the 5th failure and doubles to 24 h (`:343-345`). `failed_logins` is reset only after a second factor succeeds (`:453`, `:482`), on link redemption (`:158`) or by the CLI. A correct password during a lock is refused (`:318`).
- Exploit: send 5 wrong passwords for the address, then 1 more each time the lock expires. Each attempt can come from a different /24, so the per-IP limit does not help. The per-e-mail window allows 5 attempts per 15 min, and the attack needs only about 1 per lock period. PoC result against migration 0024 (scratch test): after the first 5, each further single request gave locks of 1800, 3600, 7200, 14400, 28800, 57600, 86400 and 86400 s. After about 13 requests, one request a day keeps the account locked. The victim's correct password is refused throughout.
- Impact: the only admin (Farjad Iranmehr, an address that is easy to guess) loses `/admin`. The only recovery is `npm run admin:reset` in the Railway shell, and the attacker can re-lock the account straight after. No confidentiality impact.
- Fix: the per-e-mail throttle (`bump`, `:301-306`) already caps password guessing, so password failures should not hard-lock the account. Split the counters:
  1. Drop `recordFailure` from the wrong-password branch (`:315`), or use a separate `failed_password` counter that only throttles and does not set `locked_until`.
  2. Keep `locked_until` and the revoke-all-sessions behaviour for second-factor failures (`completeMfa`, `redeemRecoveryCode`, `stepUp`), which need the correct password.
  3. Remove `isLocked` from the password step (`:318`), or check it only for locks caused by codes.
  4. Test: 50 wrong passwords from 50 prefixes, then the correct password and TOTP in a new window, must succeed.

**S2. The per-IP limit trusts `X-Real-IP` without verification. Depending on Railway's behaviour, it is either a global login lock or spoofable** (not verified on staging)
- Evidence: `website/src/lib/admin/request-meta.ts:38-43` takes `X-Real-IP` first, then the last `X-Forwarded-For` entry. `service.ts:302-303` refuses any login after 20 attempts per prefix per 15 min, and the count is taken before the password is checked. The code comment and `docs/runbook-website-admin.md:48` both say "verify on staging"; this has not been done. The same issue was raised for the web app in S2 (`docs/security/S2-review-pr7-final.md:62`, with Railway forum sources).
- Exploit, case (a): if the edge puts its own or a Fastly address in `X-Real-IP`, or the last XFF hop, many users share one prefix. 21 bad logins from anyone then make every sign-in through that edge prefix return `LOGIN_FAILED` until the 15-min window ends, including the correct password.
- Exploit, case (b): if a client-sent `X-Real-IP` passes through unchanged, the per-IP limit is bypassed with one random header per request. `ip_prefix` in `website_log` and `website_session` can then be forged, which weakens the audit trail.
- Impact: (a) a cheap admin login DoS; (b) loss of the per-IP limit (the per-e-mail limit still holds) and forged log attribution.
- Fix: use the client-IP header only after a staging check shows the edge overwrites it (send `X-Real-IP: 6.6.6.6` and `X-Forwarded-For: 6.6.6.6` and confirm neither appears as `6.6.6.0/24`). Put the header name in an env var, e.g. `ADMIN_TRUSTED_IP_HEADER`, empty by default; when it is empty, disable the per-IP limit rather than key it on the proxy. Add a unit test for the spoofed-header case. Under the S1 fix the per-e-mail throttle is the main control, so a disabled per-IP limit is acceptable for 5 or fewer users.

**S3. Unauthenticated requests can exhaust the 3-connection admin pool and force an argon2 hash on every attempt, including rate-limited ones**
- Evidence: `website/src/lib/admin/server.ts:23` sets `max: 3` with no `connectionTimeoutMillis`, so `pg` waits forever for a free connection. `website/src/app/admin/login/actions.ts:16-21` runs the whole login, including argon2 (19 MiB, `password.ts:4`), inside a pooled transaction. `service.ts:303-305` still calls `burnPasswordTime` when the request is rate-limited, and every failure writes a `website_log` row (`:290-292`).
- Exploit: flood `loginAction` with POSTs. The `pre` cookie and field come from one GET of `/admin/login`. Concurrency stays at 3 but the queue is unbounded: real admin requests wait behind it, Node memory grows, and the log fills up (bounded by the 60-day purge and the 4 KB `detail` limit). The public site's pool is separate and is not affected.
- Fix: (1) set `connectionTimeoutMillis: 5_000` on the admin pool and turn a timeout into a "try again" message; (2) skip `burnPasswordTime` on the rate-limited path, since the response there says nothing about whether the account exists; (3) write at most one `rate_limited` log row per key per window (only when `perEmail === MAX+1`); (4) optionally add a cheap in-memory per-instance limiter before the DB call.

### NOTE

**N1. Logout does not remove the `__Host-` cookie from the browser** (code-verified; not tested in a browser)
- `website/src/lib/admin/server.ts:72-74` calls `cookies().delete(SESSION_COOKIE)` with no options. In Next's `ResponseCookies.delete` (`next/dist/compiled/@edge-runtime/cookies/index.js:304`), that becomes `set({name, value:"", expires:0})` with no `Secure`. Browsers drop a `__Host-` Set-Cookie that has no `Secure`, so the stale cookie stays.
- The server-side session is already revoked, so there is no auth bypass. The only effect is that the optimistic proxy check passes after logout.
- Fix: `(await cookies()).set(SESSION_COOKIE, "", { httpOnly: true, secure: true, sameSite: "strict", path: "/", maxAge: 0 })`.

**N2. The "admins can't reset another admin's sign-in" rule can be bypassed by demoting first**
- `website/src/lib/admin/users.ts:87-101` lets any admin demote another admin while one other admin remains. After that, `resetPassword` (`:128`) and `resetMfa` (`:139`) no longer see an admin. The attacker re-promotes the target after taking over the account.
- Every step is logged and needs step-up, so this only weakens the attribution goal of L2. It does not escalate privilege, because the actor is already an admin.
- Fix: refuse both resets when the target's current role is admin or the target was an admin within the last 24 h (check `website_log` `user.role` rows), or require that demoting an admin is done through the CLI.

**N3. Role change does not rotate the target's session token (ADR 0012 deviation)**
- The ADR says "rotate token on login and privilege change". `users.ts:99` keeps the sessions on purpose. Demotion takes effect on the next request (`guardAction` re-reads the role), so the risk is low.
- Fix: either revoke the target's sessions on any role change (one line: `revokeAllSessions(db, id, now)`) or amend the ADR.

**N4. The 24 DB-backed admin tests run nowhere in CI**
- They are opt-in through `WEBSITE_TEST_DATABASE_URL` (`website/tests/admin-*.test.ts`). `.github/workflows/ci.yml` does not set it, so in CI every lockout, replay, CSRF-binding, session-expiry and last-admin test is skipped.
- Fix: add a CI job with a `postgis/postgis` service that runs the root migrations (with `scripts/migrate.mjs` pointed at `db/migrations`) and sets the env var.

**N5. The live site still serves a pre-PR #60 proxy, so the admin is not exposed**
- A read-only GET to `https://website-production-a1991e11.up.railway.app/admin` (and `/admin/login`, `/admin/setup`, `/admin/users`) returned `307 → /en/admin…`, and `/en/admin/login` returned 404, served from the prerender cache.
- At `b508e2a`, `website/src/proxy.ts:76` handles `/admin` before the locale redirect, so this 404 does not come from the merged code. The running build predates PR #60, or Railway deploys another ref.
- No security issue is hidden here: the admin is simply not live. After the next deploy, re-check that `/admin/login` returns 200 with the CSP, `no-store`, `X-Robots-Tag` and `__Host-cp_admin_pre` cookie set by `proxy.ts:59-70`, and that `/en/admin` stays 404.

**N6. Small items (no action needed for P1)**
- Pre-MFA sessions can live up to 12 h (`service.ts:203`), capped by the 30-min idle timeout. Consider a 10-min cap while `mfa_verified_at` is null.
- `createFirstAdmin` checks the admin count and then inserts without a lock (`service.ts:523-532`). Only an operator can race it.
- Recovery codes have a slight modulo bias (`service.ts:407`, 256 % 31). Entropy is still about 49 bits and the codes are HMAC-hashed. No action.

## Verified OK

- **Password hashing:** argon2id, m=19456 KiB, t=2, p=1 (`password.ts:4`, `algorithm: 2` = Argon2id in `@node-rs/argon2`). The library verifies the hash; rehash on login when parameters change (`service.ts:323-325`); a DB check requires `$argon2id$` (`0024:43`). Length 12–128.
- **No user enumeration:** one `LOGIN_FAILED` message for unknown user, wrong password, locked, disabled and rate-limited (`service.ts:280-318`). A dummy argon2 verify on the unknown-user path equalises timing. The existing test covers it.
- **Constant-time compares:** `safeEqual` uses `timingSafeEqual` with a length check (`crypto.ts:17-21`) for CSRF. TOTP comparison is constant-time and does not exit early (`totp.ts:64-70`). Session, link and recovery lookups go through a hash or HMAC index.
- **MFA:** the secret is 160 random bits (`totp.ts:41-43`), sealed with AES-256-GCM envelope encryption and AAD bound to the user id (`service.ts:98`, `:377`; `envelope.ts:11-16`). ±1 step window. Replay is blocked by a per-user-per-step claim row (`service.ts:385-392`), purged after 1 day (`0024:198`). The 10 recovery codes are HMAC-hashed and single-use (`:412-413`, `:473-476`). Code failures count per user, lock the account and end every session. Enrolment is forced: `requirePage` and `guardAction` both require `mfa_verified_at` (`server.ts:87`, `:101`), and only an enrolled user can get it.
- **Sessions:** 32-byte random token, only sha256 stored (`service.ts:193-210`). Cookie is `__Host-cp_admin`, HttpOnly, Secure, SameSite=Strict, Path=/ (`server.ts:62-70`). Idle 30 min and absolute 12 h are enforced server-side (`service.ts:231-235`). A new session is created on login and the old one revoked (`login/actions.ts:16-21`); the token is rotated after MFA and recovery (`service.ts:456`, `:484`). All sessions are revoked on password redemption, disable, MFA reset, delete and a lock caused by codes. A disabled or deleted user loses the session on the next request.
- **CSRF:** every state-changing server action checks an explicit token: `guardAction` (HMAC of the session token, rotates with it) for users, keys, step-up and log export, the MFA action checks it directly, and login and setup use a double-submit with the `__Host-` pre cookie. This works independently of Next's own Origin check and is backed by SameSite=Strict. Logout skips the token on purpose (it only ends the caller's own session).
- **Authorisation on every entry point:** all 7 `"use server"` files and the one admin route handler (`app/admin/log/export/route.ts:8`) check for themselves. `proxy.ts` only does the optimistic redirect. Role matrix: `permissions.ts`. Users, keys and log export need a step-up within 5 min (`permissions.ts:29-30`, `users/actions.ts:11`).
- **No web bootstrap:** the first admin is created only by the CLI (`scripts/admin-create.mts`; it refuses when an admin exists unless `--additional`). `/admin/setup` is reachable without a session but does nothing without a valid 256-bit, single-use, expiring token. The token travels in the URL fragment and is stripped from history (`SetupForm.tsx:12-18`).
- **No open redirect:** there is no `next=` parameter. All redirects go to fixed `/admin/*` paths. `stepUpAction` uses `path` only for `revalidatePath`.
- **Headers on /admin:** CSP with a per-request nonce, `strict-dynamic`, `object-src 'none'`, `base-uri 'none'`, `form-action 'self'`, `frame-ancestors 'none'`; also `no-store`, `X-Robots-Tag`, XFO DENY, `no-referrer`, `nosniff`, and HSTS in production (`proxy.ts:22-71`). The admin uses its own root layout and is not localised.
- **DB role:** the admin uses its own pool on `ADMIN_DATABASE_URL` (`cp_website_admin_login` in `cp_website_admin`). Grants cover the `website_*` tables only, with column-level `UPDATE` on `website_user`, no hard delete, an append-only log, and the last-admin guard in a trigger (`0024:145-218`). Least privilege for its purpose. Residual risk: the public site and the admin share one process, so RCE in the public site also reaches the admin credential. This was accepted with option A.
- **Personal data in logs:** login failures log a reason and the user id, never the e-mail or password. Logs store the IP prefix (/24 or /48) and browser family only, and `cleanDetail` scrubs `detail`. No `console.*` in the admin auth code.
- **Dependencies:** `npm audit --omit=dev` in `website/` found 0 vulnerabilities (scratch copy, lockfile unchanged).

## Tests

- `npm ci --ignore-scripts && npm test` in a scratch copy of `website/` (the read-only checkout was not touched): 63 tests, 39 pass, 24 skipped (DB tests are opt-in).
- With `WEBSITE_TEST_DATABASE_URL` pointing at a disposable local `postgis/postgis:17-3.5` container, migrated with root `db/migrations` 0001–0025: **63/63 pass.** The container was removed afterwards.
- S1 PoC: a scratch-only test (not in the repo) confirmed the escalating lock with the numbers given under S1.

## Not verified

- Railway's handling of `X-Real-IP` and `X-Forwarded-For` (S2). This needs staging; production was not touched.
- Browser behaviour for N1 (based on the `__Host-` prefix rules and Next's `delete` implementation; not run in a browser).
- The rendered CSP on a live admin build (N5: the admin is not deployed). No login attempts were made against the live site.
- Next 16's built-in server-action Origin check was not re-read in the docs, because the admin does not rely on it.
- Keys (PR #64) and log (PR #63) internals beyond their guards.
