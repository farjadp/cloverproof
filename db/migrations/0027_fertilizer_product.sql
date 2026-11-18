-- 0027: fertilizer_product, a global per-country catalog of label facts (story S2-DB-19,
-- GL-09, ADR 0008 §5 class `catalog`). Does not depend on 0026.
--
-- Facts only: no price, vendor, affiliate, url or commission column, ever (CLAUDE.md "out of
-- scope"; pinned by app/tests/db/test_fertilizer_product.py).
--
-- Grades are percentages as printed on the product label: N and S elemental, P as P2O5, K as
-- K2O (rule 7: the form is explicit in the column name). They are label facts with a recorded
-- source, not agronomic constants. No rows are seeded: a human confirms each source.
--
-- Not organisation data, so no organisation column and no org boundary policy.
--   read    active rows: any context whose app.user_id is an existing, enabled user
--           (human or service). Draft rows: only those who may write them.
--   write   INSERT creates a draft. UPDATE edits a draft or activates it. Active rows are
--           frozen. No DELETE grant. Who: a human superadmin context, or cp_admin (CLI).
--   denied  org_admin, advisor, agronomist, farmer, service/AI contexts, no context.
--
-- The superadmin check goes through app_ctx_platform_role(), which returns the role only if
-- app.platform_role equals the column of an enabled human user: narrows, never elevates. This
-- is the first cp_app policy that uses it; it opens no path to organisation data.
--
-- Open item: the story names a platform `staff` writer. app_user.platform_role allows only
-- `superadmin` today, so no such role exists and none is invented here.
set local role cp_migrator;

create table fertilizer_product (
  id               uuid primary key default gen_random_uuid(),
  country_code     char(2) not null
    constraint fertilizer_product_country_code_check check (country_code ~ '^[A-Z]{2}$'),
  name             text not null
    constraint fertilizer_product_name_check check (name <> '' and name = btrim(name)),
  n                numeric(5,2) not null
    constraint fertilizer_product_n_check check (n between 0 and 100),
  p2o5             numeric(5,2) not null
    constraint fertilizer_product_p2o5_check check (p2o5 between 0 and 100),
  k2o              numeric(5,2) not null
    constraint fertilizer_product_k2o_check check (k2o between 0 and 100),
  s                numeric(5,2) not null
    constraint fertilizer_product_s_check check (s between 0 and 100),
  form             text not null
    constraint fertilizer_product_form_check check (form in ('granular', 'liquid')),
  density_kg_per_l numeric(6,3),
  status           text not null default 'draft'
    constraint fertilizer_product_status_check check (status in ('draft', 'active')),
  grade_source     text not null
    constraint fertilizer_product_grade_source_check check (btrim(grade_source) <> ''),
  created_by       uuid not null references app_user (id),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint fertilizer_product_grade_sum_check check (n + p2o5 + k2o + s <= 100),
  constraint fertilizer_product_density_check check (
    (form = 'liquid' and density_kg_per_l is not null and density_kg_per_l > 0)
    or (form = 'granular' and density_kg_per_l is null))
);

create unique index fertilizer_product_active_name_key
  on fertilizer_product (country_code, lower(name)) where status = 'active';

comment on table fertilizer_product is
  'Global per-country catalog of product label facts. No commercial data (GL-09). ADR 0008.';
comment on column fertilizer_product.n is 'Label grade, % elemental N.';
comment on column fertilizer_product.p2o5 is 'Label grade, % P2O5 (oxide form, as printed).';
comment on column fertilizer_product.k2o is 'Label grade, % K2O (oxide form, as printed).';
comment on column fertilizer_product.s is 'Label grade, % elemental S.';
comment on column fertilizer_product.density_kg_per_l is
  'From the product label or data sheet. Required for liquid, NULL for granular.';
comment on column fertilizer_product.grade_source is
  'Where the label fact came from (document, edition or date), confirmed by a human.';

create function fertilizer_product_touch() returns trigger
language plpgsql set search_path = pg_catalog as $$
begin
  new.updated_at := now();
  return new;
end
$$;
revoke execute on function fertilizer_product_touch() from public;

create trigger fertilizer_product_touch
  before update on fertilizer_product
  for each row execute function fertilizer_product_touch();

-- Column grants: id, timestamps and (on UPDATE) the author are never written by the app or CLI.
-- cp_admin inherits these through cp_app. cp_website and cp_website_admin get nothing.
grant select on fertilizer_product to cp_app;
grant insert (country_code, name, n, p2o5, k2o, s, form, density_kg_per_l, status,
              grade_source, created_by)
  on fertilizer_product to cp_app;
grant update (country_code, name, n, p2o5, k2o, s, form, density_kg_per_l, status,
              grade_source)
  on fertilizer_product to cp_app;

alter table fertilizer_product enable row level security;
alter table fertilizer_product force row level security;

-- cp_app (web app; also applies to cp_admin, a member of cp_app).
create policy fertilizer_product_select_active on fertilizer_product
  for select to cp_app
  using (status = 'active' and exists (
    select 1 from public.app_user u
    where u.id = (select public.app_ctx_user()) and u.disabled_at is null));

create policy fertilizer_product_select_draft on fertilizer_product
  for select to cp_app
  using (status = 'draft' and (select public.app_ctx_platform_role()) = 'superadmin');

create policy fertilizer_product_insert on fertilizer_product
  for insert to cp_app
  with check (status = 'draft'
              and (select public.app_ctx_platform_role()) = 'superadmin'
              and created_by = (select public.app_ctx_user()));

create policy fertilizer_product_update on fertilizer_product
  for update to cp_app
  using (status = 'draft' and (select public.app_ctx_platform_role()) = 'superadmin')
  with check ((select public.app_ctx_platform_role()) = 'superadmin');

-- cp_admin (CLI): runs without a web context, or with a human one. A service context is
-- refused. The author must be an enabled human and, with a context, that same user.
create policy fertilizer_product_admin_select on fertilizer_product
  for select to cp_admin
  using ((select public.app_ctx_user()) is null or (select public.app_ctx_is_human()));

create policy fertilizer_product_admin_insert on fertilizer_product
  for insert to cp_admin
  with check (
    status = 'draft'
    and ((select public.app_ctx_user()) is null
         or ((select public.app_ctx_is_human())
             and created_by = (select public.app_ctx_user())))
    and exists (select 1 from public.app_user u
                where u.id = created_by and u.actor_kind = 'human' and u.disabled_at is null));

create policy fertilizer_product_admin_update on fertilizer_product
  for update to cp_admin
  using (status = 'draft'
         and ((select public.app_ctx_user()) is null or (select public.app_ctx_is_human())))
  with check ((select public.app_ctx_user()) is null or (select public.app_ctx_is_human()));

comment on function app_ctx_platform_role() is
  'RLS: app.platform_role only if it equals app_user.platform_role (narrows, never elevates). '
  'Used only by the fertilizer_product catalog policies (0027); grants no organisation data. '
  'ADR 0008.';
