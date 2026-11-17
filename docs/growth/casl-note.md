# CASL note: 2027 wheat pilot outreach

Status: DRAFT, 2026-11-17. Owner: cro (email). NOT LEGAL ADVICE: written by a non-lawyer for `legal-compliance-specialist` (CPO → coo). Answers open questions a-d in `pilot-recruitment-plan.md` §6 as working positions and replaces that section's unverified points. Question e (PIPEDA, farm data) is out of scope and listed for legal.
Skills used: none invoked (statute and regulation reading; no copy written here beyond replacement lines).

**Evidence tags.** [V] = verified against an official text fetched 2026-11-17. [S] = from a secondary summary, verify.
- [V] Act, S.C. 2010, c. 23 (CASL), consolidated text: https://laws-lois.justice.gc.ca/eng/acts/E-1.6/FullText.html
- [V] Electronic Commerce Protection Regulations, SOR/2013-221 ("IC Regs"), current to 2026-10-29: https://laws-lois.justice.gc.ca/eng/regulations/SOR-2013-221/FullText.html
- [V] Electronic Commerce Protection Regulations (CRTC), SOR/2012-36 ("CRTC Regs"): https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-36/FullText.html
- [V] ISED CASL site (fightspam.gc.ca now returns 404; its content lives here): https://ised-isde.canada.ca/site/canada-anti-spam-legislation/en , pages "Getting consent to send email" and "Understanding CASL".
- BLOCKED: crtc.gc.ca returned 403 (guide.htm, faq500.htm, bulletins 2012-183, 2012-548, 2014-326); web.archive.org returned 429. Every CRTC-guidance point below is therefore [S].

## 1. Ground rules that apply to every category
- **Is a free-pilot invitation a CEM? (question a). Treat it as one.** "Commercial activity" covers conduct of a commercial character "whether or not the person who carries it out does so in the expectation of profit" (s.1(1)) [V]. A CEM includes a message that offers a business opportunity, advertises or promotes a service, or promotes a person as someone who does so (s.1(2)(a)-(d)) [V]. A start-up recruiting users for a product that will later be billed (backend plan: billing S26) fits. A message asking for consent is itself a CEM (s.1(3)) [V].
- **Prohibition:** no CEM to an electronic address without express or implied consent, and every CEM must meet the content rules (s.6(1)) [V]. This applies when a computer system in Canada is used to send or access the message (s.12(1)) [V], so it covers every message Farjad sends, including the Prairie track.
- **Content of every CEM** (s.6(2); CRTC Regs s.2-3) [V]:
  1. The name the sender carries on business under, and the name of the person the message is sent on behalf of, with a statement of who is sending for whom (CRTC Regs s.2(1)(a)-(c)). For us: "Sent by Farjad Iranmehr on behalf of {legal entity}, operating as CloverProof". The entity is still `[confirm]` in `outreach-drafts.md`.
  2. A mailing address, plus a phone number, email address or web address (s.2(1)(d)), valid for at least 60 days after sending (Act s.6(3)).
  3. An unsubscribe mechanism using the same electronic means, at no cost, that names an email address or web page to send it to (s.11(1)), valid for 60 days (s.11(2)). It must be clear and prominent and easy to use (CRTC Regs s.3).
  4. If the information cannot practicably fit (SMS, DM), a clear and prominent link to a web page that carries it (CRTC Regs s.2(2)).
- **Unsubscribe deadline:** effect "without delay, and in any event no later than 10 business days", "without any further action" by the person (s.11(3)) [V]. Our rule: action the same day, log it.
- **Mechanism scope:** s.11(1)(a) lets the person stop *any* CEMs from the sender, or a specified class [V]. The current `{OPTOUT}` ("rather not hear from me about this") reads as a narrow opt-out. Proposed replacement:
  `Reply "stop" to this email, or write to {reply_email}, and CloverProof will not send you any further messages.`
