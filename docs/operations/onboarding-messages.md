# Onboarding messages and stages (pilot path, English)

Owner: `customer-onboarding-specialist`, for `coo`. Status: DRAFT. Nothing here is sent by us. Farjad Iranmehr sends every message.

Sources: `docs/operations/pilot-sop.md` (statuses, steps, targets), `docs/operations/intake-checklist.md` (section 9 = the 13 questions, section 10 = ready for plan), `docs/operations/support-macros.md` (M-ids).

## Rules for every message

- Transactional only: it answers the farmer's own request or serves the pilot they joined. No promotion, no offers, no newsletter, no upsell (CASL).
- Every message ends with the identification and contact block below.
- No agronomic numbers: no rates, thresholds, yields, depths or dates of growth stages. Plans reach the farmer only as the approved PDF (gate G1).
- Sent only to the email on file. Signer: Farjad Iranmehr, as founder of CloverProof (not as the agronomist).
- Reviewer honesty (D4, 2026-11-16): software and an AI assistant help prepare the plan; a named human agronomist, `[HUMAN AGRONOMIST NAME, CREDENTIALS]` (not yet named; fill before any send), checks and approves every number. Never write "reviewed by an agronomist" unless a human did.
- Approval kinds (decision by Farjad Iranmehr, 2026-11-16; CLAUDE.md rule 8): a plan is approved either by the human agronomist (`agronomist_approved`) or by `[SUPERADMIN NAME, ROLE]`, a human superadmin who is not an agronomist (`superadmin_approved`). Messages sent before a plan exists (2, 7) describe both possibilities; messages about a specific plan (8, 9) use the variant for that plan's stored approval kind. For `superadmin_approved` never write "reviewed/approved by an agronomist", "agronomist review" or "carefully reviewed" (`docs/operations/legal/proof-pdf-wording.md` B2, J).
- Residency (OQ-06, 2026-11-16): real farmer data is stored in Canada. Until Canadian hosting is live (SOP gate G9), do not enter farmer replies into any hosted environment.
- Pilot scope: Ontario (Canada) farms, launch crop winter wheat.
- All time targets are `PROPOSED — validate in S3 workload model` (business days, Eastern time), taken from the SOP.
- Log the send date on the case. Use the request id in notes, never the farmer's name or contact details in repo files.
- Replies that are not covered here go to the support macros (M-ids below), not improvised.

### Standard footer (append to all messages)

```
Farjad Iranmehr
CloverProof, a service of [LEGAL ENTITY]
Contact: [CONTACT EMAIL]
How we handle your data: [PRIVACY NOTICE LINK]
You are receiving this because you asked to take part in the CloverProof pilot. Reply "stop" and we will stop contacting you about the pilot.
```

### Placeholders used

`[NAME]`, `[REQUEST ID]` (internal only, not in body), `[FIELD NAME]`, `[FARM NAME]`, `[CONTACT EMAIL]`, `[PRIVACY NOTICE LINK]`, `[PILOT TERMS LINK]`, `[LEGAL ENTITY]`, `[VERSION]`, `[OLD VERSION]`, `[NEW VERSION]`, `[WHAT CHANGED]`, `[MISSING ITEMS]`, `[SEASON]`, `[REPLY-BY DATE]` (only a date we have set, never invented).

---

## 1. Request received

- SOP trigger: `pilot_request.status = new`; step 1. Send as the first reply, then set `contacted`.
- Follow-up timing (PROPOSED): first reply within 2 business days of the request. Decision within 5 business days after this reply.
- Attach: nothing.
- Related macro: M1 (same intent; this version adds the footer).

**Subject:** We received your CloverProof pilot request

```
Hi [NAME],

Thank you for your request to join the CloverProof pilot. We have it on file.

The pilot is open to farms in Ontario, Canada, and for now covers winter wheat. Places are limited and depend on fit, so this is not yet a confirmation. We will write to you again with a decision and, if you are accepted, the next steps.

If you already have a laboratory soil test for the field, you can send it now. If you do not, that is fine.

[STANDARD FOOTER]
```

