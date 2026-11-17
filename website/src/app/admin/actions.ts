"use server";

import { redirect } from "next/navigation";
import { adminConfig, adminDb, clearSessionCookie, requestMeta, sessionToken } from "@/lib/admin/server";
import { csrfValid, loadSession, logout } from "@/lib/admin/service";

export async function logoutAction(form: FormData): Promise<void> {
  const db = adminDb();
  const config = adminConfig();
  const token = await sessionToken();
  // Signing out is always honoured (it can only end the caller's own session); CSRF is still
  // checked so the log says whether it came from our form.
  if (db && config) {
    const current = await loadSession(db, token, new Date());
    if (current) await logout(db, current, await requestMeta(), new Date(), csrfValid(config, token, form.get("csrf")));
  }
  await clearSessionCookie();
  redirect("/admin/login");
}