- **Burden of proof:** whoever claims consent has to prove it (s.13) [V]. No record means no consent.
- **Implied-consent bases** (s.10(9)) [V]: (a) an existing business or non-business relationship; (b) conspicuous publication; (c) the person gave us the address themselves, with no "no CEM" statement and a message relevant to their business role; (d) circumstances set by regulation. Business relationship (s.10(10)) [V]: a purchase, lease, barter, accepted business opportunity or written contract within 2 years, or an inquiry or application within 6 months, measured on the day the message is sent.
- **Wholly outside s.6** [V]: personal or family relationship (s.6(5)(a) + IC Regs s.2); a message to someone engaged in a commercial activity that "consists solely of an inquiry or application related to that activity" (s.6(5)(b)); a message sent in response to a request, inquiry or complaint, or otherwise solicited (IC Regs s.3(b)); interactive two-way voice calls (s.6(8)(a)). Phone calls fall under the CRTC telemarketing rules and the National DNCL instead [S].
- **Business-to-business exemption** (IC Regs s.3(a)(ii)) [V] needs an *existing* relationship between the two organisations. It does not cover cold outreach.

## 2. By recipient category
**(1) Organisations' published business addresses: commodity groups, OFA county federations, OSCIA, labs, extension inboxes**
- May send without express consent under s.10(9)(b) [V], if all three conditions hold: the organisation published the address itself or caused it to be published; the publication carries no statement that it does not want unsolicited CEMs (check the contact page, footer and terms); and the message is relevant to the recipient's "business, role, functions or duties". Relevance is strong for a member-communications, newsletter-editor or extension-crop inbox. It is weaker for a lab's billing or sample-intake address, so pick the outreach or general inbox.
- A named staff member's address on the organisation's page counts as published by them only if they caused it to be published [S]. Prefer the role inbox.
- An address handed over at an event (a card at SWAC) is implied consent under s.10(9)(c) [V], subject to the same "no statement" and relevance tests.
- Message must carry the full §1 content. A pure question with no pitch ("Do you run a member newsletter, and who edits it?") is exempt under s.6(5)(b) [V] and is the safest first touch.
- Needs express consent first: anything beyond the role. Examples: adding the person to a recurring CloverProof update, or messaging a personal address.

**(2) Independent agronomy / CCA firms' published addresses**
- Same basis as (1): s.10(9)(b) [V]. Relevance is strongest here, since they advise on fertilizer for clients.
- A professional or CCA directory is published by the association, not by the person. It counts only if the person chose to be listed, and it fails if the directory's terms forbid solicitation, because that is a "statement" under s.10(9)(b) [S, ask legal]. Default: use the firm's own website address, not the directory.
- Drafts #3a/#3b/#8 work on this basis once the §1 content and the new opt-out are in. Cap: one first touch and one follow-up, then stop unless they reply.

**(3) Co-ops / retailers**
- CASL treats them like (1)/(2): s.10(9)(b) [V]. Co-operatives count as businesses for business-relationship purposes (s.10(11)) [V].
- CASL is not the constraint here. The plan's conflict rule is: a supply co-op that sells fertilizer is a conflict, so use draft #5 for grower-governed associations only.

**(4) Contact-form submissions**
- There is no general contact form on the site today; the pilot form is the only one (see (7)). If one is added:
- A reply to the submission is excluded from s.6 (IC Regs s.3(b)) [V]. Include sender ID and the opt-out anyway; it costs nothing.
- Later messages: implied consent under s.10(10)(e) for 6 months after the inquiry [V]. That covers only an inquiry about buying or leasing a product or service, or a business opportunity, so whether a *free* pilot counts is a question for legal. If the person was not asking about the pilot, implied consent rests on s.10(9)(c) (they gave us the address, and the message must be relevant to their role).
- Express consent needed for anything after 6 months, or unrelated to what they asked.

**(5) Farjad's personal, family and business relationships (question b)**
- Personal or family (s.6(5)(a); IC Regs s.2) [V]: exempt from s.6 only if all three hold. The message is sent by or on behalf of an individual to an individual. The two have had direct, voluntary, two-way communication. And it is reasonable to conclude a personal relationship exists; factors include shared interests, how often they communicate, how long since they last did, and whether they have met. "Family" is marriage, common-law partnership or a legal parent-child relationship, plus two-way communication. Not covered: a LinkedIn connection or a one-off exchange [S]. Open: does a message sent from a CloverProof address "on behalf of" the company still count as from an individual? Ask legal.
- Existing business relationship (s.10(9)(a), s.10(10)) [V]: it has to exist between the recipient and the person sending, causing or permitting the message. A purchase or contract between a farmer and Farjad personally, or Ashavid Inc. or VisaRoads Inc., is not obviously a relationship with CloverProof's entity. Windows: 2 years after a purchase, barter or contract (or after a contract expires); 6 months after an inquiry.
- Non-business relationship (s.10(13)) [V]: covers only charities, political parties and candidates, and non-profit clubs or associations (IC Regs s.7). It rarely applies to us.
- Record per contact: how they know Farjad, date of the last two-way exchange, channel. Include the §1 content in every message even when exempt.

