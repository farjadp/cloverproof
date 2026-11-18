-- 0028: access_grant reads for `farmer` members (S2-DB-15 audit).
--
-- Gap: 0021 lets every member of the owning or grantee organisation read its grants. A member
-- whose only role is `farmer` could therefore read the grants of other farmers, which
-- S2-DB-15 forbids ("user B with no grant ... another farmer's grants: zero rows").
--
-- Fix: one RESTRICTIVE SELECT policy, so this migration only narrows access. A row stays
-- readable if the context user
--   - holds a role other than `farmer` in the context organisation (the existing owner-side
--     and grantee-organisation reads),
--   - is the grantee user named on the row, or
--   - is the login of the farmer the row is about.
-- UPDATE reads rows through SELECT policies too, so a hidden grant also cannot be revoked.
-- No other table's policy reads access_grant: grants still open no farm data before S9.
set local role cp_migrator;

create function access_grant_org_reader() returns boolean
language sql stable set search_path = pg_catalog, public as $$
  select exists (
    select 1 from public.membership m
    where m.organisation_id = public.app_ctx_org()
      and m.user_id = public.app_ctx_user()
      and m.role <> 'farmer'
  )
$$;

comment on function access_grant_org_reader() is
  'RLS: the context user holds a non-farmer role in the context organisation. S2-DB-15.';

revoke execute on function access_grant_org_reader() from public;
grant execute on function access_grant_org_reader() to cp_app;

create policy access_grant_farmer_scope on access_grant
  as restrictive for select to cp_app
  using (
    (select public.access_grant_org_reader())
    or grantee_user_id = (select public.app_ctx_user())
    or exists (
      select 1 from public.farmer f
      where f.organisation_id = access_grant.owner_organisation_id
        and f.id = access_grant.farmer_id
        and f.app_user_id = (select public.app_ctx_user())));
