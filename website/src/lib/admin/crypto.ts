import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";

/** 32 random bytes as base64url (cookie / link tokens). */
export function randomToken(bytes = 32): string {
  return randomBytes(bytes).toString("base64url");
}

export function sha256(value: string | Buffer): Buffer {
  return createHash("sha256").update(value).digest();
}

export function hmac(key: Buffer, value: string): Buffer {
  return createHmac("sha256", key).update(value).digest();
}

/** Constant-time comparison; false for different lengths. */
export function safeEqual(a: Buffer | string, b: Buffer | string): boolean {
  const x = Buffer.isBuffer(a) ? a : Buffer.from(a);
  const y = Buffer.isBuffer(b) ? b : Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

/** Decode a base64 key from an env var and require an exact length. */
export function keyFromBase64(name: string, value: string | undefined, length = 32): Buffer {
  if (!value) throw new Error(`${name} is not set`);
  const key = Buffer.from(value, "base64");
  if (key.length !== length) throw new Error(`${name} must be ${length} bytes, base64-encoded`);
  return key;
}
