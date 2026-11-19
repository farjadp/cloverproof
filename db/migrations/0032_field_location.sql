-- 0032: optional field location, one point near the middle of the field.
--
-- The point is what a SoilGrids estimate will be looked up with (next PR). It is not a boundary:
-- field_geometry_version stays untouched for map drawing (S18).
--
-- Decimal degrees (WGS 84). Five decimals are about 1 m, far finer than the 250 m soil data.
-- Both columns are set or both are null; existing fields stay null.
--
-- Privacy: a field's coordinates can identify a farm. They stay on this table and are never
-- copied into recommendation.inputs_snapshot, recommendation.result or a proof document.
-- Rule 12 needs no new policy: field_ai_boundary (0021) already hides real farmers' field rows
-- from non-human contexts, whole rows and therefore these columns too.
--
-- Grants and RLS: 0004 granted cp_app table-level SELECT/INSERT/UPDATE/DELETE on field, which
-- covers new columns, so no grant is added. The 0021 policies are per row and apply unchanged.
set local role cp_migrator;

alter table field
  add column location_lat numeric(7, 5),
  add column location_lon numeric(8, 5),
  add constraint field_location_both_or_neither
    check ((location_lat is null) = (location_lon is null)),
  -- numeric(p, s) accepts 'NaN', which sorts above every number and so fails BETWEEN.
  add constraint field_location_lat_range check (location_lat between -90 and 90),
  add constraint field_location_lon_range check (location_lon between -180 and 180);

comment on column field.location_lat is
  'Latitude of one point near the middle of the field, decimal degrees. Identifying: never copy into snapshots, proofs or logs.';
comment on column field.location_lon is
  'Longitude of one point near the middle of the field, decimal degrees (negative = west). Identifying: never copy into snapshots, proofs or logs.';
