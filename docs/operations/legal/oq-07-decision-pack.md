# OQ-07 decision pack — legal sign-off for the 2027 pilot

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> For Farjad Iranmehr (founder) and the lawyer he engages. Prepared by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO, 2026-11-16. Nothing was sent, signed or filed.
> Updated 2026-11-16 for decisions by Farjad Iranmehr (source: `git diff origin/main origin/cpo-decisions-sa-fe-residency -- CLAUDE.md`): OQ-06 Canada (D-8), superadmin approval (D-13, §2a).
> Deadline driver: a named human approver (agronomist, or superadmin) before the S5 concierge gate (2027-01-29); first real-farm plan Feb 2027. Counsel review must finish before any farm signs.

## 1. Documents that need sign-off

| # | Document (`docs/operations/legal/`) | Who signs off | Blocks |
|---|---|---|---|
| 1 | `privacy-notice.md` Part A (v0.2) | Lawyer → Farjad | Pilot enrolment |
| 2 | `privacy-notice.md` Part B (website page, NB-WEB-05) | Lawyer → Farjad | Removing the "Draft" label |
| 3 | `consent-wording.md` (form boxes A/B; pilot consent; optional C/D/E) | Lawyer → Farjad | Form release; enrolment |
| 4 | `pilot-terms.md` (esp. §3 review, §9 liability, §12 law/forum) | Lawyer → Farjad signs per farm | Any farm signing |
| 5 | `proof-pdf-wording.md` block I (disclaimer) + reviewer line (B) + **superadmin approver line (B2)** | Lawyer → Farjad; `cp-agronomy-guard` enforces | First farmer-facing PDF |
| 6 | Canadian host's DPA / data terms (provider chosen in hosting ADR) | Lawyer review → Farjad signs | Any real farm data in a hosted environment |
| 6a | Railway DPA (self-serve, railway.com/legal/dpa) — only for what stays on Railway (website form, synthetic/de-identified environments) | Lawyer review → Farjad signs | Website form data on Railway, if the hosting ADR keeps it there |
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
| D-8 | **Data residency** for pilot farm data (OQ-06) — **DECIDED** 2026-11-16 by Farjad Iranmehr: Canada | Hosting ADR (`cto` + `devops-engineer`, with `ciso`) picks the provider; until live, only synthetic or de-identified data in hosted environments. Website form location not decided by this. See `data-residency-input.md`. | `[CANADIAN HOSTING PROVIDER, REGION]`; `[WEBSITE FORM DATA LOCATION — confirm in hosting ADR]` |
| D-9 | **Human agronomist** (OQ-04, Q4) | Name, verified credentials, employee or contractor, hours. Without this, no real farm gets a plan. Founder is not the agronomist. | `[HUMAN AGRONOMIST NAME, CREDENTIALS]` |
| D-10 | **Lawyer engagement — paid, needs Farjad's go** | Ontario lawyer with privacy + agri/commercial experience; fixed-fee review of items 1–8. Get a quote first. | — |
| D-11 | **E&O insurance — paid, needs Farjad's go** | Quote before the first plan is delivered | — |
| D-12 | Sign the Canadian host's DPA (and the Railway DPA if anything stays on Railway) after counsel review | — | — |
| D-13 | **Superadmin approval** — **DECIDED** 2026-11-16 by Farjad Iranmehr | Human superadmin without the `agronomist` role may approve (`superadmin_approved`); never AI/service accounts; only `agronomist_approved` feeds calibration and the agreement gate. Wording: never "reviewed/approved by an agronomist". Liability flag in §2a — not blocking. | `[SUPERADMIN NAME, ROLE]` |

Also: CLAUDE.md still names Farjad Iranmehr as "our agronomist" (Current goal). It conflicts with D4; CPO to correct it. With D-13, if Farjad is the superadmin who approves, he approves as **superadmin, not as agronomist** — every document must say that.

## 2a. Liability note — `superadmin_approved` plans reaching farmers (flag, not a block)
The decision stands; these are the exposures counsel should price before the first `superadmin_approved` plan reaches a real farm. Detail: `ontario-agronomist-credentials.md` §3.6.
1. **Negligence.** Giving fertilizer advice a farmer relies on creates a duty of care whoever approves it. A non-agronomist approver makes the standard of care harder to show, and pilot constants are all PLACEHOLDER (SOP G7), so the plan rests on unvalidated values with no professional check. The "not reviewed by an agronomist" disclosure (PDF Block B2) bears on reasonable reliance but does not remove the duty.
2. **E&O.** A policy written for credentialed agronomic advice may exclude or not contemplate advice approved by a non-credentialed person; not disclosing `superadmin_approved` to the insurer risks denial. Ask the broker before the first such plan.
3. **Competition Act.** Any general claim ("every plan is reviewed by an agronomist", "agronomist-approved plans") on the website, FAQ, emails or PDFs becomes false or misleading in a material respect once one plan is `superadmin_approved` (ss. 52, 74.01(1)(a); general impression s. 74.03(5)). All copy must be by approval kind.
4. **Prairie backup.** In Manitoba (and likely Saskatchewan) fertilizer advice is practising agrology; a non-member approving it is an offence. `superadmin_approved` must never be used for a Prairie farm.

