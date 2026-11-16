# CloverProof privacy notice (website + pilot) — DRAFT

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> Drafted by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO, 2026-11-16.
> Status: draft. Do not publish until every `[PLACEHOLDER]` is filled and counsel has reviewed it.

Open placeholders (Farjad Iranmehr must supply): `[LEGAL ENTITY]`, `[CONTACT EMAIL]`, `[ADDRESS]`, `[PRIVACY OFFICER NAME]`, `[RAILWAY REGION]`, `[EMAIL PROVIDER]`, `[EFFECTIVE DATE]`, and the retention periods marked *proposed*.

Sources are listed at the end (S1–S16), with the date checked. Facts about our systems come from the repo (`website/db/migrations/0001_pilot_request.sql`, `db/migrations/0003–0009`, `website/src/app/[lang]/actions.ts`, ADR 0004, ADR 0005).

---

## Part A — Full privacy notice (publish as the long-form notice)

### 1. Who we are
CloverProof is operated by **[LEGAL ENTITY]**, [ADDRESS], Ontario, Canada ("we", "us"). We are responsible for the personal information described here.
Privacy contact: **[PRIVACY OFFICER NAME]**, [CONTACT EMAIL], [ADDRESS].

CloverProof is software that turns farm data into a field-specific fertilizer plan, reviewed by our agronomist, with a proof PDF that records how the plan was made.

### 2. The short version
- We collect only what we need to run the website and the pilot.
- We do not sell your information, and we do not use advertising trackers or analytics on the website. *(True as of 2026-11-16: `website/package.json` has no analytics or tracking dependency. Re-check before every release.)*
- Our database and files are hosted by Railway, a US company. Your information may be stored and processed in the United States.
- With your permission, we use **de-identified** pilot results to improve our engine.
- You can ask to see, correct or delete your information at any time: [CONTACT EMAIL].

### 3. What we collect, why, and our legal basis

| What | When | Why | Legal basis for people in the EU/EEA (GDPR Art. 6) |
|---|---|---|---|
| Name, email, country, farm size (as typed), main crop, notes, the language you used, the exact consent wording you agreed to and the time | You send the pilot request form | Decide whether we can include your farm in the pilot and contact you about it | Steps you asked us to take before a pilot agreement (Art. 6(1)(b)); consent for the contact itself is also recorded |
| Contact details (name, email, phone if given), farm name, region, country | You join the pilot | Run the pilot and talk to you | Performance of the pilot agreement (Art. 6(1)(b)) |
| Field names, field area, field boundary or location (if given), crop, target yield, previous crop, plan dates | During the pilot | Calculate the plan for each field | Performance of the pilot agreement (Art. 6(1)(b)) |
| Soil-test results (lab, date, depth, method, values) | During the pilot | Calculate P and K advice; without a soil test we give nitrogen advice only | Performance of the pilot agreement (Art. 6(1)(b)) |
| Engine output, the agronomist's final numbers, the reason for any change, review time | During the pilot | Approve or change every number before it reaches you; keep an unchangeable record of how each plan was made | Performance of the pilot agreement (Art. 6(1)(b)); our legitimate interest in an audit trail (Art. 6(1)(f)) |
| What you actually applied (product, rate, date) | If you choose to tell us | Compare plan with practice | Performance of the pilot agreement (Art. 6(1)(b)) |
| Proof PDF and its fingerprint (SHA-256) | When a plan is approved | Give you a record of the plan and let anyone check the file has not been changed | Performance of the pilot agreement (Art. 6(1)(b)) |
| De-identified comparison of engine output vs agronomist's final numbers ("calibration data") | During and after the pilot | Improve the engine's accuracy for future users | **Your separate consent** (Art. 6(1)(a)); see section 5 |
| Technical logs kept by our host (IP address, browser, time, page) | Every website visit | Keep the site running and secure | Our legitimate interest in security (Art. 6(1)(f)) |
| News or marketing emails | Only if you tick the separate box | Send you CloverProof news | Your consent (Art. 6(1)(a)); CASL express consent |

Information about your farm and fields is treated as personal information when it can be linked to you (for example, a sole-proprietor farm). *(Assumption — counsel to confirm; S1, S11 Art. 4(1).)*

We do not ask for and do not want: government ID numbers, bank details, health information, or information about children.

### 4. Agronomist review — no automated decisions
The engine proposes numbers; our agronomist approves, changes or rejects every number before it is sent to you. No decision about you is made by software alone (GDPR Art. 22, S11). You keep the final decision about what you apply.

### 5. Using pilot results to improve the engine (calibration)
The difference between what the engine proposed and what the agronomist approved tells us where the engine is wrong. With your consent we keep a **de-identified** copy of this comparison:
- removed: your name, email, phone, farm name, field names, notes, exact field boundaries and coordinates;
- generalised: location to province/state or a coarse region, dates to season (month or year);
- kept: crop, previous crop, target yield, soil-test values and method, engine version, engine output, agronomist's final numbers and reason (with any names removed from the text).

