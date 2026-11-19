// Roadmap and "What's new": structure and the truthfulness rules that can be checked mechanically.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { groupByMonth } from "../src/lib/changelog.ts";

const locales = ["en", "fr", "it", "es", "bg", "fi", "tr", "ar", "he"];
const load = (l: string) => JSON.parse(readFileSync(new URL(`../src/messages/${l}.json`, import.meta.url), "utf8"));
const en = load("en");
const stages = ["now", "next", "later"] as const;
const items = (d: typeof en) => stages.flatMap((s) => d.roadmap[s].items) as { kind: string; title: string; text: string }[];

test("every roadmap and changelog kind has a label", () => {
  for (const item of items(en)) assert.ok(en.roadmap.kinds[item.kind], item.kind);
  for (const entry of en.changelog.entries) assert.ok(en.changelog.kinds[entry.kind], entry.kind);
});

test("changelog entries have real dates, newest first, none in the future of the repo's history", () => {
  const dates: string[] = en.changelog.entries.map((e: { date: string }) => e.date);
  for (const d of dates) assert.match(d, /^\d{4}-\d{2}-\d{2}$/);
  assert.deepEqual(dates, [...dates].sort().reverse());
});

for (const l of locales.filter((x) => x !== "en")) {
  test(`${l}: dates and kinds match English; the translation stays marked as unreviewed`, () => {
    const t = load(l);
    assert.deepEqual(items(t).map((i) => i.kind), items(en).map((i) => i.kind));
    assert.deepEqual(
      t.changelog.entries.map((e: { date: string; kind: string }) => [e.date, e.kind]),
      en.changelog.entries.map((e: { date: string; kind: string }) => [e.date, e.kind]),
    );
    assert.equal(t.meta.translationStatus, "machine — review pending");
  });
}

test("English copy states the current limits", () => {
  const text = JSON.stringify(en.roadmap.status);
  assert.match(text, /internal/i);
  assert.match(text, /not yet validated by a human agronomist/);
  assert.match(text, /approved/);
});

test("English copy has no internal details, claims or out-of-scope promises", () => {
  const text = JSON.stringify({ roadmap: en.roadmap, changelog: en.changelog });
  const banned = [
    /\bPR\b/, /#\d/, /migration/i, /\bsprint/i, /\bADR\b/, /\bagent\b/i, /claude/i, /railway/i, /postgres/i, /github/i,
    /\bMFA\b/, /encrypt/i, /sensor/i, /\bIoT\b/i, /hardware/i, /variable[- ]rate/i, /zone map/i, /carbon/i, /price/i, /satellite/i,
    /\bsav(e|es|ing|ings)\b/i, /higher yield/i, /accura(te|cy) of \d/i, /\d+\s*%/, /complian/i, /certif/i, /partner/i, /\bguarantee/i,
    /\d+\s+(farms|farmers)/i,
  ];
  for (const pattern of banned) assert.doesNotMatch(text, pattern);
});

test("groupByMonth keeps order and labels each month in the page's language", () => {
  const entries = [{ date: "2026-12-01" }, { date: "2026-11-30" }, { date: "2026-11-01" }];
  const groups = groupByMonth(entries, "en");
  assert.deepEqual(groups.map((g) => [g.key, g.label, g.entries.length]), [["2026-12", "December 2026", 1], ["2026-11", "November 2026", 2]]);
  assert.match(groupByMonth(entries, "fr")[1].label, /novembre 2026/);
});
