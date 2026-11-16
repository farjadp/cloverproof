# OQ-04: what the human agronomist must hold, and who carries liability (Ontario first, Prairie backup), 2026-11

> **This is not legal advice. A licensed Ontario lawyer should review it before use.**
> Prepared by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO on 2026-11-16. Nothing was filed, sent or signed, and no regulator or certifying body was contacted.
> This extends `compliance-review.md` §5 and does not repeat it. Context: the launch is Ontario winter wheat, with Prairie wheat as backup (pilot-terms v0.2, R4). The AI pre-review (`ai_reviewed`, `cp-agronomist`) can never approve. Only a named human with the `agronomist` role can set `agronomist_approved` (`pilot-sop.md` D4, G1). That human has not been named yet.

**Repo vs my default brief:** my global agent file describes VisaRoads. CLAUDE.md overrides it: this is CloverProof (agri-tech), and the immigration and RCIC rules do not apply here. **Legal entity:** still `[LEGAL ENTITY]` (compliance-review §0). Every contract and liability point below depends on which corporation contracts with farms and with the agronomist.

Status key: **CONFIRMED** = read in the statute or bill text. **SECONDARY** = from a regulator or government summary, not the statute. **UNKNOWN**.

---

## 0. Answer in three lines
1. **Ontario:** I found no licence requirement for giving fertilizer-rate advice to a crop farm outside Nutrient Management Act (NMA) documents. Ontario's agrologist Act protects **titles only**, and s. 12 says it does not restrict non-members' right to practise (bill text, CONFIRMED; enacted text still to be verified). So the credential is a **quality and insurance choice, not a legal gate**, except for NMA documents and pesticide-related work.
2. **Saskatchewan and Manitoba are right-to-practice provinces.** Fertilizer advice that a farmer relies on is very likely "practising agrology" there, so the approver must be a registered agrologist **in that province**. Alberta is probably the same but UNKNOWN. This means the Prairie backup **cannot** be served by an Ontario-only CCA.
3. **Liability sits with whoever gives the advice and with whoever sells it.** The farmer contracts with CloverProof, so CloverProof is exposed whether the agronomist is an employee or a contractor. We need E&O cover that names both the company and the reviewer, and the cover must not exclude AI-assisted or software-generated advice.

---

## 1. Per jurisdiction: regulated practice or protected title?

