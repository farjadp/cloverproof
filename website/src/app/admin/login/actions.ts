"use server";

import { redirect } from "next/navigation";
import { adminConfig, adminDb, inTransaction, preValid, requestMeta, sessionToken, setSessionCookie } from "@/lib/admin/server";
import { loadSession, login, LOGIN_FAILED, logout } from "@/lib/admin/service";

export type LoginState = { error: string | null };

export async function loginAction(_prev: LoginState, form: FormData): Promise<LoginState> {
  const db = adminDb();
  const config = adminConfig();
  if (!db || !config) return { error: "The admin is not configured." };
  if (!(await preValid(form))) return { error: "This form has expired. Reload the page." };
  const meta = await requestMeta();
  const previous = await sessionToken();
  const result = await inTransaction(db, async (tx) => {
    // A new sign-in replaces whatever session this browser had.
    const old = await loadSession(tx, previous, new Date());
    if (old) await logout(tx, old, meta, new Date());
    return login(tx, config, { email: String(form.get("email") ?? ""), password: String(form.get("password") ?? "") }, meta, new Date());
  });
  if (!result.ok) return { error: result.error || LOGIN_FAILED };
  await setSessionCookie(result.token);
  redirect("/admin/mfa");
}
