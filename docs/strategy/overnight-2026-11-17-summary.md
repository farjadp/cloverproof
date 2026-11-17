# Strategy overnight research — summary and CSO review (2026-11-17)

Owner: `cso` via `market-research-analyst` (×3) and `business-strategist`. Desk research only: read-only browsing, no contact, no accounts. Every link was accessed 2026-11-17.

| File | What it answers |
|---|---|
| [market-sizing.md](market-sizing.md) | Ontario winter wheat acres by county, spend, soil testing, advisors, Prairie snapshot, TAM/SAM/SOM |
| [competitive-landscape.md](competitive-landscape.md) | 12 software and official tools: recs, records/proof, logs, multi-farm, pricing, gaps, threats, S3 corrections |
| [rnd-roadmap.md](rnd-roadmap.md) | Calibration science stages, ML sample-size gates, possible research partners, grant options, phased roadmap |
| [farmer-voice.md](farmer-voice.md) | 10 themes from public sources, anonymised paraphrases, interview questions |

## Key findings
- **Market size.** Ontario winter wheat is 0.93–1.18M seeded acres a year (2021–25). Southern and Western Ontario hold 82% of acres.
- **Farm count is UNKNOWN** (StatCan returned 403). Our ESTIMATE is 9k–18k farms.
- **TAM / SAM / SOM (ESTIMATE).** The prices are illustrations from competitor prices, not CloverProof prices.
  - TAM: $0.7–9.0M/yr.
  - SAM: $0.1–2.7M/yr.
  - SOM: 25–250 farms, which is $2k–125k per season.
  - One reviewer can serve about 67–960 farms per spring window, depending on minutes per plan.
- **Ontario winter wheat alone cannot carry a company.** It can carry a calibration dataset and an advisor wedge. Revenue needs more crops and the advisor channel.
- **Strongest incumbent missed in S3: OSCIA Soil Test Manager + AgriSuite.** Both are free and OMAFRA-based, and give N/P/K recs with a PDF, so our P/K job overlaps with theirs. No product we read shows a confidence level for each number or a hash-verified, immutable record. Our nearest advisor-workflow rival is Agworld; Nutrien is the retail rival.
- **There is still no public Ontario winter wheat N calculator.** The guidance is Agronomy Guide Table 4-14.
- **Farmer voice.**
  - In 2026, N price and supply shocks dominate fertilizer talk.
  - There is a gap between belief and practice: about 65% of farmers believe they follow 4R, but about 17% have a formal plan.
  - Concern about data sharing is real (44% uncomfortable).
  - Willingness to pay: no measured figure found.
- **R&D.**
  - With no human agronomist there is no usable evidence (D4).
  - The 2027 pilot is anecdote-scale: it can find bugs, but it cannot justify changing a constant.
  - ML is reasonable only after ESTIMATE ≥400 approved plans from ≥100 farms over ≥2 seasons, with ≥2 human reviewers. The earliest go/no-go is 2029.
  - Mitacs ($7,500 per unit, no deadline) is the realistic first grant. NSERC Alliance likely fails today (it needs ≥2 full-time staff).

## CSO review notes
- I checked all four files against CLAUDE.md:
  - no agronomic rates given as advice (Pub 60 figures are budget costs, $/ac, not rates);
  - no claims of endorsement or partnership (partners are "possible" only);
  - no "agronomist-reviewed";
  - no personal data and no verbatim quotes in farmer-voice.
- **Weak spots.** ontario.ca and statcan.gc.ca returned 403, so several figures come from search snippets and are labelled "snippet". Re-verify them in a browser before anything external (deck, website, grant application).
- **Fix needed in positioning.md.** The Canola Council link cited there returns 404, so the "most growers don't pay for independent agronomy" claim is unverified. The positioning file also needs the AgExpert price corrected: Premium is $399; $499 is the bundle with accounting.
- **Neutrality risk.** Fertilizer Canada-funded research and the Manitoba industry research chair: read their work, take no money and no co-branding until Farjad Iranmehr decides (R&D question 5).
- **Not done.** `docs/operations/grants-radar.md` is cited by the R&D roadmap but is not on `main` yet.

## Decisions / questions for Farjad Iranmehr
1. **Human agronomist of record (OQ-04), and by when.** This blocks the pilot evidence, calibration and every R&D track.
2. **Legal entity.** Is CloverProof a CCPC, and will it have ≥2 full-time staff in 2027–28? This decides NSERC Alliance, AgriScience and SR&ED eligibility.
3. **Mitacs approach.** OK to approach a Guelph researcher for a Mitacs project after the pilot (June 2027)? Outreach by you only.
4. **Yield record.** Should a post-harvest yield record be in 2027 scope, so the 2028 strip trials have a baseline?
5. **Industry co-funding.** Accept research partners co-funded by the fertilizer industry, or not (neutrality)?
6. **Second reviewer.** Can we recruit a second human reviewer for 2028?
