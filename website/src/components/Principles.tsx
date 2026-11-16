import type { Dictionary } from "@/i18n/dictionaries";
import { Reveal } from "./Reveal";

export function Principles({ t }: { t: Dictionary }) {
  return (
    <section id="principles" aria-labelledby="principles-title" className="bg-sand">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:px-8">
        <h2 id="principles-title" className="font-serif text-3xl text-ink sm:text-4xl">{t.principles.title}</h2>
        <ul className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
          {t.principles.items.map((item, i) => (
            <li key={item.title}>
              <Reveal delay={(i % 3) as 0 | 1 | 2} className="group h-full rounded-xl border-t-4 border-olive bg-ivory p-6 transition-all hover:-translate-y-1 hover:shadow-lg">
              <h3 className="font-serif text-xl text-ink">{item.title}</h3>
              <p className="mt-2 text-ink-soft">{item.body}</p>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
