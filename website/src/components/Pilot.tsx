import Image from "next/image";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import soil from "../../public/images/soil-sample.webp";
import { PilotForm } from "./PilotForm";

export function Pilot({ t, lang }: { t: Dictionary; lang: Locale }) {
  return (
    <section id="pilot" aria-labelledby="pilot-title" className="bg-sage-soft">
      <div className="mx-auto grid max-w-6xl items-start gap-10 px-4 py-24 sm:px-6 lg:grid-cols-[1fr_1.4fr] lg:px-8">
        <div>
          <h2 id="pilot-title" className="font-serif text-4xl text-ink sm:text-5xl">{t.pilot.title}</h2>
          <p className="mt-4 text-ink-soft">{t.pilot.intro}</p>
          <div className="mt-8 overflow-hidden rounded-2xl">
            <Image src={soil} alt={t.pilot.imageAlt} placeholder="blur" sizes="(min-width: 1024px) 40vw, 100vw" className="h-auto w-full transition-transform duration-700 hover:scale-105" />
          </div>
        </div>
        <PilotForm t={t.pilot} privacyHref={`/${lang}/privacy`} locale={lang} />
      </div>
    </section>
  );
}
