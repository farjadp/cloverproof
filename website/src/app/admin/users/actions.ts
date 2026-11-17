"use server";

import { revalidatePath } from "next/cache";
import { guardAction, inTransaction } from "@/lib/admin/server";
import { changeRole, deleteUser, inviteUser, resetMfa, resetPassword, setDisabled, type Result } from "@/lib/admin/users";

export type UserActionState = { result: Result | null };

/** One action for every user operation; `op` picks it. Session, CSRF, role and step-up checked first. */
export async function userAction(_prev: UserActionState, form: FormData): Promise<UserActionState> {
  const guard = await guardAction("users.manage", form, { stepUp: true });
  if (!guard.ok) {
    return { result: { ok: false, error: guard.error === "STEP_UP" ? "Confirm with a new code first (reload the page)." : guard.error } };
  }
  const { db, config, current, meta } = guard;
  const now = new Date();
  const id = String(form.get("id") ?? "");
  const op = String(form.get("op") ?? "");
  const result = await inTransaction(db, async (tx) => {
    switch (op) {
      case "invite":
        return inviteUser(tx, config, current, { email: String(form.get("email") ?? ""), name: String(form.get("name") ?? ""), role: String(form.get("role") ?? "") }, meta, now);
      case "role":
        return changeRole(tx, current, id, String(form.get("role") ?? ""), meta);
      case "disable":
        return setDisabled(tx, current, id, true, meta, now);
      case "enable":
        return setDisabled(tx, current, id, false, meta, now);
      case "reset_password":
        return resetPassword(tx, config, current, id, meta, now);
      case "reset_mfa":
        return resetMfa(tx, current, id, meta, now);
      case "delete":
        return deleteUser(tx, current, id, String(form.get("confirm") ?? ""), meta, now);
      default:
        return { ok: false as const, error: "Unknown action." };
    }
  });
  revalidatePath("/admin/users");
  return { result };
}
