/**
 * The only pilot-request fields we accept and store (data minimisation, Farjad Iranmehr 2026-11-16).
 * Free-text "notes" was removed until Canadian hosting is live; anything not listed here is ignored,
 * even if a client posts it.
 */
export const PILOT_FIELDS = ["name", "email", "country", "farmSize", "crop"] as const;
export type PilotFields = Record<(typeof PILOT_FIELDS)[number], string>;

const MAX: Record<(typeof PILOT_FIELDS)[number], number> = { name: 200, email: 320, country: 100, farmSize: 100, crop: 100 };
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type FormLike = { get(name: string): unknown };

export function readPilotRequest(form: FormLike): { ok: true; value: PilotFields } | { ok: false } {
  const value = Object.fromEntries(PILOT_FIELDS.map((k) => [k, String(form.get(k) ?? "").trim()])) as PilotFields;
  const valid = PILOT_FIELDS.every((k) => value[k] !== "" && value[k].length <= MAX[k]) && EMAIL.test(value.email);
  return valid ? { ok: true, value } : { ok: false };
}
