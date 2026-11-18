"use client";

import Link from "next/link";
import { useActionState, useState } from "react";
import { mfaAction, type MfaState } from "./actions";
import { Field, FormError, Submit } from "../ui";

export function MfaForm({ csrf, enrolling, optional }: { csrf: string; enrolling: boolean; optional: boolean }) {
  const [state, action, pending] = useActionState<MfaState, FormData>(mfaAction, { error: null });
  const [recovery, setRecovery] = useState(false);

  if (state.done && state.recoveryCodes) {
    return (
      <div>
        <h2 className="font-serif text-xl text-ink">Save your recovery codes</h2>
        <p className="mt-2 text-sm text-ink-soft">
          Each code works once if you lose your phone. They are shown only now. Store them in your password manager.
        </p>
        <ul className="mt-4 grid grid-cols-2 gap-2 font-mono text-sm" aria-label="Recovery codes">
          {state.recoveryCodes.map((c) => (
            <li key={c} className="rounded border border-rule bg-white px-2 py-1 text-center">
              {c}
            </li>
          ))}
        </ul>
        <Link
          href="/admin"
          className="mt-6 inline-flex min-h-11 w-full items-center justify-center rounded-md bg-olive px-4 py-2.5 font-semibold text-ivory hover:bg-olive-deep"
        >
          I saved them — continue
        </Link>
      </div>
    );
  }
  if (state.done) {
    return (
      <Link
        href="/admin"
        className="inline-flex min-h-11 w-full items-center justify-center rounded-md bg-olive px-4 py-2.5 font-semibold text-ivory hover:bg-olive-deep"
      >
        Continue
      </Link>
    );
  }
  return (
    <form action={action}>
      <input type="hidden" name="csrf" value={csrf} />
      <input type="hidden" name="mode" value={recovery ? "recovery" : "totp"} />
      <FormError message={state.error} />
      {recovery ? (
        <Field label="Recovery code" name="code" autoComplete="off" maxLength={20} hint="Format XXXXX-XXXXX. Each code works once." />
      ) : (
        <Field
          label="6-digit code from your authenticator app"
          name="code"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={7}
          pattern="[0-9 ]{6,7}"
        />
      )}
      <Submit pending={pending}>{pending ? "Checking…" : enrolling ? "Turn on two-step sign-in" : "Verify"}</Submit>
      {!enrolling ? (
        <button
          type="button"
          onClick={() => setRecovery((r) => !r)}
          className="mt-4 min-h-11 w-full text-sm text-olive underline underline-offset-4"
        >
          {recovery ? "Use the authenticator app instead" : "Use a recovery code instead"}
        </button>
      ) : null}
      {optional ? (
        <Link href="/admin" className="mt-4 inline-flex min-h-11 w-full items-center justify-center text-sm text-olive underline underline-offset-4">
          Not now
        </Link>
      ) : null}
    </form>
  );
}
