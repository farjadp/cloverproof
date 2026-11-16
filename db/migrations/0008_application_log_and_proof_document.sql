-- application_log (planned vs actual) and proof_document (immutable, approved only).
set local role cp_migrator;

-- One planned and/or actual application of one nutrient on a crop plan.
-- Rates are kg/ha of the stated form (elemental vs oxide always explicit).
create table application_log (
  id                  uuid primary key default gen_random_uuid(),
  organisation_id     uuid not null,
  crop_plan_id        uuid not null,
  -- The approved recommendation this application follows, if any.
  recommendation_id   uuid,
  form                nutrient_form not null,
  product             text check (product is null or char_length(product) <= 200),
  planned_date        date,
  planned_rate_kg_ha  numeric check (planned_rate_kg_ha is null or planned_rate_kg_ha >= 0),
  actual_date         date,
  actual_rate_kg_ha   numeric check (actual_rate_kg_ha is null or actual_rate_kg_ha >= 0),
  notes               text check (notes is null or char_length(notes) <= 4000),
  created_by          uuid not null references app_user (id),
  created_at          timestamptz not null default now(),
  check (planned_rate_kg_ha is not null or actual_rate_kg_ha is not null),
  foreign key (organisation_id, crop_plan_id) references crop_plan (organisation_id, id),
  foreign key (organisation_id, crop_plan_id, recommendation_id)
    references recommendation (organisation_id, crop_plan_id, id)
);

create index application_log_crop_plan_idx on application_log (crop_plan_id);

create table proof_document (
  id                 uuid primary key default gen_random_uuid(),
  organisation_id    uuid not null,
  recommendation_id  uuid not null,
  sha256             char(64) not null check (sha256 ~ '^[0-9a-f]{64}$'),
  -- Object key in the private bucket (ADR 0005 B1), write-once.
  storage_key        text not null unique,
  created_by         uuid not null references app_user (id),
  created_at         timestamptz not null default now(),
  check (storage_key = format('proof/%s/%s/%s.pdf', organisation_id, recommendation_id, sha256)),
  foreign key (organisation_id, recommendation_id) references recommendation (organisation_id, id)
);

create index proof_document_recommendation_idx on proof_document (recommendation_id);

comment on table proof_document is
  'Immutable. UPDATE/DELETE/TRUNCATE raise; cp_app has SELECT, INSERT only. Only for approved recommendations.';

create function proof_document_check_approved() returns trigger
language plpgsql as $$
begin
  if not exists (
    select 1 from review r
    where r.recommendation_id = new.recommendation_id and r.decision = 'approve'
  ) then
    raise exception 'recommendation % is not approved; no proof document allowed',
      new.recommendation_id
      using errcode = 'check_violation';
  end if;
  return new;
end
$$;

create trigger proof_document_check_approved
  before insert on proof_document
  for each row execute function proof_document_check_approved();

create trigger proof_document_immutable
  before update or delete on proof_document
  for each row execute function forbid_change();

create trigger proof_document_no_truncate
  before truncate on proof_document
  for each statement execute function forbid_change();

grant select, insert, update, delete on application_log to cp_app;
grant select, insert on proof_document to cp_app;
