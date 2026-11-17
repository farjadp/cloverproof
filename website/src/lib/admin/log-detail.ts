// website_log.detail whitelist (ADR 0014): only these keys, only short scalar values.
// Never secrets, tokens, passwords, codes, bodies, form values or full URLs.
export const DETAIL_KEYS = [
  "role",
  "from_role",
  "to_role",
  "provider",
  "last4",
  "reason",
  "count",
  "mfa_count",
  "status",
  "error_name",
  "error_code",
  "path",
  "locale",
  "via",
  "budget_usd",
] as const;

const FORBIDDEN = /token|secret|password|passwd|code_value|otp|key_value|authorization|cookie/i;

export function cleanDetail(input: Record<string, unknown> | undefined): Record<string, string | number | boolean> {
  const out: Record<string, string | number | boolean> = {};
  if (!input) return out;
  for (const key of DETAIL_KEYS) {
    const value = input[key];
    if (value === undefined || value === null) continue;
    if (typeof value === "number" && Number.isFinite(value)) out[key] = value;
    else if (typeof value === "boolean") out[key] = value;
    else if (typeof value === "string") {
      // Paths lose their query string and fragment first (tokens live there).
      const text = key === "path" ? value.split(/[?#]/)[0].slice(0, 200) : value.slice(0, 120);
      if (!FORBIDDEN.test(text)) out[key] = text;
    }
  }
  return out;
}
