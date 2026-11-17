# CloverProof blog: SEO / GEO requirements checklist (v0.1, 2026-11-17)

Scope: `/[lang]/blog` and `/[lang]/blog/[slug]` in `website/` (Next.js 16 App Router, 8 locales, ar = RTL). Posts in Postgres, multi-locale, human approval before publish. Each item should be something a developer or reviewer can tick. Sources are listed at the end as [S1] and so on.

## 0. Baseline gaps in the current code (fix before the blog ships)
- [ ] `sitemap.ts` sets `lastModified: new Date()` on every build. Google uses `lastmod` only when it is "consistently and verifiably" accurate [S6]. Use real content dates.
- [ ] `changeFrequency` and `priority` can be dropped. Google ignores both [S6].
- [ ] `languageAlternates()` in `src/lib/site.ts` lists every enabled locale. Posts need a per-post variant that lists only the translations that exist and qualify (section 4).

## 1. Per-post data model
Post (locale-independent): `id`, `translation_group_id`, `primary_locale`, `author_id`, `reviewer_id` (nullable), `og_image_id`, `status`, `created_at`.
Translation (one row per locale): every field below unless marked otherwise.
- [ ] `title` (H1), required, at most 70 chars, unique per locale.
- [ ] `meta_title`, at most 60 chars (warn above that), unique per locale. Falls back to `title`.
- [ ] `meta_description`, 70–160 chars, unique per locale, no placeholder text.
- [ ] `slug` per locale: lowercase, `[a-z0-9-]`, at most 75 chars, unique within its locale, stop words trimmed. Latin transliteration for bg and ar (pick one rule and test it). Slug is locked after first publish; a later change writes a 301 row to a `redirect` table.
- [ ] `canonical_url` defaults to the post's own locale URL. An override is allowed only to another URL on our own domain, and it is validated.
- [ ] `og_image`: at least 1200×630, under 300 KB, with `alt` per locale (required, at most 125 chars). Store 16:9, 4:3 and 1:1 crops for Article `image` [S2].
- [ ] `author` → `person` table: `name` (name only, no "Dr."/"by"), `honorific`, `job_title`, `credentials` (free text plus an optional verifiable link such as a professional registry), `bio` per locale, `profile_url` (our `/[lang]/team/[slug]` page), `same_as[]` (LinkedIn and similar). Each author gets a real profile page [S2][S4].
- [ ] `reviewer` → `person` table, with `is_human = true` enforced by a DB CHECK or trigger. `cp-agronomist` and any AI account can never be selected. Agronomic posts also need the reviewer to hold the `agronomist` role. Store `reviewed_at` and `review_scope` (agronomy / legal / editorial).
- [ ] `published_at` is set by the server at the moment of publish. It cannot be edited and cannot be earlier than `created_at` (no backdating).
- [ ] `updated_at` changes only on a "substantive update" toggle that requires a change note. Typo fixes do not change it.
- [ ] `sources[]`: `title`, `publisher`, `url`, `accessed_at`, `type` (guideline / peer-reviewed / government / dataset / other), `licence_note`. At least one source for any factual post.
- [ ] `faq[]`: `question`, `answer` (plain text, at most 300 chars), ordered. Every answer must also be visible on the page.
- [ ] `howto_steps[]` (optional): `name`, `text`, optional image. Shown as an ordered list.
- [ ] `primary_keyword` (internal only, never rendered), `secondary_keywords[]`, `cluster_id`, `funnel_stage`.
- [ ] `internal_links[]`: target post or page id, not a raw URL, so links survive slug changes. At least 2 out and 1 in before publish.
- [ ] `translation_status` per locale: `human_written` | `human_reviewed` | `machine` (with `machine_reviewed_by` and `machine_reviewed_at`).
- [ ] `index_policy`: `index` | `noindex`. Defaults to `noindex` until approved.
- [ ] `content_kind`: `agronomic` | `product` | `company` | `regulatory`. Drives the guardrails in section 8.

## 2. Rendering and HTML
- [ ] One `<h1>` per page (the title). H2 and H3 come from the editor with no skipped levels. The editor cannot insert an H1.
- [ ] `<article>` wraps the post. `<header>` holds the H1, byline, dates and reviewer. `<nav aria-label>` holds breadcrumbs and the TOC. `<aside>` holds related posts.
- [ ] Byline shows author name and link, "Reviewed by [human name, role]" only when a reviewer exists, and both dates as visible `<time datetime="ISO-8601+tz">`.
- [ ] Answer-first summary block: 40–60 words directly under the H1. Required field.
- [ ] TOC is generated from H2s for posts over about 800 words. Anchors are stable slug ids that do not change on re-render.
- [ ] Tables use `<table>`, `<caption>`, `<thead>` and `<th scope>`, never images of tables. They scroll horizontally on mobile.
- [ ] Images: `next/image` with explicit width and height (no CLS), required `alt` per locale (decorative images get `alt=""`), `loading="lazy"` except the LCP hero (`priority`/`fetchpriority="high"`), AVIF/WebP, served from our own domain.
- [ ] Visible breadcrumbs: Home › Blog › [Cluster] › Post. They match the BreadcrumbList markup.
- [ ] RTL: `dir="rtl"` on `ar`, logical CSS properties (`ms-`/`me-`), and the TOC and breadcrumb order mirror correctly. Checked with a screenshot test.
- [ ] `<html lang>` matches the route locale. Content in another language inside a post gets its own `lang` attribute.
- [ ] External links in the body use `rel="noopener"`. Sponsored or affiliate links are not allowed (vendor-neutral). No `nofollow` on cited sources.
- [ ] Sources render as a numbered "Sources" section with in-text references that link to it.

