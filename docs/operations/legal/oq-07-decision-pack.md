# OQ-07 decision pack — legal sign-off for the 2027 pilot

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> For Farjad Iranmehr (founder) and the lawyer he engages. Prepared by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO, 2026-11-16. Nothing was sent, signed or filed.
> Deadline driver: human agronomist named before the S5 concierge gate (2027-01-29); first real-farm plan Feb 2027. Counsel review must finish before any farm signs.

## 1. Documents that need sign-off

| # | Document (`docs/operations/legal/`) | Who signs off | Blocks |
|---|---|---|---|
| 1 | `privacy-notice.md` Part A (v0.2) | Lawyer → Farjad | Pilot enrolment |
| 2 | `privacy-notice.md` Part B (website page, NB-WEB-05) | Lawyer → Farjad | Removing the "Draft" label |
| 3 | `consent-wording.md` (form boxes A/B; pilot consent; optional C/D/E) | Lawyer → Farjad | Form release; enrolment |
| 4 | `pilot-terms.md` (esp. §3 review, §9 liability, §12 law/forum) | Lawyer → Farjad signs per farm | Any farm signing |
| 5 | `proof-pdf-wording.md` block I (disclaimer) + reviewer line | Lawyer → Farjad; `cp-agronomy-guard` enforces | First farmer-facing PDF |
| 6 | Railway DPA (self-serve, railway.com/legal/dpa) | Lawyer review → Farjad signs | Any real farm data on Railway |
| 7 | AI provider terms — not needed under D-7 (de-identified only); DPA required before any change | Lawyer → Farjad accepts | Any identifiable pilot data sent to an AI provider (forbidden under D-7) |
| 8 | Human agronomist agreement (if contractor) | Lawyer drafts → Farjad + agronomist sign | Any approval |

## 2. Decisions only Farjad can make

| # | Decision | Options / recommendation | Fills |
|---|---|---|---|
| D-1 | **Legal entity** that runs CloverProof | Existing corporation or a new one. Recommend: one entity for the website, pilot terms and Railway account — same name everywhere. | `[LEGAL ENTITY]` |
| D-2 | **Contact email** | Role address on the CloverProof domain (e.g. privacy@…), not a personal inbox | `[CONTACT EMAIL]` |
| D-3 | **Mailing address** (CASL needs one in every consent request and email) | Business address or PO box; the repo is **public**, so do not put a home address in it | `[ADDRESS]` |
| D-4 | **Privacy officer** | Default: Farjad. Can be delegated later. | `[PRIVACY OFFICER NAME]` |
| D-5 | **Retention** | Approve or change privacy-notice §8 (12 months / season + 2 years / consent + 3 years) | §8, Part B |
| D-6 | **Liability cap** | Amount for pilot-terms §9.2, or no cap clause; ask counsel what is enforceable for a free pilot | `[CAP AMOUNT]` |
| D-7 | **Does the AI reviewer see real pilot data?** — **DECIDED** 2026-11-16 by CPO (policy), effective now; any change needs Farjad Iranmehr | `cp-agronomist` never receives real pilot farmers' personal data or identifiable farm data. It works only on published sources, synthetic cases and de-identified case data: no names, contacts, addresses or exact field geometry (SOP gate G8). Any change needs (1) a DPA with the AI provider AND (2) disclosure in the privacy notice, decided by Farjad Iranmehr. Applied: privacy-notice §4, §6, §8, Part B; pilot-terms §3.2; pilot-sop G8. **Still to align (not edited here):** `consent-wording.md` §2 AI bullet. | `[AI PROVIDER]` named in privacy-notice §6 for transparency only |
| D-8 | **Data residency** for pilot farm data (OPEN, Q6) | US (Railway, disclose) vs Canada (different host, ADR + cost). Business/trust call; counsel advises on risk. | `[RESIDENCY DECISION]` |
| D-9 | **Human agronomist** (OQ-04, Q4) | Name, verified credentials, employee or contractor, hours. Without this, no real farm gets a plan. Founder is not the agronomist. | `[HUMAN AGRONOMIST NAME, CREDENTIALS]` |
| D-10 | **Lawyer engagement — paid, needs Farjad's go** | Ontario lawyer with privacy + agri/commercial experience; fixed-fee review of items 1–8. Get a quote first. | — |
| D-11 | **E&O insurance — paid, needs Farjad's go** | Quote before the first plan is delivered | — |
| D-12 | Sign Railway DPA after counsel review | — | — |