---

## 2. Accepted: welcome and what we need

- SOP trigger: `pilot_request.status = accepted`; step 2 entry. Creates the farm record; farm status becomes `intake_open`.
- Follow-up timing (PROPOSED): send within 1 business day after acceptance. Chase per message 4.
- Attach: `[PILOT TERMS LINK]` as a link, not a file. Optional: the 13 questions pasted in the body (below).
- Source of questions: intake-checklist section 9. Question 13 uses the consent wording approved by the COO; do not reword it.

**Subject:** Welcome to the CloverProof pilot: what we need from you

```
Hi [NAME],

Good news: we would like to include [FARM NAME] in the CloverProof pilot. Thank you for taking part.

What happens: you send us some details about one field. Our software and an AI assistant help prepare a fertilizer plan. A named person approves every number before you see it: our human agronomist, [HUMAN AGRONOMIST NAME, CREDENTIALS], or [SUPERADMIN NAME, ROLE], who is not an agronomist. The plan says which, and says so plainly if no agronomist reviewed it; you can ask us to send only plans our agronomist has reviewed. You then receive a PDF with the plan, the reasons, and how it was made. You keep the final decision on what you do in your field.

This is a pilot. Please read the terms here: [PILOT TERMS LINK]

To start, please reply with answers to these questions. Short answers are fine, and "I don't know" is an acceptable answer. We only ask for what the plan uses.

1. Your name and the best email to reach you.
2. Your country and region.
3. The name of the field you want a plan for.
4. How big the field is. Give the number and the unit you use (hectares, acres, or something else).
5. Where it is: nearest town plus a pin on a map, or a photo of the field boundary.
6. The crop you plan to grow there this coming season.
7. The yield you are aiming for, and the unit you usually measure it in.
8. How you got to that goal (average of recent years, best recent year, a neighbour's yield, or a guess). Any of these is fine.
9. The crop grown in this field last season. If it was left empty, tell us.
10. Do you have a recent soil test report for this field? Yes or no.
11. If yes, please send the whole report: a PDF or clear photos of every page. If no, that is fine. We can plan nitrogen only, and we will recommend a lab test so we can also advise on phosphorus and potassium.
12. If you have a report, do you know the date the soil was sampled?
13. [CONSENT WORDING APPROVED BY COO — must match `docs/operations/legal/consent-wording.md` §2 v0.3: you agree we may use this information to prepare your plan, and that it will be approved by a named person (our agronomist, or [SUPERADMIN NAME, ROLE], who is not an agronomist). Reply "yes" to confirm.]

You do not need to tell us the sampling depth, the lab method, or how the lab reports phosphorus and potassium. We read those from the report. If something is missing there, we ask the lab.

Why we ask: each answer is used in your plan, or helps the person who approves it check it. If you are unsure why we need something, ask us.

[STANDARD FOOTER]
```

- Internal note: if the farm is outside Ontario, Canada, or the main crop is not winter wheat, do not send this. Use the not-selected message (3) and log the demand (SOP escalation "outside scope"). Question 2 (country and region) confirms Ontario.

---

## 3. Not selected

- SOP trigger: `pilot_request.status = declined` (Founder decides; confirm with Founder before sending, per M16).
- Follow-up timing (PROPOSED): send with the decision, within 5 business days after the first reply. No chasing.
- Attach: nothing.
- Related macro: M16.
- Keep-in-touch rule: include the optional paragraph only if the farmer ticked the marketing/updates opt-in on the form. A later "we will tell you if places open" note is a message about their own request, but do not add any promotional content. See open item 1.

**Subject:** Your CloverProof pilot request