## 3. Structured data (JSON-LD, server-rendered)
- [ ] `BlogPosting`: Google lists no required properties. Recommended ones: `headline`, `image` (multiple ratios), `datePublished` and `dateModified` (ISO 8601 with timezone), `author` (one entry per Person with `name` and `url` or `sameAs`) [S2]. Also add `publisher` (Organization), `inLanguage` and `mainEntityOfPage`.
- [ ] `reviewedBy` (schema.org WebPage property) is emitted only for a human reviewer. CI fails if it resolves to an AI account.
- [ ] `BreadcrumbList` on every post, matching the visible breadcrumbs [S3].
- [ ] One sitewide `Organization` (`@id` = `${siteUrl}/#org`, `name` "CloverProof", `url`, `logo`, `sameAs`). Posts reference it by `@id`. Each author is a `Person` with `@id` = profile URL.
- [ ] FAQPage: Google stopped showing FAQ rich results on 2026-05-07 and removed the docs on 2026-06-15 [S1][S5]. Visible FAQs stay because they are useful to readers. Keep the JSON-LD only as low-cost, unverified GEO value, since Google says unused markup "does not cause problems" [S7]. Do not promise anyone a rich result. Decide yes or no in one place (a feature flag).
- [ ] HowTo: rich results deprecated since 2023-09-13 [S7]. Same rule as FAQPage: steps stay visible and the markup is optional.
- [ ] Do not emit `MedicalWebPage`, `Review` or `AggregateRating`, or any certification-like type.
- [ ] All markup matches visible text (Google requirement) [S4]. Validated in CI with the schema.org validator and Rich Results Test on 3 sample posts per locale.

## 4. International
- [ ] Hreflang only among translations of the same `translation_group_id` that are published and indexable. Every member lists itself and all others, and the links are reciprocal [S8].
- [ ] `machine` translations stay `noindex` and out of hreflang and the sitemap until a human reviews them. Unreviewed bulk machine translation fits Google's scaled-content-abuse example ("translating") [S9]. The page shows a visible "Machine translation" banner.
- [ ] `x-default` points to the `en` version if one exists, otherwise to the primary locale.
- [ ] A post that is not translated into the visitor's locale does not 404 and is not silently swapped for another language. The `/[lang]/blog` index shows only that locale's posts and can offer an "Also in English" link without hreflang.
- [ ] Blog index pages carry hreflang among locale indexes that have at least 1 post.
- [ ] `og:locale` comes from `ogLocale`. `og:locale:alternate` lists only the existing translations.

## 5. Indexing
- [ ] Sitemap: split into `sitemap-pages` and `sitemap-blog` (index file). One `<url>` per published, indexable translation, `lastmod` = `updated_at` (else `published_at`), with `xhtml:link` alternates matching section 4 [S6][S8]. No drafts, previews, noindex, machine-only or redirected URLs.
- [ ] RSS 2.0 or Atom feed per locale (`/[lang]/blog/feed.xml`) with `<link rel="alternate" type="application/rss+xml">` in `<head>`. Real dates, summary only or full text (decide once).
- [ ] Drafts and previews: served on `/preview/...` behind admin auth, with an `X-Robots-Tag: noindex, nofollow` header, never under `/[lang]/blog`. `robots.txt` disallows `/preview/` and `/admin/`. Auth is the real protection; robots is not access control.
- [ ] Tag and cluster archive pages are `noindex,follow` until they have at least 3 posts and an intro paragraph.
- [ ] Pagination uses plain crawlable `<a href>` links and self-canonical URLs per page.
- [ ] Unpublishing a post returns 410 (or a 301 to the closest post), and the post leaves the sitemap the same day.
- [ ] `llms.txt`: optional, low priority. It is a community proposal (llmstxt.org). Google says no "AI text files" are needed for its AI features [S4]. Ship one only if it costs under 1 hour and lists canonical pages. Never treat it as a ranking or citation lever.
- [ ] Search Console and Bing Webmaster verification uses a DNS or meta tag (no script). Submit the sitemap index.

