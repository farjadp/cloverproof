-- Review gate hardening and admin audit (ADR 0007 "Migration 0012"; security review
-- S2-review-pr7-delta B1, F1, F2, F4, N11, N16; CPO decision D4).
--
--   B1/D4  app_user.actor_kind human|service; service accounts hold no password and never
--          author an agronomist recommendation.
--   SA     app_user.platform_role (null | superadmin), human accounts only, set by cp_admin
--          only (decision by Farjad Iranmehr, 2026-11-16: superadmin may approve).
--   D4 / CLAUDE.md rule 11: review.review_kind agronomist_approved | superadmin_approved |
--          ai_reviewed, fixed by the reviewer: service -> ai_reviewed; human agronomist of
--          the organisation -> agronomist_approved (even if also superadmin); other human
--          superadmin -> superadmin_approved. decision stays approve|edit|reject; an
--          ai_reviewed row is the AI's opinion (approve or reject, reason required, never
--          edit). It is never final, never an approval, never unlocks a proof and never
--          enters recommendation_diff. A superadmin_approved review is a human decision:
--          final for status, F1 and proof documents, but never calibration data.
--   N16    human reviews (approve, edit, reject) need a human agronomist of the organisation
--          or a human superadmin who is a member of it.
--   F1     at most one child per recommendation, at most one final human review (approve
--          or reject), never both. Violations are SQLSTATE 23505 with these
--          constraint names:
--            recommendation_one_child_idx, review_final_after_child        -> stale version
--            review_one_final_idx, review_one_approval_idx,
--            recommendation_child_after_final                               -> already reviewed
--   F4     review.started_at (signed timer start) for later recomputation of minutes.
--   N11    app_user.temp_password_expires_at, set by trigger (72 h) for admin-set passwords.
--   F2     append-only admin_event written by triggers on membership and app_user.
set local role cp_migrator;

-- ---------------------------------------------------------------------------------------
-- B1 / D4: human vs service accounts
-- ---------------------------------------------------------------------------------------

alter table app_user
  add column actor_kind text not null default 'human'
    constraint app_user_actor_kind_check check (actor_kind in ('human', 'service')),
  -- A service account can never log in with a password (B1).
  add constraint app_user_service_no_password
    check (actor_kind = 'human' or password_hash is null);

comment on column app_user.actor_kind is
  'human = a person; service = an automated actor (e.g. AI reviewer). Only cp_admin (CLI) sets it; '
  'cp_app has no INSERT/UPDATE on this column. Service accounts never approve, edit or reject.';

-- cp_app's column grants (0011) do not include actor_kind: inserts by the app get the
-- default 'human' and it cannot change the value. cp_admin has table-level INSERT/UPDATE.

-- Platform role (decision 2026-11-16). NULL = none; more values (staff) come with RK-X11.
-- Not in cp_app's column grants either: only cp_admin (CLI) sets it.
alter table app_user
  add column platform_role text
    constraint app_user_platform_role_check check (platform_role in ('superadmin')),
  add constraint app_user_platform_role_human
    check (platform_role is null or actor_kind = 'human');

comment on column app_user.platform_role is
  'NULL or superadmin. Human accounts only. Only cp_admin (CLI) sets it; changes are audited '
  'in admin_event. A human superadmin who is a member of an organisation may approve, edit '
  'and reject there (review_kind superadmin_approved, never calibration data).';

-- ---------------------------------------------------------------------------------------
-- D4 / rule 11: review_kind
-- ---------------------------------------------------------------------------------------

-- Reviews before 0012 were all recorded by human accounts (actor_kind did not exist), so
-- they are agronomist_approved. The default only fills existing rows (no rewrite, no UPDATE
-- of the immutable table) and is dropped at once: new rows get the value from the trigger.
alter table review
  add column review_kind text not null default 'agronomist_approved'
    constraint review_kind_check
      check (review_kind in ('agronomist_approved', 'superadmin_approved', 'ai_reviewed')),
  -- The AI gives an opinion only; it never produces a new version (service accounts cannot
  -- author agronomist recommendations) and always says why.
  add constraint review_ai_no_edit
    check (review_kind <> 'ai_reviewed' or decision <> 'edit'),
  add constraint review_ai_reason
    check (review_kind <> 'ai_reviewed' or char_length(btrim(coalesce(reason, ''))) > 0);

