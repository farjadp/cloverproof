import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { isEnabledLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/dictionaries";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export async function generateMetadata({ params }: PageProps<"/[lang]/privacy">): Promise<Metadata> {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) return {};
  const t = await getDictionary(lang);
  return { title: `${t.privacy.title} · CloverProof`, robots: { index: false } };
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
