// Website admin auth service against a real, migrated Postgres (migration 0024).
// Opt-in: WEBSITE_TEST_DATABASE_URL = superuser URL of a disposable, migrated database.
// Each test runs in a transaction as cp_website_admin and is rolled back.
import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import pg from "pg";
import { totpAt } from "../src/lib/admin/totp.ts";
import { open } from "../src/lib/admin/envelope.ts";
import { hasFullAccess, isPasswordOnly } from "../src/lib/admin/mfa-policy.ts";
import { listUsers } from "../src/lib/admin/users.ts";
import {
  completeMfa,
  createFirstAdmin,
  csrfToken,
  csrfValid,
  issueLink,
  loadSession,
  login,
  LOGIN_FAILED,
  pendingMfaSecret,
  redeemLink,
  stepUp,
  type AdminConfig,
  type Current,
} from "../src/lib/admin/service.ts";

const url = process.env.WEBSITE_TEST_DATABASE_URL;
const skip = url ? false : "WEBSITE_TEST_DATABASE_URL not set (DB tests are opt-in)";
const config: AdminConfig = {
  keks: [{ id: "t1", key: randomBytes(32) }],
  hmacKey: randomBytes(32),
  siteUrl: "https://example.test",
};
const meta = { ipPrefix: "203.0.113.0/24", uaFamily: "Firefox" };
const PASSWORD = "green pasture morning rain";
const T0 = new Date("2026-11-17T12:00:00Z");
const at = (seconds: number) => new Date(T0.getTime() + seconds * 1000);

async function withDb(fn: (db: pg.Client) => Promise<void>): Promise<void> {
  const db = new pg.Client({ connectionString: url });
  await db.connect();
  try {
    await db.query("begin");
    await db.query("set local role cp_website_admin");
    await fn(db);
  } finally {
    await db.query("rollback").catch(() => {});
    await db.end();
  }
}

/** Admin with a password; returns the session token after the password step. */
async function adminWithPassword(db: pg.Client, email = "a@example.com"): Promise<string> {
  const { link } = await createFirstAdmin(db, config, { email, name: "A", additional: true }, T0);
  const result = await redeemLink(db, link.split("#")[1], PASSWORD, meta, T0);
  assert.deepEqual(result, { ok: true });
  const signedIn = await login(db, config, { email, password: PASSWORD }, meta, at(1));
  assert.equal(signedIn.ok, true);
  return (signedIn as { token: string }).token;
}

async function session(db: pg.Client, token: string, when: Date): Promise<Current> {
  const current = await loadSession(db, token, when);
  assert.ok(current);
  return current;
}

async function enrolled(db: pg.Client): Promise<{ token: string; secret: string }> {
  const token = await adminWithPassword(db);
  const secret = await pendingMfaSecret(db, config, await session(db, token, at(2)));
  const result = await completeMfa(db, config, await session(db, token, at(2)), totpAt(secret, at(2).getTime() / 1000), meta, at(2));
  assert.equal(result.ok, true);
  return { token: (result as { token: string }).token, secret };
}

