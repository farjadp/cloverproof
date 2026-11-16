# Backup and restore test plan (S3–S5, pilot Feb–Apr 2027)

- Status: DRAFT for `ciso` review (2026-11-16). Desk work: repo + public Railway docs. Nothing here has been set up or run.
- Protects: `recommendation`, `review`, `proof_document` (+ the PDFs in the bucket) first; then the rest of the schema; then `pilot_request` (PII).
- Rule: **never restore over production.** Every drill restores into a local Docker container or a separate non-production Railway environment.
- "Needs OK" = needs Farjad Iranmehr's explicit go (new service, cost, Railway setting change, new vendor).
- Companion: `docs/security/railway-hardening.md` (roles, network, bucket facts).

## 1. What Railway gives us natively (and what it does not)

| Layer | Native protection | Limits that matter to us | Source |
|---|---|---|---|
| Postgres / PostGIS volume | Volume backups: manual + schedules Daily (kept 6 days), Weekly (kept 27 days), Monthly (kept 89 days); incremental, billed like volume storage. | Restore "only into the same project + environment"; it mounts a new volume on the same service and redeploys (old volume kept, unmounted). "Wiping a volume deletes all backups." Same account, same platform → no protection from account compromise or platform loss. Plan requirement not stated → **verify**. | https://docs.railway.com/volumes/backups |
| Postgres PITR | Point-in-time recovery for Postgres: WAL archived by pgBackRest to a Railway bucket; "last 4 full backups ... roughly 4 weeks"; restore "Creates a brand-new service", source untouched; no separate fee. | Built into Railway's Postgres image. Plain `postgis/postgis:17-3.5` (our planned image) has no archiver → **no PITR** unless we use a Railway-derived image (hardening §6, decision D2). Window starts at enable time, not retroactive. | https://docs.railway.com/volumes/point-in-time-recovery, https://docs.railway.com/databases |
| Bucket (proof PDFs) | None. "Railway doesn't currently offer automatic backups or snapshots for buckets." No versioning, no object lock. Deleted bucket restorable for 52 hours. | An app bug, leaked key or wrong script can delete or overwrite PDFs with no recovery. | https://docs.railway.com/storage-buckets |
| Logs | 7 days (Hobby) / 30 days (Pro) | Not a backup of anything. | https://docs.railway.com/observability/logs |

Conclusion: Railway's volume backups are a fast in-place recovery path, not a backup we can rely on alone. We add an independent, encrypted, off-service copy of both the database and the PDFs.

## 2. Backup design (target for go-live 2027-02-01)

### 2.1 Layers

| # | What | How | Frequency / retention | Protects against | Needs OK |
|---|---|---|---|---|---|
| L1 | `postgis` volume | Railway volume backups, Daily + Weekly + Monthly schedules | Railway retention (6 / 27 / 89 days) | bad migration, data corruption, fast rollback | Yes (setting, small cost) |
| L2 | `postgis` PITR | Only if D2 picks a Railway-derived image and PITR works with it (**verify**) | ~4 weeks window | "restore to 10:42 before the bad script" | Yes |
| L3 | Logical DB dump, offsite | Railway cron service `backup` → `pg_dump -Fc` as `cp_backup_login` over private network → encrypt with `age` → upload to the backup destination (D1) with a manifest | Hourly during the pilot; keep hourly 72 h, daily 35 days, monthly 12 months (retention to be confirmed by `legal-compliance-specialist`: backups contain PII) | volume wipe, service/project deletion, Railway account compromise (if D1 = off-platform), platform outage | Yes (new service + cost) |
| L4 | Proof PDF copy, offsite | Same `backup` job: list `proof/` in the bucket, copy every key missing at the destination, after checking the bytes hash to the SHA-256 in the key. Never overwrites, never deletes at the destination. | Hourly; kept as long as the evidence must be kept (D4) | bucket deletion, object deletion/overwrite, bucket key leak | Yes (with L3) |
| L5 | Cold copy | Farjad Iranmehr downloads the latest daily encrypted dump + PDF set to an encrypted disk | Monthly during the pilot | total loss of cloud accounts | No cost; Farjad Iranmehr's time (~10 min) |

