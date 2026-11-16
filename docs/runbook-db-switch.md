# Runbook — move to the shared PostGIS database on Railway

Status: NOT RUN. Each step needs the named owner; the website switch needs an agreed window with `cp-website`.
Decisions: ADR 0002, ADR 0004, `docs/plans/webapp-v1.md` §5. Never commit passwords or URLs with credentials.

## 1. Create the `postgis` service (Farjad Iranmehr, Railway dashboard — the CLI action is blocked for agents)
Project `cloverproof`, environment `production`:
- New service → Docker image `postgis/postgis:17-3.5`, name `postgis`.
- Variables: `POSTGRES_USER=postgres`, `POSTGRES_DB=cloverproof`, `POSTGRES_PASSWORD=<random, 32+ chars>`, `PGDATA=/var/lib/postgresql/data/pgdata`,
  `DATABASE_URL=postgresql://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@${{RAILWAY_PRIVATE_DOMAIN}}:5432/${{POSTGRES_DB}}`.
- Volume mounted at `/var/lib/postgresql/data`. Enable volume backups.
- No public TCP proxy unless needed for a one-off migration; remove it afterwards.

## 2. Apply migrations (lead / `cp-database`)
`DATABASE_URL=<postgis superuser URL> make db-migrate`. Expected: 0001 … 0009 applied, `select postgis_version();` returns 3.5.
Create the app login outside git: `create role cp_app_login login password '<secret>' in role cp_app;` — the web app uses this, not the superuser.

## 3. Move `pilot_request` (with `cp-website`, in an agreed window of a few minutes)
1. Pause website writes (maintenance flag or accept a short failure window).
2. `pg_dump --data-only --table=pilot_request <old URL> | psql <postgis URL>` (table already exists from 0001).
3. Check row counts match on both sides.

## 4. Switch the website (`cp-website`)
1. Website `DATABASE_URL` → `${{postgis.DATABASE_URL}}`.
2. Remove the website pre-deploy `npm run db:migrate`; `db/migrations/` is now the single source and the Python runner applies it.
   (If left in place it is harmless: it only sees `website/db/migrations/0001`, already recorded in `schema_migrations`.)
3. Delete `website/db/migrations/` in a later PR, once the website no longer runs it.
4. Deploy, submit a test pilot request, confirm it lands in `postgis`.

## 5. Old `Postgres` service
Keep it until Farjad Iranmehr approves deletion (at least one week after the switch, with a final `pg_dump` saved).
