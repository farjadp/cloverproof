# CloverProof content plan: Ontario winter wheat, 2026-27

Owner: Content & SEO strategist (agent draft). Status: DRAFT, 2026-11-17. Nothing here is published; the website has no blog yet.
Every article in this plan is marked "DRAFT — needs human agronomist review before publishing". Reviewer box on every article: "Reviewer: [to be named]".

## 0. Baseline and constraints

- **Site today:** one Next.js landing page per locale (`/en`, section anchors `#how`, `#proof`, `#principles`, `#faq`, `#check`, `#pilot`) and a draft privacy page (noindex). `website/src/app/sitemap.ts` lists locale roots only. There is no blog route, no Article schema and no author pages.
- **Before any article can go live (engineering, not this plan):** a `/[lang]/learn/[slug]` route (proposed path), sitemap entries per article, Article + BreadcrumbList + FAQPage JSON-LD, a visible "last reviewed" date, an author/reviewer box component, and canonical/hreflang for `en` only until translations exist (ADR 0003 covers multi-language).
- **Landing copy (CPO ruling, 2026-11-17):** the site's "approved by a human agronomist" lines describe the enforced process (rule 8) and are not a rule-11 breach; no change. **Guard for every article:** never claim that a named agronomist or partner already reviews plans, and never claim that any plan has been delivered.
- **Hard rules for every article:** no rates, thresholds or yield numbers as advice; point to OMAFA Publication 811 for numbers. No yield or savings promises. No claim that any third party (OMAFA, GFO, Fertilizer Canada, a lab, a lender) approves or accepts CloverProof or its proof PDF. Do not say "agronomist-reviewed" about CloverProof content or plans. CloverProof is vendor-neutral and software only.
- **Keyword data:** no Search Console, Ahrefs or DataForSEO source is connected. Every volume is "volume unknown". Queries are phrased the way growers and CCAs search, taken from extension article titles, People-Also-Ask style questions and the pilot ICP's call questions. Priority = pilot-recruitment value + intent fit + how thin the existing answers are.

## 1. Source register (only sources I fetched or found)

