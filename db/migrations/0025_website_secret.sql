-- Website admin: AI-provider API keys (ADR 0013; docs/plans/website-admin.md §5).
-- Envelope-encrypted by the website (AES-256-GCM data key wrapped by WEBSITE_SECRETS_KEK from env;
-- the master key is never in git or this database). The database never sees a plaintext key.
-- One active row per provider; replacing a key inserts a new version and revokes the old one, so
-- history stays (without plaintext). Only cp_website_admin can read or write; no DELETE.
-- RLS class website_admin (db/rls_tables.yaml).

set local role cp_migrator;

create type website_secret_provider as enum ('anthropic', 'google_gemini', 'openai', 'fal');

create table website_secret (
  id                 uuid primary key default gen_random_uuid(),
  provider           website_secret_provider not null,
  version            int not null check (version >= 1),
  -- Sealed envelope (versioned JSON bytes: wrapped data key, IVs, tags, ciphertext, KEK id).
  sealed             bytea not null check (octet_length(sealed) between 64 and 8192),
  kek_id             text not null check (kek_id ~ '^[A-Za-z0-9_.-]{1,40}$'),
  -- Shown in the admin instead of the key.
  last4              text not null check (last4 ~ '^[A-Za-z0-9_-]{4}$'),
  -- Monthly spending cap in USD for the future content agents (P4); null = no cap set.
  monthly_budget_usd numeric(10, 2) check (monthly_budget_usd is null or monthly_budget_usd >= 0),
  created_at         timestamptz not null default now(),
  created_by         uuid not null references website_user (id),
  revoked_at         timestamptz,
  revoked_by         uuid references website_user (id),
  last_test_at       timestamptz,
  last_test_ok       boolean,
  unique (provider, version),
  check ((revoked_at is null) = (revoked_by is null))
);

-- At most one active key per provider.
create unique index website_secret_one_active on website_secret (provider) where revoked_at is null;

-- Sealed bytes, provider, version and authorship never change after insert; a revoked key stays revoked.
create function website_secret_guard() returns trigger
language plpgsql set search_path = '' as $$
begin
  if new.sealed <> old.sealed or new.kek_id <> old.kek_id or new.provider <> old.provider
     or new.version <> old.version or new.last4 <> old.last4 or new.created_by <> old.created_by
     or new.created_at <> old.created_at then
    raise exception 'website_secret % is immutable; insert a new version', old.id
      using errcode = 'insufficient_privilege';
  end if;
  if old.revoked_at is not null and new.revoked_at is distinct from old.revoked_at then
    raise exception 'website_secret % is revoked', old.id using errcode = 'insufficient_privilege';
  end if;
  return new;
end
$$;
revoke all on function website_secret_guard() from public;

create trigger website_secret_guard before update on website_secret
  for each row execute function website_secret_guard();
create trigger website_secret_no_delete before delete or truncate on website_secret
  for each statement execute function forbid_change();

grant select, insert on website_secret to cp_website_admin;
grant update (revoked_at, revoked_by, monthly_budget_usd, last_test_at, last_test_ok)
  on website_secret to cp_website_admin;

comment on table website_secret is
  'AI-provider API keys for the website admin (ADR 0013): envelope-encrypted (KEK in env), last 4'
  ' characters shown, one active row per provider, versions kept, never deleted. cp_website_admin only.';
