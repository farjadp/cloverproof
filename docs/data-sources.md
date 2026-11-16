# External data and tools: licence register

Owner: data governance specialist (reports to `head-of-data`). Last checked: 2026-11-16.
Rule: a cell is "unknown" unless the official page stated it. Nothing here is legal advice; every row is "not reviewed" by a lawyer until `legal-compliance-specialist` signs off.
Farmers own their farm data; CloverProof processes it to produce plans. External data below is context only and never replaces a farmer's soil test.

Verification note: the official ISRIC docs, JRC ESDAC and PCSE LICENSE pages were unreachable from the fetch tool on 2026-11-16 (connection refused / 404). For those rows the licence comes from search-result excerpts of the official pages and is marked "(excerpt)". Re-verify on the page before any use beyond reading.

## Pilot region coverage
- Ontario (first): SoilGrids, WoSIS (sparse, per-profile licence), FRST (US-centred; Canada coverage unverified), AgriSuite Crop Nutrient Calculator, Ontario Corn N calculator, FTW, AAFC ACI, Docling, farmOS (concepts), PCSE (offline).
- Prairies (backup): SoilGrids, WoSIS, FTW, AAFC ACI, Docling. AgriSuite and Ontario Corn N do not apply (Ontario-specific).
- Not covering Canada: LUCAS (EU only), EuroCrops (EU only).

## Licence table

| source | URL | use | licence | redistribution | commercial use | attribution text | phase | lawyer review status | last checked |
|---|---|---|---|---|---|---|---|---|---|
| SoilGrids v2.0 (ISRIC) | https://docs.isric.org/globaldata/soilgrids/ ; files: https://files.isric.org/soilgrids/latest/data/ | No-test mode context: pH, OC, texture, total N, offline cached grids | CC BY 4.0 (excerpt of ISRIC FAQ: "since 2019, SoilGrids products are provided under the CC BY 4.0 licence") | yes (CC BY 4.0, with attribution) | yes (CC BY 4.0) | "SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0"; cite de Sousa et al. 2021, SOIL 7, 217-240, doi 10.5194/soil-7-217-2021 (author order to verify) | 1 (no-test context) | not reviewed | 2026-11-16 |
| LUCAS 2022 topsoil (JRC ESDAC) | https://esdac.jrc.ec.europa.eu/projects/lucas | Measured P/K, EU only | Registration plus per-dataset licence on ESDAC; terms conflict across pages (excerpt) | no (onward transfer to third parties restricted; no sub-licence) | unknown (one 2022 page says any purpose incl. commercial; older LUCAS licences say non-commercial only and new products need JRC consent) | "European Union / JRC acknowledged as source" (exact wording per licence text: unknown) | 4 (EU pack, not before) | not reviewed | 2026-11-16 |
| WoSIS (ISRIC) | https://www.isric.org/explore/wosis | Global profiles, P by extraction method | Per profile: CC BY or CC BY-NC (excerpt of ISRIC Data Hub record: "licensed per profile ... indicated in the data"). Limiting licences are not served | per profile (CC BY yes; CC BY-NC no) | per profile (CC BY yes; CC BY-NC no) | Per data provider's licence column plus WoSIS snapshot citation (exact text: unknown) | 3/4 | not reviewed | 2026-11-16 |
| PCSE / WOFOST | https://pcse.readthedocs.io/ ; https://github.com/ajwdewit/pcse | Wheat phenology, offline validation only | EUPL (docs: "licensed under the European Union Public License"; v1.1 or later in 5.2.5 docs). LICENSE file not read; a third-party wiki says "EUPL/GPL". WOFOST crop-parameter licence: unknown | unknown (copyleft obligations apply on distribution) | unknown | Not applicable while offline; cite PCSE and de Wit if results published | 3 (offline notebook) | not reviewed | 2026-11-16 |
| FRST (USDA) | https://frst.scinet.usda.gov/ | Critical soil-test P/K, reference only (US/Canada) | unknown (site shows only a copyright line "(c) 2026 FRST"; no terms of use found; Privacy page not read) | unknown | unknown | unknown | 3 (reference) | not reviewed | 2026-11-16 |
| Ontario AgriSuite Crop Nutrient Calculator | https://data.ontario.ca/dataset/18988bd0-8835-4e2a-9cf2-f63e4554d346 | Reference only; test cases entered by hand, never scraped | unknown (Ontario catalogue record: "not subject to a licence because it is not yet public"; OMAFRA copyright page not read) | unknown | unknown | unknown | 2 (hand-entered comparison cases) | not reviewed | 2026-11-16 |
| Ontario Corn N calculator / MRTN-MERN | https://www.farms.com/agriculture-apps/technology/ontario-corn-nitrogen-calculator | Concept only (economic N rate approach) | unknown (Grain Farmers Ontario / Univ. Guelph database; no terms found). Ontario uses "MERN"; "MRTN" not confirmed for Ontario | unknown | unknown | unknown | 2 (concept only) | not reviewed | 2026-11-16 |
| Fields of The World (FTW) Global | https://source.coop/ftw/global-data | Field-boundary pre-fill | Global dataset: CC-BY-4.0 (source.coop). Sentinel-2 inputs (c) Copernicus/ESA. Other FTW products differ: Kerner Lab benchmark mixes CC-BY, CC0, CC-BY-NC, GPL-2.0; Wherobots regional predictions CC BY-NC 4.0 | yes (global dataset only) | yes (global dataset only; NOT the benchmark or Wherobots sets) | Per source.coop record: Taylor Geospatial et al., FTW Global, CC-BY-4.0 (exact wording: unknown; copy from record at use) | 4 | not reviewed | 2026-11-16 |
| AAFC Annual Crop Inventory | https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9 | Previous crop (Canada) | Government of Canada Open Government Licence (excerpt: service metadata says "Government of Canada Open Data Licence Agreement"; a third-party record says OGL 2.0 - Canada). Check each year's record | yes (OGL-Canada) | yes (OGL-Canada) | "Contains information licensed under the Open Government Licence - Canada" plus "(c) Government of Canada" per year record | 4 | not reviewed | 2026-11-16 |
| EuroCrops v2.0 | https://doi.org/10.2905/b9fb9e67-78a9-4327-9d59-39a928d812d3 | EU parcels + crop (previous crop) | CC BY 4.0 per the ESSD paper; v1 GitHub listed CC BY-SA 4.0; source licences per paying agency (18 agencies) not verified | unknown (per agency) | unknown (per agency) | unknown | 4 | not reviewed | 2026-11-16 |
| Docling (IBM) | https://github.com/docling-project/docling | Lab-report PDF table extraction | MIT for code. Model weights: separate licences, not stated on the repo page | yes (code, MIT) | yes (code, MIT); weights unknown | MIT notice retained | 3/4 spike | not reviewed | 2026-11-16 |
| farmOS data model | https://github.com/farmOS/farmOS | Concepts only; never copy code | GPL-2.0 per GitHub metadata; v1 FAQ says "GPL v2+". Current "or later" not confirmed | n/a (we copy nothing) | n/a (we copy nothing) | none needed for concepts | 0-3 (reading only) | not reviewed | 2026-11-16 |
| Hugging Face crop/fertilizer datasets, student repos | n/a | Do NOT use | unknown provenance | no | no | n/a | never | not applicable | 2026-11-16 |

