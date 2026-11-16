import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { IBM_Plex_Sans_Arabic, Noto_Naskh_Arabic, Source_Sans_3, Source_Serif_4 } from "next/font/google";
import { enabledLocales, isEnabledLocale, localeMeta } from "@/i18n/config";
import { getDictionary } from "@/i18n/dictionaries";
import { languageAlternates, ogLocale, siteUrl } from "@/lib/site";
import "../globals.css";

// `subsets` only controls which files are preloaded (LCP). Every subset stays declared via
// unicode-range, so latin-ext (fr, it, es, fi, tr) and cyrillic (bg) glyphs load on demand.
// Arabic: Noto Naskh Arabic (headings) + IBM Plex Sans Arabic (body), only attached to <html lang="ar">.
const serif = Source_Serif_4({ subsets: ["latin"], variable: "--font-source-serif" });
const sans = Source_Sans_3({ subsets: ["latin"], variable: "--font-source-sans" });
const arabicSerif = Noto_Naskh_Arabic({ subsets: ["arabic"], variable: "--font-arabic-serif", preload: false });
const arabicSans = IBM_Plex_Sans_Arabic({ subsets: ["arabic"], weight: ["400", "600", "700"], variable: "--font-arabic-sans", preload: false });

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
    applicationName: "CloverProof",
    alternates: { canonical: `/${lang}`, languages: languageAlternates() },
    openGraph: {
      type: "website",
      siteName: "CloverProof",
      locale: ogLocale[lang],
      url: `/${lang}`,
      title: t.meta.title,
      description: t.meta.description,
    },
    twitter: { card: "summary_large_image", title: t.meta.title, description: t.meta.description },
  };
}

export default async function LocaleLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!isEnabledLocale(lang)) notFound();

  return (
    <html lang={lang} dir={localeMeta[lang].dir} className={`${serif.variable} ${sans.variable} ${lang === "ar" ? `${arabicSerif.variable} ${arabicSans.variable}` : ""}`}>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
