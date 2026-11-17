-- 0017: farmer.record_kind (CPO decision Q5, 2026-11-16; CLAUDE.md rule 8 "any farm not
-- flagged as synthetic test data is a real farm").
--
--   real       a real farmer (the default; every existing row becomes real)
--   demo       synthetic test or demo data
--   reference  a published reference case entered by hand (external_reference goldens)
--
-- Rules:
--   * cp_app (web app) cannot write the column at all: its INSERT/UPDATE grants on farmer
--     become column grants without record_kind, so every farmer the app creates is real.
--   * Only a human superadmin may set a non-real value or change it: the trigger requires
--     the operator (superuser) or app.user_id = a human, enabled superadmin. The CLI path is
--     cp_admin (column grants below) with that context.
--   * Frozen once the farmer has a recommendation (any crop plan on any field of any farm of
--     theirs): no real <-> demo switch under an existing plan. Create a new farmer instead.
-- The trigger runs as the invoker. All rows it reads (farm, field, crop_plan,
-- recommendation) are in the farmer's organisation (composite foreign keys), so a writer
-- that can see the farmer row under RLS (0021) also sees every row that freezes it.
set local role cp_migrator;

alter table farmer
  add column record_kind text not null default 'real'
    constraint farmer_record_kind_check check (record_kind in ('real', 'demo', 'reference'));

comment on column farmer.record_kind is
  'real (default) | demo | reference. Set or changed only by a human superadmin (CLI) and '
  'only while the farmer has no recommendation. cp_app cannot write it.';

-- cp_app: same columns as before, minus record_kind. (id/created_at keep their defaults.)
revoke insert, update on farmer from cp_app;
grant insert (organisation_id, display_name, app_user_id, notes) on farmer to cp_app;
grant update (display_name, app_user_id, notes) on farmer to cp_app;
-- cp_admin inherits cp_app's grants and may also set record_kind (trigger below decides).
grant insert (record_kind), update (record_kind) on farmer to cp_admin;

create function farmer_has_recommendation(p_organisation_id uuid, p_farmer_id uuid)
returns boolean
language sql stable set search_path = pg_catalog, public as $$
  select exists (
    select 1
    from public.farm fa
    join public.field fi on fi.organisation_id = fa.organisation_id and fi.farm_id = fa.id
    join public.crop_plan cp on cp.organisation_id = fi.organisation_id and cp.field_id = fi.id
    join public.recommendation r on r.organisation_id = cp.organisation_id and r.crop_plan_id = cp.id
    where fa.organisation_id = p_organisation_id and fa.farmer_id = p_farmer_id
  )
$$;

create function farmer_record_kind_guard() returns trigger
language plpgsql set search_path = pg_catalog, public as $$
declare
  v_operator boolean := exists (select 1 from pg_roles where rolname = current_user and rolsuper);
  v_actor    uuid := public.admin_event_actor();
begin
  if tg_op = 'INSERT' then
    if new.record_kind = 'real' then
      return new;
    end if;
  elsif new.record_kind is not distinct from old.record_kind then
    return new;
  end if;
  if not v_operator and not (v_actor is not null and public.is_human_superadmin(v_actor)) then
    raise exception 'only a human superadmin can set farmer.record_kind (set app.user_id)'
      using errcode = 'insufficient_privilege';
  end if;
  if tg_op = 'UPDATE' and public.farmer_has_recommendation(old.organisation_id, old.id) then
    raise exception 'farmer % already has a recommendation; record_kind is frozen. Create a new farmer instead',
      old.id
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end
$$;

create trigger farmer_record_kind_guard
  before insert or update of record_kind on farmer
  for each row execute function farmer_record_kind_guard();
