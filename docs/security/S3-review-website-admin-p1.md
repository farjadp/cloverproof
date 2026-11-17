# S3 security review — website admin P1 (ADR 0012–0014, PRs #55, #60, #62, #63, #64)

Owner: `ciso` (via `security-engineer` ×2). Reviewed: `main` at b508e2a, read-only. Tests ran only on scratch copies against a throwaway local PostGIS. No Railway, no login attempts on the live site. Date: 2026-11-17.
Detail: [auth part](S3-review-website-admin-p1-auth.md) (ADR 0012, #60, #62) and [data part](S3-review-website-admin-p1-data.md) (ADR 0013/0014, #55, #63, #64).

## Verdicts
| Item | Verdict |
|---|---|
| ADR 0012 admin auth | **PASS with findings.** Implemented as written except N3 (no session rotation on role change). |
| ADR 0013 integration secrets | **PASS with findings.** Crypto is sound: AES-256-GCM envelope, fresh IV, AAD bound to row and KEK id, write-only, server-only decrypt, no SSRF. |
| ADR 0014 system log + retention | **PASS with findings.** Append-only is enforced in Postgres; 60-day purge via a pinned SECURITY DEFINER function; CSV-injection guard; step-up on export. |
| Merged P1 code | **0 BLOCKER, 6 SHOULD-FIX, 12 NOTE.** |

Tests: website 63/63 (with DB), `make db-test` 604 passed, `npm audit --omit=dev` 0 vulnerabilities. CISO spot-checked A-S1 (`service.ts:313-318,339-356`) and D-S1 (`keys.ts:213-229` re-seals `website_secret` only; TOTP secrets are under the same KEK at `service.ts:377-396`): both confirmed.

## SHOULD-FIX (ranked)
| # | Finding | Where (b508e2a) | Fix | Before |
|---|---|---|---|---|
| A-S1 | Anyone who knows an admin's email can keep them locked out. Wrong passwords hard-lock the account, doubling to 24 h, and the correct password is refused during the lock. One request a day keeps the admin out. | `website/src/lib/admin/service.ts:313-318`, `:339-356` | Throttle wrong passwords per email only (that limit exists); keep account lock + revoke-all for second-factor failures only; add a test. | **first admin** |
| A-S2 | The per-IP limit trusts `X-Real-IP`, unverified on Railway. Either everyone shares one bucket, or the header is spoofable (bypassing the limit and forging log IPs). | `website/src/lib/admin/request-meta.ts:38-43`, `service.ts:302-303` | Trusted header name from an env var, empty by default; per-IP limit off when empty; spoofed-header test; probe on staging. | **first admin** (env empty is acceptable) |
| D-S2 | KEK ids default to `k1`/`previous` and are never compared. A forgotten new id makes rewrap re-seal 0 rows; deleting the old KEK then loses every key. | `website/src/lib/admin/server.ts:34,38`; `website/scripts/secrets-rewrap.mts:12,14` | Require `*_KEK_ID`, require the two to differ, and assert after rewrap that no row is still under the old id; runbook order: redeploy, then rewrap. | first admin (require the id); first rotation (assert) |
| D-S1 | KEK rotation skips the encrypted TOTP secrets. Following the runbook (delete the old KEK) breaks MFA for every admin. | `website/src/lib/admin/keys.ts:213-229`; `docs/runbook-website-admin.md:52` | Re-seal `website_user.mfa_secret_enc` in the same transaction; rotation test covering MFA. | **first KEK rotation** (runbook marked "do not rotate" until fixed) |
| A-S3 | Unauthenticated login floods tie up the admin DB pool (3 connections, no timeout, an argon2 hash per attempt even when rate-limited, a log row per attempt). | `website/src/lib/admin/server.ts:23`, `login/actions.ts:16-21`, `service.ts:303-305` | `connectionTimeoutMillis`; skip the dummy hash when rate-limited; one rate-limit log row per window. | S4 |
| D-S3 | ADR 0014's own gate isn't met: ADRs 0012–0014 are still Proposed, and the privacy notice lacks the admin-security-log sentence (IP prefixes of sign-in attempts). | `docs/adr/0013…:3`, `0014…:3,33` | Farjad Iranmehr accepts the ADRs; `coo` ships the notice sentence. | **first admin** |

## NOTES (no gate)
- **A-N1:** logout doesn't clear the cookie (`server.ts:72-74`); it is revoked server-side.
- **A-N2:** demote → reset → re-promote bypasses "admins can't reset admins"; every step is logged and needs step-up.
- **A-N3:** no session rotation on role change (`users.ts:99`). Revoke the target's sessions, or amend ADR 0012.
- **A-N4:** the 24 DB-backed admin tests don't run in CI. Add a PostGIS service job.
- **A-N5:** the live site serves a pre-#60 build. `/admin` → `/en/admin/login` 404 is a stale deploy, not locale interference. Re-check headers on the first deploy.
- **A-N6:** pre-MFA sessions last up to 12 h; there's a first-admin check-then-insert race (operator only); recovery codes have a slight modulo bias.
- **D-N1:** the admin role can insert log rows with any `occurred_at` (a 2099 row survives purge). Column-level INSERT grant without `occurred_at`.
- **D-N2:** ADR 0013 text says the AAD includes the row id; the code uses provider + version (equivalent). Fix the ADR text.
- **D-N3:** a misconfigured KEK fails closed but silently. Log the variable name (never its value).
- **D-N4:** the fal test endpoint may answer without a valid key (P2).
- **D-N5:** the "key never in HTML/RSC/network/build" test is missing.
- **D-N6:** distributed failed logins grow the log until purge.
- **CISO note:** `app/admin/mfa/page.tsx:38` injects the QR SVG via `dangerouslySetInnerHTML`. It is generated server-side from our own otpauth URI (no user HTML), so low risk. Keep it that way, and prefer `<img src="data:image/svg+xml…">`.

## Gate: CONDITIONAL — not "ciso go" yet
**"ciso go" for creating the first admin and enabling `/admin` (setting `ADMIN_DATABASE_URL`, `WEBSITE_SECRETS_KEK`, applying 0024/0025)** is given when all of these hold:
1. A-S1 fixed and tested (cp-website PR).
2. A-S2: trusted-header env var shipped, and left empty in production until the staging probe shows the right header.
3. D-S2 (part): `WEBSITE_SECRETS_KEK_ID` required, no default.
4. D-S3: Farjad Iranmehr accepts ADRs 0012–0014, and the privacy-notice sentence on admin security logs is live.
5. The first deploy is checked for CSP/headers on `/admin/login` (A-N5).

D-S1 and the D-S2 post-rewrap assertion must land before the **first KEK rotation**. Until then the runbook says "do not rotate". A-S3 and the notes go to the S4 backlog.

Code fixes: `cp-website`, each as its own PR. CISO re-reviews the fix PRs, then gives "ciso go" in writing to the CPO.
