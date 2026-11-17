-- 0019: recommendation_state, the derived status of every recommendation version
-- (CPO decision RK-X4 = A, 2026-11-16: a view, no status column on the immutable table).
--
-- status, first match wins:
--   approved    a human approve review (agronomist_approved or superadmin_approved)
--   rejected    a human reject review
--   superseded  a newer version exists: a child row (edit), or a later root on the same
--               crop plan that is approved
--   in_review   otherwise (an engine row enters the review queue on insert; no draft state)
-- ai_reviewed reviews never set a status (CLAUDE.md rule 11); they show up only as
-- ai_review_count / last_ai_reviewed_at.
-- version_no = 1 for a root (engine row), parent's version_no + 1 for an edit.
-- approval_kind says who decided: agronomist_approved or superadmin_approved (rule 8:
-- only agronomist_approved feeds calibration; recommendation_diff already filters on it).
--
-- security_invoker: the caller's grants and RLS policies (0021) apply to every table read.
set local role cp_migrator;

create view recommendation_state with (security_invoker = true) as
with recursive lineage as (
  select r.id, r.id as root_id, 1 as version_no
  from recommendation r
  where r.parent_id is null
  union all
  select c.id, l.root_id, l.version_no + 1
  from recommendation c
  join lineage l on c.parent_id = l.id
),
final as (
  -- At most one human final review per recommendation (review_one_final_idx, 0012).
  select v.recommendation_id, v.decision, v.review_kind, v.reviewer_id, v.created_at
  from review v
  where v.decision in ('approve', 'reject') and v.review_kind <> 'ai_reviewed'
),
ai as (
  select v.recommendation_id, count(*)::int as n, max(v.created_at) as last_at
  from review v
  where v.review_kind = 'ai_reviewed'
  group by v.recommendation_id
)
select
  r.organisation_id,
  r.crop_plan_id,
  r.id                    as recommendation_id,
  r.parent_id,
  l.root_id,
  r.kind,
  l.version_no,
  case
    when f.decision = 'approve' then 'approved'
    when f.decision = 'reject' then 'rejected'
    when exists (select 1 from recommendation c where c.parent_id = r.id) then 'superseded'
    when exists (
      select 1
      from recommendation o
      join final fo on fo.recommendation_id = o.id and fo.decision = 'approve'
      where o.organisation_id = r.organisation_id and o.crop_plan_id = r.crop_plan_id
        and o.id <> r.id and o.created_at > r.created_at
    ) then 'superseded'
    else 'in_review'
  end                     as status,
  f.review_kind           as decision_kind,
  case when f.decision = 'approve' then f.reviewer_id end as approved_by,
  case when f.decision = 'approve' then f.created_at end  as approved_at,
  case when f.decision = 'approve' then f.review_kind end as approval_kind,
  coalesce(a.n, 0)        as ai_review_count,
  a.last_at               as last_ai_reviewed_at,
  r.created_by,
  r.created_at
from recommendation r
join lineage l on l.id = r.id
left join final f on f.recommendation_id = r.id
left join ai a on a.recommendation_id = r.id;

comment on view recommendation_state is
  'Derived status per recommendation version (RK-X4): approved | rejected | superseded | '
  'in_review, version_no, who approved and as which kind. ai_reviewed never sets a status. '
  'security_invoker; filter by organisation_id like any table.';

grant select on recommendation_state to cp_app;