alter table review alter column review_kind drop default;

comment on column review.review_kind is
  'agronomist_approved = human agronomist of the organisation (the review gate, calibration '
  'data); superadmin_approved = human superadmin without the agronomist role there (final, '
  'unlocks proofs, never calibration data); ai_reviewed = service account (AI reviewer): '
  'opinion only, never final, never an approval. Set by trigger review_check_kind from the '
  'reviewer; a mismatch raises.';

-- Named so that it fires first among the BEFORE INSERT triggers on review (PostgreSQL fires
-- them in name order): review_check_kind < review_check_no_child < review_check_reviewer.
create function review_check_kind() returns trigger
language plpgsql as $$
declare
  v_actor    text;
  v_platform text;
  v_expected text;
begin
  select u.actor_kind, u.platform_role into v_actor, v_platform
  from app_user u where u.id = new.reviewer_id;
  if v_actor is null then
    raise exception 'reviewer % does not exist', new.reviewer_id
      using errcode = 'foreign_key_violation';
  end if;
  -- A human who is neither agronomist nor superadmin gets agronomist_approved here and is
  -- refused by review_check_reviewer with the usual message.
  v_expected := case
    when v_actor = 'service' then 'ai_reviewed'
    when has_org_role(new.reviewer_id, new.organisation_id, 'agronomist') then 'agronomist_approved'
    when v_platform = 'superadmin' then 'superadmin_approved'
    else 'agronomist_approved'
  end;
  if new.review_kind is null then
    new.review_kind := v_expected;
  elsif new.review_kind not in ('agronomist_approved', 'superadmin_approved', 'ai_reviewed') then
    return new;  -- review_kind_check rejects it
  elsif new.review_kind <> v_expected then
    if v_actor = 'service' then
      raise exception 'a service account cannot record a % review; its reviews are ai_reviewed',
        new.review_kind
        using errcode = 'insufficient_privilege';
    elsif new.review_kind = 'ai_reviewed' then
      raise exception 'only a service account can record an ai_reviewed review'
        using errcode = 'insufficient_privilege';
    elsif v_expected = 'superadmin_approved' then
      raise exception 'reviewer % is a superadmin, not an agronomist of the organisation; '
        'the review is superadmin_approved', new.reviewer_id
        using errcode = 'insufficient_privilege';
    elsif new.review_kind = 'superadmin_approved'
          and has_org_role(new.reviewer_id, new.organisation_id, 'agronomist') then
      raise exception 'reviewer % is an agronomist of the organisation; the review is '
        'agronomist_approved', new.reviewer_id
        using errcode = 'insufficient_privilege';
    end if;
    raise exception 'only a human superadmin can record a superadmin_approved review'
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end
$$;

create trigger review_check_kind
  before insert on review
  for each row execute function review_check_kind();

create function is_human_superadmin(p_user_id uuid) returns boolean
language sql stable as $$
  select exists (
    select 1 from app_user u
    where u.id = p_user_id and u.actor_kind = 'human' and u.platform_role = 'superadmin'
      and u.disabled_at is null
  )
$$;

create or replace function review_check_reviewer() returns trigger
language plpgsql as $$
begin
  if not exists (select 1 from member_organisation_ids(new.reviewer_id) o where o = new.organisation_id) then
    raise exception 'reviewer % is not an active member of organisation %',
      new.reviewer_id, new.organisation_id
      using errcode = 'insufficient_privilege';
  end if;
  if new.review_kind = 'ai_reviewed' then
    return new;  -- service account (review_check_kind); opinion only, never final
  end if;
  -- Human review: the review gate (hard rule 8 as amended 2026-11-16, N16) for approve,
  -- edit and reject: a human agronomist of the organisation or a human superadmin member.
  if (select u.actor_kind from app_user u where u.id = new.reviewer_id) is distinct from 'human' then
    raise exception 'a service account cannot approve, edit or reject a recommendation'
      using errcode = 'insufficient_privilege';
  end if;
  if new.review_kind = 'superadmin_approved' then
    if not is_human_superadmin(new.reviewer_id) then
      raise exception 'only a human superadmin can record a superadmin_approved review'
        using errcode = 'insufficient_privilege';
    end if;
  elsif not has_org_role(new.reviewer_id, new.organisation_id, 'agronomist') then
    raise exception 'only an agronomist of the organisation can % a recommendation', new.decision
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end
$$;

