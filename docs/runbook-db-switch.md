# Runbook — move to the shared PostGIS database on Railway

Status: NOT RUN. Each step needs the named owner; the website switch (step 3) needs Farjad Iranmehr's go and `cp-website` on hand; no write pause is needed.
Decisions: ADR 0002, ADR 0004, ADR 0007 (database roles), `docs/plans/webapp-v1.md` §5. Never commit passwords or URLs with credentials.

**The superuser URL is never a variable of the app or the website service.** It is used only by an operator to run migrations (step 2). Each service logs in with its own least-privilege login (ADR 0007):

| Who | Login | Member of | Can |
|---|---|---|---|
| Web app (`app/`) | `cp_app_login` | `cp_app` | farm data; read users/roles; no approver grants |
| Admin CLI (`user-create`) | `cp_admin_login` | `cp_admin` | `cp_app` + organisations, memberships, users (agronomist/owner roles) |
| Website (pilot form) | `cp_website_login` | `cp_website` | INSERT into `pilot_request` only |
| Operator, migrations | `postgres` (superuser) | — | everything; never stored in a service |

## 1. Create the PostGIS service — DONE 2026-11-16 (CPO session, Farjad Iranmehr approved)
Live service: **`PostGIS-cXKk`** (id `85ebd5a9-7fe9-4176-a377-34905ff81969`, image `postgis/postgis:18-3.7`, pre-18 `PGDATA` layout under `/var/lib/postgresql/data`, database **`railway`**). The first service `PostGIS` (`65b71098…`, 18-3.6) failed with a Railway infra error — do not use; delete only with Farjad Iranmehr's OK.
`${{PostGIS-cXKk.DATABASE_PRIVATE_URL}}` is the **superuser** URL: never set it on the app or website service. Below, `postgis` means `PostGIS-cXKk` and `POSTGRES_DB` is `railway`.
Original instructions, kept for a rebuild:
Project `cloverproof`, environment `production`:
- New service → Docker image `postgis/postgis:18-3.6` (same as local `docker-compose.yml` and CI), name `postgis`.
- Variables: `POSTGRES_USER=postgres`, `POSTGRES_DB=cloverproof`, `POSTGRES_PASSWORD=<random, 32+ chars>`, `PGDATA=/var/lib/postgresql/data/pgdata`,
  `DATABASE_URL=postgresql://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@${{RAILWAY_PRIVATE_DOMAIN}}:5432/${{POSTGRES_DB}}`.
- Volume: for Postgres 18 images mount it at `/var/lib/postgresql` (data lives in `/var/lib/postgresql/18/docker`; then do not set `PGDATA`). Enable volume backups.
- No public TCP proxy unless needed for a one-off migration; remove it afterwards.

## 2. Apply migrations and create the logins (lead / `cp-database`)
From the operator's machine (temporary TCP proxy, removed afterwards), with the superuser URL only in that shell:
`DATABASE_URL=<postgis superuser URL> make db-migrate`. Expected: 0001 … 0011 applied, `select postgis_version();` returns 3.6.
Do not put the superuser URL in the app's pre-deploy command or any service variable; until a dedicated deploy role exists, migrations are run this way by an operator.

Create the three logins outside git, in `psql` as the superuser (generate each password with `openssl rand -base64 32`, store it only in Railway variables / the password manager):
```sql
create role cp_app_login     login password '<app secret>'     in role cp_app;
create role cp_admin_login   login password '<admin secret>'   in role cp_admin;
create role cp_website_login login password '<website secret>' in role cp_website;
alter role cp_app_login     connection limit 20;
alter role cp_admin_login   connection limit 2;
alter role cp_website_login connection limit 10;
```
Check: `select rolname, rolsuper, rolcreaterole, rolbypassrls from pg_roles where rolname like 'cp\_%';` — all three logins `f, f, f`.

