"use client";

import Link from "next/link";
import { useActionState } from "react";
import { stepUpAction, type StepUpState } from "./step-up";
import { Field, FormError, Submit } from "./ui";

export function StepUpForm({ csrf, path, what, enrolled }: { csrf: string; path: string; what: string; enrolled: boolean }) {
  const [state, action, pending] = useActionState<StepUpState, FormData>(stepUpAction, { error: null });
  if (!enrolled) {
    return (
      <section aria-labelledby="step-up-title" className="max-w-md rounded-lg border border-rule bg-ivory p-6">
        <h2 id="step-up-title" className="font-serif text-xl text-ink">
          Two-step sign-in needed
        </h2>
        <p className="mt-1 mb-4 text-sm text-ink-soft">You need two-step sign-in on your account to {what}. It takes about a minute.</p>
        <Link
          href="/admin/mfa"
          className="inline-flex min-h-11 w-full items-center justify-center rounded-md bg-olive px-4 py-2.5 font-semibold text-ivory hover:bg-olive-deep"
        >
          Set up two-step sign-in
        </Link>
      </section>
    );
  }
  return (
    <section aria-labelledby="step-up-title" className="max-w-md rounded-lg border border-rule bg-ivory p-6">
      <h2 id="step-up-title" className="font-serif text-xl text-ink">
        Confirm it&apos;s you
      </h2>
      <p className="mt-1 mb-4 text-sm text-ink-soft">
        Enter a code from your authenticator app to {what}. You won&apos;t be asked again for 5 minutes.
      </p>
      <form action={action}>
        <input type="hidden" name="csrf" value={csrf} />
        <input type="hidden" name="path" value={path} />
        <FormError message={state.error} />
        <Field label="6-digit code" name="code" inputMode="numeric" autoComplete="one-time-code" maxLength={7} pattern="[0-9 ]{6,7}" />
        <Submit pending={pending}>{pending ? "Checking…" : "Confirm"}</Submit>
      </form>
    </section>
  );
}