| Jurisdiction | Practice regulated? | Credential required to approve fertilizer plans | NMA / special plans | Status | Sources |
|---|---|---|---|---|---|
| **Ontario** | **No (title only).** *Ontario Institute of Professional Agrologists Act, 2013* (S.O. 2013, c. Pr9), s. 9(1): members "may use the designation 'Professional Agrologist (Ontario)' or 'P.Ag.'". Under s. 9(3), a non-member who uses the designations or "holds out" as a member commits an offence. Under **s. 12, "This Act does not affect, restrict or interfere with the right of any person who is not a member of the Institute … to practise in the field of professional agrology."** The OIA describes registration as voluntary in Ontario (search summary). No penalty amount appears in the bill text. | **None found in law** for advice on a crop-only farm. P.Ag., T.Ag. and A.Ag. may be **printed only if held**. | Phased-in farms need an NMS/NMP from a certified nutrient management consultant (or the farmer with a planning certificate) and a NASM plan from a NASM Plan Developer certificate holder (Factsheet 21-025, already in §5). Certificates are issued under O. Reg. 267/03, Part X (agricultural operation strategy/plan development, agricultural operation planning, NASM plan development, among others; **section numbers vary by version**, current text not read). | Title-only: CONFIRMED on bill text, enacted text UNVERIFIED. Crop-farm advice needs no licence: SECONDARY plus absence of evidence → **needs counsel** | O1, O2, O3, O4, O5 |
| **Ontario, contrast: pesticides** | **Yes, for specific acts.** The Pesticides Act and O. Reg. 63/09 licence exterminators and vendors. For neonicotinoid-treated seed (formerly Class 12, now Class E per O. Reg. 134/20), a "professional pest advisor" must be a CCA (ASA-certified, in good standing with CCA-ON) or an OIA member such as a P.Ag. (MOECC 2015 fact sheet, search summary; the OFA has asked for the definition to be widened). | n/a for fertilizer | It shows Ontario **does** name CCA and P.Ag. when it wants to regulate advice. It has not done this for fertilizer rates. | SECONDARY, current definition not read | O6, O7, O8, O9 |
| **Ontario, contrast: fertilizer products** | The federal *Fertilizers Act* (CFIA) regulates products (registration, labels), not advice. **From memory, not verified this session.** | n/a | n/a | UNKNOWN | O10 |
| **Saskatchewan** | **Yes, right to practice.** *The Agrologists Act, 1994* (S.S. 1994, c. S-16.1). The SIA says anyone who is qualified and practising agrology must be registered and licensed, and that unauthorized practice breaches the Act (s. 22 per a provincial presentation). The definition of "practise agrology" was amended in 2018 to add environmental practice. A 2016 law-firm note lists "commercial advising" on crop cultivation and farm management as SIA-regulated. I did **not** read the statutory definition or the exemptions. | Registered SIA member (P.Ag. or the licensed category for the work) approves the plan. Whether an out-of-province CCA may advise remotely: UNKNOWN. | n/a (Ontario NMA does not apply) | SECONDARY → **needs counsel / SIA confirmation** | P1, P2, P3, P4 |
| **Manitoba** | **Yes, right to practice.** *The Agrologists Act*, C.C.S.M. c. A50 (unofficial consolidation read). s. 1(1): "practising agrology" includes "every act, with or without reward, which has as its objective … the giving of advice with respect to the principles, laws or practices relating to the production, improvement, use, processing or marketing of agricultural products, crops or livestock". s. 15(1): "A person who is not a member in good standing of the institute shall not practise agrology." Penalties under s. 15(3)–(5): fine up to $100 for a first offence and $200 after, **no right to recover fees**, and injunction. Exemptions in s. 1(2) cover farmers who do not hold out, supervised students and technicians, other statutory professionals who do not hold out, and **sellers giving advice on their own product "under the authority or supervision of a member"**. None of these covers CloverProof. Agrologists Manitoba says CCA "does not replace professional registration". | Member in good standing of Agrologists Manitoba. | n/a | CONFIRMED (unofficial consolidation) | P5, P6 |
| **Alberta** | **Probably yes.** The *Agrology Profession Act* and Agrology Profession Regulation apply. Government of Alberta (ALIS) says registration is mandatory if two criteria are met (criteria not retrieved). A mobility document says unregistered people "cannot practice agrology nor call themselves agrologists". The statute was not read: the King's Printer link failed and ALIS refused the connection. | Likely a registered AIA member (P.Ag. or RTAg in scope). | n/a | UNKNOWN → **needs counsel / AIA confirmation** | P7, P8 |
| **Quebec** | Out of scope. Already flagged in §5: OAQ reserved acts may cover fertilization plans. Keep Quebec farms excluded. | n/a | PAEF | UNKNOWN | §5 S21 |

**Consequence for the Prairie backup:** a Prairie plan approved by an Ontario-only person is at least a Manitoba offence (and probably a Saskatchewan one) for that person. In Manitoba it also means **no right to recover fees** for the service. Before any Prairie farm is accepted, the approver needs registration in that province. The agrology regulators have a labour-mobility arrangement (Agrologists Manitoba notice, P9, not read); a P.Ag. in one right-to-practice province may be able to register in another without re-examination. Confirm this with each institute.

---

## 2. Recommended minimum credential profile (hiring brief)

The law does not require any of this in Ontario. I recommend it because (a) the PDF names the person, and the title is the main trust signal; (b) E&O insurers price on credentials; (c) the profile has to work for the Prairie backup; (d) CCA and P.Ag. both carry codes of ethics and continuing-education duties, which help show the standard of care was met.

