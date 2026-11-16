# CloverProof privacy notice (website + pilot) — DRAFT v0.2

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> Drafted by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO. v0.1 2026-11-16; v0.2 2026-11-16 (CPO decisions D4 + R4); v0.2.1 2026-11-16 (CPO decision D-7).
> Status: draft. Do not publish until every `[PLACEHOLDER]` is filled and counsel has reviewed it (OQ-07, see `oq-07-decision-pack.md`).

**What changed in v0.2**
- D4: plan review is now described as *AI-assisted, human-approved*. An AI system (`cp-agronomist`) may check a plan; only a named human agronomist can approve a real farm's plan, and nothing reaches a farmer before that. The founder is **not** described as the agronomist anywhere.
- R4: pilot eligibility = farms in **Ontario, Canada** (another Canadian province only if we extend the pilot in writing; Quebec excluded). GDPR text is kept but reduced to EU/EEA **website visitors**.
- D-7 (CPO, 2026-11-16, policy): the AI reviewer `cp-agronomist` never receives real pilot farmers' personal data or identifiable farm data — only published sources, synthetic cases and de-identified case data (no names, contacts, addresses or exact field geometry). §4, §6, §8 and Part B updated. Any change needs a DPA with the AI provider AND an update to this notice, decided by Farjad Iranmehr.
- Data residency for pilot farm data is **OPEN** (Railway has no Canadian region; ADR 0004). §7 carries both options; one must be deleted before publication.

Open placeholders (Farjad Iranmehr must supply): `[LEGAL ENTITY]`, `[CONTACT EMAIL]`, `[ADDRESS]`, `[PRIVACY OFFICER NAME]`, `[RAILWAY REGION]`, `[RESIDENCY DECISION]`, `[AI PROVIDER]`, `[HUMAN AGRONOMIST NAME, CREDENTIALS]`, `[EMAIL PROVIDER]`, `[EFFECTIVE DATE]`, and the retention periods marked *proposed*.

Sources are listed at the end (S1–S23), with the date checked. Facts about our systems come from the repo (`website/db/migrations/0001_pilot_request.sql`, `db/migrations/0003–0009`, `website/src/app/[lang]/actions.ts`, ADR 0004, ADR 0005) and from `docs/plans/backend-plan-reconciliation.md` on `origin/backend-traceability` (D4, R4).

---

## Part A — Full privacy notice (publish as the long-form notice)

### 1. Who we are
CloverProof is operated by **[LEGAL ENTITY]**, [ADDRESS], Ontario, Canada ("we", "us"). We are responsible for the personal information described here.
Privacy contact: **[PRIVACY OFFICER NAME]**, [CONTACT EMAIL], [ADDRESS].

CloverProof is software that turns farm data into a field-specific fertilizer plan. An AI system may help check each plan; a human agronomist reviews and approves every plan before you see it. Each approved plan comes with a proof PDF that records how it was made.

### 2. The short version
- We collect only what we need to run the website and the pilot.
- The 2027 pilot is open to farms in **Ontario, Canada** only.
- **A person, not software, approves your plan.** An AI system may help check a plan, but no plan reaches you until our human agronomist, [HUMAN AGRONOMIST NAME, CREDENTIALS], has reviewed and approved it.
- We do not sell your information, and we do not use advertising trackers or analytics on the website. *(True as of 2026-11-16: `website/package.json` has no analytics or tracking dependency. Re-check before every release.)*
- Website form data is hosted by Railway, a US company, and may be stored and processed in the United States. Where pilot farm data is stored: see section 7.
- With your permission, we use **de-identified** pilot results to improve our engine.
- You can ask to see, correct or delete your information at any time: [CONTACT EMAIL].

### 3. What we collect and why

