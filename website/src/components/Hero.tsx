import type { Dictionary } from "@/i18n/dictionaries";
import { FieldArt } from "./FieldArt";

export function Hero({ t }: { t: Dictionary }) {
  return (
    <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 md:grid-cols-[1.15fr_1fr] md:py-24 lg:px-8">
      <div>
        <p className="mb-5 text-sm font-semibold uppercase tracking-[0.14em] text-olive">{t.hero.eyebrow}</p>
        <h1 className="font-serif text-4xl leading-[1.08] tracking-tight text-ink sm:text-5xl lg:text-6xl">{t.hero.title}</h1>
        <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-soft">{t.hero.lead}</p>
        <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-4">
          <a href="#pilot" className="rounded-full bg-olive px-6 py-3 font-semibold text-ivory transition-colors hover:bg-olive-deep">
            {t.hero.ctaPrimary}
          </a>
          <a href="#proof" className="group inline-flex items-center gap-2 font-semibold text-ink underline decoration-sage decoration-2 underline-offset-[6px] hover:decoration-olive">
            {t.hero.ctaSecondary}
            <span aria-hidden="true" className="transition-transform group-hover:translate-x-0.5 rtl:-scale-x-100">→</span>
          </a>
        </div>
        <p className="mt-10 border-t border-rule pt-4 text-sm text-ink-soft">{t.hero.note}</p>
      </div>
      <figure className="border border-rule bg-white p-3">
        <FieldArt />
        <figcaption className="mt-3 text-sm italic text-ink-soft">{t.hero.figureCaption}</figcaption>
      </figure>
    </section>
  );
}