| Tier | Profile | Why |
|---|---|---|
| **Must have (Ontario launch)** | **CCA-ON** in good standing (ASA International exam plus Ontario exam, experience requirement, continuing education; status listed in the ASA professional search), **or** **P.Ag. (Ontario)** in good standing with a stated practice area in soil fertility / crop production. Plus: documented Ontario field-crop and winter-wheat fertility experience; comfort with OMAFA soil-test interpretation and units (P vs P2O5, K vs K2O, extraction method). | CCA-ON is the most common field-crop advisory credential in Ontario, and Ontario regulation already uses it as a competence marker for pest advice (O6). P.Ag. is the protected professional title. |
| **Strongly preferred** | Both CCA-ON and P.Ag., **or** CCA with the **4R Nutrient Management Specialist (4R NMS)** specialty (Ontario performance objectives exist, O11). Independence: no employment with, or commission from, a fertilizer retailer. Alternatively, disclose it, because our "vendor-neutral" claim depends on it. | The 4R NMS covers exactly the scope we deliver. Independence protects the Competition Act exposure on the vendor-neutral claim (§3.5). |
| **Only if phased-in NMA farms are accepted** | An OMAFA **nutrient management consultant certificate** (O. Reg. 267/03, Part X) and, for NASM land, a NASM plan development certificate. | Recommendation: **don't accept** farms that need an NMS/NMP/NASM plan from us. Accept them only if the farm already has a certified plan and ours is consistent with it (§5 rec. 2). Then the certificate is optional. |
| **Prairie backup (only if activated)** | **Registration with SIA (Sask.), Agrologists Manitoba, or AIA (Alta.)** for each province we serve, plus CCA-PP (Prairie Provinces board) if wanted. | Right-to-practice (§1). A CCA alone is not enough in Manitoba (P6). |

**How to verify (before naming, then every year and before each season):**
1. **CCA:** use the ASA / Science Societies "Find a Professional" search (O12). Search the name and the board code ("CCA-ON"; Prairie: "CCA-PP"). Screenshot it with the date and store it in the hiring file. Also ask the candidate for the certificate number and expiry.
2. **P.Ag. (Ontario):** search the OIA member listing (oia.on.ca, O3; exact URL not confirmed). If the person is not listed, ask OIA in writing. Farjad sends this, not the agent.
3. **SK / MB / AB:** check the public registers ("Find an Agrologist" on agrologistsmanitoba.ca, P6; SIA and AIA registers, URLs to confirm).
4. **NMA certificate:** ask for the OMAFA certificate number and expiry. I found no public register; confirm with OMAFA.
5. Record the evidence in an `agronomist_credential` record: body, number, class, verified_at, evidence file, expiry. This needs a `cp-database` ticket if the CTO agrees. The PDF prints only credentials verified within the last 12 months.
6. Ask the candidate to disclose any discipline history and any retailer affiliation.

---

## 3. Liability note

**3.1 Who carries it.**
- **The agronomist** owes the farmer a duty of care in negligence when giving advice the farmer relies on. Standard of care: that of a reasonably prudent professional in the field. For a P.Ag. or CCA, the code of ethics and practice standards inform it. That is a Saskatchewan analysis (P4, McDougall Gauley, 2016); Ontario should be similar under negligent misrepresentation principles (**needs counsel**). A P.Ag. or CCA also faces discipline by the OIA or ASA.
- **CloverProof** is the party in contract with the farmer (pilot terms) and the party that generates the numbers. It is exposed (a) **in contract** for its own promises, (b) **in negligence** for the engine, the pack constants (still `PLACEHOLDER` with `TODO(agronomist)`) and the process, and (c) **vicariously** for an employee's negligence. With a contractor, vicarious liability is less certain, but the direct claims against CloverProof remain. *Contractor status does not shield the company in practice* (**needs counsel**).
- **A split that probably won't hold:** "software proposes, human approves, so the human carries it all." The engine is ours and the AI pre-review is ours. If a wrong number came from a placeholder constant and the human missed it, both parties are likely in the claim.

