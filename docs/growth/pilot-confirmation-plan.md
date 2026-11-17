# Pilot confirmation plan: from qualified request to confirmed farm, Dec 14 to Jan 15

Owner: `account-executive`, for `cro`. Status: DRAFT, 2026-11-16. Nothing here is sent by us; Farjad Iranmehr runs every call and sends every message.
Inputs: `pilot-icp.md` (checklist, disqualifiers), `pilot-recruitment-plan.md` (W3-W7, A1b), `pilot-funnel.md` (stages 4-6).
Labels: FACT (from those docs), PROPOSAL (needs a decision), ESTIMATE, UNKNOWN.
No agronomic numbers, no yield or savings promises, no third-party approval claims, no fertilizer brands.

## 0. Honesty frame (D4), used in every call and message
- Every plan is reviewed before it reaches the farm. Until a human agronomist is named, the reviewer is an AI agent (`ai_reviewed`) and **no real-farm plan is released**. Target for naming a human agronomist: before Jan 29, 2027. FACT (D4 as cited in `pilot-icp.md`).
- Confirmation = a **place in the pilot**. It is not a delivery date and not a guarantee that a plan will be delivered by a given date.
- Approved wording: "reviewed before it reaches you". Never "agronomist-reviewed" until a human agronomist is named. Reviewer details are confirmed to each farm before its plan is released.
- Pilot terms (free, concierge, A1) are an ASSUMPTION still to be confirmed by Farjad. No price is quoted.

## 1. Definition of "confirmed" (PROPOSAL for `head-of-data` and CPO; closes funnel question Q5)

Confirmed = status `accepted` in the funnel = **all** of:
1. The farm passed all 8 ICP checklist items on a call (section 2), recorded as `qualified`.
2. We sent a short written pilot-terms message (one page, plain language; content in 1.2).
3. A **written reply from the decision-maker** accepts those terms: a reply email that states acceptance, from the address on the pilot request. A text-only "yes" on a call is NOT confirmed; it is `qualified`, awaiting the reply.
4. We replied with a written place offer (one line: "we hold a place for you").

Date of confirmation = the date of the farm's written reply. Store the email (or a pointer to it) outside the repo; no personal data in the repo.

### 1.2 What the terms message must say (draft content, legal review pending via COO)
- Pilot, free during the pilot (if A1 is confirmed). No price quoted, no later-price promise.
- Scope: wheat, nitrogen only. No soil test = N only, with a lower confidence level, plus a recommendation to take a lab test for P/K. P/K needs a lab test.
- Reviewed before it reaches you; reviewer is an AI agent until a human agronomist is named; no real-farm plan is released before that; the target date is not a promise; we tell you the reviewer details before your plan is released.
- Data: what we ask for, why (to make your plan and to improve the tool), who sees it. Consent wording is PENDING legal review (COO); use no final wording and collect no data beyond the pilot request until it exists.
- No guarantee of results of any kind. A place is not a delivery date.
- Either side may withdraw at any time before release (PROPOSAL, to confirm).
- Sender identified, contact details and unsubscribe line (CASL; see recruitment plan section 6).

### 1.3 Edge cases (PROPOSAL)
- Advisor replies instead of the farmer: not confirmed. The decision-maker must reply.
- Reply with conditions ("yes, if it raises yield"): not confirmed; answer with objection 6.
- No reply after the terms message: reminder day 3, second reminder day 7, then `withdrawn` (`no_reply`). Sending is Farjad's.
- Two farms, one email: one confirmation per farm; ask `head-of-data` (funnel Q7).

## 2. 20-minute qualification call guide

Goal of the call: one outcome only, a yes or no on the 8 checklist items and agreement to receive the terms message. Not a sale; not an agronomy session.
Before the call: read the pilot request (name, country, main crop, farm size, notes). Have this page open. Do not copy personal data into the repo.

