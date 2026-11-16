-- Roles, extensions and shared helpers (ADR 0002).
-- Runs as the deploy user (superuser on the PostGIS service). Later migrations switch to
-- cp_migrator with `set local role cp_migrator;` so it owns every app object.
--
-- Roles are NOLOGIN and have no password here. To let the app log in, an operator runs
-- (outside git, password from the secret store):
--   create role cp_app_login login password '...' in role cp_app;
-- and points the app's DATABASE_URL at cp_app_login.

create extension if not exists postgis;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'cp_migrator') then
    create role cp_migrator nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'cp_app') then
    create role cp_app nologin;
  end if;
end
$$;

-- The deploy user must be able to `set role cp_migrator` (superusers can anyway).
do $$
begin
  if not pg_has_role(current_user, 'cp_migrator', 'member') then
    execute format('grant cp_migrator to %I', current_user);
  end if;
end
$$;

grant usage, create on schema public to cp_migrator;
grant usage on schema public to cp_app;
-- Migration files end in `set local role cp_migrator`; the runner then records the file in
-- schema_migrations within the same transaction, so cp_migrator must be able to do that.
grant select, insert on schema_migrations to cp_migrator;

-- Shared trigger function: rows of the table it is attached to can never change.
set local role cp_migrator;

create function forbid_change() returns trigger
language plpgsql as $$
begin
  raise exception '% on % is not allowed: rows are immutable; insert a new row instead',
    tg_op, tg_table_name
    using errcode = 'insufficient_privilege';
end
$$;

comment on function forbid_change() is
  'Attached BEFORE UPDATE/DELETE/TRUNCATE on immutable tables (recommendation, review, proof_document).';
