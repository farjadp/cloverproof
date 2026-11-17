"use server";

import { redirect } from "next/navigation";
import { adminConfig, adminDb, preValid, requestMeta, setSessionCookie } from "@/lib/admin/server";
import { login, LOGIN_FAILED } from "@/lib/admin/service";

export type LoginState = { error: string | null };

export async function loginAction(_prev: LoginState, form: FormData): Promise<LoginState> {
  const db = adminDb();
  const config = adminConfig();
  if (!db || !config) return { error: "The admin is not configured." };
  if (!(await preValid(form))) return { error: "This form has expired. Reload the page." };
  const result = await login(
    db,
    config,
    { email: String(form.get("email") ?? ""), password: String(form.get("password") ?? "") },
    await requestMeta(),
    new Date(),
  );
  if (!result.ok) return { error: result.error || LOGIN_FAILED };
  await setSessionCookie(result.token);
  redirect("/admin/mfa");
}