### 2.2 Backup job (spec for `cp-database` + `cp-platform`, not built yet)
- Railway service `backup`, cron schedule `7 * * * *` (UTC, hourly; Railway cron needs ≥5 min between runs and skips a run if the previous one is still going). Source: https://docs.railway.com/cron-jobs
- Image: `postgis/postgis:17-3.5` (or the D2 image) so `pg_dump` matches server major 17; plus `age` and an S3 client. Pinned by digest.
- Variables on this service only: `BACKUP_DATABASE_URL` (→ `cp_backup_login`, member of `pg_read_all_data`, sealed), proof bucket read credentials (sealed), destination write credentials (sealed; write-only/no-delete if D1 allows), `BACKUP_AGE_RECIPIENT` (public key, not secret). The age **private** key never enters Railway or git; Farjad Iranmehr keeps it in his password manager + one offline copy.
- Steps per run (Python + psycopg, same style as `app/cloverproof_app/db/migrate.py`, URL never printed):
  1. `begin isolation level repeatable read read only; set local timezone = 'UTC'; select pg_export_snapshot();`
  2. In that transaction write `manifest.json`: UTC timestamp, `schema_migrations` names, row count and digest per table (§4 V1–V2), `postgis_lib_version()`, server version.
  3. `pg_dump --format=custom --snapshot=<id> --no-password` with the same snapshot, so dump and manifest describe the same instant.
  4. `age -r $BACKUP_AGE_RECIPIENT` on the dump and on the manifest; upload as `db/<YYYY>/<MM>/<DD>/cloverproof-<UTC timestamp>.dump.age` and `.manifest.json.age`; then commit.
  5. PDF copy (L4): for each source key `proof/{org}/{rec}/{sha256}.pdf` absent at destination: download, `sha256(bytes) == {sha256}` else **alert, do not copy**; upload with the same key.
  6. Exit non-zero on any error; failure alert (Telegram/email via the existing admin channel, or a GitHub Actions check of "newest dump < 2 h old" — `cp-platform` picks; no new vendor).
- Pruning of old dumps runs from a separate credential (or destination lifecycle rules) so the hourly job's key cannot delete.

### 2.3 Proposed RPO / RTO for the pilot (Feb–Apr 2027)

| Scope | RPO | RTO | Basis |
|---|---|---|---|
| Database (all tables), in-platform failure | ≤ 1 h (L3); ≤ minutes if L2 adopted | ≤ 4 h during working hours | ≤4 internal users, no farmer-facing service; one lost hour = at most one or two reviews to re-enter from notes. Estimate. |
| Proof PDFs | ≤ 1 h (L4) | ≤ 4 h (with DB) | PDFs cannot be regenerated byte-identically (render timestamps/fonts) → a lost PDF is lost evidence; the hash in the DB alone does not replace it. |
| Total loss of Railway project/account | ≤ 1 h if D1 = off-platform; ≤ 30 days (L5) otherwise | ≤ 2 business days (new hosting + DNS) | Rebuild is documented, rehearsed partly by the local-Docker drill. |
| `pilot_request` (website) | ≤ 1 h after the switch (same dump); ≤ 24 h before it (L1 on old `Postgres`, if enabled) | ≤ 1 day | Low volume, contacts can re-submit. |

## 3. Decisions needing Farjad Iranmehr

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Backup destination (L3/L4) | (a) Railway bucket in a **separate** Railway project `cloverproof-backup` — cents/month, no new vendor, but same account (no protection from account compromise, no object lock). (b) Off-platform object storage with object lock / write-only keys (e.g. Backblaze B2 or Cloudflare R2) — new vendor, estimated < $1/month at pilot volume (verify current pricing). (c) only L5. | (b) + L5. If no new vendor: (a) + L5. |
| D2 | PostGIS image | plain `postgis/postgis:17-3.5` (no TLS, no PITR) vs own image on Railway `postgres-ssl:17` + `postgresql-17-postgis-3` (TLS, possibly PITR) | Evaluate the derived image in S3 staging; fall back to plain image + L1/L3. |
| D3 | Enable L1 volume backup schedules on `postgis` (and on the old `Postgres` until it is deleted) | — | Yes, at service creation (runbook step 1 already says so). |
| D4 | Retention of dumps and PDF copies | evidence vs PII minimisation | Ask `legal-compliance-specialist`; proposal above. |
| D5 | A `staging` Railway environment for drills (and PR base) | extra services ≈ small monthly cost (estimate; read on the usage page after a week) | Yes, from S3. |
| D6 | Who holds the age private key | Farjad Iranmehr only vs Farjad + one named deputy | Two holders; losing the only key = no backups. |

## 4. Verification queries (run on the restored copy; never on production)

