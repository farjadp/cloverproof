# CASL answers: 12 questions from the casl-note

> **Not legal advice; for lawyer review. Drafted by legal-compliance-specialist (not a lawyer) for the CloverProof COO, 2026-11-17.**
> This is not legal advice; a licensed Ontario lawyer should review before use.

Answers the 12 "Questions for legal" in `docs/growth/casl-note.md` (origin/main, 2026-11-17). Working positions only, for `cro` to act on until counsel answers.

**Sources and tags**
- [N] = section verified in the casl-note against the official text on 2026-11-17 ("from casl-note [V]"). I have not re-read it, except where marked [R].
- [R] = re-checked by me against the official text on 2026-11-17.
- [S] = search summary or secondary source only. Verify before relying on it.
- [M] = from memory. Not verified. Do not rely on it until checked.
- CASL, S.C. 2010, c. 23: https://laws-lois.justice.gc.ca/eng/acts/E-1.6/FullText.html
- IC Regs, Electronic Commerce Protection Regulations, SOR/2013-221: https://laws-lois.justice.gc.ca/eng/regulations/SOR-2013-221/FullText.html
- CRTC Regs, Electronic Commerce Protection Regulations (CRTC), SOR/2012-36: https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-36/FullText.html
- CRTC guidance pages (crtc.gc.ca) returned 403 to the casl-note author. Every CRTC-bulletin point here is [S] unless marked otherwise.

Entities. CloverProof's legal entity is still `[LEGAL ENTITY]` in every draft. Ashavid Inc. and VisaRoads Inc. are separate Ontario corporations with the same director. Nothing here treats them as CloverProof's sender unless Farjad decides that one of them operates CloverProof.

---

## Q1. Is an invitation to a free pilot, from a start-up that plans to charge later, a CEM?
- **Answer: yes (probably, at high confidence).**
- **Reasoning.** "Commercial activity" covers conduct of a commercial character "whether or not the person who carries it out does so in the expectation of profit" (CASL s.1(1)) [N]. A CEM includes a message whose purpose, or one of whose purposes, is to encourage participation in a commercial activity, including one that offers a business opportunity or promotes a service (s.1(2)) [N]. The pilot recruits users for a product that will be billed later, which fits. A message asking for consent is also a CEM (s.1(3)) [N].
- **Source:** CASL s.1(1)-(3), from casl-note [V], 2026-11-17.
- **Confidence:** high.
- **Rule for cro:** treat every pilot invitation, follow-up and consent request as a CEM. It needs consent (or an exemption) plus the full sender-ID and unsubscribe content.

## Q2. Does a pilot-form submission, or an email asking about the free pilot, count as an "inquiry or application" under s.10(10)(e) and give 6 months of implied consent?
- **Answer: probably yes, but unknown for a free pilot.**
- **Reasoning.** s.10(10)(e) [N] covers an inquiry or application "in respect of anything mentioned in any of paragraphs (a) to (c)": the purchase or lease of a product, good, service or land, or the acceptance of a business opportunity. A free pilot is not a purchase. It may be a "business opportunity" or, for a farm business, an inquiry about a service it may later buy, but CASL does not answer this. The point matters less than it looks:
  1. Our **direct reply** to a submission is a message "sent in response to a request, inquiry or complaint", which is outside s.6 entirely (IC Regs s.3(b)) [N].
  2. The person gave us the address themselves without saying "no CEMs", and pilot messages are relevant to their farm business. That is implied consent under s.10(9)(c) [N], with no 6-month clock in the statute.
  3. The form's Box A is express consent for pilot contact (see Q6), which has no expiry until withdrawn.
- **Source:** CASL s.10(9)(c), s.10(10)(e); IC Regs s.3(b), all from casl-note [V], 2026-11-17.
- **Confidence:** medium.
- **Rule for cro:** rely on the form's consent box for pilot contact, not on s.10(10)(e). For people who only emailed: reply, then keep pilot-only messages within 6 months of their last inquiry, and ask for express consent in that window if contact will run longer. Never send news, launch or paid offers on this basis.

