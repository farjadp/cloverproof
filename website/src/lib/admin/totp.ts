import { createHmac, randomBytes } from "node:crypto";

// TOTP (RFC 6238): HMAC-SHA1, 6 digits, 30-second steps, ±1 step tolerance.
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

export function base32Encode(bytes: Buffer): string {
  let bits = 0;
  let value = 0;
  let out = "";
  for (const byte of bytes) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      out += ALPHABET[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) out += ALPHABET[(value << (5 - bits)) & 31];
  return out;
}

export function base32Decode(text: string): Buffer {
  const clean = text.replace(/[\s=-]/g, "").toUpperCase();
  let bits = 0;
  let value = 0;
  const out: number[] = [];
  for (const char of clean) {
    const index = ALPHABET.indexOf(char);
    if (index < 0) throw new Error("invalid base32");
    value = (value << 5) | index;
    bits += 5;
    if (bits >= 8) {
      out.push((value >>> (bits - 8)) & 255);
      bits -= 8;
    }
  }
  return Buffer.from(out);
}

/** 20 random bytes (160 bits, RFC 4226 recommendation), base32. */
export function newTotpSecret(): string {
  return base32Encode(randomBytes(20));
}

export function hotp(secret: Buffer, counter: number, digits = 6, algorithm = "sha1"): string {
  const message = Buffer.alloc(8);
  message.writeBigUInt64BE(BigInt(counter));
  const digest = createHmac(algorithm, secret).update(message).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const code = (digest.readUInt32BE(offset) & 0x7fffffff) % 10 ** digits;
  return code.toString().padStart(digits, "0");
}

export function totpAt(secretBase32: string, unixSeconds: number, digits = 6): string {
  return hotp(base32Decode(secretBase32), Math.floor(unixSeconds / 30), digits);
}

/** Returns the matching time step, or null. Callers reject a step that was already used. */
export function verifyTotp(secretBase32: string, code: string, unixSeconds: number, window = 1): number | null {
  if (!/^\d{6}$/.test(code)) return null;
  const secret = base32Decode(secretBase32);
  const step = Math.floor(unixSeconds / 30);
  let match: number | null = null;
  for (let delta = -window; delta <= window; delta++) {
    // Check every step (no early exit) so timing doesn't reveal which step matched.
    const candidate = hotp(secret, step + delta);
    let diff = 0;
    for (let i = 0; i < 6; i++) diff |= candidate.charCodeAt(i) ^ code.charCodeAt(i);
    if (diff === 0 && match === null) match = step + delta;
  }
  return match;
}

/** otpauth:// URI for authenticator apps (shown as a QR code). */
export function otpauthUri(secretBase32: string, account: string, issuer = "CloverProof admin"): string {
  const label = encodeURIComponent(`${issuer}:${account}`);
  return `otpauth://totp/${label}?secret=${secretBase32}&issuer=${encodeURIComponent(issuer)}&algorithm=SHA1&digits=6&period=30`;
}