create or replace function recommendation_check_author() returns trigger
language plpgsql as $$
begin
  if not exists (select 1 from member_organisation_ids(new.created_by) o where o = new.organisation_id) then
    raise exception 'recommendation author % is not an active member of organisation %',
      new.created_by, new.organisation_id
      using errcode = 'insufficient_privilege';
  end if;
  if new.kind = 'agronomist' then
    if (select u.actor_kind from app_user u where u.id = new.created_by) is distinct from 'human' then
      raise exception 'a service account cannot author an agronomist recommendation'
        using errcode = 'insufficient_privilege';
    end if;
    -- An edit by a human superadmin member is allowed; its edit review is
    -- superadmin_approved and the version line leaves recommendation_diff.
    if not (has_org_role(new.created_by, new.organisation_id, 'agronomist')
            or is_human_superadmin(new.created_by)) then
      raise exception 'only an agronomist of the organisation or a superadmin can create an agronomist recommendation'
        using errcode = 'insufficient_privilege';
    end if;
  end if;
  return new;
end
$$;

comment on table review is
  'Immutable. UPDATE/DELETE/TRUNCATE raise; cp_app has SELECT, INSERT only. review_kind '
  'agronomist_approved requires a human agronomist, superadmin_approved a human superadmin '
  'member; ai_reviewed (service account) is never final.';

-- Only a human approve (agronomist_approved or superadmin_approved) unlocks a proof
-- (replaces 0008).
create or replace function proof_document_check_approved() returns trigger
language plpgsql as $$
begin
  if not exists (
    select 1 from review r
    where r.recommendation_id = new.recommendation_id and r.decision = 'approve'
      and r.review_kind <> 'ai_reviewed'
  ) then
    raise exception 'recommendation % is not approved; no proof document allowed',
      new.recommendation_id
      using errcode = 'check_violation';
  end if;
  return new;
end
$$;

-- Calibration dataset: agronomist approvals only (replaces 0009; same columns). Versions
-- with a superadmin_approved review, and every version after a superadmin edit, are left
-- out: the engine-vs-final difference must come from an agronomist alone.
create or replace view recommendation_diff with (security_invoker = true) as
with recursive lineage as (
  select r.id as recommendation_id, r.id as engine_recommendation_id, 0 as edit_depth,
         false as superadmin_line
  from recommendation r
  where r.parent_id is null
  union all
  select c.id, l.engine_recommendation_id, l.edit_depth + 1,
         l.superadmin_line or exists (
           select 1 from review x
           where x.resulting_recommendation_id = c.id and x.review_kind = 'superadmin_approved')
  from recommendation c
  join lineage l on c.parent_id = l.recommendation_id
)
select
  f.organisation_id,
  f.crop_plan_id,
  e.id                            as engine_recommendation_id,
  f.id                            as final_recommendation_id,
  f.parent_id                     as edited_from_id,
  f.kind                          as final_kind,
  l.edit_depth,
  e.engine_version,
  e.pack_id,
  e.pack_version,
  e.pack_status,
  e.pack_sha256,
  e.n_rate_kg_ha                  as engine_n_rate_kg_ha,
  f.n_rate_kg_ha                  as final_n_rate_kg_ha,
  f.n_rate_kg_ha - e.n_rate_kg_ha as n_rate_delta_kg_ha,
  e.confidence                    as engine_confidence,
  f.confidence                    as final_confidence,
  f.reason                        as edit_reason,
  f.created_by                    as final_created_by,
  f.created_at                    as final_created_at,
  a.reviewer_id                   as approved_by,
  a.created_at                    as approved_at,
  a.minutes_spent                 as approval_minutes_spent,
  e.result                        as engine_result,
  f.result                        as final_result
from lineage l
join recommendation f on f.id = l.recommendation_id
join recommendation e on e.id = l.engine_recommendation_id
left join review a on a.recommendation_id = f.id and a.decision = 'approve'
  and a.review_kind = 'agronomist_approved'
where not l.superadmin_line
  and not exists (
    select 1 from review s
    where s.recommendation_id = f.id and s.review_kind = 'superadmin_approved'
      and s.decision in ('approve', 'reject'));