De-identified data can sometimes be re-identified when combined with other information. We keep it access-restricted, do not publish it at field level, and do not try to re-identify anyone. You can say no to this use and still take part in the pilot. You can withdraw later; we will then stop adding your data and remove what can still be linked to you. *(Whether calibration can be a condition of the pilot instead of optional is a counsel question — see compliance-review.md.)*

### 6. Who we share it with
We do **not** sell, rent or trade personal information. We share it only with:
- **Railway Corporation** (US) — hosts our website, database and proof-PDF storage, as our service provider (processor) under its Data Processing Addendum (S15).
- **[EMAIL PROVIDER]** — if we use one to send email. *(None in the repo today; fill or delete.)*
- **Anyone you ask us to share with** — for example, if you give a proof PDF to your lender or certifier, you choose to share it.
- **Authorities** — only where the law requires it.

The proof PDF records how a plan was made. It is not approved or endorsed by any lender, certifier or regulator.

### 7. Where your information is stored (cross-border transfer)
Our host Railway states that its primary processing is in the United States (S15 §9.1). Railway has no Canadian region; its regions are US West (California), US East (Virginia), EU West (Amsterdam) and Southeast Asia (Singapore) (S14). Our services run in **[RAILWAY REGION]**.

This means your information may be stored in, and accessed from, the United States, and may be available to US courts, law enforcement and national-security authorities under US law (S4).

- **Canada:** we stay responsible for your information when our provider processes it, and we use a contract to require comparable protection (S4).
- **EU/EEA:** we collect your information directly from you in Canada. The EU recognises Canada (PIPEDA) as adequate (S12). Where our provider processes EU personal data in the US, Railway's DPA provides the EU Standard Contractual Clauses (S15 §9). *(Counsel to confirm the transfer analysis — see compliance-review.md.)*

### 8. How long we keep it (*proposed — Farjad to approve*)
| Data | Proposed retention |
|---|---|
| Pilot request not accepted, or no reply | 12 months after the decision, then deleted |
| Pilot farm, field, soil-test, plan, review and proof records | Pilot season + 2 years (so you can use your plan records), then deleted or de-identified |
| Calibration data (de-identified, with consent) | Until the engine is retired or you withdraw consent, whichever is first |
| Marketing consent record | While you are subscribed + 3 years (proof of consent) |
| Deletion request record (who, what, when — no farm data) | 3 years |
| Host technical logs | As set by Railway; *[confirm Railway log retention for our plan]* |
| Breach records | At least 24 months after we determine a breach occurred (S5) |

### 9. How we protect it
Server-only database access; private file storage; passwords hashed (argon2id); session tokens stored only as hashes; access limited to the CloverProof team members who need it; every plan record is write-once so it cannot be silently changed. No system is perfectly secure. If a breach creates a real risk of significant harm to you, we will tell you and report it to the Privacy Commissioner of Canada as required (S5), and to EU authorities where GDPR requires it (S11 Arts. 33–34).

### 10. Your rights
You can ask us to:
- tell you what we hold about you and give you a copy;
- correct it;
- delete it;
- stop using it for calibration or marketing (withdraw consent);
- *(EU/EEA)* restrict or object to processing, and receive your data in a portable format.

Email [CONTACT EMAIL] or write to [ADDRESS]. We may ask you to confirm your identity. We reply within 30 days (S1 s.8(3), to verify) and, for EU/EEA requests, within one month (S11 Art. 12(3)).

**Deletion and the plan record.** Approved plans and proof PDFs are stored write-once so nobody can alter them. When you ask for deletion we remove or irreversibly de-identify everything that links those records to you (names, contacts, farm and field names, location). If we must keep anything (for example, to defend a legal claim), we will tell you what and why. *(Engineering gap: the database currently blocks deletion of these records — see compliance-review.md G2.)*

### 11. Unsubscribing
Every marketing email has an unsubscribe link. We act on it within 10 business days at most (S6 s.11(3), S9) — in practice, straight away.

### 12. Complaints
Contact us first. You can also complain to:
- the **Office of the Privacy Commissioner of Canada**: https://www.priv.gc.ca;
- *(EU/EEA)* the data-protection authority where you live or work.

### 13. Children
CloverProof is for farm businesses and is not directed to anyone under 18. *(Age threshold to be confirmed by counsel.)*

### 14. Changes
We will post changes here with a new date and tell pilot farms by email before a material change takes effect.

Effective date: [EFFECTIVE DATE]. Version: 0.1-draft.

---

## Part B — Website privacy-page copy (hand to `cp-website`)

