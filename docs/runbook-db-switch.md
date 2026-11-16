# Runbook — move to the shared PostGIS database on Railway

Status: NOT RUN. Each step needs the named owner; the website switch needs an agreed window with `cp-website`.
Decisions: ADR 0002, ADR 0004, ADR 0006 (database roles), `docs/plans/webapp-v1.md` §5. Never commit passwords or URLs with credentials.

**The superuser URL is never a variable of the app or the website service.** It is used only by an operator to run migrations (step 2). Each service logs in with its own least-privilege login (ADR 0006):

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

## 3. Move `pilot_request` (with `cp-website`, in an agreed window of a few minutes)
1. Pause website writes (maintenance flag or accept a short failure window).
2. `pg_dump --data-only --table=pilot_request <old URL> | psql <postgis URL>` (table already exists from 0001).
3. Check row counts match on both sides.

## 4. Switch the website (`cp-website`)
Precondition: `cp_website_login` exists (step 2). Never point the website at `${{postgis.DATABASE_URL}}` (that is the superuser).
1. Website `DATABASE_URL` → `postgresql://cp_website_login:${{CP_WEBSITE_DB_PASSWORD}}@${{postgis.RAILWAY_PRIVATE_DOMAIN}}:5432/${{postgis.POSTGRES_DB}}`.
   The form's insert must not use `RETURNING` (the role has no SELECT).
2. Remove the website pre-deploy `npm run db:migrate`; `db/migrations/` is now the single source and the Python runner applies it.
   (If left in place it is harmless: it only sees `website/db/migrations/0001`, already recorded in `schema_migrations`.)
3. Delete `website/db/migrations/` in a later PR, once the website no longer runs it.
4. Deploy, submit a test pilot request, confirm it lands in `postgis` (check as the operator; the website login cannot read the table).

## 5. Old `Postgres` service
Keep it until Farjad Iranmehr approves deletion (at least one week after the switch, with a final `pg_dump` saved).
