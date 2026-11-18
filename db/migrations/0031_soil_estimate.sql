-- 0031: soil_estimate, modelled soil properties with full source metadata (S3-DB-01, DM-12,
-- XD-08; CLAUDE.md rules 3, 4, 5, 7 and Data rules; ADR 0006).
--
-- One row = one property, one depth layer, one field and season, one retrieval. The columns
-- follow data_sources.soilgrids.models.EstimateValue; `value` is its `mean`.
--
-- Rule 3: `property` is limited to the SoilGrids allowlist (ADR 0006). No P or K property can
-- be stored here, so an estimate cannot feed a P/K path.
-- Rule 7: values are in the canonical unit of their property; the database never converts.
-- XD-08: every metadata column is NOT NULL. The uncertainty is the one alternative, because
-- the cache may lack a layer (estimate.py gives None): the Q0.05/Q0.95 pair, the uncertainty
-- ratio, or both, and a row with neither is refused.
--
-- Refresh rule (no silent overwrite): rows are immutable; a new retrieval adds rows with a new
-- retrieved_at, and the current value is the latest retrieved_at. Storing the same retrieval
-- twice is a unique violation. forbid_change on UPDATE/DELETE/TRUNCATE; cp_app has SELECT and
-- INSERT only.
--
-- Existing soil_test rows with source = 'estimate' are KEPT and NOT moved or copied: they are
-- hand-entered estimates without source metadata, stay valid, and stay readable by existing
-- recommendations' evidence. Nothing here reads or changes them (ADR 0002 addendum).
--
-- The "estimates are always low confidence" rule lives in the engine, not here.
--
-- RLS follows 0021 / 0026: forced, restrictive org boundary, permissive SELECT and INSERT,
-- author bound to the context user. No UPDATE/DELETE policy exists.
set local role cp_migrator;

create table soil_estimate (
  id                 uuid primary key default gen_random_uuid(),
  organisation_id    uuid not null,
  field_id           uuid not null,
  season_id          uuid not null,
  property           text not null,
  value              numeric not null,
  unit               text not null,
  value_q05          numeric,
  value_q95          numeric,
  uncertainty_ratio  numeric,
  source             text not null,
  source_version     text not null,
  resolution_m       numeric not null,
  depth_top_cm       integer not null,
  depth_bottom_cm    integer not null,
  retrieved_at       timestamptz not null,
  licence            text not null,
  attribution        text not null,
  created_by         uuid not null references app_user (id),
  created_at         timestamptz not null default now(),

  constraint soil_estimate_property_allowlist
    check (property in ('phh2o', 'soc', 'nitrogen', 'clay', 'sand', 'silt')),
  constraint soil_estimate_canonical_unit check (
    (property = 'phh2o' and unit = 'pH')
    or (property in ('soc', 'nitrogen') and unit = 'mg/kg')
    or (property in ('clay', 'sand', 'silt') and unit = '%')),
  -- Only SoilGrids until another source has a loader and its licence rules are enforced.
  constraint soil_estimate_source_known check (source = 'soilgrids'),
  -- numeric accepts 'NaN' and 'Infinity', and both compare >= 0.
  constraint soil_estimate_value_finite check (value >= 0 and value < 'Infinity'),
  constraint soil_estimate_q05_finite check (value_q05 >= 0 and value_q05 < 'Infinity'),
  constraint soil_estimate_q95_finite check (value_q95 >= 0 and value_q95 < 'Infinity'),
  constraint soil_estimate_quantile_order check (value_q05 <= value_q95),
  constraint soil_estimate_ratio_finite
    check (uncertainty_ratio >= 0 and uncertainty_ratio < 'Infinity'),
  constraint soil_estimate_quantile_pair check ((value_q05 is null) = (value_q95 is null)),
  constraint soil_estimate_uncertainty_present
    check (value_q05 is not null or uncertainty_ratio is not null),
  constraint soil_estimate_resolution_finite
    check (resolution_m > 0 and resolution_m < 'Infinity'),
  constraint soil_estimate_depth_order
    check (depth_top_cm >= 0 and depth_bottom_cm > depth_top_cm),
  constraint soil_estimate_source_version_text
    check (char_length(btrim(source_version)) between 1 and 100),
  constraint soil_estimate_licence_text check (char_length(btrim(licence)) between 1 and 200),
  constraint soil_estimate_attribution_text
    check (char_length(btrim(attribution)) between 1 and 1000),
  constraint soil_estimate_retrieved_before_stored check (retrieved_at <= created_at),

  unique (organisation_id, id),
  -- Also the lookup path for "latest retrieval" and the index led by the org column.
  constraint soil_estimate_one_row_per_retrieval unique (
    organisation_id, field_id, season_id, property, depth_top_cm, depth_bottom_cm,
    source, source_version, retrieved_at),
  foreign key (organisation_id, field_id) references field (organisation_id, id),
  foreign key (organisation_id, season_id) references season (organisation_id, id)
);

comment on table soil_estimate is
  'Immutable. Modelled soil properties with source metadata; never a lab test, never P or K '
  '(rule 3). A new retrieval adds rows; the current value is the latest retrieved_at. '
  'soil_test.source = ''estimate'' rows are separate and kept.';

create trigger soil_estimate_immutable
  before update or delete on soil_estimate
  for each row execute function forbid_change();

create trigger soil_estimate_no_truncate
  before truncate on soil_estimate
  for each statement execute function forbid_change();

grant select, insert on soil_estimate to cp_app;

alter table soil_estimate enable row level security;
alter table soil_estimate force row level security;

create policy soil_estimate_org_boundary on soil_estimate
  as restrictive for all to cp_app
  using (organisation_id = (select public.app_ctx_org()))
  with check (organisation_id = (select public.app_ctx_org()));

create policy soil_estimate_select on soil_estimate for select to cp_app
  using (organisation_id = (select public.app_ctx_org()));

create policy soil_estimate_insert on soil_estimate for insert to cp_app
  with check (organisation_id = (select public.app_ctx_org())
              and created_by = (select public.app_ctx_user()));
