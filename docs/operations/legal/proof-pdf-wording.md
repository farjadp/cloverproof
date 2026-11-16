# Proof PDF wording by review state — DRAFT v0.1 (PD-05)

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> Drafted by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO, 2026-11-16. For `cto/cp-pdf` (templates, `app/pdf/`) and `cp-agronomy-guard` (review).
> Basis: D4 + R4, `origin/backend-traceability:docs/plans/backend-plan-reconciliation.md`; trace row PD-05 (`docs/plans/backend-traceability.md`); CLAUDE.md hard rules 2–5, 8–9.
> No agronomic numbers in this file. Text in `{braces}` is filled by the template from data; text in `[BRACKETS]` is a placeholder a person must fill.

## 0. Which block goes on which PDF

| Review state | May a PDF exist? | May it go to a farmer? | Blocks |
|---|---|---|---|
| `in_review` (no review yet) | Internal preview only | **No** | A (banner, draft variant) + C–I |
| `ai_reviewed` (AI check by `cp-agronomist`, no human) | Internal / test only | **No** | A (banner) + C–I |
| `agronomist_approved` (named human with `agronomist` role) | Yes | Yes | B + C–I |
| `rejected` | No PDF | — | — |

Rules for `cp-pdf`:
1. The state comes from the database review record, never from template input. If the approving user is not flagged human (`REC-D4`), render as `ai_reviewed`.
2. Block B may only render when the approving review is human `agronomist_approved` **and** the farm is a real farm. Otherwise block A, always.
3. Block A's banner is on **every page**: top of page, full width, high contrast, plus a diagonal watermark "NOT FOR FARMER USE". The banner text is not configurable.
4. Blocks C–I appear on every PDF in every state, in this order, after the plan table. Block I (legal disclaimer) is `[COUNSEL — OQ-07]`: ship the draft text only on internal/test PDFs until counsel approves it.
5. The proof-document hash stored in `proof_document.sha256` is computed on the final file, so the file cannot print its own hash (block H handles this).

---

## A. `ai_reviewed` / `in_review` — internal and test only

Banner (every page):
> **NOT FOR FARMER USE — not reviewed by a human agronomist.**

Status line (under the title):
> Status: {`AI-checked only` | `Draft — not reviewed`}. This document is an internal test record. It has not been reviewed or approved by a human agronomist and must not be given to a farmer or used to make fertilizer decisions.

If AI-checked, add:
> An AI system (`cp-agronomist`) checked this plan on {ai_review_date}. An AI check is not an agronomist review or approval.

## B. `agronomist_approved` — the only farmer-facing state

Reviewer line (under the title, and again in the signature block):
> This plan was prepared with CloverProof and reviewed by [HUMAN AGRONOMIST NAME, CREDENTIALS] on {approval_date}.

If an AI check was also made (D4 transparency):
> An AI system helped check this plan before the agronomist's review. The agronomist made the final decision on every number.

If the agronomist changed any number:
> Numbers marked ✎ were changed by the agronomist from the software's proposal. The reason is given next to each change.

Credentials rule: print only credentials that are held and verified (e.g. P.Ag., CCA). Until verified, print the name only.

## C. Confidence levels

> **Confidence** tells you how much evidence stands behind each number — not how likely a yield or profit is.
> - **High:** {one-line rule from `engine/cloverproof_engine/confidence.py`}
> - **Medium:** {one-line rule from `confidence.py`}
> - **Low:** {one-line rule from `confidence.py`}
> Treat medium- and low-confidence numbers with extra care.

`cp-engine` supplies the three one-line rules from code; `cp-agronomy-guard` checks they match the code. Legal does not write them.

## D. PLACEHOLDER notice (render whenever any line depends on a constant marked `PLACEHOLDER` in the pack)

> **Not yet validated.** {n} number(s) in this plan (marked ⚠) rely on values in CloverProof's method that a human agronomist has not yet validated. Treat them as provisional.

Recommendation to CPO / `cp-agronomy-guard` (not a legal rule): a real-farm `agronomist_approved` PDF should not be issued while a line rests on a PLACEHOLDER unless the human agronomist has explicitly confirmed that line in the review reason. Decision owner: CPO.

## E. No soil test — nitrogen only

> **No soil test for this field.** This plan gives nitrogen (N) advice only, at no more than medium confidence. We do not give phosphorus (P) or potassium (K) rates without a recent soil test. **We recommend a soil test** for this field before deciding on P and K.

## F. Version and supersedes

> Plan {recommendation_id}, version {version}. Engine {engine_version} · Method pack {pack_id} {pack_version} · Generated {created_at, UTC}.
> {if parent_id} This version replaces version {parent_version} of {parent_created_at}. What changed and why: {reason}. The earlier version is kept unchanged in our records.

