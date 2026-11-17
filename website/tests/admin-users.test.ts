// Website staff management against a migrated Postgres (opt-in: WEBSITE_TEST_DATABASE_URL).
import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import pg from "pg";
import { createFirstAdmin, loadSession, login, redeemLink, type AdminConfig, type Current } from "../src/lib/admin/service.ts";
import { changeRole, deleteUser, inviteUser, listUsers, resetMfa, resetPassword, setDisabled } from "../src/lib/admin/users.ts";

const url = process.env.WEBSITE_TEST_DATABASE_URL;
const skip = url ? false : "WEBSITE_TEST_DATABASE_URL not set (DB tests are opt-in)";
const config: AdminConfig = { keks: [{ id: "t1", key: randomBytes(32) }], hmacKey: randomBytes(32), siteUrl: "https://example.test" };
const meta = { ipPrefix: null, uaFamily: null };
const PASSWORD = "green pasture morning rain";
const now = new Date("2026-11-17T12:00:00Z");

async function withDb(fn: (db: pg.Client, admin: Current) => Promise<void>): Promise<void> {
  const db = new pg.Client({ connectionString: url });
  await db.connect();
  try {
    await db.query("begin");
    await db.query("set local role cp_website_admin");
    const { link } = await createFirstAdmin(db, config, { email: "boss@example.com", name: "Boss", additional: true }, now);
    await redeemLink(db, link.split("#")[1], PASSWORD, meta, now);
    const signedIn = (await login(db, config, { email: "boss@example.com", password: PASSWORD }, meta, now)) as { token: string };
    const admin = await loadSession(db, signedIn.token, now);
    assert.ok(admin);
    await fn(db, admin);
  } finally {
    await db.query("rollback").catch(() => {});
    await db.end();
  }
}

async function invite(db: pg.Client, admin: Current, email: string, role = "editor"): Promise<{ id: string; link: string }> {
  const r = await inviteUser(db, config, admin, { email, name: email.split("@")[0], role }, meta, now);
  assert.equal(r.ok, true, JSON.stringify(r));
  const { rows } = await db.query("select id from website_user where email = $1", [email]);
  return { id: rows[0].id, link: (r as { link: string }).link };
}

