import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { isEnabledLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/dictionaries";
import { languageAlternates } from "@/lib/site";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export async function generateMetadata({ params }: PageProps<"/[lang]/privacy">): Promise<Metadata> {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) return {};
  const t = await getDictionary(lang);
  const title = `${t.privacy.title} · CloverProof`;
  return {
    title,
    description: t.privacy.description,
    // Draft until legal review: keep out of search results.
    robots: { index: false, follow: true },
    alternates: { canonical: `/${lang}/privacy`, languages: languageAlternates("/privacy") },
    openGraph: { type: "website", siteName: "CloverProof", title, description: t.privacy.description, url: `/${lang}/privacy` },
  };
}

export default async function Privacy({ params }: PageProps<"/[lang]/privacy">) {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) notFound();
  const t = await getDictionary(lang);

  return (
    <>
      <Header t={t} lang={lang} />
      <main id="main" className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <h1 className="font-serif text-4xl text-ink">{t.privacy.title}</h1>
        <p className="mt-3 inline-block rounded bg-sage-soft px-3 py-1 text-sm font-semibold text-olive">{t.privacy.draft}</p>
        <p className="mt-3 text-sm text-ink-soft">{t.privacy.updated}</p>
        <div className="mt-10 space-y-8">
          {t.privacy.sections.map((s) => (
            <section key={s.h}>
              <h2 className="font-serif text-2xl text-ink">{s.h}</h2>
              <p className="mt-2 leading-relaxed text-ink-soft">{s.p}</p>
            </section>
          ))}
        </div>
      </main>
      <Footer t={t} lang={lang} />
    </>
  );
}
