# Pilot ICP, season 2027

Owner: cro (SDR draft). Status: draft for review, 2026-11-16. Nothing here is a promise to any farm.
Scope: 5-10 farms, plans produced Feb-Apr 2027, farms confirmed by Jan 15, 2027. Engine v0 = **wheat, nitrogen only**. No soil test = N only (max `medium`); P/K needs a lab test. Every plan is reviewed before it reaches the farmer. Per D4 (`docs/plans/backend-plan-reconciliation.md` on `cpo-backend-plan`), the reviewer is an AI agent (`ai_reviewed`) until a human agronomist is named, and no real-farm plan is released until then. Vendor-neutral, software only.
Labels: FACT (cited), ESTIMATE (mine, unverified), UNKNOWN.

## 1. Crop: wheat, and why winter vs spring matters
- **Winter wheat** is seeded in the previous fall; the N decision is a spring top-dress once the crop breaks dormancy. A Feb-Apr plan is therefore on time, and Feb-Mar is the right window to deliver it. FACT (Ontario, OMAFRA specialist): early spring N is aimed at the last frost and in many years may be the only application; split spring N is advised for late-planted fields. [farms.com / OMAFRA](https://www.farms.com/news/winter-wheat-fertilizer-application-reminders-121205.aspx), [Field Crop News](https://fieldcropnews.com/?p=24016)
- **Spring wheat** is seeded in spring, so N is decided at or just before seeding (a plan arriving in late April may already be too late), unless fall-applied N is used. Prairie spring wheat pilots need plans in hand by about March. ESTIMATE of timing; Prairie N-timing practice sources not found, UNKNOWN until the agronomist confirms.
- Winter wheat fits the Feb-Apr window with more slack. The website's sample proof already shows winter wheat. [website en.json](../../website/src/messages/en.json) (`proof.cropValue`)
- Fall-applied N on Ontario winter wheat is reported as no benefit (same OMAFRA source). Not our scope either way; the engine covers one spring decision.
- Durum, soft white, hard red, etc.: class-level differences are an agronomist call. UNKNOWN to me.

## 2. Region options (decision for Farjad Iranmehr)
The agronomist's own regional expertise decides this and I do not know it. Below is evidence only.

| | A. Ontario winter wheat | B. Prairie spring wheat (SK/AB/MB) | C. US Great Lakes winter wheat (MI/OH) |
|---|---|---|---|
| Wheat area | Winter wheat estimates 1.05-1.12 M acres for the 2025 crop; sources disagree, UNKNOWN which is final. [Syngenta market news](https://www.syngenta.ca/market-news/wheat-area-falls-from-march-intentions), [Field Crop News](https://fieldcropnews.com/?p=29704). Canada winter wheat 1.6 M acres, mostly Eastern Canada. [StatCan 2025](https://www.statcan.gc.ca/o1/en/app/7889-principal-field-crop-areas-2025) | SK 14.0 M, MB 3.3 M total wheat (2025, June survey); AB 8.4 M is a March intention, not final. [StatCan 2025](https://www.statcan.gc.ca/o1/en/app/7889-principal-field-crop-areas-2025), [Grain Central](https://www.graincentral.com/markets/wheat-oats-pulses-curry-favour-in-canada/) | MI 530k, OH 570k planted (2025). [USDA NASS Sept 2025](https://esmis.nal.usda.gov/sites/default/release-files/5t34sj573/xs55pd582/3t947p85w/smgr0925.pdf) |
| N decision timing | Spring top-dress at green-up/last frost (see above). Fits Feb-Apr. | Spring pre-seed (or fall); tight for an April plan. UNKNOWN beyond that. | UNKNOWN; not researched. |
| Soil-test habit | Ontario-specific farmer share UNKNOWN. | Old poll: 51% SK, 67% MB, 68% AB test every year (2005, dated). [Western Producer](https://www.producer.com/?p=44474). National use survey says test frequency fell. [Fertilizer Canada 2023](https://fertilizercanada.ca/wp-content/uploads/2025/04/Fertilizer-Use-Survey-2023-Report.pdf) | UNKNOWN. |
| Lab methods (names only) | P: Olsen (sodium bicarbonate); K/Mg: ammonium acetate; Mehlich-3 and Bray P1 may appear on reports but are not accredited for Ontario recommendations. [OMAFRA via Ontario.ca](https://ontario.ca/page/interpreting-your-soil-test-results), [Field Crop News](https://fieldcropnews.com/2025/05/omafa-accredited-soil-testing-program/) | Modified Kelowna and Olsen (P); Mehlich-3, Bray, 2M KCl also run by labs; nitrate results are similar across labs but N recommendation logic differs. [Top Crop Manager](https://www.topcropmanager.com/soil-test-methodologies-affect-recommendations-part-ii-919/), [USask BMO lab](https://agbio.usask.ca/research/centres-and-facilities/bmo-soil-analytical-lab.php) | UNKNOWN; not researched. |
| Who advises | UNKNOWN split retail vs independent; no source found. OMAFRA/GFO extension is widely read (Field Crop News). | UNKNOWN split; Fertilizer Canada names 4R Designated Agronomists and 4R Certified Retailers as trusted advisers, no numbers. [Fertilizer Canada 2024](https://fertilizercanada.ca/wp-content/uploads/2026/03/Fertilizer-Use-Survey-National-Report-2024.pdf) | UNKNOWN. |
| Reach from Newmarket | ESTIMATE: same province, drive-in, farm visits possible; CASL/PIPEDA already our setup. | ESTIMATE: about 2,000-3,000 km, flight plus drive; remote-only call work. | Cross-border; US privacy/marketing rules not covered by our setup. Needs separate review. |
| Engine pack | Needs Ontario rule set, `PLACEHOLDER` until agronomist validates (CLAUDE.md rule 9). | Needs Prairie rule set, same. | Third pack; weakest fit. |

**Decision (Farjad Iranmehr via CPO, 2026-11-16): "Both" — Ontario winter wheat is the primary track; Prairie spring wheat (Manitoba first) is a smaller backup track.** Prairie plans must be delivered before seeding (target: by about March, to be confirmed by the agronomist), so Prairie farms must be confirmed and their data received earlier than Ontario farms.

Research basis:
- **Primary: Ontario winter wheat.** Timing fits Feb-Apr best, reach is easiest, and the Olsen-based test culture matches the engine's required inputs (method, depth, date stored). Seeded-fall farms already have the crop in the ground by Feb, which de-risks the "wheat in 2027" check.
- **Backup: Prairie spring wheat, Manitoba first.** Largest wheat area; Manitoba had the highest soil-test share in the dated poll. Risks: April timing and remote-only work.
- **Not recommended: US Great Lakes.** Cross-border legal and rule-set cost for a 5-10 farm pilot.
- Caveat: if the agronomist's validated experience is Prairie or elsewhere, that overrides this. **Decision for Farjad Iranmehr.**

## 3. Farm size band
Manual plans, 5-10 farms, one agronomist. The binding limit is fields, not acres.
- ESTIMATE: 1-6 wheat fields per farm, about 2-3 hours of agronomist review per farm at most. Target total across the pilot is about 10-40 fields. We will measure real time (`minutes_spent`), so treat this as a starting guess.
- Acres: do not set a hard band by acres. Free-text farm size on the form is unreliable. Qualify by "number of wheat fields in 2027" on the call. Avoid farms where wheat is a minor side crop on one field and farms with dozens of fields (anti-ICP).
- Farm-size distributions for Ontario and the Prairies: UNKNOWN, not sourced.

## 4. Soil-test habit
- **Must-have (3 of 5-8 farms):** a lab soil test from the last 3 years or a willingness to pull a fresh one before seeding, with the report available: method, depth, date, units, form. These farms test the full workflow. The "3 years" cutoff is an ESTIMATE; agronomist to confirm.
- **Nice-to-have:** field history (previous crop, last two years' N), prior-year yield range, field boundaries. Each field's history lets confidence rise.
- **At least 1-2 deliberate no-test farms:** N-only plan, max `medium` confidence, and an explicit recommendation to test P/K. These must also have a farmer who understands the limit up front. They test what happens with no soil test.
- Mixed testers (some fields tested, some not) are good: both paths in one conversation.
- Winter wheat spring-sample timing: a Feb-Mar plan may use fall-sampled data; the engine should record the sampling date (CLAUDE.md rule 7). Prairie source suggests spring pre-seed sampling is ideal and N shifts between fall and spring. [Top Crop Manager](https://www.topcropmanager.com/soil-sampling-and-testing-doing-it-right-17707/)

## 5. Who decides, who influences
- **Decides:** owner-operator (small/mid farms), or farm manager with owner sign-off. They fill in the website form, and they must agree to share data and receive an unproven product.
- **Influences:** their agronomist or retail advisor (fertilizer retailers often shape product and rate choices; the website positions CloverProof as an alternative to supplier-shaped advice). The advisor can block us if they see a threat. Ask early whether the advisor knows and agrees to see the plan.
- **Also:** custom applicator, lender/insurer (low), family partners.
- Split retail vs independent share by region: UNKNOWN. Do not claim any advisor endorses us.

## 6. Qualification checklist (yes/no)
Map to `pilot_request` fields: name, email, country, farm size (free text), main crop, notes. Call questions in italics.

| # | Criterion | Field / call question | Pass |
|---|---|---|---|
| 1 | Country is in the pilot region (Canada, then province per section 2) | `country`; *which province and county?* | yes |
| 2 | Main crop is wheat, and wheat is grown in 2027 | `main crop`; *winter or spring? How many wheat fields?* | yes |
| 3 | 1-6 wheat fields we can map and review (estimate band) | `farm size`; *field count and acres?* | yes |
| 4 | Has a lab soil test, or accepts N-only plan with a P/K test recommendation | `notes`; *do you have a test report, which lab, which date?* | yes |
| 5 | Can share data: field, previous crop, previous N, test report | *Can you send these by Jan 15?* | yes |
| 6 | Decision-maker is on the call, or the advisor is aware | `name`; *who signs off on N?* | yes |
| 7 | Understands every plan is reviewed before release, it is a pilot, and nothing is guaranteed | *Any expectations on results?* | yes |
| 8 | Valid email, consent to be contacted (CASL: implied consent only via their own request) | `email` | yes |

**Disqualifiers (any one):** no wheat in 2027; wants a fertilizer brand or product recommendation; needs a guaranteed yield or savings outcome; wants P/K rates without a lab test; crop other than wheat (engine v0 cannot serve it); region the pilot cannot serve; cannot provide field info by Jan 15; wants the farmer-facing app (not in scope).

## 7. Anti-ICP
- Retailers, distributors or any fertilizer sellers (conflicts with vendor neutrality). Treat their requests as non-pilot; advisors who want to see a plan for their own client can be kept as an influencer path, to be decided by the CRO.
- Large multi-hundred-field operations or enterprise buyers (manual process won't scale).
- Farms seeking an app, a live dashboard, automation, sensor or satellite features (out of scope).
- Non-wheat farms (barley, canola, corn, soy): later, not 2027 v0.
- Organic-only certification needs, or regulatory filings (nutrient management plan sign-off): we are not issuing certifications; the proof doc is a record, not a certification.
- Buyers wanting a payment-for-service price promise: pricing is undecided.

## Open decisions
1. ~~Pilot region~~ DECIDED 2026-11-16: Ontario primary, Prairie backup ("Both").
2. Final field-count band and agronomist hours per farm.
3. Number of no-test farms (draft: 1-2).
4. Whether to talk to farmer-side advisors, and how: CRO.
5. Gaps to research with the agronomist: Prairie spring N timing, advisor mix by region, farmer test frequency, current Ontario wheat area.
