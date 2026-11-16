// Locale order is the launch order agreed in ADR 0003.
// A locale is `enabled` only after native-speaker review.
export const locales = ["en", "fr", "it", "es", "bg", "fi", "tr", "ar"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

export const localeMeta: Record<Locale, { label: string; dir: "ltr" | "rtl"; enabled: boolean }> = {
  en: { label: "English", dir: "ltr", enabled: true },
  fr: { label: "Français", dir: "ltr", enabled: false },
  it: { label: "Italiano", dir: "ltr", enabled: false },
  es: { label: "Español", dir: "ltr", enabled: false },
  bg: { label: "Български", dir: "ltr", enabled: false },
  fi: { label: "Suomi", dir: "ltr", enabled: false },
  tr: { label: "Türkçe", dir: "ltr", enabled: false },
  ar: { label: "العربية", dir: "rtl", enabled: false },
};

export const enabledLocales = locales.filter((l) => localeMeta[l].enabled);

export function isEnabledLocale(value: string): value is Locale {
  return (enabledLocales as readonly string[]).includes(value);
}