Shape matches `website/src/messages/en.json` → `privacy` (keys `title`, `draft`, `updated`, `sections[] {h, p}`). English only; other locales only after native review (ADR 0003). Replace placeholders before release; keep `draft` until counsel signs off.

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
      "h": "What we collect",
      "p": "When you request a pilot plan we collect what you enter: name, email, country, approximate farm size, main crop and any notes, plus the language you used and the exact consent wording you agreed to, with the time. If you join the pilot we also collect farm, field and soil-test information and the plans we make for you."
    },
    {
      "h": "Why we collect it",
      "p": "To decide whether we can include your farm in the pilot, to contact you about it and, if you join, to make and record your fertilizer plans. We send news emails only if you tick the separate box for them."
    },
    {
      "h": "Improving the engine",
      "p": "If you agree, we keep a de-identified copy of pilot results (engine proposal vs our agronomist's final numbers) to make the engine more accurate. Names, contact details, farm and field names and exact locations are removed. You can say no and still take part."
    },
    {
      "h": "Who sees it",
      "p": "Only the CloverProof team members who need it, and Railway, the company that hosts our website and database. We do not sell your information and we do not use advertising trackers or analytics."
    },
    {
      "h": "Where it is stored",
      "p": "Railway is a US company and our data may be stored and accessed in the United States, where US authorities may be able to access it under US law. We use a data-processing contract to protect it."
    },
    {
      "h": "How long we keep it",
      "p": "Pilot requests we can't accept: 12 months. Pilot records: the pilot season plus 2 years. De-identified engine data: until you withdraw consent or we retire the engine. You can ask us to delete your details at any time."
    },
    {
      "h": "Your rights",
      "p": "You can ask to see, correct or delete your information, and withdraw consent at any time, by emailing [CONTACT EMAIL]. We reply within 30 days. You can also complain to the Office of the Privacy Commissioner of Canada (priv.gc.ca) or, in the EU, to your local data-protection authority."
    }
  ]
}
```

Notes for `cp-website`:
- Retention figures above are *proposed*; do not ship until Farjad approves them.
- "We do not use advertising trackers or analytics" must be re-checked whenever a dependency or script is added.
- Link this page from the pilot form (already done: `pilot.privacyLink`).

---

## Sources (checked 2026-11-16)
Some Government of Canada and CRTC pages refused connections from this environment; those are marked *(not fetched — confirmed via search summaries only; verify before reliance)*.

- S1 PIPEDA, S.C. 2000, c. 5, incl. Schedule 1 and s. 8(3) — https://laws-lois.justice.gc.ca/eng/acts/P-8.6/ *(not fetched)*
- S2 OPC, PIPEDA fair information principles — https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/p_principle/ *(not fetched)*
- S3 OPC, Guidelines for obtaining meaningful consent (2018) — https://www.priv.gc.ca/en/privacy-topics/collecting-personal-information/consent/gl_omc_201805/ *(not fetched; search-confirmed)*
- S4 OPC, Guidelines for processing personal data across borders (2009; unchanged after 2019 consultation) — https://www.priv.gc.ca/en/privacy-topics/airports-and-borders/gl_dab_090127/ *(not fetched; search-confirmed)*
- S5 OPC, What you need to know about mandatory reporting of breaches — https://www.priv.gc.ca/en/privacy-topics/business-privacy/safeguards-and-breaches/privacy-breaches/respond-to-a-privacy-breach-at-your-business/gd_pb_201810/ ; Breach of Security Safeguards Regulations SOR/2018-64 — https://canadagazette.gc.ca/rp-pr/p2/2018/2018-04-18/html/sor-dors64-eng.html *(search-confirmed: 24-month record keeping)*
- S6 CASL, S.C. 2010, c. 23 — https://laws-lois.justice.gc.ca/eng/acts/E-1.6/ *(not fetched)*
- S9 CRTC CASL FAQ — https://crtc.gc.ca/eng/com500/faq500.htm *(not fetched; search-confirmed 10 business days)*
- S11 GDPR, Regulation (EU) 2016/679 — https://eur-lex.europa.eu/eli/reg/2016/679/oj *(fetched; Arts. 3, 4, 7, 13, 21, 27, 45 read)*
- S12 Commission Decision 2002/2/EC (Canada adequacy) — https://eur-lex.europa.eu/eli/dec/2002/2/oj *(fetched; Art. 1 read)*; 2024 review kept Canada's adequacy — secondary: https://www.hunton.com/privacy-and-cybersecurity-law-blog/european-commission-reviews-and-reaffirms-adequacy-decisions-for-11-jurisdictions
- S14 Railway deployment regions — https://docs.railway.com/reference/deployment-regions *(fetched)*
- S15 Railway Data Processing Addendum — https://railway.com/legal/dpa *(fetched: Railway = processor §2.1; primary processing in US §9.1; SCCs and DPF §9; breach notice "without undue delay" §8.1; subprocessors at https://trust.railway.com/item/subprocessors, 10 days' notice §6.2)*

## Needs licensed counsel
1. Whether PIPEDA applies to a free pilot (commercial activity) and whether farm/field data is personal information for incorporated vs sole-proprietor farms.
2. Whether calibration use can be a condition of the pilot or must stay optional (PIPEDA Principle 4.3.3; GDPR Art. 7(4)).
3. Whether our de-identification standard is enough to treat calibration data as non-personal.
4. EU transfer analysis (direct collection by a Canadian controller + US processor) and whether an Art. 27 EU representative is needed.
5. Retention periods and the "legal claims" exception to deletion of immutable plan records.
6. Minimum age wording.