| Min | Part | What to do |
|---|---|---|
| 0-2 | Opening | Introduce yourself and CloverProof in one sentence: "We turn field and soil data into a field-specific nitrogen plan for wheat, with the reasons, and a proof document. It is a pilot." Ask if 20 minutes still works. Say you will take notes and that nothing is promised on this call. |
| 2-4 | Honest framing | Say it plainly: "This is early-stage. A place in the pilot is not a delivery date. Every plan is reviewed before it reaches you; reviewer details are confirmed before your plan is released." Do not say "agronomist-reviewed". |
| 4-5 | Scope | See 2.1. |
| 5-16 | 8 ICP questions | See 2.2. Mark each pass, fail or unsure as you go. |
| 16-18 | Data use | See 2.3. |
| 18-20 | Close | See 2.4. |

### 2.1 What to say about scope
- Wheat only, this season. Other crops: not now, kept on a list for later.
- Nitrogen only unless there is a lab soil test. With no soil test we give N only, at a lower confidence level, and recommend a lab test for P/K. P/K rates are not given without a lab test.
- Vendor-neutral: "We do not sell fertilizer, take commissions or recommend products or brands. The plan says what, how much, when and why; where you buy is your choice." If they ask for a brand, that is a disqualifier; say so politely.
- Software only. No app or dashboard for farmers in this pilot; plans arrive as a document.
- Not a nutrient-management filing or a certification. The proof document is a record.

### 2.2 The 8 ICP questions (from `pilot-icp.md` section 6)
| # | Ask | Pass signal | Fail or flag |
|---|---|---|---|
| 1 | Which province and county? | Ontario (primary), Manitoba or other Prairie (backup). | Elsewhere: objection 9; not served. Note it as a waitlist or `out_of_region`. |
| 2 | Will you grow wheat in 2027? Winter or spring? How many wheat fields? | Wheat in 2027. Ontario: winter stand already in the ground. Prairie: spring wheat. | No wheat: `not_wheat`. Ontario with no stand: flag for Farjad. |
| 3 | How many wheat fields, and how many acres? | 1-6 fields (ESTIMATE band, agronomist to confirm). | Dozens of fields, or one minor side field: flag. |
| 4 | Do you have a lab soil test report? Which lab, which date? | A report, or willing to take a test, or accepts N-only. | Wants P/K rates with no test: disqualifier. |
| 5 | Can you send field, previous crop, previous N and the report by Jan 15 (Prairie: earlier, see section 6)? | Yes, with a date. | No: `no_data_in_time`. |
| 6 | Who signs off on N decisions? Does your advisor know? | Decision-maker on the call, or advisor aware. | Advisor opposed: flag as risk; do not claim any advisor endorses us. |
| 7 | What do you expect from the pilot? | Understands: pilot, reviewed before release, nothing guaranteed. | Expects a guaranteed yield or savings result: disqualifier. |
| 8 | Is this email the right one for follow-up? Is it fine to follow up about the pilot? | Yes, recorded. | No: stop. |

Mark 4: record whether the farm is a "full", "confirm" or "N-only" case (matches the field-check result). Aim to hold at least one deliberate no-test farm (ICP open decision 3, draft 1-2).
Anything unsure: say "I will confirm and write to you", never improvise an answer.

### 2.3 Data use (wording pending legal review via the COO)
- Say only: "We will ask you for field details, previous crop and your soil test report so we can make the plan. You will get a short written consent before we use them. Your data is not sold and not shared with fertilizer sellers." Confirm the last sentence with the COO and legal before saying it; if not yet confirmed, drop it and say "we will send you the exact terms in writing".
- Do not state retention periods, jurisdictions or anonymisation details. UNKNOWN until legal review.
- Do not collect field data on the call beyond what is needed to qualify.

### 2.4 Closing and next steps
- Summarise: pass, fail or unsure on each item.
- If qualified: "I will send you the pilot terms in writing. A place is held when you reply accepting them. A place is not a delivery date."
- If not qualified: say why, in one line, and what could change it (for example a lab test).
- Set one follow-up date (reply expected within 3 days). Record in the tracker (section 4), outside the repo.
- Never send, sign or promise a date on the call.

