-- Least-privilege roles (ADR 0007; security review S2 findings S5 and A1, threat T-W3).
--
-- The review gate in the database (0007) trusts `membership`. Until now cp_app could write
-- it, so any app bug could make a staff user an agronomist. After this file:
--   cp_app      reads organisation/membership; writes only listed app_user columns; grants
--               or removes `staff` / `farmer` through the two SECURITY DEFINER functions below.
--   cp_admin    (new, NOLOGIN) = cp_app + organisation/membership/app_user writes. CLI only.
--   cp_website  (new, NOLOGIN) = INSERT on pilot_request (the columns the form writes). Nothing else.
--
-- Runs as the deploy user (CREATEROLE, owner of pilot_request from 0001). Logins are created
-- outside git by an operator (docs/runbook-db-switch.md):
--   create role cp_app_login     login password '...' in role cp_app;
--   create role cp_admin_login   login password '...' in role cp_admin;
--   create role cp_website_login login password '...' in role cp_website;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'cp_admin') then
    create role cp_admin nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'cp_website') then
    create role cp_website nologin;
  end if;
end
$$;

-- The CLI does everything the app does (sessions, password reset) plus identity writes.
grant cp_app to cp_admin;

-- Website: insert pilot requests, nothing else. No SELECT, so no RETURNING; id, created_at
-- and status come from column defaults (gen_random_uuid() is in pg_catalog, PUBLIC execute).
grant usage on schema public to cp_website;
grant insert (locale, full_name, email, country, farm_size_text, main_crop, notes,
              consent_at, consent_text)
  on pilot_request to cp_website;

set local role cp_migrator;

-- cp_app: no identity writes except the app_user columns the web app needs.
revoke insert, update, delete, truncate on organisation, membership from cp_app;
revoke insert, update, delete, truncate on app_user from cp_app;
-- Owner creates a user (repo/admin_users.create_member).
grant insert (email, display_name, password_hash, password_change_required) on app_user to cp_app;
-- Rehash on login, own/temporary password, display name, disable/enable.
grant update (password_hash, password_change_required, display_name, disabled_at)
  on app_user to cp_app;

grant insert, update, delete on organisation, membership to cp_admin;
grant insert, update on app_user to cp_admin;

-- Web user management: only `staff` and `farmer`, only by an enabled owner of the org.
-- `agronomist` and `owner` are granted and removed with the CLI (cp_admin) only.
-- The actor id comes from the app's session; these functions bound what a compromised
-- app can do, they do not authenticate the actor.
create function web_grant_member_role(
  p_actor_id uuid, p_organisation_id uuid, p_user_id uuid, p_role public.membership_role
) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if p_role is null or p_role not in ('staff', 'farmer') then
    raise exception 'role % can only be granted with the admin CLI', p_role
      using errcode = 'insufficient_privilege';
  end if;
  if not exists (
    select 1 from public.membership m join public.app_user u on u.id = m.user_id
    where m.user_id = p_actor_id and m.organisation_id = p_organisation_id
      and m.role = 'owner' and u.disabled_at is null
  ) then
    raise exception 'only an enabled owner of the organisation can change roles'
      using errcode = 'insufficient_privilege';
  end if;
  -- A brand-new user or an existing member of this organisation; adding someone who
  -- belongs to another organisation is CLI-only.
  if exists (
    select 1 from public.membership
    where user_id = p_user_id and organisation_id <> p_organisation_id
  ) and not exists (
    select 1 from public.membership
    where user_id = p_user_id and organisation_id = p_organisation_id
  ) then
    raise exception 'user belongs to another organisation; add them with the admin CLI'
      using errcode = 'insufficient_privilege';
  end if;
  insert into public.membership (organisation_id, user_id, role)
  values (p_organisation_id, p_user_id, p_role)
  on conflict (organisation_id, user_id, role) do nothing;
end
$$;

create function web_revoke_member_role(
  p_actor_id uuid, p_organisation_id uuid, p_user_id uuid, p_role public.membership_role
) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if p_role is null or p_role not in ('staff', 'farmer') then
    raise exception 'role % can only be removed with the admin CLI', p_role
      using errcode = 'insufficient_privilege';
  end if;
  if not exists (
    select 1 from public.membership m join public.app_user u on u.id = m.user_id
    where m.user_id = p_actor_id and m.organisation_id = p_organisation_id
      and m.role = 'owner' and u.disabled_at is null
  ) then
    raise exception 'only an enabled owner of the organisation can change roles'
      using errcode = 'insufficient_privilege';
  end if;
  delete from public.membership
  where organisation_id = p_organisation_id and user_id = p_user_id and role = p_role;
end
$$;

revoke execute on function web_grant_member_role(uuid, uuid, uuid, membership_role),
                           web_revoke_member_role(uuid, uuid, uuid, membership_role)
  from public;
grant execute on function web_grant_member_role(uuid, uuid, uuid, membership_role),
                          web_revoke_member_role(uuid, uuid, uuid, membership_role)
  to cp_app;

comment on function web_grant_member_role(uuid, uuid, uuid, membership_role) is
  'Owner page: grant staff/farmer. agronomist/owner are CLI-only (cp_admin). ADR 0007.';
comment on function web_revoke_member_role(uuid, uuid, uuid, membership_role) is
  'Owner page: remove staff/farmer. agronomist/owner are CLI-only (cp_admin). ADR 0007.';
