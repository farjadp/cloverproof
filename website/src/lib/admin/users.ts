// Website staff management (ADR 0012): invite, role, disable/enable, password/MFA reset, delete.
// Every change is logged. Delete = pseudonymise (the database refuses hard deletes and undeletes).
import { isEmail, issueLink, linkUrl, normaliseEmail, revokeAllSessions, writeLog, type AdminConfig, type Current, type Db, type RequestMeta } from "./service.ts";
import { isWebsiteRole, type WebsiteRole } from "./permissions.ts";

export type UserRow = {
  id: string;
  email: string | null;
  display_name: string;
  role: WebsiteRole;
  status: "invited" | "active" | "locked" | "disabled";
  mfa: boolean;
  last_sign_in: Date | null;
  created_at: Date;
};

export async function listUsers(db: Db, now: Date): Promise<UserRow[]> {
  const { rows } = await db.query<UserRow & { password_set: boolean; disabled: boolean; locked: boolean }>(
    `select u.id, u.email, u.display_name, u.role, u.mfa_enabled_at is not null as mfa, u.created_at,
            u.password_hash is not null as password_set, u.disabled_at is not null as disabled,
            coalesce(u.locked_until > $1, false) as locked,
            (select max(s.mfa_verified_at) from website_session s where s.user_id = u.id) as last_sign_in
       from website_user u
      where u.deleted_at is null
      order by u.disabled_at is not null, u.role, lower(u.display_name)`,
    [now],
  );
  return rows.map((r) => ({
    id: r.id,
    email: r.email,
    display_name: r.display_name,
    role: r.role,
    mfa: r.mfa,
    last_sign_in: r.last_sign_in,
    created_at: r.created_at,
    status: r.disabled ? "disabled" : !r.password_set ? "invited" : r.locked ? "locked" : "active",
  }));
}

// An admin can't take over another admin's account through a reset link: that would make the
// target's later actions unattributable. Admin resets go through the operator CLI (runbook §4).
const ADMIN_RESET = "Admins can't reset another admin's sign-in here. Use the operator reset (runbook §4).";

export type Result = { ok: true; message: string; link?: string } | { ok: false; error: string };

type Target = { id: string; email: string | null; role: WebsiteRole; disabled_at: Date | null };

async function target(db: Db, id: string): Promise<Target | null> {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return null;
  const { rows } = await db.query<Target>(
    "select id, email, role, disabled_at from website_user where id = $1 and deleted_at is null",
    [id],
  );
  return rows[0] ?? null;
}

/** Postgres check_violation from the last-admin guard → readable message. */
function lastAdmin(error: unknown): Result | null {
  const code = (error as { code?: string })?.code;
  return code === "23514" ? { ok: false, error: "There must always be at least one active admin." } : null;
}

export async function inviteUser(
  db: Db,
  config: AdminConfig,
  actor: Current,
  input: { email: string; name: string; role: string },
  meta: RequestMeta,
  now: Date,
): Promise<Result> {
  const email = normaliseEmail(input.email);
  const name = input.name.trim();
  if (!isEmail(email)) return { ok: false, error: "Enter a valid e-mail address." };
  if (!name || name.length > 120) return { ok: false, error: "Enter a name (up to 120 characters)." };
  if (!isWebsiteRole(input.role)) return { ok: false, error: "Choose a role." };
  const { rows: existing } = await db.query("select 1 from website_user where email = $1", [email]);
  if (existing.length) return { ok: false, error: "A user with this e-mail already exists." };
  const { rows } = await db.query<{ id: string }>(
    "insert into website_user (email, display_name, role, created_by) values ($1, $2, $3, $4) returning id",
    [email, name, input.role, actor.user.id],
  );
  const token = await issueLink(db, rows[0].id, "invite", actor.user.id, now);
  await writeLog(db, { actor: actor.user.id, kind: "admin", action: "user.invite", outcome: "ok", targetType: "website_user", targetId: rows[0].id, meta, detail: { role: input.role } });
  return { ok: true, message: `Invited ${name}. Send them this link (valid 72 hours, works once).`, link: linkUrl(config, token) };
}

export async function changeRole(db: Db, actor: Current, id: string, role: string, meta: RequestMeta): Promise<Result> {
  const user = await target(db, id);
  if (!user) return { ok: false, error: "User not found." };
  if (!isWebsiteRole(role)) return { ok: false, error: "Choose a role." };
  if (role === user.role) return { ok: true, message: "No change." };
  try {
    await db.query("update website_user set role = $2 where id = $1", [id, role]);
  } catch (error) {
    const r = lastAdmin(error);
    if (r) return r;
    throw error;
  }
  // A changed role takes effect on the next request; sessions stay (permissions are checked per request).
  await writeLog(db, { actor: actor.user.id, kind: "admin", action: "user.role", outcome: "ok", targetType: "website_user", targetId: id, meta, detail: { from_role: user.role, to_role: role } });
  return { ok: true, message: `Role changed to ${role}.` };
}

