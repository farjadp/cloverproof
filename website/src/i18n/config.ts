// Locale order is the launch order agreed in ADR 0003.
// All locales enabled with machine translation (Farjad Iranmehr, 2026-11-16, ADR 0003 amendment);
// native review status per locale lives in each file's `meta.translationStatus`.
export const locales = ["en", "fr", "it", "es", "bg", "fi", "tr", "ar"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

// `flag` is a file in public/flags/ (flag-icons, MIT). English uses the UK flag, Arabic the Arab League flag.
export const localeMeta: Record<Locale, { label: string; flag: string; dir: "ltr" | "rtl"; enabled: boolean }> = {
  en: { label: "English", flag: "gb", dir: "ltr", enabled: true },
  fr: { label: "Français", flag: "fr", dir: "ltr", enabled: true },
  it: { label: "Italiano", flag: "it", dir: "ltr", enabled: true },
  es: { label: "Español", flag: "es", dir: "ltr", enabled: true },
  bg: { label: "Български", flag: "bg", dir: "ltr", enabled: true },
  fi: { label: "Suomi", flag: "fi", dir: "ltr", enabled: true },
  tr: { label: "Türkçe", flag: "tr", dir: "ltr", enabled: true },
  ar: { label: "العربية", flag: "arab", dir: "rtl", enabled: true },
};

export const enabledLocales = locales.filter((l) => localeMeta[l].enabled);

export function isEnabledLocale(value: string): value is Locale {
  return (enabledLocales as readonly string[]).includes(value);
}