## 3. Objection handling

Rule for every answer: only real product behaviour, no promises. If the product cannot do it, say so.

| # | Objection | Answer |
|---|---|---|
| 1 | "Is this from a fertilizer company?" | No. We sell no inputs and take no commissions, and the plan names no products or brands. Software only. The terms message states this in writing. |
| 2 | "Who reviews it?" | "Every plan is reviewed before it reaches you; reviewer details are confirmed before your plan is released." If pressed: today the reviewer is an AI agent, and no real-farm plan is released until a human agronomist is named. Make no claim about agronomist review, certification or credentials. |
| 3 | "My retailer already does this." | The plan is a second view, not a replacement: what, how much, when and why, written down, with a proof document you can show your advisor. We do not sell product, so there is no conflict. We do not say your retailer is wrong. If the retailer will be upset, ask whether they know; advisor awareness is item 6. |
| 4 | "What will it cost later?" | "The pilot is free (if A1 is confirmed). Pricing after the pilot is not decided, so I will not guess. You will be told before anything is charged." Quote no number. |
| 5 | "Who owns my data?" | You do. We ask for it to make your plan and to improve the tool. The exact consent text is being finalised and you will see it in writing before we use anything. Do not state retention or sharing terms until legal review is done. |
| 6 | "Will this increase my yield?" | "I cannot promise that, and no tool honestly can. The plan gives a reasoned recommendation with a confidence level, and the reasons. Results depend on many things we do not control." Do not cite savings or yield figures. |
| 7 | "I don't have a soil test." | Fine. We can make an N-only plan, at a lower confidence level, and we tell you which lab test to take for P/K. P/K rates are not given without a lab test. If a fresh test is possible before the data deadline, it gives a fuller plan. |
| 8 | "I'm in Manitoba / on the Prairies." | Possible, as the smaller backup track, remote only. Spring wheat N is decided around seeding, so we need your data earlier, in January, to deliver before seeding. A place is not a delivery date. Check against the Prairie rule set status before confirming (PLACEHOLDER until validated). |
| 9 | "I'm somewhere else (US, other province, other crop)." | Not in this pilot. Say so, offer the waitlist (consent to follow up recorded), promise nothing. |
| 10 | "Can I see a sample or a testimonial?" | There is a sample proof on the website. We have no testimonials and no endorsements, and we will not borrow anyone's name. |
| 11 | "Can I get the plan before Jan 29 / by February?" | Not promised. Real-farm plans are released only after a human agronomist is named (target before Jan 29, 2027, not guaranteed). Hold the place; send the data. |

## 4. Confirmation pipeline tracker (template only)

No personal data in the repo. Keep the live tracker outside the repo, or in the CRM `revops-specialist` sets up. Use opaque IDs (the `pilot_request` id), never names or emails. Status names follow `pilot-funnel.md` section 4.1.

| Farm ID (opaque) | Track (ON / Prairie) | Channel | Stage | Stage date | Next step | Next-step date | Owner | Close reason |
|---|---|---|---|---|---|---|---|---|
| | | | new / contacted / qualified / terms sent / accepted / declined / withdrawn | | | | Farjad (acts), AE (prepares) | |

Stage rules:
- `terms sent` is a tracker-only sub-stage between `qualified` and `accepted` (no DB status for it); the funnel keeps `qualified` until the reply.
- Each row needs a next step and a date. No next-step date = row is stale.
- Weekly roll-up (no names) goes to the funnel report: counts per stage, accepted vs goal, rows past their next-step date.
- Close reasons: `not_wheat`, `out_of_region`, `no_capacity`, `no_data_in_time`, `no_reply`, `not_interested`, `duplicate`, `other`.
- Until a status-update process exists (funnel 4.3), stage changes are by hand; flag this to `revops-specialist`.

