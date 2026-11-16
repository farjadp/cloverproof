import type { Dictionary } from "@/i18n/dictionaries";

export function Faq({ t }: { t: Dictionary }) {
  return (
    <section id="faq" aria-labelledby="faq-title" className="border-t border-rule">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 md:grid-cols-[1fr_2fr] lg:px-8">
        <h2 id="faq-title" className="font-serif text-3xl text-ink sm:text-4xl">{t.faq.title}</h2>
        <div className="divide-y divide-rule border-y border-rule">
          {t.faq.items.map((item) => (
            <details key={item.q} className="group py-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-ink marker:hidden">
                {item.q}
                <span aria-hidden="true" className="text-xl text-olive transition-transform group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 max-w-2xl text-ink-soft">{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
