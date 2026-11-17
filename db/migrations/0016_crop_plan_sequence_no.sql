-- 0016: crop_plan.sequence_no (CPO decision RK-X5 = A, 2026-11-16).
--
-- `season` (organisation planning period) + `crop_plan` (field x season x crop) stay; docs
-- and API call crop_plan the "season plan". Double-cropping is allowed (e.g. winter wheat
-- then soybeans on one field in one season), so there is NO unique on (field_id,
-- season_id). sequence_no orders the crops of one field in one season: 1, 2, ...
-- unique (field_id, season_id, sequence_no).
--
-- Insert without sequence_no (the current app form): the BEFORE INSERT trigger takes the
-- next free number for that field and season, under a transaction advisory lock so two
-- concurrent inserts do not pick the same number (the unique index is the backstop, 23505).
--
-- Existing rows: numbered 1, 2, ... per (field_id, season_id) by created_at, id. Before
-- this migration the app could create several plans for one field and season; they keep
-- their order. Runs before RLS (0021), so cp_migrator still sees every row.
set local role cp_migrator;

alter table crop_plan add column sequence_no smallint;

update crop_plan c
set sequence_no = n.rn
from (
  select id, row_number() over (partition by field_id, season_id order by created_at, id) as rn
  from crop_plan
) n
where n.id = c.id;

alter table crop_plan
  alter column sequence_no set not null,
  add constraint crop_plan_sequence_no_check check (sequence_no between 1 and 20),
  add constraint crop_plan_field_season_sequence_key unique (field_id, season_id, sequence_no);

comment on column crop_plan.sequence_no is
  'Order of this crop on the field within the season (1 = first crop; double-cropping = 2, ...). '
  'Unique per field and season. Assigned by trigger (next free number) when not given.';

create function crop_plan_next_sequence_no() returns trigger
language plpgsql set search_path = pg_catalog, public as $$
begin
  if new.sequence_no is null then
    perform pg_advisory_xact_lock(12016, hashtext(new.field_id::text || '/' || new.season_id::text));
    select coalesce(max(c.sequence_no), 0) + 1 into new.sequence_no
    from public.crop_plan c
    where c.field_id = new.field_id and c.season_id = new.season_id;
  end if;
  return new;
end
$$;

create trigger crop_plan_next_sequence_no
  before insert on crop_plan
  for each row execute function crop_plan_next_sequence_no();
