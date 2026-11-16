import type { Dictionary } from "@/i18n/dictionaries";

export function Problem({ t }: { t: Dictionary }) {
  return (
    <section aria-labelledby="problem-title" className="border-t border-rule">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 md:grid-cols-[1fr_2fr] lg:px-8">
        <div>
          <h2 id="problem-title" className="font-serif text-3xl text-ink sm:text-4xl">{t.problem.title}</h2>
          <p className="mt-4 text-ink-soft">{t.problem.intro}</p>
        </div>
        <ol className="divide-y divide-rule border-y border-rule">
          {t.problem.items.map((item, i) => (
            <li key={item.title} className="grid grid-cols-[3rem_1fr] gap-4 py-6">
              <span className="font-serif text-lg text-olive" aria-hidden="true">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <h3 className="font-semibold text-ink">{item.title}</h3>
                <p className="mt-1 text-ink-soft">{item.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
