# Notes: agronomy firms and co-ops/retailers (updated 2026-11-17)

Extends `docs/growth/partner-shortlist.md`. Nothing contacted; no forms, accounts or logins.

## Method
WebSearch + WebFetch only, public pages. Pass 1: homepages/contact pages of the original 14 rows. Pass 2 (~35 calls): searches by region and role, then two public directories that list firms:
- nutrientmanagement.ca "Nutrient Management Consultants" (public directory, firm names and regions only; no websites printed) - source of most new rows.
- soilsatguelph.ca digital soil mapping providers (firm + town, no websites) and the Raisin Region CA BMP list (PDF, June 2025; could not be text-extracted via fetch, only via search snippets).
Independence label rules: `verified` only if the firm's own site says it is independent / sells no inputs; `unverified` otherwise (reason given); `conflict` if own site shows input sales. Contact: only a form URL or general business address on the firm's own site; named staff addresses not stored.

## Counts
- Independent/consultant rows: 25 (9 original + 16 new); 5 retailer/co-op rows unchanged (conflict: sells fertilizer).
- Independence verified on own site: 4 (Stratford Agri Analysis, LandLogic, Agri-Solve, Agronomy Advantage). Agri-Solve is verified on the strength of its "Independent Crop Consultants" heading only; input sales not stated.
- Unverified: 21. Veritas has a possible conflict (formerly a division of an input retailer).
- Rows with a usable contact channel: 5 (Agri-Solve, Warriner, Stratford, LandLogic [gmail, confirm], Agronomy Advantage). The other 20 have no own-site contact found.

## Top 10 independents (estimate: independence evidence + wheat-belt location + contact)
1. Agronomy Advantage (Dundalk) - verified, contact form
2. Agri-Solve (Brucefield, Huron) - verified by heading, contact form
3. Stratford Agri Analysis (Perth) - verified, sampling only
4. LandLogic Nutrient Management (Chatham) - verified, gmail to confirm
5. NithField Advanced Agronomy (Drumbo) - self-described independent per AIC bio, 75k acres, site/contact not confirmed
6. Warriner Ag (SW Ontario) - form, independence unverified
7. Bos Agronomy (Goderich) - directory only
8. Koch Ag Consulting (Brussels) / Tina Beirnes Ag Consulting (Atwood) - Huron/Perth, directory only
9. Fieldwalker Ag (Minto) - founded 2018, no site found
10. Crop Quest (Ontario) / Elite Agri Solutions (St. Thomas) - confirm entity and site first

## Gaps
- 20 of 25 rows lack an own-site check: sites not found by search; fetch of nithfield.com returned HTTP 500. Next pass: find each firm's site (e.g. OSCIA/Ontario CCA event pages) and re-label.
- Ontario CCA Association has no public firm directory found; certifiedcropadviser.org "Find a CCA" (national) not opened. OMAFA's certified consultant list not found as a public page; nutrientmanagement.ca directory used instead.
- FHCU "Find an Advisor" page lists named individuals only; not used.
- Winter-wheat focus and willingness to relay a pilot notice: unknown for all firms.
- CASL basis for forms still needs legal confirmation; rows with no channel are `unknown` (do not email).
- Not covered: Attema (Niagara), Apedaile and Egis (Ottawa), APVEC, Clean Field Services, Elmwood Farms, Naturaide, Triple G (listed in directory; lower fit or livestock). Hoegys Farm Supply is a supply firm, excluded. MNP and E4 returned 403 earlier.
