import "server-only";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { Pool } from "pg";
import { keyFromBase64 } from "./crypto.ts";
import { can, STEP_UP_SECONDS, type Action } from "./permissions.ts";
import { clientIp, ipPrefix, uaFamily } from "./request-meta.ts";
import { csrfToken, csrfValid, loadSession, type AdminConfig, type Current, type RequestMeta } from "./service.ts";
import { siteUrl } from "../site.ts";

// Website admin server glue (ADR 0012): its own pool (cp_website_admin_login via
// ADMIN_DATABASE_URL), never the public site's pool, and the session cookie.

export const SESSION_COOKIE = "__Host-cp_admin";
export const PRE_COOKIE = "__Host-cp_admin_pre";

let pool: Pool | null = null;

/** Admin pool, or null when ADMIN_DATABASE_URL is not set. */
export function adminDb(): Pool | null {
  const url = process.env.ADMIN_DATABASE_URL;
  if (!url) return null;
  pool ??= new Pool({ connectionString: url, max: 3, statement_timeout: 10_000, idle_in_transaction_session_timeout: 30_000 });
  return pool;
}

let config: AdminConfig | null | undefined;

/** Keys from env (never in git or the DB). Null when the admin is not configured. */
export function adminConfig(): AdminConfig | null {
  if (config !== undefined) return config;
  try {
    const keks = [
      { id: process.env.WEBSITE_SECRETS_KEK_ID || "k1", key: keyFromBase64("WEBSITE_SECRETS_KEK", process.env.WEBSITE_SECRETS_KEK) },
    ];
    if (process.env.WEBSITE_SECRETS_KEK_PREVIOUS) {
      keks.push({
        id: process.env.WEBSITE_SECRETS_KEK_PREVIOUS_ID || "previous",
        key: keyFromBase64("WEBSITE_SECRETS_KEK_PREVIOUS", process.env.WEBSITE_SECRETS_KEK_PREVIOUS),
      });
    }
    config = { keks, hmacKey: keyFromBase64("WEBSITE_ADMIN_HMAC_KEY", process.env.WEBSITE_ADMIN_HMAC_KEY), siteUrl };
  } catch {
    config = null;
  }
  return config;
}

export function adminReady(): boolean {
  return adminDb() !== null && adminConfig() !== null;
}

export async function requestMeta(): Promise<RequestMeta> {
  const h = await headers();
  return { ipPrefix: ipPrefix(clientIp(h.get("x-forwarded-for"), h.get("x-real-ip"))), uaFamily: uaFamily(h.get("user-agent")) };
}

export async function sessionToken(): Promise<string | undefined> {
  return (await cookies()).get(SESSION_COOKIE)?.value;
}

export async function setSessionCookie(token: string): Promise<void> {
  (await cookies()).set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: true,
    sameSite: "strict",
    path: "/",
    maxAge: 12 * 60 * 60,
  });
}

export async function clearSessionCookie(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}

/** Current session (any MFA state), or null. */
export async function currentSession(): Promise<Current | null> {
  const db = adminDb();
  if (!db || !adminConfig()) return null;
  return loadSession(db, await sessionToken(), new Date());
}

/** Signed-in, MFA-verified user allowed to do `action`; otherwise redirect. Use in pages. */
export async function requirePage(action: Action): Promise<Current> {
  const current = await currentSession();
  if (!current) redirect("/admin/login");
  if (!current.session.mfa_verified_at) redirect("/admin/mfa");
  if (!can(current.user.role, action)) redirect("/admin?denied=1");
  return current;
}

export type Guard = { ok: true; current: Current; db: Pool; config: AdminConfig; meta: RequestMeta } | { ok: false; error: string };

/** Server actions: session + MFA + role + CSRF (+ step-up when needed). Never redirects. */
export async function guardAction(action: Action, form: FormData, opts: { stepUp?: boolean } = {}): Promise<Guard> {
  const db = adminDb();
  const cfg = adminConfig();
  if (!db || !cfg) return { ok: false, error: "The admin is not configured." };
  const token = await sessionToken();
  const current = await loadSession(db, token, new Date());
  if (!current || !current.session.mfa_verified_at) return { ok: false, error: "Your session has ended. Sign in again." };
  if (!csrfValid(cfg, token, form.get("csrf"))) return { ok: false, error: "This form has expired. Reload the page." };
  if (!can(current.user.role, action)) return { ok: false, error: "You don't have permission for this." };
  if (opts.stepUp) {
    const at = current.session.step_up_at ? new Date(current.session.step_up_at).getTime() : 0;
    if (Date.now() - at > STEP_UP_SECONDS * 1000) return { ok: false, error: "STEP_UP" };
  }
  return { ok: true, current, db, config: cfg, meta: await requestMeta() };
}

/** Hidden-field CSRF value for the signed-in session. */
export async function csrfField(): Promise<string> {
  const cfg = adminConfig();
  const token = await sessionToken();
  return cfg && token ? csrfToken(cfg, token) : "";
}

/** Pre-session CSRF (double submit) for login / setup forms; cookie set by proxy.ts. */
export async function preToken(): Promise<string> {
  return (await cookies()).get(PRE_COOKIE)?.value ?? "";
}

export async function preValid(form: FormData): Promise<boolean> {
  const cookie = await preToken();
  const sent = form.get("pre");
  return cookie.length >= 32 && typeof sent === "string" && sent === cookie;
}
