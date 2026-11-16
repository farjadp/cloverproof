# Secrets inventory and rotation (SC-03)

- Status: draft, 2026-11-16. Owner: `ciso`. Applies to Railway (ADR 0004), app auth + Railway Bucket (ADR 0005), backups (`backup-restore-test-plan.md`).
- No real values anywhere in this file, in git, in tickets, chat or agent transcripts. Names and locations only.
- Source of truth for every value: Farjad Iranmehr's password manager (sealed Railway variables cannot be read back, see `railway-hardening.md` §4).

## 1. Inventory

"Holder" = who can read or change the value today. "Sealed" = Railway sealed variable (planned, `railway-hardening.md` §4; needs Farjad Iranmehr's OK).

| # | Secret | Where it lives | Used by | Holder | Sealed |
|---|---|---|---|---|---|
| S1 | `POSTGRES_PASSWORD` (superuser of the `postgis` service) | Railway variable on `postgis` | Operator one-offs only (`railway connect` / `railway ssh`) | Farjad Iranmehr | yes |
| S2 | `cp_app_login` password, inside `DATABASE_URL` of `app` | Railway variable on `app` (reference or literal) | FastAPI tool runtime | Farjad Iranmehr | yes |
| S3 | `cp_migrator_login` password, inside the migration `DATABASE_URL` | Railway variable on the `migrate` service only (never on `app`) | `make db-migrate` | Farjad Iranmehr | yes |
| S4 | `cp_website_login` password, inside `DATABASE_URL` of `website` | Railway variable on `website` (today: superuser reference, see hardening §5) | Next.js pilot-request insert | Farjad Iranmehr | yes |
| S5 | `cp_backup_login` password, inside `BACKUP_DATABASE_URL` | Railway variable on `backup` | Backup cron (`pg_dump`) | Farjad Iranmehr | yes |
| S6 | `cp_admin_login` password (if created) | Password manager only; never a Railway variable | Operator CLI (`make user-create`, membership changes) | Farjad Iranmehr | n/a |
| S7 | `SESSION_SECRET` (≥ 32 chars) | Railway variable on `app` | HMAC for per-session CSRF tokens and the signed org cookie (`S2-auth-review-step5.md`) | Farjad Iranmehr | yes |
| S8 | TOTP encryption key (planned, ADR 0005 "optional TOTP") | Railway variable on `app` | Encrypts `app_user` TOTP secrets | Farjad Iranmehr | yes |
| S9 | `BUCKET_ACCESS_KEY_ID` / `BUCKET_SECRET_ACCESS_KEY` (proof PDFs) | Railway variables on `app` (per environment) | `ProofStore` via boto3 | Farjad Iranmehr | secret key yes |
| S10 | Bucket read credentials on `backup` | Railway variables on `backup` | L4 PDF copy | Farjad Iranmehr | yes |
| S11 | Backup destination write keys (D1) | Railway variables on `backup` | Upload encrypted dumps/PDFs | Farjad Iranmehr | yes |
| S12 | Backup destination prune/delete key | Not on `backup`; separate job or lifecycle rule | Retention pruning | Farjad Iranmehr | yes |
| S13 | `age` private key for backups | Password manager + one offline copy. Never Railway, never git. `BACKUP_AGE_RECIPIENT` is the public key (not secret). | Restores only | Farjad Iranmehr (+ deputy per D6) | n/a |
| S14 | Railway account / workspace / project tokens | Railway dashboard; a project token, if CI ever needs one, as a GitHub Actions secret | CLI, automation | Farjad Iranmehr | n/a |
| S15 | GitHub tokens: personal access tokens, `gh` CLI OAuth tokens on laptops, any Actions secrets | GitHub account settings; local keychain | Pushes, PRs, `gh api` | Farjad Iranmehr and anyone with repo write | n/a |
| S16 | Account credentials + 2FA recovery codes (Railway, GitHub, backup destination, domain registrar) | Password manager | Account recovery | Farjad Iranmehr | n/a |

Not secrets (fine in `.env.example` names and in plain variables): `BUCKET_ENDPOINT`, `BUCKET_NAME`, `BUCKET_REGION`, `BACKUP_AGE_RECIPIENT`, cookie flags, environment name.

Rules
- `.env.example` holds names with empty values only (CLAUDE.md rule 10). Local `.env` is git-ignored and holds local-only values (local Docker PostGIS), never production values.
- Separate values per environment (production, staging, local). Never copy a production value into staging or `.env`.
- Never pass a secret in argv, a URL query, a log line or an error message. CLI tools read via `getpass` or env.
- The `gitleaks` job in `.github/workflows/security.yml` scans every push and, weekly, every branch.

## 2. Rotation triggers

| Trigger | What to rotate | Deadline |
|---|---|---|
| Suspected or confirmed leak (in git, a log, a screenshot, a chat, a lost laptop) | The leaked secret and anything it could read (e.g. a leaked `DATABASE_URL` → that login; a leaked Railway account token → everything in §1) | Immediately (§4) |
| Person with access leaves or changes role (staff, contractor, agent operator) | Every secret they could read: Railway workspace member → S1–S11, S14; GitHub write → S15 | Same day as access removal |
| Device lost / stolen / sold | GitHub tokens on it, Railway CLI token on it, password-manager session | Same day |
| Railway or GitHub security advisory affecting variables or tokens | As the advisory says | Per advisory |
| Scheduled | DB login passwords S2–S5, bucket keys S9–S11, Railway project tokens: every 90 days. `SESSION_SECRET`: every 180 days (forces fresh CSRF tokens). GitHub PATs: fine-grained, expiry ≤ 90 days. `age` key: only on leak or holder change (rotating means re-encrypting or keeping old private key for old dumps). | Calendar reminder |
| Before the first farmer-facing number (Step 7 release gate) | Anything that was ever set during development on a shared machine | Before go-live |

## 3. Rotation procedures

General order for every credential: **create new → deploy consumer with new → verify → revoke old.** Exception: on a confirmed leak, revoke first and accept the downtime (§4).

Every procedure ends with: update the password manager entry (date, reason), record the rotation in the security log (date, secret name, trigger, who; never the value).

### S1 `POSTGRES_PASSWORD` (superuser)
1. `railway connect` / `railway ssh` to `postgis`; `alter role postgres password '<new>';` typed in the psql prompt (use `\password postgres` so the value is not in history).
2. Update the `POSTGRES_PASSWORD` variable on `postgis`. **Verify first** whether the image re-reads it on restart (the official image only uses it at first init) and whether any reference variable (`${{postgis.DATABASE_URL}}`) depends on it; every service still referencing it redeploys.
- Impact: none for services once they use their own login roles (target state). Today `website` uses the superuser reference (hardening §5) → `website` redeploy, pilot form fails until it restarts (seconds).
- Verify: `psql` with the new password works, old fails; `website` health page and one test pilot request in staging.

### S2–S5 DB login roles (`cp_app_login`, `cp_migrator_login`, `cp_website_login`, `cp_backup_login`)
Zero-downtime option (preferred): create a second login in the same group role, switch, drop the old.
1. As an operator: `create role cp_app_login_2 login in role cp_app;` then `\password cp_app_login_2`.
2. Update the consumer's `DATABASE_URL` (sealed) to the new login; redeploy that service.
3. Verify (below), then `alter role cp_app_login nologin;` wait one deploy cycle, then `drop role cp_app_login;` (if it owns nothing; login roles should own nothing).
Simple option: `\password cp_app_login`, update the variable, redeploy. Running connections keep working; new connections with the old password fail until the redeploy finishes (seconds to a minute of errors on `app`).
- Impact: `app` restart drops in-flight requests; sessions survive (they live in `user_session`, not in memory). Migrator: none unless a migration runs at that moment. Backup: the next hourly run must succeed; check it.
- Verify: service healthy; `select usename, count(*) from pg_stat_activity group by 1;` shows only the new login for that service; old login cannot connect; for `backup`, the next dump + manifest appear at the destination.

### S6 `cp_admin_login`
`\password cp_admin_login` from a superuser session; update the password manager. No service impact.

### S7 `SESSION_SECRET`
1. Generate ≥ 32 random bytes locally (`python -c "import secrets; print(secrets.token_urlsafe(48))"` straight into the password manager; do not paste in chat or terminal history you keep).
2. Set the sealed variable on `app` (one environment at a time); redeploy.
- Impact (verify against `app/cloverproof_app` auth code when merged): every CSRF token and every signed org cookie becomes invalid. Open pages fail their next POST (403) until reloaded; the org selection is lost. Session tokens themselves are random and stored hashed in `user_session`, so **rotation alone does not log users out**.
- On a leak, also force logout: `update user_session set revoked_at = now() where revoked_at is null;` (column name per migration `0003_identity.sql`; check before running) → everyone logs in again.
- Verify: log in, switch org, submit a review in staging; an old CSRF token replayed against the new deploy gets 403.

### S8 TOTP encryption key (when built)
Needs key versioning in code (store `key_id` with each encrypted TOTP secret, decrypt with old, re-encrypt with new). Until that exists, rotation = re-enrol TOTP for every user. Flag for `cp-concierge-app` before TOTP ships.

### S9–S11 Bucket and backup-destination keys
1. Create a new key pair (Railway bucket credentials page / destination provider console). **Verify** whether Railway buckets allow more than one active credential; if not, rotation causes a short window where uploads fail.
2. Update the sealed variables on the consumer (`app` or `backup`); redeploy.
3. Revoke the old key.
- Impact `app`: PDF generation/download fails during the switch; PDFs are generated only after approval, so retry is safe (keys are content-addressed, never overwritten). Impact `backup`: one hourly run may fail; next run must catch up.
- Verify: generate and download a proof PDF in staging, hash matches `proof_document.sha256`; next backup run uploads; old key gets `AccessDenied`.
- After a bucket key leak, also compare the object list and every object's hash against `proof_document` (a leaked key may have deleted or overwritten).

### S13 `age` backup key
1. Generate a new key pair offline (`age-keygen`), store private key in the password manager + offline copy.
2. Set `BACKUP_AGE_RECIPIENT` on `backup` to the new public key; redeploy; check the next dump decrypts with the new key.
3. Keep the old private key as long as dumps encrypted with it are in retention (12 months), unless it leaked: then re-encrypt retained dumps or treat them as exposed (they contain PII: tell `legal-compliance-specialist`).

### S14 Railway tokens
Railway → account/workspace/project settings → tokens: create new (if still needed), update the GitHub Actions secret, delete the old one. Account tokens: delete, do not rotate, unless a named automation needs one. Verify: the automation runs; `railway whoami` with the old token fails.

### S15 GitHub tokens
GitHub → Settings → Developer settings → revoke the PAT / OAuth app authorisation; `gh auth logout` + `gh auth login` on each machine; update any Actions secret that held it. Verify: old token returns 401 on `gh api user`.

## 4. Emergency: secret committed to the public repo (or pushed anywhere public)

The repo is public. Once pushed, assume the value was harvested within minutes (automated scrapers). Purging history does not un-leak it.

1. **Revoke / rotate first** (minutes, not hours). Use §3 but in revoke-first order: kill the old credential even if a service goes down. For a DB URL: `alter role <login> nologin;` immediately, then rotate. For Railway account tokens: delete, then check Railway audit/activity for actions you did not do.
2. **Contain**: check what the secret could reach and look for use since the commit time: Postgres logs / `pg_stat_activity`, Railway activity, bucket object list vs `proof_document`, GitHub audit log.
3. **Notify** `ciso` and Farjad Iranmehr. If personal data may have been read (DB or backup credentials, bucket keys), `legal-compliance-specialist` decides on breach notification (PIPEDA and the farm's jurisdiction).
4. **Clean the tree**: remove the value in a normal commit; make sure `.gitignore` covers the file. Add a `gitleaks` allow rule only for confirmed false positives, never for a real secret.
5. **History purge: optional.** The value is already public and revoked, so rewriting history adds little security and breaks every clone and open PR. Do it only if Farjad Iranmehr decides (irreversible, force-push): `git filter-repo --replace-text`, then ask GitHub Support to drop cached views of the commit. Forks keep the old history regardless.
6. **Post-mortem** (short): how it got in, why `gitleaks` / push protection did not stop it. Enabling GitHub secret scanning + push protection on this public repo is open item A2 (`S2-auth-review-step5.md`).

## 5. Open items
- Seal the variables in §1 and record the "sealed" column as done (needs Farjad Iranmehr's OK, hardening §4).
- Verify: multiple active Railway bucket credentials; `POSTGRES_PASSWORD` re-read behaviour; reference variables resolving from sealed values.
- TOTP key versioning before TOTP ships (S8).
- D6: name the second holder of the `age` private key.
- Calendar reminders for the scheduled rotations (90 / 180 days).
