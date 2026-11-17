# Backup and restore test plan (Railway now, Canada from S4; pilot Feb–Apr 2027)

- Status: DRAFT for `ciso` review (2026-11-16, restructured for ADR 0009). Desk work: repo + public Railway / DigitalOcean / AWS / Google Cloud docs. Nothing here has been set up or run.
- Decision (Farjad Iranmehr, 2026-11-16): **Railway now, Canada later.** Railway holds only synthetic or de-identified data plus the website `pilot_request` form (US storage disclosed). Production moves to a Canadian host (ADR 0009: recommended **D = DigitalOcean TOR1** + offsite copy in **AWS S3 ca-central-1 Object Lock**; runner-up **C = Google Cloud Toronto/Montréal**) **before the first real farm data** — the S5 rehearsal enters 3 real farms from **Jan 18, 2027**, which is earlier than the S5 gate (Jan 29). Host choice due Jan 4; migration in S4 (Jan 4–15).
- Two phases:
  - **Phase R** (§1–§2) — Railway, from now until cutover. Light protection: almost nothing real is stored.
  - **Phase C** (§3–§7) — Canadian host, from S4. Full protection of the calibration dataset and proof evidence; the go-live gate.
- Protects (Phase C priority order): `recommendation`, `review`, `proof_document` (+ the PDFs in the bucket) first; then the rest of the schema; then `pilot_request` (PII).
- Rule: **never restore over production.** Every drill restores into a local Docker container or a separate non-production environment.
- Rule: **every drill includes the residency check (§8).**
- "Needs OK" = needs Farjad Iranmehr's explicit go (new service, cost, setting change, new vendor, production access).
- Companions: `docs/security/railway-hardening.md` (Railway facts), `docs/adr/0009-production-data-residency-canada.md`, `docs/runbook-db-switch.md`, `docs/security/release-gate-checklist.md` §6.
- Markers used below: **[REPLACED by …]** = earlier design item that no longer applies to production; kept for history and for Phase R where noted.

---

# Phase R — Railway (now → cutover, S4)

## 1. What is on Railway and why protection is light

| Data on Railway | Real? | Value if lost | Protection |
|---|---|---|---|
| `pilot_request` (website form: name, email, country, farm size, crop, notes, consent text) | **Yes — real PII**, US storage disclosed on the form | Prospective pilot farmers; they can re-submit, but we lose leads and consent records | R1 + R2 below |
| Farm, soil, recommendation, review, proof tables (`PostGIS-cXKk`, staging/sandbox) | **No** — synthetic / de-identified only (ADR 0009) | Re-created from `db/seeds/dev.sql` + synthetic fixtures | R1 only (convenience) |
| Proof PDFs | None in a Railway bucket (ADR 0009: Railway Bucket not created for production) | — | — |

