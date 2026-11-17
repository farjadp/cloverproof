# Market sizing: Ontario winter wheat (Prairie backup)

Owner: market-research-analyst for `cso`. Date: 2026-11-17. Internal only; never published. Access date for every source: 2026-11-17.
Labels: FACT (cited), ESTIMATE (my inference, assumptions shown), UNKNOWN. Prices are the reference points already in `billing-model-options.md`; CloverProof has no price yet. Costs below are published budget spend, never fertilizer rates or advice.
Method limits: statcan.gc.ca tables and pages returned HTTP 403 to my fetcher (Census tables 32-10-0416 and 32-10-0359 not read). Where a figure comes from a search snippet of a page I could not open, it says "snippet".

## 1. Ontario winter wheat: acres, farms, spend

**Acres seeded, Ontario (FACT)** ([OMAFRA/data.ontario.ca county file, updated 2026-06-25](https://data.ontario.ca/dataset/ontario-field-crop-area-and-production-estimates-by-county/resource/5af26019-30c2-4c97-b7bb-803817a3469c), accessed 2026-11-17; xlsx read directly):

| Year | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| Acres seeded | 1,081,600 | 930,300 | 1,107,701 | 1,008,900 | 1,183,700 |

5-year mean 1,062,440 (my arithmetic). Fall-seeding report for 2025 harvest agrees, 1.183M, +17.3% on 2024 ([Farms.com quoting StatCan](https://farms.com/news/correction-ontario-winter-wheat-area-planted-in-the-fall-up-from-a-year-ago-220981.aspx), accessed 2026-11-17). June "remaining" area is lower (1.12M for 2025, [Syngenta market news, snippet](https://syngenta.ca/market-news/2025-all-wheat-area-seen-up-2-6-)); measures differ. Insured: 801,900 acres in 2026 program year, but the page may cover all fall-seeded crops ([Agricorp](https://www.agricorp.com/en-ca/News/2025/Pages/2026-winter-wheat-insured-acres-county-maps-and-historical-data.aspx), accessed 2026-11-17). Ontario holds 76.1% of Canadian winter wheat farm area (Census 2021, [StatCan 96-325-X snippet](https://www150.statcan.gc.ca/n1/pub/96-325-x/2021001/article/00006-eng.htm)).

**By region, 2025 seeded acres (FACT, same file):** Western Ontario 497,898; Southern 477,377; Central 126,269; Eastern 57,771; Northern 24,385. Southern + Western = 82% (my arithmetic). Top 10 counties = 746,371 ac = 63% of Ontario: Lambton 102,782; Huron 100,900; Middlesex 83,213; Perth 82,165; Wellington 75,700; Simcoe 75,064; Chatham-Kent 68,161; Bruce 59,085; Essex 51,651; Haldimand-Norfolk 47,650.

**Farm count: UNKNOWN (published).** The Census table of farms reporting winter wheat was not readable. Context (FACT): 48,346 Ontario census farms in 2021, 11.77M acres, so about 243 acres per farm all-in ([StatCan 96-325-X via search](https://www150.statcan.gc.ca/n1/pub/96-325-x/2021001/article/00006-eng.htm); [OFA Local Snapshot](https://ofa.on.ca/wp-content/uploads/2023/03/local-snapshot-Essex.pdf), accessed 2026-11-17). Typical winter wheat acres per growing farm: UNKNOWN.
**ESTIMATE:** 1.06M ac / 60-120 ac winter wheat per growing farm (assumption; wheat is a rotation crop) = **~9,000-18,000 farms**. Validate with the Census table 32-10-0416 and Agricorp contract counts.

**Spend per acre (FACT, budget not survey):** OMAFA Pub 60 (2026), soft red winter wheat sample budget, grain only: fertility $107.85/ac for N, $54.45 P2O5, $18.60 K2O (P and K are crop-removal-based lines), total $180.90/ac; straw P/K adds $42.99 ([Pub 60 2026](https://www.ontario.ca/files/2026-01/omafa-field-crop-budgets-pub-60-en-2026-01-14.pdf), p.15, accessed 2026-11-17). "Considerable variation" is stated by OMAFA. ESTIMATE: N-only pool = 1.06M ac x $107.85 = ~$115M/yr; all grain fertility = ~$192M/yr. Actual StatCan farm-expense fertilizer data: UNKNOWN (not retrieved).

## 2. Soil testing
- Canada, all farms, Census 2020 reference year: 32.0% of farms reported soil sample testing; **Ontario 36.4%** (snippet of [StatCan Census release](https://www150.statcan.gc.ca/n1/daily-quotidien/220615/dq220615a-eng.htm), accessed 2026-11-17; universe is all farms, not wheat).
- Canada, field crop farms that applied fertilizer, Farm Management Survey 2021: 94% tested soil for nutrients, +4 points on 2017 (snippet of [StatCan FMS 2021](https://www150.statcan.gc.ca/n1/daily-quotidien/230217/dq230217f-eng.pdf)). Ontario-only FMS figure: UNKNOWN.
- Frequency, Canada, mixed crops (Fertilizer Canada 2024, n=1,258; Ontario sample is corn and soybean only, no wheat): over 55% test N and P every one to three years; N tested more often than P, P most commonly every three years ([Fertilizer Use Survey 2024](https://fertilizercanada.ca/wp-content/uploads/2026/03/Fertilizer-Use-Survey-National-Report-2024.pdf), p.12, accessed 2026-11-17). Self-reported, online, $25-50 incentive.
- Read: farms that test are the majority among fertilizer-applying field-crop farms; the 36% Ontario figure is a different universe. Ontario winter wheat test share: UNKNOWN. Fraction testing every year before the N decision: UNKNOWN.

## 3. Who advises today
- CCAs in Ontario: **540** (Dec 2015, Ontario CCA Association executive director, [Better Farming](https://www.betterfarming.com/magazines/better-farming-ontario/featured-articles/ontario-crop-advisor-organization-to-offer-nm-planning-specialist-certification-in-2016), accessed 2026-11-17). Current count UNKNOWN; 10 years old.
- 4R Certified retail sites in Ontario: 28 full-service (older source, from `competitor-scan.md`); 29 more at pre-audit stage (undated, [Farms.com](https://www.farms.com/news/fertilizer-canada-releases-updated-guidance-to-strengthen-4r-planning-243200.aspx)). 4R Designated Agronomists: UNKNOWN. Independent consultants: UNKNOWN.
- Demand side (Canada, 2024): 35.8% of growers work with a 4R Certified retailer or agronomist; 17.3% have a formal 4R plan; 79.6% have none ([Fertilizer Canada 2024](https://fertilizercanada.ca/wp-content/uploads/2026/03/Fertilizer-Use-Survey-National-Report-2024.pdf), p.10).

## 4. Prairie backup snapshot
- Wheat, June 2025 seeded: Manitoba 3.3M ac (+1.9%); Saskatchewan 14.0M; Alberta 8.1M ([StatCan principal field crop areas, June 2025](https://www.statcan.gc.ca/o1/en/app/8263-principal-field-crop-areas-june-2025), accessed 2026-11-17). Winter wheat is minor there.
- Manitoba: 14,543 farms, average 1,177 ac, 11.6M ac cropland ([Manitoba Ag census profile 2021](https://www.gov.mb.ca/agriculture/markets-and-statistics/ag-census/pubs/census-manitoba-profile-2021.pdf)). Spring wheat is the second-ranked crop by farm count. Wheat farm count: UNKNOWN. ESTIMATE: at 300-600 wheat ac per wheat farm, ~5,500-11,000 farms (assumption).
- Soil testing, Manitoba: 92% of field crop producers tested in 2021; among fertilizer + GPS-variable-rate users 98% test, 74% yearly, 18% every 2-3 years ([MB Agriculture, FMS 2021 summary](https://www.gov.mb.ca/agriculture/markets-and-statistics/economic-analysis/pubs/adoption-of-sustainable-farming-practices-in-manitoba.pdf)). SK and AB shares: UNKNOWN. Implication: Prairie growers test more but farms are 5x larger, so fewer farms and more fields per farm; the capacity constraint binds harder.

## 5. TAM / SAM / SOM (Ontario winter wheat, per season)

Price points, ESTIMATE, taken from `billing-model-options.md`: $75 per farm-season (the doc's low-end cost illustration, 2 fields x 15 min at $150/h, a cost not a price); $399 and $499 per year (AgExpert Premium and FieldView, competitor references). These are not CloverProof prices; per-farm unit follows option A/D.

**TAM = all Ontario winter wheat farms x price.** 9,000-18,000 farms (section 1, ESTIMATE).
- $75: $0.7M-$1.4M. $399: $3.6M-$7.2M. $499: $4.5M-$9.0M. **Range ~$0.7M-$9.0M/yr.**

**SAM = TAM farms x regions we can serve x share already working with documented advice.**
- Southern + Western Ontario = 82% of acres (FACT). Share inclined to a documented decision: proxy 17%-36% (formal 4R plan holders to those working with certified advice; Canada 2024, not wheat-specific, ESTIMATE as a proxy).
- Farms: 9,000 x 0.82 x 0.17 = ~1,250 (low); 18,000 x 0.82 x 0.36 = ~5,300 (high).
- $75: $0.09M-$0.40M. $399: $0.5M-$2.1M. $499: $0.6M-$2.7M. **Range ~$0.1M-$2.7M/yr.**

**SOM = what one agronomist can review.** Capacity formula: plans = (review hours per season x 60) / minutes per plan; farms = plans / fields per farm. Window Feb-Apr (~12 weeks). Reviewer minutes per plan: UNKNOWN (pilot measures it, `review.minutes_spent`); fields per farm: 1-6 (pilot ICP ESTIMATE).

| Scenario | Hours/week on review | Min/plan | Fields/farm | Plans | Farms |
|---|---|---|---|---|---|
| Light (part-time) | 25 (300 h) | 45 | 6 | 400 | ~67 |
| Mid | 25 (300 h) | 25 | 3 | 720 | ~240 |
| Heavy (full-time) | 40 (480 h) | 15 | 2 | 1,920 | ~960 |

Demand check: pilot is 5-10 free farms; paid prep is Nov 2027, so the first paid season is spring 2028. ESTIMATE of paid uptake: 2%-5% of SAM = ~25-265 farms (assumption; no conversion data exists). **Realistic SOM = ~25-250 farms**, capacity-bound at the top by the mid scenario.
- $75: ~$2k-$19k. $399: ~$10k-$100k. $499: ~$12k-$125k. **Range ~$2k-$125k per season.**

Sensitivity: SOM revenue moves 1:1 with price and uptake, but capacity depends on minutes per plan (9x between light and mid at the same hours). One variable decides it: minutes per plan. Note review today is an AI agent; with a human agronomist as sign-off (CLAUDE.md rule 8) the "heavy" scenario is the ceiling, not the plan. Fee context: $399 on a 100-ac farm = ~$4/ac against ~$108/ac N budget line (ESTIMATE arithmetic).

Challenge: at this size, Ontario winter wheat alone does not support a company; it supports a calibration dataset and an advisor wedge. Revenue depends on adding crops (corn, soybean) and the advisor channel, which the TAM above excludes.

## 6. UNKNOWN list
1. Number of Ontario farms growing winter wheat; winter wheat acres per farm (Census table 32-10-0416; Agricorp contracts).
2. Ontario winter wheat soil-test share and annual-testing share; Ontario-only FMS 2021.
3. Actual farm-expense fertilizer spend per acre (StatCan), versus the Pub 60 sample budget.
4. Current CCA count in Ontario; number of 4R Designated Agronomists; independent consultants.
5. SK and AB soil-test shares and wheat farm counts; MB wheat farm count.
6. Willingness to pay, payer (grower vs advisor), uptake rate: no data; pilot and beta hypotheses only.
7. Reviewer minutes per plan and fields per farm: pilot measurements.
8. Winter wheat acres per growing farm and field-count distribution (drives farm-count estimate).
