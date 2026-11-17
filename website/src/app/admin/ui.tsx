// Small shared admin UI pieces (Tailwind only, brand tokens from globals.css).
import Link from "next/link";

export function AuthCard({ title, children, intro }: { title: string; intro?: React.ReactNode; children: React.ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center px-4 py-10">
      <p className="mb-6 font-serif text-lg text-olive">
        CloverProof <span className="text-ink-soft">admin</span>
      </p>
      <section className="rounded-lg border border-rule bg-ivory p-6 shadow-sm sm:p-8">
        <h1 className="font-serif text-2xl text-ink">{title}</h1>
        {intro ? <div className="mt-2 text-sm leading-relaxed text-ink-soft">{intro}</div> : null}
        <div className="mt-6">{children}</div>
      </section>
    </main>
  );
}

export function Field({
  label,
  name,
  type = "text",
  autoComplete,
  inputMode,
  hint,
  required = true,
  maxLength,
  pattern,
}: {
  label: string;
  name: string;
  type?: string;
  autoComplete?: string;
  inputMode?: "numeric" | "email" | "text";
  hint?: string;
  required?: boolean;
  maxLength?: number;
  pattern?: string;
}) {
  const hintId = hint ? `${name}-hint` : undefined;
  return (
    <div className="mb-4">
      <label htmlFor={name} className="mb-1 block text-sm font-semibold text-ink">
        {label}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        required={required}
        autoComplete={autoComplete}
        inputMode={inputMode}
        maxLength={maxLength}
        pattern={pattern}
        aria-describedby={hintId}
        className="block w-full rounded-md border border-rule bg-white px-3 py-2.5 text-base text-ink focus-visible:border-olive"
      />
      {hint ? (
        <p id={hintId} className="mt-1 text-xs text-ink-soft">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function Submit({ children, pending }: { children: React.ReactNode; pending?: boolean }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="inline-flex min-h-11 w-full items-center justify-center rounded-md bg-olive px-4 py-2.5 font-semibold text-ivory transition-colors hover:bg-olive-deep disabled:opacity-70"
    >
      {children}
    </button>
  );
}

export function FormError({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="mb-4 rounded-md border border-red-800/30 bg-red-50 px-3 py-2 text-sm text-red-900">
      {message}
    </p>
  );
}

export function NotConfigured() {
  return (
    <AuthCard title="Admin not configured" intro="The admin database or keys are not set on this server yet.">
      <Link href="/en" className="text-olive underline underline-offset-4">
        Back to the website
      </Link>
    </AuthCard>
  );
}
