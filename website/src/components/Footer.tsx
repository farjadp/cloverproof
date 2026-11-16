import Link from "next/link";
import type { Dictionary } from "@/i18n/dictionaries";
import { locales, localeMeta, type Locale } from "@/i18n/config";
import { Flag } from "./Flag";
import { Logo } from "./Logo";

export function Footer({ t, lang }: { t: Dictionary; lang: Locale }) {
  return (
    <footer className="bg-ink text-ivory">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[1.5fr_1fr_1.5fr] lg:px-8">
        <div>
          <Logo tone="white" className="h-10 w-auto" />
          <p className="mt-4 text-ivory/75">{t.footer.tagline}</p>
        </div>
        <nav aria-label="Legal">
          <Link href={`/${lang}/privacy`} className="underline decoration-sage underline-offset-4 hover:text-sage">
            {t.footer.privacy}
          </Link>
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
                    <Link href={`/${l}`} lang={l} aria-label={m.label} aria-current={l === lang ? "page" : undefined} className={`${chip} border-sage/60 text-ivory hover:bg-ivory/10`}>
                      <Flag locale={l} />
                      {l}
                    </Link>
                  ) : (
                    <span lang={l} aria-label={`${m.label} (${t.footer.comingSoon})`} title={`${m.label} — ${t.footer.comingSoon}`} className={`${chip} border-ivory/15 text-ivory/50`}>
                      <Flag locale={l} className="h-4 w-auto opacity-60" />
                      {l}
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
