-- Organisations, users, sessions, memberships (ADR 0002, ADR 0005 A1).
set local role cp_migrator;

create table organisation (
  id          uuid primary key default gen_random_uuid(),
  name        text not null check (char_length(btrim(name)) between 1 and 200),
  created_at  timestamptz not null default now()
);

create table app_user (
  id                uuid primary key default gen_random_uuid(),
  email             text not null
                    check (char_length(email) <= 320 and email ~* '^[^\s@]+@[^\s@]+\.[^\s@]+$'),
  display_name      text not null check (char_length(btrim(display_name)) between 1 and 200),
  -- argon2id PHC string, written by the app. NULL = no password set, cannot log in locally.
  password_hash     text check (password_hash is null or password_hash like '$argon2id$%'),
  -- Optional TOTP secret. The app encrypts it before storing (key from env), never plaintext.
  totp_secret       text,
  auth_provider     text not null default 'local' check (auth_provider in ('local', 'oidc')),
  -- Subject claim from an external identity provider (Phase 4); NULL for local accounts.
  external_subject  text,
  disabled_at       timestamptz,
  created_at        timestamptz not null default now(),
  check (auth_provider <> 'oidc' or external_subject is not null),
  unique (auth_provider, external_subject)
);

create unique index app_user_email_key on app_user (lower(email));

comment on table app_user is 'Internal tool users (ADR 0005 A1). Accounts are created by CLI only. PII: email, display_name.';

create table user_session (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references app_user (id) on delete cascade,
  -- SHA-256 hex of the random cookie token; the token itself is never stored.
  token_sha256  char(64) not null unique check (token_sha256 ~ '^[0-9a-f]{64}$'),
  created_at    timestamptz not null default now(),
  last_seen_at  timestamptz not null default now(),
  -- Absolute expiry; idle expiry is checked by the app against last_seen_at.
  expires_at    timestamptz not null,
  revoked_at    timestamptz,
  check (expires_at > created_at)
);

create index user_session_user_idx on user_session (user_id);

create type membership_role as enum ('owner', 'agronomist', 'staff', 'farmer');

-- One row per (organisation, user, role); a user may hold several roles in one organisation.
create table membership (
  id               uuid primary key default gen_random_uuid(),
  organisation_id  uuid not null references organisation (id) on delete cascade,
  user_id          uuid not null references app_user (id) on delete cascade,
  role             membership_role not null,
  created_at       timestamptz not null default now(),
  unique (organisation_id, user_id, role)
);

create index membership_user_idx on membership (user_id);

-- Org-scoping helpers for the app's data-access layer (and the review trigger).
create function member_organisation_ids(p_user_id uuid) returns setof uuid
language sql stable as $$
  select distinct m.organisation_id
  from membership m
  join app_user u on u.id = m.user_id
  where m.user_id = p_user_id and u.disabled_at is null
$$;

create function has_org_role(p_user_id uuid, p_organisation_id uuid, p_role membership_role)
returns boolean
language sql stable as $$
  select exists (
    select 1
    from membership m
    join app_user u on u.id = m.user_id
    where m.user_id = p_user_id
      and m.organisation_id = p_organisation_id
      and m.role = p_role
      and u.disabled_at is null
  )
$$;

grant select, insert, update, delete on organisation, app_user, user_session, membership to cp_app;