| What | When | Why |
|---|---|---|
| Name, email, country, farm size (as typed), main crop, notes, the language you used, the exact consent wording you agreed to and the time | You send the pilot request form | Decide whether we can include your farm in the pilot and contact you about it |
| Contact details (name, email, phone if given), farm name, region | You join the pilot | Run the pilot and talk to you |
| Field names, field area, field boundary or location (if given), crop, target yield, previous crop, plan dates | During the pilot | Calculate the plan for each field |
| Soil-test results (lab, date, depth, method, values) | During the pilot | Calculate P and K advice; without a soil test we give nitrogen advice only |
| Engine output, AI check notes, the human agronomist's final numbers, the reason for any change, review time | During the pilot | Check and approve every number before it reaches you; keep an unchangeable record of how each plan was made |
| What you actually applied (product, rate, date) | If you choose to tell us | Compare plan with practice |
| Proof PDF and its fingerprint (SHA-256) | When a plan is approved by the human agronomist | Give you a record of the plan and let anyone check the file has not been changed |
| De-identified comparison of engine output vs the human agronomist's final numbers ("calibration data") | During and after the pilot | Improve the engine's accuracy for future users — **with your separate consent** (section 5) |
| Technical logs kept by our host (IP address, browser, time, page) | Every website visit | Keep the site running and secure |
| News or marketing emails | Only if you tick the separate box | Send you CloverProof news (CASL express consent) |

Information about your farm and fields is treated as personal information when it can be linked to you (for example, a sole-proprietor farm). *(Assumption — counsel to confirm; S1, S11 Art. 4(1).)*

We do not ask for and do not want: government ID numbers, bank details, health information, or information about children.

### 4. How plans are reviewed — AI assists, a person decides
1. Our software (the engine) calculates a proposed plan from your data.
2. An **AI system** may check a **de-identified** copy of the proposal (for example, consistency of the numbers and the plain-language explanation) and leave notes. Before the AI sees it, we remove your name, contact details, address, farm and field names, and exact field boundaries or coordinates; it sees only the region (county level), crop, previous crop, target yield, soil-test values and plan date. The AI system never receives information that identifies you or your farm. *(D-7, `oq-07-decision-pack.md`; whether county-level region plus field values could still identify a farm is a counsel question — Needs licensed counsel item 3.)*
3. Our **human agronomist**, [HUMAN AGRONOMIST NAME, CREDENTIALS], approves, changes or rejects every number. An AI check alone can never approve a plan for your farm; our system blocks it.
4. Only an approved plan is sent to you. You keep the final decision about what you apply.

No decision about you is made by software or AI alone (S11 Arts. 13(2)(f), 22; S23). You can ask us how a number in your plan was produced; every plan shows the reason for each number and its confidence level.

### 5. Using pilot results to improve the engine (calibration)
The difference between what the engine proposed and what the human agronomist approved tells us where the engine is wrong. With your consent we keep a **de-identified** copy of this comparison:
- removed: your name, email, phone, farm name, field names, notes, exact field boundaries and coordinates;
- generalised: location to province or a coarse region, dates to season (month or year);
- kept: crop, previous crop, target yield, soil-test values and method, engine version, engine output, the human agronomist's final numbers and reason (with any names removed from the text).

AI check notes are not counted as agronomist decisions in this comparison.

De-identified data can sometimes be re-identified when combined with other information. We keep it access-restricted, do not publish it at field level, and do not try to re-identify anyone. You can say no to this use and still take part in the pilot. You can withdraw later; we will then stop adding your data and remove what can still be linked to you. *(Whether calibration can be a condition of the pilot instead of optional is a counsel question — `oq-07-decision-pack.md` §3 Q8.)*

