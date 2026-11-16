"use client";

import Link from "next/link";
import { useActionState } from "react";
import { requestPilot, type PilotState } from "@/app/[lang]/actions";
import type { Dictionary } from "@/i18n/dictionaries";

type Labels = Dictionary["pilot"];

function Field({ id, label, hint, required, type = "text", autoComplete, requiredLabel }: {
  id: string; label: string; hint?: string; required?: boolean; type?: string; autoComplete?: string; requiredLabel: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-semibold text-ink">
        {label}
        {required && <span className="ms-1 text-olive" aria-label={requiredLabel}>*</span>}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        required={required}
        autoComplete={autoComplete}
        aria-describedby={hint ? `${id}-hint` : undefined}
        className="rounded-md border border-rule bg-white px-3 py-2.5 text-ink placeholder:text-ink-soft/60 focus:border-olive focus:outline-none focus:ring-2 focus:ring-olive/30"
      />
      {hint && <p id={`${id}-hint`} className="text-xs text-ink-soft">{hint}</p>}
    </div>
  );
}

export function PilotForm({ t, privacyHref, locale }: { t: Labels; privacyHref: string; locale: string }) {
  const [state, action, pending] = useActionState<PilotState, FormData>(requestPilot, { status: "idle" });
  const message =
    state.status === "success" ? t.success
    : state.status === "invalid" ? t.invalid
    : state.status === "notConnected" ? t.notConnected
    : state.status === "error" ? t.error
    : null;

  return (
    <form action={action} noValidate className="grid gap-5 border border-rule bg-ivory p-6 sm:grid-cols-2 sm:p-8">
      <Field id="name" label={t.name} required autoComplete="name" requiredLabel={t.required} />
      <Field id="email" label={t.email} type="email" required autoComplete="email" requiredLabel={t.required} />
      <Field id="country" label={t.country} required autoComplete="country-name" requiredLabel={t.required} />
      <Field id="farmSize" label={t.farmSize} hint={t.farmSizeHint} required requiredLabel={t.required} />
      <div className="sm:col-span-2">
        <Field id="crop" label={t.crop} required requiredLabel={t.required} />
      </div>
      <div className="flex flex-col gap-1.5 sm:col-span-2">
        <label htmlFor="notes" className="text-sm font-semibold text-ink">{t.notes}</label>
        <textarea id="notes" name="notes" rows={3} className="rounded-md border border-rule bg-white px-3 py-2.5 text-ink focus:border-olive focus:outline-none focus:ring-2 focus:ring-olive/30" />
      </div>
      <input type="hidden" name="locale" value={locale} />
      <div className="hidden" aria-hidden="true">
        <label htmlFor="website">Website</label>
        <input id="website" name="website" tabIndex={-1} autoComplete="off" />
      </div>
      <label className="flex items-start gap-3 text-sm text-ink-soft sm:col-span-2">
        <input type="checkbox" name="consent" required className="mt-1 size-4 accent-olive" />
        <span>
          {t.consent}{" "}
          <Link href={privacyHref} className="font-semibold text-olive underline underline-offset-2">{t.privacyLink}</Link>
        </span>
      </label>
      <div className="flex flex-wrap items-center gap-4 sm:col-span-2">
        <button
          type="submit"
          disabled={pending}
          className="rounded-full bg-olive px-6 py-3 font-semibold text-ivory transition-colors hover:bg-olive-deep disabled:opacity-60"
        >
          {pending ? t.submitting : t.submit}
        </button>
        <p role="status" aria-live="polite" className={state.status === "success" ? "text-olive" : "text-ink-soft"}>
          {message}
        </p>
      </div>
    </form>
  );
}