Per-farm checks before marking `accepted`: written reply on file; checklist items 1-8 recorded; D4 wording used (no "agronomist-reviewed"); track noted; test or no-test noted.

## 5. Week-by-week schedule, Dec 14 to Jan 15

Targets are cumulative confirmed, from the recruitment plan section 4 (ESTIMATES, not promises): end W4 = 1, W5 = 3, W6 = 6, W7 = 8. The floor is 5 by Jan 8 or the plan floor of 5 applies.
Conversion assumptions (qualified to confirmed 80%) come from the recruitment plan; they are not benchmarks.

| Week | Dates | Focus | Actions | Target (cumulative confirmed) |
|---|---|---|---|---|
| W3 | Dec 14-20 | Calls | Call every request within 2 business days (speed to lead). Qualify; send terms to qualified farms the same day. Add Prairie farms first for terms so their data comes early. | 0 confirmed; about 1 qualified |
| W4 | Dec 21-27 | Terms and replies; freeze starts Dec 25 | Send terms to qualified farms before Dec 24. Dec 24 checkpoint (recruitment plan): at least 20 conversations, otherwise more effort on independent agronomists and network. From Dec 25: no new outreach; reply only if a farm writes. State in the terms message that replies after Dec 25 may be slower. | 1 |
| W5 | Dec 28-Jan 3 | Freeze: replies only | Answer inbound replies; record written acceptances; reminders only on terms already sent, no new push. Jan 3 checkpoint, see below. | 2-3 by Jan 3 |
| W6 | Jan 4-10 | Second push, follow-ups | Reminder day 3 and day 7 on open terms. Calls with new qualified requests. SWAC Jan 5-6 is the only event that feeds the funnel; attending is Farjad's decision. Jan 8 checkpoint, see below. | 5-6 |
| W7 | Jan 11-15 | Close | Final reminder Jan 11-12. Final call slots Jan 12-13. Confirm or waitlist everything open by Jan 15. Do not confirm more than capacity (R5): waitlist beyond 10. Report Jan 15 count. | 8 target (5 floor) |

