# CloverProof consent wording — DRAFT

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> Drafted by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO. v0.1 2026-11-16; v0.2 2026-11-16 (CPO decisions D4 + R4); v0.3 2026-11-16 (Farjad Iranmehr decisions: OQ-06 Canada, superadmin approval); v0.4 2026-11-16 (Farjad Iranmehr decision: website form data in the US on Railway until Canadian hosting is live).

**v0.2 changes:** D4 — consent text now says an AI system may check plans and a named human agronomist approves every plan; nothing says or implies the founder is the agronomist. R4 — pilot is for Ontario farms; the form intro says so.

**v0.3 changes:** OQ-06 DECIDED (Farjad Iranmehr, 2026-11-16): real farmer data is stored in Canada; the US/Railway option for pilot data is removed (§2). The website form's data location is **not** decided by OQ-06 — `[WEBSITE FORM DATA LOCATION — confirm in hosting ADR]` (§1). Superadmin approval: the §2 bullet now says who may approve and that a farmer is told when no agronomist reviewed the plan.

**v0.4 changes:** Decision by Farjad Iranmehr (2026-11-16): the website pilot-request form stays open; the free-text notes field is removed from the form (no consent text here listed it, so no wording change for that); until Canadian hosting is live, form data is stored in the United States by our website host, Railway, and moves to Canada when Canadian hosting is live. `[WEBSITE FORM DATA LOCATION — confirm in hosting ADR]` replaced in §1. "AI check notes" in §2 is unrelated and kept.

Placeholders: `[LEGAL ENTITY]`, `[ADDRESS]`, `[CONTACT EMAIL]`, `[PRIVACY URL]`, `[HUMAN AGRONOMIST NAME, CREDENTIALS]`, `[SUPERADMIN NAME, ROLE]`, `[CANADIAN HOSTING PROVIDER, REGION]`, `[AI PROVIDER]`.
English only. Other locales need native-speaker review (ADR 0003) and a counsel check that the translation keeps the legal meaning.

## Rules that shape the wording
| Rule | Source |
|---|---|
| Express consent cannot be obtained with a pre-checked box or by silence; the person must take a positive action | CRTC 2012-549 (S8); CRTC 2012-548 (S7) |
| A consent request must state the purpose, identify who is seeking consent, give contact information (mailing address + one of phone, email or web address) and state that consent can be withdrawn | Electronic Commerce Protection Regulations (CRTC), SOR/2012-36, s. 4 (S6a); CRTC 2012-548 (S7) |
| Consent to commercial electronic messages must be sought separately from consent to terms of use / other purposes | CRTC 2012-548 (S7) |
| You cannot ask for CASL consent by email — that request is itself a commercial electronic message | CRTC 2012-548 (S7) |
| Unsubscribe requests must take effect within 10 business days | CASL s. 11(3) (S6); CRTC FAQ (S9) |
| Meaningful consent: key elements up front (what, why, who it is shared with, risks); individual can choose for non-essential purposes | OPC meaningful consent guidelines (S3); PIPEDA Sch. 1, 4.3 (S1) |
| Cannot require consent beyond what is needed for the explicitly specified, legitimate purpose | PIPEDA Sch. 1, 4.3.3 (S1) |
| GDPR consent must be distinguishable from other matters, plain language, withdrawable as easily as given, demonstrable | GDPR Art. 7(1)–(3) (S11) |
| Performance of a contract should not be conditional on consent to processing not necessary for it | GDPR Art. 7(4) (S11) |
| Tell people how AI is used with their information and its role in decisions | FPT regulators' generative-AI principles, 2023 (S23, search only); GDPR Art. 13(2)(f) for EU website visitors (S11) |

S-numbers refer to the source list at the end.

---

## 1. Website pilot request form

### Current wording (en.json `pilot.consent`)
> "I agree that CloverProof may store these details and contact me about the pilot. I can ask for them to be deleted at any time."

Assessment: acceptable core; missing (a) who "CloverProof" is legally, (b) link to the privacy notice next to the box, (c) where the data is stored, (d) any marketing option. Keep it as a single required box, and add a second, optional box for news.

### Proposed form block

Intro line (above the boxes, plain text):
> The 2027 pilot is for farms in Ontario, Canada. We use these details only to review your pilot request and contact you about it. Until our Canadian hosting is live, they are stored in the United States by our website host, Railway, where US authorities may be able to access them under US law; when it is live, they move to Canada. [Privacy notice]([PRIVACY URL])

**Box A — required, unticked by default**
> ☐ I agree that [LEGAL ENTITY] (CloverProof) may store these details and contact me by email about my pilot request. I can ask for them to be deleted at any time by writing to [CONTACT EMAIL].

