// The log-export route must answer a malformed POST with 400, not a 500 (pre-switch check, 2026-11-17).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readForm } from "../src/lib/admin/form.ts";

const req = (body: BodyInit | null, type?: string) =>
  new Request("http://x/admin/log/export", { method: "POST", body, headers: type ? { "content-type": type } : {} });

test("form posts are parsed", async () => {
  const form = await readForm(req("csrf=abc&kind=auth", "application/x-www-form-urlencoded"));
  assert.equal(form?.get("kind"), "auth");
});

test("no body, wrong content type or broken multipart give null (caller answers 400)", async () => {
  assert.equal(await readForm(req(null)), null);
  assert.equal(await readForm(req("{}", "application/json")), null);
  assert.equal(await readForm(req("garbage", "multipart/form-data; boundary=x")), null);
});