| ID | Source | Status | What it supports |
|---|---|---|---|
| S1 | OMAFA, *Publication 811: Agronomy Guide for Field Crops* (landing page) https://www.ontario.ca/page/agronomy-guide-field-crops | fetched | Chapter list, links to chapter PDFs |
| S2 | Pub 811 Chapter 4, Cereals (2022 PDF) https://www.ontario.ca/files/2022-10/omafra-agronomy-guide-for-field-crops-chapter-4-en-2022-10-13.pdf | fetched, text read | Verified table titles: 4-10 *Management considerations for wheat following various crops in rotation*; 4-13 *Nitrogen requirements for cereal crops*; 4-14 *Nitrogen requirements for pastry wheat (most profitable N application)*, read by N:wheat price ratio and expected yield; 4-15 *Managing for increased protein*; 4-16 *Fall-applied nitrogen*; 4-20 *Phosphate (P2O5) guidelines for cereals*; 4-21 *Potash (K2O) guidelines for cereals* (both "based on OMAFRA-accredited soil tests"). Text: fall N "strongly discouraged"; disease control, lodging and fungicide cost shape the economic N rate; split N raises protein but often not economically |
| S3 | Pub 811 Chapter 9, Soil Fertility and Nutrient Use (2022 PDF) https://www.ontario.ca/files/2022-10/omafra-agronomy-guide-for-field-crops-chapter-9-en-2022-10-13.pdf | fetched, text read | Table 9-1 *OMAFRA-accredited soil tests*; Table 9-9 *Adjustment of nitrogen requirement, where crops containing legumes are plowed down*; Table 9-15 *Average nutrient (N, P2O5, K2O) removal by common field crops*. Text: Olsen for P, ammonium acetate for K and Mg; results in mg/L or ppm, "approximately equal"; Olsen pH 8.5 vs Bray-1/Bray-2/Mehlich-3 pH 2.5; Bray or Mehlich-3 P "cannot be used" with Pub 811 fertility tables; Mehlich-3 K comparable to ammonium acetate; sampling depth 15 cm (6 in), nitrate 30 cm (12 in), pH in continuous no-till 10 cm (4 in); "once every 3 years is adequate" for most farms, same point in the rotation; sample at the same time of year; P to P2O5 x 2.29 and K to K2O x 1.2 (used in the manure worksheet) |
| S4 | Field Crop News (OMAFA), Colin Elgie, "OMAFA-Accredited Soil Testing Program", May 2025 https://fieldcropnews.com/2025/05/omafa-accredited-soil-testing-program/ | fetched | Eight accredited tests (pH, buffer pH SMP or Sikora, Olsen P, ammonium acetate K and Mg, Zn and Mn indices, KCl nitrate-N); program run with NAPT; "OMAFA-accredited soil tests will provide the most accurate fertilizer guidelines for Ontario field crops." |
| S5 | Field Crop News (OMAFA), Joanna Follings, "Should I split apply nitrogen in winter wheat?", Mar 2022 https://fieldcropnews.com/?p=24016 | fetched | Split N depends on year and field; late-planted or poorly tillered fields vs early-planted, heavily tillered or lodging-prone fields (delay to about GS30); loss risk on sand and clay; single pass limits flexibility; extra pass costs money |
| S6 | Grain Farmers of Ontario, Crop Management page https://gfo.ca/agronomy/crop-management | fetched | GFO publishes a winter wheat staging guide (download) |
| S7 | Ontario.ca, "Interpreting your soil test results" https://ontario.ca/page/interpreting-your-soil-test-results | found, fetch blocked (403) | Cite only after a human opens and checks it |
| S8 | Fertilizer Canada, *4R Nutrient Stewardship* brochure https://fertilizercanada.ca/wp-content/uploads/2015/11/4R-Brochure.pdf | found; PDF text not extractable | Right source, right rate, right time, right place. Verify exact wording before quoting |
| S9 | Fertilizer Canada, *Fertilizer Use Survey National Report 2024* https://fertilizercanada.ca/wp-content/uploads/2026/03/Fertilizer-Use-Survey-National-Report-2024.pdf | found (via search summary) | Soil-test frequency trend; 4R Designated Agronomists as advisers. Verify any number before use |
| S10 | Fertilizer Canada, *4R Certification Standards 2026* https://fertilizercanada.ca/wp-content/uploads/2026/07/4R-Certification-Standards-2026.pdf | found | Ontario 4R Certification for nutrient service providers |
| S11 | AAFC, "Managing nitrogen use efficiently" https://agriculture.canada.ca/en/node/3791 | found | Source, rate, placement and timing as the N-efficiency levers (AAFC research framing) |
| S12 | Grain Farmers of Ontario, "Nitrogen management on wheat: Production, environmental and quality implications" https://gfo.ca/?p=60308 | found | GFO-funded N research summary; read before citing |
| S13 | Ontario Grain Farmer, "Split apply nitrogen", Mar 2022 https://ontariograinfarmer.ca/2022/03/01/split-apply-nitrogen/ | found | Split-N framing, OMAFA cereals specialist |
| S14 | University of Guelph news, "U of G researcher receives funding to develop more sustainable wheat" https://news.uoguelph.ca/u-of-g-researcher-receives-funding-to-develop-more-sustainable-wheat | found | Ongoing Ontario winter wheat N research (rates, timing, sources). Context only; no results yet |
| S15 | Field Crop News, "Nitrogen (N)" https://fieldcropnews.com/?p=18991 | found | General N background; read before citing |
| S16 | Farms.com (OMAFA specialist), "Winter wheat fertilizer application reminders" https://www.farms.com/news/winter-wheat-fertilizer-application-reminders-121205.aspx | found (cited in `pilot-icp.md`) | Early spring N timing framing. Secondary source; prefer S2/S5 |

Rule: an article may cite a "found" source only after a human (author or reviewer) has opened it and confirmed the statement. "Fetched" sources were read for this plan; table titles in S2/S3 were checked against the PDF text.

## 2. Cluster map

