-- 0020: access_grant, farmer-revocable access for advisors and other organisations
-- (CPO decision RK-X7 = A, 2026-11-16; backend plan §6; model in S2, UI in S9).
--
-- One row per grant. The only change ever allowed is a one-time revoke: revoked_at,
-- revoked_by and revoke_reason go from NULL to a value, nothing else changes (revoked_at is
-- overwritten with the server's now()). Un-revoke,
-- a second revoke, a scope change and DELETE/TRUNCATE all raise. Changing the scope =
-- revoke + a new row. Active = revoked_at is null and (expires_at is null or expires_at > now()).
--
-- Who: grant and revoke are by the farmer themselves (farmer.app_user_id) or by an enabled
-- org_admin of the owning organisation, recorded in granted_by / revoked_by. The grantee is
-- an organisation or a single user, never both, never the owning organisation itself.
-- Grants give NO read path to farm data yet: RLS reads through grants arrive with the S9
-- farmer & advisor portal (DM-R1). RLS on this table itself is in 0021.
-- Audit: every grant/revoke will also be written to audit_event when that table lands (gap
-- analysis 0021+); until then the row itself is the history (it is never deleted).
set local role cp_migrator;

create type access_scope as enum ('view', 'edit');

create table access_grant (
  id                       uuid primary key default gen_random_uuid(),
  owner_organisation_id    uuid not null,
  farmer_id                uuid not null,
  grantee_organisation_id  uuid references organisation (id),
  grantee_user_id          uuid references app_user (id),
  scope                    access_scope not null,
  granted_by               uuid not null references app_user (id),
  granted_at               timestamptz not null default now(),
  expires_at               timestamptz,
  revoked_at               timestamptz,
  revoked_by               uuid references app_user (id),
  revoke_reason            text,
  constraint access_grant_one_grantee
    check ((grantee_organisation_id is null) <> (grantee_user_id is null)),
  constraint access_grant_not_self
    check (grantee_organisation_id is distinct from owner_organisation_id),
  constraint access_grant_expiry check (expires_at is null or expires_at > granted_at),
  constraint access_grant_revoke_complete check (
    (revoked_at is null and revoked_by is null and revoke_reason is null)
    or (revoked_at is not null and revoked_by is not null
        and char_length(btrim(coalesce(revoke_reason, ''))) between 1 and 500)),
  constraint access_grant_revoke_after_grant check (revoked_at is null or revoked_at >= granted_at),
  unique (owner_organisation_id, id),
  foreign key (owner_organisation_id, farmer_id) references farmer (organisation_id, id)
);

create index access_grant_owner_farmer_idx on access_grant (owner_organisation_id, farmer_id);
create index access_grant_grantee_org_idx on access_grant (grantee_organisation_id)
  where grantee_organisation_id is not null;
create index access_grant_grantee_user_idx on access_grant (grantee_user_id)
  where grantee_user_id is not null;

comment on table access_grant is
  'Farmer-revocable access grant (RK-X7 A). One row per grant; only a one-time revoke may '
  'change it; DELETE/TRUNCATE raise. No read path to farm data until S9 (DM-R1).';

-- May this user grant or revoke on behalf of the farmer? The farmer's own login, or an
-- enabled org_admin of the owning organisation. Humans only: a service/AI account never
-- grants access to a farmer's data (CLAUDE.md rules 11, 12).
create function access_grant_actor_allowed(p_owner_organisation_id uuid, p_farmer_id uuid,
                                           p_user_id uuid) returns boolean
language sql stable set search_path = pg_catalog, public as $$
  select exists (
      select 1 from public.farmer f
      join public.app_user u on u.id = f.app_user_id
      where f.organisation_id = p_owner_organisation_id and f.id = p_farmer_id
        and f.app_user_id = p_user_id and u.disabled_at is null and u.actor_kind = 'human')
    or exists (
      select 1 from public.membership m
      join public.app_user u on u.id = m.user_id
      where m.user_id = p_user_id and m.organisation_id = p_owner_organisation_id
        and m.role = 'org_admin' and u.disabled_at is null and u.actor_kind = 'human')
$$;

create function access_grant_guard() returns trigger
language plpgsql set search_path = pg_catalog, public as $$
begin
  if tg_op = 'INSERT' then
    if new.revoked_at is not null then
      raise exception 'a new access grant cannot be revoked already'
        using errcode = 'check_violation';
    end if;
    if not public.access_grant_actor_allowed(new.owner_organisation_id, new.farmer_id, new.granted_by) then
      raise exception 'only the farmer or an org_admin of the organisation can grant access'
        using errcode = 'insufficient_privilege';
    end if;
    return new;
  end if;
  -- UPDATE: exactly one revoke, nothing else.
  if old.revoked_at is not null then
    raise exception 'access grant % is already revoked; grant again with a new row', old.id
      using errcode = 'insufficient_privilege';
  end if;
  if new.revoked_at is null
     or (new.id, new.owner_organisation_id, new.farmer_id, new.grantee_organisation_id,
         new.grantee_user_id, new.scope, new.granted_by, new.granted_at, new.expires_at)
        is distinct from
        (old.id, old.owner_organisation_id, old.farmer_id, old.grantee_organisation_id,
         old.grantee_user_id, old.scope, old.granted_by, old.granted_at, old.expires_at) then
    raise exception 'an access grant can only be revoked; to change it, revoke it and grant a new one'
      using errcode = 'insufficient_privilege';
  end if;
  if not public.access_grant_actor_allowed(old.owner_organisation_id, old.farmer_id, new.revoked_by) then
    raise exception 'only the farmer or an org_admin of the organisation can revoke access'
      using errcode = 'insufficient_privilege';
  end if;
  -- The revoke time is the server's, never the caller's (no back- or future-dating).
  new.revoked_at := now();
  return new;
end
$$;

create trigger access_grant_guard
  before insert or update on access_grant
  for each row execute function access_grant_guard();

create trigger access_grant_no_delete
  before delete on access_grant
  for each row execute function forbid_change();

create trigger access_grant_no_truncate
  before truncate on access_grant
  for each statement execute function forbid_change();

grant select on access_grant to cp_app;
grant insert (owner_organisation_id, farmer_id, grantee_organisation_id, grantee_user_id, scope,
              granted_by, expires_at)
  on access_grant to cp_app;
grant update (revoked_at, revoked_by, revoke_reason) on access_grant to cp_app;
