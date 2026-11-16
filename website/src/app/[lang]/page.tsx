import { notFound } from "next/navigation";
import { isEnabledLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/dictionaries";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { Problem } from "@/components/Problem";
import { FieldCheck } from "@/components/FieldCheck";
import { HowItWorks } from "@/components/HowItWorks";
import { SampleProof } from "@/components/SampleProof";
import { Principles } from "@/components/Principles";
import { Pilot } from "@/components/Pilot";
import { Faq } from "@/components/Faq";
import { Footer } from "@/components/Footer";

export default async function Home({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) notFound();
  const t = await getDictionary(lang);

  return (
    <>
      <Header t={t} lang={lang} />
      <main id="main">
        <Hero t={t} />
        <Problem t={t} />
        <FieldCheck t={t.check} />
        <HowItWorks t={t} />
        <SampleProof t={t} />
        <Principles t={t} />
        <Pilot t={t} lang={lang} />
        <Faq t={t} />
      </main>
      <Footer t={t} lang={lang} />
    </>
  );
}
