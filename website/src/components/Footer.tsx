import Link from "next/link";
import type { Dictionary } from "@/i18n/dictionaries";
import { locales, localeMeta, type Locale } from "@/i18n/config";
import { Flag } from "./Flag";
import { Logo } from "./Logo";

export function Footer({ t, lang, path = "" }: { t: Dictionary; lang: Locale; path?: string }) {
  const link = "inline-flex min-h-11 items-center underline decoration-sage underline-offset-4 hover:text-sage";
  return (
    <footer className="bg-ink text-ivory">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[1.5fr_1fr_1.5fr] lg:px-8">
        <div>
          <Logo tone="white" className="h-10 w-auto" />
          <p className="mt-4 text-ivory/75">{t.footer.tagline}</p>
        </div>
        <nav aria-label={t.footer.more}>
          <ul>
            <li><Link href={`/${lang}/roadmap`} className={link}>{t.footer.roadmap}</Link></li>
            <li><Link href={`/${lang}/whats-new`} className={link}>{t.footer.whatsNew}</Link></li>
            <li><Link href={`/${lang}/privacy`} className={link}>{t.footer.privacy}</Link></li>
          </ul>
        </nav>
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-sage">{t.footer.languages}</h2>
          <ul className="mt-3 flex flex-wrap gap-2 text-sm">
            {locales.map((l) => {
              const m = localeMeta[l];
              const chip = "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-semibold uppercase";
              return (
                <li key={l}>
                  {m.enabled ? (
                    <Link href={`/${l}${path}`} lang={l} aria-current={l === lang ? "page" : undefined} className={`${chip} border-sage/60 text-ivory hover:bg-ivory/10`}>
                      <Flag locale={l} />
                      {l}
                      <span className="sr-only"> {m.label}</span>
                    </Link>
                  ) : (
                    <span lang={l} title={`${m.label} — ${t.footer.comingSoon}`} className={`${chip} border-ivory/15 text-ivory/70`}>
                      <Flag locale={l} className="h-4 w-auto opacity-60" />
                      {l}
                      <span className="sr-only"> {m.label} ({t.footer.comingSoon})</span>
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      </div>
      <div className="border-t border-ivory/15">
        <p className="mx-auto max-w-6xl px-4 py-5 text-sm text-ivory/60 sm:px-6 lg:px-8">{t.footer.rights}</p>
      </div>
    </footer>
  );
}
