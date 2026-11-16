-- recommendation_diff: engine output vs agronomist final, the calibration dataset.
-- One row per recommendation version ("final_*"), joined to the engine row at the root of
-- its parent_id chain ("engine_*"). Engine rows appear with edit_depth 0 and delta 0, so
-- an approval without edits is part of the dataset too.
-- Calibration dataset = `where approved_at is not null`.
set local role cp_migrator;

create view recommendation_diff with (security_invoker = true) as
with recursive lineage as (
  select r.id as recommendation_id, r.id as engine_recommendation_id, 0 as edit_depth
  from recommendation r
  where r.parent_id is null
  union all
  select c.id, l.engine_recommendation_id, l.edit_depth + 1
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
left join review a on a.recommendation_id = f.id and a.decision = 'approve';

comment on view recommendation_diff is
  'Engine vs final per recommendation version. Filter by organisation_id like any table.';

grant select on recommendation_diff to cp_app;
