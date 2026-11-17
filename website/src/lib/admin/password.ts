import { hash, verify } from "@node-rs/argon2";

// argon2id, OWASP 2024 baseline (ADR 0012): m = 19 MiB, t = 2, p = 1.
export const ARGON2_PARAMS = { algorithm: 2, memoryCost: 19456, timeCost: 2, parallelism: 1 } as const;
export const MIN_PASSWORD_LENGTH = 12;
export const MAX_PASSWORD_LENGTH = 128;

export function passwordProblem(password: string, email?: string | null): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) return `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
  if (password.length > MAX_PASSWORD_LENGTH) return `Use at most ${MAX_PASSWORD_LENGTH} characters.`;
  const name = email?.split("@")[0].toLowerCase() ?? "";
  if (name.length >= 4 && password.toLowerCase().includes(name)) {
    return "Don't use your e-mail name in the password.";
  }
  return null;
}

export function hashPassword(password: string): Promise<string> {
  return hash(password, ARGON2_PARAMS);
}

export async function verifyPassword(stored: string, password: string): Promise<boolean> {
  try {
    return await verify(stored, password);
  } catch {
    return false;
  }
}

/** True when the stored hash uses older parameters and should be re-hashed after login. */
export function needsRehash(stored: string): boolean {
  const { memoryCost, timeCost, parallelism } = ARGON2_PARAMS;
  return !stored.startsWith(`$argon2id$v=19$m=${memoryCost},t=${timeCost},p=${parallelism}$`);
}

// A fixed hash so "unknown user" costs the same time as "wrong password" (no enumeration).
let dummy: Promise<string> | null = null;
export async function burnPasswordTime(password: string): Promise<void> {
  dummy ??= hashPassword("timing-equaliser-not-a-real-password");
  await verifyPassword(await dummy, password);
}
