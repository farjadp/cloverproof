import "server-only";
import type en from "@/messages/en.json";
import type { Locale } from "./config";

// English is the source of truth; every other locale must match its shape.
export type Dictionary = typeof en;

const dictionaries: Partial<Record<Locale, () => Promise<Dictionary>>> = {
  en: () => import("@/messages/en.json").then((m) => m.default),
};

export async function getDictionary(locale: Locale): Promise<Dictionary> {
  const load = dictionaries[locale];
  if (!load) throw new Error(`No dictionary for locale "${locale}"`);
  return load();
}