Railway native facts (unchanged from the earlier plan; source https://docs.railway.com/volumes/backups, https://docs.railway.com/volumes/point-in-time-recovery, https://docs.railway.com/storage-buckets):
- Volume backups: Daily (kept 6 days), Weekly (27 days), Monthly (89 days); restore "only into the same project + environment"; "Wiping a volume deletes all backups."
- PITR exists for Railway's own Postgres image only; plain `postgis/postgis` images have no archiver.
- Buckets: no backups, no versioning, no object lock.
- All Railway regions are outside Canada. Phase R backups are therefore **in the US** (or wherever the service region is) — acceptable only because the only real data there is `pilot_request`, whose US storage is disclosed.

## 2. Phase R design

| # | What | How | Frequency / retention | Needs OK |
|---|---|---|---|---|
| R1 | Volume backups on the Railway service that holds `pilot_request` (today `Postgres`; `PostGIS-cXKk` if the website was switched per `runbook-db-switch.md`) | Railway Daily + Weekly schedules (Monthly not needed: Railway is gone by Feb) | Railway retention | Yes (setting, small cost) |
| R2 | `pilot_request` export | Farjad Iranmehr (production access) runs `pg_dump --data-only --table=public.pilot_request` through `railway connect` (SSH tunnel, no TCP proxy), encrypts with `age` on his Mac, keeps it on his FileVault disk (in Canada) + password-manager-adjacent offline copy. No upload to any cloud in Phase R. | Weekly + before any website schema change + at cutover (§7.1) | No cost; Needs OK = FI runs it himself |
| R3 | Synthetic data | Not backed up. Recreate from seed + fixtures. | — | — |

R2 command (Farjad Iranmehr runs it; agents never hold the Railway URL):
```sh
# Run on Farjad Iranmehr's Mac. All variables defined here.
R2_DIR="$HOME/cp-backup/pilot_request"
R2_SERVICE="Postgres"                                   # Railway service holding pilot_request; change to the PostGIS service if the website was switched
R2_AGE_RECIPIENT="age1..."                              # public key (not secret); private key stays in the password manager
R2_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$R2_DIR"
# railway connect opens psql; for pg_dump, start the tunnel per https://docs.railway.com/cli/connect and use the local URL it prints:
R2_LOCAL_URL="postgresql://<user>@127.0.0.1:<tunnel port>/<db>"   # typed at run time, never saved to a file or shell history
pg_dump "$R2_LOCAL_URL" --data-only --table=public.pilot_request --format=custom \
  | age -r "$R2_AGE_RECIPIENT" -o "$R2_DIR/pilot_request-$R2_STAMP.dump.age"
psql "$R2_LOCAL_URL" -At -c "select count(*), max(created_at) from pilot_request" > "$R2_DIR/pilot_request-$R2_STAMP.count.txt"
```
`pg_dump` major must be ≥ the server major (Postgres 18 on `PostGIS-cXKk`; check `select version()` on the template `Postgres`).

### 2.1 Phase R RPO / RTO

| Scope | RPO | RTO | Basis |
|---|---|---|---|
| `pilot_request` | ≤ 24 h (R1 daily) ; ≤ 7 days if Railway volume is lost (R2 weekly) | ≤ 1 business day | Low volume; contacts can re-submit. Estimate. |
| Synthetic data | n/a | ≤ 1 day (re-seed) | No real value. |
| Total Railway loss | ≤ 7 days for `pilot_request` | ≤ 2 business days (site on new host, DNS) | Phase C build covers this anyway. |

### 2.2 Phase R drills (synthetic data only)
- **Drill R-A** (local Docker, ~30 min): restore the latest R2 export into a local container (§10.1 steps, `--data-only` into a schema created from `db/migrations/0001_pilot_request.sql`), compare count and `max(created_at)` with the `.count.txt`. Teardown mandatory (real PII). Once in S2/S3.
- **Drill R-B** (Railway `staging` environment, if one exists — otherwise skip; staging moves to TOR1 per ADR 0009): old Drill B (§10.2) with synthetic data. Purpose: practice only; **not** a go-live gate, since Railway will not hold production.
- Residency check for Phase R (§8.1): confirm Railway still holds **no real farmer data**.

---

# Phase C — Canadian host (from S4, Jan 4–15, 2027)

## 3. What the Canadian host gives us natively

| Layer | Option D: DigitalOcean TOR1 | Option C: Google Cloud Toronto/Montréal | Gap we close ourselves |
|---|---|---|---|
| Postgres backups | Managed PostgreSQL: daily backups + PITR "limited to the last 7 days"; restore "to a new node" (https://docs.digitalocean.com/products/databases/postgresql/details/limits/). Backup + WAL **location not stated** on official pages; third-party sources say "same region" — **unverified**, needs DO in writing (§12). | Cloud SQL: 1–365 automated backups, PITR (transaction logs). **Default backup location = nearest multi-region, i.e. outside Canada**, unless a custom location is set (`--backup-location=northamerica-northeast2` or `-northeast1`). Transaction-log storage location for PITR: **verify**. | 7-day window is short; same account → no protection from account compromise → L3/L4. |
| Proof PDFs | Spaces TOR1: versioning yes; **Object Lock not found** (ADR 0009 S18) | GCS regional bucket, Object Retention Lock | Offsite WORM copy → L4. |
| Logs | App Platform runtime/build logs; location **not stated** | Cloud Logging `_Default` bucket is **global** unless log buckets are set to a Canadian region; Cloud Build default is global | Keep logs PII-free (release gate §5); confirm location (§8). |

## 4. Layers (Phase C)

| # | What | How | Frequency / retention | Protects against | Needs OK |
|---|---|---|---|---|---|
| L1 | ~~Railway volume backups on `postgis`~~ **[REPLACED by C1]** | — | — | — | — |
| L2 | ~~Railway PITR on `postgis`~~ **[REPLACED by C1]** | — | — | — | — |
| C1 | Managed DB backups + PITR | D: DO daily backups + 7-day PITR (on by default, not configurable). C: Cloud SQL automated backups with **custom Canadian backup location**, PITR on, retention ≥ 7 days. | Provider retention (D: 7 days) | bad migration, bad script ("restore to 10:42"), corruption | Yes (part of host cost) |
| L3 | Logical DB dump, offsite | Scheduled job (D: App Platform scheduled job / worker; C: Cloud Run job + Cloud Scheduler, region `northamerica-northeast2`) → `pg_dump -Fc` as the backup role over the private network → `age` encrypt → upload to **AWS S3 ca-central-1, Object Lock compliance mode** (separate AWS account) with a manifest | Hourly during the pilot; keep hourly 72 h, daily 35 days; **no monthly tier — max age of any copy 35 days** (CISO resolution of D4 per `adr-0009-ciso-coo-answers.md` Q6, so erasure reaches every backup within 35 days; counsel to confirm) | provider account compromise, cluster deletion, provider outage, ransomware/wrong delete (WORM) | Yes (new AWS account + cents/month) |
| L4 | Proof PDF copy, offsite | Same job: list `proof/` in Spaces TOR1 (or GCS), copy every missing key to S3 after checking bytes hash to the SHA-256 in the key. Never overwrites, never deletes. | Hourly; retention = evidence retention (D4) | bucket/object deletion or overwrite, bucket key leak | Yes (with L3) |
| L5 | Cold copy | Farjad Iranmehr downloads the latest daily encrypted dump + PDF set to an encrypted disk **in Canada** | Monthly during the pilot | total loss of cloud accounts | No cost; ~10 min |

Why S3 Object Lock and not Spaces/GCS as the offsite: a second vendor + second account means one compromised login cannot delete both the database and its backups; S3 compliance mode cannot be shortened by anyone, including the AWS root user. Details and conditions in §12.

## 5. Backup job (spec for `cp-database` + `cp-platform`, not built yet; host-agnostic)
The job is a container with `pg_dump`, `age` and an S3 client; only its scheduler differs per host. Keep it host-agnostic so option C uses the same image.
- Schedule `7 * * * *` (UTC, hourly). D: App Platform scheduled job (**verify** cron support and minimum interval in TOR1; fallback: worker with an internal loop). C: Cloud Scheduler → Cloud Run job, both in `northamerica-northeast2`.
- Image: `postgis/postgis:18-3.7` client tools (Postgres 18 baseline, ADR 0009; `pg_dump` major must be ≥ server major) — **[REPLACED: `postgis/postgis:17-3.5`]** — plus `age` and an S3 client. Pinned by digest.
- Variables on this job only: `BACKUP_DATABASE_URL` (backup role; on DO/GCP `pg_read_all_data` needs a grant via the admin user — ADR 0009 consequence; **verify**), proof bucket **read** credentials, `BACKUP_DEST_*` (S3 write credentials: `s3:PutObject` only, no delete, no `PutObjectRetention`, no `BypassGovernanceRetention`, no bucket-config actions), `BACKUP_AGE_RECIPIENT` (public key). The age **private** key never enters any host, CI or git; Farjad Iranmehr keeps it in his password manager + one offline copy (D6: + one deputy).
- Steps per run (Python + psycopg, same style as `app/cloverproof_app/db/migrate.py`, URL never printed):
  1. `begin isolation level repeatable read read only; set local timezone = 'UTC'; select pg_export_snapshot();`
  2. In that transaction write `manifest.json`: UTC timestamp, `schema_migrations` names, row count and digest per table (§9 V1–V2), `postgis_lib_version()`, server version, **host + region label** (for the residency check).
  3. `pg_dump --format=custom --snapshot=<id> --no-password` with the same snapshot.
  4. `age -r $BACKUP_AGE_RECIPIENT` on dump and manifest; upload as `db/<YYYY>/<MM>/<DD>/cloverproof-<UTC timestamp>.dump.age` and `.manifest.json.age` with per-object retention (hourly 3 days; the 00:07 run 35 days; no longer-lived tier — D4 resolved at 35 days max, counsel to confirm).
  5. PDF copy (L4): for each source key `proof/{org}/{rec}/{sha256}.pdf` absent at destination: download, `sha256(bytes) == {sha256}` else **alert, do not copy**; upload with the same key and the evidence retention.
  6. Exit non-zero on any error; failure alert via the existing admin channel, or a GitHub Actions check of "newest dump < 2 h old" (reads object metadata only) — `cp-platform` picks; no new vendor.
- Pruning: none by the job. Object Lock retention + an S3 lifecycle rule (expire after retention) delete old objects; the job key cannot delete.

## 6. RPO / RTO for the pilot (Feb–Apr 2027, Phase C)

| Scope | RPO | RTO | Basis |
|---|---|---|---|
| Database, in-provider failure (bad script, migration) | ≤ minutes (C1 PITR, within 7 days) | ≤ 4 h during working hours | ≤4 internal users, no farmer-facing service. Estimate. |
| Database, provider account/cluster lost | ≤ 1 h (L3) | ≤ 1 business day (restore L3 into a new cluster in TOR1, or into option C) | Restore path is drill A. |
| Proof PDFs | ≤ 1 h (L4) | ≤ 4 h (with DB) | PDFs cannot be regenerated byte-identically → a lost PDF is lost evidence. |
| Total loss of the provider | ≤ 1 h | ≤ 2 business days (stand up option C in Canada from L3/L4 + DNS) | Rebuild = drill A + infra from the ADR; **never** back to Railway once real data exists (ADR 0009 rollback). |
| `pilot_request` | ≤ 1 h (same dump) | ≤ 1 day | Low volume. |

## 7. Cutover (S4, Railway → Canadian host)

### 7.1 Final Railway dump (Farjad Iranmehr, production access)
1. Pause website writes on Railway (maintenance flag or scale the Railway `website` to 0) — window agreed with `cp-website`.
2. Full dump of the Railway DB holding `pilot_request`: R2 command with `--format=custom` and **without** `--data-only --table` (whole DB), plus the `pilot_request`-only export used for the copy. Encrypt with `age`.
3. Record on the Railway side: `select count(*), max(created_at), md5(coalesce(string_agg(md5(p::text), '' order by p.id), '')) from pilot_request p;` (status is mutable → only valid while writes are paused).
4. Save the encrypted dumps **in Canada**: S3 ca-central-1 under `cutover/` (retention ≥ 90 days, D4) + L5 disk. Never in a US region, never in git or Notion.
5. Restore the `pilot_request` export into the Canadian production DB (`cp-website` / `cp-database`), run the same query there: count, max and digest **equal**. File the three values (no rows) as evidence.
6. Switch DNS → test submission on the new host → resume writes.

### 7.2 Railway after cutover
- Railway DB kept **read-only**, not deleted: remove the website's DB variable / stop the Railway website service; `alter database <db> set default_transaction_read_only = on;` (session-overridable; the real guard is that no service holds credentials); keep R1 volume backups on.
- Only Farjad Iranmehr approves deletion, ≥ 1 week after cutover (ADR 0009) and only after drill A on the cutover dump passed. On deletion: delete volume (this also deletes its backups) and record the date — it is the end of US storage for pilot PII, which the privacy notice references.
- Railway may keep a synthetic-only sandbox (§8.1 query must stay at 0).

## 8. Residency check (part of **every** drill, Phase R and C)

### 8.1 Railway holds no real farmer data (Phase R and after cutover)
Rule for hosted synthetic data: every `organisation.name` ends with `(dev seed)` or `(synthetic)`, every `app_user.email` ends with `@example.org` (as `db/seeds/dev.sql`). `cp-database` adds this rule to the fixture generator. Query on each Railway environment (run by Farjad Iranmehr or via a read-only role), must return all zeros:
```sql
select
  (select count(*) from organisation where name !~ '\((dev seed|synthetic)\)$')            as real_orgs,
  (select count(*) from app_user where email !~* '@example\.org$')                           as real_users,
  (select count(*) from farmer f join organisation o on o.id = f.organisation_id
     where o.name !~ '\((dev seed|synthetic)\)$')                                           as real_farmers,
  (select count(*) from soil_test s join organisation o on o.id = s.organisation_id
     where o.name !~ '\((dev seed|synthetic)\)$')                                           as real_soil_tests;
-- pilot_request is the disclosed exception until cutover; after cutover: select count(*) from pilot_request where deleted_at is null; -> 0 on any Railway env still running
```
(`soil_test.organisation_id` exists per `0005_soil_test.sql`.)

### 8.2 All Phase C storage is in Canada
Evidence per drill = command output (read-only) or redacted screenshot, plus the provider's written confirmation on file (§12). Run by Farjad Iranmehr or a read-only token; agents get outputs only.

| Item | D: DigitalOcean | C: Google Cloud | Pass |
|---|---|---|---|
| DB cluster | `doctl databases get "$DO_DB_ID" --format Region` (`DO_DB_ID`= cluster id from the dashboard) | `gcloud sql instances describe "$GCP_SQL_INSTANCE" --project "$GCP_PROJECT" --format='value(region,settings.backupConfiguration.location)'` | `tor1` / `northamerica-northeast1|2` for **both** values (empty backup location = multi-region = FAIL) |
| DB backups + PITR WAL | No API field → DO written confirmation (§12) | backup location above; transaction-log location per GCP docs/written answer | confirmation on file and still current |
| App, worker, website, jobs | `doctl apps get "$DO_APP_ID" --format Region` | `gcloud run services list --project "$GCP_PROJECT" --format='value(metadata.name,region)'` (+ `gcloud run jobs list`) | Canadian region only |
| Proof bucket | Spaces endpoint `tor1.digitaloceanspaces.com` in the bucket settings | `gcloud storage buckets describe "gs://$GCP_PROOF_BUCKET" --format='value(location)'` | `TOR1` / `NORTHAMERICA-NORTHEAST2` (not `US`, not dual-region outside Canada) |
| Offsite backups | `aws s3api get-bucket-location --bucket "$BACKUP_BUCKET" --profile "$AWS_BACKUP_READ_PROFILE"`; `aws s3api get-bucket-replication ...` | same (S3 is used with C too) | `ca-central-1`; replication = `ReplicationConfigurationNotFoundError` (or Canada-only target) |
| Object Lock | `aws s3api get-object-lock-configuration --bucket "$BACKUP_BUCKET" --profile "$AWS_BACKUP_READ_PROFILE"` | same | `Enabled`, `COMPLIANCE` |
| Logs | App Platform log location: DO written confirmation; log forwarding off or to a Canadian destination | `gcloud logging buckets list --project "$GCP_PROJECT"` | D: on file. C: `_Default` and `_Required` buckets not `global` for app logs (route to a regional log bucket) |
| Org-wide guard (C only) | — | `gcloud resource-manager org-policies describe gcp.resourceLocations --project "$GCP_PROJECT"` | `in:canada-locations` (or the two regions) |
| Drill copies | Local Docker on a FileVault Mac in Canada; teardown done | same | yes |

Variables: `DO_DB_ID`, `DO_APP_ID` = ids from the DO dashboard (not secret); `GCP_PROJECT`, `GCP_SQL_INSTANCE`, `GCP_PROOF_BUCKET` = names from the console; `BACKUP_BUCKET` = S3 bucket name; `AWS_BACKUP_READ_PROFILE` = local AWS CLI profile with read-only drill credentials. The public repo records pass/fail only, not bucket names.

## 9. Verification queries (run on the restored copy; never on production)

All in one `psql` session with `set timezone = 'UTC';`. Expected values come from the matching `manifest.json`.

V1 — row counts (compare each to the manifest):
```sql
select 'organisation' t, count(*) from organisation union all
select 'app_user', count(*) from app_user union all
select 'membership', count(*) from membership union all
select 'farmer', count(*) from farmer union all
select 'farm', count(*) from farm union all
select 'field', count(*) from field union all
select 'season', count(*) from season union all
select 'field_geometry_version', count(*) from field_geometry_version union all
select 'soil_test', count(*) from soil_test union all
select 'soil_test_value', count(*) from soil_test_value union all
select 'crop_plan', count(*) from crop_plan union all
select 'recommendation', count(*) from recommendation union all
select 'review', count(*) from review union all
select 'application_log', count(*) from application_log union all
select 'proof_document', count(*) from proof_document union all
select 'pilot_request', count(*) from pilot_request union all
select 'schema_migrations', count(*) from schema_migrations
order by 1;
```

V2 — content digest of the immutable tables (must equal the manifest exactly):
```sql
select 'recommendation' t, md5(coalesce(string_agg(md5(r::text), '' order by r.id), '')) from recommendation r
union all
select 'review', md5(coalesce(string_agg(md5(v::text), '' order by v.id), '')) from review v
union all
select 'proof_document', md5(coalesce(string_agg(md5(d::text), '' order by d.id), '')) from proof_document d;
```

V3 — schema, triggers and grants survived:
```sql
select name from schema_migrations order by name;                 -- = files in db/migrations
select postgis_full_version();                                     -- note: 3.7 local vs 3.6.x managed (ADR 0009)
-- 9 rows expected (3 per table), all tgenabled = 'O'
select c.relname, t.tgname, t.tgenabled
from pg_trigger t join pg_class c on c.oid = t.tgrelid
where not t.tgisinternal and c.relname in ('recommendation', 'review', 'proof_document')
order by 1, 2;
-- all false
select has_table_privilege('cp_app', 'recommendation', 'UPDATE') as rec_upd,
       has_table_privilege('cp_app', 'recommendation', 'DELETE') as rec_del,
       has_table_privilege('cp_app', 'review', 'UPDATE') as rev_upd,
       has_table_privilege('cp_app', 'proof_document', 'DELETE') as doc_del;
select relname, pg_get_userbyid(relowner) from pg_class
where relname in ('recommendation', 'review', 'proof_document');  -- owner cp_migrator
```

V4 — recommendation chain integrity (every query must return 0 or `true`):
```sql
select (select count(*) from recommendation) = (select count(*) from recommendation_diff) as all_reachable;
select count(*) from recommendation where (kind = 'engine') <> (parent_id is null);
select count(*) from recommendation c join recommendation p on p.id = c.parent_id where c.created_at < p.created_at;
select count(*) from review r join recommendation c on c.id = r.resulting_recommendation_id
where r.decision = 'edit' and c.parent_id is distinct from r.recommendation_id;
select count(*) from (select recommendation_id from review where decision = 'approve' group by 1 having count(*) > 1) x;
select count(*) from proof_document d
where not exists (select 1 from review r where r.recommendation_id = d.recommendation_id and r.decision = 'approve');
select count(*) from proof_document where storage_key <> format('proof/%s/%s/%s.pdf', organisation_id, recommendation_id, sha256);
select count(*) from recommendation_diff where approved_at is not null;   -- compare to manifest
-- warning only (membership is mutable)
select count(*) from review r where r.decision = 'approve'
and not has_org_role(r.reviewer_id, r.organisation_id, 'agronomist');
```

V5 — proof PDFs re-hashed against the restored DB:
```sh
DRILL_DIR="$HOME/cp-drill"
DRILL_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:55433/cloverproof_restore"
DRILL_PDF_DIR="$DRILL_DIR/pdf"
psql "$DRILL_DATABASE_URL" -At -F ' ' -c "select sha256, storage_key from proof_document order by id" |
while read -r expected key; do
  file="$DRILL_PDF_DIR/$key"
  if [ ! -f "$file" ]; then echo "MISSING $key"; continue; fi
  actual=$(shasum -a 256 "$file" | cut -d' ' -f1)
  [ "$actual" = "$expected" ] && echo "OK $key" || echo "MISMATCH $key"
done | tee "$DRILL_DIR/v5.txt" | cut -d' ' -f1 | sort | uniq -c
# Orphans (PDF without a DB row) are reported, not failed.
```
Pass = zero `MISSING`, zero `MISMATCH`.

V6 — PostGIS data:
```sql
select count(*) from field_geometry_version where geom is not null and not st_isvalid(geom);  -- 0
```

V7 — residency: §8 table, all rows pass.

## 10. Restore drills

### 10.1 Drill A — offsite dump into local Docker (proves L3/L4 and off-provider recovery; host-agnostic)
Operator: `cp-database` with Farjad Iranmehr (he holds the age key). Machine: FileVault on, in Canada. Never put a production URL in this shell.

```sh
DRILL_DIR="$HOME/cp-drill"
DRILL_DUMP="$DRILL_DIR/cloverproof-<UTC timestamp>.dump.age"
DRILL_MANIFEST="$DRILL_DIR/cloverproof-<UTC timestamp>.manifest.json.age"
DRILL_AGE_KEY="$DRILL_DIR/age-key.txt"          # copied from the password manager for the drill, deleted after
DRILL_PORT=55433
DRILL_IMAGE="postgis/postgis:18-3.7"            # [REPLACED: 17-3.5] match the production major (18)
DRILL_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:${DRILL_PORT}/cloverproof_restore"

date -u +"start %FT%TZ"                           # RTO clock starts
age -d -i "$DRILL_AGE_KEY" -o "$DRILL_DIR/db.dump" "$DRILL_DUMP"
age -d -i "$DRILL_AGE_KEY" -o "$DRILL_DIR/manifest.json" "$DRILL_MANIFEST"

docker run -d --name cp-drill -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=cloverproof \
  -p 127.0.0.1:${DRILL_PORT}:5432 "$DRILL_IMAGE"
until docker exec cp-drill pg_isready -U postgres -d cloverproof; do sleep 2; done
docker exec cp-drill createdb -U postgres -T template0 cloverproof_restore

# pg_dump does not carry roles: create them first so ownership and grants restore as in production.
psql "$DRILL_DATABASE_URL" -v ON_ERROR_STOP=1 -c "
  create role cp_migrator nologin; create role cp_app nologin;
  create role cp_website nologin; create role cp_backup nologin;"
# Managed-host role names (doadmin / cloudsqlsuperuser grants) may appear in the dump: add them here as nologin, or use --no-owner and re-check V3 owners.

docker cp "$DRILL_DIR/db.dump" cp-drill:/tmp/db.dump
docker exec cp-drill pg_restore -U postgres -d cloverproof_restore --exit-on-error /tmp/db.dump
date -u +"db restored %FT%TZ"
```
Then: download the PDF copy from S3 into `$DRILL_DIR/pdf/` (read-only profile), run V1–V7, compare with `manifest.json`, `date -u` = RTO clock stops.

Teardown (mandatory, the data includes PII):
```sh
DRILL_DIR="$HOME/cp-drill"
docker rm -f cp-drill
rm -rf "$DRILL_DIR"
```
Expected trouble to note, not hide: PostGIS minor mismatch (3.6.x dump → 3.7 local: usually fine upward; never restore a 3.7 dump into 3.6), managed-host role names, `spatial_ref_sys` rows, generated column `n_rate_kg_ha` (recomputed; V2 must still match).

Host-agnostic variant (runner-up C or provider loss): same steps, but restore into a **new** managed cluster in a Canadian region instead of Docker (`pg_restore --no-owner` + role script); V7 checks the new cluster's region.

### 10.2 Drill B — provider-native restore (proves C1)
**[REPLACED: Railway volume restore in `staging` — now Drill R-B, Phase R only.]** Runs on the **staging** cluster of the Canadian host, never production.
1. Staging DB with migrations + synthetic recommendation → review → proof chain (no real farm data). Record V1/V2 and UTC time `T0`.
2. Change data (insert one extra synthetic recommendation via the migration role); note time `T1`.
3. D: Restore from backup / fork to a point between `T0` and `T1` → **new** cluster in TOR1 (DO restores always create a new node). C: `gcloud sql instances clone` with `--point-in-time` → new instance in the same Canadian region.
4. Run V1–V4 and V7 on the new cluster: counts/digests equal step 1, the step-2 row is absent, region Canadian. Record duration.
5. Delete the restored cluster (Needs OK only if on production account).

### 10.3 Real incident (outline; full runbook after the S5 rehearsal)
Stop writes (scale `app` to 0 or maintenance flag) → note the incident time → C1 PITR restore to a **new** cluster (or L3 dump if C1 is unavailable) → V1–V7 → switch `DATABASE_URL` of `app`/`worker`/`website` to the new cluster → keep the damaged cluster until Farjad Iranmehr approves deletion. Never restore to Railway once real data exists. Every step Needs OK.

## 11. Decisions, schedule, owners, evidence

### 11.1 Decisions needing Farjad Iranmehr

| # | Decision | Status after ADR 0009 | Recommendation |
|---|---|---|---|
| D1 | Backup destination (L3/L4) | **Answered by ADR 0009 (proposed):** AWS S3 ca-central-1, Object Lock compliance, separate AWS account. [REPLACED: Railway bucket / B2 / R2 options] | Accept, with §12 conditions. |
| D2 | PostGIS image on Railway | **[REPLACED]** — moot for production; managed PG 18 + PostGIS on the Canadian host | — |
| D3 | Railway volume backup schedules | Phase R only: Daily + Weekly on the service holding `pilot_request` (R1) | Yes, now. |
| D4 | Retention of dumps, PDF copies, cutover dump | Open. Object Lock **compliance** makes retention unchangeable → decide before the bucket is created; ties to erasure (ER-30, ADR 0009 Q6). | Ask `legal-compliance-specialist`; proposal in §4/§5. |
| D5 | Staging environment for drills | Staging moves to the Canadian host (ADR 0009) | Yes, built before production in S4. |
| D6 | Who holds the age private key | Open | Two holders. |
| D7 | Host D or C | Due Jan 4 (brief) — ADR 0009 table says Dec 4 | Decide by Dec 11 at the latest if possible; see open items. |

### 11.2 Schedule (dates from the brief and ADR 0009)

| When | What | Owner | Exit |
|---|---|---|---|
| Now → S3 | Phase R: R1 schedules on; first R2 export; Drill R-A; §8.1 query on every Railway env | Farjad Iranmehr, `cp-database` | evidence filed |
| By Dec 11 | DO written answers (§12) — else option C | `devops-engineer` drafts, Farjad Iranmehr sends | answers on file |
| By Jan 4 | Host chosen (D or C); AWS backup account + Object Lock bucket created (test bucket in governance mode first) | Farjad Iranmehr | decision recorded |
| S4 Jan 4–15 | Staging on Canadian host → **Drill B** + **Drill A** on staging (synthetic); production built; backup job live; cutover (§7); Drill A on the cutover dump; §8 residency check | `cp-platform`, `cp-database`, Farjad Iranmehr | evidence filed; **must pass before Jan 18** |
| From Jan 18 | First real farm data, Canada only | Farjad Iranmehr | — |
| S5 Jan 18–29 | **Timed rehearsal**: Drill A + Drill B on the Canadian host, RPO/RTO measured against §6, failure alert tested by breaking the job once in staging, V7 residency | `cp-database`, `cp-qa` observes | `ciso` sign-off = release gate §4/§6 item |
| Pilot Feb–Apr 2027 | Drill A monthly, L5 monthly, Drill A after any migration touching immutable tables; residency check each time | `cp-database`, Farjad Iranmehr | evidence per drill |

### 11.3 Owners

| Role | Who |
|---|---|
| Approves cost, provider accounts, settings, new vendors; holds age key; production access (R2, cutover dump); L5 cold copy; Railway deletion | Farjad Iranmehr |
| Backup job, roles (`cp_backup`), verification queries, drills, synthetic-data naming rule | `cp-database` |
| Hosting services (staging, jobs), scheduler, alerting | `cp-platform` |
| Independent check of drill evidence | `cp-qa` |
| Sign-off, retention questions routed to legal | `ciso` |
| Keeps this plan and the incident runbook current; drafts provider questions | `devops-engineer` |

### 11.4 Evidence to file per drill
The repo is public: the committed record holds **no PII, no secrets, no hostnames with credentials, no bucket names**. Full outputs go to Notion via `documentation-manager`.

`docs/security/evidence/drill-<YYYY-MM-DD>-<R-A|R-B|A|B>.md`:
- date, operator, environment (local Docker / staging on DO or GCP / Railway staging), image digest used;
- backup used: UTC timestamp and SHA-256 of the encrypted dump file;
- V1 counts and V2 digests: restored vs manifest (equal / not equal per table);
- V3, V4, V6 results; V5 totals; **V7 residency: pass/fail per §8 row + date of the provider's written confirmation**;
- measured RTO and RPO;
- problems found, tasks opened, teardown confirmed;
- sign-off: `cp-qa` checked, `ciso` accepted.

## 12. ADR 0009 Q3 — backup locations (draft answer for `ciso` / `coo`)

**Question:** confirm in writing that DB backups, PITR WAL and App Platform/build logs stay in Canada; is the S3 ca-central-1 copy acceptable as the offsite location (Canada, second US vendor)?

### 12.1 What must be confirmed in writing (before Dec 11; via support ticket or account manager, answer saved as PDF with date and author)
DigitalOcean (option D), for a Managed PostgreSQL cluster, App Platform app and Spaces bucket in TOR1:
1. Physical location of automated daily backups **and** of the WAL used for PITR (country + data centre/region). Are any copies kept outside TOR1/Canada (e.g. a DR copy in NYC)?
2. Location of App Platform runtime logs, build logs and build workers; retention; whether log forwarding is off by default.
3. Location of DOCR images used by App Platform (contain no data by design — low priority).
4. Backup retention and deletion: when a backup expires or a cluster is deleted, when are backups/WAL destroyed; is there a post-deletion grace copy and where.
5. Encryption at rest for managed DB volumes, backups and Spaces (key ownership).
6. Support/ops staff access: from which countries; is customer data copied out of region for support.
7. Whether these commitments are in the DPA or only in a support answer (support answers are weaker; ask for the DPA clause or sub-processor list with locations).

Google Cloud (option C): items 1–2, 4–6 for Cloud SQL (backups with custom location set; transaction-log storage for PITR), Cloud Run and Cloud Logging; plus confirmation that `gcp.resourceLocations` = `in:canada-locations` blocks out-of-Canada backups. Note: **Cloud SQL default backup location is a multi-region outside Canada unless a Canadian custom location is set** — this is a configuration item, not just a question. GCP documents locations more completely than DO, so fewer written answers are needed.

### 12.2 How to verify (not only trust)
- Config evidence per §8.2 (region fields, backup-location field on GCP, bucket location, replication off, object lock on) at setup and in every drill.
- Restore test: Drill B restores land in a new TOR1 / Canadian cluster (region checked).
- DPA + sub-processor list with locations filed; re-checked when the provider notifies a sub-processor change.
- What cannot be verified technically: where a provider keeps its own internal backup copies and logs. That rests on the written confirmation + DPA; record it as an accepted residual risk.

### 12.3 Is S3 ca-central-1 Object Lock acceptable as the offsite copy?
**Yes, from a backup/security view, with conditions.** Reasons: (a) independent vendor and account → one compromised DO login cannot delete production **and** backups; (b) compliance-mode WORM protects against ransomware, wrong scripts and insiders, which DO Spaces cannot (no object lock found); (c) ca-central-1 keeps the copy in Canada; AWS documents that content stays in the chosen region unless the customer replicates it; (d) the dumps and PDFs are `age`-encrypted before upload and the key never reaches AWS → AWS (and any CLOUD Act order served on AWS) gets ciphertext only. The second US vendor therefore adds no meaningful plaintext exposure. Note: proof PDFs in L4 are copied as-is (hash-addressed) — **encrypt them with `age` too** (store `{sha256}.pdf.age`, verify hash after decrypt) or accept that AWS holds plaintext PDFs (contain farmer/field data). Recommendation: encrypt.

Conditions:
1. Separate AWS account (or org member account) used only for backups; root MFA, no root access keys; one IAM user/role for the writer (`s3:PutObject` only) and one read-only role for drills; billing alerts.
2. Bucket created in `ca-central-1` with Object Lock enabled at creation; **no replication**; SSE-S3 (or KMS in ca-central-1) on; Block Public Access on; bucket policy denies non-TLS.
3. **Test first in governance mode** on a throwaway bucket; compliance mode is irreversible — a wrong default retention (e.g. years instead of days) cannot be shortened and is billed for that period and blocks erasure. Use per-object retention values from D4.
4. Erasure: compliance mode means a deletion request cannot purge backups early → privacy notice states the maximum backup age (ADR 0009 Q6); `legal-compliance-specialist` confirms this is acceptable under PIPEDA.
5. Cost: estimate < $1/month at pilot volume (S3 $0.025/GB-mo in ca-central-1, ADR 0009 S0; dumps < 1 GB).
6. Same S3 copy applies if option C is chosen (keeps the second-vendor property; GCS Retention Lock would be same-vendor).
