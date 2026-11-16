"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import { CloverMark } from "./Logo";
import { useInView } from "./useInView";

function Typed({ text, start }: { text: string; start: boolean }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!start || n >= text.length) return;
    const id = setTimeout(() => setN(n + 1), 55);
    return () => clearTimeout(id);
  }, [start, n, text.length]);
  return (
    <span>
      {text.slice(0, n)}
      {start && n < text.length && <span className="animate-pulse">▍</span>}
    </span>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-[0.12em] text-ink-soft">{label}</dt>
      <dd className="mt-1 font-semibold text-ink">{value}</dd>
    </div>
  );
}

export function SampleProof({ t }: { t: Dictionary }) {
  const p = t.proof;
  const { ref, inView } = useInView<HTMLElement>(0.3);
  const step = ["delay-[200ms]", "delay-[500ms]", "delay-[800ms]"];
  const show = (i: number) => `transition-all duration-500 ${step[i] ?? ""} ${inView ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-3"}`;
  return (
    <section id="proof" aria-labelledby="proof-title" className="overflow-x-clip border-t border-rule">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.6fr] lg:px-8 [&>*]:min-w-0">
        <div>
          <h2 id="proof-title" className="font-serif text-3xl text-ink sm:text-4xl">{p.title}</h2>
          <p className="mt-4 text-ink-soft">{p.intro}</p>
          <p className="mt-8 border-s-2 border-sage ps-4 text-sm text-ink-soft">{p.disclaimer}</p>
        </div>

        <article ref={ref} aria-label={p.docTitle} className="relative rotate-[0.4deg] border border-rule bg-white transition-transform duration-500 hover:rotate-0 shadow-[0_1px_0_var(--color-rule),0_12px_32px_-24px_var(--color-ink)]">
          <header className="flex items-center justify-between gap-4 border-b border-rule px-6 py-4">
            <div className="flex items-center gap-3">
              <CloverMark className="h-6 w-auto" />
              <span className="font-serif text-lg text-ink">{p.docTitle}</span>
              <span className="rounded bg-sand px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wider text-ink-soft">{p.sampleTag}</span>
            </div>
            <span className="font-mono text-xs text-ink-soft">{p.docId} · —</span>
          </header>

          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 px-6 py-5 sm:grid-cols-4">
            <Meta label={p.field} value={p.fieldValue} />
            <Meta label={p.crop} value={p.cropValue} />
            <Meta label={p.season} value={p.seasonValue} />
            <Meta label={p.soilTest} value={p.soilTestValue} />
          </dl>

          <div className="overflow-x-auto px-6">
            <table className="w-full min-w-[30rem] text-start text-sm">
              <thead>
                <tr className="border-y border-rule text-xs uppercase tracking-[0.12em] text-ink-soft">
                  <th scope="col" className="py-2 text-start font-semibold">{p.nutrient}</th>
                  <th scope="col" className="py-2 text-start font-semibold">{p.rate}</th>
                  <th scope="col" className="py-2 text-start font-semibold">{p.timing}</th>
                  <th scope="col" className="py-2 text-start font-semibold">{p.confidence}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {p.rows.map((r, i) => (
                  <tr key={r.nutrient} className={show(i)}>
                    <th scope="row" className="py-3 text-start font-semibold text-ink">{r.nutrient}</th>
                    <td className="py-3 text-ink">{r.rate}</td>
                    <td className="py-3 text-ink-soft">{r.timing}</td>
                    <td className="py-3">
                      {r.confidence === "—" ? (
                        <span className="text-ink-soft">—</span>
                      ) : (
                        <span className="rounded-full bg-sage px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-ink">{r.confidence}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="m-6 bg-ivory p-4">
            <h3 className="text-sm font-semibold text-ink">{p.whyTitle}</h3>
            <ul className="mt-2 list-disc space-y-1 ps-5 text-sm text-ink-soft">
              {p.whyLines.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>

          <footer className="grid grid-cols-2 gap-4 border-t border-rule px-6 py-4 text-sm sm:grid-cols-3">
            <Meta label={p.reviewer} value={p.reviewerValue} />
            <Meta label={p.versions} value={p.versionsValue} />
            <div>
              <dt className="text-xs uppercase tracking-[0.12em] text-ink-soft">{p.fingerprint}</dt>
              <dd className="mt-1 font-mono text-olive"><Typed text={p.fingerprintValue} start={inView} /></dd>
            </div>
          </footer>

          {inView && (
            <div aria-hidden="true" className="pointer-events-none absolute bottom-5 end-5 animate-stamp rounded-md border-[3px] border-olive bg-white/70 px-3 py-0.5 font-serif text-base font-bold uppercase tracking-widest text-olive opacity-90 [animation-delay:1.3s] sm:bottom-28 sm:end-10 sm:border-4 sm:px-4 sm:py-1 sm:text-2xl">
              {p.stamp}
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
