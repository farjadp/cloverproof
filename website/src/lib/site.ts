import { defaultLocale, enabledLocales, type Locale } from "@/i18n/config";

/**
 * Public base URL for canonical, hreflang, sitemap and Open Graph links.
 * SITE_URL wins (custom domain later); Railway sets RAILWAY_PUBLIC_DOMAIN at build and run time.
 */
export const siteUrl =
  process.env.SITE_URL ??
  (process.env.RAILWAY_PUBLIC_DOMAIN ? `https://${process.env.RAILWAY_PUBLIC_DOMAIN}` : "http://localhost:3000");

/** hreflang map for a path under /[lang] (path "" = home), plus x-default. */
export function languageAlternates(path = ""): Record<string, string> {
  return {
    ...Object.fromEntries(enabledLocales.map((l: Locale) => [l, `/${l}${path}`])),
    "x-default": `/${defaultLocale}${path}`,
  };
}

/** Open Graph locale tag, e.g. en -> en_GB. */
export const ogLocale: Record<Locale, string> = {
  en: "en_GB", fr: "fr_FR", it: "it_IT", es: "es_ES", bg: "bg_BG", fi: "fi_FI", tr: "tr_TR", ar: "ar_AR",
};
