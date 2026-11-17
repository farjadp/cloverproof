"use server";

import { isEnabledLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/dictionaries";
import { getDb } from "@/lib/db";
import { readPilotRequest } from "@/lib/pilot-request";
import { safeError } from "@/lib/safe-error";

export type PilotState = { status: "idle" | "success" | "invalid" | "notConnected" | "error" };

const read = (formData: FormData, key: string) => String(formData.get(key) ?? "").trim();

export async function requestPilot(_prev: PilotState, formData: FormData): Promise<PilotState> {
  // Honeypot: real users never fill the hidden "website" field.
  if (read(formData, "website") !== "") return { status: "success" };

  const locale = read(formData, "locale");
  const consent = formData.get("consent") === "on";
  // Only whitelisted fields are read; free-text notes are no longer collected or stored.
  const parsed = readPilotRequest(formData);
  if (!isEnabledLocale(locale) || !consent || !parsed.ok) {
    return { status: "invalid" };
  }
  const v = parsed.value;

  const db = getDb();
  if (!db) return { status: "notConnected" };

  try {
    const t = await getDictionary(locale);
    await db.query(
      `insert into pilot_request
         (locale, full_name, email, country, farm_size_text, main_crop, consent_at, consent_text)
       values ($1, $2, $3, $4, $5, $6, now(), $7)`,
      [locale, v.name, v.email, v.country, v.farmSize, v.crop, t.pilot.consent],
    );
    return { status: "success" };
  } catch (error) {
    // Never log the raw error: pg errors can carry the submitted name/email.
    console.error("requestPilot failed", safeError(error));
    return { status: "error" };
  }
}
