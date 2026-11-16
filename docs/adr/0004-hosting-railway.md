# ADR 0004 — Host everything on Railway; Railway Postgres instead of Supabase

- Status: Accepted (2026-11-16)
- Decider: Farjad Iranmehr

## Context
CLAUDE.md chose Supabase (Postgres + PostGIS, Auth, Storage, RLS). A new Supabase project costs $10/month in the Ashavid organisation. Farjad Iranmehr decided to run the whole project on Railway and use Railway's Postgres for now.

## Decision
- Railway project `cloverproof` (environment `production`): services `Postgres` (Railway template) and `website`.
- `website` builds from `farjadp/cloverproof`, root directory `/website`, watch path `/website/**`, health check `/en`.
- `DATABASE_URL` is a Railway reference variable (`${{Postgres.DATABASE_URL}}`); no credentials in git.
- Migrations: plain SQL in `website/db/migrations/`, applied by `npm run db:migrate` as the pre-deploy command, tracked in `schema_migrations`.
- Access control is enforced in application code (server-only database access), not by RLS.

## Consequences
- Supabase Auth, Storage and RLS are no longer assumed. The web app step must pick auth (e.g. a library in the Python app) and file storage (e.g. a Railway bucket) — decided in its own ADR.
- PostGIS: confirm the Railway Postgres image supports the extension before field geometry work; otherwise use a PostGIS image.
- Region: Railway has no Canadian region. The default region is used; revisit for data-residency questions.
- When the Python web app arrives, migrations move out of `website/` to a shared location run by one service.
