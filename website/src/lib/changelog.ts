// "What's new": groups dated entries by calendar month. Dates are plain YYYY-MM-DD, read as UTC so
// a visitor's time zone can't move an entry to another day or month.

const asUtc = (date: string) => new Date(`${date}T00:00:00Z`);

export function formatDay(date: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(asUtc(date));
}

export function groupByMonth<T extends { date: string }>(entries: readonly T[], locale: string) {
  const format = new Intl.DateTimeFormat(locale, { month: "long", year: "numeric", timeZone: "UTC" });
  const groups: { key: string; label: string; entries: T[] }[] = [];
  for (const entry of entries) {
    const key = entry.date.slice(0, 7);
    const last = groups.at(-1);
    if (last?.key === key) last.entries.push(entry);
    else groups.push({ key, label: format.format(asUtc(entry.date)), entries: [entry] });
  }
  return groups;
}
