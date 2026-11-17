import type { Metadata } from "next";
import { Source_Sans_3, Source_Serif_4 } from "next/font/google";
import "../globals.css";

// Separate root layout: the admin is English only, never localised or indexed (ADR 0012).
const serif = Source_Serif_4({ subsets: ["latin"], variable: "--font-source-serif" });
const sans = Source_Sans_3({ subsets: ["latin"], variable: "--font-source-sans" });

export const metadata: Metadata = {
  title: { default: "CloverProof admin", template: "%s · CloverProof admin" },
  robots: { index: false, follow: false, nocache: true },
  referrer: "no-referrer",
};

export const dynamic = "force-dynamic";

export default function AdminRootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr" className={`${serif.variable} ${sans.variable}`}>
      <body className="min-h-dvh bg-sand text-ink">{children}</body>
    </html>
  );
}
