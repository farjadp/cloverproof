-- 0015: organisation roles renamed to the plan's names (CPO decision RK-X11 = A, 2026-11-16;
-- docs/plans/schema-gap-analysis.md). Ships in one release with the app (literals in
-- app/cloverproof_app) and before any RLS policy is written, so policies never name the
-- old labels.
--
--   owner -> org_admin   (manages users of the organisation)
--   staff -> advisor     (enters farm data; never approves)
--   agronomist, farmer   unchanged
--
-- `alter type ... rename value` is catalog-only: no row is rewritten, so the immutable
-- tables are not touched and admin_event keeps its history (old rows say "owner"/"staff"
-- in their jsonb; that is history, not a label in use).
--
-- Every function that names the old labels as a literal is recreated here (a plpgsql
-- literal 'owner' compared with the enum would fail at run time after the rename):
--   web_grant_member_role, web_revoke_member_role (0011), app_user_cli_only_guard (0014).
-- No CHECK constraint, index predicate or view names them (checked with grep on 0001-0014).
set local role cp_migrator;

alter type membership_role rename value 'owner' to 'org_admin';
alter type membership_role rename value 'staff' to 'advisor';

-- Web user management: only `advisor` and `farmer`, only by an enabled org_admin of the org.
-- `agronomist` and `org_admin` are granted and removed with the CLI (cp_admin) only.
create or replace function web_grant_member_role(
  p_actor_id uuid, p_organisation_id uuid, p_user_id uuid, p_role public.membership_role
) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if p_role is null or p_role not in ('advisor', 'farmer') then
    raise exception 'role % can only be granted with the admin CLI', p_role
      using errcode = 'insufficient_privilege';
  end if;
  if not exists (
    select 1 from public.membership m join public.app_user u on u.id = m.user_id
    where m.user_id = p_actor_id and m.organisation_id = p_organisation_id
      and m.role = 'org_admin' and u.disabled_at is null
  ) then
    raise exception 'only an enabled org_admin of the organisation can change roles'
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

create or replace function web_revoke_member_role(
  p_actor_id uuid, p_organisation_id uuid, p_user_id uuid, p_role public.membership_role
) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if p_role is null or p_role not in ('advisor', 'farmer') then
    raise exception 'role % can only be removed with the admin CLI', p_role
      using errcode = 'insufficient_privilege';
  end if;
  if not exists (
    select 1 from public.membership m join public.app_user u on u.id = m.user_id
    where m.user_id = p_actor_id and m.organisation_id = p_organisation_id
      and m.role = 'org_admin' and u.disabled_at is null
  ) then
    raise exception 'only an enabled org_admin of the organisation can change roles'
      using errcode = 'insufficient_privilege';
  end if;
  delete from public.membership
  where organisation_id = p_organisation_id and user_id = p_user_id and role = p_role;
end
$$;

comment on function web_grant_member_role(uuid, uuid, uuid, membership_role) is
  'Org admin page: grant advisor/farmer. agronomist/org_admin are CLI-only (cp_admin). ADR 0007.';
comment on function web_revoke_member_role(uuid, uuid, uuid, membership_role) is
  'Org admin page: remove advisor/farmer. agronomist/org_admin are CLI-only (cp_admin). ADR 0007.';

-- 0014's guard with the new label (body otherwise unchanged).
create or replace function app_user_cli_only_guard() returns trigger
language plpgsql set search_path = '' as $$
declare
  v_actor uuid := public.admin_event_actor();
begin
  if new.password_hash is not distinct from old.password_hash
     and new.password_change_required is not distinct from old.password_change_required
     and new.disabled_at is not distinct from old.disabled_at then
    return new;
  end if;
  -- Operator (superuser) and CLI (cp_admin) are not limited.
  if exists (select 1 from pg_catalog.pg_roles where rolname = current_user and rolsuper)
     or pg_catalog.pg_has_role(current_user, 'cp_admin', 'member')
     or not pg_catalog.pg_has_role(current_user, 'cp_app', 'member') then
    return new;
  end if;
  if v_actor is not null and v_actor = old.id then
    return new;  -- the account holder's own change
  end if;
  if old.platform_role is not null
     or exists (select 1 from public.membership m
                 where m.user_id = old.id and m.role in ('agronomist', 'org_admin')) then
    raise exception 'password and disabled state of platform, agronomist and org_admin accounts'
      ' are changed with the CLI only'
      using errcode = '42501';
  end if;
  return new;
end
$$;

comment on function app_user_cli_only_guard() is
  'NB1: cp_app cannot reset/disable platform, agronomist or org_admin accounts except their own'
  ' password; CLI (cp_admin) only. ADR 0007.';
