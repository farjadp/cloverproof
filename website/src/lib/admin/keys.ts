// AI-provider API keys (ADR 0013). Write-only in the admin: after saving, only the provider, the
// last 4 characters and test results are ever shown. Plaintext exists only inside this module,
// in server memory, for the test call (and later the P4 agents). Never sent to the browser or logged.
import { open, seal } from "./envelope.ts";
import { writeLog, type AdminConfig, type Current, type Db, type RequestMeta } from "./service.ts";

export const PROVIDERS = {
  anthropic: { label: "Claude (Anthropic)", hint: "Starts with sk-ant-" },
  google_gemini: { label: "Gemini (Google)", hint: "Google AI Studio key" },
  openai: { label: "OpenAI", hint: "Starts with sk-" },
  fal: { label: "fal", hint: "Key ID and secret, as shown by fal" },
} as const;
export type Provider = keyof typeof PROVIDERS;

export function isProvider(value: unknown): value is Provider {
  return typeof value === "string" && Object.hasOwn(PROVIDERS, value);
}

export type KeyRow = {
  provider: Provider;
  version: number;
  last4: string;
  created_at: Date;
  created_by: string;
  monthly_budget_usd: string | null;
  last_test_at: Date | null;
  last_test_ok: boolean | null;
};

const aad = (provider: Provider, version: number) => `website_secret|${provider}|${version}`;

/** Active key per provider (metadata only — no ciphertext leaves this function). */
export async function listKeys(db: Db): Promise<Partial<Record<Provider, KeyRow>>> {
  const { rows } = await db.query<KeyRow>(
    `select s.provider, s.version, s.last4, s.created_at, u.display_name as created_by, s.monthly_budget_usd::text,
            s.last_test_at, s.last_test_ok
       from website_secret s join website_user u on u.id = s.created_by
      where s.revoked_at is null`,
  );
  return Object.fromEntries(rows.map((r) => [r.provider, r]));
}

export type KeyResult = { ok: true; message: string } | { ok: false; error: string };

/** Thrown (to roll back the transaction) when another admin changed the same key at once. */
export class ConcurrentChange extends Error {
  constructor() {
    super("concurrent key change");
    this.name = "ConcurrentChange";
  }
}

export function keyProblem(key: string): string | null {
  if (key.length < 20 || key.length > 400) return "That doesn't look like an API key (20–400 characters).";
  if (/\s/.test(key)) return "Remove spaces or line breaks from the key.";
  if (!/^[\x21-\x7e]+$/.test(key)) return "The key contains characters that API keys don't use.";
  return null;
}

/** Saves a new key version for the provider and revokes the previous one (budget carries over). */
export async function saveKey(
  db: Db,
  config: AdminConfig,
  actor: Current,
  provider: string,
  rawKey: string,
  meta: RequestMeta,
  now: Date,
): Promise<KeyResult> {
  if (!isProvider(provider)) return { ok: false, error: "Unknown provider." };
  const key = rawKey.trim();
  const problem = keyProblem(key);
  if (problem) return { ok: false, error: problem };
  const { rows: prev } = await db.query<{ id: string; version: number; monthly_budget_usd: string | null }>(
    `select id, version, monthly_budget_usd from website_secret
      where provider = $1 order by version desc limit 1 for update`,
    [provider],
  );
  const version = (prev[0]?.version ?? 0) + 1;
  await db.query(
    "update website_secret set revoked_at = $2, revoked_by = $3 where provider = $1 and revoked_at is null",
    [provider, now, actor.user.id],
  );
  const kek = config.keks[0];
  const last4 = key.slice(-4).replace(/[^A-Za-z0-9_-]/g, "_");
  try {
    await db.query(
    `insert into website_secret (provider, version, sealed, kek_id, last4, monthly_budget_usd, created_by, created_at)
     values ($1, $2, $3, $4, $5, $6, $7, $8)`,
      [provider, version, seal(key, aad(provider, version), kek), kek.id, last4, prev[0]?.monthly_budget_usd ?? null, actor.user.id, now],
    );
  } catch (error) {
    // Two admins saving the same provider at once: the database keeps one; tell the other.
    if ((error as { code?: string })?.code === "23505") throw new ConcurrentChange();
    throw error;
  }
  await writeLog(db, {
    actor: actor.user.id,
    kind: "secret",
    action: version === 1 ? "key.add" : "key.replace",
    outcome: "ok",
    targetType: "website_secret",
    targetId: provider,
    meta,
    detail: { provider, last4 },
  });
  return { ok: true, message: `${PROVIDERS[provider].label} key saved (ends in ${last4}). It can't be shown again.` };
}