All in one `psql` session with `set timezone = 'UTC';` (row text of `timestamptz` depends on it). Expected values come from the matching `manifest.json`.

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
select postgis_full_version();
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
-- every version reachable from an engine root
select (select count(*) from recommendation) = (select count(*) from recommendation_diff) as all_reachable;
-- engine rows have no parent, agronomist rows have one
select count(*) from recommendation where (kind = 'engine') <> (parent_id is null);
-- children are not older than parents
select count(*) from recommendation c join recommendation p on p.id = c.parent_id where c.created_at < p.created_at;
-- an 'edit' review points at a child of the reviewed recommendation
select count(*) from review r join recommendation c on c.id = r.resulting_recommendation_id
where r.decision = 'edit' and c.parent_id is distinct from r.recommendation_id;
-- at most one approval per recommendation
select count(*) from (select recommendation_id from review where decision = 'approve' group by 1 having count(*) > 1) x;
-- proof documents only for approved recommendations
select count(*) from proof_document d
where not exists (select 1 from review r where r.recommendation_id = d.recommendation_id and r.decision = 'approve');
-- storage key carries the stored hash
select count(*) from proof_document where storage_key <> format('proof/%s/%s/%s.pdf', organisation_id, recommendation_id, sha256);
-- calibration dataset size (compare to manifest)
select count(*) from recommendation_diff where approved_at is not null;
-- warning only (membership is mutable): approvals whose reviewer is no longer an agronomist
select count(*) from review r where r.decision = 'approve'
and not has_org_role(r.reviewer_id, r.organisation_id, 'agronomist');
```

V5 — proof PDFs re-hashed against the restored DB (shell; `DRILL_PDF_DIR` = local folder holding the restored PDF copy):
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
# Orphans (PDF without a DB row) are reported, not failed: an upload can succeed before its transaction rolls back.
```
Pass = zero `MISSING`, zero `MISMATCH`.

V6 — PostGIS data:
```sql
select count(*) from field_geometry_version where geom is not null and not st_isvalid(geom);  -- 0
```

## 5. Restore drill procedure

### 5.1 Drill A — offsite dump into local Docker (default; proves L3/L4 and off-platform recovery)
Operator: `cp-database` with Farjad Iranmehr (he holds the age key). Machine: FileVault on. Never put a production URL in this shell.

```sh
# All variables defined here. DRILL_DUMP / DRILL_MANIFEST / DRILL_AGE_KEY are local file paths.
DRILL_DIR="$HOME/cp-drill"
DRILL_DUMP="$DRILL_DIR/cloverproof-<UTC timestamp>.dump.age"
DRILL_MANIFEST="$DRILL_DIR/cloverproof-<UTC timestamp>.manifest.json.age"
DRILL_AGE_KEY="$DRILL_DIR/age-key.txt"          # copied from the password manager for the drill, deleted after
DRILL_PORT=55433                                  # not 5432/55432: avoids local dev DBs
DRILL_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:${DRILL_PORT}/cloverproof_restore"

date -u +"start %FT%TZ"                           # RTO clock starts
age -d -i "$DRILL_AGE_KEY" -o "$DRILL_DIR/db.dump" "$DRILL_DUMP"
age -d -i "$DRILL_AGE_KEY" -o "$DRILL_DIR/manifest.json" "$DRILL_MANIFEST"

docker run -d --name cp-drill -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=cloverproof \
  -p 127.0.0.1:${DRILL_PORT}:5432 postgis/postgis:17-3.5
until docker exec cp-drill pg_isready -U postgres -d cloverproof; do sleep 2; done
# Fresh database from template0: the postgis image pre-installs extra extensions in POSTGRES_DB,
# which would collide with the dump.
docker exec cp-drill createdb -U postgres -T template0 cloverproof_restore

# pg_dump does not carry roles: create them first so ownership and grants restore as in production.
psql "$DRILL_DATABASE_URL" -v ON_ERROR_STOP=1 -c "
  create role cp_migrator nologin; create role cp_app nologin;
  create role cp_website nologin; create role cp_backup nologin;"
# Extra roles that production does not have yet are harmless.

docker cp "$DRILL_DIR/db.dump" cp-drill:/tmp/db.dump
docker exec cp-drill pg_restore -U postgres -d cloverproof_restore --exit-on-error /tmp/db.dump
date -u +"db restored %FT%TZ"
```
Then: download the PDF copy from the backup destination into `$DRILL_DIR/pdf/` (read-only credential), run V1–V6, compare with `manifest.json`, `date -u` = RTO clock stops.

