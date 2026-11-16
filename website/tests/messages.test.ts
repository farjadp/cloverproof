import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const locales = ["en", "fr", "it", "es", "bg", "fi", "tr", "ar"];
const load = (l: string) => JSON.parse(readFileSync(new URL(`../src/messages/${l}.json`, import.meta.url), "utf8"));
const en = load("en");

/** Every key path (and array length) in `src` must exist in `dst` with the same kind of value. */
function diff(src: unknown, dst: unknown, path: string, out: string[]) {
  if (Array.isArray(src)) {
    if (!Array.isArray(dst)) return out.push(`${path}: expected array`);
    if (dst.length !== src.length) out.push(`${path}: ${dst.length} items, en has ${src.length}`);
    src.forEach((v, i) => diff(v, dst[i], `${path}[${i}]`, out));
  } else if (src && typeof src === "object") {
    if (!dst || typeof dst !== "object" || Array.isArray(dst)) return out.push(`${path}: expected object`);
    for (const k of Object.keys(src)) {
      if (!(k in (dst as object))) out.push(`${path}.${k}: missing`);
      else diff((src as Record<string, unknown>)[k], (dst as Record<string, unknown>)[k], `${path}.${k}`, out);
    }
  } else if (typeof src !== typeof dst) out.push(`${path}: expected ${typeof src}`);
  else if (typeof src === "string" && (dst as string).trim() === "") out.push(`${path}: empty`);
}

const placeholders = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join();

for (const l of locales.filter((x) => x !== "en")) {
  test(`${l}.json has every key of en.json`, () => {
    const out: string[] = [];
    diff(en, load(l), l, out);
    assert.deepEqual(out, []);
  });

  test(`${l}.json keeps {placeholders}, logic codes and the translation status`, () => {
    const t = load(l);
    const walk = (a: unknown, b: unknown, p: string) => {
      if (typeof a === "string") {
        assert.equal(placeholders(b as string), placeholders(a), `${p}: placeholders differ`);
        if (/\.(v|id)$/.test(p)) assert.equal(b, a, `${p}: logic value must not be translated`);
      } else if (a && typeof a === "object") for (const k of Object.keys(a)) walk((a as never)[k], (b as never)[k], `${p}.${k}`);
    };
    walk(en, t, l);
    assert.match(t.meta.translationStatus, /review/);
  });
}
