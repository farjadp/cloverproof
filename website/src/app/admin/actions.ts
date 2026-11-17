"use server";

import { redirect } from "next/navigation";
import { adminConfig, adminDb, clearSessionCookie, requestMeta, sessionToken } from "@/lib/admin/server";
import { csrfValid, loadSession, logout } from "@/lib/admin/service";

export async function logoutAction(form: FormData): Promise<void> {
  const db = adminDb();
  const config = adminConfig();
  const token = await sessionToken();
  if (db && config && csrfValid(config, token, form.get("csrf"))) {
    const current = await loadSession(db, token, new Date());
    if (current) await logout(db, current, await requestMeta(), new Date());
  }
  await clearSessionCookie();
  redirect("/admin/login");
}
