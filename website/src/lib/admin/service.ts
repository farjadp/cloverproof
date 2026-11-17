// Website admin auth service (ADR 0012). Framework-free: used by the Next.js server code, the
// CLI and the integration tests. Every function takes the database and the config explicitly.
// Raw tokens, passwords and TOTP secrets never reach the database or the log; only hashes,
// HMACs and envelope-encrypted secrets do.
import { randomBytes } from "node:crypto";
import type { QueryResultRow } from "pg";
import { hmac, randomToken, safeEqual, sha256 } from "./crypto.ts";
import { open, seal, type Kek } from "./envelope.ts";
import { cleanDetail } from "./log-detail.ts";
import { hashPassword, needsRehash, passwordProblem, verifyPassword, burnPasswordTime } from "./password.ts";
import { isWebsiteRole, type WebsiteRole } from "./permissions.ts";
import { newTotpSecret, verifyTotp } from "./totp.ts";

export type Db = {
  query<R extends QueryResultRow = QueryResultRow>(text: string, values?: unknown[]): Promise<{ rows: R[]; rowCount: number | null }>;
};

export type AdminConfig = {
  keks: Kek[]; // first = current KEK (seal), all = accepted for open (rotation)
  hmacKey: Buffer;
  siteUrl: string;
};

export type RequestMeta = { ipPrefix: string | null; uaFamily: string | null };

export const SESSION_IDLE_SECONDS = 30 * 60;
export const SESSION_ABSOLUTE_SECONDS = 12 * 60 * 60;
export const LINK_SECONDS = { invite: 72 * 3600, password_reset: 3600, mfa_reset: 3600 } as const;
const RATE_WINDOW_SECONDS = 15 * 60;
const MAX_FAILS_PER_ACCOUNT = 5;
const MAX_FAILS_PER_IP = 20;
const LOCK_BASE_SECONDS = 15 * 60;
const LOCK_MAX_SECONDS = 24 * 3600;
const RECOVERY_CODES = 10;

export type User = {
  id: string;
  email: string | null;
  display_name: string;
  role: WebsiteRole;
  password_hash: string | null;
  mfa_secret_enc: Buffer | null;
  mfa_enabled_at: Date | null;
  failed_logins: number;
  locked_until: Date | null;
  disabled_at: Date | null;
  deleted_at: Date | null;
};

export type Session = {
  id: string;
  user_id: string;
  created_at: Date;
  last_seen_at: Date;
  expires_at: Date;
  mfa_verified_at: Date | null;
  step_up_at: Date | null;
};

export type LogEntry = {
  actor?: string | null;
  kind: "auth" | "admin" | "content" | "secret" | "error" | "job";
  action: string;
  outcome: "ok" | "denied" | "failed";
  targetType?: string;
  targetId?: string;
  meta?: RequestMeta;
  detail?: Record<string, unknown>;
};

