import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Source_Sans_3, Source_Serif_4 } from "next/font/google";
import { enabledLocales, isEnabledLocale, localeMeta } from "@/i18n/config";
import { getDictionary } from "@/i18n/dictionaries";
import "../globals.css";

// Latin-ext covers French, Italian, Spanish, Finnish, Turkish; Cyrillic covers Bulgarian.
// Arabic gets its own font when the `ar` locale is enabled (ADR 0003).
const serif = Source_Serif_4({ subsets: ["latin", "latin-ext", "cyrillic"], variable: "--font-source-serif" });
const sans = Source_Sans_3({ subsets: ["latin", "latin-ext", "cyrillic"], variable: "--font-source-sans" });

// Absolute base for Open Graph and alternate URLs. SITE_URL wins (custom domain later);
// Railway sets RAILWAY_PUBLIC_DOMAIN automatically.
const siteUrl =
  process.env.SITE_URL ??
  (process.env.RAILWAY_PUBLIC_DOMAIN ? `https://${process.env.RAILWAY_PUBLIC_DOMAIN}` : "http://localhost:3000");

export function generateStaticParams() {
  return enabledLocales.map((lang) => ({ lang }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: LayoutProps<"/[lang]">): Promise<Metadata> {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) return {};
  const t = await getDictionary(lang);
  return {
    metadataBase: new URL(siteUrl),
    title: t.meta.title,
    description: t.meta.description,
    alternates: {
      languages: Object.fromEntries(enabledLocales.map((l) => [l, `/${l}`])),
    },
  };
}

export default async function LocaleLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) notFound();

  return (
    <html lang={lang} dir={localeMeta[lang].dir} className={`${serif.variable} ${sans.variable}`}>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
