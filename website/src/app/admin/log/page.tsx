import type { Metadata } from "next";
import Link from "next/link";
import { actors, KINDS, OUTCOMES, readLog, RETENTION_DAYS, type LogFilter } from "@/lib/admin/log";
import { stepUpGate } from "@/lib/admin/mfa-policy";
import { adminDb, adminReady, csrfField, mfaOptional, requirePage } from "@/lib/admin/server";
import { AdminShell } from "../shell";
import { StepUpForm } from "../StepUpForm";
import { NotConfigured } from "../ui";

export const metadata: Metadata = { title: "System log" };

type Search = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

const OUTCOME_STYLE: Record<string, string> = {
  ok: "bg-sage-soft text-ink",
  denied: "bg-sand text-ink",
  failed: "bg-red-50 text-red-900",
};

function stamp(d: Date): string {
  return new Date(d).toISOString().slice(0, 19).replace("T", " ");
}

function Select({ name, label, value, options }: { name: string; label: string; value: string; options: { value: string; label: string }[] }) {
  return (
    <div>
      <label htmlFor={`f-${name}`} className="mb-1 block text-xs font-semibold text-ink-soft">
        {label}
      </label>
      <select id={`f-${name}`} name={name} defaultValue={value} className="min-h-11 w-full rounded-md border border-rule bg-white px-2 text-sm">
        <option value="">All</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export default async function LogPage({ searchParams }: { searchParams: Promise<Search> }) {
  if (!adminReady()) return <NotConfigured />;
  const current = await requirePage("log.view");
  const db = adminDb()!;
  const csrf = await csrfField();
  const gate = stepUpGate(current, mfaOptional());
  const sp = await searchParams;
  const filter: LogFilter = {
    kind: one(sp.kind),
    outcome: one(sp.outcome),
    actor: one(sp.actor),
    from: one(sp.from),
    to: one(sp.to),
    page: Number(one(sp.page)) || 1,
  };
  const [{ rows, more }, people] = await Promise.all([readLog(db, filter, new Date()), actors(db)]);
  const query = (page: number) => {
    const q = new URLSearchParams(Object.entries({ ...filter, page: String(page) }).filter(([, v]) => v) as [string, string][]);
    return `/admin/log?${q}`;
  };
  return (
    <AdminShell current={current} csrf={csrf} active="/admin/log">
      <h1 className="font-serif text-3xl text-ink">System log</h1>
      <p className="mt-1 mb-6 text-ink-soft">
        Sign-ins, admin actions, content and key changes, errors and jobs. Entries are deleted automatically after {RETENTION_DAYS} days.
        IP addresses are kept only as a network prefix.
      </p>
      <form method="get" className="mb-6 grid grid-cols-2 gap-3 rounded-lg border border-rule bg-ivory p-4 sm:grid-cols-3 lg:grid-cols-6">
        <Select name="kind" label="Type" value={filter.kind ?? ""} options={KINDS.map((k) => ({ value: k, label: k }))} />
        <Select name="outcome" label="Outcome" value={filter.outcome ?? ""} options={OUTCOMES.map((o) => ({ value: o, label: o }))} />
        <Select name="actor" label="Who" value={filter.actor ?? ""} options={people.map((p) => ({ value: p.id, label: p.name }))} />
        <div>
          <label htmlFor="f-from" className="mb-1 block text-xs font-semibold text-ink-soft">
            From
          </label>
          <input id="f-from" name="from" type="date" defaultValue={filter.from} className="min-h-11 w-full rounded-md border border-rule bg-white px-2 text-sm" />
        </div>
        <div>
          <label htmlFor="f-to" className="mb-1 block text-xs font-semibold text-ink-soft">
            To
          </label>
          <input id="f-to" name="to" type="date" defaultValue={filter.to} className="min-h-11 w-full rounded-md border border-rule bg-white px-2 text-sm" />
        </div>
        <div className="flex items-end gap-2">
          <button type="submit" className="min-h-11 flex-1 rounded-md bg-olive px-3 text-sm font-semibold text-ivory hover:bg-olive-deep">
            Filter
          </button>
          <Link href="/admin/log" className="inline-flex min-h-11 items-center px-2 text-sm text-olive underline underline-offset-4">
            Reset
          </Link>
        </div>
      </form>

      {rows.length === 0 ? (
        <p className="rounded-lg border border-rule bg-ivory p-6 text-ink-soft">No entries match these filters.</p>
      ) : (
        <ol className="divide-y divide-rule rounded-lg border border-rule bg-ivory" aria-label="Log entries, newest first">
          {rows.map((r) => (
            <li key={r.id} className="grid gap-1 p-3 text-sm sm:grid-cols-[11rem_1fr_auto] sm:gap-4">
              <time dateTime={new Date(r.occurred_at).toISOString()} className="font-mono text-xs text-ink-soft">
                {stamp(r.occurred_at)} UTC
              </time>
              <div className="min-w-0">
                <p className="text-ink">
                  <span className="font-semibold">{r.action}</span>
                  <span className="text-ink-soft"> · {r.kind}</span>
                  {r.actor ? <span className="text-ink-soft"> · by {r.actor}</span> : null}
                </p>
                <p className="break-words font-mono text-xs text-ink-soft">
                  {[r.target_type && `${r.target_type} ${r.target_id ?? ""}`, Object.keys(r.detail).length ? JSON.stringify(r.detail) : null, r.ip_prefix, r.ua_family]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <span className={`justify-self-start rounded-full px-2 py-0.5 text-xs font-semibold ${OUTCOME_STYLE[r.outcome] ?? ""}`}>{r.outcome}</span>
            </li>
          ))}
        </ol>
      )}

      <nav aria-label="Pages" className="mt-4 flex items-center justify-between">
        {filter.page && filter.page > 1 ? (
          <Link href={query(filter.page - 1)} className="inline-flex min-h-11 items-center text-olive underline underline-offset-4">
            ← Newer
          </Link>
        ) : (
          <span />
        )}
        {more ? (
          <Link href={query((filter.page ?? 1) + 1)} className="inline-flex min-h-11 items-center text-olive underline underline-offset-4">
            Older →
          </Link>
        ) : null}
      </nav>

      <section className="mt-10" aria-labelledby="export-title">
        <h2 id="export-title" className="font-serif text-xl text-ink">
          Export
        </h2>
        {gate === "open" ? (
          <form method="post" action="/admin/log/export" className="mt-3 flex flex-wrap items-center gap-3">
            <input type="hidden" name="csrf" value={csrf} />
            {Object.entries(filter).map(([k, v]) => (v && k !== "page" ? <input key={k} type="hidden" name={k} value={String(v)} /> : null))}
            <button type="submit" className="min-h-11 rounded-md border border-olive px-4 text-sm font-semibold text-olive">
              Download CSV (current filters, up to 5,000 rows)
            </button>
            <span className="text-xs text-ink-soft">The export itself is logged.</span>
          </form>
        ) : (
          <div className="mt-3">
            <StepUpForm closed={gate === "closed"} csrf={csrf} path="/admin/log" what="export the log" />
          </div>
        )}
      </section>
    </AdminShell>
  );
}
