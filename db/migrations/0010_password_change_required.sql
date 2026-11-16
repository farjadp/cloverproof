-- Admin-driven password recovery (ADR 0005 A1, no email sending).
-- Temporary passwords set by an owner (web) or by `user-create --reset-password` (CLI) set
-- this flag; while it is true the app only allows /account/password and /logout. The app
-- clears it when the user chooses their own password.
set local role cp_migrator;

alter table app_user
  add column password_change_required boolean not null default false;

comment on column app_user.password_change_required is
  'True after an admin-set temporary password; the user must choose a new password before using the app.';
