-- 0018: a soil test locks once it is used (CPO decision Q6, 2026-11-16; CLAUDE.md rules 4, 5).
--
-- "Used" = referenced by a crop plan (crop_plan.soil_test_id) that has at least one
-- recommendation. From then on the evidence behind a number cannot change:
--   soil_test        UPDATE and DELETE raise
--   soil_test_value  INSERT, UPDATE and DELETE raise (adding a value changes the test too)
-- Correction = a new soil_test row (+ values) and a new recommendation on it.
-- recommendation_line (later migration) will add "referenced by a line" to the same rule.
--
-- SQLSTATE 55000 (object_not_in_prerequisite_state) with constraint name soil_test_locked,
-- so the app can map it to a 409 like the version conflicts of 0012.
-- Runs as the invoker: crop plans and recommendations that reference a soil test are in its
-- organisation (composite foreign keys), so under RLS (0021) a writer that can see the soil
-- test also sees what locks it.
set local role cp_migrator;

create function soil_test_is_locked(p_organisation_id uuid, p_soil_test_id uuid) returns boolean
language sql stable set search_path = pg_catalog, public as $$
  select exists (
    select 1
    from public.crop_plan cp
    join public.recommendation r on r.organisation_id = cp.organisation_id and r.crop_plan_id = cp.id
    where cp.organisation_id = p_organisation_id and cp.soil_test_id = p_soil_test_id
  )
$$;

create function soil_test_lock_guard() returns trigger
language plpgsql set search_path = pg_catalog, public as $$
declare
  v_org  uuid;
  v_test uuid;
begin
  if tg_table_name = 'soil_test' then
    v_org := old.organisation_id;
    v_test := old.id;
  elsif tg_op = 'INSERT' then
    v_org := new.organisation_id;
    v_test := new.soil_test_id;
  else
    v_org := old.organisation_id;
    v_test := old.soil_test_id;
  end if;
  if public.soil_test_is_locked(v_org, v_test) then
    raise exception 'soil test % was used by a recommendation and is locked; enter a new soil test instead',
      v_test
      using errcode = 'object_not_in_prerequisite_state', constraint = 'soil_test_locked';
  end if;
  -- A value moved to another (unlocked) test: the target must not be locked either.
  if tg_table_name = 'soil_test_value' and tg_op = 'UPDATE'
     and new.soil_test_id is distinct from old.soil_test_id
     and public.soil_test_is_locked(new.organisation_id, new.soil_test_id) then
    raise exception 'soil test % was used by a recommendation and is locked; enter a new soil test instead',
      new.soil_test_id
      using errcode = 'object_not_in_prerequisite_state', constraint = 'soil_test_locked';
  end if;
  if tg_op = 'DELETE' then
    return old;
  end if;
  return new;
end
$$;

create trigger soil_test_lock_guard
  before update or delete on soil_test
  for each row execute function soil_test_lock_guard();

create trigger soil_test_value_lock_guard
  before insert or update or delete on soil_test_value
  for each row execute function soil_test_lock_guard();

comment on function soil_test_lock_guard() is
  'Q6: soil_test / soil_test_value rows of a test used by a recommendation cannot change. '
  'Correction = new soil test. SQLSTATE 55000, constraint soil_test_locked.';
