# Support macros (English, draft for review)

Owner: customer-support-specialist, for `coo`. Farjad Iranmehr sends every reply; we only draft. Use the request's database id (`[REQUEST ID]`) in notes, never names or contact details. Placeholders: `[CONTACT EMAIL]`, `[PRIVACY NOTICE LINK]`, `[NAME]`.

Updated 2026-11-16 (D4, launch scope). Farjad Iranmehr signs as founder, not as the agronomist. "The agronomist" in these macros means the named human agronomist `[HUMAN AGRONOMIST NAME, CREDENTIALS]` (not yet named; fill before any send). Never write "reviewed by an agronomist" unless a human did. The AI assistant (`ai_reviewed`) is a check, never an approval. Launch scope: Ontario (Canada) farms, winter wheat.

Global rules: no rates, thresholds, prices or dates of growth stages. No third-party acceptance claims. Field-specific questions go to agronomist review. No legal promises.

## M1. Request received
- Trigger: new pilot request or field check submitted.
- Reply: Hi [NAME], thank you for your request. We have it on file. Places in the pilot are limited and depend on location and fit, so this is not yet a confirmation. We will come back to you with next steps. If you have a laboratory soil test for the field, you can send it now.
- Internal note: log request id; check country/region and whether a soil test exists. Do not promise a place.
- Escalation: none. Founder if the request looks like a partner or press enquiry.

## M2. Missing soil test
- Trigger: farmer has no soil test, or asks why P/K is missing.
- Reply: Thanks for the details. Without a soil test we can plan nitrogen only, and our confidence is limited. For phosphorus and potassium we recommend a soil test from a laboratory in your area before we plan them. When you have the result, send it and we will update the plan as a new version.
- Internal note: engine rule is N only, max medium confidence, test recommended for P/K. Never suggest an estimate for P/K.
- Escalation: agronomist only if the farmer insists on P/K advice (reply is still the same).

## M3. Unreadable lab report
- Trigger: photo or PDF blurry, cropped, or key values unreadable.
- Reply: Thank you for the report. We could not read all of it clearly. Could you send a sharper copy or the original file from the lab? Please make sure the page with the values, units and method is included. We do not want to guess any value.
- Internal note: do not transcribe unclear values. Record the request id and what is unreadable.
- Escalation: agronomist if the lab format is unfamiliar.

## M4. Units or method unclear
- Trigger: report lacks unit, extraction method, depth, date, or P/K form (element vs oxide).
- Reply: Your report is missing some details we need to use it safely: [LIST: unit / extraction method / sampling depth / sampling date / whether phosphorus and potassium are reported as the element or the oxide]. Could you check the report or ask the lab? We will not assume these, because a wrong assumption changes the plan.
- Internal note: these fields are mandatory in the soil_test data. Do not fill in from memory.
- Escalation: agronomist if the lab confirms something unusual.

## M5. "What rate should I use?"
- Trigger: any request for an amount, timing or product for a field.
- Reply: We do not give rates in messages. Amounts appear only in your plan after a human agronomist has reviewed and approved it. I have passed your question and your field details to the agronomist review, and it will be included. If you have not yet sent a soil test or field details, please do, so the plan is as well supported as it can be.
- Internal note: do not quote the placeholder pack, past plans or other farms' numbers.
- Escalation: agronomist (always).

## M6. "Can you change the number?"
- Trigger: farmer wants a lower or higher figure, or disputes one.
- Reply: Thank you for telling us. We never edit a plan in place. If there is a reason to change it, for example new information, the agronomist reviews it and issues a new version with the reason recorded; the earlier version stays on file. Please tell us what has changed or why you think the number does not fit. I cannot promise a particular result.
- Internal note: collect the reason in the farmer's words; log under the recommendation id.
- Escalation: agronomist.

