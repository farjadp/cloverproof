# Pilot recruitment plan: 5-10 wheat farms by Jan 15, 2027

Owner: Partnerships Manager, for CRO. Status: DRAFT, 2026-11-16. Nothing in this plan is sent by us; Farjad Iranmehr sends everything.
Skills used: `prospecting`, `cold-email`, `co-marketing` (marketingskills).

## 0. Assumptions to confirm (Farjad / CRO)
- A1. The pilot is free and concierge-style (every plan reviewed before it reaches the farmer, proof PDF). ASSUMPTION, not confirmed.
- A1b. **D4 (CPO):** the reviewer is an AI agent until a human agronomist is named; real-farm plans stay unreleased until then (target: named before Jan 29, 2027). Outreach must **never** promise "agronomist-reviewed" plans. Approved wording: "reviewed before it reaches you".
- A2. Region DECIDED (Farjad Iranmehr via CPO, 2026-11-16, "Both"): **Ontario winter wheat = primary track; Prairie spring wheat (Manitoba first) = smaller backup track** (section 4b).
- A3. Winter wheat is fall-seeded; the plan covers the spring N decision on an existing stand, which OMAFRA sources place around green-up/last frost (see `pilot-icp.md` section 1). Qualification therefore requires a wheat stand already in the ground for 2027. Agronomist to confirm the timing window.
- A4. Engine covers wheat N only. Any P/K advice needs a lab soil test; farms without a test get N only, max `medium` confidence (CLAUDE.md rules 2-3).
- A5. No external claim of savings, yield, or endorsement. No agronomic numbers in any outreach.
- A6. Target = 8 confirmed (midpoint of 5-10). Funnel is sized for 8; 5 is the floor.

## 1. Channels, ranked
Ranking = expected confirmed farms per hour of Farjad's time, weighted by trust.

