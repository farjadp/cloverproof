// API keys (ADR 0013) against a migrated Postgres (opt-in: WEBSITE_TEST_DATABASE_URL).
import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import pg from "pg";
import { decryptKeyServerSide, keyProblem, listKeys, revokeKey, rewrapAll, saveKey, setBudget, testKey, testRequest } from "../src/lib/admin/keys.ts";
import { createFirstAdmin, loadSession, login, redeemLink, type AdminConfig, type Current } from "../src/lib/admin/service.ts";

const url = process.env.WEBSITE_TEST_DATABASE_URL;
const skip = url ? false : "WEBSITE_TEST_DATABASE_URL not set (DB tests are opt-in)";
const config: AdminConfig = { keks: [{ id: "t1", key: randomBytes(32) }], hmacKey: randomBytes(32), siteUrl: "https://example.test" };
const meta = { ipPrefix: null, uaFamily: null };
const now = new Date("2026-11-17T12:00:00Z");
const SECRET = "sk-ant-api03-THIS-IS-A-TEST-KEY-0123456789-wxyz";

async function withDb(fn: (db: pg.Client, admin: Current) => Promise<void>): Promise<void> {
  const db = new pg.Client({ connectionString: url });
  await db.connect();
  try {
    await db.query("begin");
    await db.query("set local role cp_website_admin");
    const { link } = await createFirstAdmin(db, config, { email: "boss@example.com", name: "Boss", additional: true }, now);
    await redeemLink(db, link.split("#")[1], "green pasture morning rain", meta, now);
    const t = (await login(db, config, { email: "boss@example.com", password: "green pasture morning rain" }, meta, now)) as { token: string };
    const admin = await loadSession(db, t.token, now);
    assert.ok(admin);
    await fn(db, admin);
  } finally {
    await db.query("rollback").catch(() => {});
    await db.end();
  }
}

test("key format checks", () => {
  assert.ok(keyProblem("short"));
  assert.ok(keyProblem("sk-ant-has space in the middle-123456"));
  assert.equal(keyProblem(SECRET), null);
});