**Box B — optional, unticked by default, separate from A**
> ☐ Yes, send me CloverProof news and updates by email. Sent by [LEGAL ENTITY] (CloverProof), [ADDRESS], [CONTACT EMAIL]. You can unsubscribe at any time using the link in every email or by writing to [CONTACT EMAIL].

Implementation notes for `cp-website` (do not edit `website/` from this task):
- Neither box may be pre-ticked. Submitting without A → `invalid`. Submitting without B → valid; marketing consent = false.
- Do not hide B inside A or inside the privacy link.
- Do not send news to anyone without B, including pilot applicants. Replies about their pilot request are covered by box A and are not marketing; keep them free of promotional content. *(Counsel to confirm whether replies to a pilot inquiry rely on the CASL inquiry-based implied consent, 6 months, CASL s. 10(10) — S6, S9a.)*
- Store the exact text of A and B shown, in the language shown (see §4).
- Location flag: a pilot request holds a farmer's name and contact details and is stored in the US (Railway) until Canadian hosting is live, while pilot farm data is in Canada. The intro says so plainly; the website must not claim "your data stays in Canada" anywhere until the form data has moved (Competition Act general impression; counsel item 7). Update the intro and the stored `consent_text` version on the day the data moves.
- Notes field removed (Farjad Iranmehr, 2026-11-16): `cp-website` removes `pilot.notes` from the form and `actions.ts`; not done here.

## 2. Pilot data-use consent (at enrolment, attached to pilot-terms.md)

**Required for the pilot (one box, unticked):**
> ☐ I agree that [LEGAL ENTITY] (CloverProof) may collect and use the information I provide about me, my farm, my fields, my soil tests and what I apply, to prepare, review and record fertilizer plans for me during the pilot, as explained in the privacy notice. I understand that:
> - the fields I enrol are in Ontario, Canada;
> - the information is stored in Canada by [CANADIAN HOSTING PROVIDER, REGION] [IF NOT CANADIAN-OWNED: "; the provider is a [COUNTRY] company and may be required by that country's law to give access to it"];
> - an AI system may check a de-identified copy of a proposed plan, which never includes my name, contact details, address, farm or field names or exact field location (D-7, CPO 2026-11-16; any change needs a DPA with the AI provider and an updated privacy notice);
> - no plan is sent to me until a named person at CloverProof has approved it: either the human agronomist, [HUMAN AGRONOMIST NAME, CREDENTIALS], or [SUPERADMIN NAME, ROLE], who is not an agronomist. Each plan says who approved it and, if it was not reviewed by an agronomist, says so on the first page. I can ask to receive only agronomist-reviewed plans. An AI check is never an approval;
> - CloverProof records the software's proposal, any AI check notes, the approver's final number and the reason for any change, to check how accurate the software is;
> - approved plans are kept as write-once records; if I ask for deletion, everything linking them to me is removed;
> - I can withdraw at any time by writing to [CONTACT EMAIL]; CloverProof will then stop making plans for me.

## 3. Optional consents (each a separate, unticked box)

**C — De-identified data to improve the engine after the pilot**
> ☐ Optional. After the pilot, CloverProof may keep a de-identified copy of my plan data (crop, yields, soil-test values, the software's proposal and the human agronomist's final numbers) to improve the software. My name, contact details, farm and field names and exact locations will be removed, and locations generalised to region. I can say no and still take part. I can withdraw this later by writing to [CONTACT EMAIL]; data that can still be linked to me will then be removed.

**D — Case study / quote (only if we ever want one)**
> ☐ Optional. CloverProof may name my farm and quote me in a case study, after showing me the text and getting my written approval of it.

**E — News emails** — same text as Box B (§1) if not already given on the website.

Do not bundle C, D or E with the pilot terms signature. A farm that declines C, D and E still gets the full pilot.

## 4. Consent record — what to store

For each consent event (grant or withdrawal), one row, never overwritten:

| Field | Why |
|---|---|
| `person_id` / email | Whose consent |
| `consent_type` (`pilot_request`, `pilot_data_use`, `calibration_after_pilot`, `case_study`, `marketing_email`) | Separate purposes, separate proof |
| `granted` (true/false) | Grant or withdrawal |
| `consent_text` (exact wording shown) | Prove what the person agreed to (GDPR Art. 7(1); CASL burden of proof s. 13) |
| `locale` | Which translation |
| `notice_version` (privacy notice + pilot terms versions) | What notice was in force |
| `collected_via` (`website_form`, `signed_pdf`, `email`, `phone`) + form/page URL | How consent was obtained |
| `occurred_at` (UTC timestamp) | When |
| `recorded_by` (system or staff user id) | Who recorded it (for oral/written consents) |
| `evidence_ref` (signed PDF key, email message id) | Pointer to the original for non-web consents |
| For withdrawals: `requested_at`, `actioned_at` | Prove unsubscribe ≤ 10 business days |

