# Least-privilege database role for the public website (`cp_website`)

Owner of this spec: `security-engineer` (reports to `ciso`). Date: 2026-11-16. Status: PROPOSED.
Adopters: `cp-database` (migration + tests), operator / Farjad Iranmehr (password, Railway variable), `cp-website` (pre-deploy removal, `DATABASE_URL`).
Closes: T-W3 / T-H6 in `docs/security/threat-model-webapp.md`. **Blocker:** do not run step 4 of `docs/runbook-db-switch.md` (step 4.1 sets the website `DATABASE_URL` to `${{postgis.DATABASE_URL}}`, i.e. the PostGIS superuser) until §8 of this spec passes on the target database.

## 1. What the website actually needs (evidence)

| Fact | Evidence | Consequence |
|---|---|---|
| One statement, plain `INSERT`, no `RETURNING`, no `ON CONFLICT` | `website/src/app/[lang]/actions.ts:39-44` | `INSERT` on 9 columns only. No `SELECT` at all. |
| Columns written: `locale, full_name, email, country, farm_size_text, main_crop, notes, consent_at, consent_text` | same | Column-level `INSERT`. `id`, `created_at`, `status`, `deleted_at` are filled by defaults; the website cannot set `status = 'accepted'`, back-date `created_at` or set `deleted_at`. |
| `id uuid default gen_random_uuid()` | `db/migrations/0001_pilot_request.sql:5` | No sequence → no `USAGE` on a sequence. `gen_random_uuid()` is built in (EXECUTE to PUBLIC by default). |
| Pool `max: 5` per process | `website/src/lib/db.ts:10` | `CONNECTION LIMIT 10` = one replica + overlap during a deploy. Raise only if replicas > 1. |
| `pilot_request` owned by the deploy superuser (0001 has no `set local role cp_migrator`) | `db/migrations/0001_pilot_request.sql` vs `0003+` | Not a blocker for this spec. Flag for `cp-database`: forward migration `alter table pilot_request owner to cp_migrator` before ADR 0008 applies FORCE RLS. |

Postgres privilege rules relied on (PostgreSQL 17 docs):
- "If a column list is specified, you only need `INSERT` privilege on the listed columns." "Each column not present in the explicit or implicit column list will be filled with a default value." "Use of the `RETURNING` clause requires `SELECT` privilege on all columns mentioned in `RETURNING`." — https://www.postgresql.org/docs/17/sql-insert.html
- Defaults to `PUBLIC`: "`CONNECT` and `TEMPORARY` ... for databases; `EXECUTE` privilege for functions and procedures". Tables, sequences, columns: none. — https://www.postgresql.org/docs/17/ddl-priv.html
- PG 15+ (`postgis/postgis:17-3.5`): schema `public` gives `PUBLIC` only `USAGE`, no `CREATE`. The migration still revokes `CREATE` explicitly so the file is correct on any server.

**RLS on `pilot_request`: not needed for the website.** With no `SELECT` and a column-level `INSERT` that excludes `status` / `deleted_at`, the role can neither read rows nor create rows in a state other than `new`. RLS would add nothing. Interaction with ADR 0008: if ADR 0008 enables RLS on every table, `pilot_request` gets exactly one policy for this role — `create policy pilot_request_website_insert on pilot_request for insert to cp_website with check (status = 'new' and deleted_at is null);` — and no `SELECT` policy. Without that policy the default-deny would break the form.

## 2. Role design

One role, `cp_website`, that is itself the login role and holds the grants directly. It is a member of no other role. (The threat model and `railway-hardening.md` called it `cp_website_login`; a separate NOLOGIN group would require `INHERIT` and buys nothing for a single-statement client. If `cp-database` prefers the `cp_app` / `cp_app_login` pattern for consistency, the group must be granted to the login with `INHERIT` and the login must hold nothing else; all checks in §6–§7 still apply to the login role.)

| Attribute | Value | Why |
|---|---|---|
| `LOGIN` | yes, **password set outside git** (§4) | The migration creates the role without a password; password auth fails until the operator sets one. |
| `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS` | explicit | Re-asserted even if the role already exists. |
| `NOINHERIT` + no memberships | explicit, plus a loop that revokes any membership found | Cannot pick up `cp_app` / `cp_migrator` by mistake. |
| `CONNECTION LIMIT 10` | §1 | Bounds connection exhaustion from a flood on the public form; superusers are not affected, so the operator can still get in. |
| `statement_timeout = 5s`, `lock_timeout = 2s`, `idle_in_transaction_session_timeout = 10s` | role-level `ALTER ROLE ... SET` | One small insert needs milliseconds. Note: role settings are defaults, not a boundary — the session may `SET` them. Acceptable: the website code never does. |
| `search_path = public` | role-level | No writable schema exists for this role anyway (§3: no `CREATE` on database or schema). |
| Database: `CONNECT` yes; `CREATE`, `TEMPORARY` no | revoke from `PUBLIC`, grant `CONNECT` to the three roles | Removes the PUBLIC defaults for every non-superuser. |
| Schema `public`: `USAGE` only | | |
| `pilot_request`: `INSERT` on 9 columns | no `SELECT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER` | |

