# Brief for the CPO: landing-page measurement and pilot-recruit copy

To: `product-manager` (CPO), via `cro`. Not for `cp-website` directly. Route as the CPO decides: `cto` → `cp-website` (events, form), `cto` / `cp-database` (schema), `legal-compliance-specialist` (privacy notice), `head-of-data` (definitions).
From: `growth-marketer`, 2026-11-16. Skills used: `cro`, `copywriting`, `analytics` (marketingskills); `marketing-psychology:dark-pattern-check` principles for the copy (no false urgency or scarcity).
Companion: `docs/growth/pilot-funnel.md` (stage definitions, status proposal, weekly report).

## 1. The ask

Make the pilot funnel measurable with the least tracking that works: no cookies, no device storage, no PII in events. Close the copy gaps that stop a wheat farmer from knowing whether the pilot is for them. Deadline driver: 5–10 confirmed wheat farms by 2027-01-15, about 8.5 weeks from today. Every week without measurement is a week of outreach we can't attribute.

Decisions needed from the CPO / Farjad Iranmehr are in §8.

## 2. Current state (verified)

- No analytics of any kind in `website/src` or `website/package.json`.
- The field-check result is not passed to the form.
- Form steps, errors and the visit source are not recorded.
- The honeypot returns "success" without writing a row. A client-side success event would count bots.
- Site URL is the Railway preview `https://website-production-a1991e11.up.railway.app`. Production domain not decided (`docs/plans/website-v1.md`).

## 3. Privacy requirements (non-negotiable for any option)

1. No cookies, `localStorage`, `sessionStorage` or IndexedDB written for measurement. A per-page-load `view_id` lives in JS memory only.
2. No PII in events: never names, emails, notes, free-text fields, full IPs or full referrer URLs. Referrer = host only. IP may be used in transit for bot and country lookup, and is never stored.
3. Events hold only the whitelisted properties in §5. Anything else is dropped by the collector.
4. No third-party script that sets identifiers or fingerprints. No GA4, Meta Pixel or LinkedIn Insight Tag for now (they need a consent banner in EU locales and add PII risk for no pilot-scale benefit).
5. The privacy notice lists what is measured and, if used, the analytics processor. `legal-compliance-specialist` confirms whether cookieless measurement needs consent in each launch market. I don't know the answer for every one of the 8 locale markets; don't assume.

## 4. Options

| # | Option | Custom events (needed for check / form) | Cost | New processor in the privacy notice | Notes |
|---|---|---|---|---|---|
| A | **First-party events in our own Postgres.** A small route handler (e.g. `POST /api/e`; `api` is already excluded by the `proxy.ts` matcher) validates a whitelisted payload and inserts into a `site_event` table. Form success/error are written **server-side** inside `requestPilot`, so honeypot hits are never counted. | Yes | **$0 extra** (existing Railway Postgres; negligible rows) | No | Needs a schema change (→ `cto`, ADR) and SQL for reports. Bot filtering is basic (UA list). Full control, nothing leaves our infra. **Recommended.** |
| B | Umami Cloud, Hobby plan | Yes | Free tier reported as $0 for ~100k events/month, 1 site, 6-month retention; Pro about $20/month (third-party figures; check umami.is before relying on them) | Yes (Umami) | Cookieless, quick to add, dashboard included. Check the data region and free-tier terms for commercial use. Free today, so no approval needed unless we outgrow it. |
| C | Umami self-hosted on Railway | Yes | Software free; **extra Railway usage** for one more service (estimate: a few USD/month) | No | More to run and patch. Incremental spend on Railway: treat as needing Farjad Iranmehr's approval. |
| D | Plausible Cloud | Yes | **Paid**: Starter reported at about $9/month (10k pageviews); no free plan, 30-day trial (third-party figures) | Yes (Plausible) | Cookieless, good dashboard. **Paid service: needs Farjad Iranmehr's approval.** |
| E | Cloudflare Web Analytics | No (page views only, as far as I know; verify) | Free | Yes (Cloudflare) | Covers stage 0 only. Not enough alone. |
| F | GA4 / GTM | Yes | Free | Yes (Google) | Rejected: cookies, consent banner, PII risk. |