test("invite: link, duplicate refused, bad input refused, listed as invited", { skip }, () =>
  withDb(async (db, admin) => {
    const { link } = await invite(db, admin, "ed@example.com");
    assert.match(link, /\/admin\/setup#/);
    assert.equal((await inviteUser(db, config, admin, { email: "ED@example.com", name: "x", role: "author" }, meta, now)).ok, false);
    assert.equal((await inviteUser(db, config, admin, { email: "bad", name: "x", role: "author" }, meta, now)).ok, false);
    assert.equal((await inviteUser(db, config, admin, { email: "z@example.com", name: "x", role: "superadmin" }, meta, now)).ok, false);
    const users = await listUsers(db, now);
    assert.equal(users.find((u) => u.email === "ed@example.com")?.status, "invited");
  }));

test("role change logged; last admin can't be demoted", { skip }, () =>
  withDb(async (db, admin) => {
    const { id } = await invite(db, admin, "ed@example.com");
    assert.equal((await changeRole(db, admin, id, "author", meta)).ok, true);
    const { rows } = await db.query("select detail from website_log where action = 'user.role'");
    assert.deepEqual(rows[0].detail, { from_role: "editor", to_role: "author" });
    const { rows: admins } = await db.query("select id from website_user where role = 'admin' and disabled_at is null");
    // Other admins may exist in a shared test DB only inside this rolled-back transaction: demote all but self first.
    for (const a of admins) if (a.id !== admin.user.id) await db.query("update website_user set disabled_at = now() where id = $1", [a.id]);
    assert.deepEqual(await changeRole(db, admin, admin.user.id, "editor", meta), { ok: false, error: "There must always be at least one active admin." });
  }));

test("disable signs the user out everywhere; can't disable yourself; enable works", { skip }, () =>
  withDb(async (db, admin) => {
    const { id, link } = await invite(db, admin, "ed@example.com");
    await redeemLink(db, link.split("#")[1], PASSWORD, meta, now);
    const t = (await login(db, config, { email: "ed@example.com", password: PASSWORD }, meta, now)) as { token: string };
    assert.ok(await loadSession(db, t.token, now));
    assert.equal((await setDisabled(db, admin, id, true, meta, now)).ok, true);
    assert.equal(await loadSession(db, t.token, now), null);
    assert.equal((await login(db, config, { email: "ed@example.com", password: PASSWORD }, meta, now)).ok, false);
    assert.equal((await setDisabled(db, admin, admin.user.id, true, meta, now)).ok, false);
    assert.equal((await setDisabled(db, admin, id, false, meta, now)).ok, true);
    assert.equal((await login(db, config, { email: "ed@example.com", password: PASSWORD }, meta, now)).ok, true);
  }));

test("disable kills pending links; another admin's sign-in can't be reset here", { skip }, () =>
  withDb(async (db, admin) => {
    const { id, link } = await invite(db, admin, "ed@example.com");
    await setDisabled(db, admin, id, true, meta, now);
    await setDisabled(db, admin, id, false, meta, now);
    assert.equal((await redeemLink(db, link.split("#")[1], PASSWORD, meta, now)).ok, false, "link stays dead after re-enable");
    const { id: other } = await invite(db, admin, "admin2@example.com", "admin");
    assert.equal((await resetPassword(db, config, admin, other, meta, now)).ok, false);
    assert.equal((await resetMfa(db, admin, other, meta, now)).ok, false);
  }));

test("password reset link and MFA reset", { skip }, () =>
  withDb(async (db, admin) => {
    const { id, link } = await invite(db, admin, "ed@example.com");
    await redeemLink(db, link.split("#")[1], PASSWORD, meta, now);
    const reset = await resetPassword(db, config, admin, id, meta, now);
    assert.equal(reset.ok, true);
    assert.deepEqual(await redeemLink(db, (reset as { link: string }).link.split("#")[1], "a brand new passphrase", meta, now), { ok: true });
    await db.query("update website_user set mfa_secret_enc = 'x'::bytea, mfa_enabled_at = now() where id = $1", [id]);
    await db.query("insert into website_user_recovery_code (user_id, code_hash) values ($1, $2)", [id, randomBytes(32)]);
    assert.equal((await resetMfa(db, admin, id, meta, now)).ok, true);
    const { rows } = await db.query("select mfa_enabled_at, mfa_secret_enc, (select count(*)::int from website_user_recovery_code where user_id = $1) as codes from website_user where id = $1", [id]);
    assert.deepEqual(rows[0], { mfa_enabled_at: null, mfa_secret_enc: null, codes: 0 });
    assert.equal((await resetMfa(db, admin, admin.user.id, meta, now)).ok, false, "not your own");
  }));

test("delete: needs the e-mail typed, pseudonymises, kills links and sessions; not yourself", { skip }, () =>
  withDb(async (db, admin) => {
    const { id, link } = await invite(db, admin, "ed@example.com");
    assert.equal((await deleteUser(db, admin, id, "wrong@example.com", meta, now)).ok, false);
    assert.equal((await deleteUser(db, admin, id, " ED@example.com", meta, now)).ok, true);
    const { rows } = await db.query("select email, password_hash, deleted_at is not null as deleted, display_name from website_user where id = $1", [id]);
    assert.deepEqual(rows[0], { email: null, password_hash: null, deleted: true, display_name: "ed" });
    assert.equal((await redeemLink(db, link.split("#")[1], PASSWORD, meta, now)).ok, false, "invite link dead");
    assert.equal((await listUsers(db, now)).some((u) => u.id === id), false);
    assert.equal((await deleteUser(db, admin, admin.user.id, "boss@example.com", meta, now)).ok, false);
    const { rows: log } = await db.query("select action from website_log where target_id = $1 order by id", [id]);
    assert.deepEqual(log.map((r) => r.action), ["user.invite", "user.delete"]);
  }));