## G. Data used

> Based on the information supplied for this field on {snapshot_date}: {field summary from inputs snapshot}. Soil test: {lab, sampling date, depth, extraction method, P/K form} | none. If any of this is wrong, the plan may be wrong — tell us and we will issue a new version.

## H. Fingerprint (SHA-256)

> **Fingerprint.** Document {proof_document_id}. When CloverProof issued this file it recorded its SHA-256 fingerprint. To check that this file has not been changed, compute its SHA-256 value and compare it with the value we hold — ask us at [CONTACT EMAIL].
> Input fingerprint (SHA-256 of the input record): {inputs_sha256} *(optional — only if `cp-pdf` computes it)*.

## I. Limits of this document — `[COUNSEL — OQ-07]`

> **Decision support, not a guarantee.** This plan is decision support based on the information supplied, published agronomic methods and the assumptions stated above. It is not a guarantee of any yield, crop quality, profit, cost saving or environmental result. **The farmer decides** what, how much and when to apply, and is responsible for the application and for following the law that applies to the farm.
> **Not a Nutrient Management Act document.** This plan is not a nutrient management strategy (NMS), nutrient management plan (NMP) or non-agricultural source material (NASM) plan under Ontario's *Nutrient Management Act, 2002*, and does not replace one.
> **Not accepted or endorsed by anyone else.** This document is a record of how the plan was made. It has not been accepted, approved or endorsed by any lender, certifier, insurer, buyer, government program or regulator, and no one is obliged to accept it.
> Issued by [LEGAL ENTITY], [ADDRESS], Ontario, Canada · [CONTACT EMAIL].

---

## J. Banned phrases (in any PDF, template, filename or metadata)

`cp-agronomy-guard` blocks a template change that contains any of these. Case-insensitive.

| Banned | Why | Use instead |
|---|---|---|
| "reviewed by an agronomist", "agronomist-reviewed", "agronomist approved" — on any `ai_reviewed` or `in_review` PDF | D4: AI review is not agronomist review; misleading (Competition Act false/misleading representation risk — counsel to confirm) | Block A text |
| "AI agronomist", "our agronomist" without a name | Implies a professional where there is software or no named person | "An AI system" / "[name, credentials]" |
| "accepted by …", "approved by [bank / lender / insurer / OMAFA / certifier / buyer]", "endorsed by", "recognised by" | No third party has accepted anything | Block I, third paragraph |
| "certified", "certificate", "certified plan" | Implies certification under a scheme or the NMA | "record", "proof document" |
| "compliant", "complies with", "meets NMA / regulatory requirements", "NMS", "NMP", "NASM plan" (except in block I's negation) | We do not assess legal compliance | Block I, second paragraph |
| "guaranteed", "guarantee" (except "not a guarantee"), "risk-free", "will increase yield", "ensures", "optimal", "maximum yield" | Outcome promise | "decision support"; confidence label |
| "P.Ag.", "CCA", "agrologist" | Protected / certified titles — only if the named person holds them and we verified | Name only |
| "approved" on any PDF not in `agronomist_approved` | Status misstatement | "AI-checked only" / "Draft — not reviewed" |
| Any fertilizer brand presented as recommended for payment | Pilot terms 1.3 | Generic product description |

## Sources (checked 2026-11-16)
- D4, R4 — `origin/backend-traceability:docs/plans/backend-plan-reconciliation.md`; PD-05, REC-D4 — `origin/backend-traceability:docs/plans/backend-traceability.md`.
- OMAFRA Factsheet 21-025 (NMS/NMP/NASM) — https://files.ontario.ca/pdf1/omafra-when-a-farm-needs-an-nms-nmp-nasm-21-025-en-27-05-21.pdf *(fetched and read earlier, 2026-11-16)*
- Ontario Institute of Professional Agrologists Act, 2013 — https://www.ontario.ca/laws/statute/pr13009 *(search only; title protection)*
- Competition Act, R.S.C. 1985, c. C-34, s. 52 and s. 74.01 (misleading representations) — https://laws-lois.justice.gc.ca/eng/acts/C-34/ *(not fetched; section numbers from memory — verify)*
- FPT generative-AI principles (2023), transparency — see privacy-notice.md S23 *(search only)*

## Needs licensed counsel
1. Block I in full (decision support / NMA / no third-party acceptance) — OQ-07.
2. Whether block B's reviewer line creates a professional-advice duty for the named agronomist and for [LEGAL ENTITY], and what credentials may be printed.
3. Whether showing an internal `ai_reviewed` PDF to anyone outside the team (e.g. a lender in a demo) is a misleading representation even with the banner.
4. Whether the AI-assistance sentence in block B is enough AI transparency.
