# CloverProof pilot participation terms — DRAFT v0.3

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> Drafted by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO. v0.1 2026-11-16; v0.2 2026-11-16 (CPO decisions D4 + R4); v0.2.1 2026-11-16 (CPO decision D-7, §3.2); v0.3 2026-11-16 (Farjad Iranmehr decisions: superadmin approval, §3; Canadian storage, §7.6).
> Never sign or send on Farjad Iranmehr's behalf. Farjad signs for the company; each farm signs for itself.
> Clauses marked **[COUNSEL]** must not be used until a lawyer has reviewed them.

Open placeholders: `[LEGAL ENTITY]`, `[ADDRESS]`, `[CONTACT EMAIL]`, `[PILOT END DATE]`, `[FARM BUSINESS NAME]`, `[SIGNATORY]`, `[CAP AMOUNT]`, `[HUMAN AGRONOMIST NAME, CREDENTIALS]`, `[SUPERADMIN NAME, ROLE]`, `[CANADIAN HOSTING PROVIDER, REGION]`, `[PRIVACY URL]`.

---

## Drafting notes (internal — remove before sending)
- **v0.2 changes.** D4: review is AI-assisted, human-approved (§3). The founder is not the reviewing agronomist; the earlier note describing him as "CloverProof's agronomist" is withdrawn. R4: eligibility = Ontario farms (§1.5); Prairie wheat is a backup — extending to another province needs a written addendum and a privacy-law check first (`oq-07-decision-pack.md` §3 Q10).
- **v0.3 changes (decisions by Farjad Iranmehr, 2026-11-16; source: CLAUDE.md on `origin/cpo-decisions-sa-fe-residency`).** (1) A human `superadmin` without the `agronomist` role may approve a plan (`superadmin_approved`); AI/service accounts never. §3.1 now says a plan is approved by a named person and tells the farmer, plan by plan, whether an agronomist reviewed it. (2) OQ-06 decided: real farmer data stored in Canada (§7.6). Until Canadian hosting is live, no real farm data in hosted environments, so these terms cannot be performed and must not be sent.
- **Do not send these terms to a farm until (a) a named human approver exists (agronomist, or superadmin under §3.1(b)) and (b) Canadian hosting is live (§7.6).** Target for (a): before the S5 concierge gate, 2027-01-29.
- **Liability flag (do not ignore):** a `superadmin_approved` plan reaches the farmer with no agronomist review, on constants still marked PLACEHOLDER. See `ontario-agronomist-credentials.md` §3.6. §3.1(b) discloses this, but disclosure does not remove the duty of care, and E&O cover for it is unconfirmed. **[COUNSEL]** Never use §3.1(b) for a Prairie farm (right-to-practice provinces; same file §1).
- **Agronomist title.** Print only the credentials the named person actually holds and that we have verified (e.g., P.Ag. on the Ontario agrologists' public register — body to verify; CCA status with the certifying body). Protected / certified titles — compliance-review.md §5.
- **Agronomist contract.** If the agronomist is a contractor, we need a separate written agreement: scope, confidentiality, data handling, who carries professional liability, insurance. **[COUNSEL]**
- **Nutrient Management Act.** Phased-in farms (e.g., ≥300 livestock nutrient units, NMS farms within 100 m of a municipal well, NASM land) need an NMP/NASM plan by a certified person (OMAFRA Factsheet 21-025). A CloverProof plan is **not** one. Screen every farm at intake.
- **Insurance.** Get a professional liability (E&O) quote before the first plan is delivered (paid — Farjad's go). A liability cap does not replace insurance.
- **Signing.** Simple e-signature or signed PDF; keep the signed copy with the consent record (consent-wording.md §4).

---

## Terms

**Between** [LEGAL ENTITY], [ADDRESS], Ontario, Canada ("CloverProof", "we") **and** [FARM BUSINESS NAME], represented by [SIGNATORY] ("you").

### 1. What the pilot is
1.1 The CloverProof pilot runs from the date you sign until [PILOT END DATE] (planned: February–April 2027 planning season).
1.2 During the pilot we prepare field-specific fertilizer plans for the fields you choose, from the information you give us. Each plan states what, how much, when and why, with a confidence level (high / medium / low).
1.3 The pilot is **free**. You pay nothing and have no obligation to buy anything later. We are not paid by any fertilizer maker, dealer or retailer, and we do not recommend specific brands for payment.
1.4 The pilot is a test of new software. Its purpose includes checking and improving how accurate the software is (see section 7).
1.5 **Eligibility.** The pilot is open only to farm businesses whose enrolled fields are in **Ontario, Canada**. We may extend it to another Canadian province only by a written addendum. Fields outside Ontario are not covered by these terms.

### 2. Decision support, not a guarantee
2.1 A plan is decision support. It is based on the information you provide, general agronomic methods and the assumptions stated in the plan. It is **not** a guarantee of any yield, crop quality, profit, cost saving or environmental result.
2.2 Weather, soil variability, timing, equipment, product quality and many other factors outside our control affect results.
2.3 The confidence level in each plan tells you how much evidence stands behind each number. Treat low- and medium-confidence numbers with extra care.

### 3. How plans are approved — AI assists, a named person approves **[COUNSEL]**
3.1 **No plan is sent to you until a named person at CloverProof has approved it and approved or changed every number.** That person is either:
(a) our human agronomist, [HUMAN AGRONOMIST NAME, CREDENTIALS]; or
(b) [SUPERADMIN NAME, ROLE], who is **not an agronomist**. A plan approved this way has **not been reviewed by an agronomist**, and the plan and its proof PDF say so on the first page.
Each plan tells you which of the two approved it. If neither is available, we do not send a plan; we will tell you, and either of us may end the pilot under section 10. You may tell us at any time that you want only plans approved under (a); we will then send you no plan approved under (b).
3.2 Our software proposes each plan. An **AI system** may check the proposal and leave notes for the person who approves it. An AI check is never an approval, and our system does not let it approve a plan for your farm. The AI system only ever sees a de-identified copy of your case: we remove your name, contact details, address, farm and field names and exact field boundaries first. We will not give an AI provider information that identifies you or your farm unless we first sign a data-processing agreement with it and update our privacy notice.
3.3 We keep a record of the software's proposal, any AI check notes, the approver's final number and the reason for any change.
3.4 Approved plans are never edited. A correction creates a new version that says what changed and why.
3.5 Each approved plan and its proof PDF name the person who approved it, their role, the date, and whether an agronomist reviewed it.

### 4. Your decisions and your responsibilities
4.1 **You make the final decision** on what, how much and when to apply, and you are responsible for the application itself, including product choice, equipment calibration, timing, weather and field conditions, and safe handling.
4.2 **You are responsible for following the law that applies to your farm**, including the Ontario *Nutrient Management Act, 2002* and its regulations, setback and timing rules, municipal by-laws, source-water protection rules and any conditions of your permits, certifications or programs.
4.3 **A CloverProof plan is not a nutrient management strategy (NMS), nutrient management plan (NMP) or non-agricultural source material (NASM) plan** under the *Nutrient Management Act, 2002*, and does not replace one. If your farm needs one of those documents, it must be prepared by a person certified under that Act (or by you, if you hold the required certificate). Tell us at sign-up if your farm needs one.
4.4 You confirm that the information you give us is accurate to the best of your knowledge, and that you have the right to share it (for example, soil-test reports and information about rented land).
4.5 Tell us promptly if anything you gave us was wrong or has changed. A plan made from wrong information may be wrong.

### 5. Soil tests, phosphorus and potassium
5.1 **Without a recent soil test for a field, we give nitrogen advice only**, at no more than medium confidence. For phosphorus (P) and potassium (K) we will recommend that you take a soil test; we will not give P or K rates for that field.
5.2 Soil-test results must state the lab, sampling date, sampling depth and extraction method. If any of these are missing, we may decline to use the result or lower the confidence level.

### 6. The proof PDF
6.1 For each approved plan we produce a proof PDF that records how the plan was made: the inputs, the software version, the method version, the approver's decision (name, role or verified credentials, date, and whether an agronomist reviewed it) and a fingerprint (SHA-256) that shows whether the file has been changed.
6.2 **The proof PDF is a record, not a certification.** It is not accepted, approved or endorsed by any lender, insurer, certifier, buyer, government program or regulator, and we make no promise that any of them will accept it. If you give it to a third party, they decide what it is worth to them.
6.3 You may share your proof PDF with anyone you choose. You may not alter it and present it as ours.
6.4 A PDF marked "NOT FOR FARMER USE" is an internal test document. If you ever receive one, do not use it; tell us.

### 7. Your data
7.1 Our privacy notice ([PRIVACY URL]) explains what we collect, why, where it is stored, how AI is used in review, and your rights. It forms part of these terms.
7.2 You own your farm data. You give us permission to use it to run the pilot for you: to calculate, check, review and record your plans and to contact you about them.
7.3 **Improving the engine.** The difference between the software's proposal and the human agronomist's final number is how we learn where the software is wrong. Within the pilot we analyse this for every plan our agronomist approved (plans approved under §3.1(b) are not used for this). Separately, and **only if you tick the box in the consent form**, we keep a de-identified copy after the pilot to keep improving the software (no names, contacts, farm or field names or exact locations). You can withdraw that permission at any time.
7.4 We will not sell your data, give your farm-level data to fertilizer companies, or publish anything that identifies your farm without your separate written permission.
7.5 Statistics or findings that cannot identify you or your farm may be published.
7.6 **Where your data is stored.** We store your farm data in Canada, with [CANADIAN HOSTING PROVIDER, REGION]. [IF THE PROVIDER IS NOT CANADIAN-OWNED: "The provider is a [COUNTRY] company, so the law of that country may require it to give access to data it holds, even in Canada."] The AI check in §3.2 receives only a de-identified copy, which may be processed outside Canada. **[COUNSEL]**

### 8. Intellectual property
8.1 The CloverProof software, methods, templates and documentation remain ours. You receive a free, non-exclusive right to use your plans and proof PDFs for your own farm.
8.2 Feedback you give us may be used to improve CloverProof without payment to you. **[COUNSEL: confirm feedback clause]**

### 9. Limitation of liability **[COUNSEL — OQ-07, do not use until reviewed]**
9.1 To the extent the law allows, CloverProof is not liable for indirect, incidental or consequential losses, including lost yield, lost profit, crop loss or fines, arising from the pilot or a plan.
9.2 To the extent the law allows, our total liability arising from the pilot is limited to [CAP AMOUNT].
9.3 Nothing in these terms limits liability that cannot be limited by law, including for fraud, gross negligence or wilful misconduct, or for death or personal injury caused by negligence.
*Counsel questions: enforceability of a cap in a free agreement; effect of a named human agronomist's professional review on exclusions; allocation between CloverProof and a contractor agronomist; Ontario Consumer Protection Act, 2002 if a participant is an individual not acting for a business; interaction with E&O insurance.*

### 10. Ending the pilot
10.1 Either of us may end your participation at any time by email, with no cost or penalty.
10.2 When the pilot ends for you: we stop making plans; plans already approved stay valid as records; we keep your data as set out in the privacy notice unless you ask us to delete it.
10.3 **Deletion.** If you ask, we delete or irreversibly de-identify your personal and farm-identifying data within 30 days and confirm in writing. Approved plan records are write-once; for those we remove everything that links them to you. Your copies of proof PDFs are yours to keep. Data already de-identified for calibration can no longer be linked to you and may be kept unless you withdrew that consent before de-identification.

### 11. Communication
We will contact you by email or phone about your plans. We will only send you news or marketing if you separately agreed to it.

### 12. General **[COUNSEL]**
12.1 These terms are governed by the laws of Ontario and the federal laws of Canada that apply there. **[COUNSEL: forum clause]**
12.2 These terms and the privacy notice are the whole agreement about the pilot. Changes must be in writing (email is enough) and agreed by both of us.
12.3 If part of these terms is unenforceable, the rest still applies.

**Signed**
For [LEGAL ENTITY]: ______________________ Name: Farjad Iranmehr, [TITLE, e.g. Director] Date: ________
For [FARM BUSINESS NAME]: ________________ Name: [SIGNATORY] Date: ________

Attached: Pilot data-use consent (consent-wording.md §2–3).

---

## Sources (checked 2026-11-16)
- OMAFRA Factsheet 21-025, *Understanding When Farms Require an NMS, an NMP or a NASM Plan* (April 2021) — https://files.ontario.ca/pdf1/omafra-when-a-farm-needs-an-nms-nmp-nasm-21-025-en-27-05-21.pdf *(fetched and read)*
- Nutrient Management Act, 2002, S.O. 2002, c. 4 — https://www.ontario.ca/laws/statute/02n04 ; O. Reg. 267/03 — https://www.ontario.ca/laws/regulation/030267 *(e-Laws requires JavaScript; text not read)*
- Ontario Institute of Professional Agrologists Act, 2013 — https://www.ontario.ca/laws/statute/pr13009 *(search only; title protection)*
- Decisions D4, R4 — `origin/backend-traceability:docs/plans/backend-plan-reconciliation.md` (CPO, 2026-11-16).
- Decisions superadmin approval + Canadian storage — `git diff origin/main origin/cpo-decisions-sa-fe-residency -- CLAUDE.md` (Farjad Iranmehr, 2026-11-16).
- Competition Act ss. 52, 74.01(1)(a), 74.03(5) — https://laws-lois.justice.gc.ca/eng/acts/c-34/section-74.03.html *(search summary, 2026-11-16; text not read)*
- Privacy and AI-transparency sources: see privacy-notice.md (S1–S23).

## Needs licensed counsel
1. Clause 9 (limitation of liability) in full; enforceability for a free pilot with a named human agronomist's review — and separately for a plan approved under §3.1(b) with no agronomist review.
1a. Clause 3.1(b): is the disclosure enough to avoid a misleading impression (Competition Act s. 74.01(1)(a), s. 74.03(5)) and to limit reliance; should (b) be opt-in per farm rather than opt-out? Does E&O cover (b)?
1b. Clause 7.6: wording if the Canadian host is a US-owned company; whether de-identified data sent to an AI provider outside Canada is consistent with the residency commitment.
2. Professional liability allocation between CloverProof and the human agronomist (employee vs contractor); the agronomist's agreement; E&O scope.
3. Whether any participant could be a "consumer" under the Ontario Consumer Protection Act, 2002.
4. Clause 3 — adequacy of the AI-assisted review disclosure; clause 4.3 — NMA wording and exposure for phased-in farms.
5. Clause 7.3 — whether in-pilot calibration analysis can be part of the core purpose.
6. Clause 1.5 — extension to a Prairie province (provincial privacy law, agronomy title rules).
7. Clause 8.2 feedback/IP; clause 12 governing law and forum.
