-- crop_plan (editable draft inputs) and recommendation (immutable, versioned) (ADR 0002).
-- A recommendation stores the full engine document (`result`) and the exact inputs it was
-- computed from (`inputs_snapshot`); typed columns duplicate the fields we filter and join
-- on, and CHECK constraints keep them equal to the document.
set local role cp_migrator;

create table crop_plan (
  id                 uuid primary key default gen_random_uuid(),
  organisation_id    uuid not null,
  field_id           uuid not null,
  season_id          uuid not null,
  -- Crop id as used by packs (engine `Crop`, e.g. 'wheat'); validated by the engine.
  crop               text not null check (crop ~ '^[a-z][a-z0-9_-]*$'),
  target_yield_t_ha  numeric not null check (target_yield_t_ha > 0),
  -- Normalised like the engine: trimmed, lower case, non-empty.
  previous_crop      text not null
                     check (previous_crop <> '' and previous_crop = lower(btrim(previous_crop))),
  plan_date          date not null,
  soil_test_id       uuid,
  created_by         uuid not null references app_user (id),
  created_at         timestamptz not null default now(),
  unique (organisation_id, id),
  foreign key (organisation_id, field_id) references field (organisation_id, id),
  foreign key (organisation_id, season_id) references season (organisation_id, id),
  foreign key (organisation_id, soil_test_id) references soil_test (organisation_id, id)
);

create index crop_plan_field_season_idx on crop_plan (field_id, season_id);

create type confidence_level as enum ('low', 'medium', 'high');
create type recommendation_kind as enum ('engine', 'agronomist');

create table recommendation (
  id                uuid primary key default gen_random_uuid(),
  organisation_id   uuid not null,
  crop_plan_id      uuid not null,
  -- engine rows: NULL (a re-run is a new root). agronomist rows: the version they edit.
  parent_id         uuid,
  kind              recommendation_kind not null,
  reason            text,
  inputs_snapshot   jsonb not null check (jsonb_typeof(inputs_snapshot) = 'object'),
  -- Full engine output (cloverproof_engine.results.Recommendation, model_dump(mode="json")).
  -- Agronomist rows hold the same document with the agronomist's final numbers.
  result            jsonb not null check (jsonb_typeof(result) = 'object'),
  engine_version    text not null check (engine_version <> ''),
  pack_id           text not null check (pack_id <> ''),
  pack_version      text not null check (pack_version <> ''),
  pack_status       text not null check (pack_status <> ''),
  pack_sha256       char(64) not null check (pack_sha256 ~ '^[0-9a-f]{64}$'),
  confidence        confidence_level not null,
  -- Typed copy of result.nitrogen.rate.value for queries and the diff view.
  n_rate_kg_ha      numeric not null
                    generated always as ((result #>> '{nitrogen,rate,value}')::numeric) stored,
  created_by        uuid not null references app_user (id),
  created_at        timestamptz not null default now(),

  check ((kind = 'engine' and parent_id is null) or (kind = 'agronomist' and parent_id is not null)),
  check (parent_id is null or char_length(btrim(coalesce(reason, ''))) > 0),
  check (parent_id is null or parent_id <> id),
  -- Typed columns must equal the stored document.
  check (result ->> 'engine_version' = engine_version),
  check (result ->> 'pack_id' = pack_id),
  check (result ->> 'pack_version' = pack_version),
  check (result ->> 'pack_status' = pack_status),
  check (result ->> 'pack_sha256' = pack_sha256),
  check (result ->> 'confidence' = confidence::text),
  check (result -> 'input_snapshot' = inputs_snapshot),
  check (result #>> '{nitrogen,rate,unit}' = 'kg N/ha'),
  check (n_rate_kg_ha >= 0),

  unique (organisation_id, id),
  unique (organisation_id, crop_plan_id, id),
  unique (id, parent_id),
  foreign key (organisation_id, crop_plan_id) references crop_plan (organisation_id, id),
  -- Parent must be in the same organisation and the same crop plan.
  foreign key (organisation_id, crop_plan_id, parent_id)
    references recommendation (organisation_id, crop_plan_id, id)
);

create index recommendation_crop_plan_idx on recommendation (crop_plan_id, created_at);
create index recommendation_parent_idx on recommendation (parent_id);

comment on table recommendation is
  'Immutable. UPDATE/DELETE/TRUNCATE raise; cp_app has SELECT, INSERT only. Edits are new rows (parent_id + reason).';

-- Author checks: the creator is an active member of the organisation; an agronomist row
-- (an edit of numbers) can only be written by an agronomist of that organisation.
create function recommendation_check_author() returns trigger
language plpgsql as $$
begin
  if not exists (select 1 from member_organisation_ids(new.created_by) o where o = new.organisation_id) then
    raise exception 'recommendation author % is not an active member of organisation %',
      new.created_by, new.organisation_id
      using errcode = 'insufficient_privilege';
  end if;
  if new.kind = 'agronomist'
     and not has_org_role(new.created_by, new.organisation_id, 'agronomist') then
    raise exception 'only an agronomist of the organisation can create an agronomist recommendation'
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end
$$;

create trigger recommendation_check_author
  before insert on recommendation
  for each row execute function recommendation_check_author();

create trigger recommendation_immutable
  before update or delete on recommendation
  for each row execute function forbid_change();

create trigger recommendation_no_truncate
  before truncate on recommendation
  for each statement execute function forbid_change();

grant select, insert, update, delete on crop_plan to cp_app;
grant select, insert on recommendation to cp_app;
