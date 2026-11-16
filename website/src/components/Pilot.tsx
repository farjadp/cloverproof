import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { PilotForm } from "./PilotForm";

export function Pilot({ t, lang }: { t: Dictionary; lang: Locale }) {
  return (
    <section id="pilot" aria-labelledby="pilot-title" className="bg-sage-soft">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.6fr] lg:px-8">
        <div>
          <h2 id="pilot-title" className="font-serif text-3xl text-ink sm:text-4xl">{t.pilot.title}</h2>
          <p className="mt-4 text-ink-soft">{t.pilot.intro}</p>
        </div>
        <PilotForm t={t.pilot} privacyHref={`/${lang}/privacy`} />
      </div>
    </section>
  );
}