comment on view recommendation_diff is
  'Calibration dataset: engine vs final per recommendation version; approvals by human '
  'agronomists only. ai_reviewed rows never appear; versions decided or edited by a '
  'superadmin_approved review are left out. Filter by organisation_id like any table.';

-- AI reviews, reported separately from human ones (CLAUDE.md "Key metric"); each with the
-- agronomist's final decision on the same version, if any, for AI-vs-agronomist agreement
-- (a superadmin_approved decision is not agronomist ground truth and is not joined).
create view ai_review with (security_invoker = true) as
select
  v.organisation_id,
  r.crop_plan_id,
  v.recommendation_id,
  v.id               as review_id,
  v.decision,
  v.reason,
  v.reviewer_id,
  v.created_at,
  h.decision         as agronomist_decision,
  h.reviewer_id      as agronomist_reviewer_id,
  h.created_at       as agronomist_decided_at
from review v
join recommendation r on r.organisation_id = v.organisation_id and r.id = v.recommendation_id
left join review h on h.recommendation_id = v.recommendation_id
  and h.review_kind = 'agronomist_approved' and h.decision in ('approve', 'reject')
where v.review_kind = 'ai_reviewed';

comment on view ai_review is
  'Reviews by service accounts (ai_reviewed) with the human final decision on the same '
  'version. Never part of the calibration dataset or the agreement gate.';

grant select on ai_review to cp_app;

-- ---------------------------------------------------------------------------------------
-- F1: one version line, one final review
-- ---------------------------------------------------------------------------------------

create unique index recommendation_one_child_idx
  on recommendation (parent_id) where parent_id is not null;

-- review_one_approval_idx (0007) is rebuilt for human reviews only (several AI opinions are
-- allowed); review_one_final_idx also covers approve + reject and reject twice. Human =
-- agronomist_approved or superadmin_approved.
drop index review_one_approval_idx;
create unique index review_one_approval_idx
  on review (recommendation_id) where decision = 'approve' and review_kind <> 'ai_reviewed';
create unique index review_one_final_idx
  on review (recommendation_id)
  where decision in ('approve', 'reject') and review_kind <> 'ai_reviewed';

-- An edit review points at exactly one new version.
create unique index review_one_edit_idx
  on review (resulting_recommendation_id) where resulting_recommendation_id is not null;

-- The two cross-table rules below take a transaction-scoped advisory lock on the
-- reviewed/parent recommendation, so concurrent "edit" and "approve" serialise and the
-- second one sees the first one's row (READ COMMITTED: each statement takes a new snapshot).
-- Lock key: (12012, hashtext(recommendation id)); collisions only serialise more.

create function review_check_no_child() returns trigger
language plpgsql as $$
begin
  if new.decision in ('approve', 'reject') and new.review_kind <> 'ai_reviewed' then
    perform pg_advisory_xact_lock(12012, hashtext(new.recommendation_id::text));
    if exists (select 1 from recommendation c where c.parent_id = new.recommendation_id) then
      raise exception 'recommendation % already has a newer version; review the latest version',
        new.recommendation_id
        using errcode = 'unique_violation', constraint = 'review_final_after_child';
    end if;
  end if;
  return new;
end
$$;

create trigger review_check_no_child
  before insert on review
  for each row execute function review_check_no_child();

create function recommendation_check_parent_open() returns trigger
language plpgsql as $$
begin
  if new.parent_id is not null then
    perform pg_advisory_xact_lock(12012, hashtext(new.parent_id::text));
    if exists (
      select 1 from review r
      where r.recommendation_id = new.parent_id and r.decision in ('approve', 'reject')
        and r.review_kind <> 'ai_reviewed'
    ) then
      raise exception 'recommendation % is already approved or rejected; it cannot be edited',
        new.parent_id
        using errcode = 'unique_violation', constraint = 'recommendation_child_after_final';
    end if;
  end if;
  return new;
end
$$;

create trigger recommendation_check_parent_open
  before insert on recommendation
  for each row execute function recommendation_check_parent_open();

-- ---------------------------------------------------------------------------------------
-- F4: timer start
-- ---------------------------------------------------------------------------------------

-- Nullable, no default: ADD COLUMN does not rewrite or UPDATE the immutable rows.
alter table review add column started_at timestamptz;

