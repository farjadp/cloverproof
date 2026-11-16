-- review: the agronomist gate (CLAUDE.md hard rule 8, ADR 0005). Insert-only.
-- decision 'edit' points at the new agronomist recommendation it produced, whose parent
-- is the reviewed recommendation (enforced by the foreign key on (id, parent_id)).
set local role cp_migrator;

create type review_decision as enum ('approve', 'edit', 'reject');

create table review (
  id                           uuid primary key default gen_random_uuid(),
  organisation_id              uuid not null,
  recommendation_id            uuid not null,
  decision                     review_decision not null,
  reason                       text,
  reviewer_id                  uuid not null references app_user (id),
  -- Key metric of the internal tool: agronomist minutes spent on this review.
  minutes_spent                integer not null check (minutes_spent >= 0),
  -- For decision 'edit': the new recommendation row (child of recommendation_id).
  resulting_recommendation_id  uuid,
  created_at                   timestamptz not null default now(),

  check ((decision = 'edit') = (resulting_recommendation_id is not null)),
  check (decision = 'approve' or char_length(btrim(coalesce(reason, ''))) > 0),

  foreign key (organisation_id, recommendation_id) references recommendation (organisation_id, id),
  foreign key (resulting_recommendation_id, recommendation_id) references recommendation (id, parent_id)
);

create index review_recommendation_idx on review (recommendation_id, created_at);
-- A recommendation is approved at most once.
create unique index review_one_approval_idx on review (recommendation_id) where decision = 'approve';

comment on table review is
  'Immutable. UPDATE/DELETE/TRUNCATE raise; cp_app has SELECT, INSERT only. Approve requires an agronomist membership.';

create function review_check_reviewer() returns trigger
language plpgsql as $$
begin
  if not exists (select 1 from member_organisation_ids(new.reviewer_id) o where o = new.organisation_id) then
    raise exception 'reviewer % is not an active member of organisation %',
      new.reviewer_id, new.organisation_id
      using errcode = 'insufficient_privilege';
  end if;
  if new.decision = 'approve'
     and not has_org_role(new.reviewer_id, new.organisation_id, 'agronomist') then
    raise exception 'only an agronomist of the organisation can approve a recommendation'
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end
$$;

create trigger review_check_reviewer
  before insert on review
  for each row execute function review_check_reviewer();

create trigger review_immutable
  before update or delete on review
  for each row execute function forbid_change();

create trigger review_no_truncate
  before truncate on review
  for each statement execute function forbid_change();

grant select, insert on review to cp_app;
