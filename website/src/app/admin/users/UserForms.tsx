"use client";

import { useActionState, useState } from "react";
import { userAction, type UserActionState } from "./actions";
import { Field, FormError, Submit } from "../ui";

const ROLES = [
  { value: "author", label: "Author — writes drafts" },
  { value: "editor", label: "Editor — edits and publishes posts" },
  { value: "admin", label: "Admin — users, log, keys, everything" },
];

function ResultBox({ state }: { state: UserActionState }) {
  const [copied, setCopied] = useState(false);
  if (!state.result) return null;
  if (!state.result.ok) return <FormError message={state.result.error} />;
  const { message, link } = state.result;
  return (
    <div role="status" className="mb-4 rounded-md border border-sage bg-sage-soft px-3 py-2 text-sm text-ink">
      <p>{message}</p>
      {link ? (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <code className="min-w-0 flex-1 break-all rounded bg-white px-2 py-1 text-xs">{link}</code>
          <button
            type="button"
            onClick={() => navigator.clipboard.writeText(link).then(() => setCopied(true))}
            className="min-h-11 rounded-md border border-olive px-3 text-olive"
          >
            {copied ? "Copied" : "Copy link"}
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function InviteForm({ csrf }: { csrf: string }) {
  const [state, action, pending] = useActionState<UserActionState, FormData>(userAction, { result: null });
  return (
    <form action={action} className="rounded-lg border border-rule bg-ivory p-5">
      <h2 className="mb-4 font-serif text-xl text-ink">Invite a user</h2>
      <input type="hidden" name="csrf" value={csrf} />
      <input type="hidden" name="op" value="invite" />
      <ResultBox state={state} />
      <Field label="Name" name="name" autoComplete="off" maxLength={120} />
      <Field label="E-mail" name="email" type="email" autoComplete="off" inputMode="email" maxLength={320} />
      <div className="mb-4">
        <label htmlFor="invite-role" className="mb-1 block text-sm font-semibold text-ink">
          Role
        </label>
        <select id="invite-role" name="role" defaultValue="author" className="block min-h-11 w-full rounded-md border border-rule bg-white px-3 text-base">
          {ROLES.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </div>
      <Submit pending={pending}>{pending ? "Creating…" : "Create invite link"}</Submit>
      <p className="mt-2 text-xs text-ink-soft">No e-mail is sent. You get a one-time link to pass on yourself.</p>
    </form>
  );
}

type Row = { id: string; email: string | null; display_name: string; role: string; status: string; self: boolean };

export function UserActions({ csrf, user }: { csrf: string; user: Row }) {
  const [state, action, pending] = useActionState<UserActionState, FormData>(userAction, { result: null });
  const [confirmDelete, setConfirmDelete] = useState(false);
  const button = "min-h-11 rounded-md border px-3 text-sm disabled:opacity-60";
  return (
    <div className="mt-3">
      <ResultBox state={state} />
      <div className="flex flex-wrap items-end gap-2">
        <form action={action} className="flex items-end gap-2">
          <input type="hidden" name="csrf" value={csrf} />
          <input type="hidden" name="id" value={user.id} />
          <input type="hidden" name="op" value="role" />
          <div>
            <label htmlFor={`role-${user.id}`} className="block text-xs font-semibold text-ink-soft">
              Role
            </label>
            <select id={`role-${user.id}`} name="role" defaultValue={user.role} className="min-h-11 rounded-md border border-rule bg-white px-2 text-sm">
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.value}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={pending} className={`${button} border-olive text-olive`}>
            Save role
          </button>
        </form>
        {!user.self ? (
          <form action={action}>
            <input type="hidden" name="csrf" value={csrf} />
            <input type="hidden" name="id" value={user.id} />
            <input type="hidden" name="op" value={user.status === "disabled" ? "enable" : "disable"} />
            <button type="submit" disabled={pending} className={`${button} border-rule text-ink`}>
              {user.status === "disabled" ? "Enable" : "Disable"}
            </button>
          </form>
        ) : null}
        {user.status !== "disabled" ? (
          <form action={action}>
            <input type="hidden" name="csrf" value={csrf} />
            <input type="hidden" name="id" value={user.id} />
            <input type="hidden" name="op" value="reset_password" />
            <button type="submit" disabled={pending} className={`${button} border-rule text-ink`}>
              {user.status === "invited" ? "New invite link" : "Password reset link"}
            </button>
          </form>
        ) : null}
        {!user.self && user.status !== "invited" ? (
          <form action={action}>
            <input type="hidden" name="csrf" value={csrf} />
            <input type="hidden" name="id" value={user.id} />
            <input type="hidden" name="op" value="reset_mfa" />
            <button type="submit" disabled={pending} className={`${button} border-rule text-ink`}>
              Reset two-step sign-in
            </button>
          </form>
        ) : null}
        {!user.self ? (
          <button type="button" onClick={() => setConfirmDelete((v) => !v)} className={`${button} border-red-800/40 text-red-900`} aria-expanded={confirmDelete}>
            Delete…
          </button>
        ) : null}
      </div>
      {confirmDelete && !user.self ? (
        <form action={action} className="mt-3 rounded-md border border-red-800/30 bg-red-50 p-3">
          <input type="hidden" name="csrf" value={csrf} />
          <input type="hidden" name="id" value={user.id} />
          <input type="hidden" name="op" value="delete" />
          <p className="mb-2 text-sm text-red-900">
            Deleting removes the e-mail, password and two-step sign-in. The name stays in the history. This can&apos;t be undone.
          </p>
          <label htmlFor={`confirm-${user.id}`} className="mb-1 block text-xs font-semibold text-ink">
            Type {user.email} to confirm
          </label>
          <div className="flex flex-wrap gap-2">
            <input id={`confirm-${user.id}`} name="confirm" type="email" autoComplete="off" required className="min-h-11 min-w-0 flex-1 rounded-md border border-rule bg-white px-3 text-sm" />
            <button type="submit" disabled={pending} className={`${button} border-red-900 bg-red-900 text-white`}>
              Delete user
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
