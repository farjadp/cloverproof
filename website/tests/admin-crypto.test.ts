import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import { open, rewrap, seal, sealedKekId } from "../src/lib/admin/envelope.ts";
import { keyFromBase64, randomToken, safeEqual, sha256 } from "../src/lib/admin/crypto.ts";
import { base32Decode, base32Encode, hotp, otpauthUri, totpAt, verifyTotp } from "../src/lib/admin/totp.ts";
import { hashPassword, needsRehash, passwordProblem, verifyPassword } from "../src/lib/admin/password.ts";

const kek = { id: "k1", key: randomBytes(32) };
const kek2 = { id: "k2", key: randomBytes(32) };

test("envelope round trip and no plaintext in the sealed bytes", () => {
  const sealed = seal("sk-ant-SECRET-123456", "website_secret|anthropic|1", kek);
  assert.ok(!sealed.toString("utf8").includes("SECRET"));
  assert.equal(open(sealed, "website_secret|anthropic|1", [kek]), "sk-ant-SECRET-123456");
  assert.equal(sealedKekId(sealed), "k1");
});

test("envelope refuses wrong AAD, wrong KEK and tampering", () => {
  const sealed = seal("value", "row-a", kek);
  assert.throws(() => open(sealed, "row-b", [kek]));
  assert.throws(() => open(sealed, "row-a", [{ id: "k1", key: randomBytes(32) }]));
  assert.throws(() => open(sealed, "row-a", [kek2]), /unknown KEK/);
  const parsed = JSON.parse(sealed.toString("utf8"));
  for (const field of ["ct", "tag", "dek", "dekTag"]) {
    const bytes = Buffer.from(parsed[field], "base64");
    bytes[0] ^= 1;
    const tampered = Buffer.from(JSON.stringify({ ...parsed, [field]: bytes.toString("base64") }));
    assert.throws(() => open(tampered, "row-a", [kek]), field);
  }
});

test("envelope refuses truncated tags", () => {
  const parsed = JSON.parse(seal("v", "aad", kek).toString("utf8"));
  const short = Buffer.from(JSON.stringify({ ...parsed, tag: Buffer.from(parsed.tag, "base64").subarray(0, 4).toString("base64") }));
  assert.throws(() => open(short, "aad", [kek]), /bad envelope/);
});

test("envelope rewrap moves a value to a new KEK", () => {
  const moved = rewrap(seal("v", "aad", kek), "aad", [kek], kek2);
  assert.equal(sealedKekId(moved), "k2");
  assert.equal(open(moved, "aad", [kek2]), "v");
});

test("keyFromBase64 requires exactly 32 bytes", () => {
  assert.throws(() => keyFromBase64("K", undefined), /not set/);
  assert.throws(() => keyFromBase64("K", Buffer.alloc(16).toString("base64")), /32 bytes/);
  assert.equal(keyFromBase64("K", Buffer.alloc(32).toString("base64")).length, 32);
});

test("tokens are random, hashes fixed-length, compare is length-safe", () => {
  assert.notEqual(randomToken(), randomToken());
  assert.equal(sha256("x").length, 32);
  assert.equal(safeEqual("abc", "abc"), true);
  assert.equal(safeEqual("abc", "abcd"), false);
});

// RFC 6238 Appendix B (SHA-1 seed "12345678901234567890", 8 digits).
test("TOTP matches RFC 6238 test vectors", () => {
  const seed = Buffer.from("12345678901234567890");
  const vectors: [number, string][] = [
    [59, "94287082"],
    [1111111109, "07081804"],
    [1111111111, "14050471"],
    [1234567890, "89005924"],
    [2000000000, "69279037"],
    [20000000000, "65353130"],
  ];
  for (const [time, code] of vectors) assert.equal(hotp(seed, Math.floor(time / 30), 8), code, String(time));
  assert.equal(totpAt(base32Encode(seed), 59, 8), "94287082");
});

test("TOTP verify accepts ±1 step only and returns the step", () => {
  const secret = base32Encode(Buffer.from("12345678901234567890"));
  const now = 1_700_000_000;
  const code = totpAt(secret, now);
  assert.equal(verifyTotp(secret, code, now), Math.floor(now / 30));
  assert.notEqual(verifyTotp(secret, totpAt(secret, now - 30), now), null);
  assert.equal(verifyTotp(secret, totpAt(secret, now - 90), now), null);
  assert.equal(verifyTotp(secret, "12345", now), null);
  assert.equal(verifyTotp(secret, "abcdef", now), null);
});

test("base32 round trip and otpauth URI", () => {
  const bytes = randomBytes(20);
  assert.deepEqual(base32Decode(base32Encode(bytes)), bytes);
  assert.match(otpauthUri("JBSWY3DPEHPK3PXP", "a@example.com"), /^otpauth:\/\/totp\/CloverProof%20admin%3Aa%40example\.com\?secret=JBSWY3DPEHPK3PXP/);
});

test("argon2id hash, verify, rehash check and password rules", async () => {
  const stored = await hashPassword("correct horse battery");
  assert.match(stored, /^\$argon2id\$v=19\$m=19456,t=2,p=1\$/);
  assert.equal(await verifyPassword(stored, "correct horse battery"), true);
  assert.equal(await verifyPassword(stored, "wrong"), false);
  assert.equal(await verifyPassword("not-a-hash", "x"), false);
  assert.equal(needsRehash(stored), false);
  assert.equal(needsRehash("$argon2id$v=19$m=4096,t=3,p=1$abc$def"), true);
  assert.ok(passwordProblem("short"));
  assert.ok(passwordProblem("farjad-long-password", "farjad@example.com"));
  assert.equal(passwordProblem("a long enough passphrase"), null);
  assert.equal(passwordProblem("a long enough passphrase", "a@example.com"), null, "short local parts don't count");
});
