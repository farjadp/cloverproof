# Railway hardening checklist — project `cloverproof`

- Status: DRAFT for `ciso` review (2026-11-16). Desk review only: repo files + public Railway docs. No `railway` command was run, no dashboard or production DB was looked at, so every "Current" that depends on dashboard state says **unknown**.
- Scope: Railway project `cloverproof`, environment `production`. Services today: `Postgres` (Railway template), `website` (Next.js, pre-deploy `npm run db:migrate`). Planned: `postgis` (`postgis/postgis:17-3.5`, `docs/runbook-db-switch.md`), `app` (FastAPI), a Railway Bucket for proof PDFs (ADR 0005 B1).
- Threat that matters most: losing or silently changing recommendations, reviews or proof hashes (calibration dataset + evidence). Second: leaking pilot-request PII (name, email) from a public repo's infrastructure.
- Repo is public: assume every committed file, workflow and config is read by attackers.
- "Needs OK" = needs Farjad Iranmehr's explicit go (Railway setting change, new service, cost, access change). Nothing in this file has been applied.

Legend: **Current** = what the repo shows or "unknown" (dashboard state not checked). **Target** = what we want before production on 2027-02-01. **Owner** = who does it.

## 0. Top gaps (ranked)

| # | Gap | Why it ranks here | Fix (section) |
|---|---|---|---|
| 1 | No independent backup of the DB or proof PDFs. Railway buckets have no backups, versioning or object lock; volume backups restore only into the same project + environment and are deleted when the volume is wiped; the planned plain `postgis/postgis` image has no PITR. | Single failure (wrong delete, volume wipe, account compromise) loses the calibration dataset and evidence. | §8, `backup-restore-test-plan.md` |
| 2 | Credential separation is not built yet. Website writes `pilot_request` as the DB superuser (no website role in `db/migrations`); the `app` pre-deploy shares service variables with the runtime, so a migration/superuser URL there is readable by the running app; `cp_migrator` owns every table and can disable the immutability triggers. | One injection or leaked env var = full write/delete on immutable tables. | §5 |
| 3 | The planned `postgis/postgis:17-3.5` service has TLS off by default, no pgBackRest/PITR, and is outside Railway's database support scope. Enabling a TCP proxy on it (the runbook allows "one-off") would send superuser credentials in clear text over the internet. | Easy to do by accident during the DB switch. | §4, §6 |
| 4 | Account access unknown: members/roles, 2FA, API tokens, workspace SSH keys. 2FA enforcement needs the Pro plan; tokens keep working without 2FA. | Railway account = every secret, the DB and the backups. | §1–§3 |
| 5 | Deploy gate and logs: website has no CI (`ci.yml` ignores `website/**`), so "Wait for CI" cannot gate it; branch protection unknown; PR environments state unknown. `website/src/app/[lang]/actions.ts:48` logs the raw `pg` error, whose `detail` on a CHECK violation contains the whole failing row (name, email). | Unreviewed code reaches production; PII lands in logs we cannot purge. | §9, §10, §12 |

## 1. Project members and roles

| Item | Current | Target | Owner |
|---|---|---|---|
| Workspace roles (Admin / Member / Deployer) | unknown | Farjad Iranmehr = only Admin. Staff (≤3) = Member only if they need variables/logs; otherwise Deployer. Agents never get a Railway seat. | Farjad Iranmehr (Needs OK) |
| Project roles (Owner / Editor / Viewer) | unknown | Owner: Farjad Iranmehr. Editor: nobody by default (Editors can deploy and change settings and read variables). Viewer for read-only staff ("Viewers can not make deploys or see environment variables"). | Farjad Iranmehr (Needs OK) |
| Quarterly access review | none | List members + roles + last activity; remove leavers same day. File screenshot in `docs/security/evidence/`. | Farjad Iranmehr, reviewed by `ciso` |
| Audit logs | unknown | Admin-only; check before go-live and after any incident. | Farjad Iranmehr |

