import { test } from "node:test";
import assert from "node:assert/strict";
import pg from "pg";
import { purgeHealth, readLog, recordPurgeError, runPurge, toCsv, type LogRow } from "../src/lib/admin/log.ts";

const row = (over: Partial<LogRow>): LogRow => ({
  id: "1", occurred_at: new Date("2026-11-17T12:00:00Z"), actor: "A", kind: "auth", action: "login",
  target_type: null, target_id: null, outcome: "ok", ip_prefix: "203.0.113.0/24", ua_family: "Firefox", detail: {}, ...over,
});

test("CSV: header, quoting and formula-injection guard", () => {
  const csv = toCsv([row({ actor: '=HYPERLINK("x")', detail: { reason: "a,b" } }), row({ actor: "-2+3", action: "@sum" })]);
  const lines = csv.trim().split("\r\n");
  assert.equal(lines[0], "occurred_at,actor,kind,action,target_type,target_id,outcome,ip_prefix,browser,detail");
  assert.match(lines[1], /^2026-11-17T12:00:00.000Z,"'=HYPERLINK\(""x""\)",auth,login,,,ok,203\.0\.113\.0\/24,Firefox,"\{""reason"":""a,b""\}"$/);
  assert.match(lines[2], /,'-2\+3,auth,'@sum,/);
});

const url = process.env.WEBSITE_TEST_DATABASE_URL;
const skip = url ? false : "WEBSITE_TEST_DATABASE_URL not set (DB tests are opt-in)";
const now = new Date();

async function withDb(fn: (db: pg.Client) => Promise<void>): Promise<void> {
  const db = new pg.Client({ connectionString: url });
  await db.connect();
  try {
    await db.query("begin");
    // Seed old rows as the owner (the app role can't back-date), then act as the app role.
    await db.query(
      `insert into website_log (occurred_at, kind, action, outcome) values
        (now() - interval '61 days', 'auth', 'old.one', 'ok'),
        (now() - interval '10 days', 'admin', 'recent.admin', 'ok'),
        (now() - interval '1 hour', 'auth', 'recent.fail', 'failed')`,
    );
    await db.query("delete from website_job_run");
    await db.query("set local role cp_website_admin");
    await fn(db);
  } finally {
    await db.query("rollback").catch(() => {});
    await db.end();
  }
}

test("purge runs once per 23 h, deletes > 60 days, records health and a log row", { skip }, () =>
  withDb(async (db) => {
    assert.equal((await purgeHealth(db, now)).stale, true, "never ran = stale");
    const first = await runPurge(db, now);
    assert.equal(first.ran, true);
    assert.ok((first.deleted ?? 0) >= 1);
    const { rows } = await db.query("select action from website_log where action = 'old.one'");
    assert.equal(rows.length, 0);
    assert.deepEqual(await runPurge(db, new Date(now.getTime() + 3600_000)), { ran: false }, "not again within 23 h");
    assert.equal((await runPurge(db, new Date(now.getTime() + 24 * 3600_000))).ran, true);
    const health = await purgeHealth(db, new Date(now.getTime() + 24 * 3600_000));
    assert.equal(health.stale, false);
    assert.equal((await purgeHealth(db, new Date(now.getTime() + 51 * 3600_000))).stale, true, "overdue after 26 h");
    const { rows: jobs } = await db.query("select detail from website_log where action = 'log.purge' and outcome = 'ok'");
    assert.equal(jobs.length, 2);
  }));

test("purge errors are recorded without messages", { skip }, () =>
  withDb(async (db) => {
    const error = Object.assign(new Error("secret value in message"), { code: "57014" });
    await recordPurgeError(db, error, now);
    const { rows } = await db.query("select last_error from website_job_run");
    assert.equal(rows[0].last_error, "Error 57014");
    const { rows: log } = await db.query("select detail::text as d from website_log where action = 'log.purge'");
    assert.ok(!log[0].d.includes("secret"));
  }));

test("reader: filters, 60-day window, junk filter values ignored", { skip }, () =>
  withDb(async (db) => {
    const all = await readLog(db, {}, now);
    assert.ok(all.rows.every((r) => r.action !== "old.one"), "older than 60 days hidden");
    const failed = await readLog(db, { outcome: "failed" }, now);
    assert.ok(failed.rows.length >= 1 && failed.rows.every((r) => r.outcome === "failed"));
    const junk = await readLog(db, { kind: "auth' or 1=1 --", outcome: "nope", actor: "x", from: "2026-13-99'", page: -5 }, now);
    assert.equal(junk.rows.length, all.rows.length);
    const paged = await readLog(db, {}, now, 1);
    assert.equal(paged.rows.length, 1);
    assert.equal(paged.more, true);
  }));
