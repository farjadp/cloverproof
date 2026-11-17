// Node-only background work for the website admin, started from instrumentation.ts.
// Not "server-only" (instrumentation runs outside the React server layer); never imported by pages.
import pg from "pg";
import { writeLog } from "./service.ts";
import { recordPurgeError, runPurge } from "./log.ts";

let pool: pg.Pool | null = null;
function db(): pg.Pool | null {
  const url = process.env.ADMIN_DATABASE_URL;
  if (!url) return null;
  pool ??= new pg.Pool({ connectionString: url, max: 1, statement_timeout: 10_000, idle_in_transaction_session_timeout: 30_000 });
  return pool;
}

async function inTx<T>(p: pg.Pool, fn: (c: pg.PoolClient) => Promise<T>): Promise<T> {
  const client = await p.connect();
  try {
    await client.query("begin");
    const result = await fn(client);
    await client.query("commit");
    return result;
  } catch (error) {
    await client.query("rollback").catch(() => {});
    throw error;
  } finally {
    client.release();
  }
}

export async function purgeTick(): Promise<void> {
  const p = db();
  if (!p) return;
  try {
    await inTx(p, (c) => runPurge(c, new Date()));
  } catch (error) {
    await inTx(p, (c) => recordPurgeError(c, error, new Date())).catch(() => {});
  }
}

let started = false;
/** Hourly check (first after 1 minute); the purge itself runs at most once per 23 h. */
export function startPurgeTimer(): void {
  if (started || !process.env.ADMIN_DATABASE_URL) return;
  started = true;
  setTimeout(() => void purgeTick(), 60_000).unref();
  setInterval(() => void purgeTick(), 3600_000).unref();
}

/** Server errors on /admin only: path, error name and digest. No message, stack, body or IP. */
export async function logAdminError(path: string, error: unknown): Promise<void> {
  const p = db();
  if (!p || !(path === "/admin" || path.startsWith("/admin/"))) return;
  const name = error instanceof Error ? error.name : "Error";
  const digest = typeof error === "object" && error !== null && "digest" in error ? String((error as { digest: unknown }).digest) : undefined;
  await writeLog(p, {
    kind: "error",
    action: "request.error",
    outcome: "failed",
    detail: { path, error_name: name, error_code: digest?.slice(0, 40) },
  }).catch(() => {});
}