test("first admin via CLI: one-time link in the URL fragment, second admin refused without --additional", { skip }, () =>
  withDb(async (db) => {
    const { link } = await createFirstAdmin(db, config, { email: " First@Example.com ", name: "First" }, T0);
    assert.match(link, /^https:\/\/example\.test\/admin\/setup#[A-Za-z0-9_-]{43}$/);
    const { rows } = await db.query("select email, role, password_hash from website_user");
    assert.deepEqual(rows, [{ email: "first@example.com", role: "admin", password_hash: null }]);
    await assert.rejects(createFirstAdmin(db, config, { email: "b@example.com", name: "B" }, T0), /already exists/);
  }));

test("links: single use, expire, wrong kind refused", { skip }, () =>
  withDb(async (db) => {
    const { link, userId } = await createFirstAdmin(db, config, { email: "l@example.com", name: "L" }, T0);
    const token = link.split("#")[1];
    assert.equal((await redeemLink(db, token, "short", meta, T0)).ok, false);
    assert.equal((await redeemLink(db, token, PASSWORD, meta, at(73 * 3600))).ok, false, "expired");
    assert.deepEqual(await redeemLink(db, token, PASSWORD, meta, at(10)), { ok: true });
    assert.equal((await redeemLink(db, token, PASSWORD, meta, at(11))).ok, false, "used");
    const mfaReset = await issueLink(db, userId, "mfa_reset", userId, at(20));
    assert.equal((await redeemLink(db, mfaReset, PASSWORD, meta, at(21))).ok, false, "mfa_reset can't set a password");
  }));

test("login: same error for unknown user and wrong password; 5 wrong passwords throttle the e-mail for the window only", { skip }, () =>
  withDb(async (db) => {
    await adminWithPassword(db);
    const unknown = await login(db, config, { email: "nobody@example.com", password: PASSWORD }, meta, at(5));
    assert.deepEqual(unknown, { ok: false, error: LOGIN_FAILED });
    for (let i = 0; i < 5; i++) {
      const wrong = await login(db, config, { email: "a@example.com", password: "wrong password!!" }, { ...meta, ipPrefix: null }, at(10 + i));
      assert.deepEqual(wrong, { ok: false, error: LOGIN_FAILED });
    }
    // A-S1: wrong passwords never lock the account itself.
    const { rows } = await db.query("select failed_logins, locked_until from website_user");
    assert.deepEqual(rows[0], { failed_logins: 0, locked_until: null });
    const right = await login(db, config, { email: "a@example.com", password: PASSWORD }, { ...meta, ipPrefix: null }, at(20));
    assert.deepEqual(right, { ok: false, error: LOGIN_FAILED }, "throttled for the rest of the window, even with the right password");
    const later = await login(db, config, { email: "a@example.com", password: PASSWORD }, { ...meta, ipPrefix: null }, at(15 * 60));
    assert.equal(later.ok, true, "the next window is open again");
  }));

test("login: an attacker repeating wrong passwords for days can't extend a lock (A-S1)", { skip }, () =>
  withDb(async (db) => {
    await enrolled(db);
    for (let day = 0; day < 3; day++) {
      for (let i = 0; i < 6; i++) {
        await login(db, config, { email: "a@example.com", password: "wrong password!!" }, { ...meta, ipPrefix: null }, at(day * 86400 + 100 + i));
      }
    }
    const { rows } = await db.query("select failed_logins, locked_until from website_user");
    assert.deepEqual(rows[0], { failed_logins: 0, locked_until: null }, "no account lock, no doubling");
    const { rows: revoked } = await db.query("select count(*)::int as n from website_session where revoked_at is not null");
    assert.equal(revoked[0].n, 0, "wrong passwords don't end the admin's sessions");
    const next = await login(db, config, { email: "a@example.com", password: PASSWORD }, { ...meta, ipPrefix: null }, at(2 * 86400 + 100 + 15 * 60));
    assert.equal(next.ok, true, "right password works as soon as the throttle window ends");
    const { rows: log } = await db.query("select count(*)::int as n from website_log where action = 'account.lock'");
    assert.equal(log[0].n, 0, "no account.lock from passwords");
  }));

test("login: 20 failures from one IP prefix block that prefix", { skip }, () =>
  withDb(async (db) => {
    await adminWithPassword(db);
    for (let i = 0; i < 20; i++) {
      await login(db, config, { email: `x${i}@example.com`, password: "whatever123456" }, meta, at(10));
    }
    const blocked = await login(db, config, { email: "a@example.com", password: PASSWORD }, meta, at(11));
    assert.equal(blocked.ok, false);
    const otherIp = await login(db, config, { email: "a@example.com", password: PASSWORD }, { ...meta, ipPrefix: "198.51.100.0/24" }, at(11));
    assert.equal(otherIp.ok, true);
  }));

test("login: without a trusted IP header (no prefix) the per-IP limit is off and no IP is logged (A-S2)", { skip }, () =>
  withDb(async (db) => {
    await adminWithPassword(db);
    const noIp = { ...meta, ipPrefix: null };
    for (let i = 0; i < 25; i++) {
      await login(db, config, { email: `x${i}@example.com`, password: "whatever123456" }, noIp, at(10));
    }
    const signedIn = await login(db, config, { email: "a@example.com", password: PASSWORD }, noIp, at(11));
    assert.equal(signedIn.ok, true, "25 failures with no IP don't block everyone");
    const { rows } = await db.query(
      "select count(*) filter (where ip_prefix is null)::int as without, count(*) filter (where ip_prefix is not null)::int as with from website_log where action = 'login' and outcome = 'failed'",
    );
    assert.deepEqual(rows[0], { without: 25, with: 0 });
  }));

test("sessions: idle 30 min and absolute 12 h; disabled user loses the session", { skip }, () =>
  withDb(async (db) => {
    const token = await adminWithPassword(db);
    assert.ok(await loadSession(db, token, at(29 * 60)));
    assert.equal(await loadSession(db, token, at(29 * 60 + 31 * 60)), null, "idle");
    const t2 = (await login(db, config, { email: "a@example.com", password: PASSWORD }, meta, at(7200))) as { token: string };
    for (let s = 7200 + 1500; s < 7200 + 12 * 3600; s += 1500) assert.ok(await loadSession(db, t2.token, at(s)), String(s));
    assert.equal(await loadSession(db, t2.token, at(7200 + 12 * 3600 + 1)), null, "absolute");
    const t3 = (await login(db, config, { email: "a@example.com", password: PASSWORD }, meta, at(90000))) as { token: string };
    await db.query("insert into website_user (email, display_name, role) values ('b@example.com', 'B', 'admin')");
    await db.query("update website_user set disabled_at = now() where email = 'a@example.com'");
    assert.equal(await loadSession(db, t3.token, at(90001)), null, "disabled");
    assert.equal(await loadSession(db, undefined, at(1)), null);
    assert.equal(await loadSession(db, "x".repeat(500), at(1)), null);
  }));

test("MFA: secret sealed at rest, enrol rotates the session token, codes can't be replayed", { skip }, () =>
  withDb(async (db) => {
    const passwordToken = await adminWithPassword(db);
    const current = await session(db, passwordToken, at(2));
    const secret = await pendingMfaSecret(db, config, current);
    const { rows } = await db.query("select id, mfa_secret_enc from website_user");
    assert.ok(!rows[0].mfa_secret_enc.toString("utf8").includes(secret), "not stored in clear");
    assert.equal(open(rows[0].mfa_secret_enc, `website_user.mfa|${rows[0].id}`, config.keks), secret);
    const code = totpAt(secret, at(2).getTime() / 1000);
    const result = await completeMfa(db, config, current, code, meta, at(2));
    assert.equal(result.ok, true);
    if (!result.ok) return;
    assert.equal(result.recoveryCodes?.length, 10);
    assert.equal(await loadSession(db, passwordToken, at(3)), null, "old token no longer works");
    const verified = await session(db, result.token, at(3));
    assert.ok(verified.session.mfa_verified_at);
    assert.equal(await stepUp(db, config, verified, code, meta, at(3)), false, "same code twice is refused");
    const next = totpAt(secret, at(40).getTime() / 1000);
    assert.equal(await stepUp(db, config, verified, next, meta, at(40)), true);
    const { rows: codes } = await db.query("select count(*)::int as n from website_user_recovery_code");
    assert.equal(codes[0].n, 10);
  }));

test("MFA: wrong codes count per user across sessions, lock the account and end every session", { skip }, () =>
  withDb(async (db) => {
    const { token } = await enrolled(db);
    // Five fresh password sessions, one wrong code each (a new session must not reset the count).
    for (let i = 0; i < 5; i++) {
      const fresh = (await login(db, config, { email: "a@example.com", password: PASSWORD }, meta, at(100 + i))) as { token: string };
      assert.ok(fresh.token, `login ${i}`);
      const r = await completeMfa(db, config, await session(db, fresh.token, at(100 + i)), "000000", meta, at(100 + i));
      assert.equal(r.ok, false);
    }
    const { rows } = await db.query("select failed_logins, locked_until from website_user");
    assert.equal(rows[0].failed_logins, 5);
    assert.ok(rows[0].locked_until > at(110));
    assert.equal(await loadSession(db, token, at(106)), null, "every session ended, including the verified one");
    const again = await login(db, config, { email: "a@example.com", password: PASSWORD }, meta, at(120));
    assert.equal(again.ok, false, "locked account can't sign in");
  }));

test("step-up: not granted by signing in; wrong codes count toward the lock", { skip }, () =>
  withDb(async (db) => {
    const { token } = await enrolled(db);
    const current = await session(db, token, at(3));
    assert.equal(current.session.step_up_at, null);
    for (let i = 0; i < 4; i++) assert.equal(await stepUp(db, config, current, "000000", meta, at(10 + i)), false);
    const { rows } = await db.query("select failed_logins from website_user");
    assert.equal(rows[0].failed_logins, 4);
  }));

test("CSRF token is bound to the session token", { skip }, () => {
  const a = csrfToken(config, "session-a");
  assert.equal(csrfValid(config, "session-a", a), true);
  assert.equal(csrfValid(config, "session-b", a), false);
  assert.equal(csrfValid(config, undefined, a), false);
  assert.equal(csrfValid(config, "session-a", null), false);
});

test("log rows never contain passwords, tokens, codes or secrets", { skip }, () =>
  withDb(async (db) => {
    const { secret } = await enrolled(db);
    await login(db, config, { email: "a@example.com", password: "wrong password!!" }, meta, at(50));
    const { rows } = await db.query("select row_to_json(l)::text as row from website_log l");
    assert.ok(rows.length >= 5);
    for (const { row } of rows) {
      for (const needle of [PASSWORD, "wrong password", secret, "a@example.com"]) assert.ok(!row.includes(needle), `${needle} in ${row}`);
      assert.ok(!/\$argon2/.test(row));
    }
  }));

// ---------------------------------------------------------------- ADMIN_MFA_OPTIONAL (ADR 0012, 2026-11-18)

const optional: AdminConfig = { ...config, mfaOptional: true };
type SignedIn = { ok: true; token: string; mfaEnrolled: boolean };

async function authRows(db: pg.Client): Promise<string[]> {
  const { rows } = await db.query("select action from website_log where kind = 'auth' and action like 'login%' and outcome = 'ok' order by occurred_at, id");
  return rows.map((r) => r.action);
}

test("flag off: password alone leaves the session without access and logs a normal password step", { skip }, () =>
  withDb(async (db) => {
    const token = await adminWithPassword(db);
    const current = await session(db, token, at(2));
    assert.equal(current.session.mfa_verified_at, null);
    assert.equal(hasFullAccess(current, false), false);
    assert.deepEqual(await authRows(db), ["login.password"]);
  }));

test("flag on, no MFA enrolled: full session after the password, logged as password-only, session not marked verified", { skip }, () =>
  withDb(async (db) => {
    const { link } = await createFirstAdmin(db, optional, { email: "a@example.com", name: "A" }, T0);
    await redeemLink(db, link.split("#")[1], PASSWORD, meta, T0);
    const result = (await login(db, optional, { email: "a@example.com", password: PASSWORD }, meta, at(1))) as SignedIn;
    assert.equal(result.ok, true);
    assert.equal(result.mfaEnrolled, false);
    const current = await session(db, result.token, at(2));
    assert.equal(current.session.mfa_verified_at, null, "never recorded as a second factor");
    assert.equal(hasFullAccess(current, true), true);
    assert.equal(isPasswordOnly(current, true), true);
    assert.equal(hasFullAccess(current, false), false, "removing the flag ends access at once");
    assert.deepEqual(await authRows(db), ["login.password_only"]);
    const { rows } = await db.query("select row_to_json(l)::text as row, detail from website_log l where action = 'login.password_only'");
    assert.deepEqual(rows[0].detail, { via: "mfa_optional" });
    for (const needle of [PASSWORD, result.token, "a@example.com"]) assert.ok(!rows[0].row.includes(needle));
    const [user] = await listUsers(db, at(3));
    assert.ok(user.last_sign_in, "a password-only sign-in shows as the last sign-in");
  }));

test("flag on, MFA enrolled: the code is still required at sign-in", { skip }, () =>
  withDb(async (db) => {
    const { secret } = await enrolled(db);
    const result = (await login(db, optional, { email: "a@example.com", password: PASSWORD }, meta, at(100))) as SignedIn;
    assert.equal(result.mfaEnrolled, true);
    const current = await session(db, result.token, at(100));
    assert.equal(hasFullAccess(current, true), false);
    const rows = await authRows(db);
    assert.ok(!rows.includes("login.password_only"), rows.join());
    const done = await completeMfa(db, optional, current, totpAt(secret, at(100).getTime() / 1000), meta, at(100));
    assert.equal(done.ok, true);
    assert.equal(hasFullAccess(await session(db, (done as SignedIn).token, at(101)), true), true);
  }));

test("flag on: voluntary enrolment works, and other password-only sessions then lose access", { skip }, () =>
  withDb(async (db) => {
    const { link } = await createFirstAdmin(db, optional, { email: "a@example.com", name: "A" }, T0);
    await redeemLink(db, link.split("#")[1], PASSWORD, meta, T0);
    const other = (await login(db, optional, { email: "a@example.com", password: PASSWORD }, meta, at(1))) as SignedIn;
    const mine = (await login(db, optional, { email: "a@example.com", password: PASSWORD }, meta, at(1))) as SignedIn;
    const current = await session(db, mine.token, at(2));
    const secret = await pendingMfaSecret(db, optional, current);
    const done = await completeMfa(db, optional, current, totpAt(secret, at(2).getTime() / 1000), meta, at(2));
    assert.equal(done.ok, true);
    assert.equal((done as { recoveryCodes: string[] }).recoveryCodes.length, 10);
    assert.equal(hasFullAccess(await session(db, (done as SignedIn).token, at(3)), true), true);
    assert.equal(hasFullAccess(await session(db, other.token, at(3)), true), false, "the older password-only session needs the code now");
  }));

test("flag on, no MFA: step-up can't succeed and no failure is counted", { skip }, () =>
  withDb(async (db) => {
    const { link } = await createFirstAdmin(db, optional, { email: "a@example.com", name: "A" }, T0);
    await redeemLink(db, link.split("#")[1], PASSWORD, meta, T0);
    const { token } = (await login(db, optional, { email: "a@example.com", password: PASSWORD }, meta, at(1))) as SignedIn;
    const current = await session(db, token, at(2));
    assert.equal(await stepUp(db, optional, current, "000000", meta, at(2)), false);
    const after = await session(db, token, at(3));
    assert.equal(after.session.step_up_at, null);
    assert.equal(after.user.failed_logins, 0);
  }));

test("flag on, MFA enrolled: a valid code grants no step-up and counts no failure (R1)", { skip }, () =>
  withDb(async (db) => {
    const { token, secret } = await enrolled(db);
    const current = await session(db, token, at(60));
    assert.equal(await stepUp(db, optional, current, totpAt(secret, at(60).getTime() / 1000), meta, at(60)), false);
    const after = await session(db, token, at(61));
    assert.equal(after.session.step_up_at, null, "nothing carries over to when the flag is removed");
    assert.equal(after.user.failed_logins, 0);
    assert.equal(await stepUp(db, config, current, totpAt(secret, at(60).getTime() / 1000), meta, at(60)), true, "flag off: the same code works");
  }));

test("flag on: wrong enrolment codes lock the account and end its sessions (ADR 0012 risk, F6)", { skip }, () =>
  withDb(async (db) => {
    const { link } = await createFirstAdmin(db, optional, { email: "a@example.com", name: "A" }, T0);
    await redeemLink(db, link.split("#")[1], PASSWORD, meta, T0);
    const { token } = (await login(db, optional, { email: "a@example.com", password: PASSWORD }, meta, at(1))) as SignedIn;
    const current = await session(db, token, at(2));
    await pendingMfaSecret(db, optional, current);
    for (let i = 0; i < 5; i++) await completeMfa(db, optional, current, "000000", meta, at(3 + i));
    assert.equal(await loadSession(db, token, at(10)), null);
    assert.equal((await login(db, optional, { email: "a@example.com", password: PASSWORD }, meta, at(11))).ok, false);
  }));
