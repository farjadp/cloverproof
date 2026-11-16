"use server";

import { isEnabledLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/dictionaries";
import { getDb } from "@/lib/db";
import { safeError } from "@/lib/safe-error";

export type PilotState = { status: "idle" | "success" | "invalid" | "notConnected" | "error" };

const REQUIRED = ["name", "email", "country", "farmSize", "crop"] as const;
const MAX = { name: 200, email: 320, country: 100, farmSize: 100, crop: 100, notes: 2000 } as const;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const read = (formData: FormData, key: string) => String(formData.get(key) ?? "").trim();

export async function requestPilot(_prev: PilotState, formData: FormData): Promise<PilotState> {
  // Honeypot: real users never fill the hidden "website" field.
  if (read(formData, "website") !== "") return { status: "success" };

  const locale = read(formData, "locale");
  const v = {
    name: read(formData, "name"),
    email: read(formData, "email"),
    country: read(formData, "country"),
    farmSize: read(formData, "farmSize"),
    crop: read(formData, "crop"),
    notes: read(formData, "notes"),
  };
  const consent = formData.get("consent") === "on";

  const tooLong = (Object.keys(MAX) as (keyof typeof MAX)[]).some((k) => v[k].length > MAX[k]);
  if (!isEnabledLocale(locale) || !consent || tooLong || REQUIRED.some((k) => !v[k]) || !EMAIL.test(v.email)) {
    return { status: "invalid" };
  }

  const db = getDb();
  if (!db) return { status: "notConnected" };

  try {
    const t = await getDictionary(locale);
    await db.query(
      `insert into pilot_request
         (locale, full_name, email, country, farm_size_text, main_crop, notes, consent_at, consent_text)
       values ($1, $2, $3, $4, $5, $6, $7, now(), $8)`,
      [locale, v.name, v.email, v.country, v.farmSize, v.crop, v.notes || null, t.pilot.consent],
    );
    return { status: "success" };
  } catch (error) {
    // Never log the raw error: pg errors can carry the submitted name/email.
    console.error("requestPilot failed", safeError(error));
    return { status: "error" };
  }
}