Sources: https://docs.railway.com/projects/project-members, https://docs.railway.com/projects/workspaces (Admin/Member/Deployer; "Only Admins can access audit logs").

## 2. Two-factor authentication

| Item | Current | Target | Owner |
|---|---|---|---|
| 2FA on Farjad Iranmehr's Railway account | unknown | On (authenticator app or passkey); recovery codes stored offline. | Farjad Iranmehr |
| 2FA on every member account | unknown | On. | each member |
| Workspace "Require 2FA" | unknown; **plan unknown** | On, if the workspace is on Pro. On Hobby it does not exist: then enforce by policy + quarterly check. | Farjad Iranmehr (Needs OK if a plan change) |
| 2FA on GitHub accounts with write access to `farjadp/cloverproof` | unknown | Required (Railway deploys whatever lands on `main`). | Farjad Iranmehr |

"2FA Enforcement is available on the Pro plan and above." Token access "remains valid without 2FA" → §3 matters even with 2FA on. Source: https://docs.railway.com/access/two-factor-enforcement

## 3. Railway API tokens and SSH keys

| Item | Current | Target | Owner |
|---|---|---|---|
| Account (personal) tokens | unknown | None long-lived. Broadest scope ("all your resources and workspaces"). Delete unused. | Farjad Iranmehr |
| Workspace tokens | unknown | None unless a named automation needs one. | Farjad Iranmehr |
| Project tokens | unknown | Only if CI needs Railway access; one per environment (they are "scoped to a specific environment within a project"), stored as a GitHub Actions secret, named after their use, rotated every 90 days. Today nothing in `.github/workflows/ci.yml` uses Railway → expect zero. | Farjad Iranmehr |
| Workspace SSH keys | unknown | None. Workspace keys "grant SSH access to every service in the workspace". Personal keys only, removed when not needed. | Farjad Iranmehr |
| Tokens in git | none found in repo | Keep it so; pre-commit secret scan (`security-engineer`). | `security-engineer` |

Revocation procedure is not in the API docs page — **verify** in the dashboard (Account → Tokens). Sources: https://docs.railway.com/integrations/api, https://docs.railway.com/cli/ssh

## 4. Environment variables and secrets

| Item | Current | Target | Owner |
|---|---|---|---|
| `DATABASE_URL` as reference variable | yes for `website` (ADR 0004: `${{Postgres.DATABASE_URL}}`) | Keep references; no credential copied by hand between services. After the switch: `website` → website role URL, `app` → `cp_app_login` URL (§5). | `cp-platform` |
| Sealed variables | unknown | Seal: `POSTGRES_PASSWORD` (postgis), login-role passwords, `SESSION_SECRET`, TOTP encryption key, `BUCKET_SECRET_ACCESS_KEY`, backup-destination keys. Sealed values are not shown in UI/API/CLI and "are not copied over when creating PR environments". They "cannot be un-sealed" → keep the source value in Farjad Iranmehr's password manager. **Verify** that a reference variable built from a sealed variable still resolves (e.g. `DATABASE_URL` built from sealed `POSTGRES_PASSWORD`). | Farjad Iranmehr (Needs OK: setting change) |
| Shared variables | unknown | Only non-secrets (e.g. `BUCKET_REGION`). Secrets per service so each service sees only what it needs. | `cp-platform` |
| Migration credential not in app runtime | n/a yet | Pre-deploy runs "in a separate container" but with the service's variables, so any URL set on `app` is visible to the running app. Target: the owner/migration URL lives only on a separate service or is used by an operator; `app` holds only `cp_app_login` (§5). | `cp-platform`, `cp-database` |
| `.env.example` | present, values should be empty (not opened in this review — permission denied) | **Verify** all values empty. | `security-engineer` |
| Variables at build time | Railway passes variables to builds | Never print env in build logs; Next.js `NEXT_PUBLIC_*` only for non-secrets. | `cp-website` |

Sources: https://docs.railway.com/variables, https://docs.railway.com/deployments/pre-deploy-command