Recommendation: **A.** Pilot volume is tiny, the funnel's important stages (3–6) already live in our Postgres, and A adds no vendor and no cost. Fallback if `cto` won't add a table and endpoint before launch: **B**, with the same event names and the same whitelist so we can switch later without renaming.

Whatever option is chosen, the **attribution and check-scope columns on `pilot_request`** (`pilot-funnel.md` §4.2) are needed. They are what joins channels to qualified and accepted farms.

## 5. Event specification

Common properties on every event: `event`, `view_id` (uuid v4, memory only, new per page load), `ts` (server time), `locale`, `path` (no query string), `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` (from the landing URL, lowercased, ≤ 100 chars, else null), `referrer_host`, `device` (`mobile` | `desktop` from viewport width, no UA string stored), `country` (2-letter, from the edge or IP lookup, IP discarded; optional).

| Event | Fires when | Extra properties (whitelist) | Funnel stage |
|---|---|---|---|
| `page_view` | Each page load of `/{locale}` and `/{locale}/privacy` (not on anchor scrolls) | — | 0 |
| `check_view` (optional) | `#check` section first ≥ 50% visible in this view | — | 0→1 diagnosis |
| `check_start` | First answer in the check for this view (the `soilTest` answer). Fires once per view, again only after "Start again" | — | 1 |
| `check_answer` | Each answer click | `question` ∈ {soilTest, method, previousCrop, target}; `answer` = option `v` (yes/no/unsure/skip); `step` (0–3) | 1→2 |
| `check_back` (optional) | Back clicked | `step` | diagnosis |
| `check_result` | Result panel shown | `type` ∈ {full, confirm, nOnly}; `gaps` = count 0–4 | 2 |
| `check_restart` (optional) | "Start again" clicked | `type` | diagnosis |
| `check_cta_click` | "Request a pilot plan for this field" clicked | `type` | 2a |
| `cta_click` | Hero / nav / chip CTA clicked | `location` ∈ {hero_primary, hero_secondary, hero_chip, nav} | path split |
| `form_step` | Step `n` reached: n=1 on the first focus of any step-1 field; n=2 / n=3 on a successful "Next" | `n` ∈ {1,2,3} | 3 (pre) |
| `form_back` (optional) | Back clicked in the form | `n` (step left) | diagnosis |
| `form_submit_success` | **Server-side**, after the `pilot_request` insert succeeds. Not on honeypot hits | `check_scope` (if passed) | 3 |
| `form_submit_error` | Server returns a non-success state | `reason` ∈ {invalid, notConnected, error} | 3 |

Forbidden in any event: field values from the form, email domain, notes, the `pilot_request.id`, the full referrer URL, the IP address, the full user-agent string.

Attribution into `pilot_request` (no device storage): on page load, read `utm_*` from `location.search` and the referrer host into component state, and post them as hidden fields with the form. The field-check result is posted the same way as `check_scope` (the result is already in memory; the CTA is on the same page). If the visitor reloads, the UTM is gone. We accept that and `heard_from` covers it.

## 6. UTM conventions for outreach links

