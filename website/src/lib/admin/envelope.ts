import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

// Envelope encryption (ADR 0013): a random data key (DEK) encrypts the value with AES-256-GCM;
// the master key (KEK, from env) encrypts the DEK. `aad` binds the ciphertext to its row so a
// value can't be swapped between rows or purposes. Serialised as versioned JSON bytes.

export type Kek = { id: string; key: Buffer };

type Sealed = { v: 1; kek: string; dek: string; dekIv: string; dekTag: string; iv: string; tag: string; ct: string };

function gcm(key: Buffer, plain: Buffer, aad: string): { iv: Buffer; tag: Buffer; ct: Buffer } {
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  cipher.setAAD(Buffer.from(aad));
  const ct = Buffer.concat([cipher.update(plain), cipher.final()]);
  return { iv, tag: cipher.getAuthTag(), ct };
}

function ungcm(key: Buffer, iv: Buffer, tag: Buffer, ct: Buffer, aad: string): Buffer {
  const decipher = createDecipheriv("aes-256-gcm", key, iv);
  decipher.setAAD(Buffer.from(aad));
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(ct), decipher.final()]);
}

const b64 = (b: Buffer) => b.toString("base64");
const unb64 = (s: string) => Buffer.from(s, "base64");

export function seal(plaintext: string, aad: string, kek: Kek): Buffer {
  if (kek.key.length !== 32) throw new Error("KEK must be 32 bytes");
  const dek = randomBytes(32);
  const value = gcm(dek, Buffer.from(plaintext, "utf8"), aad);
  const wrapped = gcm(kek.key, dek, `dek|${kek.id}|${aad}`);
  dek.fill(0);
  const sealed: Sealed = {
    v: 1,
    kek: kek.id,
    dek: b64(wrapped.ct),
    dekIv: b64(wrapped.iv),
    dekTag: b64(wrapped.tag),
    iv: b64(value.iv),
    tag: b64(value.tag),
    ct: b64(value.ct),
  };
  return Buffer.from(JSON.stringify(sealed), "utf8");
}

/** The KEK id a sealed value was wrapped with (for rotation). */
export function sealedKekId(bytes: Buffer): string {
  return (JSON.parse(bytes.toString("utf8")) as Sealed).kek;
}

/** Throws if the KEK is unknown, the AAD differs or anything was tampered with. */
export function open(bytes: Buffer, aad: string, keks: Kek[]): string {
  const sealed = JSON.parse(bytes.toString("utf8")) as Sealed;
  if (sealed.v !== 1) throw new Error("unknown envelope version");
  const kek = keks.find((k) => k.id === sealed.kek);
  if (!kek) throw new Error("unknown KEK id");
  const dek = ungcm(kek.key, unb64(sealed.dekIv), unb64(sealed.dekTag), unb64(sealed.dek), `dek|${kek.id}|${aad}`);
  try {
    return ungcm(dek, unb64(sealed.iv), unb64(sealed.tag), unb64(sealed.ct), aad).toString("utf8");
  } finally {
    dek.fill(0);
  }
}

/** Re-wrap with a new KEK (rotation); the value itself is re-encrypted with a fresh DEK. */
export function rewrap(bytes: Buffer, aad: string, keks: Kek[], to: Kek): Buffer {
  return seal(open(bytes, aad, keks), aad, to);
}