## 5. Database roles (least privilege)

What `db/migrations` does today (0002–0009):
- `cp_migrator` (NOLOGIN) creates and **owns** every app table; `cp_app` (NOLOGIN) gets grants.
- `cp_app`: SELECT/INSERT only on `recommendation`, `review`, `proof_document`; SELECT on `recommendation_diff`; full CRUD on `organisation`, `app_user`, `user_session`, `membership`, `farmer`, `farm`, `field`, `season`, `field_geometry_version`, `soil_test`, `soil_test_value`, `crop_plan`, `application_log`.
- Immutability: BEFORE UPDATE/DELETE/TRUNCATE triggers (`forbid_change`) on the three immutable tables.
- `pilot_request` (0001): **no grants at all** → only its owner or a superuser can write it. Today the website connects as the Railway template's superuser.
- Login roles are created outside git (`create role cp_app_login login password '...' in role cp_app;`). Good.

| Role | Current | Target | Owner |
|---|---|---|---|
| Bootstrap (superuser `postgres`) | used by website runtime + website pre-deploy; runbook uses it for `make db-migrate` | Used only by an operator for 0002 (needs superuser for `create extension postgis` and `create role`) and for creating login roles. Never set on a long-running service except `postgis` itself. | Farjad Iranmehr / `cp-database` |
| Migration login `cp_migrator_login` (new, `in role cp_migrator`) | does not exist | Runs migrations 0003+ (they all start with `set local role cp_migrator`). Lives only where migrations run (§6). Needs `select, insert on schema_migrations` (0002 grants it to `cp_migrator`). | `cp-database` |
| App runtime `cp_app_login` | planned in runbook | `app` service `DATABASE_URL` points here, never at the superuser. Tighten: `membership` → SELECT only for `cp_app` (today the app can grant itself `agronomist` and then pass the approval trigger); membership changes via CLI under the migration/admin login. | `cp-database` (migration 0010+) |
| Website `cp_website_login` (new role `cp_website`) | missing — website uses superuser | `grant insert on pilot_request to cp_website` (the insert has no RETURNING, so INSERT only; no SELECT). Needs a new migration + operator-created login. | `cp-database` + `cp-website` |
| Backup `cp_backup_login` (new) | missing | `login`, member of `pg_read_all_data` (PG 14+), nothing else. Used only by the backup job. **Verify** in the drill that `pg_dump` succeeds with it (it takes ACCESS SHARE locks). | `cp-database` |
| Owner can disable triggers | `cp_migrator` owns tables → can `alter table ... disable trigger` | Accept (needed for migrations) but: migration credential not on the app service; schema changes only via reviewed migration files; drill verification §V3 checks triggers are enabled. | `cp-database`, `ciso` |

Note: the current `Postgres` template database before the switch: whatever grants exist there are **unknown** (not inspected; no prod connection allowed).

## 6. Database network exposure (Postgres / PostGIS)

| Item | Current | Target | Owner |
|---|---|---|---|
| `Postgres` template TCP proxy | unknown. Docs: "Databases are deployed private by default"; public access = TCP proxy, which sets `DATABASE_PUBLIC_URL`. Older projects may differ. | Off. Check: no `DATABASE_PUBLIC_URL` variable and no TCP proxy under Settings → Networking. | Farjad Iranmehr (check: read-only) |
| `postgis` TCP proxy | runbook: "No public TCP proxy unless needed for a one-off migration" | **Never** on this image: TLS is not configured in `postgis/postgis` (upstream default `ssl=off`), so a proxy would expose plaintext auth. Remove the "unless needed" clause from the runbook. | `cp-database` (runbook edit) |
| How migrations run without a public proxy | website: pre-deploy (works). app: not built | Pre-deploy commands "execute within your private network and have access to your application's environment variables" → migrations can run there. Because of §4, preferred: a small `migrate` service (same repo, start command `make db-migrate`, holds `cp_migrator_login`, no public domain), deployed before `app`; `app` refuses to boot if `schema_migrations` lags the files on disk. Operator one-offs (0002, login roles): `railway connect` "automatically tunnels over SSH" when no TCP proxy exists, or `railway ssh` into `postgis` and run `psql` locally. | `cp-platform`, `cp-database` |
| Service-to-service traffic | private DNS `*.railway.internal` | All DB traffic over private networking ("All inter-service communication uses Wireguard encryption"). | `cp-platform` |
| PostGIS image choice | `postgis/postgis:17-3.5` (runbook) | Option to evaluate (**verify**): build our own image `FROM` Railway's `postgres-ssl:17` and `apt-get install postgresql-17-postgis-3`. Keeps Railway's TLS and dormant pgBackRest (PITR) — the stock Railway image ships pgvector + pgaudit but **not** PostGIS. Whether Railway's PITR feature accepts a derived image is not documented. Decision for Farjad Iranmehr. | `cp-platform` proposes |