comment on column review.started_at is
  'Start of the signed review timer (app clock) for this review; minutes_spent stays the stored '
  'metric. NULL for reviews recorded before 0012.';

-- ---------------------------------------------------------------------------------------
-- N11: temporary passwords expire
-- ---------------------------------------------------------------------------------------

alter table app_user
  add column temp_password_expires_at timestamptz,
  add constraint app_user_temp_password_expiry
    check (temp_password_expires_at is null or password_change_required);

comment on column app_user.temp_password_expires_at is
  'Set by trigger to now() + 72 h when an admin-set temporary password is stored; cleared when '
  'the user chooses their own. The app treats an expired temporary password as invalid. '
  'cp_app cannot write it; an operator (cp_admin) may extend it.';

-- Existing temporary passwords get the same 72 h from now (no trigger involved yet).
update app_user set temp_password_expires_at = now() + interval '72 hours'
where password_change_required and password_hash is not null;

create function app_user_temp_password_expiry() returns trigger
language plpgsql as $$
begin
  if new.password_change_required and new.password_hash is not null then
    if tg_op = 'INSERT' then
      new.temp_password_expires_at := coalesce(new.temp_password_expires_at, now() + interval '72 hours');
    elsif new.password_hash is distinct from old.password_hash or not old.password_change_required then
      new.temp_password_expires_at := now() + interval '72 hours';
    end if;
  else
    new.temp_password_expires_at := null;
  end if;
  return new;
end
$$;

create trigger app_user_temp_password_expiry
  before insert or update of password_hash, password_change_required on app_user
  for each row execute function app_user_temp_password_expiry();

-- ---------------------------------------------------------------------------------------
-- F2: admin_event (append-only audit of who can approve)
-- ---------------------------------------------------------------------------------------

create table admin_event (
  id               uuid primary key default gen_random_uuid(),
  at               timestamptz not null default clock_timestamp(),
  -- app_user id of the acting user, from `SET LOCAL app.user_id` (web app). NULL = not set
  -- (CLI, operator psql). No foreign key: the audit outlives the user.
  actor_user_id    uuid,
  -- Database login that made the change (session_user: e.g. cp_app_login, cp_admin_login).
  actor_db_role    text not null,
  target_user_id   uuid not null,
  -- NULL for account-wide events (app_user).
  organisation_id  uuid,
  action           text not null check (action in (
                     'user_created', 'user_deleted', 'password_reset', 'password_set',
                     'actor_kind_changed', 'platform_role_changed', 'user_disabled',
                     'user_enabled',
                     'password_change_required_changed',
                     'membership_granted', 'membership_revoked', 'membership_changed')),
  -- Only the audited facts; never email, names or password hashes.
  old_value        jsonb,
  new_value        jsonb
);

create index admin_event_target_idx on admin_event (target_user_id, at);
create index admin_event_organisation_idx on admin_event (organisation_id, at);

comment on table admin_event is
  'Append-only audit of identity changes (membership, account state). Written only by '
  'SECURITY DEFINER triggers; cp_app has SELECT only. UPDATE/DELETE/TRUNCATE raise.';

create trigger admin_event_immutable
  before update or delete on admin_event
  for each row execute function forbid_change();

create trigger admin_event_no_truncate
  before truncate on admin_event
  for each statement execute function forbid_change();

-- Acting app user from the transaction-local setting; '' (reset) counts as not set.
create function admin_event_actor() returns uuid
language plpgsql stable set search_path = '' as $$
declare
  v text := nullif(btrim(coalesce(current_setting('app.user_id', true), '')), '');
begin
  if v is null then
    return null;
  end if;
  if v !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    raise exception 'app.user_id must be a uuid'
      using errcode = 'invalid_parameter_value';
  end if;
  return v::uuid;
end
$$;

