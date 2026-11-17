import Image from "next/image";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import soil from "../../public/images/soil-sample.webp";
import { PilotForm } from "./PilotForm";

function List({ title, items, mark }: { title: string; items: string[]; mark: string }) {
  return (
    <div>
      <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-olive">{title}</h3>
      <ul className="mt-3 space-y-2 text-ink-soft">
        {items.map((item) => (
          <li key={item} className="flex gap-3">
            <span aria-hidden="true" className="mt-0.5 font-semibold text-olive">{mark}</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Pilot({ t, lang }: { t: Dictionary; lang: Locale }) {
  const p = t.pilot;
  return (
    <section id="pilot" aria-labelledby="pilot-title" className="bg-sage-soft">
      <div className="mx-auto grid max-w-6xl items-start gap-10 px-4 py-24 sm:px-6 lg:grid-cols-[1fr_1.4fr] lg:px-8">
        <div>
          <h2 id="pilot-title" className="font-serif text-4xl text-ink sm:text-5xl">{p.title}</h2>
          <p className="mt-4 text-ink-soft">{p.intro}</p>
          <div className="mt-8 grid gap-7 sm:grid-cols-2 lg:grid-cols-1">
            <List title={p.giveTitle} items={p.give} mark="○" />
            <List title={p.getTitle} items={p.get} mark="✓" />
          </div>
          <p className="mt-7 border-s-2 border-olive ps-4 font-semibold text-ink">{p.control}</p>
          <p className="mt-2 ps-4 text-sm text-ink-soft">{p.terms}</p>
          <div className="mt-8 overflow-hidden rounded-2xl">
            <Image src={soil} alt={p.imageAlt} placeholder="blur" sizes="(min-width: 1024px) 40vw, 100vw" className="h-auto w-full transition-transform duration-700 hover:scale-105" />
          </div>
        </div>
        <div className="lg:sticky lg:top-24">
          <PilotForm t={p} privacyHref={`/${lang}/privacy`} locale={lang} />
        </div>
      </div>
    </section>
  );
}