**(6) Third-party referrals (IC Regs s.4)** [V]
- Exempt from consent (s.6(1)(a)) for the **first** message only, and only when the referrer is an individual with a business, non-business, family or personal relationship with **both** Farjad (or CloverProof) and the recipient. The message must give the referrer's **full name** and state that it is sent because of the referral. The §1 content is still required (only the consent test is lifted).
- After that, keep messaging only if the recipient replies (s.10(9)(c) or IC Regs s.3(b)) or gives express consent.
- Better route for draft #2: the agronomist introduces both sides in one email and the farmer replies. Our reply is then a solicited response (IC Regs s.3(b)).
- Template line: `{referrer_full_name} suggested I contact you about the 2027 wheat pilot; I'm writing because of that referral.`

**(7) Website pilot-form submitters**
- Consent text (`website/src/messages/en.json` `pilot.consent`): "I agree that CloverProof may store these details and contact me about the pilot. I can ask for them to be deleted at any time." The checkbox is unticked and required (`PilotForm.tsx:134`). `pilot_request` stores `consent_at`, `consent_text` and `locale` (`db/migrations/0001_pilot_request.sql`). Good.
- Does it cover follow-up? **Yes for pilot follow-up (drafts #7 onward)**, on any reading: a reply to the request is solicited (IC Regs s.3(b)) and the inquiry gives 6 months of implied consent (s.10(10)(e), the free-pilot question above). **As express consent under s.10(1) and CRTC Regs s.4 it is probably incomplete** [V]. Three reasons. It gives no mailing address and no phone, email or web contact (s.4(d)); the site footer has none either. It has no statement that consent can be *withdrawn* (s.4(e)); "ask for them to be deleted" is a deletion right, not withdrawal. "CloverProof" may not be the full business name (s.4(a)).
- Proposed wording for legal: `I agree that {legal entity} (CloverProof), {mailing address}, {email}, may store these details and email me about the 2027 pilot. I can withdraw this consent at any time by replying "stop" or writing to {email}.`
- Not covered under any reading: newsletters, launch announcements or a paid offer later. The privacy notice also says "We don't send news emails." Each of those needs a separate, unticked consent (CRTC Regs s.4: consent sought separately for each act) [V].
- Gaps in the build: `pilot_request.status` has no `unsubscribed` value and there is no suppression list. Build both before the first follow-up (brief for `cto` via `cro`).

**(8) LinkedIn / X DMs and SMS (question c)**
- SMS is a CEM: "electronic address" covers a telephone account and an instant-messaging account or "any similar account" (s.1(1)) [V]. ISED lists "email, social media and text messages" [V]. CRTC treats DMs case by case, and most commentators treat LinkedIn/X DMs as sent to an electronic address [S].
- Same consent rules as email. IC Regs s.3(d) [V] lifts s.6 for messages on a messaging service only where the sender ID and unsubscribe are conspicuously published and readily available in the platform's interface (e.g. the profile) **and** the recipient consented expressly or by implication. It removes the content burden, never the consent requirement.
- Practice: DM or text only people in (5), (6) or (7), or people whose public profile shows their business contact and role (s.10(9)(b)). Put a link to a page carrying the sender ID and opt-out (CRTC Regs s.2(2)) in the DM or SMS, plus "Reply STOP and I won't message again" (draft #1b already does). A LinkedIn connection alone is not a relationship [S].
- Public posts on Farjad's own profile (draft #6a) are not sent to an electronic address and fall outside s.6 [S]. Competition Act rules on misleading claims still apply.

**(9) Individual farmers found publicly: default DO NOT**
- In theory s.10(9)(b) [V] could cover a farm business's own website address, if the message is relevant to the farm business and there is no "no CEM" statement. In practice: a third-party directory listing is not publication by the farmer; scraping or harvesting is banned by our rules and by PIPEDA's address-harvesting provisions [S]; and the brand risk is high. The plan already says no mass blasts.
- Exception only with legal's written sign-off, recipient by recipient, with the record in §3.

## 3. Records to keep (s.13 onus) [V for onus; field list is our proposal]
One row per recipient in the CRM (not in UTMs, not in git):
- name, organisation, address or handle, category (1)-(9), legal basis (provision, e.g. "s.10(9)(b)"), source URL, access date, a screenshot or saved copy of the page showing the address and no "no CEM" statement, and a one-line relevance note;
- relationship evidence for (5): last two-way exchange date and channel; for (6): referrer full name and that person's relationship to both sides;
- for (7): `pilot_request.id`, `consent_at`, `consent_text`, locale;
- every message sent: date, channel, template id, final text;
- opt-out: date received, date actioned (target same day, maximum 10 business days), and an entry in a permanent suppression list kept even after the record is deleted (hash only, if legal agrees).
- Re-check the source page on the day of sending for (1)-(3). Recompute the 2-year or 6-month windows on the day of sending for (4)-(5).
- CRTC's compliance-program guidance (bulletin 2014-326) recommends written policies, training and record-keeping [S]. Keep this note as the written policy.

## 4. Penalties and liability [V unless marked]
- Contravening s.6-9 is a violation subject to an administrative monetary penalty (s.20(1)). The maximum is **$1,000,000 per violation for an individual and $10,000,000 for any other person** (s.20(4)). The purpose is "to promote compliance … and not to punish" (s.20(2)). Factors include the nature and scope of the violation, history, financial benefit and ability to pay (s.20(3)).
- Officers and directors are personally liable if they directed, authorized, assented to, acquiesced in or participated in a violation (s.31). Employers are liable for their employees and agents (s.32). Since Farjad sends every message himself, both apply to him directly.
- Due-diligence defence (s.33(1)): records and this policy are the evidence for it.
- The private right of action (ss.47-51) shows as "Repealed before coming into force" in the consolidated text.
- Separate exposure: misleading representations in electronic messages under the Competition Act (s.74.011) [S]. That makes the website line "Approved by a human agronomist before it reaches you" (`pilot.get`) relevant: it contradicts D4 and the privacy notice, which allow approval by an administrator. Fix before outreach points to the site.

## 5. Changes to the drafts before anything is sent
1. Replace `{SENDER_BLOCK}` with "Farjad Iranmehr, on behalf of {legal entity} (CloverProof), {mailing address}, {email}, {phone or web}", kept valid for 60 days after each send.
2. Replace `{OPTOUT}` with the §1 wording (stops all CloverProof CEMs).
3. Draft #2: add the referral line from (6), or switch to a three-way introduction.
4. DMs (#1b, #6b): add a link to a sender-info and opt-out page. That page has to be built (brief for `cto` via `cro`).
5. Subjects #3b/#8b ("Re:"): use them only as a real reply in the same thread, never as a fresh email.

## Questions for legal (CPO → coo → legal-compliance-specialist)
1. Is an invitation to a free, unpaid pilot from a start-up that plans to charge later a CEM under s.1(2)? We assume yes.
2. Does a pilot-form submission, or an email asking about the free pilot, count as an "inquiry or application" under s.10(10)(e), giving 6 months of implied consent?
3. Does the s.6(5)(a) personal-relationship exemption hold when Farjad writes from a CloverProof business address on behalf of the company?
4. Do Farjad's personal dealings, or those of Ashavid Inc. or VisaRoads Inc., with a farmer create an existing business relationship for CloverProof's legal entity?
5. Which legal entity sends, and what mailing address may we publish (CRTC Regs s.2(1)(d))? Is a virtual or registered-office address acceptable?
6. Is the §2(7) replacement consent wording sufficient as express consent under s.10(1) and CRTC Regs s.4? Must it be a separate checkbox from "store these details"?
7. CCA or association directory listings: do they count as conspicuous publication by the person, and do directory terms against solicitation defeat s.10(9)(b)?
8. Can an individual farm's own website address ever be used under s.10(9)(b), or should category (9) stay a hard no?
9. LinkedIn/X DMs: is a profile-linked sender-info page enough for IC Regs s.3(d) or CRTC Regs s.2(2)? Does an accepted connection request create implied consent?
10. How long should consent and opt-out records be kept, and may we keep a hashed suppression entry after a PIPEDA deletion request?
11. The privacy notice says the pilot is "open to farms in Ontario" while the plan runs a Manitoba backup track. Does the notice need to change before Prairie outreach?
12. PIPEDA (plan §6 question e): consent and retention for farm data collected at intake. This is separate from CASL and needs its own review.