## Q3. Does the s.6(5)(a) personal-relationship exemption hold when Farjad writes from a CloverProof address on behalf of the company?
- **Answer: unknown; probably not when the message is plainly sent for the company.**
- **Reasoning.** s.6(5)(a) [N] exempts a message sent "by or on behalf of an individual to another individual with whom they have a personal or family relationship" (definition in IC Regs s.2) [N]. The text names an individual as the sender. A message signed "Farjad Iranmehr, on behalf of [LEGAL ENTITY] (CloverProof)", which the content rules require us to write, states that it is sent for a corporation. The exemption is built around the relationship between two individuals, and CRTC/ISED guidance describes it that way [S]. I found no guidance that applies it to a corporation's message sent through its founder.
- **Source:** CASL s.6(5)(a); IC Regs s.2, from casl-note [V], 2026-11-17. Guidance points [S].
- **Confidence:** low.
- **Rule for cro:** do not rely on the personal-relationship exemption for any message from a CloverProof address or signed for CloverProof. For people Farjad knows personally, send a short personal, pitch-free note from his personal address asking whether they would like to hear about the pilot (a question to someone he knows). Once they reply yes, that reply is the express consent; record it. Every CloverProof message still carries sender ID and unsubscribe.

## Q4. Do Farjad's personal dealings, or those of Ashavid Inc. or VisaRoads Inc., create an existing business relationship for CloverProof's entity?
- **Answer: no (working position).**
- **Reasoning.** An existing business relationship is defined as one between the recipient and "the person who sends the message or the person who causes or permits it to be sent" (s.10(10)) [N]. If the CloverProof entity sends, a purchase, contract or inquiry that ran with Farjad personally, Ashavid Inc. or VisaRoads Inc. belongs to a different person. CASL lets a relationship transfer only when "the business is sold" (s.10(12)) [R], which shows the Act ties the relationship to a specific business, not to its owner or director. Common directorship does not merge the corporations.
  - Exception: if Farjad decides that Ashavid Inc. itself operates CloverProof, then Ashavid Inc.'s own customers from the past 2 years (purchase/contract) or 6 months (inquiry) might qualify, and only for messages relevant to that relationship. That depends on Q5.
- **Source:** CASL s.10(10) and s.10(12), re-checked against the official text, 2026-11-17 [R].
- **Confidence:** medium-high for "no" while the entity is unknown.
- **Rule for cro:** no contact list from Ashavid Inc., VisaRoads Inc. (including VisaRoads mentees or customers) or Farjad's personal dealings is a CloverProof consent list. Do not import them. Use them only for the personal pitch-free question described in Q3, or not at all.

## Q5. Which legal entity sends, and what mailing address may we publish? Is a virtual or registered-office address acceptable?
- **Answer: entity = unknown (Farjad decides); address = probably yes for a virtual or registered-office address that actually receives mail.**
- **Reasoning.** CRTC Regs s.2(1)(a)-(d) [N] require the name the sender carries on business under, the person on whose behalf the message is sent (if different), and a **mailing address** plus a phone number, email or web address. That information must stay valid for at least 60 days after sending (CASL s.6(3)) [N]. The regulation says "mailing address", not "physical" or "street" address. CRTC guidance is reported to accept a valid postal address, including a PO box or virtual office, where mail actually reaches the sender [S]. A Newmarket home address would work, but it publishes Farjad's home in every email; a PO box or registered-office address avoids that.
  - **Entity:** CloverProof is not an incorporated name, as far as the repo shows. The sender is either a new corporation, Ashavid Inc., or Farjad as sole proprietor. If CloverProof is used as a trade name by a corporation, Ontario requires that name to be registered under the Business Names Act [M]. This is Farjad's decision with his accountant and counsel. Do not use VisaRoads Inc.
