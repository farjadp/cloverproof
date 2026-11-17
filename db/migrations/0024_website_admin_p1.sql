-- Website admin P1: staff accounts, sessions, MFA recovery codes, one-time links, rate limits,
-- system log with 60-day retention, job health (docs/plans/website-admin.md §5, ADR 0012 auth,
-- ADR 0014 system log). Website staff only: no link to app_user / organisation (web app).
--
-- New role cp_website_admin (NOLOGIN), used by the website's /admin code through its own pool.
-- It gets grants on the website_* tables below and nothing else: no pilot_request, site_event
-- or web-app table (CLAUDE.md rule 12; least privilege). The public pages keep cp_website, which
-- gets nothing here. Login created outside git by the operator:
--   create role cp_website_admin_login login password '...' connection limit 10
--     in role cp_website_admin;
--   alter role cp_website_admin_login set statement_timeout = '10s';
--   alter role cp_website_admin_login set lock_timeout = '2s';
--   alter role cp_website_admin_login set idle_in_transaction_session_timeout = '30s';
-- (Role-level settings apply only to the role that logs in, so they go on the login role.)
--
-- RLS class (db/rls_tables.yaml): website_admin — grants + SECURITY DEFINER purge, RLS
-- disabled, never organisation-scoped (ADR 0008 §3).

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'cp_website_admin') then
    create role cp_website_admin nologin;
  end if;
end
$$;

grant usage on schema public to cp_website_admin;

set local role cp_migrator;

create type website_role as enum ('admin', 'editor', 'author');
create type website_log_kind as enum ('auth', 'admin', 'content', 'secret', 'error', 'job');
create type website_log_outcome as enum ('ok', 'denied', 'failed');
create type website_token_kind as enum ('invite', 'password_reset', 'mfa_reset');

create table website_user (
  id                  uuid primary key default gen_random_uuid(),
  -- Lower-case, trimmed by the app; null once the user is deleted (pseudonymised).
  email               text unique check (email = lower(btrim(email)) and char_length(email) between 3 and 320),
  display_name        text not null check (char_length(btrim(display_name)) between 1 and 120),
  role                website_role not null,
  -- argon2id PHC string; null until the invite is accepted.
  password_hash       text check (password_hash like '$argon2id$%'),
  password_changed_at timestamptz,
  -- TOTP secret, AES-256-GCM envelope (ADR 0013 format); null until enrolled.
  mfa_secret_enc      bytea,
  mfa_enabled_at      timestamptz,
  failed_logins       int not null default 0 check (failed_logins >= 0),
  locked_until        timestamptz,
  disabled_at         timestamptz,
  deleted_at          timestamptz,
  created_at          timestamptz not null default now(),
  -- Null only for the first admin created by the CLI.
  created_by          uuid references website_user (id),
  check (mfa_enabled_at is null or mfa_secret_enc is not null),
  check (deleted_at is null
         or (email is null and password_hash is null and mfa_secret_enc is null
             and mfa_enabled_at is null and disabled_at is not null))
);

create table website_user_recovery_code (
  id        uuid primary key default gen_random_uuid(),
  user_id   uuid not null references website_user (id),
  code_hash bytea not null unique check (octet_length(code_hash) = 32),
  used_at   timestamptz
);
create index website_user_recovery_code_user_idx on website_user_recovery_code (user_id);

create table website_session (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references website_user (id),
  -- sha256 of the cookie token / CSRF token; the raw tokens are never stored.
  token_hash      bytea not null unique check (octet_length(token_hash) = 32),
  csrf_token_hash bytea not null check (octet_length(csrf_token_hash) = 32),
  created_at      timestamptz not null default now(),
  last_seen_at    timestamptz not null default now(),
  expires_at      timestamptz not null,
  mfa_verified_at timestamptz,
  step_up_at      timestamptz,
  -- IPv4 /24 or IPv6 /48 only, never a full address.
  ip_prefix       cidr check (ip_prefix is null
                              or (family(ip_prefix) = 4 and masklen(ip_prefix) <= 24)
                              or (family(ip_prefix) = 6 and masklen(ip_prefix) <= 48)),
  ua_family       text check (char_length(ua_family) <= 40),
  revoked_at      timestamptz,
  check (expires_at > created_at)
);
create index website_session_user_idx on website_session (user_id);

create table website_one_time_token (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references website_user (id),
  kind       website_token_kind not null,
  token_hash bytea not null unique check (octet_length(token_hash) = 32),
  expires_at timestamptz not null,
  used_at    timestamptz,
  created_by uuid references website_user (id),
  created_at timestamptz not null default now(),
  check (expires_at > created_at and expires_at <= created_at + interval '72 hours')
);
create index website_one_time_token_user_idx on website_one_time_token (user_id);

