# Pre-release security gate (S5 go/no-go)

Status: DRAFT (security-engineer, 2026-11-16). Owner of the gate: `ciso`. Joint go/no-go: `cp-qa` + `ciso` + CPO (docs/sprints/roadmap.md, "Release gate go/no-go").

- When: S5, Jan 18 – Jan 29, 2027. Production deploy: Feb 1, 2027. Re-run before every production release after that.
- Scope: the internal concierge tool (`app/`, FastAPI on Railway), Railway Postgres/PostGIS, the proof-PDF bucket (ADR 0005, option B1), the public website (`website/`), and the public GitHub repo.
- Rule: every box is ticked with an evidence link (PR, CI run, screenshot, doc). No evidence, no tick. Any unticked box in sections 1–5 is a **NO-GO**. Unticked boxes in section 6 need a written waiver from `ciso` + CPO with an expiry date.
- Evidence must not contain secret values, tokens, connection strings or personal data. Screenshots of Railway settings are cropped or redacted.

## 1. Code review closed

- [ ] **Auth / session / CSRF review closed.** Login, logout, server-side session store (`user_session`), cookie flags (`HttpOnly`, `Secure`, `SameSite`), session revocation, lockout / login rate limit, CSRF token on every state-changing route, org scoping on every query, `reviewer_id` taken from the session only (ADR 0005). Owner: `security-engineer` → `ciso`. Evidence: review doc in `docs/security/` + PRs that closed each finding.
- [ ] **No open BLOCKER or SHOULD-FIX security findings.** Every finding from the S2 threat model, the auth review and later reviews is fixed (PR linked) or downgraded with a written reason signed by `ciso`. Owner: `ciso`. Evidence: findings table with status per item.
- [ ] **Immutability and review gate enforced server-side.** Recommendations insert-only (edits create a new version with `parent_id` + `reason`), `review` rows insert-only, no number reaches a farmer without approval (CLAUDE.md rules 4 and 8). Owner: `cto` (`cp-qa` tests). Evidence: tests that try to update/delete and fail; DB grants or triggers listed.
- [ ] **Error handling does not leak.** Production runs without debug/reload; 4xx/5xx pages show no stack traces, SQL or env values. Owner: `cp-platform`. Evidence: staging request for a forced 500 and its response body.

## 2. Supply chain and repository (public repo)

- [ ] **Secret scan clean on all refs.** `security.yml` gitleaks job green on `main` and the last weekly full-history run green; no unresolved hit. Any real secret found at any time was rotated (not just deleted from history). Owner: `security-engineer`. Evidence: CI run links + `docs/security/secret-and-dependency-scan-*.md`.
- [ ] **Dependency audit clean.** `pip-audit` (uv.lock, all members and groups) and `npm audit --omit=dev --audit-level=high` (website) green on the release commit; no open Dependabot alert rated high or critical. Owner: `security-engineer`. Evidence: CI run links + Dependabot alerts page (screenshot).
- [ ] **Vendored front-end code verified.** `app/cloverproof_app/static/vendor/*` matches the upstream npm tarball (hash in `vendor/README.md`) and has no open advisory. Owner: `security-engineer`. Evidence: hash check output.
- [ ] **GitHub repo settings.** Branch protection on `main` (PR required, CI + `security` checks required, no force push); secret scanning + push protection on; Dependabot alerts + security updates on; Actions workflow permissions default read-only; only the owner has admin. Owner: `ciso`. Evidence: settings screenshots.
- [ ] **Release built from a tagged commit on `main`.** Railway deploys exactly that commit; no local builds pushed. Owner: `release-manager` / `cto`. Evidence: tag + Railway deployment ID.

## 3. Runtime configuration

