-- 0033: tie every soil estimate to the field location it was looked up for (S3; CLAUDE.md
-- rules 3, 5, 12 and Data rules; ADR 0002 addendum, ADR 0006).
--
-- field.location_revision counts real changes of the point (0032). The trigger owns the value:
-- whatever a writer sends is overwritten, so cp_app cannot forge it. The coordinates themselves
-- are never copied to soil_estimate (rule 12): the revision is the only link.
--
-- soil_estimate gains the revision and the provenance the engine's SoilEstimate input needs
-- (statistic, published layer address, citation). The table is immutable and staging already
-- has 0031, so the columns are nullable and the CHECKs are NOT VALID: they bind every new row,
-- and old rows (NULL revision) stay as they are and count as stale.
--
-- Current rule: an estimate is current when its revision equals the field's revision and it is
-- the latest retrieval among the rows of that revision for its field, season, property and
-- depth. A row of an earlier location never hides a row of the present one, even when its
-- retrieval date is later. Rows are never edited or deleted; they are superseded.
-- Queries: cloverproof_app.repo.soil_estimates.
set local role cp_migrator;

-- ---------------------------------------------------------------------------------------
-- field.location_revision
-- ---------------------------------------------------------------------------------------

alter table field
  add column location_revision integer not null default 0
    constraint field_location_revision_not_negative check (location_revision >= 0);

comment on column field.location_revision is
  'Number of real changes of location_lat/location_lon, including clearing. Set by trigger only.';

create function field_location_revision_guard() returns trigger
language plpgsql set search_path = pg_catalog, public as $$
begin
  if tg_op = 'INSERT' then
    new.location_revision := 0;
  elsif new.location_lat is distinct from old.location_lat
     or new.location_lon is distinct from old.location_lon then
    new.location_revision := old.location_revision + 1;
  else
    new.location_revision := old.location_revision;
  end if;
  return new;
end
$$;

-- Every UPDATE, not only UPDATE OF the location columns: a statement that sets just
-- location_revision must be overwritten too.
create trigger field_location_revision_guard
  before insert or update on field
  for each row execute function field_location_revision_guard();

-- ---------------------------------------------------------------------------------------
-- soil_estimate: revision and provenance (no coordinates, rule 12)
-- ---------------------------------------------------------------------------------------

alter table soil_estimate
  add column field_location_revision integer,
  add column statistic text,
  add column layer_url text,
  add column citation text,
  add constraint soil_estimate_location_revision_required
    check (field_location_revision is not null and field_location_revision >= 0) not valid,
  add constraint soil_estimate_statistic_mean
    check (statistic is not null and statistic = 'mean') not valid,
  add constraint soil_estimate_standard_depth
    check ((depth_top_cm, depth_bottom_cm) in
      ((0, 5), (5, 15), (15, 30), (30, 60), (60, 100), (100, 200))) not valid,
  -- The address is fully determined by the row, so it cannot carry a location. Same rule as
  -- the engine's SoilEstimateValue.url. coalesce: a NULL comparison would pass a CHECK.
  add constraint soil_estimate_layer_url_published
    check (coalesce(layer_url = 'https://files.isric.org/soilgrids/latest/data/'
      || property || '/' || property || '_'
      || depth_top_cm::text || '-' || depth_bottom_cm::text || 'cm_' || statistic || '.vrt',
      false)) not valid,
  add constraint soil_estimate_citation_text
    check (citation is not null and char_length(btrim(citation)) between 1 and 1000) not valid;

comment on column soil_estimate.field_location_revision is
  'field.location_revision the value was looked up for. NULL only on rows older than 0033: stale.';
comment on column soil_estimate.layer_url is
  'Published SoilGrids layer of this property, depth and statistic. Never holds a location.';
comment on table soil_estimate is
  'Immutable. Modelled soil properties with source metadata; never a lab test, never P or K '
  '(rule 3). Current = revision equals the field''s, latest retrieved_at within that revision; '
  'other rows are superseded, never changed. soil_test.source = ''estimate'' rows are separate.';

-- Re-loading the same cache after a move has the same retrieval date and must add rows.
alter table soil_estimate drop constraint soil_estimate_one_row_per_retrieval;
alter table soil_estimate
  add constraint soil_estimate_one_row_per_retrieval_and_revision
    unique nulls not distinct (
      organisation_id, field_id, season_id, property, depth_top_cm, depth_bottom_cm,
      source, source_version, retrieved_at, field_location_revision);

-- Runs as the invoker (0021: no SECURITY DEFINER reads a tenant table), so a field the caller
-- cannot see is refused. FOR SHARE holds the field until commit: a concurrent move either waits
-- and then makes this row stale, or commits first and this row is refused.
create function soil_estimate_check_location() returns trigger
language plpgsql set search_path = pg_catalog, public as $$
declare
  v_revision integer;
  v_located  boolean;
begin
  -- NOT NULL (field) and the RLS check (organisation) refuse these right after this trigger.
  if new.organisation_id is null or new.field_id is null then
    return new;
  end if;
  select f.location_revision, f.location_lat is not null
    into v_revision, v_located
    from public.field f
    where f.organisation_id = new.organisation_id and f.id = new.field_id
    for share;
  if not found then
    if new.organisation_id is distinct from public.app_ctx_org() then
      raise exception 'no access to this organisation''s fields'
        using errcode = 'insufficient_privilege';
    end if;
    raise exception 'soil estimate: field not found in this organisation'
      using errcode = 'foreign_key_violation';
  end if;
  if not v_located then
    raise exception 'soil estimate: the field has no location'
      using errcode = 'check_violation', constraint = 'soil_estimate_field_located';
  end if;
  if new.field_location_revision is distinct from v_revision then
    raise exception 'soil estimate: looked up for another location of this field'
      using errcode = 'check_violation', constraint = 'soil_estimate_revision_current';
  end if;
  return new;
end
$$;

create trigger soil_estimate_check_location
  before insert on soil_estimate
  for each row execute function soil_estimate_check_location();

-- Rule 12: the means and quantiles of a 250 m map could point to a farm's pixel, so a
-- non-human context never reads or writes estimates of a real farmer's field.
create policy soil_estimate_ai_boundary on soil_estimate as restrictive for all to cp_app
  using ((select public.app_ctx_is_human()) or exists (
    select 1 from public.field f
    join public.farm fa on fa.organisation_id = f.organisation_id and fa.id = f.farm_id
    join public.farmer fr on fr.organisation_id = fa.organisation_id and fr.id = fa.farmer_id
    where f.organisation_id = soil_estimate.organisation_id and f.id = soil_estimate.field_id
      and fr.record_kind <> 'real'))
  with check ((select public.app_ctx_is_human()) or exists (
    select 1 from public.field f
    join public.farm fa on fa.organisation_id = f.organisation_id and fa.id = f.farm_id
    join public.farmer fr on fr.organisation_id = fa.organisation_id and fr.id = fa.farmer_id
    where f.organisation_id = soil_estimate.organisation_id and f.id = soil_estimate.field_id
      and fr.record_kind <> 'real'));