## 3. Questions for the lawyer (from compliance-review.md, updated for D4 + R4)

1. **Liability.** Is pilot-terms §9 enforceable for a free pilot? Does a named human agronomist's review change that? Could any participant be a "consumer" under the Consumer Protection Act, 2002?
2. **Agronomist.** How should professional liability be split between [LEGAL ENTITY] and a contractor agronomist? What must their agreement say? What credentials may we print on the PDF, and what does printing the name commit them to?
3. **AI-assisted review.** Is the disclosure in privacy-notice §4, pilot-terms §3 and consent §2 adequate under PIPEDA (openness, meaningful consent) and the 2023 FPT generative-AI principles; and under GDPR Arts. 13(2)(f)/22 for EU website visitors?
4. **AI provider (D-7 decided: de-identified only).** Is the G8 de-identified set (county-level region, crop, previous crop, target yield, soil-test values, plan date) still personal information for a small farm, so that sending it is a transfer for processing under PIPEDA? What would a DPA need if Farjad later allows identifiable data?
5. **Licensing.** Does Ontario require any licence or certificate to give fertilizer rate advice outside NMA documents? Does the Agrologists Act restrict practice or titles only?
6. **NMA.** What is our exposure if a phased-in farm uses our plan alongside, or instead of, its NMS/NMP? Is pilot-terms §4.3 and PDF block I enough?
7. **PIPEDA scope.** Is a free pilot "commercial activity"? Is farm data of incorporated vs sole-proprietor farms personal information?
8. **Calibration.** Can in-pilot calibration be part of the core purpose? Is post-pilot use valid on optional consent? Is our de-identification adequate?
9. **Residency and transfers.** Pilot data: decided Canada (D-8) — see Q18. Website form data if kept outside Canada; for EU website visitors: transfer analysis and Art. 27 representative.
10. **Prairie backup.** If the pilot extends to a Prairie province, does a provincial private-sector privacy law apply instead of PIPEDA?
11. **CASL.** Do replies to a pilot request rely on inquiry-based implied consent? How long must we keep consent records?
12. **Erasure vs immutability.** Is overwriting identifiers + deleting PDFs enough for a deletion request? How long may we keep immutable plan records to defend claims?
13. **Host DPAs.** Canadian host's DPA (provider TBD); Railway DPA only if the website stays there — anything to negotiate (breach-notice clock, subprocessor objection, deletion deadline)?
14. **Proof PDF.** Approve block I; is showing an `ai_reviewed` internal PDF to a third party (demo) a misleading representation even with the banner?
15. **Insurance.** What must E&O cover before the first plan?
16. **Translations.** Legal equivalence of the notice and consent text in each locale before enabling it.
17. **Superadmin approval (D-13).** (a) Duty of care and standard of care for a plan approved by a non-agronomist superadmin; does Block B2 + pilot-terms §3.1(b) reduce exposure or only document it? (b) Should a farm opt in to `superadmin_approved` plans rather than opt out? (c) Does pilot-terms §9 hold for those plans? (d) Personal exposure of the approving superadmin (a director/officer) vs the corporation. (e) What must be disclosed to the E&O insurer?
18. **Residency (D-8).** Wording of the Canada commitment if the Canadian host is US-owned or the app processes outside Canada; whether website form data outside Canada must be disclosed alongside it.

## Sources
- D4, R4, Q4, Q6, Q7 — `origin/backend-traceability:docs/plans/backend-plan-reconciliation.md` (2026-11-16). OQ-04, OQ-07, PD-05 — `origin/backend-traceability:docs/plans/backend-traceability.md`.
- Legal sources for each point: `compliance-review.md`, `privacy-notice.md` (S1–S23), `proof-pdf-wording.md` (all checked 2026-11-16).

## Needs licensed counsel
All of section 3, and §2a. Nothing in the four drafts should be used with a real farm until items 1–6 and 8 of section 1 are signed off and Canadian hosting is live.