- [ ] **Security headers on the app.** CSP (`default-src 'self'`, no `unsafe-inline`/`unsafe-eval`), `X-Content-Type-Options: nosniff`, `frame-ancestors 'none'`/`X-Frame-Options: DENY`, `Referrer-Policy`, and `Strict-Transport-Security` (max-age ≥ 15552000) on every response including errors and static files. Owner: `cp-platform`. Evidence: `curl -sI` output against staging and production for `/login`, a static asset and a 404.
- [ ] **Security headers on the website.** Same check for `website/` (at the 2026-11-16 snapshot `next.config.ts` sets no security headers — must be added or the waiver signed). Owner: `cp-website`. Evidence: `curl -sI` output for `/` and one locale page.
- [ ] **TLS only.** HTTP redirects to HTTPS on every public domain; no mixed content. Owner: `cp-platform`. Evidence: `curl -sI http://…` showing the redirect.
- [ ] **Env vars set, no defaults.** `DATABASE_URL`, `SESSION_SECRET` (random, ≥ the app's minimum length, generated for production only, never reused from staging or local), `BUCKET_*` set in Railway for production; the app refuses to start when any is missing (config tests). No compose-file default credential (`docker-compose.yml`) is used outside a laptop. Owner: `cp-platform`. Evidence: Railway variable *names* list (values hidden) + startup test link.
- [ ] **Database not publicly exposed.** Railway Postgres has no public TCP proxy (or it is disabled after migrations); the app connects over the private network (`RAILWAY_PRIVATE_DOMAIN`, see `docs/runbook-db-switch.md`); app DB role is not superuser and cannot drop tables. Owner: `cp-database`. Evidence: Railway networking screenshot + `\du` output (role names only).
- [ ] **Bucket private + hash verify.** Proof bucket has no public access and no presigned URL with long expiry; the app re-computes SHA-256 on read and refuses a mismatch against `proof_document.sha256`; objects are never overwritten (ADR 0005). Owner: `cp-pdf`. Evidence: anonymous GET returns 403 + test for the mismatch path.

## 4. Access and operations

- [ ] **Railway access.** Every member has 2FA on; member list reviewed and reduced to people who need it; no personal API tokens left over; project tokens scoped to one environment. Owner: `ciso`. Evidence: members page screenshot (names only) + token list review date.
- [ ] **GitHub access.** Owner account has 2FA; no deploy keys or PATs with write access that are not in use. Owner: `ciso`. Evidence: settings screenshot.
- [ ] **Backups tested.** A restore of a recent production backup into a scratch database was done in S5, row counts and one proof-document hash checked, time-to-restore recorded. Link the backup plan: `docs/ops/backup-plan.md` (TODO: path not yet in the repo on 2026-11-16 — `coo` / `cp-platform` to create in S3). Owner: `cp-platform` + `coo`. Evidence: restore log + plan link.
- [ ] **Rollback rehearsed.** Rollback to the previous Railway deployment and a migration rollback (or forward fix) rehearsed on staging within S5; time recorded. Owner: `cto` / `release-manager`. Evidence: rollback runbook link + rehearsal notes.
- [ ] **Incident contacts and runbook.** Named primary + backup contact, how to reach them, steps to revoke all sessions, rotate `SESSION_SECRET` / bucket keys / DB password, and take the app offline. Owner: `ciso`. Evidence: `docs/security/incident-response.md` (or equivalent) link.

## 5. Personal data

- [ ] **Logging without PII or secrets.** Application and access logs contain no passwords, session tokens, CSRF tokens, `DATABASE_URL`, farmer names, emails or phone numbers; request bodies are not logged. Owner: `cp-platform` + `data-governance-specialist`. Evidence: grep of one day of staging logs + logging config link.
- [ ] **Privacy notice live.** Privacy notice (and consent wording for pilot farms) reviewed by `legal-compliance-specialist`, published on the website for every live locale, and linked from the pilot-request form. Owner: `coo`. Evidence: live URLs + review note.
- [ ] **Data inventory.** PII classes from the data dictionary mapped to tables and to the bucket; retention stated. Owner: `head-of-data`. Evidence: data dictionary link.

## 6. Recommended (waivable with expiry)

- [ ] TOTP (second factor) enabled for every internal user (ADR 0005 allows it).
- [ ] Commit author email switched to the GitHub `noreply` address for future commits (public repo).
- [ ] Uptime / error alerting to the incident contacts.

## Sign-off

| Role | Name | Decision (GO / NO-GO) | Date | Notes |
|---|---|---|---|---|
| `ciso` | | | | |
| `cp-qa` | | | | |
| CPO (`product-manager`) | | | | |