export async function revokeKey(db: Db, actor: Current, provider: string, meta: RequestMeta, now: Date): Promise<KeyResult> {
  if (!isProvider(provider)) return { ok: false, error: "Unknown provider." };
  const { rows } = await db.query<{ last4: string }>(
    "update website_secret set revoked_at = $2, revoked_by = $3 where provider = $1 and revoked_at is null returning last4",
    [provider, now, actor.user.id],
  );
  if (!rows[0]) return { ok: false, error: "There is no active key for this provider." };
  await writeLog(db, { actor: actor.user.id, kind: "secret", action: "key.revoke", outcome: "ok", targetType: "website_secret", targetId: provider, meta, detail: { provider, last4: rows[0].last4 } });
  return { ok: true, message: `${PROVIDERS[provider].label} key removed. Also revoke it in the provider's console.` };
}

export async function setBudget(db: Db, actor: Current, provider: string, raw: string, meta: RequestMeta): Promise<KeyResult> {
  if (!isProvider(provider)) return { ok: false, error: "Unknown provider." };
  const text = raw.trim();
  const amount = text === "" ? null : Number(text);
  if (amount !== null && (!Number.isFinite(amount) || amount < 0 || amount > 100000 || !/^\d+(\.\d{1,2})?$/.test(text))) {
    return { ok: false, error: "Enter an amount in US dollars, e.g. 50 or 49.99, or leave it empty for no cap." };
  }
  const { rowCount } = await db.query(
    "update website_secret set monthly_budget_usd = $2 where provider = $1 and revoked_at is null",
    [provider, amount],
  );
  if (rowCount !== 1) return { ok: false, error: "Add a key first." };
  await writeLog(db, { actor: actor.user.id, kind: "secret", action: "key.budget", outcome: "ok", targetType: "website_secret", targetId: provider, meta, detail: { provider, budget_usd: amount ?? "none" } });
  return { ok: true, message: amount === null ? "Monthly cap removed." : `Monthly cap set to $${amount.toFixed(2)}. Agents will stop when it's reached (P4).` };
}

/**
 * Decrypts the active key. Server-side only: the result must never be returned to a client,
 * logged or put in an error message.
 */
export async function decryptKeyServerSide(db: Db, config: AdminConfig, provider: Provider): Promise<string | null> {
  const { rows } = await db.query<{ sealed: Buffer; version: number }>(
    "select sealed, version from website_secret where provider = $1 and revoked_at is null",
    [provider],
  );
  return rows[0] ? open(rows[0].sealed, aad(provider, rows[0].version), config.keks) : null;
}

// ---------------------------------------------------------------- test connection

type Fetch = (url: string, init: RequestInit) => Promise<{ status: number }>;

/** The cheapest authenticated read per provider (no generation, no cost). */
export function testRequest(provider: Provider, key: string): { url: string; init: RequestInit } {
  switch (provider) {
    case "anthropic":
      return { url: "https://api.anthropic.com/v1/models?limit=1", init: { headers: { "x-api-key": key, "anthropic-version": "2023-06-01" } } };
    case "openai":
      return { url: "https://api.openai.com/v1/models", init: { headers: { authorization: `Bearer ${key}` } } };
    case "google_gemini":
      return { url: "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1", init: { headers: { "x-goog-api-key": key } } };
    case "fal":
      // fal's model list may also answer without a valid key: success here proves reachability,
      // and a 401/403 proves the key is wrong.
      return { url: "https://api.fal.ai/v1/models?limit=1", init: { headers: { authorization: `Key ${key}` } } };
  }
}

export async function testKey(
  db: Db,
  config: AdminConfig,
  actor: Current,
  provider: string,
  meta: RequestMeta,
  now: Date,
  fetcher: Fetch = (url, init) => fetch(url, init),
): Promise<KeyResult> {
  if (!isProvider(provider)) return { ok: false, error: "Unknown provider." };
  const key = await decryptKeyServerSide(db, config, provider);
  if (!key) return { ok: false, error: "Add a key first." };
  const { url, init } = testRequest(provider, key);
  let status = 0;
  try {
    status = (await fetcher(url, { ...init, method: "GET", redirect: "error", cache: "no-store", signal: AbortSignal.timeout(10_000) })).status;
  } catch {
    status = 0;
  }
  const ok = status >= 200 && status < 300;
  await db.query("update website_secret set last_test_at = $2, last_test_ok = $3 where provider = $1 and revoked_at is null", [provider, now, ok]);
  await writeLog(db, { actor: actor.user.id, kind: "secret", action: "key.test", outcome: ok ? "ok" : "failed", targetType: "website_secret", targetId: provider, meta, detail: { provider, status } });
  if (ok) {
    return { ok: true, message: provider === "fal" ? "fal answered. (fal may answer this check even with a wrong key; a wrong key shows as 401.)" : `${PROVIDERS[provider].label} accepted the key.` };
  }
  const why =
    status === 401 || status === 403
      ? "the provider rejected the key"
      : status === 429
        ? "the provider is rate-limiting; try again later"
        : status === 0
          ? "the provider couldn't be reached"
          : `the provider answered ${status}`;
  return { ok: false, error: `Test failed: ${why}.` };
}