## 6. AIO / GEO
- [ ] Each post opens with the answer-first summary (section 2), which can be quoted without surrounding context.
- [ ] Each H2 is phrased as the reader's question, and the first 1–2 sentences under it answer it directly.
- [ ] Defined terms (for example "4R nutrient stewardship", "Olsen P") get a one-sentence definition on first use, worded the same way across posts (glossary table, linked).
- [ ] Every factual sentence that a reader could quote carries an inline source reference (section 2). No uncited statistics.
- [ ] Entity consistency: the same Organization name, one-line description ("vendor-neutral fertilizer-decision software"), logo and `sameAs` on every page and in JSON-LD. Author names are identical everywhere.
- [ ] Visible freshness: a "Last updated" date plus the change note. A quarterly review job flags posts older than 12 months.
- [ ] Indexability is the only gate for Google AI features. Do not use `nosnippet` or a small `max-snippet` on posts we want cited [S4].
- [ ] Tracking: a monthly manual check of target queries in Google AI Overviews, ChatGPT search and Perplexity, logged in a sheet. No third-party script (section 7).

## 7. Performance and privacy budget (post page, mobile, p75)
- [ ] LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1 [S10]. Lighthouse CI on 1 post per locale fails the build if any is breached.
- [ ] The post is a Server Component and ships no client JS except the TOC highlight and the mobile menu. Under 70 KB gzipped JS on a post route.
- [ ] Fonts are self-hosted via `next/font` (subset, `display: swap`), with at most 2 families. The Arabic subset loads only on `/ar`.
- [ ] Hero image under 150 KB, total page weight under 1 MB.
- [ ] No third-party requests at all (CSP `default-src 'self'`). No analytics, embeds, social widgets or external fonts. YouTube, if ever used, is a link only.
- [ ] Posts are statically generated or ISR, and publishing triggers `revalidatePath` for the post, the index, the sitemap and the feed.

## 8. Editorial guardrails (automated pre-publish checks in admin; publish button disabled until all pass)
- [ ] **Number gate:** a regex scan for rates, yields, savings, prices and percentages (`kg/ha`, `lb/ac`, `bu/ac`, `t/ha`, `%`, `$`, `€`, `CAD`, digits next to N/P/K/P2O5/K2O). Any hit on an `agronomic` post needs each number linked to a human-agronomist validation record (reviewer + date), otherwise it is blocked.
- [ ] **Third-party approval gate:** blocks phrases such as "approved/endorsed/certified/recognised by", "OMAFRA-approved", "lab-certified", "buyer-approved" and partner or government names next to approval verbs, in all 8 locales (keyword list per locale, reviewed by a human).
- [ ] **AI-approval gate:** blocks "AI approves", "AI-approved", "approved by our AI" and equivalents per locale. Allowed wording: "a human agronomist approves every plan".
- [ ] **Reviewer gate:** `agronomic` posts cannot publish without a human agronomist reviewer. The "Reviewed by" line never shows an AI. If no review has happened, the page shows "Agronomist review pending" and the post stays `noindex`.
- [ ] **Source gate:** at least 1 source per post. Every source URL returns 200 (checked at publish and weekly). Agronomic claims cite a primary source such as a provincial guideline or peer-reviewed paper.
- [ ] **Vendor-neutrality gate:** no brand-specific product recommendation, affiliate parameter (`utm_`, `ref=`, `aff`) or price comparison.
- [ ] **Privacy gate:** the body HTML is sanitised server-side (allow-list). `<script>`, `<iframe>`, external `<img src>`, tracking pixels and inline event handlers are stripped. No real farmer or farm names without a stored consent record.
- [ ] **Date gate:** `published_at` comes from the server only, and the admin has no field for it.
- [ ] **Translation gate:** a `machine` locale cannot be set to `index` until `machine_reviewed_by` is a human.
- [ ] **SEO lint:** title and meta lengths, unique slug, H1 count of 1, no skipped headings, every image has `alt`, at least 2 internal links, FAQ answers visible, JSON-LD validates.
- [ ] **Approval log:** an append-only `post_approval` row (approver, role, timestamp, version hash). Publish requires one approval from a human who is not the author.

## Sources
- [S1] FAQ structured data (deprecated, docs removed): https://developers.google.com/search/docs/appearance/structured-data/faqpage
- [S2] Article structured data: https://developers.google.com/search/docs/appearance/structured-data/article
- [S3] Breadcrumb structured data: https://developers.google.com/search/docs/appearance/structured-data/breadcrumb
- [S4] AI features and your website: https://developers.google.com/search/docs/appearance/ai-features
- [S5] Search Central documentation updates (2026-05-08, 2026-06-15): https://developers.google.com/search/updates
- [S6] Build and submit a sitemap: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- [S7] Changes to HowTo and FAQ rich results (2023): https://developers.google.com/search/blog/2023/08/howto-faq-changes
- [S8] Localized versions / hreflang: https://developers.google.com/search/docs/specialty/international/localized-versions
- [S9] Spam policies (scaled content abuse): https://developers.google.com/search/docs/essentials/spam-policies
- [S10] Core Web Vitals thresholds: https://web.dev/articles/vitals
