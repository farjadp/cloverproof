"use client";

import Link from "next/link";
import { useActionState, useSyncExternalStore } from "react";
import { setupAction, type SetupState } from "./actions";
import { Field, FormError, Submit } from "../ui";

// The token travels in the URL fragment (#…), which browsers never send to the server,
// so it can't end up in access logs or Referer headers.
const subscribe = () => () => {};
const readFragment = () => window.location.hash.slice(1);

export function SetupForm({ pre }: { pre: string }) {
  const token = useSyncExternalStore(subscribe, readFragment, () => "");
  const [state, action, pending] = useActionState<SetupState, FormData>(setupAction, { error: null });

  if (state.done) {
    return (
      <div>
        <p role="status" className="mb-6 text-ink">
          Password saved. Sign in to set up two-step sign-in.
        </p>
        <Link
          href="/admin/login"
          className="inline-flex min-h-11 w-full items-center justify-center rounded-md bg-olive px-4 py-2.5 font-semibold text-ivory hover:bg-olive-deep"
        >
          Go to sign-in
        </Link>
      </div>
    );
  }
  return (
    <form action={action}>
      <input type="hidden" name="pre" value={pre} />
      <input type="hidden" name="token" value={token} />
      <FormError message={state.error ?? (token ? null : "This link is incomplete. Open the full link you were given.")} />
      <Field
        label="New password"
        name="password"
        type="password"
        autoComplete="new-password"
        maxLength={128}
        hint="At least 12 characters. A passphrase of several words works well."
      />
      <Field label="Repeat the password" name="confirm" type="password" autoComplete="new-password" maxLength={128} />
      <Submit pending={pending || !token}>{pending ? "Saving…" : "Save password"}</Submit>
    </form>
  );
}
