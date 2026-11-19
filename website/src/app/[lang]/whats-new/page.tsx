import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { isEnabledLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/dictionaries";
import { formatDay, groupByMonth } from "@/lib/changelog";
import { languageAlternates } from "@/lib/site";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { StatusChip } from "@/components/StatusChip";

const PATH = "/whats-new";

export async function generateMetadata({ params }: PageProps<"/[lang]/whats-new">): Promise<Metadata> {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) return {};
  const t = await getDictionary(lang);
  const title = `${t.changelog.title} · CloverProof`;
  return {
    title,
    description: t.changelog.description,
    alternates: { canonical: `/${lang}${PATH}`, languages: languageAlternates(PATH) },
    openGraph: { type: "website", siteName: "CloverProof", title, description: t.changelog.description, url: `/${lang}${PATH}` },
  };
}

export default async function WhatsNew({ params }: PageProps<"/[lang]/whats-new">) {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) notFound();
  const t = await getDictionary(lang);
  const c = t.changelog;
  const kinds: Record<string, string> = c.kinds;

  return (
    <>
      <Header t={t} lang={lang} path={PATH} />
      <main id="main" className="mx-auto max-w-3xl px-4 py-14 sm:px-6 sm:py-16">
        <h1 className="font-serif text-4xl text-ink sm:text-5xl">{c.title}</h1>
        <p className="mt-4 text-lg leading-relaxed text-ink-soft">{c.intro}</p>

        {groupByMonth(c.entries, lang).map((month) => (
          <section key={month.key} aria-labelledby={`month-${month.key}`} className="mt-12">
            <h2 id={`month-${month.key}`} className="border-b-2 border-olive pb-2 font-serif text-2xl text-ink">{month.label}</h2>
            <ol className="divide-y divide-rule">
              {month.entries.map((entry) => (
                <li key={entry.title} className="py-5">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <time dateTime={entry.date} className="text-sm text-ink-soft">{formatDay(entry.date, lang)}</time>
                    <StatusChip>{kinds[entry.kind]}</StatusChip>
                  </div>
                  <h3 className="mt-2 font-semibold text-ink">{entry.title}</h3>
                  <p className="mt-1 leading-relaxed text-ink-soft">{entry.text}</p>
                </li>
              ))}
            </ol>
          </section>
        ))}

        <p className="mt-10">
          <Link href={`/${lang}/roadmap`} className="inline-flex min-h-11 items-center text-olive underline underline-offset-4">
            {c.roadmapLink}
          </Link>
        </p>
      </main>
      <Footer t={t} lang={lang} path={PATH} />
    </>
  );
}
