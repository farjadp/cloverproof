import type { MetadataRoute } from "next";
import { enabledLocales } from "@/i18n/config";
import { languageAlternates, siteUrl } from "@/lib/site";

// Privacy is left out while it is a draft (noindex) — add it after legal review.
export default function sitemap(): MetadataRoute.Sitemap {
  const languages = Object.fromEntries(
    Object.entries(languageAlternates()).map(([l, p]) => [l, `${siteUrl}${p}`]),
  );
  return enabledLocales.map((l) => ({
    url: `${siteUrl}/${l}`,
    lastModified: new Date(),
    changeFrequency: "monthly",
    priority: 1,
    alternates: { languages },
  }));
}