```
Hi [NAME],

Thank you for your interest in the CloverProof pilot. We have looked at your request, and we cannot include [FARM NAME] in this pilot. [USE ONLY THE TRUE REASON(S): The pilot is open only to farms in Ontario, Canada. / The pilot covers winter wheat only for now. / Places are limited and are now full.] This is not a judgement on your farm.

[ONLY IF OPTED IN: You asked to hear from us, so we will keep your request on file and contact you if this changes. We cannot promise a place.]

[IF NOT OPTED IN: We will not contact you again about the pilot unless you write to us. If you want your request removed, reply and we will pass it on to the person responsible for privacy.]

[STANDARD FOOTER, without the "You are receiving this because..." line changed if not opted in; keep it as is]
```

- Internal note: never promise a later place or a date for other regions or crops. State no reason that is not true (outside the pilot area, outside the pilot crop, capacity). Covers "outside the pilot area/crop".

---

## 4. Reminder: missing data

- SOP trigger: farm status `intake_open`, items still missing. Step 2.
- Follow-up timing (PROPOSED): chase every 3 business days; at most 3 chases; after the third with no reply, mark `paused` and stop. Reopen when the farmer replies.
- Attach: nothing. List only the missing items.
- Related macros: M3 (unreadable report), M4 (units or method unclear). Use those wording blocks for the specific item.
- Variants: A first reminder, B second reminder, C last reminder (before `paused`).

**Subject:** Still need a few details for your CloverProof plan

```
Hi [NAME],

Thank you for the details you have sent so far. To prepare the plan for [FIELD NAME] we still need:

[MISSING ITEMS: a short list, one line each, in plain language, taken from the 13 questions. For a lab report problem, use M3 or M4 wording.]

If you are not sure about an item, tell us what you do know. We do not guess, because a wrong assumption changes the plan. If you do not have a soil test, that is fine; see the note we sent about planning nitrogen only.

[VARIANT A: Reply when you can, and we will carry on.]
[VARIANT B: This is a second reminder. If now is not a good time, tell us and we will wait.]
[VARIANT C: This is our last reminder. We will pause your file so we do not keep writing to you. If you reply later, we will pick it up again.]

[STANDARD FOOTER]
```

---

## 5. Soil-test guidance: what to ask the lab to report

- SOP trigger: farm `intake_open`, farmer has no test or a report that is missing details (soil-tests table in the SOP). Send when the farmer asks how to get a test, or together with message 6.
- Follow-up timing (PROPOSED): no separate clock. Counts under the intake chase rule (message 4).
- Attach: nothing. Do not name or recommend a lab by brand. The farmer chooses a laboratory in their area.
- Related macros: M2 (missing soil test), M4 (unclear details).

**Subject:** How to get a soil test we can use

```
Hi [NAME],

You asked how to get a soil test for [FIELD NAME]. Here is what helps.

Use a laboratory in your area. We do not recommend a particular company. Your local advisor or farm supplier can tell you which labs are used locally and how to take the sample.

When you order the test, ask the lab to report these on the results:
- The extraction method used for each nutrient (the name of the test method).
- The depth the sample was taken from.
- The date the soil was sampled (not only the date of the report).
- The units for each result.
- Whether phosphorus and potassium are reported as the element or as the oxide.

Please send us the full report, with every page, as a PDF or clear photos. A report with ratings only (such as low, medium, high) and no values is hard for us to use, so if you can, ask for the measured values as well.

We do not guess these details. If something is missing, we may ask the lab or you. When the report arrives, we add it to your plan as a new version.

[STANDARD FOOTER]
```

---

## 6. No soil test: nitrogen-only plan

- SOP trigger: farm `intake_open`, farmer answered "no" to question 10 (checklist path B; gate G2). Records `no soil test` on the field.
- Follow-up timing (PROPOSED): send in the same business day as the farmer's answer, within the step 2 window. Then continue intake chases for the other missing items.
- Attach: nothing.
- Related macro: M2 (same message, expanded). Required by the "ready for plan" path B: farmer told in writing.
- Rule: never suggest an estimate for phosphorus or potassium.

**Subject:** Your plan without a soil test: nitrogen only

