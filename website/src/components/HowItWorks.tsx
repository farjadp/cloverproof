"use client";

import type { Dictionary } from "@/i18n/dictionaries";
import { useInView } from "./useInView";

const icons = [
  // Farm data: field rows
  <path key="a" d="M4 18 L12 6 L20 18 M8 18 L12 12 L16 18" />,
  // Engine: gear-ish
  <g key="b"><circle cx="12" cy="12" r="3.5" /><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" /></g>,
  // Agronomist review: check in circle
  <g key="c"><circle cx="12" cy="12" r="8" /><path d="M8 12.5l2.7 2.7L16 9.8" /></g>,
  // Proof: document
  <g key="d"><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v4h4M10 12h5M10 15.5h5" /></g>,
];

function Step({ step, i, total }: { step: { title: string; body: string }; i: number; total: number }) {
  const { ref, inView } = useInView<HTMLLIElement>(0.6);
  const highlight = i === 2;
  return (
    <li ref={ref} className="relative grid grid-cols-[3.5rem_1fr] gap-5 pb-12 last:pb-0">
      {i < total - 1 && (
        <span aria-hidden="true" className="absolute start-7 top-14 h-[calc(100%-3.5rem)] w-0.5 -translate-x-1/2 bg-ivory/15 rtl:translate-x-1/2">
          <span className={`block w-full origin-top bg-sage transition-transform duration-700 ${inView ? "scale-y-100" : "scale-y-0"} h-full`} />
        </span>
      )}
      <span
        className={`relative z-10 grid size-14 place-items-center rounded-full border-2 transition-all duration-500 ${
          inView ? (highlight ? "scale-110 border-sage bg-sage text-ink" : "border-sage bg-ink text-sage") : "border-ivory/20 bg-ink text-ivory/40"
        }`}
      >
        <svg viewBox="0 0 24 24" className="size-6 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          {icons[i]}
        </svg>
      </span>
      <div className={`transition-all duration-700 ${inView ? "translate-y-0 opacity-100" : "translate-y-3 opacity-40"}`}>
        <span className="text-sm font-semibold uppercase tracking-[0.14em] text-sage">{String(i + 1).padStart(2, "0")}</span>
        <h3 className="mt-1 font-serif text-2xl">{step.title}</h3>
        <p className="mt-2 max-w-md text-ivory/80">{step.body}</p>
      </div>
    </li>
  );
}

export function HowItWorks({ t }: { t: Dictionary }) {
  return (
    <section id="how" aria-labelledby="how-title" className="bg-ink text-ivory">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 py-24 sm:px-6 lg:grid-cols-[1fr_1.4fr] lg:px-8">
        <div className="lg:sticky lg:top-28 lg:self-start">
          <h2 id="how-title" className="font-serif text-4xl sm:text-5xl">{t.how.title}</h2>
          <p className="mt-4 max-w-sm text-ivory/80">{t.how.intro}</p>
        </div>
        <ol>
          {t.how.steps.map((step, i) => (
            <Step key={step.title} step={step} i={i} total={t.how.steps.length} />
          ))}
        </ol>
      </div>
    </section>
  );
}
