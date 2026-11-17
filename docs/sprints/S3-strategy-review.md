# S3 — Strategy review + retro (cso)

Owner: `cso` via `market-research-analyst` and `business-strategist`. Date: 2026-11-16 (S3 exit: Dec 23).
IDs: NB-STR-01, RK-08 (`docs/plans/backend-distribution.md` §6, `backend-traceability.md`). Q9 options brought forward from NB-STR-02 (S24–S25). Test code: `DR` (CPO document review).

## What is now true (evidence)
| Exit item | File | Status |
|---|---|---|
| Positioning one-pager | [docs/strategy/positioning.md](../strategy/positioning.md) | draft for DR |
| Competitor and alternative scan + RK-08 argument + pilot hypotheses | [docs/strategy/competitor-scan.md](../strategy/competitor-scan.md) | draft for DR |
| Billing-model options for Q9 (options only) | [docs/strategy/billing-model-options.md](../strategy/billing-model-options.md) | draft for DR |

Key findings:
- **AgriSuite is free** (Canada.ca 2019) and returns crop nutrient need and removal, not a single reasoned decision. We found no confidence level, immutable record, application log or multi-farm workflow in it. Whether it needs an account and how it exports are UNKNOWN (ontario.ca returned 403 to our fetcher).
- **No public Ontario winter wheat N calculator found.** The corn N calculator (MERN) covers corn only. Grain Farmers of Ontario funded a wheat N project (2014–17), but we found no release. This is a gap today and a risk later, because OMAFRA could ship one for free.
- **One soil test can lead to several P/K answers** (sufficiency, removal or build; Field Crop News 2025). One reasoned number with its confidence and the method it rests on is the clearest gap we can own.
- **Retail agronomy and the main FMS tools are not vendor-neutral.** FieldView is about $499/yr and AgExpert about $399–499/yr; both prices need checking.
- **The real competitor is last year's rate.** The cost of switching is effort, not money.
- **RK-08 is not mitigated yet.** We found no lender, insurer or buyer that requires wheat nutrient records. OFCAF cost-share for third-party crop nutrient plans may be a funded path, but whether the program is still running is unclear.
- **Billing leaning, not a decision:** a hybrid (farm-season in field-count bands, paid by the grower or by an advisor buying a block), then per farm. Cost to serve ≈ fields × reviewer minutes × reviewer rate, so minutes per plan decides the model.

## CSO review notes (checked against CLAUDE.md and D4)
- None of the three files claims "agronomist-reviewed", endorsement, acceptance or guaranteed outcomes, and none contains an agronomic rate or constant. Specialist fee anchors (e.g. $8–10/ac) are labelled Prairie/canola, not Ontario wheat.
- Many claims rest on search snippets and are marked "snippet" or UNKNOWN. They must be re-verified before any external use (deck, website, sales).
- **Hypotheses H1, H2 and H5 need released plans.** Under D4 no real-farm plan is released until a human agronomist is named (OQ-04). If nobody is named by S5, the pilot cannot test RK-08 at all. This is the biggest strategy dependency.
- **Hypothesis H3 includes "4R retailer staff".** The pilot ICP lists retailers as anti-ICP. Those interviews are for discovery only and not pilot users; the CRO decides.
- **Website conflicts with D4.** `website/src/messages/en.json` makes "agronomist" review claims at lines 4, 19, 28, 64–65, 76, 118, 200 and 346. Route this to CPO → cto/cp-website + coo/legal. `.claude/agents/cso.md` uses the same wording internally.

## Decisions for Farjad Iranmehr
1. Website wording under D4: "reviewed before release" only, or say openly that review is currently AI-assisted?
2. Primary beta buyer: growers or advisors? This decides whether the CRO recruits advisors on purpose.
3. Human agronomist pay model (hourly, per plan or retainer). This sets the cost line in every billing option (OQ-04 / Q9).
4. Is a survey-only price test with beta users allowed before S26?

## Retro
- **Slowed us:**
  - ontario.ca blocked automated fetches (403), and we had no PDF reader. AgriSuite details are therefore weaker than they should be.
  - The plan docs live on an unmerged branch (`origin/backend-traceability`), and the pilot ICP is on an unpushed branch.
- **Change for next sprint:** before any external use, verify AgriSuite by hand in a browser (account, output, export), along with OFCAF status and Ontario CCA fees. The CRO can add these questions to pilot-recruitment calls.
