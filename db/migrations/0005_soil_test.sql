-- Soil tests, matching engine/cloverproof_engine/models.py (SoilTest, SoilTestValue).
-- Enum labels are the engine's StrEnum values, character for character.
-- No agronomic constants here: only units, forms and methods as recorded on the report.
set local role cp_migrator;

create type soil_test_source as enum ('lab', 'estimate');
create type nutrient_form as enum ('N', 'NO3-N', 'P', 'P2O5', 'K', 'K2O');
create type concentration_unit as enum ('mg/kg', 'ppm');
create type extraction_method as enum ('olsen', 'bray-1', 'mehlich-3', 'other');

create table soil_test (
  id               uuid primary key default gen_random_uuid(),
  organisation_id  uuid not null,
  field_id         uuid not null,
  sample_date      date not null,
  depth_top_cm     numeric not null check (depth_top_cm >= 0),
  depth_bottom_cm  numeric not null check (depth_bottom_cm > 0),
  source           soil_test_source not null,
  lab              text check (lab is null or char_length(btrim(lab)) between 1 and 200),
  created_by       uuid not null references app_user (id),
  created_at       timestamptz not null default now(),
  check (depth_bottom_cm > depth_top_cm),
  unique (organisation_id, id),
  foreign key (organisation_id, field_id) references field (organisation_id, id)
);

create index soil_test_field_idx on soil_test (field_id, sample_date desc);

-- One measured value. The extraction method belongs to the value, not the test.
create table soil_test_value (
  id                        uuid primary key default gen_random_uuid(),
  organisation_id           uuid not null,
  soil_test_id              uuid not null,
  form                      nutrient_form not null,
  -- Element the form expresses (engine `nutrient_of`): N, P or K. Derived, never entered.
  nutrient                  text not null generated always as (
                              case form
                                when 'N' then 'N' when 'NO3-N' then 'N'
                                when 'P' then 'P' when 'P2O5' then 'P'
                                when 'K' then 'K' when 'K2O' then 'K'
                              end
                            ) stored,
  value                     numeric not null check (value >= 0),
  unit                      concentration_unit not null,
  extraction_method         extraction_method not null,
  extraction_method_detail  text,
  created_at                timestamptz not null default now(),
  check (extraction_method <> 'other'
         or char_length(btrim(coalesce(extraction_method_detail, ''))) > 0),
  -- Engine rule: each nutrient appears once per test (in one form).
  unique (soil_test_id, nutrient),
  foreign key (organisation_id, soil_test_id)
    references soil_test (organisation_id, id) on delete cascade
);

grant select, insert, update, delete on soil_test, soil_test_value to cp_app;
