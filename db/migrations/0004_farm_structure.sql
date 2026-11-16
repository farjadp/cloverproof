-- farmer -> farm -> field -> field_geometry_version (per season) (ADR 0002).
-- Every org-owned table carries organisation_id. Child tables reference their parent by
-- (organisation_id, id), so a row can never point at a parent in another organisation.
set local role cp_migrator;

-- A farmer is a client record of one organisation. A Phase 4 farmer login is an app_user
-- with a `farmer` membership, linked here through app_user_id.
create table farmer (
  id               uuid primary key default gen_random_uuid(),
  organisation_id  uuid not null references organisation (id),
  display_name     text not null check (char_length(btrim(display_name)) between 1 and 200),
  app_user_id      uuid references app_user (id),
  notes            text check (notes is null or char_length(notes) <= 4000),
  created_at       timestamptz not null default now(),
  unique (organisation_id, id)
);

comment on table farmer is 'Farm client of an organisation. PII: display_name, notes.';

create table farm (
  id               uuid primary key default gen_random_uuid(),
  organisation_id  uuid not null,
  farmer_id        uuid not null,
  name             text not null check (char_length(btrim(name)) between 1 and 200),
  country_code     char(2) check (country_code is null or country_code ~ '^[A-Z]{2}$'),
  region           text check (region is null or char_length(region) <= 200),
  created_at       timestamptz not null default now(),
  unique (organisation_id, id),
  foreign key (organisation_id, farmer_id) references farmer (organisation_id, id)
);

create index farm_farmer_idx on farm (farmer_id);

create table field (
  id               uuid primary key default gen_random_uuid(),
  organisation_id  uuid not null,
  farm_id          uuid not null,
  name             text not null check (char_length(btrim(name)) between 1 and 200),
  created_at       timestamptz not null default now(),
  unique (organisation_id, id),
  foreign key (organisation_id, farm_id) references farm (organisation_id, id)
);

create index field_farm_idx on field (farm_id);

-- A season is an organisation's planning period (e.g. "2027").
create table season (
  id               uuid primary key default gen_random_uuid(),
  organisation_id  uuid not null references organisation (id),
  label            text not null check (char_length(btrim(label)) between 1 and 50),
  starts_on        date,
  ends_on          date,
  created_at       timestamptz not null default now(),
  check (starts_on is null or ends_on is null or ends_on > starts_on),
  unique (organisation_id, label),
  unique (organisation_id, id)
);

-- One geometry version per field per season. Geometry stays NULL until map drawing
-- (Phase 4); area_ha is then entered by hand and is what the engine uses.
create table field_geometry_version (
  id               uuid primary key default gen_random_uuid(),
  organisation_id  uuid not null,
  field_id         uuid not null,
  season_id        uuid not null,
  geom             geometry(MultiPolygon, 4326)
                   check (geom is null or (st_isvalid(geom) and not st_isempty(geom))),
  area_ha          numeric not null check (area_ha > 0),
  area_source      text not null check (area_source in ('manual', 'geometry')),
  created_by       uuid not null references app_user (id),
  created_at       timestamptz not null default now(),
  check (area_source <> 'geometry' or geom is not null),
  unique (field_id, season_id),
  unique (organisation_id, id),
  foreign key (organisation_id, field_id) references field (organisation_id, id),
  foreign key (organisation_id, season_id) references season (organisation_id, id)
);

create index field_geometry_version_geom_idx on field_geometry_version using gist (geom);

grant select, insert, update, delete on farmer, farm, field, season, field_geometry_version to cp_app;