```
Hi [NAME],

Thank you for letting us know that [FIELD NAME] has no soil test.

You can still take part. Without a soil test, we can plan nitrogen only, and our confidence in the plan is limited. For phosphorus and potassium, we recommend a soil test from a laboratory in your area. We cannot advise on those two nutrients without it.

If you want to do a test, we can tell you what to ask the lab to include (separate message). When you have the result, send it and we will update your plan as a new version. The earlier version stays on file.

If you prefer not to test now, we will go ahead with the nitrogen-only plan.

Please reply to confirm that you understand the plan will cover nitrogen only, or tell us if you have questions.

[STANDARD FOOTER]
```

---

## 7. Intake complete: what happens next

- SOP trigger: farm status `intake_complete` (ready for plan, checklist section 10, all items true, keyed values second-checked for path A); step 3 starts the same day.
- Follow-up timing (PROPOSED): send same day as `intake_complete`. Review target: reviewed within 3 business days after the plan is drafted. Delivery within 1 business day after approval. Do not state these as promises to the farmer; say "we will write when there is an update".
- Attach: nothing.
- Related macro: M11 (plan delayed) for later status questions.

**Subject:** We have what we need for [FIELD NAME]

```
Hi [NAME],

Thank you. We now have the details we need to prepare the plan for [FIELD NAME].

What happens next:
1. We prepare the plan.
2. A named person approves each number: our human agronomist, [HUMAN AGRONOMIST NAME, CREDENTIALS], or [SUPERADMIN NAME, ROLE], who is not an agronomist. An AI assistant helps check the logic, but it does not approve anything. Nothing is sent to you before it has been approved, and the plan says who approved it.
3. We email you a PDF with the plan, the reasons behind it, and how it was made.

We cannot give a firm date, because the review comes first. If we need anything else, we will write to you. If something changes in the meantime, for example a new soil test or a change of crop, tell us and we will add it.

[STANDARD FOOTER]
```

---

## 8. Plan delivered: cover note

- SOP trigger: farm status `approved`, then `delivered` once sent; step 5. Only after the checklist before every send is complete (review approve row for this recommendation id; no third-party claim; sha256 matches).
- Follow-up timing (PROPOSED): send within 1 business day after approval. First application-log ask within 7 days after delivery (message 10).
- Attach: the approved proof PDF for the exact recommendation id. No other file; no screenshots or engine output.
- Wording status: the pilot and low-confidence wording is subject to Farjad Iranmehr approval and review by `legal-compliance-specialist` (SOP open decision 3). Do not change it without that.
- Cover note by approval kind (decision 2026-11-16): **8A** for `agronomist_approved` (matches `proof-pdf-wording.md` Block B); **8B** for `superadmin_approved` (matches Block B2). Read the approval kind from the review row; never choose by habit. Keep the PDF and cover note identical on this point; copy the disclaimer once counsel fixes it (OQ-07). 8B is `[COUNSEL]`-held with B2 (`oq-07-decision-pack.md` Q17); liability flag: `ontario-agronomist-credentials.md` §3.6.
- Send gate: only when a human approve row (`agronomist_approved` or `superadmin_approved`) exists for this recommendation id (an `ai_reviewed` sign-off alone is not enough). 8B only for an Ontario farm that has not asked for agronomist-only plans.
- If no soil test: add the extra paragraph (in brackets).
- Related macros: M5, M7, M8, M12.

### 8A. `agronomist_approved`

**Subject:** Your CloverProof plan for [FIELD NAME] (version [VERSION])