```
PILLAR A  Spring N for Ontario winter wheat (decision process)   -> /en#how, /en#check
  A1 Planning spring N: the decision, step by step   [draft-02]
  A2 Split N timing: the concepts behind one pass vs two
  A3 Previous crop and wheat N: what changes and why
  A4 Why fall N on winter wheat is discouraged in Ontario
  A5 Growth stages that matter for N decisions (staging)

PILLAR B  Soil tests for fertilizer decisions                    -> /en#check, /en#proof
  B1 How to read an Ontario soil test report     [draft-01]
  B2 Why the extraction method matters (Olsen vs Mehlich-3 vs Bray)
  B3 No soil test: what can and cannot be planned
  B4 Units: P vs P2O5, K vs K2O, ppm vs mg/L, lb/ac vs kg/ha
  B5 When and how often to sample before wheat

PILLAR C  Proof, records and trust                               -> /en#proof, /en#pilot
  C1 Record-keeping: proof of fertilizer decisions
  C2 What a confidence level on a fertilizer plan means
  C3 Vendor-neutral fertilizer advice: what it is, what to ask
  C4 4R nutrient stewardship basics for wheat growers
  C5 How to prepare field data for your advisor (checklist)

HUB  Glossary of fertilizer-planning terms (DefinedTermSet)      -> links to every article
```

Every spoke links up to its pillar and across to two siblings; the glossary links each term to the article that explains it. Pillars A and B link to each other at the "inputs" step.

## 3. Publishing order (pilot-recruitment value first)

Pilot farms must be confirmed by Jan 15, 2027; plans are produced Feb-Apr 2027. Slots are planned dates, not publish dates. A post's publish date is the day it actually goes live after review; never backdate.

| # | Planned slot | Article | Why this slot |
|---|---|---|---|
| 1 | Dec 1, 2026 | B1 Read an Ontario soil test report | Recruit: qualifies the "do you have a test?" question; feeds `#check` |
| 2 | Dec 1, 2026 | C5 Prepare field data for your advisor | Recruit: the exact data list the pilot asks for by Jan 15 |
| 3 | Dec 8, 2026 | A1 Planning spring N, step by step | Recruit + core intent before top-dress season |
| 4 | Dec 15, 2026 | B3 No soil test: what can be planned | Recruit: no-test farms are a deliberate pilot segment |
| 5 | Dec 22, 2026 | C2 What a confidence level means | Explains the product's core promise honestly |
| 6 | Jan 5, 2027 | C1 Record-keeping and proof of decisions | Explains `#proof` |
| 7 | Jan 12, 2027 | C3 Vendor-neutral advice | Positioning; advisor audience |
| 8 | Jan 19, 2027 | B2 Why the extraction method matters | Supports B1; CCA audience |
| 9 | Jan 26, 2027 | B4 Units: P vs P2O5, K vs K2O | Evergreen; high AI-answer citability |
| 10 | Feb 2, 2027 | A2 Split N timing concepts | Seasonal: top-dress planning |
| 11 | Feb 9, 2027 | A3 Previous crop and wheat N | Seasonal |
| 12 | Feb 16, 2027 | A5 Growth stages for N decisions | Seasonal, just before green-up |
| 13 | Feb 23, 2027 | A4 Why fall N is discouraged | Seasonal myth-buster |
| 14 | Mar 2, 2027 | C4 4R basics for wheat growers | Advisor audience |
| 15 | Mar 9, 2027 | B5 When and how often to sample | Sets up fall 2027 sampling |
| 16 | Mar 16, 2027 | Glossary hub | Ties the cluster together; can start earlier as a stub |

Cadence: one per week; two in week 1 to give outreach something to link. If review capacity is short, slots 1-6 come first and the rest slide.

## 4. Measurement and refresh

Per article: Search Console impressions, clicks, average position for the primary and related queries; `cta_click` and `pilot_request` attributed via `utm_*` and `referrer_host` (per `landing-tracking-brief.md`); monthly manual check of whether Google AI Overviews, ChatGPT search and Perplexity cite the article for its primary query (log the date, engine, query, cited or not). Refresh triggers: a new Pub 811 edition or table change, a new Field Crop News item on the topic, the article dropping below its 4-week average position, or every March before top-dress season.