### 5.1 Checkpoints and fallbacks
| Date | Test | If met | If missed (fallback, decisions are Farjad's) |
|---|---|---|---|
| Dec 24 | At least 20 conversations | Continue. | Add independent-agronomist effort (channel 1) and network (channel 2) in the freeze week; no extra cold volume. |
| Jan 3 | At least 3 confirmed | Continue plan. | Shift effort to the Prairie track (Manitoba first), but only while Prairie data can still arrive early enough (section 6). Reorder follow-ups to the warmest requests. Review the funnel: is the loss at qualification, at terms, or at reply? |
| Jan 8 | At least 5 confirmed (floor) | Continue to 8. | Decision for Farjad: (a) launch with fewer than 5, (b) extend confirmation for Ontario winter wheat after Jan 15, since the stand is already in the ground and timing allows it (A3, agronomist to confirm), (c) keep the date and accept the lower count. Do not lower the checklist to reach the number. |
| Jan 15 | 5-10 confirmed | Close: waitlist the rest, tell them it is a waitlist, not a place. | Report the real count; do not count `qualified` or verbal yeses as confirmed. |

If the terms reply rate is the bottleneck: shorten the terms message, call to answer questions, do not add urgency or pressure.

## 6. Data and intake checklist (request after confirmation)

Ask only after the written confirmation. Prairie farms first: spring wheat N is decided at or before seeding, so their data must be received before Ontario farms; Prairie intake runs first (recruitment plan 4b). Target dates for Prairie data are to set with the agronomist (UNKNOWN; spring N timing not confirmed). A written consent for data use is needed before any data is used (pending legal review, COO).

Per farm:
| # | Item | Needed | Notes |
|---|---|---|---|
| 1 | Farm and decision-maker contact (confirmed email) | Yes | Stored outside the repo. |
| 2 | Per field: location or boundary, size, name or ID | Yes | Wheat fields only; band 1-6 (ESTIMATE). |
| 3 | Per field: crop in 2027 (winter or spring wheat), variety if known | Yes | |
| 4 | Per field: previous crop | Yes | |
| 5 | Per field: previous years' nitrogen applied (what and when, as the farm recorded it) | Nice-to-have, raises confidence | Last two years (ICP). |
| 6 | Per field: prior-year yield range | Nice-to-have | Farm-reported only. |
| 7 | Soil test report, one per field if possible (copy of the lab report) | Yes for P/K; optional for N-only | Record: **extraction method** (Olsen, Bray-1, Mehlich-3, other), **sampling depth**, **sampling date**, **lab**, **units** and **form** (P vs P2O5, K vs K2O). Accept any report; do not reject for method (rule 7 stores it; the agronomist decides use). |
| 8 | If no test: confirm in writing the farm accepts N-only, lower confidence, and a P/K test recommendation | Yes | Same message as the terms. |
| 9 | Advisor aware? (yes / no / not applicable) | Yes | No claim of endorsement. |
| 10 | Notes on anything unusual in the field this season | Optional | |

Order of intake: Prairie confirmed farms first (January), then Ontario winter wheat farms. Each farm gets one list and one deadline in writing. Chase gently, no pressure language.

## 7. Risks

| # | Risk | Why it matters | Mitigation or decision |
|---|---|---|---|
| 1 | **No human agronomist named by Jan 29** | D4: no real-farm plan is released until one is. Farms confirmed on Jan 15 could wait with no plan. | Every message says confirmation is a place, not a date, and reviewer details are confirmed before release. Track the naming date weekly with Farjad. If missed: tell every confirmed farm in writing, offer to withdraw, no new promise. Never use "agronomist-reviewed" before it is true. Decision for Farjad: who and by when. |
| 2 | Confirming then not delivering erodes trust | Brand has no testimonials or endorsements. | Confirm only farms that understood D4 on the call (checklist item 7). Do not over-confirm (waitlist beyond 10, R5). |
| 3 | Capacity: calls and terms in 5 weeks; review minutes Feb-Apr | One person runs calls, terms, intake. Prairie and Ontario both need rule sets (R1). | Cap confirmed farms by what review can hold; Prairie smaller (1-2). Measure `minutes_spent` once plans exist. |
| 4 | Holiday freeze, Dec 25 to about Jan 3 | Replies slow; reminders may fall on holidays; farms are on the farm at winter events. | Send terms before Dec 24; reminders resume Jan 4; set expectation in the message. Count no confirmations as certain in W5. |
| 5 | Prairie timing | Data must come early; remote only; Prairie pack is PLACEHOLDER. | Prairie intake first; do not confirm a Prairie farm unless the agronomist confirms the rule set and timing are workable. |
| 6 | Consent and CASL wording not reviewed | Terms and data-use message can fail compliance. | No final data-use wording until COO and legal review. One-to-one messages only. Mark every message draft "needs Farjad". |
| 7 | Status tracking has no process | `qualified` and `accepted` have no UI or history (funnel 4.3), so the count could be wrong. | Tracker outside the repo, kept weekly; `revops-specialist` to set the smallest safe process. |
| 8 | Farms see AI review as a downgrade | Honest wording may reduce acceptance. | Do not hide it or soften it; acceptance rate (qualified to confirmed 80%) is an ESTIMATE and may drop. Re-forecast at Jan 3. |

## 8. Open items for Farjad / CPO / head-of-data
1. Approve the definition of "confirmed" in section 1 (reply email accepting terms).
2. Confirm free-pilot terms (A1) and the withdrawal clause.
3. Name the human agronomist or give a date; D4 target before Jan 29.
4. Legal and COO: data-use consent wording; CASL review of the terms message.
5. Confirm agronomist capacity: how many farms and Prairie share.
6. Funnel Q5 and Q7 for `head-of-data`: proof document, one email with two farms.