## 3. Proposed forward-only migration (for `cp-database` to adopt)

Filename: **`db/migrations/0011_website_role.sql`** (`0010` is already used by `0010_password_change_required.sql` on `origin/webapp-step5-app`; take the next free number at merge time; the runner rejects duplicate numbers).

Must be applied by a **superuser** (creates a role, changes database ACL), like `0002`. If the planned `migrate` service holds only `cp_migrator_login`, the operator applies this file once through `railway connect postgis` with `make db-migrate`; the guard below makes it fail loudly otherwise. It runs in one transaction (runner: one transaction per file); all statements below are transaction-safe. It does **not** end in `set local role cp_migrator` because nothing in it is owned by `cp_migrator`.

```sql
-- Least-privilege role for the public website (docs/security/website-db-role-spec.md).
-- The website may only INSERT a pilot request: 9 columns, no SELECT, no other table.
-- Applied by a superuser. The role has no password here; the operator sets it outside git
-- with psql \password (see the spec, section 4).

do $$
begin
  if not (select rolsuper from pg_roles where rolname = current_user) then
    raise exception 'website role migration must run as a superuser (creates a role, changes database privileges)';
  end if;
  if not exists (select 1 from pg_roles where rolname = 'cp_website') then
    create role cp_website;
  end if;
end
$$;

alter role cp_website with
  login nosuperuser nocreatedb nocreaterole noinherit noreplication nobypassrls
  connection limit 10;

alter role cp_website set statement_timeout = '5s';
alter role cp_website set lock_timeout = '2s';
alter role cp_website set idle_in_transaction_session_timeout = '10s';
alter role cp_website set search_path = public;

-- cp_website is a member of no role.
do $$
declare
  g record;
begin
  for g in
    select r.rolname
    from pg_auth_members m
    join pg_roles r on r.oid = m.roleid
    where m.member = 'cp_website'::regrole
  loop
    execute format('revoke %I from cp_website', g.rolname);
  end loop;
end
$$;

-- Database: remove the PUBLIC defaults (CONNECT, TEMPORARY) and CREATE; grant CONNECT by name.
-- cp_app and cp_migrator logins inherit CONNECT from their group roles.
do $$
begin
  execute format('revoke create, temporary, connect on database %I from public', current_database());
  execute format('grant connect on database %I to cp_app, cp_migrator, cp_website', current_database());
end
$$;

-- Schema: no CREATE for anyone but cp_migrator (already granted in 0002).
revoke create on schema public from public;
grant usage on schema public to cp_website;

-- Table: column-level INSERT only. id, created_at, status, deleted_at come from defaults.
revoke all on table pilot_request from cp_website;
grant insert (locale, full_name, email, country, farm_size_text, main_crop, notes, consent_at, consent_text)
  on table pilot_request to cp_website;

comment on role cp_website is
  'Public website. INSERT on 9 pilot_request columns only. No SELECT. Password set outside git.';
```

Side effects to check in the same PR:
- `cp_app` loses `TEMPORARY` (it came from `PUBLIC`). The app does not use temp tables today; if a future feature needs them, grant `temporary` to `cp_app` explicitly.
- A future `cp_backup` role (railway-hardening §3) needs its own `grant connect`.
- `spatial_ref_sys` (PostGIS) keeps `SELECT` for `PUBLIC`; public reference data, accepted. `pg_catalog` stays readable (schema names, column names); accepted, the schema is in a public repo anyway.

## 4. Password: generation, setting, storage

