// ADMIN_MFA_OPTIONAL policy (ADR 0012, amendment 2026-11-18). Pure: no database.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  authorize,
  hasFullAccess,
  isPasswordOnly,
  landingAfterPassword,
  mfaOptionalFromEnv,
  stepUpFresh,
  stepUpGate,
} from "../src/lib/admin/mfa-policy.ts";
import { ACTIONS, STEP_UP_ACTIONS, STEP_UP_SECONDS, type Action } from "../src/lib/admin/permissions.ts";
import type { Current } from "../src/lib/admin/service.ts";

const NOW = new Date("2026-11-18T12:00:00Z");
const AGO = (seconds: number) => new Date(NOW.getTime() - seconds * 1000);

function make(opts: { enrolled: boolean; verified: boolean; stepUpAt?: Date | null; role?: Current["user"]["role"] }): Current {
  return {
    session: {
      id: "s",
      user_id: "u",
      created_at: AGO(60),
      last_seen_at: AGO(1),
      expires_at: AGO(-3600),
      mfa_verified_at: opts.verified ? AGO(30) : null,
      step_up_at: opts.stepUpAt ?? null,
    },
    user: {
      id: "u",
      email: "a@example.com",
      display_name: "A",
      role: opts.role ?? "admin",
      password_hash: null,
      mfa_secret_enc: null,
      mfa_enabled_at: opts.enrolled ? AGO(9999) : null,
      failed_logins: 0,
      locked_until: null,
      disabled_at: null,
      deleted_at: null,
    },
  };
}

const noMfa = make({ enrolled: false, verified: false });
const enrolledNoCode = make({ enrolled: true, verified: false });
const enrolledVerified = make({ enrolled: true, verified: true });
const allow = { csrfOk: true, now: NOW };

test("flag: only the exact value 'true' turns it on", () => {
  assert.equal(mfaOptionalFromEnv({ ADMIN_MFA_OPTIONAL: "true" }), true);
  assert.equal(mfaOptionalFromEnv({}), false, "unset");
  for (const value of ["", " ", "TRUE", "True", " true", "true ", "1", "yes", "on", "false", "tru"]) {
    assert.equal(mfaOptionalFromEnv({ ADMIN_MFA_OPTIONAL: value }), false, JSON.stringify(value));
  }
});

test("flag off: a session without a verified code has no access, as today", () => {
  assert.equal(hasFullAccess(noMfa, false), false);
  assert.equal(isPasswordOnly(noMfa, false), false);
  assert.equal(hasFullAccess(enrolledNoCode, false), false);
  assert.equal(hasFullAccess(enrolledVerified, false), true);
  assert.deepEqual(authorize(noMfa, "dashboard.view", { ...allow, mfaOptional: false }), { ok: false, error: "SESSION" });
  assert.equal(landingAfterPassword(false, false), "/admin/mfa");
  assert.equal(landingAfterPassword(true, false), "/admin/mfa");
});

test("flag on: a user with no enrolled MFA gets a full session after the password", () => {
  assert.equal(hasFullAccess(noMfa, true), true);
  assert.equal(isPasswordOnly(noMfa, true), true);
  assert.equal(landingAfterPassword(false, true), "/admin");
  assert.deepEqual(authorize(noMfa, "dashboard.view", { ...allow, mfaOptional: true }), { ok: true });
  assert.deepEqual(authorize(noMfa, "log.view", { ...allow, mfaOptional: true }), { ok: true });
});

test("flag on: an enrolled user must still pass the code", () => {
  assert.equal(hasFullAccess(enrolledNoCode, true), false);
  assert.equal(isPasswordOnly(enrolledNoCode, true), false);
  assert.equal(landingAfterPassword(true, true), "/admin/mfa");
  for (const action of ACTIONS) {
    assert.deepEqual(authorize(enrolledNoCode, action, { ...allow, mfaOptional: true }), { ok: false, error: "SESSION" }, action);
  }
  assert.equal(hasFullAccess(enrolledVerified, true), true);
  assert.equal(isPasswordOnly(enrolledVerified, true), false);
});

test("step-up gates cover users, keys and log export", () => {
  assert.deepEqual([...STEP_UP_ACTIONS].sort(), ["keys.manage", "log.export", "users.manage"]);
});

const FRESH = AGO(STEP_UP_SECONDS - 1);

for (const action of STEP_UP_ACTIONS as readonly Action[]) {
  test(`gate ${action}: closed for everyone while the flag is on (R1)`, () => {
    const closed = { ok: false, error: "CLOSED" };
    const accounts = {
      "no MFA": noMfa,
      "no MFA, leftover step-up": make({ enrolled: false, verified: false, stepUpAt: FRESH }),
      "enrolled, code passed": enrolledVerified,
      // What a password holder reaches by enrolling their own authenticator and stepping up.
      "enrolled, fresh step-up": make({ enrolled: true, verified: true, stepUpAt: FRESH }),
    };
    for (const [name, current] of Object.entries(accounts)) {
      assert.deepEqual(authorize(current, action, { ...allow, mfaOptional: true }), closed, name);
    }
  });

  test(`gate ${action}: flag off, a fresh code from an enrolled user is still required`, () => {
    assert.deepEqual(authorize(enrolledVerified, action, { ...allow, mfaOptional: false }), { ok: false, error: "STEP_UP" });
    const old = make({ enrolled: true, verified: true, stepUpAt: AGO(STEP_UP_SECONDS) });
    assert.deepEqual(authorize(old, action, { ...allow, mfaOptional: false }), { ok: false, error: "STEP_UP" });
    const fresh = make({ enrolled: true, verified: true, stepUpAt: FRESH });
    assert.deepEqual(authorize(fresh, action, { ...allow, mfaOptional: false }), { ok: true });
  });
}

test("stepUpFresh: needs an enrolled factor behind the timestamp", () => {
  assert.equal(stepUpFresh(make({ enrolled: false, verified: true, stepUpAt: FRESH }), NOW), false);
  assert.equal(stepUpFresh(make({ enrolled: true, verified: true, stepUpAt: FRESH }), NOW), true);
});

test("stepUpGate: what the users, keys and export screens show", () => {
  const fresh = make({ enrolled: true, verified: true, stepUpAt: FRESH });
  assert.equal(stepUpGate(noMfa, true, NOW), "closed");
  assert.equal(stepUpGate(enrolledVerified, true, NOW), "closed");
  assert.equal(stepUpGate(fresh, true, NOW), "closed");
  assert.equal(stepUpGate(enrolledVerified, false, NOW), "code");
  assert.equal(stepUpGate(fresh, false, NOW), "open");
});

test("flag on: actions outside the gates keep working", () => {
  for (const action of ACTIONS.filter((a) => !STEP_UP_ACTIONS.includes(a))) {
    assert.deepEqual(authorize(enrolledVerified, action, { ...allow, mfaOptional: true }), { ok: true }, action);
  }
});

test("authorize: no session, bad CSRF and wrong role are refused, in that order", () => {
  assert.deepEqual(authorize(null, "dashboard.view", { ...allow, mfaOptional: true }), { ok: false, error: "SESSION" });
  assert.deepEqual(authorize(noMfa, "dashboard.view", { csrfOk: false, now: NOW, mfaOptional: true }), { ok: false, error: "CSRF" });
  const author = make({ enrolled: false, verified: false, role: "author" });
  assert.deepEqual(authorize(author, "keys.manage", { ...allow, mfaOptional: true }), { ok: false, error: "ROLE" });
});