Do **not** store IP address unless the CISO decides it is needed for proof; if stored, list it in the privacy notice.

Current state: `pilot_request` stores `consent_text` + `consent_at` + `locale` only (one consent). Gaps: no marketing consent, no notice version, no withdrawal history. Hand to `cp-database` / `cp-website` as a schema change (new append-only `consent_event` table) — not done here.

Retention of consent records: proposed 3 years after the consent ends (to prove consent if challenged). *(Counsel to confirm — CASL has a 3-year limitation for private actions/proceedings, unverified.)*

## 5. Withdrawal and unsubscribe wording

Email footer (every marketing email):
> You are receiving this because you agreed to CloverProof news. Sent by [LEGAL ENTITY] (CloverProof), [ADDRESS], [CONTACT EMAIL]. [Unsubscribe] — one click, no login.

Unsubscribe link must work for at least 60 days after sending (CASL s. 11(2)/(3); S6, S9) and must not require a login.

Confirmation after withdrawal:
> Done. We have stopped [news emails / using your data to improve the engine] as of [date]. If you did not ask for this, reply to this email.

---

## Sources (checked 2026-11-16)
Government of Canada / CRTC sites refused direct connections from this environment; items marked *search* were confirmed only through search summaries — verify on the official page before relying on them.
- S1 PIPEDA, Schedule 1 — https://laws-lois.justice.gc.ca/eng/acts/P-8.6/ *(not fetched)*
- S3 OPC, Guidelines for obtaining meaningful consent — https://www.priv.gc.ca/en/privacy-topics/collecting-personal-information/consent/gl_omc_201805/ *(search)*
- S6 CASL, S.C. 2010, c. 23 (ss. 6, 10, 11, 13) — https://laws-lois.justice.gc.ca/eng/acts/E-1.6/ *(not fetched; section numbers from memory — verify)*
- S6a Electronic Commerce Protection Regulations (CRTC), SOR/2012-36 — https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-36/ *(not fetched)*
- S7 CRTC Compliance and Enforcement Information Bulletin 2012-548 — https://crtc.gc.ca/eng/archive/2012/2012-548.htm *(search: purpose; identification; request for consent by email is itself a CEM)*
- S8 CRTC Compliance and Enforcement Information Bulletin 2012-549 (toggling) — https://crtc.gc.ca/eng/archive/2012/2012-549.htm *(search: pre-checked box / silence not valid)*
- S9 CRTC CASL FAQ — https://crtc.gc.ca/eng/com500/faq500.htm ; S9a CRTC implied-consent guidance — https://crtc.gc.ca/eng/com500/guide.htm *(search: 10 business days)*
- S10 ISED Canada's anti-spam legislation — https://ised-isde.canada.ca/site/canada-anti-spam-legislation/en *(search: mailing address + phone/email/web; 60 days)*
- S11 GDPR Arts. 7, 13 — https://eur-lex.europa.eu/eli/reg/2016/679/oj *(fetched)*
- S23 FPT privacy regulators, *Principles for responsible, trustworthy and privacy-protective generative AI technologies* (7 Dec 2023) — https://www.priv.gc.ca/en/privacy-topics/ai-technology-and-innovation/artificial-intelligence/leadership-ai/ ; https://oipc.bc.ca/documents/guidance-documents/2811 *(search only — verify)*
- Decisions D4, R4 — `origin/backend-traceability:docs/plans/backend-plan-reconciliation.md` (CPO, 2026-11-16)
- Decisions OQ-06 (Canada) + superadmin approval — `git diff origin/main origin/cpo-decisions-sa-fe-residency -- CLAUDE.md` (Farjad Iranmehr, 2026-11-16)

## Needs licensed counsel
1. Whether replies to a pilot request need any CASL consent beyond Box A (inquiry-based implied consent vs. exclusion).
2. Whether "news" Box B must name categories (product updates vs. events vs. partners).
3. Whether the pilot data-use consent (§2) is correctly scoped as necessary for the service, and C as optional.
4. Consent-record retention period.
5. Legal equivalence of translated consent text in each locale.
6. Whether the AI-review bullets in §2 are enough disclosure, and whether sending pilot data to an AI provider needs its own consent or only notice (service-provider transfer).
7. Residency wording: the US-owned-host qualifier for pilot data, and whether the §1 intro wording on US storage of form data (Railway, until Canadian hosting is live) is adequate.
8. §2 approval bullet: whether disclosing `superadmin_approved` at consent plus on the PDF is enough, or whether a farm must opt in to receiving non-agronomist-approved plans.
