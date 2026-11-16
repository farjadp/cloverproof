import assert from "node:assert/strict";
import { test } from "node:test";
import { safeError } from "../src/lib/safe-error.ts";

const pii = ["Jane Farmer", "jane@farm.example", "North field 12 ha"];

function pgError(message: string, extra: Record<string, unknown>) {
  return Object.assign(new Error(message), extra);
}

test("drops detail/parameters and masks values in the message", () => {
  const err = pgError('duplicate key value violates unique constraint "pilot_request_email_key"', {
    code: "23505",
    constraint: "pilot_request_email_key",
    table: "pilot_request",
    detail: "Key (email)=(jane@farm.example) already exists.",
    parameters: pii,
  });
  const out = JSON.stringify(safeError(err));
  for (const v of pii) assert.ok(!out.includes(v), `leaked ${v}`);
  assert.match(out, /"code":"23505"/);
  assert.match(out, /"table":"pilot_request"/);
});

test("masks quoted values and emails inside the message itself", () => {
  const err = pgError('invalid input syntax for type integer: "Jane Farmer" (jane@farm.example) \'North field 12 ha\' jane@farm.example', { code: "22P02" });
  const out = JSON.stringify(safeError(err));
  for (const v of pii) assert.ok(!out.includes(v), `leaked ${v}`);
});

test("rejects non-identifier codes and handles non-errors", () => {
  assert.equal(safeError(pgError("x", { code: "jane@farm.example" })).code, undefined);
  assert.deepEqual(safeError("boom"), { name: "UnknownError", message: "non-error thrown" });
});