UTM for links to articles from outreach: same conventions as the landing brief, `utm_campaign=pilot-2027-wheat`, `utm_content=<asset-code>-<article-slug>` (no personal names). Article CTAs to the landing page carry no UTM (internal links); attribution comes from `referrer_host` plus path.

## 5. Schema suggestions

- **Every article:** `Article` (headline, description, datePublished, dateModified, author as `Organization` CloverProof until a named author exists, `publisher` CloverProof, `inLanguage: en-CA`, `about` with the main entity, `citation` list of the sources used), `BreadcrumbList` (Home > Learn > Article).
- **FAQ sections:** `FAQPage` with the same questions and answers shown on the page. Google shows FAQ rich results only for a narrow set of sites now, but the markup still helps machines parse the Q&A. Never mark up questions that are not visible.
- **Glossary:** `DefinedTermSet` with one `DefinedTerm` per entry (`name`, `description`, `url` with anchor, `inDefinedTermSet`). Articles can reference terms via `mentions`.
- **Checklist article (C5):** `HowTo` is no longer shown as a rich result; use `Article` plus an ordered list.
- **Do not use:** `MedicalWebPage`, `Review`, `AggregateRating`, `reviewedBy` with a person, or `Product` offers. `reviewedBy` is added only when a named human reviewer has actually reviewed the article.
- **Entity:** one `Organization` node for CloverProof sitewide (name, url, logo, description "Vendor-neutral software for field-specific fertilizer plans", `areaServed` Ontario for the pilot). Use the same description everywhere.

## 6. AIO / GEO / AEO rules (apply to every article)

1. **Answer first.** A 40-60 word direct answer right under the H1, written to stand alone if quoted.
2. **One question per H2**, phrased the way a grower asks it. First sentence under each H2 answers it.
3. **Cited facts only.** Each factual sentence that an engine might lift carries its source inline (publisher + title, linked). Numbers come only from the source, attributed ("Publication 811 says..."), and are never phrased as a recommendation.
4. **Point to the table, don't copy it.** "See Pub 811 Chapter 4, Table 4-14" where the table title was verified (section 1); otherwise cite the chapter.
5. **Entity clarity.** Name the organisation in full on first use: Ontario Ministry of Agriculture, Food and Agribusiness (OMAFA; formerly OMAFRA). Name CloverProof once in the body and once in the CTA, with the same one-line description.
6. **Freshness.** Show "Published" and "Last checked against sources" dates. Re-check each March.
7. **Author/reviewer box** on every article:
   > Written by: CloverProof team · Reviewer: [to be named] · Last checked against sources: [date]
   > This article explains a decision process. It does not give fertilizer rates. For numbers, see OMAFA Publication 811 or ask your advisor.