## Decision / rule per source
- SoilGrids: never call the REST API at runtime (ISRIC says it is paused, no restoration date; v2.0 API was beta). Use offline cached grids from files.isric.org. Context only, never a P/K rate.
- LUCAS: EU only, outside the Ontario pilot. Do not download until the licence for the 2022 topsoil dataset is read from the licence text accepted at registration. Raw data never redistributed. Sampling depth (CPO note: 0-30 cm; 2018 differs) was not verified: confirm before use.
- WoSIS: import only rows whose licence column is CC BY (or other commercially usable); drop CC BY-NC and unknown. Store the licence per row.
- PCSE/WOFOST: offline validation only; no production import without lawyer review. Copyleft (EUPL) is the reason.
- FRST: reference only until terms are found; no bulk copy into packs. Any value used in a pack needs agronomist validation (`TODO(agronomist)`).
- AgriSuite: reference only; agronomist enters cases by hand; never scrape.
- Ontario Corn N / MRTN: concept only; do not copy tables or curves.
- FTW: use the Global CC-BY-4.0 dataset only; exclude benchmark and Wherobots data.
- AAFC ACI: previous-crop suggestion, farmer confirms.
- EuroCrops: do not use until each paying agency's licence is read for the countries in scope.
- Docling: spike only, on lab reports farmers consented to share; check model-weight licences first.
- farmOS: read concepts, write our own schema; never copy code or schema text.
- Hugging Face / student repos: not used.

## Unknowns to resolve
| source | cell | how to resolve |
|---|---|---|
| LUCAS 2022 | commercial use; exact attribution text | Read the licence accepted at ESDAC registration; ask ec-esdac@ec.europa.eu if it conflicts |
| WoSIS | exact attribution/citation text | Read the Readme in the snapshot used |
| PCSE/WOFOST | redistribution, commercial use, WOFOST parameter licence | Read repo LICENSE and the WOFOST_crop_parameters repo |
| FRST | licence, redistribution, commercial use, attribution | Read Privacy/Manual pages; ask FRST contact |
| AgriSuite Crop Nutrient Calculator | licence, redistribution, commercial use, attribution | Read OMAFRA/King's Printer copyright page; ask OMAFRA |
| Ontario Corn N / MRTN | licence, redistribution, commercial use, attribution | Ask Grain Farmers Ontario / Univ. Guelph |
| FTW Global | exact attribution wording | Copy from the source.coop record at download |
| EuroCrops v2.0 | redistribution, commercial use (per agency), attribution | Read the JRC record and per-country sources |
| Docling | commercial use of model weights | Read each model card |
| farmOS | whether "GPL v2 or later" currently applies | Read LICENSE.txt (moot while concepts only) |
| All rows | lawyer review | `legal-compliance-specialist` |
