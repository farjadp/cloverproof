# ADR 0009 — Production hosting in Canada (data residency)

- Status: **Accepted — interim Railway; Canadian host decision due 2027-01-04; migration S4** (Farjad Iranmehr, 2026-11-16: "Railway now, Canada later"). No paid service, account or contract is approved by this ADR; the host choice (D recommended, C runner-up) and its spend need his go by Jan 4.
- Decision on residency taken by Farjad Iranmehr (2026-11-16): real farmer data must be stored in Canada. The provider choice is deferred to 2027-01-04 (see Decision).
- Decider: Farjad Iranmehr. Authors: `system-architect` for `cto` + `devops-engineer`; review: `ciso`, `coo`.
- Related: ADR 0004 (Railway), ADR 0005 (auth + Railway Bucket), ADR 0006 (SoilGrids cache), ADR 0007 (DB privileges), ADR 0008 (RLS, reserved); `docs/operations/legal/data-residency-input.md` (OQ-06); `docs/security/backup-restore-test-plan.md`; `docs/runbook-db-switch.md`; `docs/plans/backend-plan.md` §4, §12, §14.

## Context
- **Decision (Farjad Iranmehr, 2026-11-16): real farmer data must be stored in Canada.** This replaces Option A ("stay on Railway US") in `data-residency-input.md` §5. Railway has no Canadian region (ADR 0004; regions: US West, US East, EU West, Southeast Asia). **Until this ADR is decided, hosted environments hold synthetic or de-identified data only.**
- What must move: Postgres + PostGIS (all farmer, soil, plan, review and proof tables, sessions), the proof-PDF bucket (write-once evidence, SHA-256 in `proof_document`), the Procrastinate worker (S4; reads the DB, renders PDFs), the backups (Railway volume backups/PITR, planned `age` dumps — `backup-restore-test-plan.md` L1–L4), and the app process itself (it holds data in memory and in logs).
- **Website:** `pilot_request` (name, email, notes, consent) is in the same database (`runbook-db-switch.md` §3, `cp_website` INSERT-only role). Pilot applicants are prospective farmers → their rows must be stored in Canada too. See "What stays on Railway".
- Scale: 5–10 farms in 2027, DB < 1 GB, hundreds of ~200 KB PDFs, 1 internal user, farmer accounts from S9. Team of 1–2: the ops burden matters more than the price.
- Deadline: the S5 rehearsal (Jan 18–29, 2027) enters **3 real farms** → production must be in Canada **before Jan 18**, not just before the Jan 29 gate.
- Repo facts to carry: local dev and CI run `postgis/postgis:18-3.7`, matching the Railway service `PostGIS-cXKk`, so **Postgres 18 is already the baseline** (no upgrade decision needed). All managed options below offer 18 except E (Fly.io); their listed PostGIS is 3.6.x (3.7 not confirmed on any), a minor-version gap to check in the staging build. Migration `0002_roles_and_extensions.sql` assumes a **superuser** deploy user (creates `cp_migrator`/`cp_app`, `create extension postgis`, `set role cp_migrator`); no managed service gives a true superuser (RDS `rds_superuser`, Cloud SQL `cloudsqlsuperuser`, Azure `azure_pg_admin`, DO `doadmin`). Expect small changes to 0002-style grants and to the backup role's `pg_read_all_data` grant.
- Law (from `data-residency-input.md`, not legal advice): PIPEDA does not require residency; storage in Canada with a US-owned provider is still reachable under the US CLOUD Act. Only a non-US-owned provider changes that.

## Decision (Farjad Iranmehr, 2026-11-16): "Railway now, Canada later"
1. **Now through S3 (to Jan 1, 2027):** staging and the concierge build stay on Railway, using the approved Railway Bucket, worker and `staging` environment. Hosted environments hold **synthetic or de-identified data only**, plus the website pilot form with its disclosed interim US storage.
2. **Canadian host chosen by 2027-01-04 (S4 start).** Option D (DigitalOcean TOR1) stays the recommendation, C (Google Cloud Toronto/Montréal) the runner-up; the choice itself is deferred to that date.
3. **Production migrates to the Canadian host in S4** (planned work; backlog `S4-PLT-01`, traceability AR-17 / SC-08), finished before the first real farmer's data. The S5 rehearsal enters real farms from Jan 18, so the cutover must be done by **Jan 15**, ahead of the Jan 29 gate.
4. **Build portable now** so S4 is a redeploy, not a rewrite: plain Postgres + PostGIS (no Railway-specific extensions or DB features), S3-compatible bucket API behind `ProofStore`, a Dockerfile for every service, configuration through env vars only, migrations through `make db-migrate`. **No Railway-only features** (e.g. Railway-specific variable references in app code, Railway-only cron or volumes as data stores).

