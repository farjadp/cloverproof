import Link from "next/link";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { Logo } from "./Logo";

export function Header({ t, lang }: { t: Dictionary; lang: Locale }) {
  const links = [
    { href: "#how", label: t.nav.how },
    { href: "#proof", label: t.nav.proof },
    { href: "#principles", label: t.nav.principles },
    { href: "#faq", label: t.nav.faq },
  ];
  return (
    <header className="sticky top-0 z-30 border-b border-rule bg-ivory/95 backdrop-blur">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-3 focus:rounded focus:bg-olive focus:px-3 focus:py-2 focus:text-ivory">
        {t.nav.skip}
      </a>
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-6 px-4 sm:px-6 lg:px-8">
        <Link href={`/${lang}`} aria-label="CloverProof">
          <Logo name="CloverProof" />
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
        <a href="#pilot" className="rounded-full bg-olive px-4 py-2 text-sm font-semibold text-ivory transition-colors hover:bg-olive-deep">
          {t.nav.cta}
        </a>
      </div>
    </header>
  );
}