```
Hi [NAME],

Your plan for [FIELD NAME] is attached as a PDF (version [VERSION]).

Please note:
- This is a pilot. The calculation constants behind the tool are still being validated, so the confidence label on your plan may show low. Low does not mean the plan is wrong. It means treat it as a carefully reviewed starting point, and tell us how it goes.
- This plan was prepared with CloverProof and reviewed by [HUMAN AGRONOMIST NAME, CREDENTIALS] on [DATE]. Software and an AI assistant helped prepare it; the human agronomist checked and approved every number.
- You keep the final decision on what you do in your field. The plan is a recommendation.
- The PDF records how the plan was made: the inputs you gave us, the reasons for each number, and which version it is. It is not endorsed or approved by any lender, certifier or regulator, and we have not agreed anything with them.

[IF NO SOIL TEST: This plan covers nitrogen only because there is no soil test. For phosphorus and potassium we recommend a laboratory soil test. Send us the result and we will update the plan as a new version.]

Questions about the plan are welcome. Reply to this email. We do not give amounts in messages; they are in the PDF only. If you think a detail is wrong, tell us and the agronomist will review it.

[STANDARD FOOTER]
```

### 8B. `superadmin_approved` — not reviewed by an agronomist `[COUNSEL]`

**Subject:** Your CloverProof plan for [FIELD NAME] (version [VERSION]) — not reviewed by an agronomist

```
Hi [NAME],

Your plan for [FIELD NAME] is attached as a PDF (version [VERSION]).

Please read this first:
- This plan was prepared with CloverProof and approved by [SUPERADMIN NAME, ROLE] at [LEGAL ENTITY] on [DATE]. It was not reviewed by an agronomist. [SUPERADMIN NAME] is not an agronomist. Please get advice from a qualified agronomist or crop adviser before you rely on it.
- This is a pilot. The calculation constants behind the tool are still being validated, so the confidence label on your plan may show low. Low does not mean the plan is wrong. It means treat it as a starting point, and tell us how it goes.
- Software and an AI assistant helped prepare it; the AI check is not a review by an agronomist and cannot approve a plan.
- You keep the final decision on what you do in your field. The plan is a recommendation.
- The PDF records how the plan was made: the inputs you gave us, the reasons for each number, and which version it is. It is not endorsed or approved by any lender, certifier or regulator, and we have not agreed anything with them.
- If you would rather receive only plans our agronomist has reviewed, reply and tell us. It may take longer, and we will tell you if we cannot.

[IF NO SOIL TEST: This plan covers nitrogen only because there is no soil test. For phosphorus and potassium we recommend a laboratory soil test. Send us the result and we will update the plan as a new version.]

Questions about the plan are welcome. Reply to this email. We do not give amounts in messages; they are in the PDF only. If you think a detail is wrong, tell us and we will review it.

[STANDARD FOOTER]
```

---

## 9. Corrected version

- SOP trigger: correction path after delivery (new soil test, changed crop plan, error). Farm returns to `in_review`, then `approved` for the new version; send after approval of the new version.
- Follow-up timing (PROPOSED): notify within 1 business day after approval of the new version.
- Attach: the new approved PDF. The old PDF is kept and never deleted; do not attach it.
- Related macros: M6 (change request), M15 (correct my details).
- Approval line by kind: use variant 9A line for `agronomist_approved`, 9B line for `superadmin_approved` (same rules as 8A/8B).
- If the correction fixes a number that went out without approval (G1 breach), the Founder and `coo` are told the same day; wording of that message goes to the Founder, not this template.

**Subject:** Updated plan for [FIELD NAME]: version [NEW VERSION] replaces [OLD VERSION]

```
Hi [NAME],

We have issued a new version of your plan for [FIELD NAME]. Version [NEW VERSION] is attached. It replaces version [OLD VERSION]. Please use the new version.

What changed: [WHAT CHANGED, in plain words and the reason, without repeating any number].

[9A — agronomist_approved: A human agronomist, [HUMAN AGRONOMIST NAME, CREDENTIALS], has reviewed and approved this version on [DATE].]
[9B — superadmin_approved: This version was approved by [SUPERADMIN NAME, ROLE] on [DATE]. It was not reviewed by an agronomist; please get advice from a qualified agronomist or crop adviser before you rely on it.]

The earlier version stays on file with us, so there is a record of both. It does not change the points in our first note: this is a pilot, the confidence label may show low, you keep the final decision, and the PDF is not endorsed by any lender, certifier or regulator.

If anything is still wrong, tell us.

[STANDARD FOOTER]
```

