"use client";

import { useActionState, useState } from "react";
import { keyAction, type KeyState } from "./actions";
import { FormError } from "../ui";

type Info = {
  provider: string;
  label: string;
  hint: string;
  active: { last4: string; version: number; created_at: string; created_by: string; budget: string | null; tested: string | null; testOk: boolean | null } | null;
};

const button = "min-h-11 rounded-md border px-3 text-sm font-semibold disabled:opacity-60";

export function KeyCard({ csrf, info }: { csrf: string; info: Info }) {
  // Each form gets its own state so results show next to the control that caused them.
  const [state, action, pending] = useActionState<KeyState, FormData>(keyAction, { result: null });
  const [replacing, setReplacing] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const hidden = (op: string) => (
    <>
      <input type="hidden" name="csrf" value={csrf} />
      <input type="hidden" name="provider" value={info.provider} />
      <input type="hidden" name="op" value={op} />
    </>
  );
  const { active } = info;
  return (
    <li className="rounded-lg border border-rule bg-ivory p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-serif text-xl text-ink">{info.label}</h2>
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${active ? "bg-sage-soft text-ink" : "bg-sand text-ink-soft"}`}>
          {active ? "Key saved" : "No key"}
        </span>
      </div>
      {active ? (
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-ink-soft">Key</dt>
          <dd className="font-mono text-ink">•••• {active.last4}</dd>
          <dt className="text-ink-soft">Added</dt>
          <dd className="text-ink">
            {active.created_at} by {active.created_by} (version {active.version})
          </dd>
          <dt className="text-ink-soft">Last test</dt>
          <dd className="text-ink">{active.tested ? `${active.tested} — ${active.testOk ? "passed" : "failed"}` : "not tested"}</dd>
          <dt className="text-ink-soft">Monthly cap</dt>
          <dd className="text-ink">{active.budget ? `$${active.budget}` : "none"}</dd>
        </dl>
      ) : (
        <p className="mt-2 text-sm text-ink-soft">Nothing stored. Keys are encrypted and can never be read back here.</p>
      )}

      <div className="mt-4" aria-live="polite">
        {state.result && !state.result.ok ? <FormError message={state.result.error} /> : null}
        {state.result?.ok ? (
          <p role="status" className="mb-4 rounded-md border border-sage bg-sage-soft px-3 py-2 text-sm text-ink">
            {state.result.message}
          </p>
        ) : null}
      </div>

      {!active || replacing ? (
        <form action={action} className="mt-2" autoComplete="off">
          {hidden("save")}
          <label htmlFor={`key-${info.provider}`} className="mb-1 block text-sm font-semibold text-ink">
            {active ? "New key" : "API key"}
          </label>
          <div className="flex flex-wrap gap-2">
            <input
              id={`key-${info.provider}`}
              name="key"
              type="password"
              autoComplete="off"
              spellCheck={false}
              maxLength={400}
              required
              aria-describedby={`hint-${info.provider}`}
              className="min-h-11 min-w-0 flex-1 rounded-md border border-rule bg-white px-3 font-mono text-sm"
            />
            <button type="submit" disabled={pending} className={`${button} border-olive bg-olive text-ivory`}>
              Save key
            </button>
          </div>
          <p id={`hint-${info.provider}`} className="mt-1 text-xs text-ink-soft">
            {info.hint}. After saving only the last 4 characters are shown.
          </p>
        </form>
      ) : (
        <div className="mt-2 flex flex-wrap gap-2">
          <form action={action}>
            {hidden("test")}
            <button type="submit" disabled={pending} className={`${button} border-olive text-olive`}>
              {pending ? "Working…" : "Test connection"}
            </button>
          </form>
          <button type="button" onClick={() => setReplacing(true)} className={`${button} border-rule text-ink`}>
            Replace key
          </button>
          <button type="button" onClick={() => setConfirmRemove((v) => !v)} aria-expanded={confirmRemove} className={`${button} border-red-800/40 text-red-900`}>
            Remove…
          </button>
        </div>
      )}

      {active && confirmRemove ? (
        <form action={action} className="mt-3 rounded-md border border-red-800/30 bg-red-50 p-3">
          {hidden("revoke")}
          <p className="mb-2 text-sm text-red-900">The key is removed here (its record stays in the history). Also revoke it in the provider&apos;s console.</p>
          <button type="submit" disabled={pending} className={`${button} border-red-900 bg-red-900 text-white`}>
            Remove key
          </button>
        </form>
      ) : null}

      {active ? (
        <form action={action} className="mt-4 flex flex-wrap items-end gap-2">
          {hidden("budget")}
          <div>
            <label htmlFor={`budget-${info.provider}`} className="mb-1 block text-xs font-semibold text-ink-soft">
              Monthly cap (USD, for future agents)
            </label>
            <input
              id={`budget-${info.provider}`}
              name="budget"
              inputMode="decimal"
              defaultValue={active.budget ?? ""}
              placeholder="none"
              className="min-h-11 w-32 rounded-md border border-rule bg-white px-3 text-sm"
            />
          </div>
          <button type="submit" disabled={pending} className={`${button} border-rule text-ink`}>
            Save cap
          </button>
        </form>
      ) : null}
    </li>
  );
}
