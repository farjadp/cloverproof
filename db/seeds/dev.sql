-- Local development seed. NOT for staging or production (the runner refuses non-local hosts).
-- Fictional data only: example.org addresses, no real people, farms or locations.
-- Idempotent: fixed ids + on conflict do nothing.
--
-- The agronomist account has NO password (password_hash is NULL, so it cannot log in).
-- Set one with the user CLI from Step 5; never put a hash or password in git.

insert into organisation (id, name) values
  ('00000000-0000-4000-8000-000000000001', 'Example Agronomy Co (dev seed)')
on conflict do nothing;

insert into app_user (id, email, display_name, password_hash) values
  ('00000000-0000-4000-8000-000000000101', 'agronomist@example.org', 'Example Agronomist', null)
on conflict do nothing;

insert into membership (organisation_id, user_id, role) values
  ('00000000-0000-4000-8000-000000000001', '00000000-0000-4000-8000-000000000101', 'org_admin'),
  ('00000000-0000-4000-8000-000000000001', '00000000-0000-4000-8000-000000000101', 'agronomist')
on conflict do nothing;

insert into farmer (id, organisation_id, display_name) values
  ('00000000-0000-4000-8000-000000000201', '00000000-0000-4000-8000-000000000001', 'Example Farmer')
on conflict do nothing;

insert into farm (id, organisation_id, farmer_id, name) values
  ('00000000-0000-4000-8000-000000000301', '00000000-0000-4000-8000-000000000001',
   '00000000-0000-4000-8000-000000000201', 'Example Farm')
on conflict do nothing;

insert into field (id, organisation_id, farm_id, name) values
  ('00000000-0000-4000-8000-000000000401', '00000000-0000-4000-8000-000000000001',
   '00000000-0000-4000-8000-000000000301', 'North field (example)'),
  ('00000000-0000-4000-8000-000000000402', '00000000-0000-4000-8000-000000000001',
   '00000000-0000-4000-8000-000000000301', 'South field (example)')
on conflict do nothing;

insert into season (id, organisation_id, label) values
  ('00000000-0000-4000-8000-000000000501', '00000000-0000-4000-8000-000000000001', '2027')
on conflict do nothing;

-- Areas are made-up example sizes, entered by hand (no geometry until map drawing).
insert into field_geometry_version
  (id, organisation_id, field_id, season_id, geom, area_ha, area_source, created_by) values
  ('00000000-0000-4000-8000-000000000601', '00000000-0000-4000-8000-000000000001',
   '00000000-0000-4000-8000-000000000401', '00000000-0000-4000-8000-000000000501',
   null, 10, 'manual', '00000000-0000-4000-8000-000000000101'),
  ('00000000-0000-4000-8000-000000000602', '00000000-0000-4000-8000-000000000001',
   '00000000-0000-4000-8000-000000000402', '00000000-0000-4000-8000-000000000501',
   null, 20, 'manual', '00000000-0000-4000-8000-000000000101')
on conflict do nothing;
