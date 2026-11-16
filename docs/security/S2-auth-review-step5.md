# S2 security review — Step 5 auth (branch `webapp-step5-app`, commit c720eec)

- Reviewer: `security-engineer` (reports to `ciso`), 2026-11-16
- Scope: `app/cloverproof_app/{auth,security,ratelimit,web,main,config,cli}.py`, `repo/*.py`, `db/pool.py`, templates, vendored htmx, `db/migrations/0002`–`0003` grants (and the review/proof triggers they feed).
- Method: static read of `git diff main...HEAD`, plus checks of the installed library code (uvicorn 0.54.0, Starlette 1.10.0, pwdlib 0.4.2, argon2-cffi 25.1.0) and of npm registry integrity for htmx. `uv run pytest app/tests -q` without a DB: 34 passed, 83 skipped (all DB/auth integration tests are opt-in and were **not** run). Nothing was run against Railway or production.
- Line numbers refer to commit c720eec.

## Verdict
No BLOCKER in the Step 5 code. The design is sound (argon2id, hashed 256-bit session tokens in Postgres, idle + absolute expiry, rotation on login, per-session HMAC CSRF on every non-GET including login, signed org cookie with membership re-checked per request, autoescaped templates, parameterised SQL). Seven SHOULD-FIX items, most of them deployment-shaped: they decide whether the controls still hold once the app sits behind Railway's proxy and connects to the shared database. Fix them before the Step 7 release gate.

## Findings

### SHOULD-FIX

**S1. Login rate limit: wrong key behind Railway, spoofable if proxy headers are trusted with `*`, no per-account ceiling**
- Evidence: `app/cloverproof_app/web.py:82-85` (`client_ip` = `request.client.host`), `app/cloverproof_app/ratelimit.py:29-31` (key = `(email, ip)`), `web.py:134-141`.
- Exploit, today (no `--proxy-headers`): every request arrives from a Railway edge address, so the key is effectively per email. Anyone who knows the agronomist's email sends 5 bad passwords every 15 minutes and keeps him locked out (availability, during the Feb–Apr review season).
- Exploit, after the likely Step 7 fix (`--forwarded-allow-ips='*'`): uvicorn 0.54 with `*` returns the **leftmost** `X-Forwarded-For` entry (`uvicorn/middleware/proxy_headers.py`, `get_trusted_client_address`, `always_trust` branch). If Railway's edge appends rather than replaces the header (not verified), a client sets `X-Forwarded-For: <random>` per request and gets a fresh bucket each time: unlimited online guessing.
- Even with a correct IP, keying on `(email, ip)` gives a distributed attacker unlimited attempts per account.
- Fix: (a) two counters: per-IP hard block (from a trusted IP) and per-account soft limit (e.g. 20 failures/hour → 503 "try later" plus a log line, unlock via CLI); (b) decide the proxy trust in Step 7: verify what Railway sends (`X-Real-IP` / `X-Forwarded-For`) on staging, then read the **rightmost** untrusted hop or Railway's single client header, never `*` + leftmost; (c) add a test that a spoofed `X-Forwarded-For` does not reset the counter. Moving the counter to Postgres also fixes multi-replica/restart resets (documented at `ratelimit.py:3-6`).

