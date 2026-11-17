# Billing model options (Q9, internal, never published)

Owner: cso (business-strategist draft), 2026-11-16. Decision: Farjad Iranmehr, sprint S26 (~Oct–Nov 2027). Pricing hypotheses are due at S11 (May 2027, `docs/sprints/roadmap.md`).
Skills used: `pricing`, `marketing-psychology:evidence-check`. Labels: FACT (cited), ESTIMATE, UNKNOWN. No CloverProof price is proposed here.

## What drives cost and value
- **Unit of work = one plan** (one field × season × crop; `crop_plan` → `recommendation` in CLAUDE.md data model). Re-plans create versions, not new plans.
- **Cost to serve per farm (ESTIMATE)** ≈ fields per farm × reviewer minutes per plan × reviewer cost per minute + compute + support.
  - Fields per farm: 1–6 wheat fields (pilot ICP ESTIMATE).
  - Reviewer minutes per plan: UNKNOWN; the pilot measures it (`review.minutes_spent`).
  - Reviewer cost: today an AI agent (D4), cost UNKNOWN but likely small (ESTIMATE). Once a human agronomist is named, comparable rates of $100–300/h for a CCA/PAg are UNVERIFIED: both former sources (Alberta Farm Express "Adding an agronomist to your farm team"; Canola Council "Shopping for an agronomist") return 404 as of 2026-11-17. Do not use externally; replace with a live source or pilot-call data.
  - Illustration only (ESTIMATE, not a benchmark): at $150/h human review, 2 fields × 15 min = $75 per farm-season; 6 fields × 45 min = $675. Range spans ~9×, so **minutes per plan and fields per farm are the two assumptions that decide the model.**
- **Reference prices (not ours):** OMAFRA AgriSuite calculator, no fee listed (ESTIMATE free) ([data.ontario.ca](https://data.ontario.ca/dataset/18988bd0-8835-4e2a-9cf2-f63e4554d346)); FCC AgExpert Field $0 Basic / $399 per yr Premium ([agexpert.ca](https://agexpert.ca/Field)); Climate FieldView $0 trial / $499 per yr, currency not stated on the Canadian page ([climate.com en-ca](https://climate.com/en-ca/pricing.html)); independent full-package agronomy ~$8–10/ac, Prairie canola context (UNVERIFIED: Canola Council "Shopping for an agronomist" returns 404 as of 2026-11-17). Ontario wheat-specific advisor rates: UNKNOWN.

## Options
### A. Per farm, per season
- **How:** one fee per farm per season covering all its plans, possibly banded by field count (e.g. 1–3, 4–6, 7+ fields).
- **Pros:** matches a once-a-season decision and the "farmer owns data" model; simple to say; predictable for the grower; review cost is absorbed across fields.
- **Cons:** without bands, high-field farms are served at a loss when review is human; one plan on a one-field farm looks expensive next to a free calculator.
- **Advisor channel:** workable if the advisor can pay for client farms (account = sum of farms). Neutral to advisors.
- **RK-08:** the grower compares one annual fee against $0 AgriSuite; value must be the record + log + workflow, not the number.
- **Margin driver:** fields per farm (bands control it) × minutes per plan.

### B. Per advisor seat (per year)
- **How:** advisor/org pays per user; unlimited or capped farms; growers free.
- **Pros:** sells to the professional who already pays for tools; avoids growers comparing directly to the free calculator; predictable recurring revenue; aligns with planned org workflow.
- **Cons:** cost scales with plans, revenue with seats: a heavy advisor with 40 farms is underpriced if review is human (ESTIMATE); seat sharing; leaves out growers with no advisor (the pilot's main contact); risks being seen as competing with the advisor's own fee.
- **Advisor channel:** strongest fit. **RK-08:** weakest exposure (advisors already go beyond free tools), but UNKNOWN whether advisors pay for software at all.
- **Margin driver:** farms per seat × fields per farm × minutes per plan; needs a farm cap or overage.

### C. Per plan (per field-season)
- **How:** pay for each reviewed plan; re-versions free.
- **Pros:** price tracks cost exactly; low entry for small farms; easy to try one field.
- **Cons:** metering friction at the moment of a time-critical decision; growers may run only one field and use AgriSuite for the rest (RK-08 strongest here); unpredictable for advisors; incentive to skip fields.
- **Advisor channel:** acceptable as pass-through billing, awkward to budget.
- **Margin driver:** minutes per plan only.

### D. Hybrid: farm-season unit, two payers
- **How:** the billable unit is the farm-season (A, banded); a grower buys it directly, or an advisor buys a block of farm-seasons for clients at a volume rate. Optional small per-plan overage above the top band.
- **Pros:** one unit for both channels; cost-linked through bands; advisors keep their client relationship; data ownership stays with the farm.
- **Cons:** two price lists to explain; volume rate needs farms-per-advisor data we do not have; more billing logic in S26.

## Leaning (not a decision)
Leaning D, then A. Reasons: the decision is seasonal and per farm; the farm owns the data; the advisor channel needs a way to pay for clients; per-plan metering invites cherry-picking against a free tool; per-seat breaks once a human reviewer costs real minutes. **What would flip it:** advisors refuse per-farm and want flat seats (→ B with farm cap); minutes per plan near zero with AI review and stable (→ any metric works; choose simplest); growers only pay for 1–2 fields (→ C).

## What the pilot and beta must measure to choose
| Metric | Why it matters | Owner group | When |
|---|---|---|---|
| Reviewer minutes per plan (median, p90), by soil-test vs no-test | Cost per plan; banding | head-of-data | Pilot, Feb–Apr 2027, every sprint |
| Fields (plans) per farm; acres per field | Band design; per-farm vs per-plan gap | head-of-data | Pilot |
| Versions per plan and reason mix | Hidden review cost of re-plans | head-of-data | Pilot |
| Share of growers who also ran AgriSuite / an advisor plan, and whether they valued our record over the number | RK-08 | cro | Pilot exit interviews, Apr–May 2027 |
| Who would pay (grower, advisor, other) and preferred unit; price-sensitivity questions, no live price | Payer and metric | cro + cso | Pilot exit + beta, spring 2027 |
| Farms per advisor; advisor time saved vs their current method | Seat vs block pricing | cro + head-of-data | Closed beta, spring 2027 |
| Intent to use next season; plans in second cycle | Retention base for any model | cro | Beta, spring–summer 2027 |
| Cost per plan of AI review (compute) and support minutes per farm | Floor cost | cto + coo | Pilot onward |

Note: pilot is free; stated willingness to pay is weak evidence. Treat it as a hypothesis until a paid offer runs.

**Options only — Farjad Iranmehr decides.**
