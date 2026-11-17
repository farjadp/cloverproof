# CloverProof positioning (one page, internal)

Owner: cso (business-strategist draft), 2026-11-16. Status: draft. Skills used: `product-marketing`, `marketing-psychology:evidence-check`.
Labels: FACT (cited), ESTIMATE, UNKNOWN. Nothing here is approved public copy.

## Positioning statement
For **Ontario winter wheat growers and the independent advisors who plan their nitrogen**, CloverProof is **field-specific fertilizer decision software** that turns one field's data (with or without a soil test) into what, how much, when and why, with a confidence level on every number, reviewed before release, and an unchangeable versioned record of the decision. Unlike free calculators, supplier agronomy or farm-management software, it is **vendor-neutral and keeps the reasoning and every change on record**, so the decision can be checked later by the grower, the advisor, or anyone the grower chooses to share it with.

## Who it is for / not for
- **For (primary):** Ontario winter wheat owner-operators with 1–6 wheat fields (ESTIMATE band, pilot ICP) who decide spring top-dress N in Feb–Apr; independent agronomists / CCAs managing several such farms. **Backup:** Manitoba spring wheat, plans delivered before seeding (ICP decision 2026-11-16).
- **Not for (now):** fertilizer retailers/distributors (neutrality conflict); multi-hundred-field enterprises; buyers wanting a brand recommendation, P/K rates without a lab test, guaranteed yield or savings, a regulatory sign-off (e.g. nutrient management plan), sensors/satellite/app features; non-wheat crops in 2027. Source: `git show myca/growth-s2-a73813:docs/growth/pilot-icp.md`.

## Job and pain
- **Job:** "Decide this field's spring N rate and timing, and be able to show later why." 
- **Pain (hypotheses, untested):** the free calculator gives a number but no field-history record or change trail; supplier advice may be shaped by what is sold; last year's rate ignores this year's field; the reasoning lives in someone's head or a spreadsheet. All UNKNOWN until pilot interviews.

## Why us vs alternatives
| Alternative | What they get today | Cost to grower | Where CloverProof differs | Where it is stronger than us |
|---|---|---|---|---|
| Free official tools (OMAFRA AgriSuite Crop Nutrient Calculator) | N-P-K needs from soil test, crop, yield goal, location ([data.ontario.ca](https://data.ontario.ca/dataset/18988bd0-8835-4e2a-9cf2-f63e4554d346), [data2.ontario.ca fertilizer calc](https://data2.ontario.ca/dataset/fertilizer-calculator-agrisuite-tool)) | No fee listed (ESTIMATE: free) | Per-number confidence + reason, review before release, immutable versioned record, application log (planned) | Official Ontario field-trial basis ([OSCIA EFP infosheet 16, 2025](https://www.ontariosoilcrop.org/wp-content/uploads/2025/07/2025_EFP-Infosheet-16_Nutrient-Mgt-in-Growing-Crops_EN_FINAL.pdf)); free; trusted. **RK-08.** |
| Dealer / retail agronomy | Advice from the input supplier | UNKNOWN whether bundled. UNVERIFIED: "most farmers do not pay for independent agronomy advice" (Canola Council "Shopping for an agronomist"; source page returns 404 as of 2026-11-17, claim seen only in a search summary — do not use externally) | Sells nothing; names nutrients and rates, never brands | Relationship, field visits, credit, delivery |
| Independent agronomist / CCA | Human judgment, field visits | UNVERIFIED: ~$8–10/ac full package; $200–300/h one-off visits (Prairie canola guide, Canola Council "Shopping for an agronomist"; source page returns 404 as of 2026-11-17 — do not use externally) | Software that can make an advisor faster and leave a record; partner, not replacement | Accountability of a named professional; we have none yet (D4) |
| FMS software (Climate FieldView, FCC AgExpert Field) | Records, maps, yield analysis, scripts | FieldView $0 trial / $499 per yr, currency not stated ([climate.com en-ca](https://climate.com/en-ca/pricing.html)); AgExpert Field $0 Basic / $399 per yr Premium; the $499/yr price is the separate Premium Bundle with accounting, currency not stated ([agexpert.ca](https://agexpert.ca/Field), accessed 2026-11-17) | A reasoned rate decision with confidence, not a data store | Breadth, machine data, installed base |
| Last year's rate | Habit | $0 | Field- and season-specific reason | Zero effort |

## Proof points
**Can claim today (true in the repo/design):** vendor-neutral, sells no inputs; software only; every number carries high/medium/low confidence with a written reason; no soil test = N only at max medium, with a P/K test recommendation; recommendations are never overwritten, every edit is a new version with a reason; each proof document stores inputs, engine and rule-set versions and a SHA-256 fingerprint (CLAUDE.md hard rules 2–5). Engine v0 covers wheat N only (pilot ICP).
**Only after the pilot (do not claim before):** reviewer minutes per plan; how often review changed the engine number; grower/advisor satisfaction or willingness to pay; any time or cost saving; that advisors use it across several farms; that any lender, program or lab finds the record useful. Calibration against real outcomes: later still.

## Words we must not use
- D4: "agronomist-reviewed", "checked/approved by an agronomist", "certified", "approved by", "expert-reviewed". Allowed: "reviewed before release"; where review is described, say it is currently AI-assisted review until a named agronomist joins.
- Endorsement: no implied acceptance by OMAFRA/OMAFA, 4R / Fertilizer Canada, lenders, insurers, labs, CCA bodies, sustainability programs. No logos.
- Outcomes: "guaranteed", "saves you $X", "increases yield", "optimal rate", "accurate", "compliant", "NMP-ready".
- "Proof" must mean "record of what was recommended and why", never proof of correctness (keep the existing disclaimer, en.json:123).

## Message variants (hypotheses to test in pilot calls, not claims)
1. **Grower:** "One field, one season: your spring N rate with the reason and confidence written down, from a company that sells no fertilizer." Test: does "record of why" matter to growers, or only the number?
2. **Advisor:** "Draft field N plans for your clients in fewer minutes, with every change you make kept as a dated, reasoned version." Test: does the advisor see a tool or a competitor? (ICP: advisor can block us.)
3. **Intermediary (lender, sustainability program, lab):** "If a grower chooses to share it, a fixed, versioned record of the rate decision and its inputs." Test only as discovery: would such a record be useful to them at all? No claim of acceptance; do not pitch before the grower owns and grants access.
