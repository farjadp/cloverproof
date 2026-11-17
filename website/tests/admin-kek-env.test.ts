// D-S2: master-key (KEK) ids come from env with no defaults, and current/previous must differ.
import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import { kekRingFromEnv } from "../src/lib/admin/kek-env.ts";

const k = () => randomBytes(32).toString("base64");
const A = k();
const B = k();

test("current KEK id is required (no default)", () => {
  assert.throws(() => kekRingFromEnv({ WEBSITE_SECRETS_KEK: A }), /WEBSITE_SECRETS_KEK_ID is not set/);
  assert.throws(() => kekRingFromEnv({ WEBSITE_SECRETS_KEK: A, WEBSITE_SECRETS_KEK_ID: "" }), /WEBSITE_SECRETS_KEK_ID is not set/);
  assert.throws(() => kekRingFromEnv({ WEBSITE_SECRETS_KEK: A, WEBSITE_SECRETS_KEK_ID: "bad id!" }), /WEBSITE_SECRETS_KEK_ID/);
  assert.throws(() => kekRingFromEnv({ WEBSITE_SECRETS_KEK_ID: "k2026a" }), /WEBSITE_SECRETS_KEK is not set/);
});

test("one KEK: ring of one with the given id", () => {
  const ring = kekRingFromEnv({ WEBSITE_SECRETS_KEK: A, WEBSITE_SECRETS_KEK_ID: "k2026a" });
  assert.deepEqual(ring.map((x) => x.id), ["k2026a"]);
  assert.equal(ring[0].key.length, 32);
});

test("previous KEK needs its own id (no default), and the ids and keys must differ", () => {
  const base = { WEBSITE_SECRETS_KEK: A, WEBSITE_SECRETS_KEK_ID: "k2027a" };
  assert.throws(() => kekRingFromEnv({ ...base, WEBSITE_SECRETS_KEK_PREVIOUS: B }), /WEBSITE_SECRETS_KEK_PREVIOUS_ID is not set/);
  assert.throws(() => kekRingFromEnv({ ...base, WEBSITE_SECRETS_KEK_PREVIOUS_ID: "k2026a" }), /WEBSITE_SECRETS_KEK_PREVIOUS is not set/);
  assert.throws(
    () => kekRingFromEnv({ ...base, WEBSITE_SECRETS_KEK_PREVIOUS: B, WEBSITE_SECRETS_KEK_PREVIOUS_ID: "k2027a" }),
    /must differ/,
  );
  assert.throws(
    () => kekRingFromEnv({ ...base, WEBSITE_SECRETS_KEK_PREVIOUS: A, WEBSITE_SECRETS_KEK_PREVIOUS_ID: "k2026a" }),
    /same key/,
  );
  const ring = kekRingFromEnv({ ...base, WEBSITE_SECRETS_KEK_PREVIOUS: B, WEBSITE_SECRETS_KEK_PREVIOUS_ID: "k2026a" });
  assert.deepEqual(ring.map((x) => x.id), ["k2027a", "k2026a"]);
});

test("errors name variables only, never values", () => {
  try {
    kekRingFromEnv({ WEBSITE_SECRETS_KEK: A, WEBSITE_SECRETS_KEK_ID: "k1", WEBSITE_SECRETS_KEK_PREVIOUS: A, WEBSITE_SECRETS_KEK_PREVIOUS_ID: "k0" });
    assert.fail("should throw");
  } catch (error) {
    assert.ok(!(error as Error).message.includes(A));
  }
});