## Options compared
Prices: USD list, before tax, accessed 2026-11-16; monthly = hourly × 730. "Est." = my estimate from listed unit prices, not a quote. "Unverified" = not confirmed on an official page. RDS PITR (35 days), S3 Object Lock and Azure Blob immutability are standard documented features, not re-fetched today.

| Criterion | **A. AWS ca-central-1** (Montréal) + ca-west-1 (Calgary) | **B. Azure Canada Central** (Toronto) / East (Québec) | **C. Google Cloud** northamerica-northeast2 (Toronto) / -northeast1 (Montréal) | **D. DigitalOcean TOR1** (Toronto) | **E. Fly.io yyz** (Toronto) | **F. OVHcloud BHS** (Beauharnois, QC) |
|---|---|---|---|---|---|---|
| DB service | RDS for PostgreSQL | Flexible Server | Cloud SQL (Enterprise) | Managed PostgreSQL | Managed Postgres (MPG) | Public Cloud Databases |
| Postgres 18 | Yes (18.6) [S1] | Yes [S5] | Yes [S9] | Yes, Standard edition [S13] | **No** — 16 or 17 only, no in-place upgrade [S17] | Yes (14–18) [S19] |
| PostGIS | 3.6.3 on 18.6; 3.5.6 on 17.11 [S1] | 3.6.1 on 17/18 [S5] | 3.6.0 on 18; 3.5.2 on 17 [S9] | Yes on Standard, **not** on Advanced edition; version not stated [S13] | Yes, "if enabled when provisioning" [S17] | Listed in extensions guide [S20]; per-region not confirmed |
| App + worker (Docker from GitHub) | App Runner **closed to new customers since 2026-04-30** [S3]; ECS Express Mode = Fargate + ALB [S4]; or Lightsail containers $7/$10 [S2] | Container Apps (consumption) | Cloud Run (both regions listed, Tier 2) [S10]; always-on worker needs min-instance or worker pool | App Platform, dynamic apps in TOR1 [S14]; $5/mo smallest container [S15]; workers + pre-deploy jobs | Machines, deploy via `fly deploy` | No container PaaS; Managed Kubernetes or VMs [S21] |
| Est. DB / month | db.t4g.micro $0.018/h ≈ $13 + 20 GB gp3 ≈ $2.5 [S0] | B1MS $0.0185/h ≈ $13.5 + storage (min 32 GiB, unverified price) [S6] | db-f1-micro ≈ $0.0198/h ≈ $14.5 (third-party listing) [S11] + SSD | from $15.15 (1 GiB, 10–30 GiB) [S16] | Basic $38 + $0.28/GB [S17] | Essential db1-4 ≈ $0.0864/h ≈ $63 (third-party) [S22] |
| Est. app + worker + website | Lightsail: ~$24–27 (incl. LB/TLS); ECS: Fargate 0.25 vCPU/0.5 GB ≈ $10/task ($0.04456/vCPU-h, $0.004865/GB-h) [S0] ×3 + ALB → ~$45–55 | ~$15–30 (consumption; worker always on) [S6] | ~$15–40 (app/website scale to zero; worker always on) | ~$15–30 ($5–12 per component) | ~$10–15 | VM/K8s, ~$20–40 + own ops |
| Bucket, write-once | S3 $0.025/GB-mo [S0]; **Object Lock** (compliance mode) | Blob immutable storage (WORM policies) | GCS **Object Retention Lock** "Locked permanently prevents the retention date from being reduced" [S12] | Spaces in TOR1 [S14], $5/mo; versioning yes; **Object Lock not found** [S18] | Tigris (global; Canadian pinning unverified) | Object Storage S3 API; object lock documented [S23] |
| **Est. total / month** | **$40–75** | **$35–55** | **$35–60** | **$35–50** | n/a (no PG 18; bucket residency unclear) | **$85–110** |
| Backups / PITR | Automated, PITR up to 35 days, same region; cross-region copy can stay in Canada (ca-west-1) | Automated + PITR (retention 7–35 days, unverified for our tier); backup LRS $0.105/GB [S6] | 1–365 backups [S9b]; **default backup location = nearest multi-region, i.e. outside Canada unless a custom Canadian location is set** [S9c] | PITR "limited to the last 7 days" [S13b]; backup location **unverified** | Automatic; retention/PITR not stated [S17] | Daily; 2 days (Essential), 14 (Business) [S19]; PITR not stated |
| Private networking | VPC; Lightsail ↔ RDS via VPC peering | VNet integration | Cloud SQL connector / private IP | VPC + DB trusted sources (App Platform VPC: unverified) | 6PN private network | vRack on all plans [S19] |
| Encryption | At rest (KMS) + TLS | At rest + TLS | At rest + TLS | Unverified on fetched pages | Unverified | TLS in transit [S19]; at rest unverified |
| Ops burden (1–2 people) | **High** (IAM, VPC, ALB/Lightsail, CloudWatch) | Medium–high | Medium (Cloud Run ≈ Railway; IAM + org policy) | **Low** (closest to Railway: GitHub → Dockerfile, env vars, pre-deploy job) | Low, but MPG young | **High** (no PaaS) |
| Lock-in | Low–medium (S3 API, plain PG) | Medium | Low–medium | Low (plain PG, S3 API) | Low | Low |
| Legal entity / DPA | US parent; DPA in service terms; Canadian contracting entity to confirm | US parent; Microsoft DPA | US parent; Cloud DPA (CDPA) | US parent (DigitalOcean LLC); online DPA | US parent | **French parent**, Canadian subsidiary — lowest US-law exposure (not researched in depth) |
| Egress | ~$0.09/GB, negligible at our size | negligible | negligible | generous allowance included | included allowance | included |