Also: CLAUDE.md still names Farjad Iranmehr as "our agronomist" (Current goal). It conflicts with D4; CPO to correct it.

## 3. Questions for the lawyer (from compliance-review.md, updated for D4 + R4)

1. **Liability.** Is pilot-terms §9 enforceable for a free pilot? Does a named human agronomist's review change that? Could any participant be a "consumer" under the Consumer Protection Act, 2002?
2. **Agronomist.** How should professional liability be split between [LEGAL ENTITY] and a contractor agronomist? What must their agreement say? What credentials may we print on the PDF, and what does printing the name commit them to?
3. **AI-assisted review.** Is the disclosure in privacy-notice §4, pilot-terms §3 and consent §2 adequate under PIPEDA (openness, meaningful consent) and the 2023 FPT generative-AI principles; and under GDPR Arts. 13(2)(f)/22 for EU website visitors?
4. **AI provider (D-7 decided: de-identified only).** Is the G8 de-identified set (county-level region, crop, previous crop, target yield, soil-test values, plan date) still personal information for a small farm, so that sending it is a transfer for processing under PIPEDA? What would a DPA need if Farjad later allows identifiable data?
5. **Licensing.** Does Ontario require any licence or certificate to give fertilizer rate advice outside NMA documents? Does the Agrologists Act restrict practice or titles only?
6. **NMA.** What is our exposure if a phased-in farm uses our plan alongside, or instead of, its NMS/NMP? Is pilot-terms §4.3 and PDF block I enough?
7. **PIPEDA scope.** Is a free pilot "commercial activity"? Is farm data of incorporated vs sole-proprietor farms personal information?
8. **Calibration.** Can in-pilot calibration be part of the core purpose? Is post-pilot use valid on optional consent? Is our de-identification adequate?
9. **Residency and transfers.** Is US storage with disclosure acceptable for pilot data? For EU website visitors: transfer analysis and Art. 27 representative.
10. **Prairie backup.** If the pilot extends to a Prairie province, does a provincial private-sector privacy law apply instead of PIPEDA?
11. **CASL.** Do replies to a pilot request rely on inquiry-based implied consent? How long must we keep consent records?
12. **Erasure vs immutability.** Is overwriting identifiers + deleting PDFs enough for a deletion request? How long may we keep immutable plan records to defend claims?
13. **Railway DPA.** Anything to negotiate (US processing, "without undue delay" breach notice, subprocessor objection)?
14. **Proof PDF.** Approve block I; is showing an `ai_reviewed` internal PDF to a third party (demo) a misleading representation even with the banner?
15. **Insurance.** What must E&O cover before the first plan?
16. **Translations.** Legal equivalence of the notice and consent text in each locale before enabling it.

## Sources
- D4, R4, Q4, Q6, Q7 — `origin/backend-traceability:docs/plans/backend-plan-reconciliation.md` (2026-11-16). OQ-04, OQ-07, PD-05 — `origin/backend-traceability:docs/plans/backend-traceability.md`.
- Legal sources for each point: `compliance-review.md`, `privacy-notice.md` (S1–S23), `proof-pdf-wording.md` (all checked 2026-11-16).

## Needs licensed counsel
All of section 3. Nothing in the four drafts should be used with a real farm until items 1–5 and 8 of section 1 are signed off.
