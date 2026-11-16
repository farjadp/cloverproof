# Pilot intake checklist

Owner: `customer-onboarding-specialist` (reports to `coo`). Status: DRAFT, not yet reviewed by Farjad Iranmehr (agronomist).

Sources: `engine/cloverproof_engine/models.py` (engine v0.2.0), `db/migrations/0003`-`0008`, `website/db/migrations/0001_pilot_request.sql`, `docs/agronomist-todo.md`, `CLAUDE.md` hard rules.

Rules this checklist follows:
- We ask only for data the plan uses, or that the agronomist may need (marked "maybe", with a `TODO(agronomist)`).
- No soil test: N-only plan (max `medium` confidence); we recommend a lab test for P and K. Never block onboarding on a missing test.
- Every soil-test value is stored with form (P vs P2O5, K vs K2O), unit, extraction method, depth and date. Never guessed.
- No agronomic constant, threshold or rate appears in this document or in any message to a farmer.
- Nothing here is sent to a farmer without agronomist approval of the plan numbers (review gate). Intake messages contain no numbers at all.

Column key. **Engine**: R = required, O = optional, - = not used (v0). **Agro**: R / O / maybe (agronomist-only, undecided).

## 1. Farmer and consent

Already captured by the website pilot request (`pilot_request`). Confirm, do not re-ask.

