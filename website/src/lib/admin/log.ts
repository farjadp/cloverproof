// System log reading and the 60-day retention job (ADR 0014). Framework-free.
import { writeLog, type Db } from "./service.ts";

export const RETENTION_DAYS = 60;
export const KINDS = ["auth", "admin", "content", "secret", "error", "job"] as const;
export const OUTCOMES = ["ok", "denied", "failed"] as const;
export const PAGE_SIZE = 50;

export type LogFilter = { kind?: string; outcome?: string; actor?: string; from?: string; to?: string; page?: number };

export type LogRow = {
  id: string;
  occurred_at: Date;
  actor: string | null;
  kind: string;
  action: string;
  target_type: string | null;
  target_id: string | null;
  outcome: string;
  ip_prefix: string | null;
  ua_family: string | null;
  detail: Record<string, unknown>;
};

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const UUID = /^[0-9a-f-]{36}$/i;

/** Parameterised WHERE clause from untrusted filter values (unknown values are ignored). */
function where(filter: LogFilter, now: Date): { sql: string; params: unknown[] } {
  const params: unknown[] = [new Date(now.getTime() - RETENTION_DAYS * 86400_000)];
  const parts = ["l.occurred_at >= $1"];
  if (filter.kind && (KINDS as readonly string[]).includes(filter.kind)) {
    params.push(filter.kind);
    parts.push(`l.kind = $${params.length}`);
  }
  if (filter.outcome && (OUTCOMES as readonly string[]).includes(filter.outcome)) {
    params.push(filter.outcome);
    parts.push(`l.outcome = $${params.length}`);
  }
  if (filter.actor && UUID.test(filter.actor)) {
    params.push(filter.actor);
    parts.push(`l.actor_user_id = $${params.length}`);
  }
  if (filter.from && DATE.test(filter.from)) {
    params.push(`${filter.from}T00:00:00Z`);
    parts.push(`l.occurred_at >= $${params.length}::timestamptz`);
  }
  if (filter.to && DATE.test(filter.to)) {
    params.push(`${filter.to}T00:00:00Z`);
    parts.push(`l.occurred_at < $${params.length}::timestamptz + interval '1 day'`);
  }
  return { sql: parts.join(" and "), params };
}

export async function readLog(
  db: Db,
  filter: LogFilter,
  now: Date,
  limit = PAGE_SIZE,
): Promise<{ rows: LogRow[]; more: boolean }> {
  const { sql, params } = where(filter, now);
  const page = Math.max(1, Math.min(Number(filter.page) || 1, 1000));
  params.push(limit + 1, (page - 1) * limit);
  const { rows } = await db.query<LogRow>(
    `select l.id::text, l.occurred_at, u.display_name as actor, l.kind, l.action, l.target_type, l.target_id,
            l.outcome, host(l.ip_prefix) || '/' || masklen(l.ip_prefix) as ip_prefix, l.ua_family, l.detail
       from website_log l left join website_user u on u.id = l.actor_user_id
      where ${sql}
      order by l.occurred_at desc, l.id desc
      limit $${params.length - 1} offset $${params.length}`,
    params,
  );
  return { rows: rows.slice(0, limit), more: rows.length > limit };
}

export async function actors(db: Db): Promise<{ id: string; name: string }[]> {
  const { rows } = await db.query<{ id: string; name: string }>(
    "select id, display_name as name from website_user order by lower(display_name)",
  );
  return rows;
}

/** CSV with a formula-injection guard (cells starting with = + - @ | % get a leading apostrophe). */
export function toCsv(rows: LogRow[]): string {
  const cell = (v: unknown) => {
    let s =
      v === null || v === undefined
        ? ""
        : v instanceof Date
          ? v.toISOString()
          : typeof v === "object"
            ? JSON.stringify(v)
            : String(v);
    if (/^[=+\-@|%\t\r]/.test(s)) s = `'${s}`;
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const head = ["occurred_at", "actor", "kind", "action", "target_type", "target_id", "outcome", "ip_prefix", "browser", "detail"];
  const lines = rows.map((r) =>
    [r.occurred_at, r.actor, r.kind, r.action, r.target_type, r.target_id, r.outcome, r.ip_prefix, r.ua_family, r.detail]
      .map(cell)
      .join(","),
  );
  return [head.join(","), ...lines].join("\r\n") + "\r\n";
}

// ---------------------------------------------------------------- retention job

export const PURGE_JOB = "website_log_purge";
export const PURGE_EVERY_HOURS = 23;
export const PURGE_STALE_HOURS = 26;

export type JobHealth = { last_ok_at: Date | null; last_error_at: Date | null; stale: boolean };

/**
 * Runs the purge if it hasn't succeeded in the last 23 h. Safe to call from every replica every
 * hour: a transaction-scoped advisory lock lets only one run at a time. Call inside a transaction.
 */
export async function runPurge(db: Db, now: Date): Promise<{ ran: boolean; deleted?: number }> {
  const { rows: lock } = await db.query<{ ok: boolean }>("select pg_try_advisory_xact_lock(hashtext($1)) as ok", [PURGE_JOB]);
  if (!lock[0].ok) return { ran: false };
  const { rows: last } = await db.query<{ last_ok_at: Date | null }>(
    "select last_ok_at from website_job_run where job = $1",
    [PURGE_JOB],
  );
  const lastOk = last[0]?.last_ok_at ? new Date(last[0].last_ok_at).getTime() : 0;
  if (now.getTime() - lastOk < PURGE_EVERY_HOURS * 3600_000) return { ran: false };
  const { rows } = await db.query<{ n: string }>("select website_log_purge() as n");
  const deleted = Number(rows[0].n);
  await db.query(
    `insert into website_job_run (job, last_ok_at) values ($1, $2)
     on conflict (job) do update set last_ok_at = excluded.last_ok_at`,
    [PURGE_JOB, now],
  );
  await writeLog(db, { kind: "job", action: "log.purge", outcome: "ok", detail: { count: deleted } });
  return { ran: true, deleted };
}

/** Records a failed run (error name and SQLSTATE only; no message, stack or values). */
export async function recordPurgeError(db: Db, error: unknown, now: Date): Promise<void> {
  const name = error instanceof Error ? error.name : "Error";
  const code = (error as { code?: string })?.code;
  await db.query(
    `insert into website_job_run (job, last_error_at, last_error) values ($1, $2, $3)
     on conflict (job) do update set last_error_at = excluded.last_error_at, last_error = excluded.last_error`,
    [PURGE_JOB, now, `${name}${code ? ` ${code}` : ""}`.slice(0, 120)],
  );
  await writeLog(db, { kind: "job", action: "log.purge", outcome: "failed", detail: { error_name: name, error_code: code } });
}

export async function purgeHealth(db: Db, now: Date): Promise<JobHealth> {
  const { rows } = await db.query<{ last_ok_at: Date | null; last_error_at: Date | null }>(
    "select last_ok_at, last_error_at from website_job_run where job = $1",
    [PURGE_JOB],
  );
  const lastOk = rows[0]?.last_ok_at ?? null;
  return {
    last_ok_at: lastOk,
    last_error_at: rows[0]?.last_error_at ?? null,
    stale: !lastOk || now.getTime() - new Date(lastOk).getTime() > PURGE_STALE_HOURS * 3600_000,
  };
}
