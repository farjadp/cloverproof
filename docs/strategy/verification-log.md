# Strategy docs — source verification log

Owner: `cso`. Date: 2026-11-17.
Scope: the ontario.ca and StatCan figures in `docs/strategy/` that came from search summaries ("snippet"), plus the dead links that were cited.

**Method.** Each source page was re-opened with the web fetcher, which uses the normal user agent and makes no attempt to get round a block.
- statcan.gc.ca (`www150`, daily releases, WDS API) returned HTTP 403.
- ontario.ca (pages and `/files/` PDFs) returned HTTP 403.
- data.ontario.ca returned HTTP 502 today.
- The built-in browser was not available in this session.
- A publications.gc.ca mirror and a regional census bulletin PDF loaded, but their text could not be extracted (no PDF reader).

**Result.** No ontario.ca or StatCan figure could be newly verified today. Before external use, a person should open each "still-snippet" page in a normal browser.

## Status per figure
| File | Figure | Status | Note |
|---|---|---|---|
| market-sizing.md | Ontario winter wheat seeded acres 2021–25, by county/region | verified (read 2026-11-17 by the specialist, OMAFRA county xlsx on data.ontario.ca) | data.ontario.ca down today (502); not re-opened |
| market-sizing.md | Ontario 36.4% / Canada 32.0% of farms soil-sample testing (ref. year 2020) | still-snippet | Two independent search summaries attribute it to StatCan 96-325-X "Canadian Agriculture at a Glance". Citation updated to that article |
| market-sizing.md | 94% of fertilizer-applying field-crop farms tested soil (FMS 2021, Canada) | still-snippet | StatCan Daily 2023-02-17 returns 403 |
| market-sizing.md | 92% of Ontario farmers tested soils (FMS 2021, via GFO) | still-snippet (new) | The GFO page cited in the search summary returns 404 |
| market-sizing.md | 48,346 Ontario census farms, 11.77M acres (2021) | still-snippet | Labelled FACT in the file, but the StatCan page was found via search only. The OFA local snapshot is a secondary source |
| market-sizing.md | Pub 60 (2026) winter wheat fertility cost $180.90/ac, of which $107.85/ac N | not re-verified | PDF on ontario.ca returns 403 today. These are budget costs, not rates |
| market-sizing.md | Ontario winter wheat farm count | UNKNOWN | Census table 32-10-0416 returns 403 |
| competitor-scan.md / competitive-landscape.md | AgriSuite: tools, free, accounts, export | AgriSuite is free per Canada.ca (2019, read). Accounts and export are still UNKNOWN | ontario.ca/page/agrisuite returns 403 |
| competitor-scan.md | Ontario lab list, "interpreting soil tests" pages | still-snippet | ontario.ca returns 403 |
| farmer-voice.md | Nutrient-management record-keeping requirements | still-snippet | ontario.ca returns 403 |
| farmer-voice.md | Soil sampling guidance (grid sampling pays only if it changes rates) | still-snippet | ontario.ca returns 403 |

## Dead links removed (marked UNVERIFIED in the files)
| Source | Cited in | Claim now marked UNVERIFIED |
|---|---|---|
| Canola Council, "Shopping for an agronomist" (`canolacouncil.org/?p=39285`, 404) | positioning.md, billing-model-options.md, competitor-scan.md | "Most farmers do not pay for independent agronomy advice". Prairie canola fees: $8–10/ac full package, $4–7/ac scouting, $200–300/h one-off visits |
| Alberta Farm Express, "Adding an agronomist to your farm team" (`albertafarmexpress.ca/?p=75272`, 404) | billing-model-options.md | CCA/PAg rate of $100–300/h |

## Price correction
- **AgExpert Field:** Premium is $399/yr. $499/yr is the separate Premium Bundle with accounting, currency not stated ([agexpert.ca/Field](https://agexpert.ca/Field), per competitive-landscape.md, 2026-11-17). positioning.md is updated; the other files already state $399 for Premium.

## Still to do (owner: cso; a person with a normal browser)
1. Open the 403 pages in a normal browser, then update this log to `verified` or `wrong`:
   - StatCan 96-325-X article 00006;
   - StatCan Daily 2023-02-17;
   - Pub 60 (2026) p.15;
   - ontario.ca AgriSuite;
   - ontario.ca record-keeping.
2. Find a live Ontario or Prairie source for independent-agronomist fees. Otherwise collect them on pilot calls (cro).