Not compared further: **Canadian-owned providers** (ThinkOn, Canadian Web Hosting) — no self-serve managed Postgres with PostGIS found; enterprise IaaS only (not verified, quota ran out). **Hybrid** (app on Railway US, DB in Canada): meets "stored in Canada" literally, but needs a public DB endpoint for Railway, adds ~15–30 ms per query across the border and keeps processing + logs in the US. Rejected.

## Recommendation (for the 2027-01-04 choice)
**Option D — DigitalOcean TOR1** (App Platform for `app`, `worker` and `website`; Managed PostgreSQL 18 Standard edition with PostGIS; Spaces TOR1 for proof PDFs), **plus the offsite backup copy (backup plan L3/L4, D1) in AWS S3 ca-central-1 with Object Lock (compliance mode).**
1. Lowest ops burden for 1–2 people: App Platform is the closest match to Railway (GitHub build from Dockerfile, env vars, pre-deploy job for `make db-migrate`, worker components). Cutover fits in one sprint.
2. All three needed services are listed for TOR1 [S14]; Postgres 18 + PostGIS available [S13]; cost ≈ $35–50/month.
3. The S3 Object Lock copy closes D's two gaps: no confirmed object lock on Spaces, and PITR only 7 days. It also protects against a compromise of the DO account (a second vendor, `backup-restore-test-plan.md` D1). Cost: cents.
4. Runner-up: **C (Google Cloud Toronto + Montréal)** if Farjad prefers one large vendor with native WORM storage and longer backups; it costs a little more and needs IAM work, and its backup location **must** be set to a Canadian region.

**Main risk:** DigitalOcean has not confirmed in writing that managed-DB backups, PITR WAL and App Platform logs stay in Canada (not on the pages I could fetch). If DO cannot confirm in writing before the Jan 4 choice, choose C. Second risk for every option here: all are US-owned (CLOUD Act). "Stored in Canada" ≠ "out of reach of US law". Say so in the privacy notice (§7).

