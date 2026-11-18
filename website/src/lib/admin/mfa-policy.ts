// Who may use the admin after which sign-in steps (ADR 0012, amendment 2026-11-18). Framework-free.
//
// ADMIN_MFA_OPTIONAL lets an account with NO enrolled two-step sign-in in on its password alone.
// It is decided on every request from the live user row and never stored on the session, and
// mfa_verified_at keeps meaning "a second factor was really checked". So removing the flag, or
// the user enrolling, takes effect for every open session (a variable change redeploys the site).
//
// While the flag is on, the step-up actions (users, API keys, log export) are closed for everyone,
// enrolled accounts included. Otherwise someone holding only the password could enrol their own
// authenticator and pass step-up (ciso review of PR #78, R1).
import { can, STEP_UP_ACTIONS, STEP_UP_SECONDS, type Action } from "./permissions.ts";
import type { Current } from "./service.ts";

/** Only the exact value "true" turns it on; anything else keeps two-step sign-in required. */
export function mfaOptionalFromEnv(env: Record<string, string | undefined> = process.env): boolean {
  return env.ADMIN_MFA_OPTIONAL === "true";
}

/** Signed in on the password alone, allowed only because the flag is on and nothing is enrolled. */
export function isPasswordOnly(current: Current, mfaOptional: boolean): boolean {
  return mfaOptional === true && !current.user.mfa_enabled_at && !current.session.mfa_verified_at;
}

export function hasFullAccess(current: Current, mfaOptional: boolean): boolean {
  return Boolean(current.session.mfa_verified_at) || isPasswordOnly(current, mfaOptional);
}

/** Where the browser goes after a correct password. */
export function landingAfterPassword(mfaEnrolled: boolean, mfaOptional: boolean): "/admin" | "/admin/mfa" {
  return mfaOptional === true && !mfaEnrolled ? "/admin" : "/admin/mfa";
}

/** True when the session confirmed a fresh code within STEP_UP_SECONDS, with a factor enrolled. */
export function stepUpFresh(current: Current, now: Date = new Date()): boolean {
  if (!current.user.mfa_enabled_at) return false;
  const at = current.session.step_up_at ? new Date(current.session.step_up_at).getTime() : 0;
  return now.getTime() - at < STEP_UP_SECONDS * 1000;
}

/** What a screen behind step-up shows: its content, the code form, or the "closed" message. */
export function stepUpGate(current: Current, mfaOptional: boolean, now: Date = new Date()): "open" | "code" | "closed" {
  if (mfaOptional === true) return "closed";
  return stepUpFresh(current, now) ? "open" : "code";
}

export type Verdict = { ok: true } | { ok: false; error: "SESSION" | "CSRF" | "ROLE" | "CLOSED" | "STEP_UP" };

/** Every server action and route handler: session + MFA state, CSRF, role, step-up. */
export function authorize(
  current: Current | null,
  action: Action,
  opts: { mfaOptional: boolean; csrfOk: boolean; now: Date; stepUp?: boolean },
): Verdict {
  if (!current || !hasFullAccess(current, opts.mfaOptional)) return { ok: false, error: "SESSION" };
  if (!opts.csrfOk) return { ok: false, error: "CSRF" };
  if (!can(current.user.role, action)) return { ok: false, error: "ROLE" };
  const needsStepUp = opts.stepUp === true || STEP_UP_ACTIONS.includes(action);
  if (needsStepUp) {
    const gate = stepUpGate(current, opts.mfaOptional, opts.now);
    if (gate === "closed") return { ok: false, error: "CLOSED" };
    if (gate === "code") return { ok: false, error: "STEP_UP" };
  }
  return { ok: true };
}
