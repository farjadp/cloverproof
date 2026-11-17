# Pre-release security gate (S5 go/no-go)

Status: DRAFT (security-engineer, 2026-11-16; residency update devops-engineer for `ciso`, 2026-11-16, per ADR 0009 and Farjad Iranmehr's decision "Railway now, Canada later"). Owner of the gate: `ciso`. Joint go/no-go: `cp-qa` + `ciso` + CPO (docs/sprints/roadmap.md, "Release gate go/no-go").

- When: S5, Jan 18 – Jan 29, 2027. Production deploy: Feb 1, 2027. Re-run before every production release after that.
- **Exception: section 6 must pass before the first real farm data is entered** (S5 rehearsal enters 3 real farms from Jan 18, 2027 — ADR 0009), i.e. at the end of S4, not at the Jan 29 gate. Whichever comes first.
- "Production host" = the Canadian host chosen under ADR 0009 (recommended DigitalOcean TOR1; runner-up Google Cloud Toronto/Montréal). Railway holds synthetic data (+ `pilot_request` until cutover) only and is **not** production for farmer data.
- Scope: the internal concierge tool (`app/`, FastAPI on the production host), production Postgres/PostGIS, the proof-PDF bucket (ADR 0009: Spaces TOR1 or GCS Canada; replaces ADR 0005 B1 Railway Bucket), the offsite backup bucket (S3 ca-central-1), the public website (`website/`), any remaining Railway environments, and the public GitHub repo.
- Rule: every box is ticked with an evidence link (PR, CI run, screenshot, doc). No evidence, no tick. Any unticked box in sections 1–6 is a **NO-GO**. Unticked boxes in section 7 need a written waiver from `ciso` + CPO with an expiry date.
- Evidence must not contain secret values, tokens, connection strings or personal data. Screenshots of provider settings (Railway, DigitalOcean / Google Cloud, AWS) are cropped or redacted; bucket names and account ids are not committed to the public repo.

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
- [ ] **Release built from a tagged commit on `main`.** The production host deploys exactly that commit; no local builds pushed. Owner: `release-manager` / `cto`. Evidence: tag + production-host deployment ID.

## 3. Runtime configuration

- [ ] **Security headers on the app.** CSP (`default-src 'self'`, no `unsafe-inline`/`unsafe-eval`), `X-Content-Type-Options: nosniff`, `frame-ancestors 'none'`/`X-Frame-Options: DENY`, `Referrer-Policy`, and `Strict-Transport-Security` (max-age ≥ 15552000) on every response including errors and static files. Owner: `cp-platform`. Evidence: `curl -sI` output against staging and production for `/login`, a static asset and a 404.
- [ ] **Security headers on the website.** Same check for `website/` (at the 2026-11-16 snapshot `next.config.ts` sets no security headers — must be added or the waiver signed). Owner: `cp-website`. Evidence: `curl -sI` output for `/` and one locale page.
- [ ] **TLS only.** HTTP redirects to HTTPS on every public domain; no mixed content. Owner: `cp-platform`. Evidence: `curl -sI http://…` showing the redirect.
- [ ] **Env vars set, no defaults.** `DATABASE_URL`, `SESSION_SECRET` (random, ≥ the app's minimum length, generated for production only, never reused from staging or local), `BUCKET_*`, `BACKUP_DEST_*` set on the production host (encrypted env) for production; the app refuses to start when any is missing (config tests). No compose-file default credential (`docker-compose.yml`) is used outside a laptop. Owner: `cp-platform`. Evidence: production-host variable *names* list (values hidden) + startup test link.
- [ ] **Database not publicly exposed.** Production DB accepts connections only from the app/worker/website/backup job over the private network (DO: trusted sources = the App Platform app only, VPC; GCP: private IP / connector, no authorised networks); no `0.0.0.0/0` rule; TLS required. App DB role is not superuser and cannot drop tables. Detailed check in §6.3. Owner: `cp-database`. Evidence: trusted-sources / networking screenshot + `\du` output (role names only). [Was: Railway TCP proxy check — now §6.7 for remaining Railway envs.]
- [ ] **Bucket private + hash verify.** Proof bucket has no public access and no presigned URL with long expiry; the app re-computes SHA-256 on read and refuses a mismatch against `proof_document.sha256`; objects are never overwritten (ADR 0005). Owner: `cp-pdf`. Evidence: anonymous GET returns 403 + test for the mismatch path.

## 4. Access and operations

- [ ] **Production host + backup account access.** DigitalOcean team (or GCP project) and the AWS backup account: every member has 2FA/MFA; member list reduced to people who need it; AWS root has MFA and no access keys; no personal API tokens left over; backup writer key is `PutObject`-only. Owner: `ciso`. Evidence: members/IAM screenshots (names only) + token list review date.
- [ ] **Railway access (while the account exists).** 2FA on; members reduced; no leftover tokens; project tokens scoped to one environment. Owner: `ciso`. Evidence: members page screenshot (names only).
- [ ] **GitHub access.** Owner account has 2FA; no deploy keys or PATs with write access that are not in use. Owner: `ciso`. Evidence: settings screenshot.
- [ ] **Backups tested.** Timed S5 rehearsal on the production host: Drill A (offsite `age` dump from S3 ca-central-1 → scratch DB) and Drill B (provider PITR → new cluster), V1–V7 passed incl. all proof-document hashes, RPO/RTO measured against plan §6. Plan: `docs/security/backup-restore-test-plan.md` (replaces the `docs/ops/backup-plan.md` TODO). Owner: `cp-database` + `cp-platform`, `cp-qa` observes. Evidence: `docs/security/evidence/drill-*.md`.
- [ ] **Rollback rehearsed.** Rollback to the previous production-host deployment and a migration rollback (or forward fix) rehearsed on staging within S5; time recorded. Owner: `cto` / `release-manager`. Evidence: rollback runbook link + rehearsal notes.
- [ ] **Incident contacts and runbook.** Named primary + backup contact, how to reach them, steps to revoke all sessions, rotate `SESSION_SECRET` / bucket keys / DB password / backup keys, restore from PITR or S3 dump, and take the app offline. Owner: `ciso`. Evidence: `docs/security/incident-response.md` (or equivalent) link.

## 5. Personal data

- [ ] **Logging without PII or secrets.** Application and access logs contain no passwords, session tokens, CSRF tokens, `DATABASE_URL`, farmer names, emails or phone numbers; request bodies are not logged. Owner: `cp-platform` + `data-governance-specialist`. Evidence: grep of one day of staging logs + logging config link.
- [ ] **Privacy notice live.** Privacy notice (and consent wording for pilot farms) reviewed by `legal-compliance-specialist`, published on the website for every live locale, and linked from the pilot-request form. Owner: `coo`. Evidence: live URLs + review note.
- [ ] **Data inventory.** PII classes from the data dictionary mapped to tables and to the bucket; retention stated. Owner: `head-of-data`. Evidence: data dictionary link.

## 6. Residency & cutover (ADR 0009) — must pass before the first real farm data

All evidence follows the rules at the top (no secrets, no PII, no bucket names). Procedures: `docs/security/backup-restore-test-plan.md` §7 (cutover) and §8 (residency check).

- [ ] **6.1 No real farmer data on Railway.** On every Railway environment still running, the synthetic-data query (backup plan §8.1) returns 0 for real orgs, users, farmers and soil tests; after cutover also 0 live `pilot_request` rows. Synthetic data follows the naming rule (`(dev seed)` / `(synthetic)` org names, `@example.org` users). Owner: `cp-database`, run by Farjad Iranmehr. Evidence: query output (counts only), date.
- [ ] **6.2 Production storage located in Canada.** DB cluster, DB backups + PITR WAL, proof bucket, offsite backup bucket (S3 `ca-central-1`, no replication), app/worker/website/jobs, and application + build logs are in Canadian regions. Evidence: (a) provider **written confirmation** for what config cannot show (DO: backup/WAL and log location; GCP: transaction-log location), dated, filed per ADR 0009 Q3 / backup plan §12; (b) region-setting screenshots or read-only CLI output per backup plan §8.2 (GCP: `settings.backupConfiguration.location` set to a Canadian region — empty = multi-region = FAIL; org policy `gcp.resourceLocations`). Owner: `cp-platform`, `ciso` accepts.
- [ ] **6.3 Production DB has no public ingress.** No public endpoint reachable from the internet: DO trusted sources limited to the app (no IP ranges), or GCP private IP only / no authorised networks; connection attempt from an outside IP fails. Owner: `cp-database`. Evidence: settings screenshot + failed `psql`/`nc` attempt from a laptop (output, no credentials).
- [ ] **6.4 DPAs signed after counsel review.** Production host (DO or Google) and AWS (backup) DPAs reviewed by `legal-compliance-specialist`/counsel, accepted by Farjad Iranmehr; sub-processor list with locations, breach-notice clock and backup expiry noted (ADR 0009 Q1, Q2, Q6). Owner: `coo`. Evidence: dated copies (stored privately, link only).
- [ ] **6.5 Privacy notice updated.** States: storage in Canada (Toronto) with a US-owned provider, possible access by US authorities (CLOUD Act); offsite encrypted backup copy with AWS in Canada; maximum backup age; out-of-Canada processors named — Sentry (US/EU, PII scrubbed), GitHub (code/CI, synthetic data only), AI reviewer (de-identified only), any email provider; former US storage of pilot requests and its end date. Live on every website locale and linked from the pilot form. Owner: `coo` + `legal-compliance-specialist`. Evidence: live URLs + review note.
- [ ] **6.6 Restore drill on the Canadian host passed.** Drill A + Drill B on the production host's staging (S4) and the timed S5 rehearsal, each including the V7 residency check. Owner: `cp-database`. Evidence: drill files (same as §4 "Backups tested").
- [ ] **6.7 Railway hosted environments contain synthetic data only.** Remaining Railway envs: no public DB TCP proxy, no production credentials (no variable points at the Canadian DB or buckets), PR environments off or based on a synthetic env; old Railway DB read-only, kept until Farjad Iranmehr approves deletion (date recorded when deleted). Owner: `cp-platform`. Evidence: variable *names* list + networking screenshot + 6.1 output.
- [ ] **6.8 Website moved or `pilot_request` copied, counts verified.** Website serves from the production host (DNS points there, test submission lands in the Canadian DB); during the write pause, Railway vs Canadian `pilot_request` count, `max(created_at)` and row digest are equal (backup plan §7.1); final full Railway dump `age`-encrypted and stored in Canada (S3 `cutover/` + cold copy). Owner: `cp-website` + `cp-database`. Evidence: the three values from both sides (no rows), DNS check, dump SHA-256.
- [ ] **6.9 Secrets rotated on cutover.** New host = new credentials: new DB passwords for every login role, new `SESSION_SECRET`, new bucket keys, new backup writer key; nothing copied from Railway, staging or local. Old Railway credentials revoked or the services stopped. Owner: `cp-platform`, `ciso` checks. Evidence: rotation log (names + dates, no values) per `docs/security/secrets-rotation.md`.

## 7. Recommended (waivable with expiry)

- [ ] TOTP (second factor) enabled for every internal user (ADR 0005 allows it).
- [ ] Commit author email switched to the GitHub `noreply` address for future commits (public repo).
- [ ] Uptime / error alerting to the incident contacts.

## Sign-off

| Role | Name | Decision (GO / NO-GO) | Date | Notes |
|---|---|---|---|---|
| `ciso` | | | | |
| `cp-qa` | | | | |
| CPO (`product-manager`) | | | | |