**3.2 Employee vs contractor.**

| | Employee | Contractor |
|---|---|---|
| Vicarious liability of CloverProof | Yes (in the course of employment) | Less likely, but direct claims against CloverProof remain |
| Control over method, review gate, `minutes_spent` logging | Natural | Too much control risks reclassification as an employee (CRA / ESA / WSIB tests) → **needs counsel / accountant** |
| Insurance | Company E&O covers employees acting in scope (check wording) | The contractor holds own E&O **and** CloverProof holds its own; the contract requires the contractor's cover, names CloverProof as additional insured where available, and requires a certificate before the first review |
| Contract must cover | Job description, credential maintenance, IP in edits/reasons (calibration data) | Scope, standard of care, credential warranty and notice of lapse or discipline, indemnities both ways, insurance, confidentiality and data handling (privacy notice), **assignment to CloverProof of rights in review notes, reasons and edited numbers (calibration dataset)**, right to refuse approval, no retailer conflicts |

**3.3 E&O insurance.** Needed before the first plan reaches a real farm (already pri 9 in compliance-review §6; this note raises it to a **blocker for G1**). Ask the broker, in writing:
1. Whether agronomic or agrology advice is covered for a technology company, not only for a professional firm.
2. Whether there is an exclusion for software or algorithm output, or for "AI".
3. Whether a contractor reviewer is covered, or whether the contractor needs a separate policy.
4. Territory: Ontario now, Prairie later.
5. Crop-loss limits and retroactive date.

The CCA and OIA may offer member-group E&O. **Unknown, not checked.** A liability cap in the pilot terms (§9, counsel-held) does not replace insurance.

**3.4 What the PDF may print (titles).**
- Print: `Approved by [Full name], [credential(s) verified on YYYY-MM-DD], on [date]`. Example forms, valid only if held: "Jane Doe, P.Ag. (Ontario)", "Jane Doe, CCA-ON", "Jane Doe, CCA-ON, 4R NMS".
- Don't print: "P.Ag." or "Professional Agrologist" unless the person is an OIA member in that class (an s. 9(3) offence). "Agrologist" alone: the bill lists only the full designations and abbreviations, so whether the bare word is protected is **UNKNOWN**. Avoid it unless the person is a member. Don't print "CCA" if certification has lapsed. Don't print "certified nutrient management plan" or "NMP/NMS/NASM" (§5 rec. 1). Never print any human title for `ai_reviewed`.
- "Agronomist" as a job description is not a protected title in Ontario as far as I found (**UNKNOWN; confirm**). It is safe to describe the role as "CloverProof's reviewing agronomist" if the person has the qualifications.
- Never present the founder as the reviewing agronomist (D4; support-macros).
- Prairie plans: print the provincial registration (e.g. "P.Ag. (SK)") of the person who approved them.

**3.5 AI-assist disclosure.**
- I found no Ontario or federal statute that requires disclosing AI use in private-sector agronomic advice. Federal AIDA (Bill C-27) died on the Order Paper; **from memory, not verified this session.** Ontario's Bill 194 (2024) covers the public sector; **from memory, not verified**.
- The real constraint is the **Competition Act misleading-representation rule** (s. 52 criminal; s. 74.01(1)(a) civil). The test is the "general impression" plus the literal meaning, and fine print does not cure a misleading impression (O13). If the PDF or marketing says or implies "agronomist-reviewed" when a plan was only `ai_reviewed`, it is misleading. The same applies to "vendor-neutral" if the reviewer is retailer-paid.
- Proposed PDF wording (for `proof-pdf-wording.md`, which is referenced in `pilot-sop.md` but **does not exist in `docs/operations/legal/` yet**):
  > "How this plan was made: CloverProof software calculated the proposal. An AI-assisted pre-check flagged possible issues for the agronomist. [Name, verified credentials] reviewed every number and approved this plan on [date]. The AI check cannot approve a plan."
