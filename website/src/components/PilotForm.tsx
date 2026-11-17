"use client";

import Link from "next/link";
import { useActionState, useEffect, useRef, useState } from "react";
import { requestPilot, type PilotState } from "@/app/[lang]/actions";
import type { Dictionary } from "@/i18n/dictionaries";
import { CloverMark } from "./Logo";

type Labels = Dictionary["pilot"];

const inputClass =
  "rounded-lg border border-rule bg-white px-3 py-3 text-ink transition-shadow focus:border-olive focus:outline-none focus:ring-4 focus:ring-olive/15";

function Field({ id, label, hint, type = "text", autoComplete, requiredLabel, required = true }: {
  id: string; label: string; hint?: string; type?: string; autoComplete?: string; requiredLabel: string; required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-semibold text-ink">
        {label}
        {required && <span className="ms-1 text-olive" aria-label={requiredLabel}>*</span>}
      </label>
      <input id={id} name={id} type={type} required={required} autoComplete={autoComplete} aria-describedby={hint ? `${id}-hint` : undefined} className={inputClass} />
      {hint && <p id={`${id}-hint`} className="text-xs text-ink-soft">{hint}</p>}
    </div>
  );
}

/** Clover leaves that burst outward once, on success. */
function LeafBurst() {
  const leaves = [
    "[--dx:-120px] [--dy:-90px] [--rot:-80deg]",
    "[--dx:110px] [--dy:-110px] [--rot:70deg]",
    "[--dx:-140px] [--dy:30px] [--rot:-140deg]",
    "[--dx:150px] [--dy:20px] [--rot:120deg]",
    "[--dx:-60px] [--dy:-140px] [--rot:40deg]",
    "[--dx:60px] [--dy:-150px] [--rot:-40deg]",
    "[--dx:-90px] [--dy:90px] [--rot:200deg]",
    "[--dx:100px] [--dy:100px] [--rot:-160deg]",
  ];
  return (
    <div aria-hidden="true" className="pointer-events-none absolute start-1/2 top-16">
      {leaves.map((v, i) => (
        <span key={i} className={`absolute animate-leaf ${v} ${i % 2 ? "[animation-delay:80ms]" : ""}`}>
          <CloverMark className="h-6 w-auto" />
        </span>
      ))}
    </div>
  );
}

