# Fundraising readiness checklist (one page)

Owner: funding desk (for the CPO, `product-manager`). Date: 2026-11-17. Status: draft. Nothing here has been sent to anyone.
Targets marked **proposal** are for the CPO and Farjad Iranmehr to confirm. Legal, tax and securities points go to `legal-compliance-specialist` and a corporate lawyer. This page gives no legal advice.

## Recommendation on timing
Do not raise equity before pilot results. The earliest credible window is **after the concierge pilot (Feb–Apr 2027) produces numbers, which means a pre-seed conversation around May–Jun 2027**. The stronger window is **after the 2027 pilot season (Nov 2027 onward)**, when there is harvest-season evidence and a paid-launch plan. Before that, use non-dilutive money (see `grants-radar.md`). This is a recommendation, not a decision.

## A. Preconditions (blockers: no investor conversation without these)
- [ ] **Legal entity decided** (Ashavid Inc. vs a new CloverProof corporation). Equity investors usually want a standalone company with only this business. A holding company that also owns VisaRoads and Contivo would need a carve-out or a new corporation. Decision: Farjad Iranmehr, with an accountant and lawyer.
- [ ] Clean cap table: founder shares, vesting, and no promises of equity made informally.
- [ ] **IP assigned to the company**, including the repo, brand and domain, plus written IP assignments from every contractor. An AI-agent workflow does not change who owns the code; confirm with a lawyer.
- [ ] A human agronomist named, under a written contract (CLAUDE.md rules 8 and 11). Without one there is no `agronomist_approved` data and no agreement metric.
- [ ] Production hosting for farmer data in Canada decided by ADR (CLAUDE.md stack note).
- [ ] Securities route checked by a lawyer: SAFE vs priced round, and Ontario prospectus exemptions. Flag to `legal-compliance-specialist`.

## B. Traction metrics from the pilot (definitions owned by `head-of-data`)
| Metric | Why investors ask | Proposal target by end of the concierge pilot |
|---|---|---|
| Farms with a delivered, human-approved plan | Demand + delivery | 5–10 (CLAUDE.md pilot range) |
| Fields / acres covered | Scale signal | unknown, set after intake |
| Agronomist minutes per plan (human reviews only) | Cost to serve, gross margin | Trend down across the pilot; the target is set by the CPO |
| Edit rate and agreement of engine vs **human** agronomist (`agronomist_approved` only) | Is the engine any good? | Report the actual value against the 90 % agreement gate; never include `ai_reviewed` |
| Farmer follow-through (planned vs actual log) | Is it used? | unknown, set S10 |
| Intent to pay, stated price band, or signed LOIs | Willingness to pay | proposal: at least 3 written LOIs or price-band answers |
| Advisor/CCA interest (multi-farm use) | Channel leverage | unknown |
| Repeat intent for the next season | Retention proxy | proposal: majority of pilot farms say yes |

## C. Narrative pieces (`investor-relations-manager`, after the pilot)
- [ ] Problem and job, backed by pilot interviews rather than hypotheses (positioning.md shows that pains are UNKNOWN today).
- [ ] Why vendor-neutral + proof record wins vs free tools (AgriSuite), dealer agronomy and farm-management software (`docs/strategy/competitor-scan.md`).
- [ ] Business model with the chosen billing option (`docs/strategy/billing-model-options.md`) and unit economics from real minutes per plan.
- [ ] Country-pack expansion logic, with Prairie wheat as the next step.
- [ ] Use of funds and milestones to the next round.

## D. Data room
- [ ] Incorporation documents, articles, minute book, share register
- [ ] Cap table and any SAFEs or convertible notes
- [ ] IP assignment agreements (founder and contractors); open-source licence report (no GPL/AGPL/EUPL, LGPL exceptions per CLAUDE.md)
- [ ] Material contracts: pilot terms, agronomist contract, data-processing agreements
- [ ] Financials: statements to date, 24-month model, burn and runway, grants received (they reduce SR&ED claims)
- [ ] Privacy and data-residency posture: privacy notice, PIPEDA review, Canadian hosting ADR
- [ ] Security summary from `ciso`: threat model, DB-enforced immutability, RLS, MFA
- [ ] Product demo (synthetic data only) and a sample proof PDF from synthetic data
- [ ] Pilot report: the metrics in B, with method and limits stated
- [ ] SR&ED and grant records (`sred-irap-readiness.md`)

## E. What we must NOT claim
- "Agronomist-reviewed", "validated" or "approved by" anyone before a named human agronomist approves real plans. `ai_reviewed` is not a review by a person.
- Any partnership or endorsement (university, OMAFA, lab, co-op, lender) that has not been signed in writing.
- Yield gains, fertilizer savings or emissions reductions: none has been measured.
- Any constant labelled `PLACEHOLDER` presented as validated.
- That the engine is AI or ML. It is a rules engine.
- Investor names or interest that we have not confirmed in writing.