| # | Channel | Why it fits | Risk | Effort | Conflict risk |
|---|---|---|---|---|---|
| 1 | Independent agronomists / CCAs | One agronomist holds many farm relationships (ESTIMATE, unsourced) and stays in the loop (their client gets a second reviewed opinion; they keep the relationship). Ontario CCA is a recognised designation, 500+ holders per a secondary source ([GFO magazine](https://ontariograinfarmer.ca/?p=1158); [CCA Ontario overview](https://fertilizercanada.ca/news-events/news/ontario-crop-advisors-taking-steps-in-the-right-direction/)). | They may see us as a competitor; slow to reply in Dec; may refuse to let clients share data. | High up front (personalised, 1:1), best yield. | Low for independents. Must not look like we replace them: frame as a second-opinion tool and a proof document they can use. |
| 2 | Direct contacts from Farjad Iranmehr's network | Highest trust, fastest; farmers know a person, not a brand. | Small pool; friends-as-pilots give polite, non-diagnostic feedback. | Low. Farjad to list names by Nov 30 (section 7). | None, but relationship bias in the calibration data. Mark these farms as "network" in the dataset. |
| 3 | Co-ops and farm organisations (commodity group, soil and crop associations, county federations) | Reach many farms at once via newsletters/meetings; legitimacy. | Slow approvals, mostly past Jan 15; may refuse to promote a pilot or a startup; endorsement claims forbidden (A5). Often have retailer sponsors. | Medium; mostly warm intros at winter meetings. | Medium. Many co-ops sell inputs; a co-op that retails fertilizer is a conflict. Prefer grower associations over supply co-ops. |
| 4 | Soil labs | Reach farms that already test (P/K and N inputs exist). Lab sees farmers who are data-minded. | Labs may not share client lists (privacy); they may want a commercial deal or reciprocal listing; some labs are owned by or sell to retailers. | Medium. Ask only for a neutral mention or a handout in results packages. | Medium. Verify ownership and retail ties before approaching. |
| 5 | Farm communities (LinkedIn, X #agtwitter / #ONag, Reddit r/farming, forums, local groups) | Cheap reach, good for finding agronomists and early adopters. | Low conversion; r/farming is US-heavy; self-promotion rules in groups; Farjad cannot be seen to spam. No account creation or group joining by us. | Medium (Farjad posts/DMs himself). | Low, but retailer reps are present in every group. |
| 6 | Website inbound | Lowest effort; qualifies self-selected. Live now with a pilot form (`pilot_request`) and a field check. | Near-zero volume without channels 1-5 driving traffic; no analytics yet (see `landing-tracking-brief.md`). | Low. Every outreach link carries UTMs. | None. The form's consent line covers follow-up about the pilot (legal review pending, section 6). |

Rule: channels 1 and 2 supply roughly 70% of the 8 confirmed farms (planning split, ASSUMPTION); 3, 4, 5, 6 share the rest.

## 2. Value exchange (no numbers, no savings or yield promises, no endorsement claims)

| Party | Gives | Gets |
|---|---|---|
| Farmer | Field location and size, crop and variety, previous crop, soil test if one exists (lab, date, depth, extraction method), a short intake call (time estimate to be set after a dry run), feedback after the season, permission to store data for calibration. | A field-specific plan (what, how much, when, why) with a confidence level, reviewed before it reaches them, plus a proof PDF with a verifiable hash. Free during the pilot (A1). Vendor-neutral: we sell no inputs and take no commissions. |
| Independent agronomist / CCA | Introductions to willing clients; optionally their own view of the plan. | Early look at a tool that can support their advice; a reviewed second opinion and proof document for their client; credit only if they agree in writing; no client is taken from them. We do not give fertilizer commissions and do not ask for them. |
| Soil lab | A neutral mention or handout; optionally data in a format the engine can read (extraction method, units). | A free, vendor-neutral reading of their results for their clients; their test remains the data source; no competing lab service from us. Commercial terms are an internal option for Farjad, not an offer. |

Never write: "save", "increase yield", "reduce cost", "approved by", "partnered with", logos, or testimonials. "agronomist-reviewed" / "reviewed by an agronomist" (D4, until a human agronomist is named). Use "pilot", "reviewed before it reaches you", "proof document".

## 3. Message angles (angles only; full drafts in S3)
1. **Second opinion, vendor-neutral.** "We don't sell fertilizer or take commissions on it, and every plan is reviewed before it reaches you."
2. **Free pilot, your data stays yours.** "We are looking for 5-10 {REGION} wheat farms for a free pilot this {SEASON}; you get a reviewed plan and a proof document, we keep your data private."
3. **For agronomists: a document your client keeps.** "If you already advise wheat growers, would a reviewed second plan with a proof PDF help you keep that conversation, with no commissions involved?"
4. **Use the soil test you already paid for.** "If you have a recent lab soil test, we turn it into a clear what/how much/when/why plan; if you don't, we tell you what test to take."

## 4. Weekly targets (backwards funnel)

Funnel for 8 confirmed (ASSUMPTIONS, deliberately conservative, blended warm and cold; no benchmarks cited):
- contacts -> conversation: 20% (cold alone is likely 5% or lower; agronomist and network contacts are warmer)
- conversation -> request (farm says "yes, send details"): 40%
- request -> qualified (winter-wheat stand, location in region, willing to share data): 62%
- qualified -> confirmed (agrees in writing/email to terms): 80%
- Result: 200 contacts -> 40 -> 16 -> 10 -> 8 (4% overall). If the cold share is higher than planned, expect 2-3% and need 270-400 contacts; fall back to channel 1-2 only, since extra cold volume fails CASL and quality tests (section 6).

"Contacts" counts distinct individuals or organisations Farjad actually contacts, including agronomists who each may open 3-10 farms. Re-forecast weekly; the numbers below are new events in that week.

| Week | Dates | Phase | Contacts | Conversations | Requests | Qualified | Confirmed |
|---|---|---|---|---|---|---|---|
| W1 | Nov 30-Dec 6 | S2: shortlist, warm network first | 20 | 2 | 0 | 0 | 0 |
| W2 | Dec 7-13 | S2 end: agronomist/CCA batch 1 | 30 | 5 | 1 | 0 | 0 |
| W3 | Dec 14-20 | S3: drafts approved, main push | 50 | 8 | 3 | 1 | 0 |
| W4 | Dec 21-27 | S3 short, freeze starts Dec 25 | 15 | 8 | 3 | 2 | 1 |
| W5 | Dec 28-Jan 3 | Freeze: replies only, no new push | 10 | 3 | 2 | 2 | 2 |
| W6 | Jan 4-10 | S4: second push, follow-ups | 45 | 9 | 4 | 3 | 3 |
| W7 | Jan 11-15 | Close: confirm, waitlist | 30 | 5 | 3 | 2 | 2 |
| Total | | | 200 | 40 | 16 | 10 | 8 |

Cumulative confirmed: 0, 0, 0, 1, 3, 6, 8. Checkpoints: Dec 24 (>= 20 conversations, else add channel 1 effort); Jan 3 (>= 3 confirmed, else shift effort to the Prairie track); Jan 8 (>= 5 confirmed or plan floor = 5).

## 4b. Prairie backup track (smaller)
- Share of effort: about 20% of contacts (ESTIMATE, planning split); target 1-2 confirmed Prairie farms inside the 8, Manitoba first.
- Timing differs: spring wheat N is decided at or before seeding, so a Prairie plan must be delivered before seeding (target about March; agronomist to confirm). Prairie farms must be confirmed and their data (field, previous crop, soil test) received **before Ontario farms**, so their intake runs first in Feb.
- Channels: remote only. Farjad's own Prairie contacts, independent agronomists via LinkedIn, and provincial grower/soil associations (to research in S3). Prairie winter events: UNKNOWN, research in S3.
- Rule set: needs a Prairie pack separate from Ontario (CLAUDE.md rule 6; all values `PLACEHOLDER` until the agronomist validates).
Constraint: S2 owns the shortlist, not the sending. Sending needs approved drafts (S3) and Farjad's hand; in W1-W2 only warm contacts are Farjad's own personal messages (confirm with compliance, section 6).

## 4a. Winter events in Ontario (for in-person intros, not sales stands)
Sources checked 2026-11-16. Only dates that sources state are shown.

| Event | Date | Place | Source |
|---|---|---|---|
| SouthWest Agricultural Conference (SWAC) | Jan 5-6, 2027 | Univ. of Guelph Ridgetown Campus (venue per page unspecified; campus listed as partner) | https://www.uoguelph.ca/ridgetown/swac |
| Midwest Agricultural Conference (MWAC) | Jan 15, 2027 | Venue unknown (2026 edition: RIM Park, Waterloo) | https://www.uoguelph.ca/ridgetown/swac/oagc-virtual ; 2026 venue: https://ontariograinfarmer.ca/2025/12/01/learning-opportunities-this-winter/ |
| Eastern Ontario Crop Conference (EOCC) | Jan 26, 2027 (after the Jan 15 deadline; useful for follow-up) | Venue unknown for 2027 (2026: Southgate Church, Kemptville) | same two URLs |
| OAgC Virtual (livestream and recordings of the three above) | Through Mar 31, 2027 (registration closes Feb 28, 2027) | Online | https://www.uoguelph.ca/ridgetown/swac/oagc-virtual |
| Grain Farmers of Ontario March Classic | Mar 22-23, 2027, Niagara Falls (after the pilot window starts; relevant for results and next season) | Niagara Falls | https://www.farms.com/news/grain-farmers-of-ontario-logo-grain-farmers-of-ontario-announces-astronaut-jeremy-hansen-and-former-ambassador-kirsten-hillman-as-headline-speakers-for-2027-march-classic-244446.aspx |
| FarmSmart Conference | UNKNOWN for 2027 (no 2027 source found; past edition Jan 18, 2020, Guelph) | Guelph (2020) | https://guides.uoguelph.ca/event/2020-farmsmart-conference |
| OSCIA Annual Meeting | UNKNOWN for 2027 (2026 edition: Feb 3-4, Elora) | Elora (2026) | https://ontariograinfarmer.ca/2025/12/01/learning-opportunities-this-winter/ |
| Ecological Farmers Association of Ontario conference | UNKNOWN for 2026-27 (2025 edition: Dec 2-4, London) | London (2025) | same Ontario Grain Farmer article |
| Grain Farmers of Ontario regional meetings | UNKNOWN | UNKNOWN | no source found |

Uncertainty: the SWAC site gives conflicting registration-open dates; check before planning. The SWAC page lists Jan 5-6, and Jan 4-15 is S4; SWAC falls in W6 and MWAC on the last day (Jan 15), so SWAC is the only event that can feed this funnel. Farjad attending is a decision (section 7); virtual access costs money (a secondary source says $229 + HST, currency not stated; confirm on the page).
Prairie backup events: UNKNOWN, not researched. Search before the region decision if the Prairie option stays open.

## 5. Partner categories for the S3-S4 shortlist
No names required yet. Examples are for orientation only, not verified contacts or an endorsement.

| Category | Examples (source) | Pick criteria |
|---|---|---|
| Independent agronomists / CCAs | Ontario CCA program: https://www.certifiedcropadviser.org/ ; Ontario performance objectives: https://www.certifiedcropadviser.org/files/certifiedcropadviser/ontario-performance-objectives.pdf | Independent (no input retail income, check their site); wheat clients in `{REGION}`; public business contact; CCA or P.Ag credential; active on LinkedIn or an own site. |
| Grower organisations / associations | Grain Farmers of Ontario: https://gfo.ca ; OSCIA: https://www.ontariosoilcrop.org (URLs from general knowledge, not fetched here) | Farmer-governed, not a supplier; has a member newsletter or winter meeting; accepts a neutral pilot notice. |
| Soil labs | Examples to check: A&L Canada Laboratories, SGS Agrifood (URLs to be fetched in S3, not verified) | No retail fertilizer arm; accepts third-party read of results; written privacy policy; lab method named on report (Olsen / Bray-1 / Mehlich-3). |
| Universities / extension | Univ. of Guelph Ridgetown (SWAC host): https://www.uoguelph.ca/ridgetown/swac | Extension staff or student clubs as listeners, not endorsers; do not request endorsement. |
| Farm media and communities | Ontario Grain Farmer: https://ontariograinfarmer.ca ; ONtag forum: https://ontag.farms.com | Editorial pitch only, public business role; no paid placement without CRO approval. |
| Co-marketing peers (software, farm-data tools, non-fertilizer) | None identified yet | No fertilizer sales; no overlapping product; shared audience of wheat growers. |

Shortlist scoring (1-5 each, total 20): audience fit, independence from fertilizer sales, reachability before Jan 15, reciprocal value. Cut anyone at 1 on independence.

## 6. Compliance: CASL (flag for `legal-compliance-specialist` via COO)
NOT LEGAL ADVICE. I could not open the official pages directly (CRTC returned 403; Justice Laws timed out), so points below come from search summaries of the CRTC guidance. Verify every line against the official text before use.
- Scope: Canada's Anti-Spam Legislation covers commercial electronic messages (CEMs) sent to or from Canada. Official sources: CRTC Guidance on Implied Consent https://crtc.gc.ca/eng/com500/guide.htm ; the Act https://laws-lois.justice.gc.ca/eng/acts/E-1.6/ ; government overview https://fightspam.gc.ca/eng/home (pages not fetched; confirm).
- Express consent: opt-in, in writing or orally; not pre-ticked; a message asking for consent is itself a CEM; burden of proof is on us, so keep records (CRTC guidance above).
- Implied consent: only the categories in CASL s.10(9), such as an existing business or non-business relationship, or conspicuously published business contact addresses with no "do not email" notice and a message relevant to that person's business role. The time limits and exact conditions are in the Act; I have not verified them.
- Every CEM must identify the sender and include contact details and a working unsubscribe mechanism honoured promptly. Exact wording and deadline: confirm in the Act.
- Open questions for compliance: (a) is a free-pilot invitation a CEM? (b) does a personal message to Farjad's own contacts rely on a relationship exemption? (c) do LinkedIn/X DMs count as CEMs? (d) what consent wording must the website pilot form carry? (e) how does PIPEDA apply to storing farm data (separate from CASL).
- Operating rule until review: send one-to-one, personalised, business-relevant messages to publicly listed business contacts only; sender identified; unsubscribe line; log sources and dates; no purchased lists; no mass blasts.

## 7. Risks and decisions for Farjad Iranmehr
Risks
- R1. Two regions = two rule sets for the agronomist to validate; keep the Prairie track small (section 4b).
- R2. Short window: 6 effective weeks, holiday freeze, S3 is 11 days; sending cannot start until drafts are approved.
- R3. Brand risk: new website, no testimonials, no endorsements. Trust must come from Farjad's name and the proof PDF.
- R4. Retailer conflict: retailer agronomists will see us as a threat; vendor-neutral claim must be verifiable (no commissions in any document).
- R5. Capacity: 8 plans in Feb-Apr plus review minutes; do not confirm more than can be reviewed. Waitlist beyond 10.
- R6. Farmers without soil tests get N only (A4); expectation must be set at intake.
- R7. Data and privacy: farm data is personal/commercial; needs a one-page data-use consent before first plan (not drafted here).

Decisions only Farjad can make
1. ~~Region~~ DECIDED: Ontario primary, Prairie backup. Still needed: confirm the spring-N timing window for both (A3, 4b).
2. Confirm the free-pilot terms (A1) and what the farm signs: data-use consent; no price quoted.
3. List 15-30 own contacts (farmers, agronomists) by Nov 30, with how each knows him.
4. Personally send every message and approve each draft; choose which channels to use of the six.
5. Attend SWAC Jan 5-6 in person (cost, travel, S4 time) or skip.
6. Whether agronomists may be named as partners (needs their written OK); default: no names.
7. Whether to accept lab or co-op commercial terms (internal options only; default: none).
8. Minimum viable count: 5 confirmed farms is the floor; decide whether to launch with fewer.

Open items for other roles: COO/legal review of section 6; CPO on tracking/UTMs (`landing-tracking-brief.md`); `product-manager`/COO on data-use consent.
