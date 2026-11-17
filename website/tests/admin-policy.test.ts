import { test } from "node:test";
import assert from "node:assert/strict";
import { ACTIONS, can, type WebsiteRole } from "../src/lib/admin/permissions.ts";
import { cleanDetail } from "../src/lib/admin/log-detail.ts";
import { clientIp, ipPrefix, uaFamily } from "../src/lib/admin/request-meta.ts";

test("role matrix: admin all, editor no users/log/keys, author drafts only", () => {
  for (const action of ACTIONS) assert.equal(can("admin", action), true, action);
  const denied: [WebsiteRole, string][] = [
    ["editor", "users.manage"], ["editor", "log.view"], ["editor", "keys.manage"],
    ["author", "users.manage"], ["author", "keys.manage"], ["author", "posts.publish"],
    ["author", "posts.edit_any"], ["author", "log.view"], ["author", "media.manage"],
  ];
  for (const [role, action] of denied) assert.equal(can(role, action as never), false, `${role} ${action}`);
  assert.equal(can("editor", "posts.publish"), true);
  assert.equal(can("author", "posts.write_own"), true);
});

test("log detail keeps whitelisted scalar keys only", () => {
  const out = cleanDetail({
    role: "editor",
    token: "abc",
    password: "x",
    count: 3,
    nested: { a: 1 },
    path: "/admin/users?token=abc",
    reason: "contains secret value",
    last4: "9f3a",
  });
  assert.deepEqual(out, { role: "editor", count: 3, path: "/admin/users", last4: "9f3a" });
});

test("only IP prefixes leave the request", () => {
  assert.equal(ipPrefix("203.0.113.77"), "203.0.113.0/24");
  assert.equal(ipPrefix("::ffff:198.51.100.9"), "198.51.100.0/24");
  assert.equal(ipPrefix("2001:db8:abcd:12::1"), "2001:db8:abcd::/48");
  assert.equal(ipPrefix("::1"), "0:0:0::/48");
  assert.equal(ipPrefix("not an ip"), null);
  assert.equal(clientIp("203.0.113.5, 10.0.0.1", null), "203.0.113.5");
  assert.equal(clientIp(null, "198.51.100.2"), "198.51.100.2");
});

test("browser family only", () => {
  assert.equal(uaFamily("Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"), "Chrome");
  assert.equal(uaFamily("Mozilla/5.0 (X11; rv:130.0) Gecko/20100101 Firefox/130.0"), "Firefox");
  assert.equal(uaFamily("Mozilla/5.0 (iPhone) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1"), "Safari");
  assert.equal(uaFamily("curl/8.4.0"), "Script");
  assert.equal(uaFamily(null), null);
});