Sources: https://docs.railway.com/databases/postgresql, https://docs.railway.com/networking/tcp-proxy, https://docs.railway.com/networking/private-networking, https://docs.railway.com/deployments/pre-deploy-command, https://docs.railway.com/cli/connect, https://docs.railway.com/cli/ssh, https://github.com/railwayapp-templates/postgres-ssl, https://docs.railway.com/databases (support scope: changing the image takes the DB out of Railway's support scope).

## 7. TLS

| Item | Current | Target | Owner |
|---|---|---|---|
| Public HTTPS for `website` / `app` | Railway domains; details of cert issuance and HTTP→HTTPS redirect not confirmed in docs read | **Verify** in https://docs.railway.com/networking/domains: auto certs, redirect. App sets `Secure` cookies (ADR 0005) and HSTS. | `cp-platform` |
| `app` public exposure | n/a | Internal tool for ≤4 users: one Railway domain or custom subdomain, login required on every route except `/healthz`. | `cp-concierge-app` |
| DB connections | private network (Wireguard) | No `sslmode` needed on private network; mandatory `sslmode=verify-full`-class settings if anything ever connects over a proxy (should not happen, §6). | `cp-platform` |
| Bucket (S3 API) | HTTPS endpoint (assumed) | **Verify** the bucket endpoint is HTTPS-only. | `cp-platform` |

## 8. Bucket (proof PDFs)

| Item | Current | Target | Owner |
|---|---|---|---|
| Privacy | not created | Private is the only option ("Public buckets are currently not supported"). Serve PDFs through the app (auth-checked) or short-lived presigned URLs (≤5 min). | `cp-pdf`, `cp-concierge-app` |
| Credentials scope | not created | Docs: "Each environment gets its own separate bucket instance with isolated credentials." Read-only or write-only keys are not documented → assume the app key can delete. **Verify** whether scoped keys exist. Seal `BUCKET_SECRET_ACCESS_KEY` (§4). | `cp-platform` |
| Write-once | ADR 0005: app never overwrites a key; key contains the SHA-256 | Railway buckets do **not** support versioning, object lock, lifecycle or server-side encryption. Write-once is app-enforced only → independent copy is mandatory (backup plan §3). | `cp-pdf` |
| Deletion | n/a | A deleted bucket "stays restorable for 52 hours". Treat bucket deletion as a P1 incident. | Farjad Iranmehr |
| Region | n/a | Fixed at creation; create it in the same region as `postgis` (§13). | Farjad Iranmehr (Needs OK: new resource/cost) |
| Backups | none | "Railway doesn't currently offer automatic backups or snapshots for buckets." → backup plan §3. | `cp-database` |

Sources: https://docs.railway.com/storage-buckets, https://docs.railway.com/storage-buckets/billing

## 9. Deploy from GitHub

