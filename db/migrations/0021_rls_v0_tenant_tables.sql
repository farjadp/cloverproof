-- 0021: Postgres row-level security v0 on every org-owned (tenant) table (ADR 0008,
-- CLAUDE.md "Access control"; ciso criteria docs/security/adr-0008-rls-review-criteria.md).
--
-- Context (set by the app per transaction, never per session, only with
-- `select set_config('app.user_id', $1, true), set_config('app.org_id', $2, true),
-- set_config('app.platform_role', $3, true)`):
--   app_ctx_user()           app.user_id as uuid; NULL if unset or '' (after SET LOCAL ends)
--   app_ctx_org()            app.org_id, but only if app_ctx_user() is an enabled member of
--                            that organisation (checked here, not trusted); else NULL
--   app_ctx_is_human()       the context user exists, is enabled and actor_kind = 'human'
--   app_ctx_platform_role()  app.platform_role only if it equals the user's DB column
--                            (narrows, never elevates); NOT used by any policy in v0
-- A garbage value raises 22P02 (invalid uuid); a NULL compares to nothing: deny by default.
--
-- Policies per tenant table T (organisation column O):
--   T_org_boundary   RESTRICTIVE, FOR ALL, TO cp_app: O = (select app_ctx_org()) in USING
--                    and WITH CHECK. Later permissive policies can never widen past it.
--   T_select/_insert/_update/_delete  PERMISSIVE, TO cp_app, one per granted command, with
--                    the same org predicate; INSERT also binds the author column to the
--                    context user (created_by / reviewer_id / granted_by).
--   T_ai_boundary    RESTRICTIVE (farmer, farm, field, field_geometry_version): a non-human
--                    context sees and writes only non-real farmers' rows (rule 12).
-- No policy names app.platform_role: superadmin gets no cross-org reads through cp_app.
-- cp_admin is a member of cp_app, so every policy here applies to the CLI too.
--
-- FORCE ROW LEVEL SECURITY on every tenant table: the owner cp_migrator has no policy and
-- sees nothing (migrations that must read or backfill tenant rows do it as the deploy
-- superuser before `set local role cp_migrator`, ADR 0008 §1.8). Every function and view
-- that reads tenant tables runs as the invoker (security_invoker views; no SECURITY
-- DEFINER function reads a tenant table), so nothing owned by cp_migrator reads tenant
-- rows at run time.
--
-- Identity tables (organisation, app_user, user_session, membership, admin_event) and the
-- website tables are NOT in v0: see db/rls_tables.yaml and ADR 0008 (identity = v1, S3,
-- with SECURITY DEFINER pre-auth lookups; website tables = 0022).
set local role cp_migrator;

-- ---------------------------------------------------------------------------------------
-- Context helpers (stable, pinned search_path, owned by cp_migrator, invoker rights)
-- ---------------------------------------------------------------------------------------

create function app_ctx_user() returns uuid
language sql stable set search_path = pg_catalog, public as $$
  select nullif(current_setting('app.user_id', true), '')::uuid
$$;

create function app_ctx_org() returns uuid
language sql stable set search_path = pg_catalog, public as $$
  select s.org
  from (select nullif(current_setting('app.org_id', true), '')::uuid as org) s
  where exists (
    select 1
    from public.membership m
    join public.app_user u on u.id = m.user_id
    where m.organisation_id = s.org
      and m.user_id = public.app_ctx_user()
      and u.disabled_at is null
  )
$$;

create function app_ctx_is_human() returns boolean
language sql stable set search_path = pg_catalog, public as $$
  select exists (
    select 1 from public.app_user u
    where u.id = public.app_ctx_user() and u.actor_kind = 'human' and u.disabled_at is null
  )
$$;

create function app_ctx_platform_role() returns text
language sql stable set search_path = pg_catalog, public as $$
  select u.platform_role
  from public.app_user u
  where u.id = public.app_ctx_user()
    and u.actor_kind = 'human'
    and u.disabled_at is null
    and u.platform_role = nullif(current_setting('app.platform_role', true), '')