### 6. Who we share it with
We do **not** sell, rent or trade personal information. We share it only with:
- **Railway Corporation** (US) — hosts our website, database and proof-PDF storage, as our service provider under its Data Processing Addendum (S15).
- **No AI provider receives information that identifies you or your farm.** The AI system that may check plans ([AI PROVIDER]) receives only de-identified case data as described in section 4 — no names, contact details, addresses, farm or field names, or exact field geometry. We will not send identifiable pilot data to any AI provider unless we first sign a data-processing agreement with it and update this notice. *(D-7. Confirm the provider's retention and no-training terms for the de-identified data before use.)*
- **[EMAIL PROVIDER]** — if we use one to send email. *(None in the repo today; fill or delete.)*
- **[HUMAN AGRONOMIST NAME]** — if the agronomist is a contractor rather than an employee, under a written confidentiality and data-processing agreement. *(Fill or delete.)*
- **Anyone you ask us to share with** — for example, if you give a proof PDF to your lender or certifier, you choose to share it.
- **Authorities** — only where the law requires it.

The proof PDF records how a plan was made. It is not accepted, approved or endorsed by any lender, certifier, insurer, buyer or regulator.

### 7. Where your information is stored
**Website form data.** Our host Railway states that its primary processing is in the United States (S15 §9.1). Railway has no Canadian region; its regions are US West (California), US East (Virginia), EU West (Amsterdam) and Southeast Asia (Singapore) (S14). Our website runs in **[RAILWAY REGION]**.

**Pilot farm data.** `[RESIDENCY DECISION — OPEN. Keep ONE option, delete the other before publishing.]`
- *Option US:* "Your pilot data is stored with Railway in [RAILWAY REGION], United States."
- *Option Canada:* "Your pilot data is stored in Canada with [CANADIAN HOST]." *(requires a host change — ADR needed)*

Where data is stored or accessed in the United States, it may be available to US courts, law enforcement and national-security authorities under US law (S4). We stay responsible for your information when our providers process it, and we use contracts to require comparable protection (S4).

*EU/EEA visitors to our website:* we collect your form data directly from you in Canada, which the EU recognises as adequate (S12); where Railway processes it in the US, Railway's DPA provides the EU Standard Contractual Clauses (S15 §9). *(Counsel to confirm — `oq-07-decision-pack.md` §3 Q9.)*

### 8. How long we keep it (*proposed — Farjad to approve*)
| Data | Proposed retention |
|---|---|
| Pilot request not accepted, or no reply | 12 months after the decision, then deleted |
| Pilot farm, field, soil-test, plan, review and proof records | Pilot season + 2 years (so you can use your plan records), then deleted or de-identified |
| Calibration data (de-identified, with consent) | Until the engine is retired or you withdraw consent, whichever is first |
| Marketing consent record | While you are subscribed + 3 years (proof of consent) |
| Deletion request record (who, what, when — no farm data) | 3 years |
| Host technical logs | As set by Railway; *[confirm Railway log retention for our plan]* |
| AI provider copies (de-identified case data only; no identifiable pilot data — D-7) | *[confirm provider retention; target: none beyond the request]* |
| Breach records | At least 24 months after we determine a breach occurred (S5) |

### 9. How we protect it
Server-only database access; private file storage; passwords hashed (argon2id); session tokens stored only as hashes; access limited to the CloverProof team members who need it; every plan record is write-once so it cannot be silently changed; only a human user with the agronomist role can approve a real farm's plan. No system is perfectly secure. If a breach creates a real risk of significant harm to you, we will tell you and report it to the Privacy Commissioner of Canada as required (S5), and to EU authorities where GDPR requires it (S11 Arts. 33–34).

### 10. Your rights
You can ask us to:
- tell you what we hold about you and give you a copy;
- correct it;
- delete it;
- explain how a number in your plan was produced, and who approved it;
- stop using it for calibration or marketing (withdraw consent);
- *(EU/EEA website visitors)* restrict or object to processing, and receive your data in a portable format.

Email [CONTACT EMAIL] or write to [ADDRESS]. We may ask you to confirm your identity. We reply within 30 days (S1 s.8(3), to verify) and, for EU/EEA requests, within one month (S11 Art. 12(3)).

**Deletion and the plan record.** Approved plans and proof PDFs are stored write-once so nobody can alter them. When you ask for deletion we remove or irreversibly de-identify everything that links those records to you (names, contacts, farm and field names, location). If we must keep anything (for example, to defend a legal claim), we will tell you what and why. *(Engineering gap: the database currently blocks deletion of these records — compliance-review.md G2.)*

### 11. Unsubscribing
Every marketing email has an unsubscribe link. We act on it within 10 business days at most (S6 s.11(3), S9) — in practice, straight away.

### 12. Complaints
Contact us first. You can also complain to:
- the **Office of the Privacy Commissioner of Canada**: https://www.priv.gc.ca;
- *(EU/EEA website visitors)* the data-protection authority where you live or work.

### 13. Children
CloverProof is for farm businesses and is not directed to anyone under 18. *(Age threshold to be confirmed by counsel.)*

### 14. Changes
We will post changes here with a new date and tell pilot farms by email before a material change takes effect (for example, if we change who approves plans or where data is stored).

Effective date: [EFFECTIVE DATE]. Version: 0.2-draft.

---

## Part B — Website privacy-page copy (hand to `cp-website`, NB-WEB-05)

Shape matches `website/src/messages/en.json` → `privacy` (keys `title`, `draft`, `updated`, `sections[] {h, p}`). English only; other locales only after native review (ADR 0003). Replace placeholders before release; keep `draft` until counsel signs off. Copy of this Part B: `side-session-notes/.../coo-website-privacy-copy.md`.

```json
{
  "title": "Privacy notice",
  "draft": "Draft — under review before launch.",
  "updated": "Last updated: [EFFECTIVE DATE]",
  "sections": [
    {
      "h": "Who we are",
      "p": "CloverProof is operated by [LEGAL ENTITY], [ADDRESS], Ontario, Canada. Privacy questions: [CONTACT EMAIL]."
    },
    {
      "h": "Who can join the pilot",
      "p": "The 2027 pilot is open to farms in Ontario, Canada. You can send a request from anywhere, but we can only include Ontario farms."
    },
    {
      "h": "What we collect",
      "p": "When you request a pilot plan we collect what you enter: name, email, country, approximate farm size, main crop and any notes, plus the language you used and the exact consent wording you agreed to, with the time. If you join the pilot we also collect farm, field and soil-test information and the plans we make for you."
    },
    {
      "h": "Why we collect it",
      "p": "To decide whether we can include your farm in the pilot, to contact you about it and, if you join, to make and record your fertilizer plans. We send news emails only if you tick the separate box for them."
    },
    {
      "h": "How plans are reviewed",
      "p": "Our software proposes each plan. An AI system may help check it. The AI system never receives your name, contact details, address or exact field boundaries; it sees only de-identified case data. A human agronomist then approves, changes or rejects every number before you see it — an AI check alone never approves a plan. You make the final decision about what you apply."
    },
    {
      "h": "Improving the engine",
      "p": "If you agree, we keep a de-identified copy of pilot results (the engine's proposal vs the human agronomist's final numbers) to make the engine more accurate. Names, contact details, farm and field names and exact locations are removed. You can say no and still take part."
    },
    {
      "h": "Who sees it",
      "p": "Only the CloverProof team members who need it, our human agronomist, and Railway, which hosts our website and database as our service provider. No AI provider receives information that identifies you or your farm. We do not sell your information and we do not use advertising trackers or analytics."
    },
    {
      "h": "Where it is stored",
      "p": "Website requests are stored by Railway, a US company, and may be stored and accessed in the United States, where US authorities may be able to access them under US law. [RESIDENCY DECISION: where pilot farm data is stored.] We use data-processing contracts to protect your information."
    },
    {
      "h": "How long we keep it",
      "p": "Pilot requests we can't accept: 12 months. Pilot records: the pilot season plus 2 years. De-identified engine data: until you withdraw consent or we retire the engine. You can ask us to delete your details at any time."
    },
    {
      "h": "Your rights",
      "p": "You can ask to see, correct or delete your information, ask how a number in your plan was produced, and withdraw consent at any time, by emailing [CONTACT EMAIL]. We reply within 30 days. You can complain to the Office of the Privacy Commissioner of Canada (priv.gc.ca) or, if you are in the EU, to your local data-protection authority."
    }
  ]
}
```

Notes for `cp-website`:
- Do not ship while any `[...]` remains. D-7 (decided): the AI system gets de-identified data only; do not add an AI provider to "Who sees it" unless Farjad approves a change (DPA + notice update).
- Retention figures are *proposed*; do not ship until Farjad approves them.
- "We do not use advertising trackers or analytics" must be re-checked whenever a dependency or script is added.
- The pilot form must say "Ontario farms only" next to the country field; a non-Ontario request is stored and answered, not enrolled.
- Link this page from the pilot form (already done: `pilot.privacyLink`).

---

## Sources (checked 2026-11-16)
Some Government of Canada and CRTC pages refused connections from this environment; those are marked *(not fetched — confirmed via search summaries only; verify before reliance)*.

- S1 PIPEDA, S.C. 2000, c. 5, incl. Schedule 1 and s. 8(3) — https://laws-lois.justice.gc.ca/eng/acts/P-8.6/ *(not fetched)*
- S2 OPC, PIPEDA fair information principles — https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/p_principle/ *(not fetched)*
- S3 OPC, Guidelines for obtaining meaningful consent (2018) — https://www.priv.gc.ca/en/privacy-topics/collecting-personal-information/consent/gl_omc_201805/ *(not fetched; search-confirmed)*
- S4 OPC, Guidelines for processing personal data across borders (2009) — https://www.priv.gc.ca/en/privacy-topics/airports-and-borders/gl_dab_090127/ *(not fetched; search-confirmed)*
- S5 OPC breach guidance — https://www.priv.gc.ca/en/privacy-topics/business-privacy/safeguards-and-breaches/privacy-breaches/respond-to-a-privacy-breach-at-your-business/gd_pb_201810/ ; SOR/2018-64 — https://canadagazette.gc.ca/rp-pr/p2/2018/2018-04-18/html/sor-dors64-eng.html *(search-confirmed: 24-month record keeping)*
- S6 CASL, S.C. 2010, c. 23 — https://laws-lois.justice.gc.ca/eng/acts/E-1.6/ *(not fetched)*
- S9 CRTC CASL FAQ — https://crtc.gc.ca/eng/com500/faq500.htm *(not fetched; search-confirmed 10 business days)*
- S11 GDPR, Regulation (EU) 2016/679 — https://eur-lex.europa.eu/eli/reg/2016/679/oj *(fetched earlier 2026-11-16; Arts. 3, 4, 7, 13, 21, 27, 45 read; Art. 22 and 13(2)(f) cited from the same text — verify)*
- S12 Commission Decision 2002/2/EC (Canada adequacy) — https://eur-lex.europa.eu/eli/dec/2002/2/oj *(fetched)*
- S14 Railway deployment regions — https://docs.railway.com/reference/deployment-regions *(fetched)*
- S15 Railway Data Processing Addendum — https://railway.com/legal/dpa *(fetched)*
- S23 Federal/provincial/territorial privacy regulators, *Principles for responsible, trustworthy and privacy-protective generative AI technologies* (7 Dec 2023) — listed at https://www.priv.gc.ca/en/privacy-topics/ai-technology-and-innovation/artificial-intelligence/leadership-ai/ ; text at https://oipc.bc.ca/documents/guidance-documents/2811 *(search only: transparency principle — tell individuals how AI uses their information and its role in decisions; full text not read — verify)*
- Decisions: `origin/backend-traceability:docs/plans/backend-plan-reconciliation.md` D4, R4 (CPO, 2026-11-16).

## Needs licensed counsel
1. Whether PIPEDA applies to a free pilot (commercial activity) and whether farm/field data is personal information for incorporated vs sole-proprietor farms.
2. Whether the §4 wording is adequate transparency about AI-assisted review under PIPEDA openness/consent and the 2023 generative-AI principles (S23), and under GDPR Arts. 13(2)(f)/22 for website visitors.
3. D-7: whether our de-identification for the AI reviewer (county-level region, crop, previous crop, target yield, soil-test values, plan date kept) makes the data non-personal under PIPEDA, so no transfer-for-processing contract is needed; and what a DPA must contain if Farjad later allows identifiable data.
4. Whether calibration use can be a condition of the pilot or must stay optional (PIPEDA 4.3.3; GDPR Art. 7(4)).
5. Whether our de-identification standard is enough to treat calibration data as non-personal.
6. Residency: whether US storage of pilot data is acceptable with disclosure, or whether Canadian storage should be required (business/trust decision too).
7. EU website-visitor transfer analysis and whether an Art. 27 EU representative is needed.
8. If the pilot extends to a Prairie province: whether a provincial private-sector privacy law applies instead of PIPEDA (not assessed).
9. Retention periods and the "legal claims" exception to deletion of immutable plan records.
10. Minimum age wording.