**S2. Unbounded concurrent argon2 on the public login endpoint (CPU/memory DoS)**
- Evidence: `security.py:15` (argon2id t=3, m=64 MiB, p=4 — confirmed RFC 9106 low-memory defaults in argon2-cffi 25.1.0), `web.py:122-139` (`def login` is sync, so it runs in AnyIO's thread pool, default 40 threads).
- Exploit: fetch `/login` once for a CSRF cookie/token pair, then send concurrent POSTs with random emails (each new email is a new rate-limit key, and unknown emails still hash against `_DUMMY_HASH` by design). Up to 40 × 64 MiB ≈ 2.5 GiB and all cores busy; the service OOMs or stalls.
- Fix: wrap `verify_password` in a module-level `threading.BoundedSemaphore(2)` (acquire with a short timeout → 503), plus a global failure budget (e.g. 30 failed logins/minute across all keys → 503 for 1 minute). Keep the dummy hash.

**S3. Password reset does not revoke existing sessions; no "revoke all" path**
- Evidence: `cli.py:91-94` sets the new hash only; `repo/sessions.py:54-58` revokes a single token.
- Exploit: the reason to reset a password is usually suspected compromise; an attacker's live session stays valid for up to 12 h (`config.py:47`) after the reset.
- Fix: add `sessions.revoke_all_for_user(conn, user_id)` (`update user_session set revoked_at = now() where user_id = %s and revoked_at is null`), call it in `user_create` when `reset_password` is set, and add a `user-revoke-sessions --email` CLI subcommand. Test: session cookie from before the reset gets 401 after it. (Disabling a user already kills sessions via the join in `repo/sessions.py:43-45`, verified.)

**S4. Nothing enforces that the app connects as `cp_app_login`; if it uses the Railway superuser URL the grant line of defence is gone**
- Evidence: `db/pool.py:29-35` and `config.py:52-62` accept any `DATABASE_URL`; the least-privilege login is only a manual runbook step (`docs/runbook-db-switch.md:16`, migration comment `db/migrations/0002_roles_and_extensions.sql:5-8`). On Railway the default reference variable is the superuser URL (ADR 0004).
- Impact: ADR 0002 promises two lines (grant stops the app, trigger stops everyone). As superuser the app can `alter table ... disable trigger` or `set session_replication_role = replica` and rewrite "immutable" recommendations/reviews — so one SQL injection or RCE later becomes undetectable tampering with approved numbers (hard rules 4 and 8).
- Fix: on startup, when `ENV` is `staging` or `production`, run `select rolsuper, rolbypassrls from pg_roles where rolname = current_user` and `select pg_has_role(current_user, 'cp_app', 'member')`; raise `ConfigError` if superuser or not a member. Unit-test with a fake connection.

**S5. `cp_app` can write `membership`, `organisation` and all of `app_user` — the database review gate trusts data the app can forge**
- Evidence: `db/migrations/0003_identity.sql:84` grants `select, insert, update, delete` on `organisation, app_user, user_session, membership` to `cp_app`. The review trigger (`db/migrations/0007_review.sql:35-48`) decides "is this reviewer an agronomist?" from `membership`.
- Exploit: any future injection or logic bug in the app (the role the trigger is meant to constrain) can `insert into membership (..., 'agronomist')` for a staff user and then approve. The gate in the DB is therefore only as strong as the app.
- Fix: new migration: `revoke insert, update, delete on membership, organisation from cp_app; revoke update on app_user from cp_app; grant update (password_hash) on app_user to cp_app;` (rehash on login is the only app write, `web.py:148-149`). The CLI runs as a separate admin login (e.g. `cp_admin_login in role cp_app, cp_admin`) that keeps those writes. Extend `app/tests/db/test_immutability.py`-style privilege tests.

**S6. Absolute URLs from `url_for` + TLS termination at Railway: assets break, and the obvious fix weakens S1**
- Evidence: `templates/base.html:8-10` use `url_for('static', ...)`; Starlette 1.10 `Request.url_for` returns `make_absolute_url(base_url=self.base_url)` (built from the request's Host and scheme). Behind Railway, without trusted proxy headers, scheme is `http` → `http://<host>/static/htmx…js` on an HTTPS page → browsers block it as mixed content.
- Impact: functional breakage at deploy, with the quick fix being `--forwarded-allow-ips='*'`, which creates the spoofing in S1. Also the response embeds whatever `Host` the client sent (no `TrustedHostMiddleware`); harmless while nothing caches, but avoidable.
- Fix: use path-only URLs (`url_for(...).path` or plain `/static/...`), add `TrustedHostMiddleware(allowed_hosts=[APP_HOST])` from an env var, and set proxy trust deliberately (S1b).

**S7. All auth integration tests are skipped in CI**
- Evidence: `.github/workflows/ci.yml:37` runs `make test` → `Makefile:35-36` `uv run pytest`; `app/tests/db/*` skip without `TEST_DATABASE_URL` (83 skipped locally). `make db-test` (`Makefile:58-60`) is never called in CI.
- Impact: CSRF, login, expiry, revocation, org-scoping and review-gate tests (`app/tests/db/test_web_auth.py`, `test_review_gate.py`, `test_org_scoping.py`) can regress unnoticed.
- Fix: CI job with a `postgis/postgis:17-3.5` service container, `TEST_DATABASE_URL` pointing to it and `make db-test` with `CP_DB_TESTS_REQUIRED=1`.

**S8. No HSTS**
- Evidence: `main.py:29-37` sets CSP, nosniff, XFO, Referrer-Policy; no `Strict-Transport-Security`. Whether Railway's edge adds HSTS: not verified.
- Fix: in staging/production add `Strict-Transport-Security: max-age=31536000; includeSubDomains` (only `includeSubDomains` if every subdomain of the custom domain is HTTPS).

### NOTE (hardening; no concrete exploit today)

- **N1. Cookie prefixes / login CSRF cookie unsigned.** `auth.py:28-30`, `web.py:57-66`, `auth.py:172-174`. `up.railway.app` is on the Public Suffix List (checked), so sibling Railway apps cannot toss cookies. On a custom domain, any sibling subdomain (e.g. the website) could set `cp_login_csrf` and forge a login CSRF. Use `__Host-` names when `cookie_secure` is true and bind the login token by HMAC (`sign(secret, "login", nonce)`) instead of plain double-submit.
- **N2. No Origin / `Sec-Fetch-Site` check** in `csrf_guard` (`auth.py:161-179`). Tokens + SameSite=Lax are sufficient; rejecting `Sec-Fetch-Site: cross-site` on non-GET is a cheap second line.
- **N3. 422 validation responses echo input.** `web.py:127-129` (`max_length` on email/password): FastAPI's default `RequestValidationError` handler returns JSON with `input`, so an over-long password is echoed back (to the sender only) and the user sees raw JSON. Add a handler that re-renders the login page with the generic message.
- **N4. Session cookie is persistent (Max-Age 12 h, `web.py:159`).** Survives browser close on a shared farm-office computer. Consider a session cookie (no Max-Age); server-side expiry already bounds it.
- **N5. Expired/revoked sessions are never purged** (`repo/sessions.py`). Add a periodic `delete from user_session where expires_at < now() - interval '30 days'`.
- **N6. htmx history cache.** Vendored htmx 2.0.11 defaults `historyCacheSize:10` (localStorage snapshots of pages). No `hx-push-url`/`hx-boost` yet, so nothing is stored; set `"historyCacheSize": 0` in the `htmx-config` meta (`base.html:6`) before Step 5B pages show farmer data.
- **N7. `ENV` defaults to `development`** (`config.py:44`). `COOKIE_SECURE` still defaults to true, so no impact today; future prod-only checks (S4, S8) would silently skip if `ENV` is unset. Require `ENV` when `DATABASE_URL` is not local, or default to `production`.
- **N8. Unhandled exceptions bypass the header middleware.** A 500 from `ServerErrorMiddleware` is outside `security_headers` (`main.py:81-90`). Body is plain "Internal Server Error" (no debug), so only headers are missing. Low.
- **N9. CLI non-TTY password path** (`cli.py:100-104`) is fine for automation, but `echo pw | ...` puts it in shell history. Document `read -s` usage.
- **N10. Uvicorn access logs** will record client IP and the `next=` query. Fine for an internal tool; mention in the privacy notice (PIPEDA).

### Adjacent (outside the Step 5 diff, flagged only)
- **A1 (BLOCKER for executing the runbook):** `docs/runbook-db-switch.md:24` points the public website's `DATABASE_URL` at the PostGIS **superuser** URL. A website compromise then owns `app_user` hashes, sessions and can rewrite approved recommendations with triggers disabled. Create `cp_website_login` with `insert` on `pilot_request` only (plus `usage` on schema) before the switch. Detail in `threat-model-webapp.md` T-W3.
- **A2:** GitHub `main` is unprotected, secret scanning and push protection are disabled on this public repo (read via `gh api`, 2026-11-16). See threat model T-R1/T-R2.

## Verified OK
- argon2id via pwdlib → argon2-cffi `PasswordHasher` defaults t=3, m=65536 KiB, p=4 (RFC 9106 low-memory); outdated hashes re-hashed on login (`web.py:148-149`). Min password 12 (`security.py:16`, enforced in `hash_password`).
- User enumeration: one message for unknown/wrong/disabled (`web.py:42,140-145`); unknown or password-less accounts verify against a dummy hash with the same parameters (`security.py:19,30-32`); disabled check happens after verification, so timing matches. Logs carry no email/IP (`web.py:142`).
- Session token: `secrets.token_urlsafe(32)` (256 bits), only SHA-256 stored, `char(64)` hex check + unique (`0003_identity.sql:36`). Lookup is by hash, so DB comparison timing leaks nothing useful.
- Expiry: absolute via `expires_at` + idle via `last_seen_at` in one query, disabled users excluded (`repo/sessions.py:39-46`); touch at most every 60 s (`auth.py:94-95`).
- Rotation on login: old session revoked, new token, org cookie and login CSRF cookie cleared (`web.py:150-161`). Logout revokes server-side and clears cookies (`web.py:165-175`).
- Cookies: HttpOnly, Secure (cannot be false in staging/production, `config.py:61-62`), SameSite=Lax, Path=/.
- CSRF: app-wide dependency on every non-GET/HEAD/OPTIONS, header or form field, constant-time compare (`security.py:59-60`); per-session HMAC token, rotates with the session; login has its own token. No state-changing GET routes. htmx `selfRequestsOnly:true` default (checked in the vendored file), so `hx-headers` never sends the token cross-origin; the attribute is built with `tojson`, which escapes `'`.
- Open redirect: `safe_next` rejects `//` and `/\`; Starlette's `RedirectResponse` percent-encodes the Location (`\`, tab, CR/LF become `%5C`, `%09`…), so `"/\t/evil"` style bypasses do not work.
- Org scoping/IDOR: org from signed cookie bound to session id, membership re-checked every request (`auth.py:116-141`); forged cookie test exists; `list_farmers` filters by `org_id` (`repo/farmers.py:27`); `farmer` role excluded from the tool (`auth.py:37`, `web.py:205`).
- Templates: Starlette `Jinja2Templates` uses `select_autoescape()` → `.html` autoescaped; no `|safe` anywhere.
- CSP: `default-src 'self'; script-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'`, `allowEval:false`, no inline script/style; nosniff, XFO DENY, Referrer-Policy, `Cache-Control: no-store` on dynamic pages. `/docs`, `/redoc`, `/openapi.json` disabled.
- SQL: every query parameterised (psycopg `%s`); no string-built SQL.
- Config: fail fast on missing `DATABASE_URL`/`SESSION_SECRET`, secret ≥ 32 chars, no default secrets, value never printed (`config.py`).
- CLI: getpass twice, never argv, never logged; roles restricted to staff roles; refuses disabled accounts.
- Error pages: only the `detail` strings written in code; 500s are generic.
- Vendored htmx: npm tarball sha512 matches registry; `package/dist/htmx.min.js` sha256 `d6fdc75f…f717` equals the vendored file (downloaded and hashed 2026-11-16).
- DB helpers `member_organisation_ids`/`has_org_role` are not `SECURITY DEFINER` (no search_path risk) and exclude disabled users.

## Not verified
- Railway edge behaviour: whether it strips or appends client-supplied `X-Forwarded-For`, which header carries the real client IP, whether it adds HSTS. Check on staging.
- `reviewer_id` from session and the approval role check: no review route exists yet in c720eec (Step 5B). The DB trigger is in place; re-review the route when it lands.
- DB integration tests (83) were not run (no `TEST_DATABASE_URL`).
- Which Postgres role the deployed app will use (no app service on Railway yet).