$$;

comment on function app_ctx_org() is
  'RLS: app.org_id if the context user (app.user_id) is an enabled member of it, else NULL. ADR 0008.';
comment on function app_ctx_platform_role() is
  'RLS: app.platform_role only if it equals app_user.platform_role (narrows, never elevates). '
  'Not used by any cp_app policy in v0. ADR 0008.';

revoke execute on function app_ctx_user(), app_ctx_org(), app_ctx_is_human(),
                           app_ctx_platform_role() from public;
grant execute on function app_ctx_user(), app_ctx_org(), app_ctx_is_human(),
                          app_ctx_platform_role() to cp_app;

-- ---------------------------------------------------------------------------------------
-- Indexes: every tenant table has an index whose leading column is its organisation column
-- (ciso 8.1). The others already have unique (organisation_id, id).
-- ---------------------------------------------------------------------------------------

create index soil_test_value_organisation_idx on soil_test_value (organisation_id, soil_test_id);
create index review_organisation_idx on review (organisation_id, recommendation_id);
create index application_log_organisation_idx on application_log (organisation_id, crop_plan_id);
create index proof_document_organisation_idx on proof_document (organisation_id, recommendation_id);

-- ---------------------------------------------------------------------------------------
-- Tenant tables
-- ---------------------------------------------------------------------------------------

do $$
declare
  -- table, organisation column, author column bound on INSERT (or ''), commands granted
  -- to cp_app besides SELECT/INSERT ('update,delete' | 'update' | '').
  t record;
  v_org text;
begin
  for t in
    select * from (values
      ('farmer',                 'organisation_id',       '',            'update,delete'),
      ('farm',                   'organisation_id',       '',            'update,delete'),
      ('field',                  'organisation_id',       '',            'update,delete'),
      ('season',                 'organisation_id',       '',            'update,delete'),
      ('field_geometry_version', 'organisation_id',       '',            'update,delete'),
      ('soil_test',              'organisation_id',       '',            'update,delete'),
      ('soil_test_value',        'organisation_id',       '',            'update,delete'),
      ('crop_plan',              'organisation_id',       '',            'update,delete'),
      ('application_log',        'organisation_id',       'created_by',  'update,delete'),
      ('recommendation',         'organisation_id',       'created_by',  ''),
      ('review',                 'organisation_id',       'reviewer_id', ''),
      ('proof_document',         'organisation_id',       'created_by',  ''),
      ('access_grant',           'owner_organisation_id', 'granted_by',  'update')
    ) as v(tbl, org_col, author_col, extra)
  loop
    v_org := format('%I = (select public.app_ctx_org())', t.org_col);

    execute format('alter table %I enable row level security', t.tbl);
    execute format('alter table %I force row level security', t.tbl);

    -- access_grant has its own boundary below (grantees may read their grants).
    if t.tbl <> 'access_grant' then
      execute format(
        'create policy %I on %I as restrictive for all to cp_app using (%s) with check (%s)',
        t.tbl || '_org_boundary', t.tbl, v_org, v_org);
      execute format('create policy %I on %I for select to cp_app using (%s)',
        t.tbl || '_select', t.tbl, v_org);
    end if;

    execute format('create policy %I on %I for insert to cp_app with check (%s%s)',
      t.tbl || '_insert', t.tbl, v_org,
      case when t.author_col = '' then ''
           else format(' and %I = (select public.app_ctx_user())', t.author_col) end);

    if t.extra like '%update%' and t.tbl <> 'access_grant' then
      execute format('create policy %I on %I for update to cp_app using (%s) with check (%s)',
        t.tbl || '_update', t.tbl, v_org, v_org);
    end if;
    if t.extra like '%delete%' then
      execute format('create policy %I on %I for delete to cp_app using (%s)',
        t.tbl || '_delete', t.tbl, v_org);
    end if;
  end loop;
