import "server-only";
import type en from "@/messages/en.json";
import type { Locale } from "./config";

// English is the source of truth; every other locale must match its shape.
export type Dictionary = typeof en;

// Key parity with en.json is enforced by `npm test` (tests/messages.test.ts).
const dictionaries: Record<Locale, () => Promise<Dictionary>> = {
  en: () => import("@/messages/en.json").then((m) => m.default),
  fr: () => import("@/messages/fr.json").then((m) => m.default as Dictionary),
  it: () => import("@/messages/it.json").then((m) => m.default as Dictionary),
  es: () => import("@/messages/es.json").then((m) => m.default as Dictionary),
  bg: () => import("@/messages/bg.json").then((m) => m.default as Dictionary),
  fi: () => import("@/messages/fi.json").then((m) => m.default as Dictionary),
  tr: () => import("@/messages/tr.json").then((m) => m.default as Dictionary),
  ar: () => import("@/messages/ar.json").then((m) => m.default as Dictionary),
  he: () => import("@/messages/he.json").then((m) => m.default as Dictionary),
};

export async function getDictionary(locale: Locale): Promise<Dictionary> {
  const load = dictionaries[locale];
  if (!load) throw new Error(`No dictionary for locale "${locale}"`);
  return load();
}