---

## 10. Application-log request (planned vs actual)

- SOP trigger: farm status `delivered` / `logging`; step 6.
- Follow-up timing (PROPOSED): first ask within 7 days after delivery; reminder every 14 days; final entry by May 7. Same message reused for reminders with the line in brackets.
- Attach: nothing.
- Ask for facts only. No advice, no judgement of what they did.

**Subject:** What did you apply on [FIELD NAME]?

```
Hi [NAME],

To close the loop on your plan, please tell us what you actually did on [FIELD NAME]. It helps us compare the plan with practice and improve the pilot. There is no right or wrong answer: please tell us what you really did, even if it differs from the plan.

For each application, please send:
- The product you used (any name or label is fine).
- How much you applied, in the unit you use, and how much of the nutrient it contains if the label shows it.
- The date.
- Which field.

Short notes or a photo of your record are fine. If you have not applied anything yet, tell us and we will check in later.

[REMINDER ONLY: This is a reminder. If you would rather not share this, say so and we will stop asking.]

[STANDARD FOOTER]
```

---

## 11. End of season: feedback and data retention

- SOP trigger: log complete or season over; step 7; Founder closes. Status `closed` after feedback.
- Follow-up timing (PROPOSED): feedback within 14 days after the log is complete. One reminder only; then close without feedback.
- Attach: nothing. Optional: the five feedback questions in the body.
- Related macros: M9 (deletion), M10 (unsubscribe).
- Retention wording: state only what `[PRIVACY NOTICE LINK]` says. The retention vs deletion rule for calibration data is open (SOP decision 4). Until it is set, use the placeholder sentence and have `legal-compliance-specialist` confirm.

**Subject:** Your feedback on the CloverProof pilot, and your data

```
Hi [NAME],

Thank you for taking part in the CloverProof pilot for [SEASON]. We would like your feedback. You can reply by email, or tell us if you prefer a short call.

1. What did you do in the field, compared with the plan?
2. What was the reason for any difference?
3. Was the plan clear? What was confusing?
4. Was anything missing from the PDF that you needed?
5. Is there anything you want us to know that we did not ask?

About your data: [RETENTION STATEMENT: what we keep, why, and for how long, exactly as stated in the privacy notice: [PRIVACY NOTICE LINK]]. You can ask us at any time to delete your data or correct it by writing to [CONTACT EMAIL]. We will confirm in writing what was deleted and what, if anything, was kept and why.

This is the last message we plan to send about the pilot. We will not contact you again unless you reply.

[STANDARD FOOTER]
```

---

## Onboarding stages

Maps farm-level SOP statuses to the stages `data-analyst` measures. Stage records live in the weekly ops sheet until the `pilot_farm` status location is decided (SOP open decision 1). Business days, Eastern time. Targets are `PROPOSED — validate in S3 workload model`.

