import { keyFromBase64 } from "./crypto.ts";
import type { Kek } from "./envelope.ts";

// Master keys (KEKs) from env (ADR 0013; D-S2). No default ids: a missing or reused id is how a
// rotation silently re-seals nothing and the old key's deletion then loses every secret.
// Errors name the variable only, never its value. Shared by the server and the CLI scripts.

const KEK_ID = /^[A-Za-z0-9_.-]{1,40}$/; // same rule as website_secret.kek_id

type Env = Record<string, string | undefined>;

function kekId(env: Env, name: string): string {
  const value = env[name]?.trim();
  if (!value) throw new Error(`${name} is not set`);
  if (!KEK_ID.test(value)) throw new Error(`${name} must be 1–40 characters: letters, digits, _ . -`);
  return value;
}

/** [current, previous?]. The previous KEK is set only during a rotation. */
export function kekRingFromEnv(env: Env = process.env): Kek[] {
  const current: Kek = {
    id: kekId(env, "WEBSITE_SECRETS_KEK_ID"),
    key: keyFromBase64("WEBSITE_SECRETS_KEK", env.WEBSITE_SECRETS_KEK),
  };
  if (!env.WEBSITE_SECRETS_KEK_PREVIOUS && !env.WEBSITE_SECRETS_KEK_PREVIOUS_ID) return [current];
  const previous: Kek = {
    id: kekId(env, "WEBSITE_SECRETS_KEK_PREVIOUS_ID"),
    key: keyFromBase64("WEBSITE_SECRETS_KEK_PREVIOUS", env.WEBSITE_SECRETS_KEK_PREVIOUS),
  };
  if (previous.id === current.id) {
    throw new Error("WEBSITE_SECRETS_KEK_ID and WEBSITE_SECRETS_KEK_PREVIOUS_ID must differ");
  }
  if (previous.key.equals(current.key)) {
    throw new Error("WEBSITE_SECRETS_KEK and WEBSITE_SECRETS_KEK_PREVIOUS hold the same key");
  }
  return [current, previous];
}