create table website_rate_limit (
  -- HMAC of the e-mail address or IP prefix (key in the app's env), never the raw value.
  key_hash     bytea not null check (octet_length(key_hash) = 32),
  window_start timestamptz not null,
  count        int not null default 0 check (count >= 0),
  primary key (key_hash, window_start)
);

create table website_log (
  id            bigint generated always as identity primary key,
  occurred_at   timestamptz not null default now(),
  actor_user_id uuid references website_user (id),
  kind          website_log_kind not null,
  action        text not null check (action ~ '^[a-z0-9_.]{1,80}$'),
  target_type   text check (target_type ~ '^[a-z0-9_]{1,40}$'),
  target_id     text check (char_length(target_id) <= 80),
  outcome       website_log_outcome not null,
  ip_prefix     cidr check (ip_prefix is null
                            or (family(ip_prefix) = 4 and masklen(ip_prefix) <= 24)
                            or (family(ip_prefix) = 6 and masklen(ip_prefix) <= 48)),
  ua_family     text check (char_length(ua_family) <= 40),
  -- Whitelisted keys only (enforced in the app); never secrets, tokens, bodies or passwords.
  detail        jsonb not null default '{}'::jsonb
                check (jsonb_typeof(detail) = 'object' and pg_column_size(detail) <= 4096)
);
create index website_log_occurred_at_idx on website_log (occurred_at);
create index website_log_actor_idx on website_log (actor_user_id, occurred_at);

-- Rows never change; deletion only through website_log_purge() (60 days).
create trigger website_log_no_update before update on website_log
  for each row execute function forbid_change();
create trigger website_log_no_truncate before truncate on website_log
  for each statement execute function forbid_change();

create table website_job_run (
  job           text primary key check (job ~ '^[a-z0-9_]{1,40}$'),
  last_ok_at    timestamptz,
  last_error_at timestamptz,
  last_error    text check (char_length(last_error) <= 500)
);

-- Last-admin guard: there is always at least one active admin once one exists.
create function website_user_keep_one_admin() returns trigger
language plpgsql set search_path = '' as $$
begin
  if old.role = 'admin' and old.disabled_at is null and old.deleted_at is null
     and not (new.role = 'admin' and new.disabled_at is null and new.deleted_at is null) then
    -- Serialise concurrent demotions so two admins can't remove each other at once.
    -- FOR UPDATE reads the latest committed rows (also under REPEATABLE READ / SERIALIZABLE,
    -- where a concurrent change then fails with a serialization error instead of passing).
    perform pg_advisory_xact_lock(hashtext('website_user_keep_one_admin'));
    perform 1 from public.website_user u
      where u.id <> old.id and u.role = 'admin' and u.disabled_at is null and u.deleted_at is null
      for update;
    if not found then
      raise exception 'the last active admin cannot be demoted, disabled or deleted'
        using errcode = 'check_violation';
    end if;
  end if;
  return new;
end
$$;

-- A deleted (pseudonymised) user stays deleted.
create function website_user_stay_deleted() returns trigger
language plpgsql set search_path = '' as $$
begin
  if old.deleted_at is not null then
    raise exception 'website_user % is deleted and cannot change', old.id
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end
$$;

create trigger website_user_stay_deleted before update on website_user
  for each row execute function website_user_stay_deleted();
create trigger website_user_keep_one_admin before update on website_user
  for each row execute function website_user_keep_one_admin();
create trigger website_user_no_delete before delete or truncate on website_user
  for each statement execute function forbid_change();

-- 60-day retention (ADR 0014). Also clears expired/revoked sessions, used/expired one-time
-- links and old rate-limit windows (after 1 day). Returns the number of log rows deleted.
create function website_log_purge() returns bigint
language plpgsql security definer set search_path = '' as $$
declare
  removed bigint;
begin
  delete from public.website_log where occurred_at < now() - interval '60 days';
  get diagnostics removed = row_count;
  delete from public.website_session
    where coalesce(revoked_at, expires_at) < now() - interval '1 day';
  delete from public.website_one_time_token
    where coalesce(used_at, expires_at) < now() - interval '1 day';
  delete from public.website_rate_limit where window_start < now() - interval '1 day';
  return removed;
end
$$;

revoke all on function website_log_purge() from public;
revoke all on function website_user_keep_one_admin() from public;
revoke all on function website_user_stay_deleted() from public;

grant select, insert on website_user to cp_website_admin;
-- No UPDATE of id, created_at, created_by: history can't be rewritten.
grant update (email, display_name, role, password_hash, password_changed_at, mfa_secret_enc,
              mfa_enabled_at, failed_logins, locked_until, disabled_at, deleted_at)
  on website_user to cp_website_admin;
grant select, insert, update on website_session, website_one_time_token, website_job_run
  to cp_website_admin;
-- Recovery codes are secret material, not an audit record: removed on delete / MFA reset.
grant select, insert, update, delete on website_user_recovery_code to cp_website_admin;
grant select, insert, update, delete on website_rate_limit to cp_website_admin;
grant select, insert on website_log to cp_website_admin;
grant execute on function website_log_purge() to cp_website_admin;

comment on table website_user is
  'Website admin/editor/author accounts (ADR 0012). Separate from app_user. Created by CLI or'
  ' invite; never hard-deleted (delete = pseudonymise). PII: email, display_name.';
comment on table website_log is
  'Website system log (ADR 0014): auth, admin, content, secret, error, job. Append-only;'
  ' deleted after 60 days by website_log_purge(). PII: actor id, IP prefix, browser family.';
comment on table website_user_recovery_code is 'MFA recovery codes (sha256 only), single use.';
comment on table website_session is
  'Website admin sessions: sha256 of the cookie token only; IP prefix (/24, /48) + browser family.';
comment on table website_one_time_token is 'Invite / reset links (sha256 only), at most 72 h.';
comment on table website_rate_limit is 'Login throttling keyed by HMAC; purged after 1 day.';
comment on table website_job_run is 'Health of website background jobs (e.g. log purge).';
comment on function website_log_purge() is
  'Deletes website_log rows older than 60 days and expired sessions/links/rate-limit windows.';
