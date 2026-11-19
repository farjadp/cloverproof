import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { isEnabledLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/dictionaries";
import { languageAlternates } from "@/lib/site";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { StatusChip } from "@/components/StatusChip";

const PATH = "/roadmap";
const STAGES = ["now", "next", "later"] as const;

export async function generateMetadata({ params }: PageProps<"/[lang]/roadmap">): Promise<Metadata> {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) return {};
  const t = await getDictionary(lang);
  const title = `${t.roadmap.title} · CloverProof`;
  return {
    title,
    description: t.roadmap.description,
    alternates: { canonical: `/${lang}${PATH}`, languages: languageAlternates(PATH) },
    openGraph: { type: "website", siteName: "CloverProof", title, description: t.roadmap.description, url: `/${lang}${PATH}` },
  };
}

export default async function Roadmap({ params }: PageProps<"/[lang]/roadmap">) {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) notFound();
  const t = await getDictionary(lang);
  const r = t.roadmap;
  const kinds: Record<string, string> = r.kinds;

  return (
    <>
      <Header t={t} lang={lang} path={PATH} />
      <main id="main" className="mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-16 lg:px-8">
        <h1 className="font-serif text-4xl text-ink sm:text-5xl">{r.title}</h1>
        <p className="mt-4 max-w-2xl text-lg leading-relaxed text-ink-soft">{r.intro}</p>

        <section aria-labelledby="today" className="mt-10 max-w-3xl border-s-4 border-olive bg-ivory px-5 py-4">
          <h2 id="today" className="font-semibold text-ink">{r.status.title}</h2>
          <p className="mt-1 leading-relaxed text-ink-soft">{r.status.text}</p>
        </section>

        <div className="mt-14 grid gap-12 lg:grid-cols-3 lg:gap-10">
          {STAGES.map((stage) => (
            <section key={stage} aria-labelledby={`stage-${stage}`} className="border-t-2 border-olive pt-5">
              <h2 id={`stage-${stage}`} className="font-serif text-3xl text-ink">{r[stage].title}</h2>
              <p className="mt-1 text-sm text-ink-soft">{r[stage].intro}</p>
              <ul className="mt-4 divide-y divide-rule">
                {r[stage].items.map((item) => (
                  <li key={item.title} className="py-5">
                    <StatusChip>{kinds[item.kind]}</StatusChip>
                    <h3 className="mt-2 font-semibold text-ink">{item.title}</h3>
                    <p className="mt-1 leading-relaxed text-ink-soft">{item.text}</p>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>

        <section aria-labelledby="tell-us" className="mt-14 rounded-lg bg-sand p-6 sm:p-8">
          <h2 id="tell-us" className="font-serif text-2xl text-ink">{r.cta.title}</h2>
          <p className="mt-2 max-w-2xl leading-relaxed text-ink-soft">{r.cta.text}</p>
          <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-3">
            <a href={`/${lang}#pilot`} className="inline-flex min-h-11 items-center rounded-full bg-olive px-5 py-2 font-semibold text-ivory transition-colors hover:bg-olive-deep">
              {r.cta.button}
            </a>
            <Link href={`/${lang}/whats-new`} className="inline-flex min-h-11 items-center text-olive underline underline-offset-4">
              {r.cta.changelog}
            </Link>
          </div>
        </section>
      </main>
      <Footer t={t} lang={lang} path={PATH} />
    </>
  );
}
