# ADR 0003 — Website stack and internationalisation

- Status: Proposed
- Date: 2026-11-16
- Decider: Farjad Iranmehr

## Context
Farjad Iranmehr changed the build order to website → web app → mobile. The website must reach a global audience in eight languages: English, French, Italian, Spanish, Bulgarian, Finnish, Turkish, and Arabic (right-to-left). CLAUDE.md previously listed multi-language as out of scope; that restriction stays for the internal concierge tool only.

## Decision
- Website lives in `website/` in the monorepo: Next.js (App Router) + TypeScript + Tailwind.
- `next-intl` with locale-prefixed routes (`/en`, `/fr`, … `/ar`), messages in `website/messages/<locale>.json`.
- RTL-ready from the first commit: `dir` set per locale, Tailwind logical utilities only (`ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`, `text-start`); no `left`/`right` physical properties.
- Fonts chosen to cover Latin, Cyrillic (Bulgarian), Turkish and Arabic scripts.
- A locale goes live only after native-speaker review; machine/AI drafts are marked draft until then.
- `hreflang` + per-locale sitemap from the start.

## Consequences
- Slightly more setup now; adding a locale later is content work, not refactoring.
- Agronomy terms need a glossary per locale before translation.
- Translation review is a recurring cost to plan for.
