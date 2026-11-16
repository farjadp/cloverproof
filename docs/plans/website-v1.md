# Website v1 — plan

Order of surfaces (Farjad Iranmehr, 2026-11-16): **website → web app portal → mobile app**, one step at a time.

## Goal
Credibility + recruit 5–10 pilot farms for Feb–Apr 2027. Primary CTA: **Request a pilot field plan**.

## Scope
| | |
|---|---|
| Location | `website/` in this monorepo |
| Stack | Next.js (App Router) + TypeScript + Tailwind, static where possible |
| i18n | Built in from day one (native Next.js i18n, `/[lang]/` routes, ADR 0003). Ship order: en → fr → it → es → bg → fi → tr → ar (RTL). One locale per step. |
| Pages | Landing (hero → problem → how it works → sample proof → principles → pilot CTA), Pilot request form, Privacy |
| Form | Railway Postgres table `pilot_request` (ADR 0004), explicit consent checkbox (PIPEDA / CASL / GDPR for EU locales) |
| Audience | Global, English first |
| Design | Google Stitch project (landing page screens added to the existing CloverProof design system) |
| Hosting | Free preview URL first; production host + domain decided before launch (no paid service without approval) |

## Content rules
- No agronomic numbers anywhere. Sample proof shows "—".
- No claim that any third party accepts or approves a CloverProof document.
- No yield or savings promises.
- Stitch mockups contain invented numbers — layout reference only, never copied.

## Steps
1. ✅ Design landing page in Stitch → approved by Farjad Iranmehr (2026-11-16).
2. ✅ ADR 0003 accepted.
3. ✅ Scaffold `website/` with i18n + RTL-ready layout.
4. ✅ Landing + privacy (draft) in English. Run: `npm --prefix website run dev`.
5. ✅ Pilot form → Railway Postgres (`pilot_request`), consent text stored, honeypot spam trap. Live: https://website-production-a1991e11.up.railway.app
6. ✅ Redesign + official logo, icons, OG image, flag language menu (S1, live).
7. QA: Lighthouse ≥ 90, mobile, keyboard/a11y, form end to end → preview deploy.
8. ✅ All 8 locales live with machine translation (Farjad Iranmehr, 2026-11-16; ADR 0003 amendment). Native review per locale follows; status in ADR 0003 and each file's `meta.translationStatus`.

## Open items
- Contact email and legal entity name for the privacy notice and footer.
- Privacy notice needs legal review before launch (`legal-compliance-specialist`).

## Owners
Code, SEO, a11y, deploy `cp-website` · design/images `cp-design` · copy `content-seo-strategist` · QA `cp-qa` · reports to `cto` → CPO.

## Sprint S2 (Nov 30 – Dec 11) — website goals
| # | Item | Done when |
|---|---|---|
| 1 | SEO basics | Per-page title/description/canonical, `sitemap.xml`, `robots.txt`, hreflang alternates (enabled locales + `x-default`); validated on the live URL |
| 2 | Lighthouse ≥ 90 mobile | Performance, Accessibility, Best Practices, SEO each ≥ 90 on `/en` and `/en/privacy` (mobile preset); scores recorded in the review |
| 3 | Keyboard / a11y pass | Every control reachable and visible on focus; field check, language menu and 3-step form usable by keyboard only; axe: 0 serious/critical |
| 4 | Pilot-funnel counts | Server-side only, from `pilot_request` (requests per day/locale); no third-party tracker without Farjad Iranmehr's go |
| 5 | DB switch | `pilot_request` on the shared PostGIS DB per `docs/runbook-db-switch.md`, in a window agreed with `cloverproof-lead`, once PostGIS is healthy |

Status (2026-11-16, commit `62310a5`, live):
- ✅ 1 SEO basics — robots.txt, sitemap.xml, canonical, hreflang + x-default, Open Graph/Twitter. Privacy stays `noindex` and out of the sitemap until legal review (deliberate; its Lighthouse SEO = 69 for that reason only).
- ✅ 2 Lighthouse mobile, live: `/en` 95 / 100 / 100 / 100 · `/en/privacy` 100 / 100 / 100 / 69 (perf / a11y / best practices / SEO).
- ✅ 3 Keyboard / a11y — axe 0 violations at 375 + 1280 px in 5 states (page, language menu open, field check done, form step 2, privacy); focus moves to the new step in the field check and the form; proof table scroll region focusable.
- ⏳ 4 Funnel counts — request counts per day/locale need no schema change; a request *rate* needs a server-side visit counter (new table), which waits for the shared DB (item 5).
- ⏳ 5 DB switch — waiting for PostGIS to be healthy and a window with `cloverproof-lead`.

Test gate on every deploy: `npm run lint`, `npm run build`, 375 px + 1280 px checks, no horizontal scroll, Lighthouse score noted.
Learning loop: `docs/sprints/S2-website-review.md` + retro at sprint end, summary to the CPO, standard report to `documentation`.
Later: S3 growth landing-page fixes (via CPO) · S4 French, enabled only after native review.

Decided (Farjad Iranmehr, 2026-11-16): flags stay — UK for English, Arab League for Arabic.
Before public launch (deferred by Farjad Iranmehr): contact email + legal entity in privacy notice and footer; privacy legal review.
Still open: design feedback on v1.
