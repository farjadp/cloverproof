# S3 review — website admin P1, data part (ADR 0013 / 0014, PRs #55, #63, #64)

- Reviewer: `security-engineer` (for `ciso`) · Date: 2026-11-17 · Commit reviewed: `b508e2a` (origin/main)
- Scope: migrations `0024_website_admin_p1.sql`, `0025_website_secret.sql`; `website/src/lib/admin/{envelope,crypto,keys,log,log-detail,background,server}.ts`; `website/src/app/admin/{keys,log}/**`; `website/src/instrumentation.ts`; `website/scripts/secrets-rewrap.mts`; tests `website/tests/admin-*.test.ts`, `app/tests/db/test_website_admin.py`.
- Out of scope (other part files): login/MFA/session/CSRF flows (PR #60), users (PR #62), `proxy.ts` headers/CSP.

## Verdicts

| ADR | Verdict |
|---|---|
| 0013 Website integration secrets | **PASS with findings.** Crypto design is sound (AES-256-GCM envelope, random 96-bit IVs, pinned 16-byte tag, AAD bound to provider+version and to the KEK id for the wrapped DEK, write-only UI, fixed provider URLs, tombstoned revocations enforced by trigger). Two SHOULD-FIX items in KEK rotation must be fixed **before the first rotation**: TOTP secrets are not re-sealed, and KEK ids default to fixed values so a rotation can silently do nothing. ADR still says "Proposed" while the code is merged. |
| 0014 Website system log and 60-day retention | **PASS with findings.** Append-only verified in Postgres (UPDATE / DELETE / TRUNCATE denied for `cp_website_admin`); purge is `SECURITY DEFINER`, owned by `cp_migrator`, pinned `search_path`, EXECUTE only for `cp_website_admin`; whitelist for `detail`; CSV formula guard present. Gate in the ADR itself ("Not shipped until worded", privacy notice) is not met, and future-dated rows escape the purge. |

Counts: BLOCKER 0 · SHOULD-FIX 3 · NOTE 6.

## Findings

### SHOULD-FIX

**S1. KEK rotation does not re-seal TOTP secrets; following the runbook locks every admin out of MFA (or leaves MFA secrets under a leaked KEK).**
- Evidence: `website/src/lib/admin/keys.ts:213-229` (`rewrapAll` selects only `website_secret`); TOTP secrets are sealed with the same KEK, `website/src/lib/admin/service.ts:377` (`seal(..., mfaAad(...), config.keks[0])`) and opened at `service.ts:381` and `:396` with `config.keks`. Runbook step `docs/runbook-website-admin.md:52` says to delete `WEBSITE_SECRETS_KEK_PREVIOUS` after `secrets:rewrap`. ADR 0013 line 18: "Same envelope used for TOTP secrets."
- Path: operator rotates (e.g. suspected KEK leak) → `npm run secrets:rewrap` reports success → removes `_PREVIOUS` → every `website_user.mfa_secret_enc` is still sealed under the old KEK id → `open()` throws "unknown KEK id" at MFA verification → no admin can complete sign-in; recovery only via `admin:reset --mfa` per user from the shell. If the operator keeps `_PREVIOUS` to avoid that, MFA secrets stay decryptable with the leaked key, so the rotation did not achieve its purpose.
- Impact: admin lock-out (availability) or incomplete rotation after a leak (confidentiality of second factor).
- Fix: in `rewrapAll` (same transaction) also re-seal `website_user.mfa_secret_enc` where it is not null and its envelope KEK id ≠ current (`sealedKekId()` already exists in `envelope.ts:51`; AAD `website_user.mfa|<id>`). Add a `mfa_kek_id` column or parse the envelope; return both counts; update the runbook text. Test: enrol MFA under `t1`, rotate to `t2`, rewrap, drop `t1`, MFA code verifies.
- Fixed: no (review only).

**S2. KEK ids default to fixed strings and are not validated against each other; a rotation can be a silent no-op that destroys the keys.**
- Evidence: `website/src/lib/admin/server.ts:34` and `website/scripts/secrets-rewrap.mts:12` default `WEBSITE_SECRETS_KEK_ID` to `"k1"`; `server.ts:38` / `secrets-rewrap.mts:14` default the previous id to `"previous"`; no check that the two ids differ or that the id matches `^[A-Za-z0-9_.-]{1,40}$` (the DB check in `0025_website_secret.sql:18`). `rewrapAll` selects `kek_id <> current.id` (`keys.ts:216`).
- Path: first deploy without `_ID` → rows carry `kek_id = 'k1'`. Rotation: operator sets a new `WEBSITE_SECRETS_KEK` but forgets the new `_ID` (stays `k1`) and sets `_PREVIOUS` without `_PREVIOUS_ID` (becomes `previous`). `rewrapAll` finds 0 rows (`kek_id <> 'k1'`), prints "Re-sealed 0 active key(s)", operator deletes `_PREVIOUS` → every stored API key (and every TOTP secret, see S1) is permanently undecryptable. Also: a key saved by a replica still running the old config after `rewrapAll` commits stays under the old KEK and is lost when `_PREVIOUS` is removed.
- Fix: make `WEBSITE_SECRETS_KEK_ID` required (no default) and validate it with the DB regex; when `_PREVIOUS` is set require `_PREVIOUS_ID` and require it ≠ current id; in `secrets-rewrap.mts` after the update, assert `select count(*) from website_secret where revoked_at is null and kek_id <> $current` = 0 (and the MFA equivalent) and print the remaining count; runbook: redeploy with the new KEK first, then rewrap, then remove `_PREVIOUS` only after a second rewrap reports 0. Test: same-id config is rejected.
- Fixed: no.

**S3. ADR 0014's own release gate is not met: the admin system log (staff and attacker IP prefixes, browser family, user ids) is merged while the privacy wording is missing and both ADRs are still "Proposed".**
- Evidence: `docs/adr/0014-website-system-log-retention.md:3` and `:33` ("`coo` decides ... Not shipped until worded"); `docs/adr/0013-website-integration-secrets.md:3` (Proposed); no mention of admin/security logs in `website/src/app/[lang]/privacy/page.tsx` or `website/src/messages/en.json`. Data stored in Railway Postgres (US region per the hosting ADR, not re-verified here).
- Impact: personal data (truncated IPs of anyone who tries `/admin/login`) collected without the notice the ADR itself requires; PIPEDA openness (Principle 4.8) gap flagged in `docs/security/privacy-posture.md`.
- Fix: keep `ADMIN_DATABASE_URL` / `WEBSITE_SECRETS_KEK` unset in production (the admin is then disabled: `server.ts:49-51`) until (a) Farjad Iranmehr accepts ADR 0013/0014, (b) `coo` ships the notice sentence and the staff notice. Mark both ADRs Accepted in the same PR. Decision for Farjad Iranmehr; not a code change.
- Fixed: no.

### NOTE

**N1. Log rows can be future-dated or attributed to anyone by the admin DB role; future rows are never purged.** `0024_website_admin_p1.sql:217` grants INSERT on all columns, including `occurred_at` and `actor_user_id`. Verified on a throwaway DB: as `cp_website_admin`, `insert ... occurred_at '2099-01-01'` succeeds and `website_log_purge()` leaves it (purge only deletes `< now() - 60 days`, `:192`); the viewer has no upper bound (`log.ts:30-31`). Precondition: control of the admin role (app RCE or leaked `ADMIN_DATABASE_URL`), so not exploitable from the browser. Fix (new migration 0026): `revoke insert on website_log from cp_website_admin; grant insert (actor_user_id, kind, action, target_type, target_id, outcome, ip_prefix, ua_family, detail) on website_log to cp_website_admin;` so `occurred_at` always takes `now()`. Actor spoofing is inherent to app-written audit logs; accept.

**N2. AAD differs from ADR 0013 text.** ADR line 13 says `provider|row id|version`; code uses `website_secret|<provider>|<version>` (`keys.ts:31`). `(provider, version)` is unique (`0025:29`) and the guard forbids changing provider/version (`0025:49-50`), so cross-row swapping still fails; MFA uses a separate namespace (`service.ts:98`). Fix: correct the ADR text, no code change.

**N3. Misconfigured KEK fails closed but silently.** `server.ts:43-45` swallows the error and the admin answers "The admin is not configured." with nothing in the logs. Not a leak (the message names only the variable, `crypto.ts:25-27`). Fix: `console.error` the variable name (never the value) once at first call.

**N4. fal "test connection" may succeed with a wrong key.** `keys.ts:165-168` — acknowledged in the UI text; ADR 0013 line 16 leaves the endpoint to P2. Fix in P2: pick an endpoint that returns 401 without a valid key.

**N5. ADR 0013 test "key absent from HTML/RSC/network/build output" is not implemented.** Only DB-level and log-level checks exist (`website/tests/admin-keys.test.ts`). Static review found no path (see verified-OK), but add a Playwright/RSC-payload assertion before P4.

**N6. Unauthenticated log growth.** Each failed `/admin/login` writes a row (`service.ts:290-292`); rate limit is per account and per IP prefix, so a distributed attempt can add many rows (each ≤ ~4 KB). Bounded by the 60-day purge; dashboard has no volume alert. Fix (later): cap or aggregate `login.failed` rows per prefix/window.

One-line flag outside this part: `website/src/app/admin/mfa/page.tsx:38` uses `dangerouslySetInnerHTML` for the QR SVG — for the auth (PR #60) reviewer to confirm the SVG is generated server-side from a fixed template.

## Verified OK (with evidence)

- **Algorithm / IV / tag:** AES-256-GCM, `randomBytes(12)` per encryption for both value and DEK (`envelope.ts:12`), fresh 32-byte DEK per seal (`:33`), tag length pinned to 16 and IV to 12 on decrypt (`:21-22`), DEK zeroed after use (`:36`, `:65`). KEK length checked = 32 (`crypto.ts:27`, `envelope.ts:32`).
- **AAD binding:** value AAD `website_secret|provider|version`; DEK AAD `dek|<kek id>|<value AAD>` (`envelope.ts:35`, `:61`), so the wrapped DEK cannot be moved between rows or KEKs. Tamper/wrong-KEK/AAD tests pass (`tests/admin-crypto.test.ts`).
- **Rewrap atomicity:** one transaction, `FOR UPDATE`, rollback on any failure (`secrets-rewrap.mts:19-25`); DB guard allows a sealed change only with a new `kek_id` (`0025:63-66`); errors print `error.message` only, never key material (`secrets-rewrap.mts:32`).
- **Tombstone:** revoke and replace set `sealed = website_secret_tombstone()` in the same statement (`keys.ts:84`, `:116`); trigger rejects any other revoked value and freezes revoked rows (`0025:55-62`); no DELETE/TRUNCATE (`0025:74-75`).
- **Write-only:** `keys.ts` imports `server-only` (`:4`); `listKeys` selects metadata only (`:36-39`); the only `"use server"` export is `keyAction` (`app/admin/keys/actions.ts`), which returns `KeyResult` messages (last 4 only); `decryptKeyServerSide` is not an action (its module has no `"use server"`). Key input `type="password"`, `autoComplete="off"` (`KeyCard.tsx:72-74`).
- **Test call:** URLs are constants per provider (`keys.ts:157-170`), key only in headers, `redirect: "error"`, 10 s timeout, only the HTTP status is stored/logged (`:187-193`), fetch errors swallowed. No SSRF.
- **Authorisation:** key ops and log export need session + MFA + CSRF + admin role + step-up ≤ 5 min (`server.ts:95-106`, `permissions.ts:30-31`); export is POST-only (`log/export/route.ts:6`); viewer `requirePage("log.view")` = admin only (`log/page.tsx:44`).
- **CSV:** cells starting `= + - @ | % \t \r` prefixed with `'`, quotes/newlines escaped (`log.ts:94-95`); `detail` exported as JSON (starts with `{`). Viewer renders through React (escaped).
- **Log content:** `cleanDetail` whitelist + forbidden-word filter, path stripped of query/fragment (`log-detail.ts`); login failure reasons are fixed codes, no email (`service.ts:296-318`); /admin errors log path, error name and digest only, no IP (`background.ts:50-60`); purge errors record name + SQLSTATE only (`log.ts:139-148`).
- **DB grants (verified on a throwaway DB):** `cp_website`, `cp_app`, `cp_admin` have no SELECT/INSERT on `website_log`, `website_secret`, `website_user`, `website_session`, `website_job_run`; `cp_website` is not a member of `cp_website_admin`; `cp_website_admin` UPDATE/DELETE/TRUNCATE on `website_log` → permission denied. Tables owned by `cp_migrator`, RLS off as declared in `db/rls_tables.yaml:46-54` (class `website_admin`, ADR 0008 §0.3 allowlist satisfied; C-0 test passes). `website_log_purge` = SECURITY DEFINER, owner `cp_migrator`, `search_path=""`, not executable by `cp_website`. Admin uses its own pool (`ADMIN_DATABASE_URL`, `server.ts:20-25`), separate from the public site.
- **Retention:** purge `< now() - 60 days` (`0024:192`); viewer and export never show rows older than 60 days (`log.ts:30`); hourly in-process timer with transaction-scoped advisory lock and 23 h gate (`log.ts:118-136`, `background.ts:42-47`); dashboard warns when `last_ok_at` > 26 h (`app/admin/page.tsx:14-33`). Runs only while the website service runs and `ADMIN_DATABASE_URL` is set (as ADR 0014 option A states).
- **Migrations forward-only:** `git diff --name-status 8344ec5^1 b0e56cb -- db/migrations` shows only `A 0024`, `A 0025`.
- **Dependencies:** `npm audit --omit=dev` → 0 vulnerabilities.

## Tests run (local only, no Railway)

- Copy of `b508e2a` in scratch (`main-ro` untouched). `npm ci --ignore-scripts && npm test` → 63 tests, 39 pass, 24 skipped (DB opt-in).
- Throwaway container `postgis/postgis` on `127.0.0.1:55499` (removed afterwards). `make db-test` → **604 passed, 1 skipped** (WeasyPrint/pango, unrelated), including `test_website_admin.py`.
- Migrated database (0001–0025) + `WEBSITE_TEST_DATABASE_URL` → `npm test` **63/63 pass, 0 skipped** (keys, log, purge, rewrap, users, service).
- Manual SQL probes for grants, append-only and N1 (results above).

## Not verified

- Whether `/admin` is enabled on the live site (Railway variables) and whether the purge timer runs there — not touched by rule.
- Railway region of the database (taken from ADRs).
- Next.js production behaviour of thrown server-action errors (message redaction) — relied on documented behaviour, not re-fetched.
- E2E check that the key never appears in HTML/RSC payloads (N5).
- KEK rotation end-to-end with MFA (S1) — derived from code; no test exists.
