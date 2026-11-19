"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { locales, localeMeta, type Locale } from "@/i18n/config";
import { Flag } from "./Flag";

/** Header language menu: flags + language code; native names stay as accessible labels. */
export function LanguageSwitcher({ lang, path = "", label, comingSoon }: { lang: Locale; path?: string; label: string; comingSoon: string }) {
  const ref = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    const close = (e: Event) => {
      const el = ref.current;
      if (!el?.open) return;
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !el.contains(e.target as Node)) {
        el.open = false;
        if (e instanceof KeyboardEvent) el.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("click", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("click", close);
      document.removeEventListener("keydown", close);
    };
  }, []);

  return (
    <details ref={ref} className="group relative">
      <summary
        className="flex cursor-pointer list-none items-center gap-1.5 rounded-full px-2 py-1.5 text-sm font-semibold text-ink-soft transition-colors hover:bg-sand hover:text-ink [&::-webkit-details-marker]:hidden"
      >
        <Flag locale={lang} className="h-4 w-auto" />
        <span className="hidden uppercase sm:inline">{lang}</span>
        <span className="sr-only">
          {label}: {localeMeta[lang].label}
        </span>
        <span aria-hidden="true" className="text-xs transition-transform group-open:rotate-180">▾</span>
      </summary>
      <ul className="absolute end-0 top-full z-40 mt-2 grid w-44 gap-0.5 rounded-xl border border-rule bg-ivory p-1.5 shadow-[0_18px_40px_-20px_rgba(39,49,37,0.45)]">
        {locales.map((l) => {
          const m = localeMeta[l];
          const inner = (
            <>
              <Flag locale={l} className="h-4 w-auto" />
              <span className="uppercase">{l}</span>
              <span lang={l} dir={m.dir} className="truncate text-ink-soft">{m.label}</span>
            </>
          );
          return (
            <li key={l}>
              {m.enabled ? (
                <Link
                  href={`/${l}${path}`}
                  lang={l}
                  aria-current={l === lang ? "page" : undefined}
                  className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-semibold text-ink hover:bg-sand aria-[current=page]:bg-sage-soft"
                >
                  {inner}
                </Link>
              ) : (
                <span title={comingSoon} aria-disabled="true" className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-semibold text-ink opacity-45">
                  {inner}
                  <span className="sr-only">({comingSoon})</span>
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </details>
  );
}
