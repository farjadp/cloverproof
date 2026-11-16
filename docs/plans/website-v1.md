# Website v1 — plan

Order of surfaces (Farjad Iranmehr, 2026-11-16): **website → web app portal → mobile app**, one step at a time.

## Goal
Credibility + recruit 5–10 pilot farms for Feb–Apr 2027. Primary CTA: **Request a pilot field plan**.

## Scope
| | |
|---|---|
| Location | `website/` in this monorepo |
| Stack | Next.js (App Router) + TypeScript + Tailwind, static where possible |
| i18n | Built in from day one (`next-intl`, `/[locale]/` routes). Ship order: en → fr → it → es → bg → fi → tr → ar (RTL). One locale per step. |
| Pages | Landing (hero → problem → how it works → sample proof → principles → pilot CTA), Pilot request form, Privacy |
| Form | Supabase table `pilot_request`, explicit consent checkbox (PIPEDA / CASL / GDPR for EU locales) |
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
5. Pilot form → Supabase, with consent and spam protection.
6. QA: Lighthouse ≥ 90, mobile, keyboard/a11y, form end to end → preview deploy.
7. Then one locale at a time (fr, it, es, bg, fi, tr, ar), each reviewed by a native speaker before going live.

## Open items
- Contact email and legal entity name for the privacy notice and footer.
- Privacy notice needs legal review before launch (`legal-compliance-specialist`).
- Field image is an SVG illustration; swap for a licensed photo later if wanted.

## Owners
Design `product-designer` · copy `content-seo-strategist` · code `frontend-developer` · form/db `cp-database` · QA `cp-qa` · lead `cloverproof-lead`.
