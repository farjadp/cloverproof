"use client";

import { useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";

type T = Dictionary["check"];
type Answers = Partial<Record<"soilTest" | "method" | "previousCrop" | "target", string>>;

/**
 * Interactive four-leaf clover for the field check; each heart-shaped leaf fills when a
 * question is answered. Kept as its own SVG (the official mark is a raster image and can't
 * fill leaf by leaf); leaf shape and stem echo the official mark.
 */
const LEAF = "M50 47C40 42 29 33 30 22C31 13 41 10 50 18C59 10 69 13 70 22C71 33 60 42 50 47Z";

function Clover({ filled }: { filled: number }) {
  return (
    <svg viewBox="0 0 100 110" className="size-40 drop-shadow-sm" aria-hidden="true">
      <path d="M53 53C58 70 60 86 70 104" className="fill-none stroke-olive" strokeWidth="5" strokeLinecap="round" />
      {[0, 90, 180, 270].map((deg, i) => (
        <g key={deg} transform={`rotate(${deg} 50 50)`}>
          <path
            d={LEAF}
            className={`transition-colors duration-500 ease-out ${i < filled ? "fill-olive stroke-olive" : "fill-sage-soft stroke-sage"}`}
            strokeWidth="2"
            strokeLinejoin="round"
          />
        </g>
      ))}
    </svg>
  );
}

function scope(a: Answers): "full" | "confirm" | "nOnly" {
  if (a.soilTest !== "yes") return "nOnly";
  return a.method === "yes" ? "full" : "confirm";
}

export function FieldCheck({ t }: { t: T }) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const questions = t.questions;
  const done = step >= questions.length;
  const filled = Object.keys(answers).length;

  function answer(id: string, v: string) {
    const next = { ...answers, [id]: v };
    // No soil test means the method question doesn't apply.
    if (id === "soilTest" && v !== "yes") {
      next.method = "skip";
      setAnswers(next);
      setStep(2);
      return;
    }
    setAnswers(next);
    setStep(step + 1);
  }

  function back() {
    const prev = step === 2 && answers.soilTest !== "yes" ? 0 : step - 1;
    const keep = Object.fromEntries(Object.entries(answers).filter(([k]) => questions.findIndex((q) => q.id === k) < prev));
    setAnswers(keep);
    setStep(Math.max(0, prev));
  }

  const result = t.results[scope(answers)];
  const gaps = (
    [
      answers.soilTest !== "yes" && "soilTest",
      answers.soilTest === "yes" && answers.method !== "yes" && "method",
      answers.previousCrop !== "yes" && "previousCrop",
      answers.target !== "yes" && "target",
    ].filter(Boolean) as (keyof T["gaps"])[]
  ).map((k) => t.gaps[k]);

  const q = questions[step];

  return (
    <section id="check" aria-labelledby="check-title" className="relative overflow-hidden bg-olive text-ivory">
      <div aria-hidden="true" className="pointer-events-none absolute -end-24 -top-24 size-96 rounded-full bg-sage/20 blur-3xl" />
      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.3fr] lg:px-8">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-sage">{t.eyebrow}</p>
          <h2 id="check-title" className="mt-3 font-serif text-3xl sm:text-4xl">{t.title}</h2>
          <p className="mt-4 text-ivory/80">{t.intro}</p>
          <div className="mt-8 flex items-center gap-5">
            <div className="rounded-full bg-ivory p-3">
              <Clover filled={done ? 4 : filled} />
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.14em] text-sage">{t.progress}</p>
              <p className="font-serif text-4xl" aria-live="polite">{done ? 4 : filled} / 4</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl bg-ivory p-6 text-ink shadow-[0_24px_60px_-30px_rgba(0,0,0,0.6)] sm:p-8">
          <div className="mb-6 flex gap-2" aria-hidden="true">
            {questions.map((_, i) => (
              <span key={i} className={`h-1.5 flex-1 rounded-full transition-colors duration-500 ${i < step || done ? "bg-olive" : i === step ? "bg-sage" : "bg-rule"}`} />
            ))}
          </div>

          {!done && q && (
            <div key={q.id} className="animate-pop">
              <h3 className="font-serif text-2xl">{q.q}</h3>
              {"hint" in q && q.hint && <p className="mt-2 text-sm text-ink-soft">{q.hint}</p>}
              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                {q.options.map((o) => (
                  <button
                    key={o.v}
                    type="button"
                    onClick={() => answer(q.id, o.v)}
                    className="rounded-xl border-2 border-rule bg-white px-4 py-4 text-start font-semibold transition-all hover:-translate-y-0.5 hover:border-olive hover:shadow-md active:translate-y-0"
                  >
                    {o.label}
                  </button>
                ))}
              </div>
              {step > 0 && (
                <button type="button" onClick={back} className="mt-6 text-sm font-semibold text-ink-soft underline underline-offset-4 hover:text-olive">
                  ← {t.back}
                </button>
              )}
            </div>
          )}

          {done && (
            <div className="animate-pop" aria-live="polite">
              <span className="inline-block rounded-full bg-sage px-3 py-1 text-xs font-bold uppercase tracking-wide">{result.tag}</span>
              <h3 className="mt-3 font-serif text-2xl">{result.title}</h3>
              <p className="mt-2 text-ink-soft">{result.body}</p>
              <div className="mt-5 border-t border-rule pt-4">
                <h4 className="text-sm font-semibold">{t.gapsTitle}</h4>
                {gaps.length ? (
                  <ul className="mt-2 space-y-1.5 text-sm text-ink-soft">
                    {gaps.map((g) => (
                      <li key={g} className="flex gap-2"><span className="text-olive">○</span>{g}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-olive">✓ {t.noGaps}</p>
                )}
              </div>
              <div className="mt-6 flex flex-wrap items-center gap-4">
                <a href="#pilot" className="rounded-full bg-olive px-5 py-3 font-semibold text-ivory transition-colors hover:bg-olive-deep">{t.cta}</a>
                <button type="button" onClick={() => { setAnswers({}); setStep(0); }} className="text-sm font-semibold text-ink-soft underline underline-offset-4 hover:text-olive">
                  {t.restart}
                </button>
              </div>
              <p className="mt-5 text-xs text-ink-soft">{t.disclaimer}</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