Service variables (Railway reference syntax; password variables set by hand, never in git):
- App service: `DATABASE_URL=postgresql://cp_app_login:${{CP_APP_DB_PASSWORD}}@${{postgis.RAILWAY_PRIVATE_DOMAIN}}:5432/${{postgis.POSTGRES_DB}}`.
- Admin CLI: not a service. Run `make user-create` from the operator's machine (TCP proxy) or `railway run`, with `DATABASE_URL` for `cp_admin_login` set in that shell only. Adding or removing `agronomist`/`owner` is done only here.

## 3. Switch the website, then copy `pilot_request` (`cp-website`; rehearsed locally 2026-11-17)
Order: **switch first, copy after.** Once the website points at `postgis`, the old database gets no more writes, so no write pause is needed and no request is lost. Rows the website writes to `postgis` after the switch are kept: the copy skips existing ids.

### 3a. Switch the website
Precondition: `cp_website_login` exists (step 2). Never point the website at `${{postgis.DATABASE_URL}}` or `DATABASE_PRIVATE_URL` (both are the superuser).
1. Write down the website's current `DATABASE_URL` value (needed for rollback).
2. **Remove the website pre-deploy command `npm run db:migrate`** (Settings → Deploy) before or together with the variable change. It is NOT harmless: its first statement is `create table if not exists schema_migrations`, and `cp_website` has no CREATE on schema `public`, so it fails with `permission denied for schema public` (42501) and Railway fails the deploy. `db/migrations/` is the single source; the operator applies it with the Python runner (step 2).
3. Website variables: `CP_WEBSITE_DB_PASSWORD` (sealed) and
   `DATABASE_URL=postgresql://cp_website_login:${{CP_WEBSITE_DB_PASSWORD}}@${{postgis.RAILWAY_PRIVATE_DOMAIN}}:5432/railway`.
   No other variable changes. The form's insert has no `RETURNING` (the role has no SELECT).
4. Deploy, then run the smoke tests in step 4.

### 3b. Copy the old rows
In a shell that reaches both databases (e.g. `railway ssh` into `postgis`, where `DATABASE_URL` is that service's own superuser URL), with credentials only in that shell:
```sh
OLD_DB_URL='<old Postgres private URL>' NEW_DB_URL="$DATABASE_URL" sh ops/copy-pilot-requests.sh
```
(Copy the script into the shell first if the repo is not there; it needs only `psql`.) It reads the old database only and writes `postgis` in one transaction, copying all 13 columns (incl. `status`, `deleted_at`). It is idempotent (`ON CONFLICT (id) DO NOTHING`).
**Verify:** it prints `old|N|<md5>`, `staged|N|<md5>`, `landed|N|<md5>` — all three equal — then `copy: committed`. On any difference it prints `mismatch: rolled back` and writes nothing.

### 3c. Rollback
1. Put the old `DATABASE_URL` back and restore the pre-deploy command, then redeploy.
2. Copy requests received on `postgis` since the switch back to the old database: run the same script with the URLs swapped (`OLD_DB_URL` = postgis, `NEW_DB_URL` = old).

## 4. Smoke tests after the switch (`cp-website` + operator)
1. Health check `/en` returns 200, and the deploy log shows no pre-deploy step.
2. Submit the pilot form on `/en` and on one other locale (e.g. `/ar`) and check the success message. As the operator, confirm the rows landed in `postgis` (`select locale, created_at from pilot_request order by created_at desc limit 2`; the website login cannot read the table), then remove or mark the test rows.
3. `site_event`: the website does not write it yet, so check the grant as the operator in a rolled-back transaction:
   `begin; set local role cp_website; insert into site_event (event, locale, path, is_test) values ('page_view', 'en', '/en', true); rollback;`
4. `/admin/login` still shows "Admin not configured" (admin variables come later, under ciso's conditions).
5. Delete `website/db/migrations/` and the `db:migrate` script in a later PR, once the website no longer runs them.

## 5. Old `Postgres` service
Keep it until Farjad Iranmehr approves deletion (at least one week after the switch, with a final `pg_dump` saved).
