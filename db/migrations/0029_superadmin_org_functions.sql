-- 0029: a human superadmin creates or joins an organisation from the web app (decision by
-- Farjad Iranmehr; until now CLI only). ADR 0007 addendum.
--
-- cp_app keeps no write grant on organisation or membership (0011). It gets two SECURITY
-- DEFINER functions instead, in the pattern of web_grant_member_role:
--   superadmin_create_organisation(actor, name, role)  creates it and adds the actor
--   superadmin_join_organisation(actor, organisation, role)  adds the actor
--
-- Rules, all enforced here and raised as 42501 unless noted:
--   * the actor must equal app.user_id and be an enabled human superadmin. This bounds the
--     app; it does not authenticate the actor (app.user_id is asserted by the app, ADR 0007).
--   * the actor only ever adds themselves.
--   * role is org_admin or advisor. NEVER agronomist: it would turn this person's
--     superadmin_approved reviews into agronomist_approved ones and put them in the
--     calibration dataset (CLAUDE.md rule 8, review_check_kind in 0012). Never farmer.
--   * a second organisation with the same name (ignoring case and outer spaces) is refused
--     with 23505, constraint organisation_name_taken. Existing duplicates are left alone,
--     so this is a check under a lock and not a unique index.
--   * an unknown organisation is P0002 (no_data_found).
--
-- Audit: the membership row is recorded by the existing trigger (membership_granted, with
-- the actor). Creating an organisation is recorded here as organisation_created: the target
-- is the acting user, because admin_event.target_user_id is NOT NULL. Like every admin_event
-- row it stores no names, so new_value is NULL and the organisation is identified by its id.
--
-- is_human_superadmin (0012) is not called: it has no pinned search_path and resolves
-- app_user through the caller's, which is empty here.
set local role cp_migrator;

alter table admin_event drop constraint admin_event_action_check;
alter table admin_event add constraint admin_event_action_check check (action in (
  'user_created', 'user_deleted', 'password_reset', 'password_set',
  'actor_kind_changed', 'platform_role_changed', 'user_disabled',
  'user_enabled',
  'password_change_required_changed',
  'membership_granted', 'membership_revoked', 'membership_changed',
  'organisation_created'));

-- Internal: the checks every function below starts with. Not executable by cp_app.
create function superadmin_org_check(p_actor_id uuid, p_role public.membership_role) returns void
language plpgsql set search_path = '' as $$
declare
  v_context uuid := public.admin_event_actor();
begin
  if p_actor_id is null or v_context is null or p_actor_id <> v_context then
    raise exception 'the actor must be the signed-in user (app.user_id)'
      using errcode = 'insufficient_privilege';
  end if;
  if not exists (
    select 1 from public.app_user u
    where u.id = p_actor_id and u.actor_kind = 'human' and u.platform_role = 'superadmin'
      and u.disabled_at is null
  ) then
    raise exception 'only an enabled human superadmin can create or join an organisation here'
      using errcode = 'insufficient_privilege';
  end if;
  if p_role is null or p_role not in ('org_admin', 'advisor') then
    raise exception 'role % cannot be taken here; only org_admin or advisor', p_role
      using errcode = 'insufficient_privilege';
  end if;
end
$$;

create function superadmin_create_organisation(
  p_actor_id uuid, p_name text, p_role public.membership_role
) returns uuid
language plpgsql security definer set search_path = '' as $$
declare
  v_name text := pg_catalog.btrim(p_name);
  v_id   uuid;
begin
  perform public.superadmin_org_check(p_actor_id, p_role);
  if v_name is null or pg_catalog.char_length(v_name) not between 1 and 200 then
    raise exception 'an organisation name has 1 to 200 characters'
      using errcode = 'check_violation', constraint = 'organisation_name_check';
  end if;
  -- Serialises concurrent creations, so two requests cannot both pass the check below.
  perform pg_catalog.pg_advisory_xact_lock(12029, 0);
  if exists (
    select 1 from public.organisation o
    where pg_catalog.lower(pg_catalog.btrim(o.name)) = pg_catalog.lower(v_name)
  ) then
    raise exception 'an organisation with this name already exists'
      using errcode = 'unique_violation', constraint = 'organisation_name_taken';
  end if;
  insert into public.organisation (name) values (v_name) returning id into v_id;
  insert into public.admin_event
    (actor_user_id, actor_db_role, target_user_id, organisation_id, action)
  values (p_actor_id, session_user, p_actor_id, v_id, 'organisation_created');
  insert into public.membership (organisation_id, user_id, role)
  values (v_id, p_actor_id, p_role);
  return v_id;
end
$$;

-- Returns true when the role was added, false when the actor already held it.
create function superadmin_join_organisation(
  p_actor_id uuid, p_organisation_id uuid, p_role public.membership_role
) returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  perform public.superadmin_org_check(p_actor_id, p_role);
  if not exists (select 1 from public.organisation o where o.id = p_organisation_id) then
    raise exception 'no such organisation' using errcode = 'no_data_found';
  end if;
  insert into public.membership (organisation_id, user_id, role)
  values (p_organisation_id, p_actor_id, p_role)
  on conflict (organisation_id, user_id, role) do nothing;
  return found;
end
$$;

revoke execute on function superadmin_org_check(uuid, public.membership_role),
                           superadmin_create_organisation(uuid, text, public.membership_role),
                           superadmin_join_organisation(uuid, uuid, public.membership_role)
  from public;
grant execute on function superadmin_create_organisation(uuid, text, public.membership_role),
                          superadmin_join_organisation(uuid, uuid, public.membership_role)
  to cp_app;

comment on function superadmin_create_organisation(uuid, text, public.membership_role) is
  'Human superadmin (actor = app.user_id) creates an organisation and joins it as org_admin or '
  'advisor, never agronomist (rule 8). Recorded in admin_event. ADR 0007.';
comment on function superadmin_join_organisation(uuid, uuid, public.membership_role) is
  'Human superadmin (actor = app.user_id) joins an organisation as org_admin or advisor, never '
  'agronomist (rule 8). Recorded in admin_event by the membership trigger. ADR 0007.';
