// Master-key (KEK) rotation across every sealed value the admin stores (ADR 0013; D-S1, D-S2):
// API keys (website_secret) and TOTP secrets (website_user.mfa_secret_enc). Call inside ONE
// transaction (npm run secrets:rewrap): if any value would stay unreadable with the new KEK
// alone, it throws and the caller rolls back, so the previous KEK is never needed afterwards.
import "server-only";
import { rewrapKeys } from "./keys.ts";
import { rewrapMfaSecrets, writeLog, type AdminConfig, type Db } from "./service.ts";

export async function rotateMasterKey(db: Db, config: AdminConfig): Promise<{ keys: number; mfa: number }> {
  const keys = await rewrapKeys(db, config);
  const mfa = await rewrapMfaSecrets(db, config);
  await writeLog(db, { kind: "secret", action: "key.rewrap", outcome: "ok", detail: { count: keys, mfa_count: mfa, via: "cli" } });
  return { keys, mfa };
}