| Item | Engine | Agro | Format / units | Stored as | Why it matters | Common mistakes | If missing |
|---|---|---|---|---|---|---|---|
| Full name | - | R | text | `farmer.display_name` | Who the plan is for; appears on the proof PDF | Business name given instead of person | Ask in welcome message |
| Email | - | R | valid email | `pilot_request.email` (PII) | Only channel for plan delivery and reminders | Typos; shared mailbox | Cannot onboard |
| Phone / preferred contact | - | O | text | `farmer.notes` (no column yet) | Faster follow-up for farmers who do not read email | Not collected by the website form | Optional, skip |
| Country | R (pack choice) | R | ISO country | `farm.country_code` | Selects the country pack | Free text "UK" vs "GB" | Ask; no plan without it |
| Region / province / county | - | R | text | `farm.region` | Agronomist judges local conditions; pack constants may vary by region (todo #2, #7) | Too vague ("north") | Ask |
| Consent to process data and share with agronomist | - | R | timestamp + exact wording | `pilot_request.consent_at`, `consent_text` | Legal basis; needed before any data is stored | Consent for contact only, not for field data | Do not proceed |
| Language / locale | - | O | locale code | `pilot_request.locale` | Message language (website is multi-language; internal tool is English) | Assuming English | Default to request locale |

## 2. Farm

| Item | Engine | Agro | Format / units | Stored as | Why it matters | Common mistakes | If missing |
|---|---|---|---|---|---|---|---|
| Farm name | - | R | text | `farm.name` | Groups fields; used on the document | Several farms under one name | Use farmer's name + "farm" |
| Total farm size (as entered on website) | - | O | free text with units | `pilot_request.farm_size_text` | Scoping only; the engine uses per-field area | Treating it as field area | Ignore; use field area |
| Main crop (website) | - | O | text | `pilot_request.main_crop` | Screens eligibility: engine v0 supports wheat only | Several crops listed | If not wheat, tell farmer we cannot plan it yet; log demand |

## 3. Field

One block per field in the pilot. Pilot target is 5-10 farms; confirm the number of fields per farm with the agronomist.

| Item | Engine | Agro | Format / units | Stored as | Why it matters | Common mistakes | If missing |
|---|---|---|---|---|---|---|---|
| Field name | - | R | text | `field.name` | Matches the plan to the farmer's own naming | Two fields with one name | Ask |
| Field area | R | R | ha, acres, or other local unit; we convert | `field_geometry_version.area_ha` (ha), `area_source = manual` | Scales the plan to total product and cost | acres vs ha; area of the whole farm instead of the field; hectares in the local sense (e.g. dunams, bigha) | Ask for farm-service-agency / cadastral figure; otherwise do not proceed |
| Area unit as the farmer stated it | - | O | text | note on field (no column yet) | Lets us audit the conversion later | Dropping the original unit | Record in message thread |
| Location | - | R | nearest town plus either a pin (lat/long) or a drawn sketch / photo of the field boundary | `field_geometry_version.geom` stays NULL until map drawing (Phase 4); keep the pin in notes | Agronomist identifies the field and local conditions | Pin on the farmyard, not the field; lat/long swapped | Town + legal land description is enough for v0 |
| Soil type / texture (as the farmer knows it) | - | maybe | words: sandy, loam, clay, etc. | not stored yet | May matter for soil N supply and bulk density (todo #2, #9) | Overconfidence in own classification | `TODO(agronomist)`: confirm whether to ask; skip until decided |
| Irrigated or rain-fed | - | maybe | irrigated / rain-fed | not stored yet | May change the maximum rate (todo #7) | Partial irrigation | `TODO(agronomist)`: confirm whether to ask |

## 4. Crop plan

| Item | Engine | Agro | Format / units | Stored as | Why it matters | Common mistakes | If missing |
|---|---|---|---|---|---|---|---|
| Crop for the coming season | R | R | wheat (only value in engine v0) | `crop_plan.crop` | Selects the nutrient method and constants | Winter vs spring wheat not stated | If not wheat: stop, log demand. `TODO(agronomist)`: do we need winter/spring, class, variety? |
| Target yield | R | R | t/ha. Accept bu/ac, kg/ha, t/ac, quintal/ha and convert at intake | `crop_plan.target_yield_t_ha` (t/ha) | Sets how much nutrient the crop removes; the largest single driver of the nitrogen rate | bu/ac typed as t/ha; fresh vs dry grain; best-ever year instead of realistic average; wheat bushel weight differs from other crops | Ask the farmer to give recent field or farm yields. Agronomist chooses. Do not default silently |
| How the farmer derived the target yield | - | R | choice: average of recent years / best recent year / neighbour or regional figure / guess; plus the years used | note on `crop_plan` (no column yet) | Lets the agronomist judge whether it is realistic; a guess is treated more carefully than a measured average. Also feeds a possible later confidence rule | Not recording the source | Record "not stated"; agronomist decides |
| Previous crop | R | R | name of the crop grown last season in this field | `crop_plan.previous_crop` (trimmed, lower case) | Previous crop changes the nitrogen credit the engine applies | Listing the crop two seasons ago; "none" for fallow; "legume" without saying which; engine v0 knows only wheat, canola, corn, soybean, field pea and rejects others (`UnknownPreviousCropError`) | Ask. If the crop is not on the pack list, the plan is blocked until the agronomist extends the list (todo #8). Fallow, alfalfa/clover and "other" are not supported yet |
| Previous-crop residue handled (removed / baled / left) | - | maybe | choice | not stored yet | May affect nitrogen credit (todo #3, #6) | - | `TODO(agronomist)`: confirm whether needed |
| Plan date | R | R | date (today's date by default; the date the plan is made) | `crop_plan.plan_date` | Engine rejects a soil test dated after the plan date; used for soil-test age rule | Using seeding date | Set by staff, not asked of the farmer |
| Planned seeding date / window | - | maybe | date or month | not stored yet | Split timing is printed per growth stage (todo #4) | - | `TODO(agronomist)`: confirm whether needed for split timing |

## 5. Soil test (one test per field per sample date)

If the farmer has no test: do not stop. Record `no soil test` on the field, tell them we can plan nitrogen only and recommend a lab test for P and K, and offer to re-plan when a report arrives (a new test creates a new recommendation version).

| Item | Engine | Agro | Format / units | Stored as | Why it matters | Common mistakes | If missing |
|---|---|---|---|---|---|---|---|
| Test available? (yes / no) | R (decides path) | R | yes / no | `crop_plan.soil_test_id` null or set | No test means N-only and lower confidence | Old report from a different field | Treat as no test |
| Source | R | R | `lab` or `estimate` | `soil_test.source` | Estimates lower confidence; labelled in the plan | Calling a neighbour's report "lab" | Default to no test, not `estimate`. `TODO(agronomist)`: when is `estimate` acceptable and who makes it? |
| Laboratory name | O | R | text | `soil_test.lab` | Different labs use different methods; traceability | Using the lab's agent or reseller name | Optional |
| Sample date | R | R | date | `soil_test.sample_date` | Age of test; engine rejects a date after the plan date | Using the report date, not the sampling date; day/month swapped | Ask; if unknown, agronomist decides whether to accept. Do not guess |
| Sampling depth (top to bottom) | R | R | cm preferred; accept in, mm. Convert to cm | `depth_top_cm`, `depth_bottom_cm` | Values are only comparable at a known depth; the nitrate conversion needs a layer depth (todo #9) | "0-6 in" typed as 0-6 cm; one number given instead of a range; several depths on one report, mixed together | Read the lab report. If absent, ask lab or farmer. Do not guess |
| Several depth layers | - | maybe | one row per layer | one `soil_test` per layer (engine takes one depth per test) | Nitrate may need deeper layers (todo #9) | Averaging layers | `TODO(agronomist)`: confirm which layers we need |
| Phosphorus value | O (needed for P advice, not used by v0 N method) | R | mg/kg or ppm (identical by mass; store the unit as printed) | `soil_test_value`, `form` P or P2O5 | Only a test gives P status | Lab reports P2O5 but farmer says "P"; kg/ha or lb/ac or index/rating (low, medium, high) instead of a concentration | Without a number plus unit, do not enter. Ask for the PDF. Never convert from a rating |
| Phosphorus form | R if P given | R | P or P2O5 | `form` | Oxide and element differ by a fixed factor; mixing them gives wrong advice | Assuming the form; "available P" without form | Read the report header or footnote; ask the lab. Else do not enter the value |
| Phosphorus extraction method | R if P given | R | Olsen / Bray-1 / Mehlich-3 / other (named) | `extraction_method`, `extraction_method_detail` (required when `other`) | Interpreting a value depends on the method | Method not printed; Bray used on high-pH soils reported as "P" | Ask the lab. Else `other` with detail "not stated" and agronomist decides |
| Potassium value, form, method | O / R if given | R | mg/kg or ppm; K or K2O; method e.g. ammonium acetate, Mehlich-3 (`other` + detail) | same as above | Same reasons. A lab report may use a different method for each nutrient | K reported as meq/100 g or cmol/kg (not accepted yet; flag to agronomist) | As P |
| Soil nitrate (NO3-N) | O (not used in v0) | maybe | mg/kg or ppm, form `NO3-N` | `soil_test_value` | Engine v0 ignores it (`SOIL_NITRATE_NOT_USED`). Agronomist may use it (todo #9) | NO3 vs NO3-N; kg/ha reported instead of mg/kg; a sample not taken at the depth we need | Store if on the report; do not ask the farmer to order it. `TODO(agronomist)` |
| Total / mineral N | O | maybe | mg/kg, form `N` | `soil_test_value` | One N form per test (engine: each nutrient only once) | Entering both N and NO3-N | Store one form only |
| Soil pH | - | maybe | pH units, method | not stored yet | Often on the same report; may affect P method choice and interpretation | - | `TODO(agronomist)`: confirm if wanted and where to store |
| Organic matter | - | maybe | % and method | not stored yet | May affect soil N supply (todo #2) | % vs g/kg; loss-on-ignition vs Walkley-Black | `TODO(agronomist)` |
| Bulk density | - | maybe | g/cm3 | not stored yet | Needed only if nitrate is converted to kg/ha (todo #9); pack value to be set by the agronomist | Farmers rarely have it | Do not ask the farmer |
| Lab report file | - | R | PDF or clear photo of every page | `proof` storage (key scheme to be set; see section 7) | Source of truth; lets the agronomist check units, forms and methods | Cropped photo missing the footnote or method line | Request again with a checklist of what must be visible |

## 6. Management history (agronomist may want; engine ignores)

All "maybe". `TODO(agronomist)`: tick which of these are worth asking for the 5-10 pilot farms. Default is to ask none of them until decided, to keep the farmer questionnaire short.

| Item | Engine | Agro | Format | Why it might matter | Common mistakes | If missing |
|---|---|---|---|---|---|---|
| Manure, compost or other organic amendments in the last seasons (type, rough amount, date) | - | maybe | text + units as given | Organic amendments supply nutrients the engine does not count (todo #6c) | Amount in loads or bags; "some" | Record "unknown" |
| Fertilizer products used in recent seasons (product, rate, date) | - | maybe | text; rates in kg/ha or lb/ac as stated, we convert | Understanding past practice; later link to `application_log` | Product name only; oxide vs elemental unstated | Record "unknown" |
| Lime or gypsum history | - | maybe | text | May affect soil test interpretation | - | Unknown |
| Tillage system | - | maybe | no-till / reduced / conventional | May affect soil N supply | - | Unknown |
| Past yield records for the field | - | maybe | t/ha, or other unit as given | Supports target yield (section 4) | Whole-farm average used for a single field | Unknown |
| Fertilizer products the farmer can buy locally | - | maybe | list | Plans give nutrient rates; product choice is the farmer's. Vendor-neutral | Asking for a brand preference | Skip |

## 7. Documents to attach

| Document | Required | Notes |
|---|---|---|
| Lab soil report (PDF or photo, all pages) | If the farmer has a test | Keep original file untouched. OCR/LLM reading is out of scope; staff keys values in and a second person checks them against the file. `TODO(coo/cto)`: where intake files are stored (`proof_document` is only for approved plan PDFs; a separate intake-file store is needed) |
| Field sketch, photo or pin | Optional | Until map drawing exists (Phase 4) |
| Yield records, previous fertilizer invoices | Optional | Only if the agronomist asks |

## 8. Unit and form conversion cheat-sheet for staff

Conversions are done by staff or tool at intake. The engine factors live in `engine/cloverproof_engine/units.py`; this list does not repeat any numbers.

- Area: store ha. Record the farmer's original unit in the thread.
- Yield: store t/ha. If the farmer gives bu/ac, the crop's bushel weight is needed; use the engine/pack conversion, never an ad-hoc one.
- Soil test concentration: mg/kg and ppm are identical by mass; store the unit as printed.
- Soil test per-area values (kg/ha, lb/ac) are not accepted as concentrations. Ask for the concentration or flag to the agronomist.
- P vs P2O5 and K vs K2O: copy the form printed on the lab report. If unclear, do not enter; ask the lab.
- Depth: convert inches or mm to cm before storing (a "0-6 in" sample is a range in inches, not 0-6 cm). Use the conversion helper, not mental arithmetic.
- Ratings (low / medium / high, index) are not values. Do not store them as numbers.
- Method: record exactly as printed; `other` always needs the name in `extraction_method_detail`.

## 9. Farmer-facing short version (13 questions, plain language, no agronomic numbers)

Used in the welcome message and any form. Staff fill the rest.

1. What is your name and the best email to reach you? (confirm from website)
2. Which country and region is your farm in?
3. What is the name of the field you want a plan for?
4. How big is that field? Please tell us the number and the unit you use (hectares, acres, or something else).
5. Where is it? A nearest town plus a pin on a map, or a photo of the field boundary, is fine.
6. What crop do you plan to grow there this coming season?
7. What yield are you aiming for, and in what unit do you usually measure it?
8. How did you get to that yield goal (average of recent years, best recent year, a neighbour's yield, a guess)? Any of these is fine.
9. What crop was grown in this field last season? (If it was left empty, tell us.)
10. Do you have a recent soil test report for this field? Yes or no.
11. If yes: please send the whole report (PDF or clear photos of every page). If no: that is fine. We can plan nitrogen only, and we will recommend a lab test so we can also advise on phosphorus and potassium.
12. If you have a report: do you know the date the soil was sampled?
13. Are you happy for us to use this information to prepare your plan, and for our agronomist to review it? (consent, as the exact wording approved by the COO)

Not asked of the farmer: depth, extraction method, form (P vs P2O5), units, lab method. Staff read these from the report; if the report does not show them, staff ask the lab, not the farmer.

## 10. "Ready for plan" definition

A field is READY FOR PLAN when all of these are true. This is the gate between onboarding stages "collecting data" and "plan in progress".

Always:
- Consent recorded (`consent_at`, exact `consent_text`).
- Country set; farmer, farm and field records exist.
- Field area in ha, entered and checked against the farmer's stated unit.
- Crop is one the engine supports (wheat in v0).
- Target yield in t/ha, with the farmer's derivation noted.
- Previous crop named and present in the pack's previous-crop list (else blocked, see section 4).
- Plan date set.

Then exactly one of:
- Path A, with soil test: sample date on or before plan date; depth range in cm; source `lab`; each entered value has form, unit and extraction method (and detail if `other`); a second person has checked the keyed values against the attached report file.
- Path B, no soil test: field marked "no soil test"; farmer told in writing that the plan covers nitrogen only (max `medium` confidence) and that a lab test is recommended for P and K.

Not required for ready: management history, soil nitrate, pH, organic matter, bulk density, irrigation, soil type. These never block a plan unless the agronomist marks them required.

Hand-off: the field moves to "plan in progress" when ready. No number reaches the farmer until the agronomist approves (review gate).

## 11. Open questions for the agronomist (`TODO(agronomist)`)

1. Which "maybe" items must we collect for the pilot: soil type, irrigation, seeding date, residue, organic amendments, tillage, pH, organic matter, soil nitrate? Which depth(s) for nitrate?
2. Previous-crop list: add fallow, alfalfa/clover, barley, potato, a generic "other" (todo #8). Until then those farms are blocked at "ready for plan".
3. Target yield: how do you want it derived or checked (years used, farm vs field average)? Any yield-conversion approach for bu/ac?
4. Is `source = estimate` allowed in the pilot, and who produces the estimate?
5. Soil tests reported in meq/100 g, cmol/kg, kg/ha, lb/ac or ratings: reject, convert, or ask the lab? The engine accepts only mg/kg and ppm.
6. Accept a test older than which age? (only the agronomist can set this; today it is a PLACEHOLDER in the pack, todo #5).
7. Multi-layer tests: one test per layer, or do you need a different model?
8. Which crops after wheat do we onboard? The website lets people request any main crop; engine v0 only supports wheat.
