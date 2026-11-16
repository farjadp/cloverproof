"use server";

export type PilotState = { status: "idle" | "success" | "invalid" | "notConnected" | "error" };

const REQUIRED = ["name", "email", "country", "farmSize", "crop"] as const;

export async function requestPilot(_prev: PilotState, formData: FormData): Promise<PilotState> {
  const values = Object.fromEntries(REQUIRED.map((k) => [k, String(formData.get(k) ?? "").trim()]));
  const email = values.email;
  const consent = formData.get("consent") === "on";
  // Honeypot: real users never fill the hidden "website" field.
  if (String(formData.get("website") ?? "") !== "") return { status: "success" };

  if (REQUIRED.some((k) => !values[k]) || !consent || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { status: "invalid" };
  }

  // Step 5 of docs/plans/website-v1.md wires this to the Supabase `pilot_request` table.
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return { status: "notConnected" };
  }

  try {
    // TODO(step-5): insert into pilot_request with consent timestamp and locale.
    return { status: "notConnected" };
  } catch (error) {
    console.error("requestPilot failed", error);
    return { status: "error" };
  }
}
