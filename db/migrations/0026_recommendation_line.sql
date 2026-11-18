-- 0026: recommendation_line, one immutable row per nutrient and split (S2-DB-09, decision R2;
-- docs/plans/schema-gap-analysis.md section 3; CLAUDE.md rules 4 and 7).
--
-- P/K and splits are stored per line, never as columns on `recommendation`.
--
-- Backfill: NONE. Existing recommendations are immutable history and keep their numbers in
-- `recommendation.result`; they get no lines. Code reading lines must fall back to `result`
-- for a recommendation that has none.
--
-- Units (rule 7): rate_kg_ha is always kg/ha of the form named in nutrient_form, so there is
-- no free unit column. The database never converts P<->P2O5 or K<->K2O (engine `units.py`).
-- rate_kg_ha NULL means "no number given" (e.g. P/K without a soil test, rule 3) and then
-- no_rate_reason is required.
--
-- split_no 0 = season total, 1..n = splits. product_id has no FK yet: the catalog and the FK
-- arrive with the product matching work. timing_basis is only a label here; GDD logic is S4.
--
-- Immutable (rule 4): forbid_change on UPDATE/DELETE/TRUNCATE and cp_app has SELECT, INSERT
-- only. A line can be added only in the transaction that created its recommendation, by the
-- same author, so a stored or approved recommendation cannot gain numbers later. An edit is
-- a new recommendation row with its own complete set of lines.
--
-- RLS follows 0021 / ADR 0008 section 7: forced, restrictive org boundary, permissive SELECT
-- and INSERT, author bound to the context user. No UPDATE/DELETE policy exists.
set local role cp_migrator;

create type timing_basis as enum ('gdd', 'calendar', 'manual');

create table recommendation_line (
  id                   uuid primary key default gen_random_uuid(),
  organisation_id      uuid not null,
  recommendation_id    uuid not null,
  nutrient             text not null check (nutrient in ('N', 'P', 'K')),
  nutrient_form        nutrient_form not null,
  rate_kg_ha           numeric,
  no_rate_reason       text,
  split_no             smallint not null default 0 check (split_no >= 0),
  stage_label          text check (char_length(btrim(stage_label)) > 0),
  timing_window_start  date,
  timing_window_end    date,
  timing_basis         timing_basis,
  product_id           uuid,
  explanation          text not null check (char_length(btrim(explanation)) > 0),
  uses_placeholder     boolean not null,
  confidence           confidence_level not null,
  created_by           uuid not null references app_user (id),
  created_at           timestamptz not null default now(),

  constraint recommendation_line_form_matches_nutrient check (
    (nutrient = 'N' and nutrient_form = 'N')
    or (nutrient = 'P' and nutrient_form in ('P', 'P2O5'))
    or (nutrient = 'K' and nutrient_form in ('K', 'K2O'))),
  -- numeric accepts 'NaN' and 'Infinity', and both compare >= 0.
  constraint recommendation_line_rate_finite
    check (rate_kg_ha >= 0 and rate_kg_ha < 'Infinity'),
  constraint recommendation_line_rate_or_reason check (
    (rate_kg_ha is not null and no_rate_reason is null)
    or (rate_kg_ha is null and char_length(btrim(coalesce(no_rate_reason, ''))) > 0)),
  constraint recommendation_line_window_complete
    check ((timing_window_start is null) = (timing_window_end is null)),
  constraint recommendation_line_window_order
    check (timing_window_end >= timing_window_start),
  constraint recommendation_line_window_has_basis
    check (timing_window_start is null or timing_basis is not null),

  unique (organisation_id, id),
  unique (organisation_id, recommendation_id, nutrient, split_no),
  foreign key (organisation_id, recommendation_id)
    references recommendation (organisation_id, id)
);

comment on table recommendation_line is
  'Immutable. One row per nutrient and split, written with its recommendation. rate_kg_ha is '
  'kg/ha of nutrient_form. Older recommendations have no lines (see recommendation.result).';

-- Runs as the invoker, so it reads the parent through RLS: from the wrong context it finds
-- nothing and fails closed.
create function recommendation_line_check_parent() returns trigger
language plpgsql set search_path = pg_catalog, public as $$
declare
  v_created_at timestamptz;
  v_created_by uuid;
begin
  select r.created_at, r.created_by into v_created_at, v_created_by
  from public.recommendation r
  where r.organisation_id = new.organisation_id and r.id = new.recommendation_id;
  if not found then
    raise exception 'recommendation % is not available in organisation %',
      new.recommendation_id, new.organisation_id
      using errcode = 'insufficient_privilege';
  end if;
  -- recommendation.created_at defaults to now(), which is the transaction start.
  if v_created_at is distinct from transaction_timestamp() then
    raise exception 'recommendation % is sealed: lines are written in the transaction that creates it',
      new.recommendation_id
      using errcode = 'object_not_in_prerequisite_state';
  end if;
  if v_created_by is distinct from new.created_by then
    raise exception 'a recommendation line must have the author of its recommendation'
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end
$$;

create trigger recommendation_line_check_parent
  before insert on recommendation_line
  for each row execute function recommendation_line_check_parent();

create trigger recommendation_line_immutable
  before update or delete on recommendation_line
  for each row execute function forbid_change();

create trigger recommendation_line_no_truncate
  before truncate on recommendation_line
  for each statement execute function forbid_change();

grant select, insert on recommendation_line to cp_app;

alter table recommendation_line enable row level security;
alter table recommendation_line force row level security;

create policy recommendation_line_org_boundary on recommendation_line
  as restrictive for all to cp_app
  using (organisation_id = (select public.app_ctx_org()))
  with check (organisation_id = (select public.app_ctx_org()));

create policy recommendation_line_select on recommendation_line for select to cp_app
  using (organisation_id = (select public.app_ctx_org()));

create policy recommendation_line_insert on recommendation_line for insert to cp_app
  with check (organisation_id = (select public.app_ctx_org())
              and created_by = (select public.app_ctx_user()));