## What stays on Railway
- **Website: moves too** (to App Platform TOR1, same app spec). Keeping it on Railway would need a public, IP-allow-listed DB endpoint for `pilot_request` PII and would keep processing + logs of that PII in the US. Moving costs ~$5–12/month and keeps the DB private.
- **Nothing with real data.** Railway may keep a **sandbox/preview environment with synthetic data only** until Farjad decides to close the account. The **staging** environment moves to TOR1 too (S5 requires "staging = production config").
- Old Railway `Postgres` service: kept until Farjad approves deletion (≥ 1 week after cutover, final `pg_dump` saved in Canada; `runbook-db-switch.md` §5). Until the S4 cutover, the Railway `PostGIS-cXKk` service and the Railway Bucket (ADR 0005 B1) serve staging and the build with synthetic data only; they are not used for real farmer data.
- Out-of-Canada processors that remain, to minimise not move: Sentry free tier (US/EU, scrub PII), GitHub Actions (synthetic data only), AI reviewer (de-identified only, D-7), future email provider.

## Consequences
- ADR 0004 is superseded for production hosting and ADR 0005 B1 (Railway Bucket) is replaced by Spaces TOR1. `ProofStore` and the S3 API stay the same; only `BUCKET_*` values change.
- New env vars: none new; `DATABASE_URL`, `BUCKET_*`, `SESSION_SECRET` move to App Platform (encrypted env). Add `BACKUP_DEST_*` for the S3 Object Lock copy (empty in `.env.example`).
- `make db-migrate` runs as an App Platform pre-deploy job using `doadmin`-derived deploy role; migration 0002 needs a no-superuser path (`cp-database`): role creation + `grant cp_migrator to <deploy user> with set true`; verify `create extension postgis` and the `pg_read_all_data` grant on DO. RLS (ADR 0008) and role split (ADR 0007) are plain Postgres and carry over unchanged.
- Local dev and CI already run `postgis/postgis:18-3.7` (Postgres 18, same as Railway `PostGIS-cXKk`), so local = production on the major version; the only gap is PostGIS minor (3.7 locally vs 3.6.x listed on the managed services), checked in the staging build.
- `backup-restore-test-plan.md` L1/L2 (Railway volume backups/PITR) are replaced by DO daily backups + 7-day PITR; L3/L4 stay (hourly `age` dump + PDF copy) with destination S3 ca-central-1 Object Lock. Drills A/B are re-run on DO.
- Privacy notice §6–7: "stored in Canada (Toronto) with DigitalOcean, a US company; may be accessible to US authorities"; list Sentry/AI provider as out-of-Canada processors.

## Migration plan (outline)
Hosted environments hold no real farmer data yet, so this is mostly a **fresh build + copy of `pilot_request`**, not a data migration.
| When | Step | Owner |
|---|---|---|
| Now – Jan 1 (S1–S3) | Stay on Railway (staging, Bucket, worker); synthetic/de-identified data only; keep every service portable (Decision §4). DO written answers on backup/log location requested. `cp-database`: no-superuser migration path, tested on PG 18 + PostGIS locally (`postgis/postgis:18-3.7`) | `cp-platform`, `devops-engineer`, `cp-database` |
| By Jan 4 (S4 start) | Farjad chooses D or C and approves spend; creates accounts; signs/accepts DPAs after counsel review | Farjad Iranmehr |
| Jan 4–8 (S4) | Build staging + production in the chosen Canadian region (app, worker, website, DB, bucket); migrations; RLS tests; synthetic seed; DB has no public ingress; offsite Object Lock backup job live; restore drill | `cp-platform`, `cp-database` |
| Jan 11–15 (S4, window) | Pause website writes → copy `pilot_request` from Railway (`pg_dump --data-only`) → verify counts → switch DNS → test submission | `cp-website`, `cp-platform` |
| By Jan 15 | Fill `[RAILWAY REGION]`/residency text in notice; security review of new setup (release-gate checklist) | `ciso`, `coo` |
| From Jan 18 (S5) | First real farm data, Canada only | Farjad Iranmehr |

**Rollback:** until real farm data exists, roll back = point DNS back at the Railway website + old Railway `Postgres` (kept untouched, read-only). After real farm data exists, there is **no rollback to Railway** (it would break residency): roll forward on DO, or restore the latest `age` dump into option C.

