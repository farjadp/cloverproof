// D-S1: master-key rotation covers BOTH sealed secret kinds — API keys and TOTP secrets — in one
// transaction, so deleting the old KEK afterwards breaks nothing. Opt-in DB test.
import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import pg from "pg";
import { sealedKekId } from "../src/lib/admin/envelope.ts";
import { decryptKeyServerSide, saveKey } from "../src/lib/admin/keys.ts";
import { rotateMasterKey } from "../src/lib/admin/rotation.ts";
import { totpAt } from "../src/lib/admin/totp.ts";
import {
  completeMfa,
  createFirstAdmin,
  loadSession,
  login,
  pendingMfaSecret,
  redeemLink,
  stepUp,
  type AdminConfig,
  type Current,
} from "../src/lib/admin/service.ts";

const url = process.env.WEBSITE_TEST_DATABASE_URL;
const skip = url ? false : "WEBSITE_TEST_DATABASE_URL not set (DB tests are opt-in)";
const OLD = { id: "k2026a", key: randomBytes(32) };
const NEW = { id: "k2027a", key: randomBytes(32) };
const before: AdminConfig = { keks: [OLD], hmacKey: randomBytes(32), siteUrl: "https://example.test" };
const during: AdminConfig = { ...before, keks: [NEW, OLD] };
const after: AdminConfig = { ...before, keks: [NEW] };
const meta = { ipPrefix: null, uaFamily: null };
const PASSWORD = "green pasture morning rain";
const T0 = new Date("2026-11-17T12:00:00Z");
const at = (s: number) => new Date(T0.getTime() + s * 1000);
const SECRET = "sk-ant-api03-THIS-IS-A-TEST-KEY-0123456789-wxyz";

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

async function user(db: pg.Client, email: string, enrol: boolean): Promise<{ current: Current; secret: string }> {
  const { link } = await createFirstAdmin(db, before, { email, name: email, additional: true }, T0);
  await redeemLink(db, link.split("#")[1], PASSWORD, meta, T0);
  const signedIn = (await login(db, before, { email, password: PASSWORD }, meta, at(1))) as { token: string };
  let current = (await loadSession(db, signedIn.token, at(2))) as Current;
  const secret = await pendingMfaSecret(db, before, current);
  if (enrol) {
    const done = await completeMfa(db, before, current, totpAt(secret, at(2).getTime() / 1000), meta, at(2));
    assert.equal(done.ok, true);
    current = (await loadSession(db, (done as { token: string }).token, at(3))) as Current;
  }
  return { current, secret };
}

test("rotation re-seals TOTP secrets and API keys together; the old KEK is no longer needed", { skip }, () =>
  withDb(async (db) => {
    const enrolled = await user(db, "a@example.com", true);
    await user(db, "b@example.com", false); // enrolment started, not finished
    await saveKey(db, before, enrolled.current, "anthropic", SECRET, meta, at(4));

    assert.deepEqual(await rotateMasterKey(db, during), { keys: 1, mfa: 2 });
    assert.deepEqual(await rotateMasterKey(db, during), { keys: 0, mfa: 0 }, "idempotent");

    const { rows } = await db.query("select mfa_secret_enc from website_user where mfa_secret_enc is not null");
    assert.equal(rows.length, 2);
    for (const r of rows) assert.equal(sealedKekId(r.mfa_secret_enc), NEW.id);

    // Old KEK deleted: two-step sign-in and the API key still work.
    const code = totpAt(enrolled.secret, at(60).getTime() / 1000);
    assert.equal(await stepUp(db, after, enrolled.current, code, meta, at(60)), true, "TOTP works with the new KEK alone");
    assert.equal(await decryptKeyServerSide(db, after, "anthropic"), SECRET);
    const { rows: log } = await db.query("select detail from website_log where action = 'key.rewrap' order by occurred_at, id");
    assert.deepEqual(log.at(0)?.detail, { count: 1, mfa_count: 2, via: "cli" });
  }));

test("rotation refuses to commit when a TOTP secret would stay unreadable with the new KEK alone", { skip }, () =>
  withDb(async (db) => {
    await user(db, "a@example.com", true);
    // New key entered under the old id: nothing looks stale, but nothing would open after the old key is gone.
    const sameId: AdminConfig = { ...before, keks: [{ id: OLD.id, key: NEW.key }, { id: "k2025z", key: OLD.key }] };
    await assert.rejects(rotateMasterKey(db, sameId), /two-step sign-in secret/);
  }));