export async function writeLog(db: Db, entry: LogEntry): Promise<void> {
  await db.query(
    `insert into website_log (actor_user_id, kind, action, target_type, target_id, outcome, ip_prefix, ua_family, detail)
     values ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
    [
      entry.actor ?? null,
      entry.kind,
      entry.action,
      entry.targetType ?? null,
      entry.targetId ?? null,
      entry.outcome,
      entry.meta?.ipPrefix ?? null,
      entry.meta?.uaFamily ?? null,
      JSON.stringify(cleanDetail(entry.detail)),
    ],
  );
}

export function normaliseEmail(email: string): string {
  return email.trim().toLowerCase();
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export function isEmail(email: string): boolean {
  return EMAIL.test(email) && email.length <= 320;
}

const mfaAad = (userId: string) => `website_user.mfa|${userId}`;

// ---------------------------------------------------------------- one-time links

export type LinkKind = keyof typeof LINK_SECONDS;

export async function issueLink(db: Db, userId: string, kind: LinkKind, createdBy: string | null, now: Date): Promise<string> {
  const token = randomToken();
  // A new link of the same kind replaces older unused ones.
  await db.query(
    "update website_one_time_token set used_at = $3 where user_id = $1 and kind = $2 and used_at is null",
    [userId, kind, now],
  );
  await db.query(
    `insert into website_one_time_token (user_id, kind, token_hash, expires_at, created_by, created_at)
     values ($1, $2, $3, $4, $5, $6)`,
    [userId, kind, sha256(token), new Date(now.getTime() + LINK_SECONDS[kind] * 1000), createdBy, now],
  );
  return token;
}

export function linkUrl(config: AdminConfig, token: string): string {
  return `${config.siteUrl.replace(/\/$/, "")}/admin/setup#${token}`;
}

type LinkRow = { id: string; user_id: string; kind: LinkKind; email: string | null; display_name: string };

export async function peekLink(db: Db, token: string, now: Date): Promise<LinkRow | null> {
  if (!token || token.length > 100) return null;
  const { rows } = await db.query<LinkRow>(
    `select t.id, t.user_id, t.kind, u.email, u.display_name
       from website_one_time_token t join website_user u on u.id = t.user_id
      where t.token_hash = $1 and t.used_at is null and t.expires_at > $2
        and u.deleted_at is null and u.disabled_at is null`,
    [sha256(token), now],
  );
  return rows[0] ?? null;
}

/** Invite / password-reset link: set a new password. Revokes all sessions of the user. */
export async function redeemLink(
  db: Db,
  token: string,
  password: string,
  meta: RequestMeta,
  now: Date,
): Promise<{ ok: true } | { ok: false; error: string }> {
  const link = await peekLink(db, token, now);
  if (!link || link.kind === "mfa_reset") {
    await writeLog(db, { kind: "auth", action: "link.use", outcome: "denied", meta });
    return { ok: false, error: "This link is invalid or has expired. Ask an admin for a new one." };
  }
  const problem = passwordProblem(password, link.email);
  if (problem) return { ok: false, error: problem };
  const used = await db.query(
    "update website_one_time_token set used_at = $2 where id = $1 and used_at is null",
    [link.id, now],
  );
  if (used.rowCount !== 1) return { ok: false, error: "This link was already used." };
  await db.query(
    `update website_user set password_hash = $2, password_changed_at = $3, failed_logins = 0, locked_until = null
      where id = $1`,
    [link.user_id, await hashPassword(password), now],
  );
  await revokeAllSessions(db, link.user_id, now);
  await writeLog(db, { actor: link.user_id, kind: "auth", action: `link.${link.kind}`, outcome: "ok", meta });
  return { ok: true };
}

// ---------------------------------------------------------------- rate limits

async function bump(db: Db, key: Buffer, now: Date): Promise<number> {
  const windowStart = new Date(Math.floor(now.getTime() / (RATE_WINDOW_SECONDS * 1000)) * RATE_WINDOW_SECONDS * 1000);
  const { rows } = await db.query<{ count: number }>(
    `insert into website_rate_limit (key_hash, window_start, count) values ($1, $2, 1)
     on conflict (key_hash, window_start) do update set count = website_rate_limit.count + 1
     returning count`,
    [key, windowStart],
  );
  return rows[0].count;
}

async function unbump(db: Db, key: Buffer, now: Date): Promise<void> {
  const windowStart = new Date(Math.floor(now.getTime() / (RATE_WINDOW_SECONDS * 1000)) * RATE_WINDOW_SECONDS * 1000);
  await db.query(
    "update website_rate_limit set count = greatest(count - 1, 0) where key_hash = $1 and window_start = $2",
    [key, windowStart],
  );
}

const emailKey = (config: AdminConfig, email: string) => hmac(config.hmacKey, `login-email|${email}`);
const ipKey = (config: AdminConfig, prefix: string) => hmac(config.hmacKey, `login-ip|${prefix}`);

// ---------------------------------------------------------------- sessions

export async function createSession(db: Db, userId: string, meta: RequestMeta, now: Date, mfaVerified: boolean): Promise<string> {
  const token = randomToken();
  await db.query(
    `insert into website_session (user_id, token_hash, csrf_token_hash, created_at, last_seen_at, expires_at, mfa_verified_at, ip_prefix, ua_family)
     values ($1, $2, $3, $4, $4, $5, $6, $7, $8)`,
    [
      userId,
      sha256(token),
      sha256(`csrf|${token}`),
      now,
      new Date(now.getTime() + SESSION_ABSOLUTE_SECONDS * 1000),
      mfaVerified ? now : null,
      meta.ipPrefix,
      meta.uaFamily,
    ],
  );
  return token;
}

export async function revokeAllSessions(db: Db, userId: string, now: Date): Promise<void> {
  await db.query("update website_session set revoked_at = $2 where user_id = $1 and revoked_at is null", [userId, now]);
}

export type Current = { session: Session; user: User };

/** Valid session + active user, or null. Slides the idle timeout (at most once a minute). */
export async function loadSession(db: Db, token: string | undefined, now: Date): Promise<Current | null> {
  if (!token || token.length > 100) return null;
  const { rows } = await db.query<Session & { u: User }>(
    `select s.id, s.user_id, s.created_at, s.last_seen_at, s.expires_at, s.mfa_verified_at, s.step_up_at,
            to_jsonb(u) - 'password_hash' - 'mfa_secret_enc' as u
       from website_session s join website_user u on u.id = s.user_id
      where s.token_hash = $1 and s.revoked_at is null`,
    [sha256(token)],
  );
  const row = rows[0];
  if (!row) return null;
  const user = { ...row.u, password_hash: null, mfa_secret_enc: null } as User;
  const idle = now.getTime() - new Date(row.last_seen_at).getTime() > SESSION_IDLE_SECONDS * 1000;
  if (idle || new Date(row.expires_at) <= now || user.disabled_at || user.deleted_at || !isWebsiteRole(user.role)) {
    await db.query("update website_session set revoked_at = $2 where id = $1 and revoked_at is null", [row.id, now]);
    return null;
  }
  if (now.getTime() - new Date(row.last_seen_at).getTime() > 60_000) {
    await db.query("update website_session set last_seen_at = $2 where id = $1", [row.id, now]);
  }
  const session: Session = {
    id: row.id,
    user_id: row.user_id,
    created_at: row.created_at,
    last_seen_at: row.last_seen_at,
    expires_at: row.expires_at,
    mfa_verified_at: row.mfa_verified_at,
    step_up_at: row.step_up_at,
  };
  return { session, user };
}

/** New token for the same session (after MFA): old cookie stops working (no fixation). */
async function rotate(db: Db, sessionId: string): Promise<string> {
  const token = randomToken();
  await db.query("update website_session set token_hash = $2, csrf_token_hash = $3 where id = $1", [
    sessionId,
    sha256(token),
    sha256(`csrf|${token}`),
  ]);
  return token;
}

export async function logout(db: Db, current: Current, meta: RequestMeta, now: Date, viaForm = true): Promise<void> {
  await db.query("update website_session set revoked_at = $2 where id = $1", [current.session.id, now]);
  await writeLog(db, { actor: current.user.id, kind: "auth", action: "logout", outcome: "ok", meta, detail: viaForm ? undefined : { via: "no_csrf" } });
}

// ---------------------------------------------------------------- CSRF

export function csrfToken(config: AdminConfig, sessionToken: string): string {
  return hmac(config.hmacKey, `csrf|${sessionToken}`).toString("base64url");
}

export function csrfValid(config: AdminConfig, sessionToken: string | undefined, submitted: unknown): boolean {
  if (!sessionToken || typeof submitted !== "string") return false;
  return safeEqual(csrfToken(config, sessionToken), submitted);
}

// ---------------------------------------------------------------- login

export const LOGIN_FAILED = "E-mail or password is wrong, or the account is locked. Try again later.";

export async function login(
  db: Db,
  config: AdminConfig,
  input: { email: string; password: string },
  meta: RequestMeta,
  now: Date,
): Promise<{ ok: true; token: string } | { ok: false; error: string }> {
  const email = normaliseEmail(input.email);
  const fail = async (reason: string, actor: string | null = null) => {
    await writeLog(db, { actor, kind: "auth", action: "login", outcome: "failed", meta, detail: { reason } });
    return { ok: false as const, error: LOGIN_FAILED };
  };
  if (!isEmail(email) || input.password.length > 128) {
    await burnPasswordTime(input.password);
    return fail("invalid_input");
  }
  // Count the attempt first (atomic), then decide: parallel requests can't all slip under the limit.
  const eKey = emailKey(config, email);
  const iKey = meta.ipPrefix ? ipKey(config, meta.ipPrefix) : null;
  const perEmail = await bump(db, eKey, now);
  const perIp = iKey ? await bump(db, iKey, now) : 0;
  if (perEmail > MAX_FAILS_PER_ACCOUNT || perIp > MAX_FAILS_PER_IP) {
    await burnPasswordTime(input.password);
    return fail("rate_limited");
  }
  const { rows } = await db.query<User>("select * from website_user where email = $1 and deleted_at is null", [email]);
  const user = rows[0];
  if (!user || !user.password_hash) {
    await burnPasswordTime(input.password);
    return fail("unknown_or_unset");
  }
  const valid = await verifyPassword(user.password_hash, input.password);
  // A-S1: a wrong password only counts toward the per-e-mail throttle above (5 per 15-min window).
  // It never locks the account, so someone who knows an admin's e-mail can't keep them out for days.
  if (!valid) return fail("bad_credentials", user.id);
  if (isLocked(user, now) || user.disabled_at) return fail(user.disabled_at ? "disabled" : "locked", user.id);
  // A successful password doesn't use up the rate-limit budget. Failure counters reset only
  // after the second factor succeeds, so password + guessed codes can't reset them.
  await unbump(db, eKey, now);
  if (iKey) await unbump(db, iKey, now);
  if (needsRehash(user.password_hash)) {
    await db.query("update website_user set password_hash = $2 where id = $1", [user.id, await hashPassword(input.password)]);
  }
  const token = await createSession(db, user.id, meta, now, false);
  await writeLog(db, { actor: user.id, kind: "auth", action: "login.password", outcome: "ok", meta });
  return { ok: true, token };
}

function isLocked(user: Pick<User, "locked_until">, now: Date): boolean {
  return Boolean(user.locked_until && new Date(user.locked_until) > now);
}

/**
 * One failed TOTP or recovery code for this account (atomic; second factor only — wrong passwords
 * are throttled per e-mail instead, A-S1). From the 5th failure the account locks for 15 min,
 * doubling up to 24 h, and every session ends. Only someone who knows the password gets here.
 */
async function recordFailure(db: Db, userId: string, meta: RequestMeta, now: Date): Promise<boolean> {
  const { rows } = await db.query<{ failed_logins: number; locked: boolean }>(
    `update website_user
        set failed_logins = failed_logins + 1,
            locked_until = case when failed_logins + 1 >= $3
              then $2::timestamptz + make_interval(secs => least($4 * power(2, failed_logins + 1 - $3), $5))
              else locked_until end
      where id = $1
      returning failed_logins, failed_logins >= $3 as locked`,
    [userId, now, MAX_FAILS_PER_ACCOUNT, LOCK_BASE_SECONDS, LOCK_MAX_SECONDS],
  );
  const locked = Boolean(rows[0]?.locked);
  if (locked) {
    await revokeAllSessions(db, userId, now);
    await writeLog(db, { actor: userId, kind: "auth", action: "account.lock", outcome: "ok", meta, detail: { count: rows[0].failed_logins } });
  }
  return locked;
}

async function clearFailures(db: Db, userId: string): Promise<void> {
  await db.query("update website_user set failed_logins = 0, locked_until = null where id = $1", [userId]);
}

// ---------------------------------------------------------------- MFA

async function userWithSecrets(db: Db, userId: string): Promise<User> {
  const { rows } = await db.query<User>("select * from website_user where id = $1", [userId]);
  return rows[0];
}

/** Secret for the enrolment screen. Kept sealed on the user row until the first code is verified. */
export async function pendingMfaSecret(db: Db, config: AdminConfig, current: Current): Promise<string> {
  const before = await userWithSecrets(db, current.user.id);
  if (before.mfa_enabled_at) throw new Error("MFA is already enrolled");
  if (!before.mfa_secret_enc) {
    // Only the first of two parallel page loads stores a secret; both then show that one.
    await db.query(
      "update website_user set mfa_secret_enc = $2 where id = $1 and mfa_enabled_at is null and mfa_secret_enc is null",
      [before.id, seal(newTotpSecret(), mfaAad(before.id), config.keks[0])],
    );
  }
  const user = await userWithSecrets(db, current.user.id);
  return open(user.mfa_secret_enc as Buffer, mfaAad(user.id), config.keks);
}

/** Marks a TOTP step as used for this user (replay protection, purged after 1 day). */
async function claimStep(db: Db, config: AdminConfig, userId: string, step: number): Promise<boolean> {
  // window_start = the step's own start time, so the same step always hits the same row.
  const { rowCount } = await db.query(
    "insert into website_rate_limit (key_hash, window_start, count) values ($1, $2, 1) on conflict do nothing",
    [hmac(config.hmacKey, `totp-used|${userId}|${step}`), new Date(step * 30_000)],
  );
  return rowCount === 1;
}

async function checkCode(db: Db, config: AdminConfig, user: User, code: string, now: Date): Promise<boolean> {
  if (!user.mfa_secret_enc) return false;
  const secret = open(user.mfa_secret_enc, mfaAad(user.id), config.keks);
  const step = verifyTotp(secret, code.replace(/\s/g, ""), Math.floor(now.getTime() / 1000));
  return step !== null && (await claimStep(db, config, user.id, step));
}

// No look-alike characters (0/O, 1/I/L) so codes can be typed from paper.
const RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";

function newRecoveryCodes(): string[] {
  return Array.from({ length: RECOVERY_CODES }, () => {
    const bytes = randomBytes(10);
    const raw = Array.from(bytes, (b) => RECOVERY_ALPHABET[b % RECOVERY_ALPHABET.length]).join("");
    return `${raw.slice(0, 5)}-${raw.slice(5)}`;
  });
}

const recoveryHash = (config: AdminConfig, code: string) =>
  hmac(config.hmacKey, `recovery|${code.replace(/[\s-]/g, "").toUpperCase()}`);

export type MfaResult = { ok: true; token: string; recoveryCodes?: string[] } | { ok: false; error: string };

const TOO_MANY = "Too many wrong codes. The account is locked for a while; sign in again later.";

/** Locked accounts can't pass a second factor; their sessions end. */
async function refuseIfLocked(db: Db, user: User, meta: RequestMeta, now: Date): Promise<boolean> {
  if (!isLocked(user, now) && !user.disabled_at) return false;
  await revokeAllSessions(db, user.id, now);
  await writeLog(db, { actor: user.id, kind: "auth", action: "mfa", outcome: "denied", meta, detail: { reason: "locked" } });
  return true;
}

/** Enrol (first code) or verify (later logins). On success the session is MFA-verified and rotated. */
export async function completeMfa(
  db: Db,
  config: AdminConfig,
  current: Current,
  code: string,
  meta: RequestMeta,
  now: Date,
): Promise<MfaResult> {
  const user = await userWithSecrets(db, current.user.id);
  const enrolling = !user.mfa_enabled_at;
  if (await refuseIfLocked(db, user, meta, now)) return { ok: false, error: TOO_MANY };
  if (!(await checkCode(db, config, user, code, now))) {
    const locked = await recordFailure(db, user.id, meta, now);
    await writeLog(db, { actor: user.id, kind: "auth", action: enrolling ? "mfa.enrol" : "mfa", outcome: "failed", meta });
    return { ok: false, error: locked ? TOO_MANY : "That code is not valid. Check the time on your phone and try the newest code." };
  }
  let recoveryCodes: string[] | undefined;
  if (enrolling) {
    recoveryCodes = newRecoveryCodes();
    await db.query("update website_user set mfa_enabled_at = $2 where id = $1", [user.id, now]);
    await db.query("delete from website_user_recovery_code where user_id = $1", [user.id]);
    for (const c of recoveryCodes) {
      await db.query("insert into website_user_recovery_code (user_id, code_hash) values ($1, $2)", [user.id, recoveryHash(config, c)]);
    }
  }
  await clearFailures(db, user.id);
  // Signing in does not count as a step-up: sensitive pages still ask for a fresh code.
  await db.query("update website_session set mfa_verified_at = $2 where id = $1", [current.session.id, now]);
  const token = await rotate(db, current.session.id);
  await writeLog(db, { actor: user.id, kind: "auth", action: enrolling ? "mfa.enrol" : "mfa", outcome: "ok", meta });
  return { ok: true, token, recoveryCodes };
}

/** Sign in with a recovery code instead of TOTP (code is used up). */
export async function redeemRecoveryCode(
  db: Db,
  config: AdminConfig,
  current: Current,
  code: string,
  meta: RequestMeta,
  now: Date,
): Promise<MfaResult> {
  const user = await userWithSecrets(db, current.user.id);
  if (!user.mfa_enabled_at) return { ok: false, error: "Set up the authenticator app first." };
  if (await refuseIfLocked(db, user, meta, now)) return { ok: false, error: TOO_MANY };
  const { rowCount } = await db.query(
    "update website_user_recovery_code set used_at = $3 where user_id = $1 and code_hash = $2 and used_at is null",
    [user.id, recoveryHash(config, code), now],
  );
  if (rowCount !== 1) {
    const locked = await recordFailure(db, user.id, meta, now);
    await writeLog(db, { actor: user.id, kind: "auth", action: "mfa.recovery", outcome: "failed", meta });
    return { ok: false, error: locked ? TOO_MANY : "That recovery code is not valid or was already used." };
  }
  await clearFailures(db, user.id);
  await db.query("update website_session set mfa_verified_at = $2 where id = $1", [current.session.id, now]);
  const token = await rotate(db, current.session.id);
  await writeLog(db, { actor: user.id, kind: "auth", action: "mfa.recovery", outcome: "ok", meta });
  return { ok: true, token };
}

/** Fresh TOTP for sensitive actions (users, keys, log export). Failures count toward the lock. */
export async function stepUp(
  db: Db,
  config: AdminConfig,
  current: Current,
  code: string,
  meta: RequestMeta,
  now: Date,
): Promise<boolean> {
  const user = await userWithSecrets(db, current.user.id);
  if (!user.mfa_enabled_at || (await refuseIfLocked(db, user, meta, now))) return false;
  const ok = await checkCode(db, config, user, code, now);
  if (ok) {
    await clearFailures(db, user.id);
    await db.query("update website_session set step_up_at = $2 where id = $1", [current.session.id, now]);
  } else {
    await recordFailure(db, user.id, meta, now);
  }
  await writeLog(db, { actor: user.id, kind: "auth", action: "mfa.step_up", outcome: ok ? "ok" : "failed", meta });
  return ok;
}

// ---------------------------------------------------------------- CLI: first admin

export async function createFirstAdmin(
  db: Db,
  config: AdminConfig,
  input: { email: string; name: string; additional?: boolean },
  now: Date,
): Promise<{ userId: string; link: string }> {
  const email = normaliseEmail(input.email);
  if (!isEmail(email)) throw new Error("invalid e-mail address");
  const name = input.name.trim();
  if (!name || name.length > 120) throw new Error("name must be 1–120 characters");
  const { rows: admins } = await db.query<{ n: number }>(
    "select count(*)::int as n from website_user where role = 'admin' and deleted_at is null",
  );
  if (admins[0].n > 0 && !input.additional) {
    throw new Error("an admin already exists; invite users from /admin/users or pass --additional");
  }
  const { rows } = await db.query<{ id: string }>(
    "insert into website_user (email, display_name, role) values ($1, $2, 'admin') returning id",
    [email, name],
  );
  const userId = rows[0].id;
  const token = await issueLink(db, userId, "invite", null, now);
  await writeLog(db, { kind: "admin", action: "user.create_cli", outcome: "ok", targetType: "website_user", targetId: userId, detail: { role: "admin", via: "cli" } });
  return { userId, link: linkUrl(config, token) };
}

