import Image from "next/image";
import type { Dictionary } from "@/i18n/dictionaries";
import hero from "../../public/images/hero-field.webp";

function Chip({ children, className }: { children: React.ReactNode; className: string }) {
  return (
    <div className={`absolute hidden items-center gap-2 rounded-xl border border-white/40 bg-ivory/90 px-4 py-3 text-sm text-ink shadow-[0_18px_40px_-20px_rgba(0,0,0,0.55)] backdrop-blur md:flex ${className}`}>
      {children}
    </div>
  );
}

export function Hero({ t }: { t: Dictionary }) {
  const c = t.hero.chips;
  return (
    <section className="relative isolate overflow-hidden bg-ink">
      <Image
        src={hero}
        alt={t.hero.imageAlt}
        priority
        placeholder="blur"
        sizes="100vw"
        className="absolute inset-0 -z-10 h-full w-full object-cover object-[center_70%]"
      />
      {/* Solid ink scrim for text contrast. */}
      <div aria-hidden="true" className="absolute inset-0 -z-10 bg-ink/50" />

      <div className="relative mx-auto grid min-h-[86vh] max-w-6xl items-center px-4 py-24 sm:px-6 lg:px-8">
        <div className="max-w-2xl text-ivory">
          <p className="mb-5 inline-flex items-center gap-2 rounded-full bg-ivory/15 px-3 py-1 text-sm font-semibold uppercase tracking-[0.14em] text-sage backdrop-blur">
            <span className="size-2 animate-pulse rounded-full bg-sage" aria-hidden="true" />
            {t.hero.eyebrow}
          </p>
          <h1 className="font-serif text-5xl leading-[1.04] tracking-tight sm:text-6xl lg:text-7xl">{t.hero.title}</h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ivory/90">{t.hero.lead}</p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <a href="#pilot" className="rounded-full bg-sage px-6 py-3.5 font-semibold text-ink shadow-lg transition-all hover:-translate-y-0.5 hover:bg-ivory">
              {t.hero.ctaPrimary}
            </a>
            <a href="#check" className="group inline-flex items-center gap-2 rounded-full border border-ivory/50 px-6 py-3.5 font-semibold text-ivory transition-colors hover:bg-ivory/10">
              {t.hero.ctaSecondary}
              <span aria-hidden="true" className="transition-transform group-hover:translate-x-1 rtl:-scale-x-100">→</span>
            </a>
          </div>
          <p className="mt-10 text-sm text-ivory/70">{t.hero.note}</p>
        </div>

        <Chip className="end-8 top-[22%] animate-float lg:end-16">
          <span className="text-ink-soft">{c.confidence}</span>
          <span className="rounded-full bg-sage px-2.5 py-0.5 text-xs font-bold uppercase">{c.confidenceValue}</span>
        </Chip>
        <Chip className="end-24 top-[46%] animate-float-slow lg:end-40">
          <span className="grid size-6 place-items-center rounded-full bg-olive text-xs text-ivory" aria-hidden="true">✓</span>
          <span className="font-semibold">{c.reviewed}</span>
        </Chip>
        <Chip className="bottom-[16%] end-10 animate-float lg:end-20">
          <span className="font-mono text-xs text-olive">v2</span>
          <span>{c.version}</span>
        </Chip>
      </div>
    </section>
  );
}