## Needs Farjad Iranmehr's go (none done)
1. **By 2027-01-04:** choose D (recommended) or C; approve the ~$35–50/month spend (paid service rule).
2. Create the DigitalOcean account/team (and the AWS account for the Object Lock backup bucket); billing card; MFA on both.
3. Accept/sign each provider's DPA after counsel review; save a dated copy.
4. Approve moving the website off Railway and, later, deleting the Railway `Postgres` service.

## Questions for `ciso` / `coo`
1. DPA: does DO's DPA name Canada-specific storage, sub-processors with locations, deletion deadline and backup expiry (same gaps as Railway D3/D6/D7)?
2. Breach notice: what clock does the provider commit to (we need enough to assess RROSH under PIPEDA s. 10.1)?
3. Backups: confirm in writing that DB backups, PITR WAL and App Platform/build logs stay in Canada; is the S3 ca-central-1 copy acceptable as the offsite location (Canada, second US vendor)?
4. Is Sentry (US/EU) acceptable with PII scrubbing, or must errors stay in Canada?
5. Do partners (co-ops, lenders) need a non-US-owned provider (only F avoids CLOUD Act reach)? If yes, re-open this ADR.
6. Backup retention for erasure (ER-30): max age of DO backups + our dumps to state in the notice.

## Sources (all accessed 2026-11-16)
- S0 AWS Price List API, ca-central-1: AmazonECS (Fargate; pub. 2026-11-11) https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/ca-central-1/index.json; AmazonS3 (pub. 2026-11-16) …/AmazonS3/current/ca-central-1/index.json; AmazonRDS (via `data-residency-input.md` S13, pub. 2026-11-13)
- S1 RDS PostgreSQL extensions https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html
- S2 Lightsail pricing https://aws.amazon.com/lightsail/pricing/ (container Nano $7, Micro $10; Lightsail containers in ca-central-1 unverified)
- S3 App Runner availability change https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html (search result)
- S4 ECS Express Mode https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html (search result)
- S5 Azure PG Flexible Server extensions https://learn.microsoft.com/en-us/azure/postgresql/extensions/concepts-extensions-versions
- S6 Azure Retail Prices API, canadacentral (PostgreSQL B1MS, backup LRS; Container Apps) https://prices.azure.com/api/retail/prices
- S9 Cloud SQL extensions https://docs.cloud.google.com/sql/docs/postgres/extensions; S9b backups https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/backups; S9c custom backup location https://cloud.google.com/sql/docs/postgres/samples/cloud-sql-postgres-instance-backup-location (search result)
- S10 Cloud Run locations https://docs.cloud.google.com/run/docs/locations
- S11 db-f1-micro Toronto rate, third-party https://sparecores.com/database/gcp/db-f1-micro (verify on https://cloud.google.com/sql/pricing)
- S12 GCS Object Retention Lock https://docs.cloud.google.com/storage/docs/object-lock
- S13 DO PostgreSQL extensions https://docs.digitalocean.com/products/databases/postgresql/details/supported-extensions/; S13b limits https://docs.digitalocean.com/products/databases/postgresql/details/limits/
- S14 DO regional availability https://docs.digitalocean.com/platform/regional-availability/
- S15 DO App Platform pricing https://www.digitalocean.com/pricing/app-platform
- S16 DO Managed Databases pricing https://www.digitalocean.com/pricing/managed-databases (via `data-residency-input.md` S14)
- S17 Fly.io Managed Postgres https://docs.fly.io/mpg; yyz changelog https://fly.io/changelog/managed-postgres-v2-toronto.md (search result)
- S18 DO Spaces versioning https://docs.digitalocean.com/products/spaces/how-to/enable-versioning; object lock question https://www.digitalocean.com/community/questions/does-digital-ocean-spaces-offer-object-lock-features (unanswered)
- S19 OVH PostgreSQL capabilities https://docs.ovhcloud.com/en/guides/public-cloud/databases/postgresql-capabilities
- S20 OVH PostgreSQL extensions https://docs.ovhcloud.com/fr/guides/public-cloud/databases/postgresql-extensions.md (search result)
- S21 OVH regions https://www.ovhcloud.com/en/public-cloud/regions-availability/
- S22 OVH Essential db1-4, third-party https://sparecores.com/database/ovh/postgresql-essential-db1-4
- S23 OVH object lock https://docs.ovhcloud.com/it/guides/storage-and-backup/object-storage/s3-managing-object-lock (search result)