| # | Stage | SOP status | Entered when | Exited when | Clock owner | Target (PROPOSED) | Message |
|---|---|---|---|---|---|---|---|
| 0 | Request | `new` | `pilot_request.created_at` | First reply sent (`contacted`) | CloverProof | 2 business days | 1 |
| 1 | Triage | `contacted` | First reply sent | `accepted` or `declined` | CloverProof (Founder) | 5 business days | 3 if declined |
| 2 | Accepted, not yet started | `accepted` | Founder accepts | Checklist sent (`intake_open`) | CloverProof | 1 business day | 2 |
| 3 | Collecting data | `intake_open` | Checklist sent | `intake_complete` (ready for plan, checklist section 10) | Farmer / CloverProof, see split below | Chase every 3 business days, max 3 | 4, 5, 6 |
| 4 | Paused | `paused` (ops label) | Third chase with no reply | Farmer replies (returns to stage 3) | Farmer | Not counted against any target | 4 (variant C) |
| 5 | Plan in progress | `intake_complete`, `plan_drafted` | `intake_complete` | Engine recommendation saved | CloverProof | Same day | 7 |
| 6 | In review | `in_review` | `plan_drafted` | `approved` (or `reject`, back to stage 3) | CloverProof (approver: agronomist or superadmin) | 3 business days | none |
| 7 | Delivery | `approved` | Review approve row saved | `delivered` (email sent) | CloverProof | 1 business day | 8 |
| 8 | Logging | `delivered`, `logging` | `delivered` | Log complete, or farmer marked non-responsive | Farmer | First ask within 7 days; reminder every 14 days; final entry by May 7 | 10 |
| 9 | Feedback | log complete | Log complete | `closed` | CloverProof (Founder) | 14 days | 11 |
| - | Correction (loop) | `in_review` after `delivered` | Correction request or error found | New version `approved` and sent | CloverProof | 1 business day to notify after approval | 9 |

### Definitions for `data-analyst`

- **Time in stage** = exit timestamp minus entry timestamp, in business days (Eastern, excluding weekends). A farm still in a stage is measured to now ("days in status", as in the weekly cadence).
- **Entry and exit events** are the status changes in the table. Each change is logged with date, farm id and who set it. Use farm id / request id, never names.
- **Wait owner split for stage 3:** time between "we asked" and "farmer replied" is farmer time; time between "farmer replied" and the next action by us is CloverProof time. Log both. Only CloverProof time counts against our targets. Farmer time is reported as a separate metric, and the stuck-farm flag uses total days.
- **Stuck farm** = days in stage over the PROPOSED target (CloverProof-owned stages), or over 3 chases in stage 3. Listed in the weekly ops note with next action and owner.
- **Reject loop:** a reject returns the farm to stage 3. Keep the first stage 6 time, start a new stage 3 count, and report how many loops each farm had.
- **Pause:** time in `paused` is excluded from lead-time totals. Report it separately.
- **Corrections** are a loop, not a new stage count: measure notify time from approval of the new version.
- **Reported metrics:** median and maximum time per stage; percentage of farms within target per stage; days from request to delivered (secondary metric in the SOP); number of chases before reply; farms per stage today versus the 10-farm cap; share of intakes by path (A with soil test, B no soil test). Primary SOP metric (agronomist `minutes_spent` per plan) stays with the review table, not this document. Report deliveries by approval kind (`agronomist_approved` vs `superadmin_approved`).
- Targets are PROPOSED. Report actuals; do not tune targets from fewer than the pilot's first few farms.

---

## Open items for `coo` / Farjad Iranmehr

1. Does the pilot request form capture a marketing / keep-in-touch opt-in? Message 3 depends on it. `support-macros.md` M16 keeps the request unless the farmer objects; this file is stricter (only if opted in). Align both. `legal-compliance-specialist` to confirm CASL wording and the footer.
2. Approve the consent wording for question 13 and the retention statement in message 11 (SOP open decision 4).
3. Approve the pilot / low-confidence cover-note wording in message 8A and 8B (SOP open decision 3); 8B and 9B are counsel-held with PDF Block B2.
6. Name the human agronomist (`[HUMAN AGRONOMIST NAME, CREDENTIALS]`) and the superadmin approver (`[SUPERADMIN NAME, ROLE]`) before any message 2, 7, 8 or 9 is sent; none can go out with a placeholder. If no agronomist will be named for the pilot, messages 2 and 7 must drop the agronomist alternative rather than imply one exists.
4. Confirm the "reply stop" opt-out line is honoured within the CASL time limit (see M10) and that someone owns the inbox.
5. `[LEGAL ENTITY]`, `[CONTACT EMAIL]`, `[PRIVACY NOTICE LINK]`, `[PILOT TERMS LINK]` must be filled before any send. Stage 3 chase wording relies on the "paused" label, which is not yet a stored status (SOP open decision 1).