## M7. "Will my bank accept this?"
- Trigger: asks if a bank, certifier, regulator, retailer or insurer will accept the PDF.
- Reply: We cannot say. Each organisation sets its own requirements and we have not agreed anything with them. The PDF records what was recommended, why, who reviewed it and which version it is. Please ask the organisation what they need; if useful, we can describe what the document contains.
- Internal note: never say "accepted", "approved", "compliant" or "recognised".
- Escalation: founder if a named organisation asks to partner.

## M8. "Which brand should I buy?"
- Trigger: asks for a product, brand or supplier.
- Reply: CloverProof is independent and sells no fertilizer, so we do not recommend brands. Your plan names nutrients, and your supplier or local advisor can help you match them to products.
- Internal note: no supplier comparisons, no price comments.
- Escalation: none.

## M9. Deletion request
- Trigger: asks to delete data, erase account, or withdraw.
- Reply: Thank you. We have recorded your request and passed it to the person responsible for privacy, who will reply to you. What we keep and for how long is described in `[PRIVACY NOTICE LINK]`. You can also write to `[CONTACT EMAIL]`.
- Internal note: do not delete anything ourselves, do not state timelines or legal rights. Log request id and date received.
- Escalation: privacy (immediately; also tell founder).

## M10. Unsubscribe
- Trigger: asks to stop emails or messages.
- Reply: Understood. We will stop contacting you about the pilot. If you also want your data deleted, tell us and we will pass it on as described in `[PRIVACY NOTICE LINK]`.
- Internal note: mark contact preference at once; keep the minimum record needed to honour it.
- Escalation: privacy if they also mention their data.

## M11. Plan delayed
- Trigger: farmer asks where the plan is.
- Reply: Thank you for waiting. Your plan has not yet been approved. Nothing goes out until a human agronomist has reviewed and approved it. [REASON: waiting for a soil test / waiting for a corrected detail / in the review queue]. I will tell you as soon as there is an update. I cannot give a firm date.
- Internal note: check status; name only a true reason. Do not promise a day.
- Escalation: agronomist if overdue relative to the farmer's season; founder if farmer is upset.

## M12. Why is confidence "low"?
- Trigger: farmer sees low confidence and worries.
- Reply: In the pilot, some regional values behind the calculation are still being validated by our agronomist team, so confidence can show low. It does not mean the plan is wrong. It means the plan is a carefully reviewed starting point, and each number comes with its reason. If you can add a soil test or other missing detail, it may improve.
- Internal note: no numbers; do not say what would change the level exactly.
- Escalation: agronomist if the farmer disputes the plan.

## M13. Complaint about a result
- Trigger: farmer unhappy with a plan or an outcome.
- Reply: I am sorry this has been a poor experience. Thank you for telling us. I have passed your message to our agronomist review and to the founder, and one of them will respond. To help, please tell us which field and what happened, in your own words. We will not argue the point in this message.
- Internal note: stay factual, no blame, no admission and no compensation promises. Record the recommendation id and version.
- Escalation: agronomist and founder.

## M14. Emergency or crop damage
- Trigger: farmer reports visible damage, burn, poisoning, spill, livestock risk or urgent loss.
- Reply: I am sorry to hear this. CloverProof cannot give advice on an emergency. Please contact a local agronomist, your supplier's technical line, or the relevant local authority straight away. If there is any danger to people or animals, contact local emergency services. We have passed your message to our agronomist review for the record.
- Internal note: send within the same working session. Give no diagnosis or remedy. Record the request id and what the plan said.
- Escalation: agronomist and founder (same day).

## M15. Correct my details
- Trigger: farmer reports wrong field name, area, crop or history.
- Reply: Thank you. Please send the corrected detail. If it affects your plan, the agronomist will review it and issue a new version with the reason; the earlier one stays on file.
- Internal note: do not edit stored plans. Log the change request.
- Escalation: agronomist.

