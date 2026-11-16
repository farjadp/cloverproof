/**
 * Describe a database error for logs without personal data.
 * pg errors can carry submitted values in `message`, `detail`, `where` or `parameters`
 * (e.g. `Key (email)=(a@b.co) already exists`), so only structural fields are kept and any
 * quoted or bracketed fragment of the message is masked.
 */
export type SafeError = { name: string; code?: string; constraint?: string; table?: string; message: string };

const MAX = 200;

export function redactMessage(message: string): string {
  return message
    .replace(/\([^)]*\)/g, "(…)")
    .replace(/"[^"]*"/g, '"…"')
    .replace(/'[^']*'/g, "'…'")
    .replace(/[^\s@]+@[^\s@]+/g, "…@…")
    .slice(0, MAX);
}

export function safeError(error: unknown): SafeError {
  if (!(error instanceof Error)) return { name: "UnknownError", message: "non-error thrown" };
  const e = error as Error & { code?: unknown; constraint?: unknown; table?: unknown };
  const str = (v: unknown) => (typeof v === "string" && /^[\w.-]{1,63}$/.test(v) ? v : undefined);
  return {
    name: e.name,
    code: str(e.code),
    constraint: str(e.constraint),
    table: str(e.table),
    message: redactMessage(e.message ?? ""),
  };
}
