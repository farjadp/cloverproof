import assert from "node:assert/strict";
import { test } from "node:test";
import { PILOT_FIELDS, readPilotRequest } from "../src/lib/pilot-request.ts";

const form = (o: Record<string, string>) => ({ get: (k: string) => (k in o ? o[k] : null) });
const good = { name: "A", email: "a@b.co", country: "Canada", farmSize: "40 ha", crop: "wheat" };

test("notes is not an accepted field", () => {
  assert.ok(!(PILOT_FIELDS as readonly string[]).includes("notes"));
});

test("posted notes (or any extra field) is dropped", () => {
  const r = readPilotRequest(form({ ...good, notes: "my neighbour Bob, 555-0100", website: "x", extra: "y" }));
  assert.equal(r.ok, true);
  assert.deepEqual(Object.keys(r.ok ? r.value : {}).sort(), [...PILOT_FIELDS].sort());
  assert.ok(!JSON.stringify(r).includes("Bob"));
});

test("required fields, length limits and email shape still enforced", () => {
  assert.equal(readPilotRequest(form({ ...good, crop: " " })).ok, false);
  assert.equal(readPilotRequest(form({ ...good, email: "nope" })).ok, false);
  assert.equal(readPilotRequest(form({ ...good, name: "x".repeat(201) })).ok, false);
});
