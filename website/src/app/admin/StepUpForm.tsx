"use client";

import { useActionState } from "react";
import { stepUpAction, type StepUpState } from "./step-up";
import { Field, FormError, Submit } from "./ui";

export function StepUpForm({ csrf, path, what }: { csrf: string; path: string; what: string }) {
  const [state, action, pending] = useActionState<StepUpState, FormData>(stepUpAction, { error: null });
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