1. Generate on the operator laptop: `openssl rand -hex 32` (64 hex chars; no URL escaping needed). Do not paste it into chat, tickets or shell history files (`HISTCONTROL=ignorespace` / leading space).
2. Set it without the plaintext reaching the server log: `railway connect postgis` (SSH tunnel, no TCP proxy), then in `psql`: `\password cp_website`. `\password` sends a SCRAM verifier, not the password. Confirm first: `show password_encryption;` → `scram-sha-256` (PG 14+ default).
3. Store it **only** on the `website` service as a **sealed** Railway variable `CP_WEBSITE_DB_PASSWORD` (not a shared variable, not on `app`, `migrate` or `postgis`). Railway: a sealed value "is provided to builds and deployments but is never visible in the UI nor can it be retrieved via the API"; it is not returned by `railway variables` / `railway run`, and not copied to duplicated or PR environments (https://docs.railway.com/variables). Never in git, never in `.env.example` (empty key only).
4. Staging and production get different passwords.
5. Rotation: on any suspected website compromise, any Next.js/`pg` CVE with RCE, and when a person with Railway access leaves. Procedure: `\password cp_website` → update the sealed variable → redeploy `website`.

## 5. Website `DATABASE_URL`

On the `website` service:

```
DATABASE_URL=postgresql://cp_website:${{CP_WEBSITE_DB_PASSWORD}}@${{postgis.RAILWAY_PRIVATE_DOMAIN}}:5432/${{postgis.POSTGRES_DB}}
```

- Private network only; no TCP proxy. No `sslmode=require`: the `postgis` image ships with `ssl=off` (railway-hardening §4), so it would fail; traffic stays on Railway's private network.
- I don't know whether Railway resolves a reference to a *sealed* variable inside another variable. Test once in staging (submit the form). If it does not, seal `DATABASE_URL` itself with the full literal value instead.
- The website must never reference `${{postgis.DATABASE_URL}}`, `${{postgis.POSTGRES_PASSWORD}}` or any `cp_migrator` / `cp_app` credential.
- Recommended for `cp-website` (not part of this spec's scope): refuse to start in production if `current_user <> 'cp_website'` or the role is superuser (mirror of T-O3 for the app).

## 6. Migrations never run with the website credential

- **Remove the website pre-deploy `npm run db:migrate` before (or in the same deploy as) the `DATABASE_URL` switch.** Runbook step 4.2 says leaving it is "harmless"; with `cp_website` it is not harmless — `website/scripts/migrate.mjs` runs `create table if not exists schema_migrations` (needs `CREATE` on the schema) and reads `schema_migrations` (needs `SELECT`), so the pre-deploy is expected to fail and block every website deploy. Flag for `cp-website` / runbook owner; this spec does not edit the runbook.
- **No migrator credential on the `website` service, ever.** Railway pre-deploy commands run with the service's own environment variables (railway-hardening §6), so a "separate migrator URL" on the website service is readable by the running website and defeats this spec. Migrations run only from the `migrate` service (holds `cp_migrator_login`) or by the operator; role/ACL migrations like this one by the operator as superuser.
- After the switch, delete `website/db/migrations/` and `website/scripts/migrate.mjs` and the `db:migrate` script (runbook step 4.3).

## 7. Verification queries (run as superuser on the target DB; all must match)

```sql
-- 7.1 Role attributes: expect f,f,f,f,f,f,t,10 (rolinherit = f)
select rolsuper, rolinherit, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls, rolcanlogin, rolconnlimit
from pg_roles where rolname = 'cp_website';

-- 7.2 Password set and SCRAM: expect t
select rolpassword like 'SCRAM-SHA-256$%' from pg_authid where rolname = 'cp_website';

-- 7.3 Memberships: expect 0
select count(*) from pg_auth_members where member = 'cp_website'::regrole;

-- 7.4 Role settings: expect statement_timeout=5s, lock_timeout=2s, idle_in_transaction_session_timeout=10s, search_path=public
select unnest(setconfig) from pg_db_role_setting where setrole = 'cp_website'::regrole and setdatabase = 0;

-- 7.5 Database: expect connect=t, create=f, temp=f
select has_database_privilege('cp_website', current_database(), 'CONNECT')   as connect,
       has_database_privilege('cp_website', current_database(), 'CREATE')    as create,
       has_database_privilege('cp_website', current_database(), 'TEMPORARY') as temp;

-- 7.6 Schema: expect usage=t, create=f
select has_schema_privilege('cp_website', 'public', 'USAGE'), has_schema_privilege('cp_website', 'public', 'CREATE');

-- 7.7 pilot_request: expect table-level INSERT=f, any-column INSERT=t, any-column SELECT=f, and f for the rest
select has_table_privilege('cp_website', 'pilot_request', 'INSERT')         as tbl_insert,
       has_any_column_privilege('cp_website', 'pilot_request', 'INSERT')    as col_insert,
       has_any_column_privilege('cp_website', 'pilot_request', 'SELECT')    as any_select,
       has_any_column_privilege('cp_website', 'pilot_request', 'UPDATE')    as any_update,
       has_table_privilege('cp_website', 'pilot_request', 'DELETE')         as del,
       has_table_privilege('cp_website', 'pilot_request', 'TRUNCATE')      as trunc,
       has_table_privilege('cp_website', 'pilot_request', 'REFERENCES')     as refs,
       has_table_privilege('cp_website', 'pilot_request', 'TRIGGER')        as trig;

-- 7.8 Exactly these 9 insertable columns; expect the 9 names, and not id/created_at/status/deleted_at
select attname from pg_attribute
where attrelid = 'pilot_request'::regclass and attnum > 0 and not attisdropped
  and has_column_privilege('cp_website', 'pilot_request', attname, 'INSERT')
order by attnum;

-- 7.9 Every other relation in non-system schemas: expect only spatial_ref_sys / geometry_columns /
-- geography_columns with SELECT (PostGIS, PUBLIC), and nothing else
select n.nspname, c.relname, p.priv
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
cross join unnest(array['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER']) as p(priv)
where n.nspname not in ('pg_catalog', 'information_schema') and n.nspname not like 'pg_toast%'
  and c.relkind in ('r', 'p', 'v', 'm', 'f')
  and has_any_column_privilege('cp_website', c.oid, p.priv)
  and c.relname <> 'pilot_request'
order by 1, 2, 3;

-- 7.10 Sequences: expect 0 rows
select c.relname from pg_class c
where c.relkind = 'S' and has_sequence_privilege('cp_website', c.oid, 'USAGE');

-- 7.11 No other non-superuser role can create in public or the database: expect only cp_migrator
select rolname from pg_roles
where not rolsuper and (has_schema_privilege(oid, 'public', 'CREATE') or has_database_privilege(oid, current_database(), 'CREATE'));
```

## 8. Negative and positive tests (`cp-database`, `app/tests/db/test_website_role.py`, runs in `make db-test`)

Harness: the existing superuser test DB with all migrations applied. Statement-level tests use `set local role cp_website` inside a rolled-back transaction (the role, not a membership, is what is tested). Login-level tests (T13–T15) set a random password in the test, connect with a real `cp_website` URL, and drop nothing (test DB is disposable).

| # | Statement as `cp_website` | Expected |
|---|---|---|
| T1 | the exact `insert` from `actions.ts:40-43` with valid values | succeeds; row has `status = 'new'`, `deleted_at is null` |
| T2 | same insert `returning id` | `42501` (proves the code must not add `RETURNING`) |
| T3 | `select * from pilot_request` / `select count(*) from pilot_request` / `select id from pilot_request` | `42501` each |
| T4 | insert listing `status` (value `'accepted'`), then `created_at`, then `deleted_at`, then `id` | `42501` each |
| T5 | `update pilot_request set status = 'accepted'`; `delete from pilot_request`; `truncate pilot_request` | `42501` each |
| T6 | `insert ... on conflict (id) do nothing` | `42501` (conflict target needs SELECT on `id`). Plain `on conflict do nothing` without a target may succeed; harmless (no readable result, only `id` is unique) |
| T7 | `copy pilot_request to stdout` | `42501` |
| T8 | `select * from app_user`, `user_session`, `membership`, `farm`, `recommendation`, `review`, `recommendation_diff`, `schema_migrations` | `42501` each |
| T9 | `insert into review (...)`, `insert into membership (...)`, `insert into schema_migrations values ('x')` | `42501` each |
| T10 | `create table x (a int)`; `create schema s`; `create temp table t (a int)`; `create function f() returns int language sql as 'select 1'` | `42501` each |
| T11 | `set role cp_app`; `set role cp_migrator`; `set role postgres` | `42501` each |
| T12 | `select pg_read_file('/etc/passwd')`; `select pg_ls_dir('.')` | `42501` each |
| T13 | real login, `show statement_timeout` / `show lock_timeout` / `show idle_in_transaction_session_timeout` | `5s` / `2s` / `10s` |
| T14 | real login, `select pg_sleep(6)` | `57014` (statement timeout) |
| T15 | real login as `cp_website` against the database with connections at limit (open 10, try 11th) | connection refused, `53300` |
| T16 | catalog assertions §7.1–§7.11 | as listed |

Every test asserts the SQLSTATE, not just "an error", so a test cannot pass on an unrelated failure.

## 9. Order of operations for the switch

1. `cp-database`: merge `0011_website_role.sql` + T1–T16 (CI green).
2. Operator: apply to `postgis` as superuser; run §7 → all match.
3. Operator: password (§4), sealed variable on `website`.
4. `cp-website`: remove pre-deploy `db:migrate`; set `DATABASE_URL` (§5); deploy; submit one test request; operator confirms the row with a superuser query and deletes it.
5. `ciso` sign-off on T-W3 / T-H6. Only then runbook step 5 (old service) can start its one-week clock.

## Adjacent flags (not fixed here)
- `pilot_request` owned by the deploy superuser, not `cp_migrator` (§1).
- `website/src/app/[lang]/actions.ts:48` logs the full `pg` error (PII in `detail`) — T-W4, open.
- Runbook step 2 creates `cp_app_login` with `password '...'` in SQL; prefer `\password` (§4.2) so the plaintext never reaches the server log.
- Runbook step 4.2 "harmless" claim is wrong once the website uses `cp_website` (§6).
