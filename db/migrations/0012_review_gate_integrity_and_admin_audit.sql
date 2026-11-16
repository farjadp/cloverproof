-- Review gate hardening and admin audit (ADR 0006 "Migration 0012"; security review
-- S2-review-pr7-delta B1, F1, F2, F4, N11, N16; CPO decision D4).
--
--   B1/D4  app_user.actor_kind human|service; service accounts hold no password, never
--          approve/edit/reject, never author an agronomist recommendation; they record
--          review decision `ai_reviewed`, which is never final and never unlocks a proof.
--   N16    approve, edit and reject all need a human agronomist of the organisation.
--   F1     at most one child per recommendation, at most one final review (approve or
--          reject), never both. Violations are SQLSTATE 23505 with these constraint names:
--            recommendation_one_child_idx, review_final_after_child        -> stale version
--            review_one_final_idx, review_one_approval_idx,
--            recommendation_child_after_final                               -> already reviewed
--   F4     review.started_at (signed timer start) for later recomputation of minutes.
--   N11    app_user.temp_password_expires_at, set by trigger (72 h) for admin-set passwords.
--   F2     append-only admin_event written by triggers on membership and app_user.
--
-- `ai_reviewed` is added with ALTER TYPE ... ADD VALUE, so nothing below may use the new
-- label in SQL that runs in this transaction (PL/pgSQL bodies are fine: they run later).
set local role cp_migrator;

-- ---------------------------------------------------------------------------------------
-- B1 / D4: human vs service accounts
-- ---------------------------------------------------------------------------------------

alter type review_decision add value 'ai_reviewed';

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

create or replace function review_check_reviewer() returns trigger
language plpgsql as $$
declare
  v_kind text;
begin
  if not exists (select 1 from member_organisation_ids(new.reviewer_id) o where o = new.organisation_id) then
    raise exception 'reviewer % is not an active member of organisation %',
      new.reviewer_id, new.organisation_id
      using errcode = 'insufficient_privilege';
  end if;
  select u.actor_kind into v_kind from app_user u where u.id = new.reviewer_id;
  if new.decision::text = 'ai_reviewed' then
    if v_kind is distinct from 'service' then
      raise exception 'only a service account can record an ai_reviewed review'
        using errcode = 'insufficient_privilege';
    end if;
    return new;
  end if;
  -- approve, edit, reject: the review gate (hard rule 8, D4).
  if v_kind is distinct from 'human' then
    raise exception 'a service account cannot approve, edit or reject a recommendation; record ai_reviewed instead'
      using errcode = 'insufficient_privilege';
  end if;
  if not has_org_role(new.reviewer_id, new.organisation_id, 'agronomist') then
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
    if not has_org_role(new.created_by, new.organisation_id, 'agronomist') then
      raise exception 'only an agronomist of the organisation can create an agronomist recommendation'
        using errcode = 'insufficient_privilege';
    end if;
  end if;
  return new;
end
$$;

comment on table review is
  'Immutable. UPDATE/DELETE/TRUNCATE raise; cp_app has SELECT, INSERT only. approve/edit/reject '
  'require a human agronomist; ai_reviewed only a service account and is never final.';

-- proof_document_check_approved (0008) and recommendation_diff (0009) look only at
-- decision = 'approve', so ai_reviewed never unlocks a proof and never enters calibration.

-- ---------------------------------------------------------------------------------------
-- F1: one version line, one final review
-- ---------------------------------------------------------------------------------------

create unique index recommendation_one_child_idx
  on recommendation (parent_id) where parent_id is not null;

-- review_one_approval_idx (0007) stays; this one also covers approve + reject and reject twice.
create unique index review_one_final_idx
  on review (recommendation_id) where decision in ('approve', 'reject');

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
  if new.decision::text in ('approve', 'reject') then
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
      where r.recommendation_id = new.parent_id and r.decision::text in ('approve', 'reject')
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
