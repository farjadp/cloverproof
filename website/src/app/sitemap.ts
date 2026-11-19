import type { MetadataRoute } from "next";
import { enabledLocales } from "@/i18n/config";
import { languageAlternates, siteUrl } from "@/lib/site";

// Privacy is left out while it is a draft (noindex) — add it after legal review.
const PAGES = [
  { path: "", priority: 1 },
  { path: "/roadmap", priority: 0.6 },
  { path: "/whats-new", priority: 0.6 },
];

export default function sitemap(): MetadataRoute.Sitemap {
  return PAGES.flatMap(({ path, priority }) => {
    const languages = Object.fromEntries(
      Object.entries(languageAlternates(path)).map(([l, p]) => [l, `${siteUrl}${p}`]),
    );
    return enabledLocales.map((l) => ({
      url: `${siteUrl}/${l}${path}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority,
      alternates: { languages },
    }));
  });
}