| Item | Current | Target | Owner |
|---|---|---|---|
| Trigger branch | `website` from `main`, watch path `/website/**` (ADR 0004) | `main` only for `production`. `app` watch paths: `/app/**`, `/engine/**`, `/packs/**`, `/db/migrations/**`, `/pyproject.toml`, `/uv.lock`. | `cp-platform` |
| Who can trigger | anyone who can push/merge to `main` | Autodeploy needs "at least one project member [with] a connected GitHub account with contributor access"; Deployer-role authors skip approval. Branch protection on `main`: PR required, 1 approval, required checks, no force-push, no bypass for admins — **unknown today** (not checked; GitHub settings out of scope of this desk review). | Farjad Iranmehr (Needs OK) |
| Wait for CI | unknown | On for `app` (ci.yml runs on push for non-website paths). For `website`: on `main` today no workflow runs on `website/**` → no check suite → nothing to wait for. The uncommitted `.github/workflows/security.yml` (parallel S2 work) runs on every push, so once merged "Wait for CI" would gate website deploys on the secret/dependency scan only. Add a `website` CI job (lint + `next build`) as well. | `cp-platform`, `cp-website` |
| Pre-deploy migrations | `website`: `npm run db:migrate` as superuser | Remove after the PostGIS switch (runbook step 4.2). `app`: §6. | `cp-website`, `cp-database` |
| GitHub Actions permissions | `permissions: contents: read`, pinned to major tags (`@v7`) | Keep read-only. Consider pinning actions to SHAs (public repo, supply chain). | `security-engineer` |

Source: https://docs.railway.com/deployments/github-autodeploys

## 10. PR environments

| Item | Current | Target | Owner |
|---|---|---|---|
| PR environments | unknown | **Off** until a `staging` environment exists. Then base PR environments on `staging`, not `production`, so they never inherit production variables or data. Bot PR environments off. | Farjad Iranmehr (Needs OK) |
| Fork PRs (public repo) | n/a | Railway "will not deploy a PR branch from a user who is not in your workspace or invited to your project". Keep it so. Whether a PR environment gets its own empty database or references the base one: **verify**. | `cp-platform` |
| Domains | n/a | PR services get domains only if the base services use Railway domains — acceptable on staging; must not expose production data. | `cp-platform` |
| Environment RBAC | n/a | Enterprise only; not available to us. | — |

Source: https://docs.railway.com/environments

## 11. Health checks and uptime

| Item | Current | Target | Owner |
|---|---|---|---|
| `website` | `/en` deploy-time health check | Keep. Railway calls it "only ... at the start of the deployment" and "does not monitor the healthcheck endpoint after the deployment has gone live". | `cp-website` |
| `app` | n/a | `/healthz`: DB reachable + migrations current; returns no version details or errors. Allow host `healthcheck.railway.app`. | `cp-concierge-app` |
| Continuous uptime | none | Scheduled GitHub Actions job (free, no new vendor) curling `/en` and `/healthz` every 15 min, failing loudly; or an external monitor (new vendor → Needs OK). | `cp-platform` |
| Backup job health | none | Backup job alerts on failure (backup plan §6). | `cp-database` |

Source: https://docs.railway.com/deployments/healthchecks

## 12. Logs

| Item | Current | Target | Owner |
|---|---|---|---|
| PII in logs | `website/src/app/[lang]/actions.ts:48` `console.error("requestPilot failed", error)` prints the `pg` error object; on a CHECK violation its `detail` is "Failing row contains (...)" with full name and email. | Log `error.code` / `error.constraint` and a request id only. Same rule for `app`: never log request bodies, form values, emails, tokens, `DATABASE_URL`. | `cp-website`, `cp-concierge-app` |
| Secrets in logs | migration runners do not print the URL (good) | Keep; never `env` / `printenv` in build or start commands. | all |
| Retention | plan unknown: Hobby 7 days, Pro 30 days | Enough for ops; not an audit trail. Audit trail lives in DB rows (review, recommendation). No log drain setting exists in Railway; forwarding would be a new vendor (Needs OK). | `ciso` |
| Who can read logs | Deployer role cannot view logs; other roles: **verify** | Restrict per §1. | Farjad Iranmehr |
| Rate limit | 500 lines/s per replica | Irrelevant at our volume. | — |