- **Source:** CRTC Regs s.2, CASL s.6(3), from casl-note [V], 2026-11-17. PO-box acceptability: search summary only; the only source found is an email-vendor blog (https://webflow-blog.cakemail.com/post/mailing-address-in-emails); the CRTC FAQ returned 403. No official guidance found. Business Names Act [M].
- **Confidence:** address medium; entity unknown.
- **Rule for cro:** nothing is sent until `[LEGAL ENTITY]` and `[ADDRESS]` are filled in. Use one entity everywhere (emails, form consent, privacy notice, pilot terms). Use a mailing address that is checked at least weekly and stays active for at least 60 days after the last send.

## Q6. Is the casl-note §2(7) replacement wording enough as express consent? Must it be a separate box from "store these details"?
- **Answer: probably sufficient for pilot email once the placeholders are filled in. Separate box: yes for news/marketing; for pilot contact, one box is probably acceptable.**
- **Reasoning.** A request for express consent must set out clearly and simply the purpose (CASL s.10(1)(a)) [R], plus the name of the person seeking consent and on whose behalf, a statement of who is seeking for whom, the mailing address plus one of phone/email/web, and a statement that consent can be withdrawn (CRTC Regs s.4(a)-(e)) [R]. The §2(7) wording names the entity, address and email; states the purpose (email about the 2027 pilot); and states withdrawal ("reply stop or write to {email}"). That covers s.10(1)(a) and s.4(a)-(e). Correction to casl-note §2(7) and `consent-wording.md`: the "sought separately for each act" wording in CRTC Regs s.4 [R] means separately for each act in CASL ss.6-8 (sending CEMs, altering transmission data, installing programs). It does **not**, on its own words, require a separate box for news vs pilot contact. The separate-box rule rests on CRTC bulletin 2012-548 [S] and PIPEDA meaningful consent, not on s.4. Express consent must be an opt-in by positive action: no pre-ticked box (CRTC bulletin 2012-549) [S]. The current box is unticked and required [N]. CRTC guidance says consent to CEMs must be sought **separately** from consent to terms and conditions or other purposes (bulletin 2012-548) [S]. Storing the details is needed only to answer the request. Bundling "store" and "email me about my pilot request" is defensible because the email is the reason for storing. Bundling any **news/marketing** consent into that required box is not.
- **Source:** CASL s.10(1) and CRTC Regs s.4, re-checked 2026-11-17 [R]; CRTC bulletins 2012-548 and 2012-549 (crtc.gc.ca returned 403 again on 2026-11-17), search summary only.
- **Confidence:** medium.
- **Rule for cro:** use the wording in §"Recommended website-form consent change" below. Pilot contact goes only to people who ticked Box A. News goes only to people who ticked Box B. Never infer B from A.

## Q7. Do CCA or association directory listings count as conspicuous publication, and do no-solicitation terms defeat s.10(9)(b)?
- **Answer: probably not publication "by the person" unless the individual chose to be listed. Yes, a no-solicitation statement defeats s.10(9)(b).**
- **Reasoning.** s.10(9)(b) [N] requires that the address was conspicuously published by the person, or that the person caused it to be published; that the publication is not accompanied by a statement that the person does not want unsolicited CEMs; and that the message is relevant to the person's business, role, functions or duties. An opt-in professional directory may be "caused to be published" by the member. A mandatory register is weaker. A directory's terms that forbid using listings for solicitation are, on a plain reading, a statement accompanying the publication [S on how CRTC reads "accompanied by"].
- **Source:** CASL s.10(9)(b), from casl-note [V], 2026-11-17.
- **Confidence:** medium.
- **Rule for cro:** do not use directory addresses. Use the address the firm publishes on its own website, after checking that page, its footer and its terms for "no unsolicited messages" wording. Save a dated screenshot. If the only route is a directory, send no CEM; use a pitch-free question (s.6(5)(b)) or skip.

## Q8. Can an individual farm's own website address ever be used under s.10(9)(b), or should category (9) stay a hard no?
- **Answer: legally possible in narrow cases; keep it a hard no in practice.**
- **Reasoning.** A farm business that publishes its own contact address on its own website, with no "no CEM" statement, meets the first two tests of s.10(9)(b) [N]. A fertilizer-planning pilot is plausibly relevant to the business. The relevance test is applied to the person's "business, role, functions or duties"; a generic farm-gate sales inbox (meat, eggs, U-pick) is aimed at customers, so a fertilizer pitch to it is weaker on relevance [S]. Brand risk with a small farming community is high. The plan already forbids mass blasts. The PIPEDA address-harvesting provisions (PIPEDA s.7.1, inserted by CASL; confirmed present in the consolidated text 2026-11-17 [R]) apply if addresses are collected with a program; manual one-by-one collection is not harvesting, but the rule shows the intent.
- **Source:** CASL s.10(9)(b), from casl-note [V]; PIPEDA s.7.1 https://laws-lois.justice.gc.ca/eng/acts/P-8.6/FullText.html [R]; 2026-11-17.
- **Confidence:** medium on the law; high on the practical rule.
- **Rule for cro:** hard no on cold CEMs to individual farms, unless counsel signs off in writing for a named recipient with the record in casl-note §3. Reach farmers through associations, agronomists, referrals (IC Regs s.4) and the website form.

## Q9. LinkedIn/X DMs: is a profile-linked sender-info page enough for IC Regs s.3(d) or CRTC Regs s.2(2)? Does an accepted connection request create implied consent?
- **Answer: a linked page is probably enough for the content rules (CRTC Regs s.2(2)). An accepted connection alone: no, not implied consent.**
- **Reasoning.**
  - Content. CRTC Regs s.2(2) [N]: if it is not practicable to include the identification and unsubscribe in the message, they may be posted on a web page that is readily accessible at no cost by a link clearly and prominently set out in the message. A DM with a working link to a CloverProof sender-info and opt-out page meets that on its terms. The unsubscribe must still use the same electronic means where practicable (CASL s.11(1)) [N]: "Reply STOP" in the DM covers that.
  - IC Regs s.3(d) [N] is different: it removes s.6(2) content duties for messages sent through a messaging service when the ID and unsubscribe are conspicuously published in the platform's user interface **and** the recipient has consented expressly or impliedly. It never removes the consent requirement. Do not rely on it; include the link anyway.
  - Connection. Accepting a request is not a purchase, contract, inquiry or application (s.10(10)), and not express consent to CEMs (s.10(1), CRTC Regs s.4). A connection may expose a profile email that meets s.10(9)(b) if the member put it there for business contact and has no "no solicitation" statement [S].
- **Source:** CRTC Regs s.2(2), CASL s.10(9)-(10), s.11(1), IC Regs s.3(d), from casl-note [V], 2026-11-17. DMs as CEMs: ISED "Understanding CASL" (casl-note [V]); CRTC case-by-case view [S].
- **Confidence:** medium.
- **Rule for cro:** DM or text only people in casl-note categories (5)-(7), or people whose public profile shows a business contact and a role the pilot is relevant to. Every DM: one line of sender ID, the sender-info link, "Reply STOP and I won't message again". The sender-info page must exist first (brief to `cto`). Never treat "connected" as consent.

## Q10. How long to keep consent and opt-out records? May we keep a hashed suppression entry after a PIPEDA deletion request?
- **Answer: retention period: unknown (proposal below). Hashed suppression entry: probably yes.**
- **Reasoning.**
  - CASL sets no retention period. s.13 [N] puts the burden of proving consent on the person who claims it. No proceeding for a violation may begin later than three years after the day the subject matter became known to a person designated under s.14 (CASL s.23(1)) [R]. That clock starts when the CRTC learns of it, not when the message was sent, so 3 years is a floor, not a guarantee. Keeping proof for the life of the consent plus 3 years covers that window. That matches the 3-year proposal in `consent-wording.md` §4.
  - PIPEDA Sch. 1 clause 4.5.3 [R]: personal information no longer required to fulfil the identified purposes "should be destroyed, erased, or made anonymous". Honouring a "do not contact" request is an identified, necessary purpose. A one-way hash of the address (no name, no other data) kept only to block future sends is minimal and is necessary to comply with s.11. Deleting the address and then re-adding it from a new source would violate the opt-out. A hash of an email address is still personal information (it can be matched); disclose it in the privacy notice.
- **Source:** CASL s.13, from casl-note [V]; CASL s.23(1) and PIPEDA Sch. 1 4.5.3, re-checked 2026-11-17 [R].
- **Confidence:** medium-low.
- **Rule for cro:** keep each consent and opt-out record for as long as the consent is in use plus 3 years. On a deletion request, delete the CRM record and keep only a salted SHA-256 hash of the address in a suppression list, checked before every send. Add one sentence about it to the privacy notice (owner: legal, before the first follow-up).

## Q11. The privacy notice says the pilot is "open to farms in Ontario" while the plan runs a Manitoba backup track. Does the notice need to change before Prairie outreach?
- **Answer: yes. The docs must change before any Prairie (Manitoba) outreach, and the terms must change before any Manitoba enrolment.**
- **Reasoning.** CASL itself does not care about the province: it applies wherever a computer system in Canada sends or accesses the message (s.12(1)) [N]. The problem is the other documents:
  - Recruiting Manitoba farms with a notice that says "Ontario only" makes the notice inaccurate (PIPEDA openness, Sch. 1 4.8 / 4.8.1 [R]). It also creates a misleading general impression in the outreach (Competition Act s.74.011 for electronic messages) [S].
  - `pilot-terms.md` §1.5 limits eligibility to Ontario and allows another province only by written addendum.
  - OPC lists only Alberta, British Columbia and Quebec as having private-sector privacy laws deemed substantially similar to PIPEDA; Manitoba is not listed (https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/legislation-related-to-pipeda/provincial-legislation-deemed-substantially-similar-to-pipeda/, fetched 2026-11-17) [R]. So PIPEDA probably applies to Manitoba farm data as it does to Ontario data. Privacy law is not the main barrier; the agronomy side is. `pilot-terms.md` already flags right-to-practice rules for agrologists in Prairie provinces and forbids superadmin-only approval there.
- **What must change (owner: legal-compliance-specialist drafts, Farjad approves):**
  1. `privacy-notice.md` lines 49 and 227 (and en.json `privacy` body, live text): change to "The 2027 pilot is open to farms in Ontario, Canada, and, where we say so in writing, Manitoba." Or keep Ontario-only and stop all Manitoba outreach. Do not do both.
  2. `pilot-terms.md` §1.5: a Manitoba addendum (eligibility, Manitoba law references, agronomist licensing in Manitoba, no `superadmin_approved` plans).
  3. `consent-wording.md` §1 intro and §2 bullet "the fields I enrol are in Ontario, Canada": add the Manitoba variant.
  4. en.json `pilot` intro ("we can only include Ontario farms"): same change as the notice, or Manitoba farmers will be turned away by the form we point them to.
  5. Outreach drafts for the Prairie track: say plainly that Manitoba places are a limited backup track, so nobody is promised a place.
  6. Record a new `notice_version` in the consent record on the day the wording changes.
- **Source:** CASL s.12(1), from casl-note [V]; `privacy-notice.md`, `pilot-terms.md` (repo, read 2026-11-17); OPC substantially-similar list [R]; PIPEDA Sch. 1 4.8 [R]; Competition Act [S].
- **Confidence:** high that the docs must change; medium that PIPEDA (not a Manitoba act) governs Manitoba farm data; Manitoba agrology licensing not assessed.
- **Rule for cro:** no Manitoba outreach until items 1, 4 and 5 are live and Farjad has approved the Manitoba addendum in principle.

## Q12. PIPEDA consent and retention for farm data at intake
- **Answer: out of scope for CASL; covered elsewhere.**
- **Reasoning.** CASL governs messages, not the farm data. Intake data consent is drafted in `consent-wording.md` §2-§3 (pilot data use, optional de-identified calibration, case study) and the privacy notice. Retention and erasure are in `erasure-requirements.md`. Those drafts already list their counsel questions.
- **Source:** repo files, read 2026-11-17.
- **Confidence:** n/a.
- **Rule for cro:** collect no farm data (soil tests, yields, field locations) by email or DM before the farm signs the pilot terms and the §2 data-use consent. Before that, only name, farm name, contact and province.

---

## Summary table

| # | Question | Working answer | Confidence | Rule for cro until counsel answers |
|---|---|---|---|---|
| 1 | Free-pilot invite a CEM? | Yes | High | Treat as CEM: consent + ID + unsubscribe |
| 2 | Pilot inquiry = s.10(10)(e) inquiry? | Probably; unknown for "free" | Medium | Rely on Box A and IC Regs s.3(b) replies; pilot-only, 6-month cap for email-only inquirers |
| 3 | Personal exemption from a company address? | Probably not | Low | Don't rely on it; ask a personal, pitch-free question first |
| 4 | Ashavid/VisaRoads/personal dealings = CloverProof relationship? | No | Medium-high | Never import those lists |
| 5 | Sender entity and mailing address | Entity unknown; PO box/virtual probably OK | Medium / unknown | Nothing sent until entity and address are fixed |
| 6 | §2(7) wording enough? Separate box? | Probably; separate box for news | Medium | Box A pilot-only, Box B news, both unticked |
| 7 | Directory listings | Probably not; no-solicitation terms defeat it | Medium | Firm's own site only, screenshot, else skip |
| 8 | Farm's own website address | Legally narrow; practically no | Medium / high | Hard no without written counsel sign-off |
| 9 | DMs: linked page; accepted connection | Link OK for content; connection ≠ consent | Medium | Link + "Reply STOP" in every DM; categories (5)-(7) only |
| 10 | Record retention; hashed suppression | Life of consent + 3 years (proposal); hash probably OK | Medium-low | Keep records; salted hash suppression list; disclose it |
| 11 | Manitoba vs Ontario-only notice | Yes, docs must change | High (docs) / low (privacy law) | No Manitoba outreach until notice, form and drafts change |
| 12 | PIPEDA intake data | Out of CASL scope | n/a | No farm data before signed terms + §2 consent |

## Recommended website-form consent change

Live today (en.json `pilot.consent`): one required unticked box: "I agree that CloverProof may store these details and contact me about the pilot. I can ask for them to be deleted at any time." Live privacy text says "We don't send news emails."

Reconciled with `consent-wording.md` §1 (Box A/B) and casl-note §2(7). Box A gets the CRTC Regs s.4 elements that `consent-wording.md` Box A still lacks (mailing address; a withdrawal statement, not only deletion). Box B stays as drafted, with one wording change.

**Box A (required, unticked):**
> ☐ I agree that [LEGAL ENTITY] (CloverProof), [ADDRESS], [CONTACT EMAIL], may store these details and email me about my 2027 pilot request. I can withdraw this consent at any time by replying "stop" or writing to [CONTACT EMAIL], and ask for my details to be deleted.

**Box B (optional, unticked, separate):**
> ☐ Yes, send me CloverProof news and updates by email. Sent by [LEGAL ENTITY] (CloverProof), [ADDRESS], [CONTACT EMAIL]. I can withdraw this consent and unsubscribe at any time using the link in every email or by writing to [CONTACT EMAIL].

Changes from `consent-wording.md` v0.4:
1. Box A: add `[ADDRESS]` and `[CONTACT EMAIL]` up front (CRTC Regs s.4(a), (d)) [R]; add "withdraw this consent" (s.4(e)) [R]; state the purpose (CASL s.10(1)(a)) [R]; narrow "contact me" to "email me about my 2027 pilot request". If phone/SMS contact is planned, add "or text" now, or ask for SMS consent separately later.
2. Box B: "You can unsubscribe" → "I can withdraw this consent and unsubscribe" (s.4(e) uses "withdraw") [R]. Keep B separate on the strength of CRTC bulletin 2012-548 [S] and PIPEDA Sch. 1 4.3.3 (no required consent beyond the specified purpose) [R], not CRTC Regs s.4's "separately for each act", which refers to CASL ss.6-8.
3. When Box B goes live, change the live privacy text "We don't send news emails" to the draft's line "We send news emails only if you tick the separate box for them" (`privacy-notice.md` line 235) on the same day.
4. Store A and B as separate `consent_event` rows with the exact text and `notice_version` (`consent-wording.md` §4). Add `unsubscribed` handling and the suppression list before the first follow-up.
5. Owner: `cp-website` via `cro`/`cto`. Not changed in this task. `consent-wording.md` itself should be bumped to v0.5 with these two edits (legal, next pass).

## Questions that truly need a lawyer
1. Q2: does an inquiry about a **free** pilot fall within s.10(10)(e) ("business opportunity" or a future purchase)?
2. Q3: can the s.6(5)(a) personal-relationship exemption apply to a message sent by Farjad expressly on behalf of a corporation?
3. Q5: which entity operates CloverProof, whether a Business Names Act registration is needed, and whether a PO box / virtual office meets CRTC Regs s.2(1)(d).
4. Q6: whether one box for "store + pilot email" is acceptable given CRTC's "seek separately" guidance.
5. Q7: whether directory terms against solicitation are a "statement" accompanying publication under s.10(9)(b).
6. Q10: retention period for consent records, and whether a hashed suppression entry survives a PIPEDA deletion request.
7. Q11: Manitoba addendum: applicable privacy law, agrology licensing (right to practice) and liability, before any Manitoba enrolment.
8. Competition Act s.74.011 exposure for the site line "Approved by a human agronomist before it reaches you" (casl-note §4), which contradicts superadmin approval.

## Verification log (2026-11-17)
| Point | Result | Source |
|---|---|---|
| CASL s.10(10) definition (EBR with "the person who sent or caused or permitted"; 2-year / 6-month windows; (e) inquiry "in respect of anything mentioned in (a) to (c)") | Confirmed | CASL consolidated text, fetched 2026-11-17 |
| CASL s.10(12) EBR transfers on sale of the business | Confirmed (was [M]) | same |
| CASL limitation period | It is **s.23(1)**, not s.21; 3 years from when the subject matter became known to a s.14 designated person | same |
| CASL s.10(1)(a) purpose must be stated in a consent request | Confirmed | same |
| CRTC Regs s.4 content of consent request (a)-(e); "sought separately for each act described in sections 6 to 8" | Confirmed; "separately" is per act in ss.6-8, not per purpose. casl-note §2(7) and `consent-wording.md` cite it too broadly | SOR/2012-36 consolidated text, fetched 2026-11-17 |
| PIPEDA Sch. 1 4.5.3 destroy/erase/anonymize | Confirmed | PIPEDA consolidated text, fetched 2026-11-17 |
| PIPEDA s.7.1 address harvesting | Present in text (definitions read; operative subsections not read in full) | same |
| Substantially similar provincial private-sector laws | Alberta, BC, Quebec only; Manitoba not listed | OPC page (URL in Q11), fetched 2026-11-17 |
| PO box / virtual office as CEM mailing address | Not verified; only a vendor blog says yes | search summary only |
| CRTC FAQ and bulletin 2012-548 | 403 again on 2026-11-17; not read | — |
| PIPEDA Sch. 1 4.8 openness; 4.3.3 | Both confirmed | PIPEDA consolidated text |
| Competition Act s.74.011 | Not checked | casl-note [S] |
