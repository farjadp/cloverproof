import Link from "next/link";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { Logo } from "./Logo";

/** `path` is the page under /[lang] ("" = home): the language menu stays on it. */
export function Header({ t, lang, path = "" }: { t: Dictionary; lang: Locale; path?: string }) {
  // Full paths, so these also work from pages other than the home page.
  const home = `/${lang}`;
  const links = [
    { href: `${home}#check`, label: t.nav.check },
    { href: `${home}#how`, label: t.nav.how },
    { href: `${home}#proof`, label: t.nav.proof },
    { href: `${home}#principles`, label: t.nav.principles },
    { href: `${home}#faq`, label: t.nav.faq },
  ];
  return (
    <header className="sticky top-0 z-30 border-b border-rule bg-ivory/95 backdrop-blur">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-3 focus:rounded focus:bg-olive focus:px-3 focus:py-2 focus:text-ivory">
        {t.nav.skip}
      </a>
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:gap-6 sm:px-6 lg:px-8">
        <Link href={`/${lang}`} className="shrink-0">
          <Logo className="h-8 w-auto sm:h-9" />
        </Link>
        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-7 text-[0.95rem] text-ink-soft">
            {links.map((l) => (
              <li key={l.href}>
                <a href={l.href} className="transition-colors hover:text-olive">{l.label}</a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="flex items-center gap-2 sm:gap-3">
          <LanguageSwitcher lang={lang} path={path} label={t.nav.language} comingSoon={t.footer.comingSoon} />
          <a href={`${home}#pilot`} className="whitespace-nowrap rounded-full bg-olive px-4 py-2 text-sm font-semibold text-ivory transition-colors hover:bg-olive-deep">
            {t.nav.cta}
          </a>
        </div>
      </div>
    </header>
  );
}
