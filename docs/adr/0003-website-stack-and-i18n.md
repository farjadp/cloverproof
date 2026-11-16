# ADR 0003 — Website stack and internationalisation

- Status: Accepted (2026-11-16)
- Date: 2026-11-16
- Decider: Farjad Iranmehr

## Context
Farjad Iranmehr changed the build order to website → web app → mobile. The website must reach a global audience in eight languages: English, French, Italian, Spanish, Bulgarian, Finnish, Turkish, and Arabic (right-to-left). CLAUDE.md previously listed multi-language as out of scope; that restriction stays for the internal concierge tool only.

## Decision
- Website lives in `website/` in the monorepo: Next.js (App Router) + TypeScript + Tailwind.
- Next.js 16 built-in i18n pattern (no extra library): `src/proxy.ts` redirects to a locale prefix (`/en`, `/fr`, … `/ar`), `app/[lang]/` routes, dictionaries in `website/src/messages/<locale>.json` loaded server-side. `next-intl` was dropped: one less dependency, and it is not needed for static marketing copy.
- Locale list and launch status live in `website/src/i18n/config.ts`; a locale is `enabled` only after native review.
- RTL-ready from the first commit: `dir` set per locale, Tailwind logical utilities only (`ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`, `text-start`); no `left`/`right` physical properties.
- Fonts: Source Serif 4 + Source Sans 3 (Latin, Latin-ext, Cyrillic). An Arabic face is added when `ar` is enabled.
- A locale goes live only after native-speaker review; machine/AI drafts are marked draft until then.
- `hreflang` + per-locale sitemap from the start.

## Consequences
- Slightly more setup now; adding a locale later is content work, not refactoring.
- Agronomy terms need a glossary per locale before translation.
- Translation review is a recurring cost to plan for.

## Amendment — 2026-11-16
Farjad Iranmehr decided to enable all locales with machine translation; native reviews follow per locale.
- Supersedes "A locale goes live only after native-speaker review" and "a locale is `enabled` only after native review".
- Every non-English file carries `meta.translationStatus` (`machine — review pending` until a native reviewer signs off, then `reviewed — <name/role>, <date>`).
- Terms are fixed in `website/src/messages/glossary.md`; reviewers check the glossary first.
- `npm test` fails if any locale misses a key, changes a `{placeholder}` or translates a logic value.
- Arabic uses Noto Naskh Arabic (headings) + IBM Plex Sans Arabic (body), loaded only for `lang="ar"`.
- Risk accepted: wording errors in machine-translated legal text (privacy notice, consent) until review; the privacy notice stays marked "draft".

Review status (open item, owner: `cp-website` with native reviewers via CPO):

| Locale | Status |
|---|---|
| en | source |
| fr | machine — review pending |
| it | machine — review pending |
| es | machine — review pending |
| bg | machine — review pending |
| fi | machine — review pending |
| tr | machine — review pending |
| ar | machine — review pending |