Teardown (mandatory, the data includes PII):
```sh
DRILL_DIR="$HOME/cp-drill"
docker rm -f cp-drill
rm -rf "$DRILL_DIR"
```

Expected trouble to note, not hide: `pg_restore` of `postgis` objects (extension version must match 3.5), `spatial_ref_sys` rows, role names missing, generated column `n_rate_kg_ha` (pg_dump skips it, value recomputed — V2 digests include it and must still match).

### 5.2 Drill B — Railway volume backup restore in `staging` (proves L1; needs D5)
Volume backups restore only into the same project + environment and redeploy that service, so this drill runs **only** in `staging`, never `production`.
1. In `staging`: `postgis` service with volume; apply migrations; load `db/seeds/dev.sql` + a synthetic recommendation → review → proof chain (made by `cp-database`, no real farm data).
2. Take a manual backup; record V1/V2 output.
3. Change data (insert one extra synthetic recommendation via the migration role); note it.
4. Restore the backup from the service's Backups tab; review the staged change; Deploy.
5. Run V1–V4: counts/digests equal step 2; the step-3 row is gone. Confirm the previous volume is kept unmounted. Record duration.
6. If D2 gives PITR: restore to a timestamp between steps 2 and 3 → new service; run V1–V4 on it; delete that service afterwards.

### 5.3 Real incident (outline only; the full runbook comes after the S5 rehearsal)
Stop writes (scale `app` to 0 or maintenance flag) → take a manual volume backup of the damaged state → restore into a **new** service (PITR or offsite dump) → run V1–V6 → switch `app`/`website` `DATABASE_URL` reference to the new service → keep the damaged service until Farjad Iranmehr approves deletion. Every step Needs OK.

## 6. Schedule (sprint dates assumed: consecutive 2-week sprints after S1 Nov 16–27 → S3 ≈ Dec 14–25, S4 ≈ Dec 28–Jan 8, S5 ≈ Jan 11–22; adjust to the real sprint plan)

| When | What | Owner | Exit |
|---|---|---|---|
| S2 | D1–D6 decided; this plan approved by `ciso` | Farjad Iranmehr, `ciso` | decisions recorded (ADR or this file) |
| S3 | `staging` env; backup job (L3/L4) against staging; **first drill A** (synthetic data) + drill B | `cp-platform`, `cp-database` | evidence filed; failures turned into tasks |
| S4 | `postgis` in production with L1 schedules on; backup job live in production; drill A on the first production dump (DB nearly empty) | Farjad Iranmehr (setup), `cp-database` | evidence filed |
| S5 | **Rehearsal**: timed drill A + drill B (+ PITR if adopted), RPO/RTO measured against §2.3; failure alert tested by breaking the job once in staging | `cp-database`, `cp-qa` observes | `ciso` sign-off = go-live gate item for 2027-02-01 |
| Pilot Feb–Apr 2027 | Drill A monthly (first working week), L5 cold copy monthly; drill A again after any migration touching immutable tables | `cp-database`, Farjad Iranmehr | evidence per drill |

## 7. Owners

| Role | Who |
|---|---|
| Approves cost, Railway settings, new services/vendors; holds age key; L5 cold copy | Farjad Iranmehr |
| Backup job, roles (`cp_backup`), verification queries, drills | `cp-database` |
| Railway services (`backup`, `staging`), cron, alerting | `cp-platform` |
| Independent check of drill evidence | `cp-qa` |
| Sign-off, retention questions routed to legal | `ciso` |
| Keeps this plan and the incident runbook current | `devops-engineer` |

## 8. Evidence to file per drill
The repo is public: the committed record holds **no PII, no secrets, no hostnames with credentials, no bucket names**. Full outputs go to Notion via `documentation-manager`.

`docs/security/evidence/drill-<YYYY-MM-DD>-<A|B>.md`:
- date, operator, environment (local Docker / Railway `staging`), image digest used;
- backup used: UTC timestamp and SHA-256 of the encrypted dump file;
- V1 counts and V2 digests: restored vs manifest (equal / not equal per table);
- V3, V4, V6 results (0 / `true` per check); V5 totals (`OK` / `MISSING` / `MISMATCH` / orphans);
- measured RTO (start → verified) and RPO (dump timestamp → simulated failure time);
- problems found, tasks opened, teardown confirmed (container + decrypted files deleted);
- sign-off: `cp-qa` checked, `ciso` accepted.
