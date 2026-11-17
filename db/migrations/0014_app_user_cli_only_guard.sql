-- 0014: approver accounts are reset, disabled or re-enabled with the CLI only (ciso NB1, PR #7).
--
-- cp_app holds UPDATE (password_hash, password_change_required, display_name, disabled_at)
-- on app_user (0011) for rehash on login, own password change and the owner page. Without
-- a guard an owner page (or a compromised app) could reset the password of a superadmin,
-- sign in as them and approve as `superadmin_approved`.
--
-- Rule, enforced here for any role that is cp_app but not cp_admin (the web app):
--   password_hash, password_change_required and disabled_at may not change on an account
--   that has a platform_role, or an `agronomist` / `owner` membership in any organisation,
--   unless the change is the account holder's own (app.user_id = that account: login
--   rehash, My account password change).
-- cp_admin (CLI) and the operator (superuser) are not limited. actor_kind and platform_role
-- are already outside cp_app's column grants (0011, 0012).
-- app.user_id is asserted by the app, not authenticated (ciso N-A1): this bounds the
-- owner page, it does not authenticate the actor.

set local role cp_migrator;

create function app_user_cli_only_guard() returns trigger
language plpgsql set search_path = '' as $$
declare
  v_actor uuid := public.admin_event_actor();
begin
  if new.password_hash is not distinct from old.password_hash
     and new.password_change_required is not distinct from old.password_change_required
     and new.disabled_at is not distinct from old.disabled_at then
    return new;
  end if;
  -- Operator (superuser) and CLI (cp_admin) are not limited.
  if exists (select 1 from pg_catalog.pg_roles where rolname = current_user and rolsuper)
     or pg_catalog.pg_has_role(current_user, 'cp_admin', 'member')
     or not pg_catalog.pg_has_role(current_user, 'cp_app', 'member') then
    return new;
  end if;
  if v_actor is not null and v_actor = old.id then
    return new;  -- the account holder's own change
  end if;
  if old.platform_role is not null
     or exists (select 1 from public.membership m
                 where m.user_id = old.id and m.role in ('agronomist', 'owner')) then
    raise exception 'password and disabled state of platform, agronomist and owner accounts'
      ' are changed with the CLI only'
      using errcode = '42501';
  end if;
  return new;
end
$$;

create trigger app_user_cli_only_guard
  before update of password_hash, password_change_required, disabled_at on app_user
  for each row execute function app_user_cli_only_guard();

comment on function app_user_cli_only_guard() is
  'NB1: cp_app cannot reset/disable platform, agronomist or owner accounts except their own'
  ' password; CLI (cp_admin) only. ADR 0007.';
