import type { Dictionary } from "@/i18n/dictionaries";

export function Principles({ t }: { t: Dictionary }) {
  return (
    <section id="principles" aria-labelledby="principles-title" className="bg-sand">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:px-8">
        <h2 id="principles-title" className="font-serif text-3xl text-ink sm:text-4xl">{t.principles.title}</h2>
        <ul className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
          {t.principles.items.map((item) => (
            <li key={item.title} className="border-t-2 border-olive pt-4">
              <h3 className="font-serif text-xl text-ink">{item.title}</h3>
              <p className="mt-2 text-ink-soft">{item.body}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
