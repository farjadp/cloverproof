"use server";

import { adminDb, preValid, requestMeta } from "@/lib/admin/server";
import { redeemLink } from "@/lib/admin/service";

export type SetupState = { error: string | null; done?: boolean };

export async function setupAction(_prev: SetupState, form: FormData): Promise<SetupState> {
  const db = adminDb();
  if (!db) return { error: "The admin is not configured." };
  if (!(await preValid(form))) return { error: "This form has expired. Reload the page." };
  const password = String(form.get("password") ?? "");
  if (password !== String(form.get("confirm") ?? "")) return { error: "The two passwords don't match." };
  const result = await redeemLink(db, String(form.get("token") ?? ""), password, await requestMeta(), new Date());
  return result.ok ? { error: null, done: true } : { error: result.error };
}