end
$$;

-- access_grant: the owning organisation reads and writes; a grantee (organisation or user)
-- reads its own grants from its own valid context. Revoke = UPDATE by the owner side only,
-- bound to the context user.
create policy access_grant_org_boundary on access_grant as restrictive for all to cp_app
  using (
    (select public.app_ctx_org()) is not null
    and (owner_organisation_id = (select public.app_ctx_org())
         or grantee_organisation_id = (select public.app_ctx_org())
         or grantee_user_id = (select public.app_ctx_user())))
  with check (owner_organisation_id = (select public.app_ctx_org()));

create policy access_grant_select on access_grant for select to cp_app
  using (
    owner_organisation_id = (select public.app_ctx_org())
    or ((select public.app_ctx_org()) is not null
        and (grantee_organisation_id = (select public.app_ctx_org())
             or grantee_user_id = (select public.app_ctx_user()))));

create policy access_grant_update on access_grant for update to cp_app
  using (owner_organisation_id = (select public.app_ctx_org()))
  with check (owner_organisation_id = (select public.app_ctx_org())
              and revoked_by = (select public.app_ctx_user()));

-- ---------------------------------------------------------------------------------------
-- Rule 12 (AI data boundary): a non-human context (service account, e.g. cp-agronomist)
-- sees and writes no identifying rows of real farmers: names, notes, farm and field names,
-- field geometry. Only demo/reference farmers' rows. Humans are not affected.
-- ---------------------------------------------------------------------------------------

create policy farmer_ai_boundary on farmer as restrictive for all to cp_app
  using ((select public.app_ctx_is_human()) or record_kind <> 'real')
  with check ((select public.app_ctx_is_human()) or record_kind <> 'real');

create policy farm_ai_boundary on farm as restrictive for all to cp_app
  using ((select public.app_ctx_is_human()) or exists (
    select 1 from public.farmer f
    where f.organisation_id = farm.organisation_id and f.id = farm.farmer_id
      and f.record_kind <> 'real'))
  with check ((select public.app_ctx_is_human()) or exists (
    select 1 from public.farmer f
    where f.organisation_id = farm.organisation_id and f.id = farm.farmer_id
      and f.record_kind <> 'real'));

create policy field_ai_boundary on field as restrictive for all to cp_app
  using ((select public.app_ctx_is_human()) or exists (
    select 1 from public.farm fa
    join public.farmer f on f.organisation_id = fa.organisation_id and f.id = fa.farmer_id
    where fa.organisation_id = field.organisation_id and fa.id = field.farm_id
      and f.record_kind <> 'real'))
  with check ((select public.app_ctx_is_human()) or exists (
    select 1 from public.farm fa
    join public.farmer f on f.organisation_id = fa.organisation_id and f.id = fa.farmer_id
    where fa.organisation_id = field.organisation_id and fa.id = field.farm_id
      and f.record_kind <> 'real'));

create policy field_geometry_version_ai_boundary on field_geometry_version
  as restrictive for all to cp_app
  using ((select public.app_ctx_is_human()) or exists (
    select 1 from public.field fi
    join public.farm fa on fa.organisation_id = fi.organisation_id and fa.id = fi.farm_id
    join public.farmer f on f.organisation_id = fa.organisation_id and f.id = fa.farmer_id
    where fi.organisation_id = field_geometry_version.organisation_id
      and fi.id = field_geometry_version.field_id and f.record_kind <> 'real'))
  with check ((select public.app_ctx_is_human()) or exists (
    select 1 from public.field fi
    join public.farm fa on fa.organisation_id = fi.organisation_id and fa.id = fi.farm_id
    join public.farmer f on f.organisation_id = fa.organisation_id and f.id = fa.farmer_id
    where fi.organisation_id = field_geometry_version.organisation_id
      and fi.id = field_geometry_version.field_id and f.record_kind <> 'real'));
