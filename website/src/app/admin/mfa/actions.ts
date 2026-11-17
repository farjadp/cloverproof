"use server";

import { adminConfig, adminDb, csrfField, requestMeta, sessionToken, setSessionCookie } from "@/lib/admin/server";
import { completeMfa, csrfValid, loadSession, redeemRecoveryCode } from "@/lib/admin/service";

export type MfaState = { error: string | null; recoveryCodes?: string[]; done?: boolean; csrf?: string };

export async function mfaAction(_prev: MfaState, form: FormData): Promise<MfaState> {
  const db = adminDb();
  const config = adminConfig();
  if (!db || !config) return { error: "The admin is not configured." };
  const token = await sessionToken();
  const current = await loadSession(db, token, new Date());
  if (!current) return { error: "Your sign-in has ended. Sign in again." };
  if (!csrfValid(config, token, form.get("csrf"))) return { error: "This form has expired. Reload the page." };
  const code = String(form.get("code") ?? "");
  const useRecovery = form.get("mode") === "recovery";
  const result = useRecovery
    ? await redeemRecoveryCode(db, config, current, code, await requestMeta(), new Date())
    : await completeMfa(db, config, current, code, await requestMeta(), new Date());
  if (!result.ok) return { error: result.error };
  await setSessionCookie(result.token);
  return { error: null, done: true, recoveryCodes: result.recoveryCodes, csrf: await csrfField() };
}