create function admin_event_from_membership() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid := public.admin_event_actor();
begin
  if tg_op = 'INSERT' then
    insert into public.admin_event
      (actor_user_id, actor_db_role, target_user_id, organisation_id, action, new_value)
    values (v_actor, session_user, new.user_id, new.organisation_id, 'membership_granted',
            jsonb_build_object('role', new.role));
  elsif tg_op = 'DELETE' then
    insert into public.admin_event
      (actor_user_id, actor_db_role, target_user_id, organisation_id, action, old_value)
    values (v_actor, session_user, old.user_id, old.organisation_id, 'membership_revoked',
            jsonb_build_object('role', old.role));
  elsif (old.user_id, old.organisation_id, old.role)
        is distinct from (new.user_id, new.organisation_id, new.role) then
    insert into public.admin_event
      (actor_user_id, actor_db_role, target_user_id, organisation_id, action, old_value, new_value)
    values (v_actor, session_user, new.user_id, new.organisation_id, 'membership_changed',
            jsonb_build_object('role', old.role)
              || case when old.user_id <> new.user_id
                      then jsonb_build_object('user_id', old.user_id) else '{}' end
              || case when old.organisation_id <> new.organisation_id
                      then jsonb_build_object('organisation_id', old.organisation_id) else '{}' end,
            jsonb_build_object('role', new.role));
  end if;
  return null;
end
$$;

create trigger membership_admin_event
  after insert or update or delete on membership
  for each row execute function admin_event_from_membership();

create function admin_event_from_app_user() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  v_actor  uuid := public.admin_event_actor();
  v_old    jsonb := '{}';
  v_new    jsonb := '{}';
  v_action text;
begin
  if tg_op = 'INSERT' then
    insert into public.admin_event
      (actor_user_id, actor_db_role, target_user_id, action, new_value)
    values (v_actor, session_user, new.id, 'user_created',
            jsonb_build_object('actor_kind', new.actor_kind,
                               'platform_role', new.platform_role,
                               'has_password', new.password_hash is not null,
                               'password_change_required', new.password_change_required,
                               'disabled', new.disabled_at is not null));
    return null;
  elsif tg_op = 'DELETE' then
    insert into public.admin_event
      (actor_user_id, actor_db_role, target_user_id, action, old_value)
    values (v_actor, session_user, old.id, 'user_deleted',
            jsonb_build_object('actor_kind', old.actor_kind));
    return null;
  end if;

  if new.password_hash is distinct from old.password_hash
     or new.password_change_required is distinct from old.password_change_required then
    v_old := v_old || jsonb_build_object('has_password', old.password_hash is not null,
                                         'password_change_required', old.password_change_required);
    v_new := v_new || jsonb_build_object('has_password', new.password_hash is not null,
                                         'password_change_required', new.password_change_required);
  end if;
  if new.actor_kind is distinct from old.actor_kind then
    v_old := v_old || jsonb_build_object('actor_kind', old.actor_kind);
    v_new := v_new || jsonb_build_object('actor_kind', new.actor_kind);
  end if;
  if new.platform_role is distinct from old.platform_role then
    v_old := v_old || jsonb_build_object('platform_role', old.platform_role);
    v_new := v_new || jsonb_build_object('platform_role', new.platform_role);
  end if;
  if (new.disabled_at is null) is distinct from (old.disabled_at is null) then
    v_old := v_old || jsonb_build_object('disabled', old.disabled_at is not null);
    v_new := v_new || jsonb_build_object('disabled', new.disabled_at is not null);
  end if;
  if v_new = '{}' then
    return null;
  end if;

  -- One row per statement-level change; the action names the most significant part.
  v_action := case
    when new.password_hash is distinct from old.password_hash and new.password_change_required
      then 'password_reset'
    when new.password_hash is distinct from old.password_hash then 'password_set'
    when new.actor_kind is distinct from old.actor_kind then 'actor_kind_changed'
    when new.platform_role is distinct from old.platform_role then 'platform_role_changed'
    when new.disabled_at is not null and old.disabled_at is null then 'user_disabled'
    when new.disabled_at is null and old.disabled_at is not null then 'user_enabled'
    else 'password_change_required_changed'
  end;
  insert into public.admin_event
    (actor_user_id, actor_db_role, target_user_id, action, old_value, new_value)
  values (v_actor, session_user, new.id, v_action, v_old, v_new);
  return null;
end
$$;

create trigger app_user_admin_event_insert_delete
  after insert or delete on app_user
  for each row execute function admin_event_from_app_user();

create trigger app_user_admin_event_update
  after update of password_hash, actor_kind, platform_role, disabled_at, password_change_required
  on app_user
  for each row execute function admin_event_from_app_user();

revoke execute on function admin_event_from_membership(), admin_event_from_app_user()
  from public;

grant select on admin_event to cp_app;
