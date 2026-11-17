"use server";

import { revalidatePath } from "next/cache";
import { ConcurrentChange, revokeKey, saveKey, setBudget, testKey, type KeyResult } from "@/lib/admin/keys";
import { guardAction, inTransaction } from "@/lib/admin/server";

export type KeyState = { result: KeyResult | null };

/** Every key operation: session + MFA + CSRF + admin role + fresh step-up, one transaction. */
export async function keyAction(_prev: KeyState, form: FormData): Promise<KeyState> {
  const guard = await guardAction("keys.manage", form, { stepUp: true });
  if (!guard.ok) {
    return { result: { ok: false, error: guard.error === "STEP_UP" ? "Confirm with a new code first (reload the page)." : guard.error } };
  }
  const { db, config, current, meta } = guard;
  const provider = String(form.get("provider") ?? "");
  const op = String(form.get("op") ?? "");
  const now = new Date();
  if (op === "test") {
    // Not inside a transaction: the provider call can take up to 10 s.
    const result = await testKey(db, config, current, provider, meta, now);
    revalidatePath("/admin/keys");
    return { result };
  }
  const run = () => inTransaction(db, (tx): Promise<KeyResult> => {
    switch (op) {
      case "save":
        return saveKey(tx, config, current, provider, String(form.get("key") ?? ""), meta, now);
      case "revoke":
        return revokeKey(tx, current, provider, meta, now);
      case "budget":
        return setBudget(tx, current, provider, String(form.get("budget") ?? ""), meta);
      default:
        return Promise.resolve({ ok: false, error: "Unknown action." });
    }
  });
  let result: KeyResult;
  try {
    result = await run();
  } catch (error) {
    if (!(error instanceof ConcurrentChange)) throw error;
    result = { ok: false, error: "Another admin just changed this key. Reload and try again." };
  }
  revalidatePath("/admin/keys");
  return { result };
}
