-- Pilot requests from the public website (docs/plans/website-v1.md, step 5).
-- Written only by the website server. No public access.

create table if not exists pilot_request (
  id              uuid primary key default gen_random_uuid(),
  created_at      timestamptz not null default now(),
  locale          text not null check (char_length(locale) between 2 and 5),
  full_name       text not null check (char_length(full_name) between 1 and 200),
  email           text not null check (char_length(email) <= 320 and email ~* '^[^\s@]+@[^\s@]+\.[^\s@]+$'),
  country         text not null check (char_length(country) between 1 and 100),
  farm_size_text  text not null check (char_length(farm_size_text) between 1 and 100), -- free text with units, as entered
  main_crop       text not null check (char_length(main_crop) between 1 and 100),
  notes           text check (notes is null or char_length(notes) <= 2000),
  consent_at      timestamptz not null,
  consent_text    text not null,          -- exact consent wording shown to the person
  status          text not null default 'new' check (status in ('new', 'contacted', 'accepted', 'declined')),
  deleted_at      timestamptz             -- set on a deletion request; row purged by a later job
);

comment on table pilot_request is 'Pilot farm requests from the website. PII: name, email.';

create index if not exists pilot_request_created_at_idx on pilot_request (created_at desc);
create index if not exists pilot_request_email_idx on pilot_request (lower(email));
