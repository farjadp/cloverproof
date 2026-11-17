"use server";

import { revalidatePath } from "next/cache";
import { guardAction } from "@/lib/admin/server";
import { stepUp } from "@/lib/admin/service";

export type StepUpState = { error: string | null };

/** Fresh 6-digit code before sensitive pages (users, keys, log export). Valid 5 minutes. */
export async function stepUpAction(_prev: StepUpState, form: FormData): Promise<StepUpState> {
  const path = String(form.get("path") ?? "/admin");
  const guard = await guardAction("dashboard.view", form);
  if (!guard.ok) return { error: guard.error };
  const ok = await stepUp(guard.db, guard.config, guard.current, String(form.get("code") ?? ""), guard.meta, new Date());
  if (!ok) return { error: "That code is not valid. Try the newest code from your app." };
  revalidatePath(path.startsWith("/admin") ? path : "/admin");
  return { error: null };
}