- Professional-practice angle: whether a P.Ag. or CCA approving AI-pre-checked work must disclose it under their code of ethics or practice standards is **UNKNOWN**. The candidate should check with their own body.

---

## 4. Actions (prepared; Farjad acts)

| # | Action | Owner | When |
|---|---|---|---|
| 1 | Use §2 "Must have" as the hiring-brief credential line | COO → Farjad | Before posting |
| 2 | Verify credentials per §2 steps 1–4, store evidence | COO (Farjad sends any written inquiry) | Before naming; target 2027-01-29 (S5 gate) |
| 3 | Decide employee vs contractor; counsel drafts the agreement (§3.2 list) | Farjad + counsel | Before naming |
| 4 | E&O quote with the §3.3 questions | Farjad, COO | Before first real-farm plan (G1 blocker) |
| 5 | Create `proof-pdf-wording.md` from §3.4–3.5 | `legal-compliance-specialist` (next task, if the COO asks) | Before PDF template freeze |
| 6 | `agronomist_credential` record, and the PDF prints only verified credentials | `cp-database`, `cp-pdf` via CTO | Before S5 |
| 7 | Prairie: no farm accepted until the approver is registered in that province and counsel confirms | Farjad | Before any Prairie intake |
| 8 | Intake screen stays: NMA phased-in farms excluded or kept consistent with their certified plan | COO | Now |

---

## Sources (checked 2026-11-16)
Note: e-Laws (ontario.ca/laws) returned HTTP 403 and alis.alberta.ca refused the connection from this environment. Items marked *search* rely on search-result summaries; read the page before relying on them.