Rules: lowercase, hyphens, no spaces, **no personal names** in any parameter (a URL with a person's name is PII in our logs). Use codes and keep the code → organisation map in the CRM, not in the link. Campaign for the whole recruit: `pilot-2027-wheat`. Always link to `/en` (or the live locale), never the bare root, so the locale redirect can't drop parameters. Test each link once before sending.

| Channel | `utm_source` | `utm_medium` | `utm_campaign` | `utm_content` (what varies) |
|---|---|---|---|---|
| Independent agronomists / advisors | `agronomist` | `referral` | `pilot-2027-wheat` | advisor code, e.g. `agr-007` |
| Co-ops | `coop` | `partner` | `pilot-2027-wheat` | co-op code + asset, e.g. `coop-012-newsletter` |
| Soil-test labs | `soil-lab` | `partner` | `pilot-2027-wheat` | lab code + asset, e.g. `lab-003-report-insert` |
| Farm communities, forums, groups | `community` | `social` | `pilot-2027-wheat` | group code, e.g. `grp-021-post` |
| LinkedIn (company or personal posts) | `linkedin` | `social` | `pilot-2027-wheat` | post id or date, e.g. `post-2026-11-20` |
| Direct email / outreach by us | `outreach` | `email` | `pilot-2027-wheat` | sequence + step, e.g. `seq-a-1` |
| Printed material, events (QR) | `print` or `event` | `offline` | `pilot-2027-wheat` | asset or event code, e.g. `qr-flyer-a` |

Example: `https://<domain>/en?utm_source=coop&utm_medium=partner&utm_campaign=pilot-2027-wheat&utm_content=coop-012-newsletter#check`

Domain risk: links sent now point at the Railway preview URL. If the production domain changes before Jan 15, every link already sent depends on a permanent redirect that keeps the query string. Either decide the domain before outreach starts or commit to that redirect (decision §8).

## 7. Copy gaps for a wheat-farmer pilot recruit

Verdict on `website/src/messages/en.json`: the product explanation is clear and honest. The **pilot offer is not**. A wheat farmer can't tell from the page whether the pilot is for wheat, whether it runs in their region, what they must hand over, how much time it takes, what it costs, or what happens after they submit. Those are the questions that decide whether someone fills in a form.

Rules followed: no agronomic numbers, no yield or savings promises, no claim that any third party accepts or approves the proof document, no invented scarcity. Brackets `[…]` are facts that only Farjad Iranmehr can supply. Ship nothing with a bracket left in it.

| # | Gap | Key(s) | Current | Suggested |
|---|---|---|---|---|
| 1 | Not said it's for wheat | `hero.eyebrow` | "Pilot season 2027 · Applications open" | "2027 wheat pilot · Applications open until [15 January 2027]" (a real deadline, not invented urgency) |
| 2 | Where it runs | `hero.note` | "Early-stage product. Pilot availability depends on location and fit." | "For wheat growers in [regions]. Early-stage product; we're taking a small number of farms." |
| 3 | Who / how many / when | `pilot.intro` | "We're working with a small number of farms for the coming season…" | "We're looking for [5–10] wheat farms in [regions] for the February–April 2027 season. Tell us about your operation and we'll reply within [n] working days." |
| 4 | What the farmer gives | new `pilot.giveTitle`, `pilot.give[]` | — | "What we'll ask you for": "The field's name and approximate area" · "What grew there last season" · "Your yield goal for this season" · "Your lab soil-test report, if you have one (we read the method, depth and date)" · "A short call, about [x] minutes, to go through it" |
| 5 | What the farmer gets | new `pilot.getTitle`, `pilot.get[]` | — | "What you get": "A fertilizer plan for [up to n] wheat field(s): what, how much, when and why" · "Checked by an agronomist before you see it" · "A proof document recording the inputs, the reasoning and who reviewed it" · "Without a soil test, the plan covers nitrogen only, and we'll recommend a test for phosphorus and potassium" |
| 6 | Time commitment | new `pilot.time` | — | "Time from you: [about x hours across the season — confirm with the agronomist]." Only once known. Don't estimate it on the site. |
| 7 | Cost | new `pilot.cost` + FAQ | — | Farjad Iranmehr decides. If true: "There is no charge for pilot farms in the 2027 season." If not decided, say "We'll explain the pilot terms on the call" rather than nothing. Don't publish a price. |
| 8 | Who decides | new `pilot.control` | — | "You stay in charge: you decide what to apply." (Legal review recommended.) |
| 9 | What happens next | `pilot.successBody` | "Thank you. We've received your request and will be in touch." | "Thank you. We'll reply by email within [n] working days to arrange a short call. If you have a soil-test report, keep it handy." |
| 10 | Crop field doesn't qualify | `pilot.crop` (form) | "Main crop" (free text) | Replace with "Will you grow wheat on this farm in 2027?" (Yes / No / Not sure). Keep "Main crops (optional)". |
| 11 | No region | form, new `pilot.region` | Country only | Add "Province / state / region" (required). Needed to qualify. |
| 12 | Source unknown | form, new `pilot.heardFrom` | — | Optional select "How did you hear about us?": An agronomist or advisor · A co-op · A soil-test lab · A farm group or forum · LinkedIn · Search · Other |
| 13 | Check result lost | `check.cta` → form | CTA anchors to `#pilot` | Pass the result as hidden `check_scope`. Optionally show one line above the form: "Your field check: [result tag]". |
| 14 | FAQ doesn't answer pilot questions | `faq.items` | 6 items, product-focused | Add: "Is the pilot only for wheat?" ("In 2027, yes. Other crops come later.") · "How much time does it take?" (from #6) · "Does it cost anything?" (from #7) · "What happens to my farm data?" (link to the privacy notice; vendor-neutral, never sold) · "Can I leave the pilot?" ("Yes, at any time; ask us and we delete your details.") Rewrite "Where is the pilot available?" with [regions]. |
| 15 | Privacy notice | `privacy.sections` | Lists form data only | Add the measurement (§3) and, if a new field is added, the region, wheat answer, how-heard and visit source on the request. Legal review. |

Not gaps, keep as they are: the sample proof with blank values, the "not a certification" disclaimers, and "no soil test, nitrogen only". These are the trust signals that fit this audience. Don't add testimonials, logos or partner names until they are real and approved.

## 8. Open decisions

| # | Decision | Who |
|---|---|---|
| 1 | Option A (first-party, $0, needs a table and endpoint) vs B (Umami Cloud free tier). C or D only with spend approval | CPO → `cto`; Farjad Iranmehr if C or D |
| 2 | Status model and `pilot_request` columns (`pilot-funnel.md` §4) | `cto` / `cp-database` (ADR) |
| 3 | Run `docs/runbook-db-switch.md` before or after recruiting, which decides whether stage 6 can be linked in SQL | `cto` |
| 4 | Pilot regions, cost/terms, time commitment, fields per farm, reply SLA, deadline wording | **Farjad Iranmehr** |
| 5 | Production domain before outreach, or a committed redirect that keeps query strings | Farjad Iranmehr / `cto` |
| 6 | Qualification criteria and the "accepted" proof rule | `cro` + Farjad Iranmehr; definitions signed by `head-of-data` |
| 7 | Who updates `pilot_request.status`, and with what tool | `cro` → `revops-specialist` |
| 8 | Consent need for cookieless measurement per launch market; privacy-notice wording | `legal-compliance-specialist` |

## 9. Acceptance criteria

Measurement
1. On production, after loading `/en`, finishing the field check and submitting the form, DevTools → Application shows **no cookies, no localStorage, no sessionStorage** written by the site or any measurement script.
2. Each event in §5 fires exactly per its rule, checked by a written QA script (one pass per check outcome: `full`, `confirm`, `nOnly`, plus "Start again" and back navigation). `check_start` fires once per view; `form_step` n=1 fires on first focus, not on page load.
3. The collector rejects any property not on the §5 whitelist (an automated test sends an event with `email` and asserts it is dropped or refused).
4. `form_submit_success` is emitted server-side only after a successful insert; a honeypot submission produces **no** success event and no row (automated test).
5. A link with all four `utm_*` parameters lands, the form is submitted, and the new `pilot_request` row holds those values plus `referrer_host` (host only) and `check_scope` when the check was done first.
6. Over 7 days of production, the count of `form_submit_success` equals the count of new non-test `pilot_request` rows; any difference is explained in the weekly report.
7. Bot requests with a known crawler UA produce no `page_view`.
8. With JavaScript measurement blocked, the page and the form still work, and the form still saves.
9. No measurable regression in page load (Lighthouse performance score and LCP on `/en`, mobile, before vs after, within run-to-run noise).
10. The privacy notice describes the measurement before it goes live (legal-reviewed).

Copy and form
11. The landing page states, above the form, the crop (wheat), the regions, the season (Feb–Apr 2027), what the farmer provides, what they get, the time commitment and the cost/terms position, with no `[…]` placeholders left.
12. No agronomic number, yield or savings promise, third-party approval claim, testimonial or invented scarcity anywhere in the new copy (checked by `cp-agronomy-guard` or the CPO before deploy).
13. The form records region, the wheat-2027 answer and the optional how-heard source; the field check result reaches the form.
14. The first weekly report (`pilot-funnel.md` §6) can be filled in completely for stages 0–3 from data alone, one week after release.