export function PilotForm({ t, privacyHref, locale }: { t: Labels; privacyHref: string; locale: string }) {
  const [state, action, pending] = useActionState<PilotState, FormData>(requestPilot, { status: "idle" });
  const [step, setStep] = useState(0);
  const formRef = useRef<HTMLFormElement>(null);
  const total = t.steps.length;
  // On step change, focus the first field of the new step so keyboard users don't land on <body>.
  const stepped = useRef(false);
  useEffect(() => {
    if (stepped.current) formRef.current?.querySelector<HTMLElement>(`[data-step="${step}"] input`)?.focus();
    stepped.current = true;
  }, [step]);

  // Distinct `key`s on Next/Submit stop React reusing the DOM node: otherwise the click that
  // reveals the last step lands on a node that has just become type="submit" and posts the form.
  function next(e: React.MouseEvent<HTMLButtonElement>) {
    e.preventDefault();
    const fields = formRef.current?.querySelectorAll<HTMLInputElement>(`[data-step="${step}"] input[required]`);
    for (const f of fields ?? []) {
      if (!f.reportValidity()) return;
    }
    setStep(Math.min(step + 1, total - 1));
  }

  if (state.status === "success") {
    return (
      <div className="relative grid place-items-center overflow-visible rounded-2xl border border-rule bg-ivory p-10 text-center" role="status" aria-live="polite">
        <LeafBurst />
        <div className="grid size-16 animate-pop place-items-center rounded-full bg-olive text-2xl text-ivory">✓</div>
        <h3 className="mt-5 font-serif text-3xl text-ink">{t.successTitle}</h3>
        <p className="mt-2 max-w-sm text-ink-soft">{t.successBody}</p>
      </div>
    );
  }

  const message =
    state.status === "invalid" ? t.invalid
    : state.status === "notConnected" ? t.notConnected
    : state.status === "error" ? t.error
    : null;

  return (
    <form
      ref={formRef}
      action={action}
      noValidate
      onSubmit={(e) => {
        const consent = formRef.current?.querySelector<HTMLInputElement>('input[name="consent"]');
        if (consent && !consent.reportValidity()) e.preventDefault();
      }}
      className="rounded-2xl border border-rule bg-ivory p-6 shadow-[0_24px_60px_-40px_rgba(39,49,37,0.6)] sm:p-8">
      <input type="hidden" name="locale" value={locale} />
      <div className="hidden" aria-hidden="true">
        <label htmlFor="website">Website</label>
        <input id="website" name="website" tabIndex={-1} autoComplete="off" />
      </div>

      <ol className="mb-7 grid grid-cols-3 gap-2" aria-label={t.stepOf.replace("{current}", String(step + 1)).replace("{total}", String(total))}>
        {t.steps.map((label, i) => (
          <li key={label} className="flex flex-col gap-2">
            <span className={`h-1.5 rounded-full transition-colors duration-500 ${i <= step ? "bg-olive" : "bg-rule"}`} />
            <span className={`hyphens-auto text-xs font-semibold uppercase tracking-wider wrap-anywhere ${i === step ? "text-olive" : "text-ink-soft"}`} aria-current={i === step ? "step" : undefined}>
              {label}
            </span>
          </li>
        ))}
      </ol>

      <div data-step="0" className={step === 0 ? "grid animate-pop gap-5 sm:grid-cols-2" : "hidden"}>
        <Field id="name" label={t.name} autoComplete="name" requiredLabel={t.required} />
        <Field id="email" label={t.email} type="email" autoComplete="email" requiredLabel={t.required} />
        <div className="sm:col-span-2">
          <Field id="country" label={t.country} autoComplete="country-name" requiredLabel={t.required} />
        </div>
      </div>

      <div data-step="1" className={step === 1 ? "grid animate-pop gap-5 sm:grid-cols-2" : "hidden"}>
        <Field id="farmSize" label={t.farmSize} hint={t.farmSizeHint} requiredLabel={t.required} />
        <Field id="crop" label={t.crop} requiredLabel={t.required} />
      </div>

      <div data-step="2" className={step === 2 ? "animate-pop" : "hidden"}>
        <label className="flex items-start gap-3 rounded-xl border border-rule bg-white p-4 text-sm text-ink-soft">
          <input type="checkbox" name="consent" required className="mt-1 size-5 accent-olive" />
          <span>
            {t.consent}{" "}
            <Link href={privacyHref} className="font-semibold text-olive underline underline-offset-2">{t.privacyLink}</Link>
          </span>
        </label>
      </div>

      <div className="mt-7 flex flex-wrap items-center gap-4">
        {step > 0 && (
          <button type="button" onClick={() => setStep(step - 1)} className="rounded-full px-4 py-3 font-semibold text-ink-soft hover:text-olive">
            <span aria-hidden="true" className="inline-block rtl:-scale-x-100">←</span> {t.back}
          </button>
        )}
        {step < total - 1 ? (
          <button key="next" type="button" onClick={next} className="rounded-full bg-olive px-6 py-3 font-semibold text-ivory transition-all hover:-translate-y-0.5 hover:bg-olive-deep">
            {t.next} <span aria-hidden="true" className="inline-block rtl:-scale-x-100">→</span>
          </button>
        ) : (
          <button key="submit" type="submit" disabled={pending} className="rounded-full bg-olive px-6 py-3 font-semibold text-ivory transition-all hover:-translate-y-0.5 hover:bg-olive-deep disabled:opacity-60">
            {pending ? t.submitting : t.submit}
          </button>
        )}
        <p role="status" aria-live="polite" className="text-sm text-ink-soft">{message}</p>
      </div>
    </form>
  );
}
