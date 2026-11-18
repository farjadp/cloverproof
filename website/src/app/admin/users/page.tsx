import type { Metadata } from "next";
import { adminDb, adminReady, csrfField, requirePage, stepUpFresh } from "@/lib/admin/server";
import { listUsers } from "@/lib/admin/users";
import { AdminShell } from "../shell";
import { StepUpForm } from "../StepUpForm";
import { NotConfigured } from "../ui";
import { InviteForm, UserActions } from "./UserForms";

export const metadata: Metadata = { title: "Users" };

const STATUS: Record<string, string> = {
  active: "bg-sage-soft text-ink",
  invited: "bg-sand text-ink",
  locked: "bg-red-50 text-red-900",
  disabled: "bg-rule text-ink-soft",
};

function when(date: Date | null): string {
  return date ? new Date(date).toISOString().slice(0, 16).replace("T", " ") + " UTC" : "never";
}

export default async function UsersPage() {
  if (!adminReady()) return <NotConfigured />;
  const current = await requirePage("users.manage");
  const csrf = await csrfField();
  const fresh = stepUpFresh(current);
  const users = await listUsers(adminDb()!, new Date());
  return (
    <AdminShell current={current} csrf={csrf} active="/admin/users">
      <h1 className="font-serif text-3xl text-ink">Users</h1>
      <p className="mt-1 mb-6 text-ink-soft">Website staff accounts. Every change is recorded in the system log.</p>
      {!fresh ? (
        <StepUpForm enrolled={Boolean(current.user.mfa_enabled_at)} csrf={csrf} path="/admin/users" what="manage users" />
      ) : (
        <div className="grid gap-8 lg:grid-cols-[1fr_22rem]">
          <ul className="space-y-4" aria-label="Users">
            {users.map((u) => (
              <li key={u.id} className="rounded-lg border border-rule bg-ivory p-4">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <h2 className="font-semibold text-ink">
                    {u.display_name}
                    {u.id === current.user.id ? <span className="font-normal text-ink-soft"> (you)</span> : null}
                  </h2>
                  <span className="break-all text-sm text-ink-soft">{u.email}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS[u.status]}`}>{u.status}</span>
                </div>
                <p className="mt-1 text-xs text-ink-soft">
                  {u.role} · two-step sign-in {u.mfa ? "on" : "not set up"} · last sign-in {when(u.last_sign_in)}
                </p>
                <UserActions csrf={csrf} user={{ ...u, self: u.id === current.user.id }} />
              </li>
            ))}
          </ul>
          <InviteForm csrf={csrf} />
        </div>
      )}
    </AdminShell>
  );
}
