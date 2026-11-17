# ADR 0014 — Website blog: editor, content model, publishing (DRAFT)

- Status: **Proposed** (2026-11-17) — Farjad Iranmehr's decision
- Decider: Farjad Iranmehr · Author: `cp-website`
- Related: ADR 0003 (i18n, machine translation), ADR 0011, `docs/plans/website-admin.md` (P3, data model §5), SEO checklist `docs/plans/website-admin-seo-checklist.md`
- Number provisional.

## Context
A multi-locale (8 locales) blog for SEO, Google AI Overviews and generative engines, with a strong editor: headings, images, tables, FAQ blocks, internal links, drafts, scheduled publish, revisions. Human approval before publishing. Future agents (P4) will create drafts.

## Editor options
### A — TipTap 3 open-source (recommended)
ProseMirror-based, MIT (core + StarterKit, Table, Image, Link, Placeholder, CharacterCount). Custom nodes are first-class: `faq` (question/answer pairs), `howto` (ordered steps), `sources` (citations), `callout`, `internalLink` (post picker storing post id, not URL). Content stored as ProseMirror JSON; HTML generated server-side (`@tiptap/html` / static renderer) without a browser. Strict schema = clean semantic HTML by construction. Only open-source extensions; no TipTap Pro/Cloud (paid, licence).
### B — Lexical (Meta, MIT)
Strong, fast; React-first plugin model; tables/custom nodes more work; server-side HTML needs a headless editor + DOM shim. Smaller extension ecosystem for our blocks.
### C — Markdown/MDX in an editor
Simple and diffable, but weak for non-technical editors, tables/FAQ blocks need custom syntax, MDX executes code (risk with future agent content).

## Content model and publishing
- `website_post` (language-neutral) → `website_post_translation` per locale (slug, meta, body JSON + rendered sanitised HTML, status, `translation_status` source | human | machine_pending_review, author, human reviewer, agronomy validation).
- Revisions: every save inserts `website_post_revision` (append-only); diff between revisions in the editor; restore = new revision.
- Workflow: draft → in_review → (editor/admin) published or scheduled. Author can't publish. P4 agent output enters as `draft` with `origin=agent`; same human gate.
- Scheduled publish needs **no job**: public queries use `status in (published, scheduled) and publish_at <= now()`; pages use ISR (`revalidate` ≈ 5 min) + `revalidateTag` on publish.
- Rendering: HTML produced at save from the JSON through a node allowlist, then sanitised (no script/style/iframe/on*/javascript: URLs); public pages render the stored HTML in a Server Component; JSON-LD (`BlogPosting`, `BreadcrumbList`, `Organization`, `Person`, `FAQPage`/`HowTo` from the blocks) generated from structured fields, not parsed from HTML.
- Media: private Railway Bucket (S3 API, `@aws-sdk/client-s3`, Apache-2.0); upload validated by magic bytes (JPEG/PNG/WebP/AVIF), ≤ 5 MB, EXIF stripped and resized with `sharp` (LGPL libvips — already allowed by name); served via `/media/[key]` route with immutable cache headers and `next/image`. **Bucket usage cost needs Farjad Iranmehr's go.**
- SEO: per-translation meta/canonical/OG; hreflang only between existing translations + `x-default`; sitemap entries with `lastmod`; RSS per locale; `llms.txt` listing published posts; `/[lang]/blog`, `/[lang]/blog/[slug]`, tag pages `noindex` until they have ≥ N posts.
- Pre-publish checks (blocking unless overridden by an admin with a reason, logged): agronomic numbers/units (kg/ha, lb/ac, mg/kg, ppm, bu/ac, %, $ near nutrient words) require `agronomy_validated_by` (human); third-party-approval phrases ("approved/endorsed/certified by …", "accepted by OMAFRA/CFIA/…"); AI-approval wording; missing meta/alt/sources; "no soil test" claims must match the strict wording. Rules reviewed by `cp-agronomy-guard`.

## Decision (proposed)
TipTap open-source, JSON source of truth, rendered sanitised HTML, no-job scheduling, private Bucket for media.

## Consequences
New deps (all MIT/Apache): `@tiptap/*` open-source packages, `@aws-sdk/client-s3`, a sanitiser (`sanitize-html`, MIT). Admin JS (editor) loads only under `/admin`; public post pages ship no editor code. ADR 0003's machine-translation status rules apply per translation.