8. **Status line** until a named human agronomist reviews it: "DRAFT — needs human agronomist review before publishing." Remove only after that review; replace with the review date.
9. **Tables and lists** where they help scanning (inputs, what's on a report), short paragraphs, no filler.
10. **No AI-spam patterns:** no "in today's fast-paced world", no doorway variants per county, no keyword stuffing. Run `humanizer` as the last pass.
11. **llms.txt:** not justified yet (one landing page). Revisit when 6+ articles are live.
12. **Robots:** confirm AI crawlers (GPTBot, PerplexityBot, Google-Extended) are allowed in `robots.ts` before publishing; this is a policy decision for Farjad Iranmehr.

Common CTA block (vary the first line per article):
> CloverProof is building field-specific fertilizer plans for Ontario winter wheat in 2027: what, how much, when and why, with a confidence level and a proof PDF. Software only, vendor-neutral. [Try the 2-minute field check](/en#check) · [Request a pilot plan](/en#pilot)

## 7. Article briefs

Format per brief: title · intent · queries (primary + related; all volume unknown) · outline · FAQ · sources · internal links · CTA.

### A1. Planning spring nitrogen for Ontario winter wheat: the decision, step by step  [DRAFTED: draft-02]
- **Intent:** informational, mid-funnel (grower planning top-dress; CCA explaining to a client).
- **Primary:** "how to decide nitrogen rate for winter wheat Ontario". **Related:** "spring nitrogen winter wheat Ontario"; "when to top dress winter wheat"; "winter wheat nitrogen calculator Ontario"; "what affects nitrogen rate in wheat"; "OMAFRA winter wheat nitrogen recommendation".
- **Outline:** H2 What goes into a spring N decision? · H2 Step 1: confirm the field and crop facts (class, seeding date, stand) · H2 Step 2: gather soil and history inputs · H2 Step 3: set the yield goal and economics (what Pub 811 Table 4-14 reads from) · H2 Step 4: decide one pass or split · H2 Step 5: adjust for disease plan and lodging risk · H2 Step 6: write down the decision and why · H2 Where the numbers come from · FAQ.
- **FAQ:** Can I put nitrogen on winter wheat in the fall? · Does the previous crop change wheat N? · Should I split spring N? · Does a fungicide plan change the N decision? · Where do I find Ontario N rate tables? · Does hard red wheat need a different plan?
- **Sources:** S2, S3, S5, S6, S13.
- **Internal links:** A2, A3, A4, A5, B1, B3, C1, C2; `/en#how`, `/en#check`.
- **CTA:** "Want this written out for each field, with the reason for every number?" → `#check`, `#pilot`.

### A2. Split nitrogen on winter wheat: the concepts behind one pass vs two
- **Intent:** informational, seasonal (Feb-Apr).
- **Primary:** "should I split apply nitrogen on winter wheat". **Related:** "split nitrogen winter wheat Ontario"; "GS30 nitrogen wheat"; "early nitrogen thin wheat stand"; "nitrogen and lodging wheat"; "split N protein wheat".
- **Outline:** H2 What is a split N application? · H2 Which field conditions favour an early first pass? · H2 Which favour waiting? · H2 What does soil type change? (loss risk) · H2 What does a split cost? · H2 Protein vs yield: what Ontario research says (cite Pub 811 Table 4-15 by title, no numbers) · FAQ.
- **FAQ:** Does splitting always pay? · What is GS30? · Does soil type matter for early N? · Can I add sulphur with the first pass? · Does split N raise protein?
- **Sources:** S5, S2 (Tables 4-13, 4-15), S13, S6.
- **Links:** A1, A5, C2; `#how`.
- **CTA:** "A CloverProof plan records the timing window and why it was chosen." → `#proof`.

### A3. Previous crop and winter wheat nitrogen: what changes and why
- **Intent:** informational.
- **Primary:** "wheat after soybeans nitrogen". **Related:** "wheat after corn nitrogen Ontario"; "nitrogen credit previous crop wheat"; "red clover nitrogen credit wheat"; "manure and wheat nitrogen"; "wheat after edible beans".
- **Outline:** H2 Why the previous crop matters for N · H2 Residual N and residue (concepts) · H2 Legume sod and manure · H2 Planting date knock-on effects · H2 Where to find the adjustments (Pub 811 Table 4-10; Table 9-9) · H2 What to record · FAQ.
- **FAQ:** Do soybeans leave nitrogen for wheat? · How does manure history change the plan? · Does red clover underseeding matter? · Why does previous crop change lodging risk? · What should I write down about history?
- **Sources:** S2 (Table 4-10), S3 (Table 9-9; manure section), S5.
- **Links:** A1, C5, C1; `#check`.
- **CTA:** field check → `#check`.

### A4. Why fall nitrogen on winter wheat is discouraged in Ontario
- **Intent:** informational, myth-busting.
- **Primary:** "fall nitrogen winter wheat". **Related:** "should I put nitrogen on wheat in the fall"; "starter fertilizer winter wheat nitrogen"; "fall applied N wheat Ontario research".
- **Outline:** H2 What Pub 811 says · H2 What happens to fall N over winter (concept) · H2 The starter exception · H2 What to do instead · FAQ.
- **FAQ:** Is starter N with phosphorus the same thing? · Does fall N help tillering? · What did the Ontario trials compare (Table 4-16, by title)? · When does spring N go on?
- **Sources:** S2 (Table 4-16 and text), S16.
- **Links:** A1, A2.
- **CTA:** `#how`.

### A5. Winter wheat growth stages that matter for nitrogen decisions
- **Intent:** informational, seasonal.
- **Primary:** "winter wheat growth stages Ontario". **Related:** "Zadoks scale wheat"; "GS30 wheat"; "green-up winter wheat nitrogen"; "winter wheat staging guide".
- **Outline:** H2 Why staging drives timing · H2 Green-up and tillering · H2 GS30-GS32 · H2 Later applications (concept) · H2 Where to get a staging guide (GFO) · FAQ.
- **FAQ:** What is green-up? · How do I identify GS30? · Does staging differ by field? · Can growing degree days predict stages?
- **Sources:** S6, S5, S2.
- **Links:** A1, A2.
- **CTA:** `#proof` (timing window shown on the proof).

### B1. How to read an Ontario soil test report before you plan fertilizer  [DRAFTED: draft-01]
- **Intent:** informational, top-to-mid funnel; grower with a lab report.
- **Primary:** "how to read a soil test report Ontario". **Related:** "Olsen phosphorus soil test"; "ammonium acetate potassium soil test"; "soil test ppm vs mg/L"; "OMAFRA accredited soil test labs"; "what soil sampling depth for soil test".
- **Outline:** H2 What's on a typical Ontario report? · H2 Which extraction method was used? · H2 What units are the numbers in? · H2 How deep and when was it sampled? · H2 Is it from an accredited test? · H2 How the report connects to fertilizer tables · H2 What to send your advisor · FAQ.
- **FAQ:** Can I use a Mehlich-3 report with Ontario tables? · How old can my soil test be? · Is ppm the same as mg/L? · Does a soil test tell me how much nitrogen to apply? · Where do I find accredited labs?
- **Sources:** S3, S4, S2, S7 (after check).
- **Links:** B2, B3, B4, B5, C5, A1; `#check`, `#proof`.
- **CTA:** "Have a report? The 2-minute field check shows what a plan could cover." → `#check`.

### B2. Why the soil test extraction method matters: Olsen, Mehlich-3 and Bray
- **Intent:** informational; CCA and grower using a US or non-accredited lab.
- **Primary:** "Olsen vs Mehlich 3 phosphorus". **Related:** "Bray P1 vs Olsen"; "Mehlich 3 Ontario recommendations"; "soil test methods phosphorus potassium"; "why do different labs give different soil test results".
- **Outline:** H2 What an extractant is · H2 Why Ontario uses Olsen for P · H2 What happens on alkaline soils · H2 Potassium: ammonium acetate and Mehlich-3 · H2 Can you convert between methods? (say: Pub 811 doesn't provide a conversion for its tables; ask advisor) · H2 What to record on every test · FAQ.
- **FAQ:** Can I convert Mehlich-3 P to Olsen? · Is Mehlich-3 K usable? · Why does pH of the extractant matter? · Which tests are accredited? · What if my lab didn't print the method?
- **Sources:** S3, S4.
- **Links:** B1, B4, C2.
- **CTA:** `#check`.

### B3. No soil test? What a fertilizer plan can and cannot cover
- **Intent:** informational + commercial (directly matches the pilot's no-test path).
- **Primary:** "fertilizer plan without soil test". **Related:** "can I fertilize wheat without a soil test"; "nitrogen without soil test"; "do I need a soil test for winter wheat"; "how much does a soil test cost Ontario" (answer: ask labs; no number).
- **Outline:** H2 Why N can be planned without a lab test (field history drives it) · H2 Why P and K need a test · H2 What estimates can and can't do · H2 How confidence changes · H2 When to get a test before the next crop · FAQ.
- **FAQ:** Will a plan without a test be less certain? · Why not estimate P and K from maps? · Can I test this spring? · What do I send instead of a test?
- **Sources:** S2 (Tables 4-20, 4-21 are "based on OMAFRA-accredited soil tests"), S3, S4.
- **Links:** B1, B5, C2, C5; `#check`, `#pilot`.
- **CTA:** "No test? The pilot can still plan nitrogen, at medium confidence at most, and will tell you what to test." → `#pilot`. (Matches the site FAQ.)

### B4. P vs P2O5, K vs K2O: fertilizer units without the confusion
- **Intent:** informational, evergreen, highly citable.
- **Primary:** "P vs P2O5". **Related:** "convert P to P2O5"; "K to K2O conversion"; "lb/ac to kg/ha fertilizer"; "ppm to lb/acre soil test"; "elemental vs oxide fertilizer".
- **Outline:** H2 Why fertilizer is labelled as oxides · H2 The conversion factors (P x 2.29 = P2O5; K x 1.2 = K2O, as used in Pub 811's manure worksheet; chemistry, not advice) · H2 Soil test units vs fertilizer units · H2 Rate units: lb/ac and kg/ha · H2 Mistakes that cause wrong numbers · FAQ.
- **FAQ:** Is a 0-46-0 bag 46% P? · Is soil test ppm the same as lb/ac? · Which unit does Pub 811 use for P and K guidelines? · Why does my plan show both?
- **Sources:** S3, S2 (Tables 4-20 P2O5, 4-21 K2O).
- **Links:** B1, B2, glossary.
- **CTA:** "CloverProof stores the form on every nutrient line, so P and P2O5 never get mixed up." → `#proof`.

### B5. When and how often to soil sample before winter wheat
- **Intent:** informational, planning.
- **Primary:** "when to soil sample for winter wheat". **Related:** "how often should I soil test"; "fall or spring soil sampling Ontario"; "soil sampling depth Ontario"; "how many cores per soil sample".
- **Outline:** H2 How often (Pub 811 guidance, attributed) · H2 Time of year and consistency · H2 Depth · H2 Banded fertilizer and no-till cautions (Table 9-2 by title) · H2 What to record per sample · FAQ.
- **FAQ:** Is a 4-year-old test too old? · Fall or spring? · Same depth every time? · Do I sample differently in no-till?
- **Sources:** S3.
- **Links:** B1, B3, C5.
- **CTA:** `#check`.

### C1. Fertilizer record-keeping: how to keep proof of your decisions
- **Intent:** informational + commercial (explains the proof PDF).
- **Primary:** "fertilizer record keeping for farms". **Related:** "fertilizer application records template"; "how to document nutrient management decisions"; "4R record keeping"; "why keep fertilizer records".
- **Outline:** H2 What a useful record contains (inputs, sources and dates, the decision, who approved, the reason for any change) · H2 Planned vs applied · H2 Why versions matter (never overwrite) · H2 What a record is not (not a certification) · H2 Formats that work · FAQ.
- **FAQ:** Is a proof document a certification? · Who can I share it with? · What if I change the rate on the day? · How long should I keep records?
- **Sources:** S8, S10 (4R framing; verify), S3.
- **Links:** C2, C3, C4, C5; `#proof`.
- **CTA:** "See a sample proof document." → `#proof`. Must say: "It is not a certification and no third party has endorsed it" (matches site FAQ).

### C2. What a confidence level on a fertilizer plan means
- **Intent:** informational; product-adjacent.
- **Primary:** "how confident is my fertilizer recommendation". **Related:** "fertilizer recommendation uncertainty"; "high medium low confidence fertilizer plan"; "how accurate are fertilizer recommendations".
- **Outline:** H2 Why any recommendation carries uncertainty · H2 What raises confidence (lab test, method, history) · H2 What lowers it (no test, estimates, missing history) · H2 How CloverProof labels it (rule-based high/medium/low; no test = N only, max medium) · H2 What to do with a low-confidence line · FAQ.
- **FAQ:** Is "medium" bad? · Why no P/K without a test? · Is confidence a statistical probability? (No: rule-based label) · Can confidence change mid-season?
- **Sources:** S3 (accredited test accuracy statement), S4. Product facts from CLAUDE.md rules 2-3.
- **Links:** B1, B3, C1; `#how`, `#proof`.
- **CTA:** `#check`.

### C3. Vendor-neutral fertilizer advice: what it means and what to ask
- **Intent:** commercial investigation; grower and independent agronomist.
- **Primary:** "independent agronomist Ontario". **Related:** "unbiased fertilizer recommendations"; "independent crop advisor vs retailer"; "questions to ask your agronomist"; "certified crop adviser Ontario".
- **Outline:** H2 What vendor-neutral means · H2 Where advice comes from in Ontario (retail, independent, extension) without disparaging anyone · H2 Questions to ask any advisor (inputs, source tables, reasoning, records) · H2 How CloverProof stays neutral (no product sales, no commissions; generic products) · FAQ.
- **FAQ:** Is retail advice biased? (neutral answer: ask how the number was made) · Do you sell fertilizer? · Do you replace my agronomist? · Can my advisor see the plan?
- **Sources:** S9 (advisers), S10.
- **Links:** C1, C4, C5; `#principles`, `#pilot`.
- **CTA:** `#pilot`. No claim of endorsement by any advisor group.

### C4. 4R nutrient stewardship basics for Ontario wheat growers
- **Intent:** informational; advisor and sustainability-program audience.
- **Primary:** "what is 4R nutrient stewardship". **Related:** "4R right source right rate right time right place"; "4R certified retailer Ontario"; "4R designated agronomist"; "4R nitrogen wheat".
- **Outline:** H2 The four Rs in one paragraph · H2 What each R means for spring N on wheat · H2 4R Certification vs 4R Designation (Fertilizer Canada programs) · H2 Where records fit · FAQ.
- **FAQ:** Is 4R a regulation? · Who runs 4R in Ontario? · Does a CloverProof plan make me 4R certified? (No) · How do I find a 4R Designated Agronomist?
- **Sources:** S8, S10, S9, S11.
- **Links:** A1, C1, C3.
- **CTA:** `#how`.

### C5. How to prepare your field data for an advisor: a checklist
- **Intent:** transactional-adjacent; directly mirrors the pilot data request.
- **Primary:** "what information does my agronomist need". **Related:** "field records checklist fertilizer plan"; "how to prepare for an agronomy consultation"; "farm field history template".
- **Outline:** H2 The short list (field name/location, crop and class, seeding date, previous crop, last two years' N and manure, soil test report with method/depth/date/units, yield history if known) · H2 How to send a soil report (whole PDF, not a retyped table) · H2 What to leave out (personal data you don't need to share) · H2 What happens next · FAQ.
- **FAQ:** Do I need field boundaries? · What if I don't know last year's N? · Should I retype my soil test? · How is my data used?
- **Sources:** S3 (what to record per sample), S2.
- **Links:** B1, A3, C1; `#check`, `#pilot`, privacy page.
- **CTA:** "Pilot farms send this list by Jan 15, 2027." → `#pilot`.

### G. Glossary: fertilizer planning terms for Ontario wheat
- **Intent:** informational, definitional (strong for AI answers).
- **Primary:** "soil test glossary". **Related:** term-level queries: "what is Olsen P"; "what is P2O5"; "what is GS30"; "what is a split application"; "what is an accredited soil test".
- **Terms (first set):** accredited soil test; ammonium acetate; Bray-1; buffer pH; confidence level; elemental form; extraction method; GS30 (Zadoks); green-up; Mehlich-3; mg/L; nitrate-N; Olsen (sodium bicarbonate); P2O5; K2O; ppm; previous crop; proof document; sampling depth; split application; top-dress; 4R; vendor-neutral; version (of a plan).
- **Format:** H2 per letter; each term = one 1-3 sentence definition + source + link to the explaining article. `DefinedTermSet` schema.
- **FAQ:** none (definitions are the content).
- **Sources:** S3, S4, S5, S8.
- **Links:** every article.
- **CTA:** `#how`.

## 8. Open items

1. Blog route, schema components and sitemap entries need a `cto`/website plan before anything goes live.
2. ~~Landing copy vs rule 11~~ RESOLVED by CPO 2026-11-17 (see section 0 guard).
3. A human must open S7-S16 and confirm each statement before an article cites them.
4. Named author and reviewer. Until a human agronomist is named, articles stay drafts.
5. AI-crawler policy in `robots.ts`: Farjad Iranmehr's decision.
6. French (`fr`) versions for Ontario francophone growers: after `en` is reviewed, per ADR 0003.
