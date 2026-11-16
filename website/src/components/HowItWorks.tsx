import type { Dictionary } from "@/i18n/dictionaries";

export function HowItWorks({ t }: { t: Dictionary }) {
  return (
    <section id="how" aria-labelledby="how-title" className="bg-ink text-ivory">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <h2 id="how-title" className="font-serif text-3xl sm:text-4xl">{t.how.title}</h2>
          <p className="mt-4 text-ivory/80">{t.how.intro}</p>
        </div>
        <ol className="mt-12 grid gap-px overflow-hidden border border-ivory/15 bg-ivory/15 sm:grid-cols-2 lg:grid-cols-4">
          {t.how.steps.map((step, i) => (
            <li key={step.title} className={i === 2 ? "bg-olive p-6" : "bg-ink p-6"}>
              <span className="text-sm font-semibold uppercase tracking-[0.14em] text-sage">{String(i + 1).padStart(2, "0")}</span>
              <h3 className="mt-3 font-serif text-xl">{step.title}</h3>
              <p className="mt-2 text-ivory/80">{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