export async function setDisabled(db: Db, actor: Current, id: string, disabled: boolean, meta: RequestMeta, now: Date): Promise<Result> {
  const user = await target(db, id);
  if (!user) return { ok: false, error: "User not found." };
  if (id === actor.user.id && disabled) return { ok: false, error: "You can't disable your own account." };
  try {
    await db.query("update website_user set disabled_at = $2 where id = $1", [id, disabled ? now : null]);
  } catch (error) {
    const r = lastAdmin(error);
    if (r) return r;
    throw error;
  }
  if (disabled) {
    await revokeAllSessions(db, id, now);
    // Pending invite/reset links die too, so re-enabling never revives a leaked link.
    await db.query("update website_one_time_token set used_at = $2 where user_id = $1 and used_at is null", [id, now]);
  }
  await writeLog(db, { actor: actor.user.id, kind: "admin", action: disabled ? "user.disable" : "user.enable", outcome: "ok", targetType: "website_user", targetId: id, meta });
  return { ok: true, message: disabled ? "Account disabled and signed out everywhere." : "Account enabled." };
}

export async function resetPassword(db: Db, config: AdminConfig, actor: Current, id: string, meta: RequestMeta, now: Date): Promise<Result> {
  const user = await target(db, id);
  if (!user) return { ok: false, error: "User not found." };
  if (user.disabled_at) return { ok: false, error: "Enable the account first." };
  if (user.role === "admin" && id !== actor.user.id) return { ok: false, error: ADMIN_RESET };
  const token = await issueLink(db, id, "password_reset", actor.user.id, now);
  await writeLog(db, { actor: actor.user.id, kind: "admin", action: "user.reset_link", outcome: "ok", targetType: "website_user", targetId: id, meta });
  return { ok: true, message: "Send this link to the user (valid 1 hour, works once). Their current password keeps working until they use it.", link: linkUrl(config, token) };
}

/** Clears two-step sign-in; the user sets it up again at the next sign-in. Signs them out. */
export async function resetMfa(db: Db, actor: Current, id: string, meta: RequestMeta, now: Date): Promise<Result> {
  const user = await target(db, id);
  if (!user) return { ok: false, error: "User not found." };
  if (id === actor.user.id) return { ok: false, error: "Ask the operator to reset your own two-step sign-in (runbook)." };
  if (user.role === "admin") return { ok: false, error: ADMIN_RESET };
  await db.query("update website_user set mfa_secret_enc = null, mfa_enabled_at = null where id = $1", [id]);
  await db.query("delete from website_user_recovery_code where user_id = $1", [id]);
  await revokeAllSessions(db, id, now);
  await writeLog(db, { actor: actor.user.id, kind: "admin", action: "user.reset_mfa", outcome: "ok", targetType: "website_user", targetId: id, meta });
  return { ok: true, message: "Two-step sign-in reset. The user sets it up again at the next sign-in." };
}

/** Delete = pseudonymise: e-mail, password, MFA and recovery codes removed; name kept for history. */
export async function deleteUser(db: Db, actor: Current, id: string, confirmEmail: string, meta: RequestMeta, now: Date): Promise<Result> {
  const user = await target(db, id);
  if (!user) return { ok: false, error: "User not found." };
  if (id === actor.user.id) return { ok: false, error: "You can't delete your own account." };
  if (!user.email || normaliseEmail(confirmEmail) !== user.email) {
    return { ok: false, error: "Type the user's e-mail address to confirm." };
  }
  try {
    await db.query(
      `update website_user set email = null, password_hash = null, mfa_secret_enc = null, mfa_enabled_at = null,
              disabled_at = coalesce(disabled_at, $2), deleted_at = $2 where id = $1`,
      [id, now],
    );
  } catch (error) {
    const r = lastAdmin(error);
    if (r) return r;
    throw error;
  }
  await db.query("delete from website_user_recovery_code where user_id = $1", [id]);
  await db.query("update website_one_time_token set used_at = $2 where user_id = $1 and used_at is null", [id, now]);
  await revokeAllSessions(db, id, now);
  await writeLog(db, { actor: actor.user.id, kind: "admin", action: "user.delete", outcome: "ok", targetType: "website_user", targetId: id, meta, detail: { role: user.role } });
  return { ok: true, message: "User deleted. Their name stays in the history; e-mail and sign-in data are removed." };
}