- O1 *Ontario Institute of Professional Agrologists Act, 2013*, S.O. 2013, c. Pr9: https://www.ontario.ca/laws/statute/pr13009 *(403, not read)*
- O2 Bill Pr15 (40th Parl., 2nd Sess.), text as on OLA: https://www.ola.org/en/legislative-business/bills/parliament-40/session-2/bill-pr15 *(fetched; ss. 2(1), 9(1)–(4), 12 read. Bill text, confirm it matches the enacted Act)*
- O3 OIA About / FAQ / Code of Ethics: https://oia.on.ca/page/AboutOIA, https://oia.on.ca/page/FAQ, https://oia.on.ca/page/CodeofEthics *(403 / search; "registration … voluntary in Ontario")*
- O4 Agrologists Canada, provincial regulators: https://agrologistscanada.ca/provincial-regulators/ *(fetched: Ontario "Right to Title"; SK and MB "Right to Practice")*
- O5 O. Reg. 267/03 (NMA), Part X certificates: https://www.ontario.ca/laws/regulation/030267 *(search; current version not read)*; AgriSuite: https://www.ontario.ca/page/agrisuite *(search)*; OMAFRA Factsheet 21-025: compliance-review S16
- O6 MOECC, "What Professional Pest Advisors Need to Know…" (2015), copy at https://legislature.vermont.gov/Documents/2022/WorkGroups/House%20Agriculture/Bills/H.626/Witness%20Documents/H.626~Ontario%20Ministry%20of%20Agriculture,%20Food%20and%20Rural%20Affairs~Professional%20Pest%20Advisors%20Information%20on%20Regulatory%20Requrements~2-17-2022.pdf *(fetched but not text-extractable; content via search summary)*
- O7 O. Reg. 63/09 (Pesticides Act): https://www.ontario.ca/laws/regulation/090063 *(search; not read)*
- O8 O. Reg. 134/20 (Class 12 → Class E): https://www.ontario.ca/laws/regulation/r20134 *(search)*
- O9 OFA letter on 63/09 amendments: https://ofa.on.ca/resources/ofa-letter-requesting-regulation-63-09-amendments/ *(search)*
- O10 *Fertilizers Act* (CFIA): https://laws-lois.justice.gc.ca/eng/acts/F-10/ *(not fetched; statement from memory)*
- O11 CCA 4R NMS Region 2 Ontario performance objectives (2020): https://www.certifiedcropadviser.org/files/certifiedcropadviser/4r-nms-region-2-ontario-performance-objectives-2020.pdf *(search)*; CCA Ontario exam and experience: https://ontariograinfarmer.ca/?p=1158 *(search)*
- O12 ASA / Science Societies "Find a Professional": https://www.sciencesocieties.org/certifications/professional-search *(search; board-code search method)*
- O13 Competition Bureau, general impression test: https://competition-bureau.canada.ca/deceptive-marketing-practices/general-impression-test *(search)*; Competition Act s. 74.01: https://laws-lois.justice.gc.ca/eng/acts/C-34/ *(not fetched; current text not read)*
- P1 SIA, Importance of Registration / Complaints and Discipline: https://sia.sk.ca/?p=112, https://sia.sk.ca/member-discipline-and-complaints/ *(search)*
- P2 SIA Regulatory Bylaws 2026: https://sia.sk.ca/wp-content/uploads/2026/06/Regulatory-Bylaws-2026.pdf *(search, not read)*
- P3 Western Producer, 2018 definition change: https://www.producer.com/news/new-agrology-definition-allows-more-to-practice-in-area-of-expertise *(search)*
- P4 McDougall Gauley LLP, "Agrology: Provincial Regulation, Negligence and Potential Areas of Liability" (2016-08-16): https://www.mcdougallgauley.com/insights/agrology-provincial-regulation-negligence-and-potential-areas-liability *(fetched)*
- P5 *The Agrologists Act*, C.C.S.M. c. A50 (unofficial consolidation): https://web2.gov.mb.ca/laws/statutes/ccsm/a050.php?lang=en *(fetched; ss. 1(1), 1(2), 15 read)*
- P6 Agrologists Manitoba, registration FAQ and Find an Agrologist: https://agrologistsmanitoba.ca/become-an-agrologist/faq-why-register/, https://agrologistsmanitoba.ca/find-an-agrologist/ *(search)*
- P7 ALIS Alberta, Agrologist profile: https://alis.alberta.ca/occinfo/occupations-in-alberta/occupation-profiles/agrologist *(connection refused; search snippet)*
- P8 Alberta Institute of Agrologists bylaws: https://www.aia.ab.ca/document/7461/2023_01_18_Bylaws.pdf *(search)*
- P9 Agrologists Manitoba, mobility rights notice: https://agrologistsmanitoba.ca/regulators-confirm-mobility-rights-for-agrology-professionals/ *(search, not read)*

## Needs licensed counsel
1. Confirm the enacted *Ontario Institute of Professional Agrologists Act, 2013* matches the bill text (s. 12 non-member practice saving; s. 9 designations; penalty provision). Is the bare word "agrologist" protected in Ontario?
2. Confirm that no Ontario statute or regulation (NMA, *Environmental Protection Act*, *Pesticides Act*, consumer law) requires a licence to give fertilizer-rate advice to a crop-only farm.
3. Saskatchewan and Alberta: does remote fertilizer advice to a farm in the province count as practising agrology, and which registration category is needed? Is CloverProof (the company) itself "practising" and so in need of a corporate permit or a responsible member? Same question for Manitoba, given that "every act" includes advice.
4. Liability allocation between CloverProof and the reviewer (contract, negligence, vicarious liability) when the error originates in the engine or in a `PLACEHOLDER` constant; enforceability of indemnities and the pilot-terms §9 cap.
5. Employee vs contractor classification (CRA, ESA, WSIB) given the control we exercise (review gate, timers, `minutes_spent`).
6. IP and data: assignment of the reviewer's edits and reasons (calibration dataset) and confidentiality, in the agreement.
7. Whether the AI-assist disclosure wording (§3.5) and the credential line (§3.4) avoid a misleading general impression under the Competition Act.
8. E&O: whether the policy wording covers software- and AI-assisted advice, and whether the contractor's own cover is required.
