// Locale order is the launch order agreed in ADR 0003.
// A locale is `enabled` only after native-speaker review.
export const locales = ["en", "fr", "it", "es", "bg", "fi", "tr", "ar"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

// `flag` is a file in public/flags/ (flag-icons, MIT). English uses the UK flag, Arabic the Arab League flag.
export const localeMeta: Record<Locale, { label: string; flag: string; dir: "ltr" | "rtl"; enabled: boolean }> = {
  en: { label: "English", flag: "gb", dir: "ltr", enabled: true },
  fr: { label: "Français", flag: "fr", dir: "ltr", enabled: false },
  it: { label: "Italiano", flag: "it", dir: "ltr", enabled: false },
  es: { label: "Español", flag: "es", dir: "ltr", enabled: false },
  bg: { label: "Български", flag: "bg", dir: "ltr", enabled: false },
  fi: { label: "Suomi", flag: "fi", dir: "ltr", enabled: false },
  tr: { label: "Türkçe", flag: "tr", dir: "ltr", enabled: false },
  ar: { label: "العربية", flag: "arab", dir: "rtl", enabled: false },
};

export const enabledLocales = locales.filter((l) => localeMeta[l].enabled);

export function isEnabledLocale(value: string): value is Locale {
  return (enabledLocales as readonly string[]).includes(value);
}