test("test requests carry the key only in headers, to the provider's own host", () => {
  for (const provider of ["anthropic", "openai", "google_gemini", "fal"] as const) {
    const { url: u, init } = testRequest(provider, "KEY-123");
    assert.ok(!u.includes("KEY-123"), provider);
    assert.match(u, /^https:\/\/(api\.anthropic\.com|api\.openai\.com|generativelanguage\.googleapis\.com|api\.fal\.ai)\//);
    assert.ok(JSON.stringify(init.headers).includes("KEY-123"));
  }
});

test("save: sealed at rest, only last 4 listed, nothing secret in the log", { skip }, () =>
  withDb(async (db, admin) => {
    assert.equal((await saveKey(db, config, admin, "anthropic", `  ${SECRET} `, meta, now)).ok, true);
    const { rows } = await db.query("select sealed, last4, version, kek_id from website_secret where provider = 'anthropic'");
    assert.ok(!rows[0].sealed.toString("utf8").includes(SECRET));
    assert.ok(!rows[0].sealed.toString("utf8").includes("THIS-IS-A-TEST"));
    assert.deepEqual([rows[0].last4, rows[0].version, rows[0].kek_id], ["wxyz", 1, "t1"]);
    const listed = await listKeys(db);
    assert.equal(listed.anthropic?.last4, "wxyz");
    assert.ok(!JSON.stringify(listed).includes("THIS-IS-A-TEST"));
    assert.equal(await decryptKeyServerSide(db, config, "anthropic"), SECRET);
    await assert.rejects(decryptKeyServerSide(db, { ...config, keks: [{ id: "t1", key: randomBytes(32) }] }, "anthropic"));
    const { rows: log } = await db.query("select row_to_json(l)::text as r from website_log l where kind = 'secret'");
    assert.ok(log.length === 1 && !log[0].r.includes("THIS-IS-A-TEST") && log[0].r.includes("key.add"));
  }));

test("replace keeps history and the budget; revoke; unknown provider refused", { skip }, () =>
  withDb(async (db, admin) => {
    await saveKey(db, config, admin, "openai", "sk-proj-first-key-aaaaaaaaaaaa1111", meta, now);
    assert.equal((await setBudget(db, admin, "openai", "49.99", meta)).ok, true);
    assert.equal((await setBudget(db, admin, "openai", "-1", meta)).ok, false);
    assert.equal((await setBudget(db, admin, "openai", "1e9", meta)).ok, false);
    await saveKey(db, config, admin, "openai", "sk-proj-second-key-bbbbbbbbbbb2222", meta, now);
    const { rows } = await db.query("select version, revoked_at is not null as revoked, monthly_budget_usd::text as b from website_secret where provider = 'openai' order by version");
    assert.deepEqual(rows, [{ version: 1, revoked: true, b: "49.99" }, { version: 2, revoked: false, b: "49.99" }]);
    assert.equal(await decryptKeyServerSide(db, config, "openai"), "sk-proj-second-key-bbbbbbbbbbb2222");
    assert.equal((await revokeKey(db, admin, "openai", meta, now)).ok, true);
    assert.equal(await decryptKeyServerSide(db, config, "openai"), null);
    assert.equal((await revokeKey(db, admin, "openai", meta, now)).ok, false);
    assert.equal((await saveKey(db, config, admin, "mistral", SECRET, meta, now)).ok, false);
  }));

test("test connection: 200 passes, 401 is a rejected key, network error handled; result stored", { skip }, () =>
  withDb(async (db, admin) => {
    await saveKey(db, config, admin, "anthropic", SECRET, meta, now);
    const seen: string[] = [];
    const ok = await testKey(db, config, admin, "anthropic", meta, now, async (u, init) => {
      seen.push(u, JSON.stringify(init.headers));
      return { status: 200 };
    });
    assert.equal(ok.ok, true);
    assert.ok(seen[1].includes(SECRET), "key sent to the provider in a header");
    const bad = await testKey(db, config, admin, "anthropic", meta, now, async () => ({ status: 401 }));
    assert.deepEqual(bad, { ok: false, error: "Test failed: the provider rejected the key." });
    const down = await testKey(db, config, admin, "anthropic", meta, now, async () => {
      throw new Error(`connect failed ${SECRET}`);
    });
    assert.equal(down.ok, false);
    assert.ok(!JSON.stringify(down).includes(SECRET));
    const { rows } = await db.query("select last_test_ok from website_secret where provider = 'anthropic' and revoked_at is null");
    assert.equal(rows[0].last_test_ok, false);
    const { rows: log } = await db.query("select string_agg(detail::text, ' ') as d from website_log where action = 'key.test'");
    assert.ok(!log[0].d.includes("THIS-IS-A-TEST"));
  }));

test("replaced and revoked keys keep no recoverable ciphertext (tombstone)", { skip }, () =>
  withDb(async (db, admin) => {
    await saveKey(db, config, admin, "openai", "sk-proj-first-key-aaaaaaaaaaaa1111", meta, now);
    await saveKey(db, config, admin, "openai", "sk-proj-second-key-bbbbbbbbbbb2222", meta, now);
    await revokeKey(db, admin, "openai", meta, now);
    const { rows } = await db.query(
      "select version, sealed = website_secret_tombstone() as tomb, revoked_at is not null as revoked from website_secret where provider = 'openai' order by version",
    );
    assert.deepEqual(rows, [{ version: 1, tomb: true, revoked: true }, { version: 2, tomb: true, revoked: true }]);
  }));

test("rotation refuses to commit if any active key is not openable with the new KEK alone (D-S2)", { skip }, () =>
  withDb(async (db, admin) => {
    await saveKey(db, config, admin, "anthropic", SECRET, meta, now);
    // The forgotten-id mistake: a NEW key put in under the OLD id. Nothing looks "old", so a
    // naive rewrap re-seals 0 rows; deleting the real old key would then lose every API key.
    const sameIdNewKey = { ...config, keks: [{ id: "t1", key: randomBytes(32) }, { id: "t0", key: config.keks[0].key }] };
    await assert.rejects(rewrapAll(db, sameIdNewKey), /not under the current master key|could not be opened/);
  }));

test("rotation asserts no active key stays under the old KEK id (D-S2)", { skip }, () =>
  withDb(async (db, admin) => {
    await saveKey(db, config, admin, "anthropic", SECRET, meta, now);
    const rotated = { ...config, keks: [{ id: "t2", key: randomBytes(32) }, ...config.keks] };
    // A database wrapper that silently drops the re-seal writes.
    const lossy = { query: (sql: string, params?: unknown[]) => (/^update website_secret set sealed/.test(sql) ? Promise.resolve({ rows: [], rowCount: 0 }) : db.query(sql, params)) };
    await assert.rejects(rewrapAll(lossy as unknown as pg.Client, rotated), /not under the current master key/);
  }));

test("master-key rotation re-seals active keys under the new KEK", { skip }, () =>
  withDb(async (db, admin) => {
    await saveKey(db, config, admin, "anthropic", SECRET, meta, now);
    const next = { id: "t2", key: randomBytes(32) };
    const rotated = { ...config, keks: [next, ...config.keks] };
    assert.equal(await rewrapAll(db, rotated), 1);
    assert.equal(await rewrapAll(db, rotated), 0, "idempotent");
    const { rows } = await db.query("select kek_id from website_secret where provider = 'anthropic' and revoked_at is null");
    assert.equal(rows[0].kek_id, "t2");
    assert.equal(await decryptKeyServerSide(db, { ...config, keks: [next] }, "anthropic"), SECRET, "old KEK no longer needed");
  }));