## M16. Not selected for the pilot
- Trigger: request outside the pilot area (not an Ontario, Canada farm), outside the pilot crop (launch crop is winter wheat), or over capacity.
- Reply: Thank you for your interest. We cannot include your farm in this pilot. The pilot is open only to farms in Ontario, Canada, and for now covers winter wheat only, and places are limited. [USE ONLY THE TRUE REASON: outside the pilot area / outside the pilot crop / places are full]. We will keep your request and tell you if that changes, unless you prefer we do not.
- Internal note: confirm with founder first. Do not promise a later place or a date for other regions or crops. Log demand by region and crop using the request id.
- Escalation: founder.

## M17. Is an AI making my plan?
- Trigger: farmer asks whether AI, a robot or software makes the plan, or who really checks it.
- Reply: Fair question. Our calculation engine works out the numbers from fixed rules. An AI assistant then checks the logic of the plan and flags anything that looks inconsistent; it does not approve anything. A human agronomist, [HUMAN AGRONOMIST NAME, CREDENTIALS], checks and approves every number before it reaches you. You make the final decision about what to do in your field.
- Internal note: be exact. Software calculates, AI assists the check (`ai_reviewed`), a human approves. Do not say "reviewed by an agronomist" for a plan no human has approved. Do not name the AI tool or claim it is accurate. Do not present Farjad Iranmehr as the agronomist.
- Escalation: founder if the farmer objects to AI being used at all.

## M18. When will my plan arrive?
- Trigger: farmer asks for a delivery date and the plan is waiting on human approval (status before `approved`).
- Reply: Thank you for asking. Your plan is being prepared, and it will be sent only after a human agronomist has checked and approved it. That review comes first, so I cannot give you a date. I will write as soon as there is an update. If we need anything from you, such as a soil test or a corrected detail, we will ask.
- Internal note: check status first; mention a waiting reason only if true. No dates, no "this week", no review-time targets (PROPOSED targets stay internal). Use M11 if the farmer says it is overdue or the reason is known.
- Escalation: agronomist review if overdue relative to the farmer's season; founder if farmer is upset.

## Escalation table

| Topic | Route | Response goal |
|---|---|---|
| Any rate, timing, product, specific-field question | Agronomist | Same working day |
| Change or dispute of a number | Agronomist | Same working day |
| Complaint about a result | Agronomist and founder | Same working day |
| Emergency or crop damage | Agronomist and founder | Immediately |
| Deletion, data access, privacy question | Privacy (founder informed) | Immediately |
| Unsubscribe | Support handles; privacy if data mentioned | Same working day |
| Bank, certifier, regulator or retailer asks | Founder | Same working day |
| Press, partner, pricing after the pilot | Founder | Within the week |
| Soil test or lab-format issue | Agronomist if unfamiliar | Within the week |
| Pilot logistics, status, "when will my plan arrive", "is an AI making my plan" | Support (founder if the farmer objects to AI use) | Within the week |
| Outside Ontario or crop other than winter wheat | Founder confirms M16 | Within the week |

## Triage rules

1. Read for safety first. Any damage, spill, animal or human risk: M14, escalate at once.
2. Privacy next. Any mention of deleting, erasing, access, or stopping: M9 or M10, escalate to privacy.
3. Does the reply need a number, timing or product for a specific field? Use M5 and route to the agronomist. Never answer it ourselves.
4. Is it a request to change or dispute a plan? M6, agronomist.
5. Does it ask whether a third party accepts the PDF? M7, and never say yes.
6. Is it a complaint? M13, agronomist and founder.
7. Missing or unclear data: M2, M3, M4. Asks about AI: M17. Asks when the plan arrives: M18 (M11 if overdue). Outside Ontario or not winter wheat: M16.
8. Anything uncertain or legal: escalate to founder; do not improvise.
9. Draft only. Farjad Iranmehr sends. Use request ids, no personal data in repo files.
10. Log every request, and each week's top questions go into the digest for `customer-success-manager`.