Source: https://docs.railway.com/observability/logs, https://docs.railway.com/projects/workspaces

## 13. Region and data residency

| Item | Current | Target | Owner |
|---|---|---|---|
| Region of each service | unknown ("default region", ADR 0004) | Record region per service. Railway regions: US West (California), US East (Virginia), EU West (Amsterdam), Southeast Asia (Singapore); **no Canadian region**. Put `postgis`, `app`, bucket and backup storage in one documented region. | Farjad Iranmehr |
| Moving later | n/a | Moving a service with a volume means a volume migration "with downtime"; bucket region cannot change → decide before creating `postgis` and the bucket. | Farjad Iranmehr (decision) |
| Privacy notice / DPA | unknown | Pilot farms and pilot requests: tell people where data is stored (PIPEDA allows cross-border transfer with notice; GDPR for EU contacts). Railway offers a self-service DPA (railway.com/legal/dpa). Railway is SOC 2 Type II. Encryption at rest for volumes is **not stated** in the docs read → verify via Railway Trust Center. | `legal-compliance-specialist`, Farjad Iranmehr signs DPA |

Sources: https://docs.railway.com/deployments/regions, https://docs.railway.com/enterprise/compliance

## 14. Egress

| Item | Current | Target | Owner |
|---|---|---|---|
| Outbound filtering | none documented (Railway offers static outbound IPs, not an egress firewall) | Accept. Keep dependencies minimal; app makes no outbound calls except the bucket and backup destination. | `ciso` |
| SMTP | Pro only | Not needed (ADR 0005: no email sending). | — |
| DB egress | private network | Public TCP proxy is billed egress and an exposure → stays off (§6). | — |

Source: https://docs.railway.com/networking/outbound-networking

## 15. Cost alerts

| Item | Current | Target | Owner |
|---|---|---|---|
| Soft limit (email alert) | unknown | Set a Compute email alert at ~1.5× the current monthly bill (estimate; read current bill first). Harmless: it "doesn't affect running services". | Farjad Iranmehr (Needs OK) |
| Hard limit | unknown | **Do not set** during the pilot, or set far above the alert: at the hard limit Railway will "shut down your workloads" — an outage of the evidence system for a billing reason. | Farjad Iranmehr (decision) |
| Agent hard limit | default $5 (Hobby) / $20 (Pro) | Leave default. | — |
| Billing failure | unknown | Card on file valid through 2027-06; Farjad Iranmehr gets billing emails. | Farjad Iranmehr |

Source: https://docs.railway.com/pricing/cost-control

## 16. Before go-live (2027-02-01) — order of work

1. Farjad Iranmehr: read-only dashboard inventory for §1–§3, §6 (TCP proxy), §13 (regions), §15, plan tier. Screenshot into `docs/security/evidence/` (no secret values visible). 30 min.
2. Decisions (below), then the DB switch with the runbook edits from §5/§6.
3. `cp-database`: migration for `cp_website`, `cp_backup`, `membership` tightening; operator creates login roles.
4. `cp-platform`: `migrate` service or equivalent, `app` service config, `website` CI job, uptime job, backup job.
5. `cp-website`: remove superuser use + PII-safe error logging.
6. First restore drill (backup plan §5) before any pilot data exists.

## Decisions needing Farjad Iranmehr

1. Plan tier: stay on Hobby (no 2FA enforcement, 7-day logs) or Pro.
2. PostGIS image: plain `postgis/postgis:17-3.5` (no TLS/PITR, simple) vs. own image on Railway `postgres-ssl` + PostGIS (TLS + possible PITR, we maintain a Dockerfile).
3. Region for `postgis`, bucket and backups (fixed once created).
4. Migration path: separate `migrate` service (recommended) vs. pre-deploy on `app` with the owner URL readable by the app.
5. PR environments: off until `staging` exists (recommended).
6. Cost alert amount; no hard limit.
7. Backup destination and new-vendor question: see `backup-restore-test-plan.md` §2.
