# Website measurement (option A): consent review per market (DRAFT)

> **This is not legal advice. A licensed Ontario lawyer should review it before use.** EU, Türkiye and Quebec points also need counsel admitted there.
> Prepared by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO on 2026-11-16.
> Design reviewed: CPO decision "option A", `origin/myca/growth-s2-a73813:docs/growth/landing-tracking-brief.md` §3 and §5, and `docs/growth/pilot-funnel.md` §4.2 on the same branch.
> Notice changes: `privacy-notice.md` v0.3, which adds §3a and the Part B section "Website measurement".

## 0. Design as reviewed

| Element | What it does | Legally relevant because |
|---|---|---|
| `site_event` table in our Railway Postgres (US; residency OQ-06 is open) | Stores first-party events. No vendor is involved. | Cross-border storage. No third-party processor beyond Railway. |
| `view_id`, a uuid v4 held in JS memory and new on every page load | Orders the events of one page view | Information stored in RAM and then sent counts as storage plus access under ePrivacy Art. 5(3) (EDPB 2/2023 ¶¶37–38, 44, 53) |
| `device` (`mobile`/`desktop`), computed from viewport width by JS | Device split | JS reads information generated on the device and sends it. That is "gaining access" (EDPB ¶¶33, 44, 53). |
| Event POST from JS (`page_view`, check answers, form steps, CTA clicks) | Funnel | JS instructs the browser to send information (EDPB ¶33) |
| `utm_*` read from `location.search`; `referrer_host` read from the referrer | Attribution | URL tracking parameters (EDPB ¶51). The referrer is held by the browser. |
| `country` derived from the IP at the edge; the IP is discarded | Market split | IP origin (EDPB ¶¶54–55). Quebec s. 8.1 "located". |
| UA used in transit for the bot filter and not stored | Data quality | Low. Same as a server log. |
| Server-side `form_submit_success` / `form_submit_error` | Counts submissions | Server-side only, so no terminal access |
| Hidden fields posted with the pilot form: `utm_*`, `referrer_host`, `check_scope` → `pilot_request` | Ties channel and check result to a named person | **Personal information.** It is outside every "anonymous audience measurement" exemption. |

## 1. Verdict per market

"Consent" here means opt-in before measurement runs. "Not needed" still means notice in the privacy policy, and in most markets an opt-out.

| Market (locale) | Rule that decides | Verdict for `site_event` as designed | Verdict with §2 changes | Confidence |
|---|---|---|---|---|
| **Canada, federal (en; any locale used from Canada)** | PIPEDA Sch. 1 4.3 (knowledge and consent; implied consent for non-sensitive information) [S1]. OPC: collecting browsing activity needs knowledge and consent; opt-out is acceptable for non-sensitive data [S2]. OPC treats an IP address as personal information [S3]. | **Opt-in not needed.** Notice is required. Implied (opt-out) consent fits non-sensitive, non-identified event data. | Same, and stronger (GPC/DNT honoured, short raw retention) | Medium |
| **Ontario** | No general Ontario private-sector privacy statute. PIPEDA applies. Substantially similar general laws exist only in AB, BC and QC [S4]. | Same as Canada | Same as Canada | Medium (counsel to confirm no other Ontario rule applies) |
| **Quebec (fr; Quebec visitors on any locale)** | P-39.1 s. 8.1: if PI is collected "using technology that includes functions allowing the person … to be identified, located or profiled", the person must be informed first, along with the means to activate those functions. Commentary reads this as off by default [S5]. | **Unknown.** `country` from the IP is plausibly a "locate" function. If the events are PI, s. 8.1 would need those functions off by default with an opt-in. | **Not needed** if `country` is dropped. Nothing identifies, locates or profiles a person, and `view_id` dies with the page. s. 8 notice still applies to the form data. | Low–medium. Whether P-39.1 reaches an Ontario business serving Quebec visitors online is a counsel question. |
| **EU: France (fr)** | ePrivacy Art. 5(3) as transposed (Loi I&L art. 82). Per EDPB 2/2023, our JS reads, memory id and event sends all trigger 5(3) [S6]. CNIL exemption for audience measurement: sole purpose is audience measurement for the publisher, anonymous statistics only, no cross-referencing, no cross-site tracking. CNIL also recommends notice and ≤ 25 months retention [S7]. | **Probably not needed.** 5(3) applies, but the CNIL exemption conditions appear met. Raw rows with `view_id` are not "anonymous statistics" until aggregated, so aggregate fast. | **Not needed** (exempt) if raw rows are aggregated quickly and nothing is cross-referenced | Medium |
| **EU: Spain (es)** | LSSI art. 22.2. AEPD audience-measurement guide (Jan 2024): exempt only if strictly limited to the publisher's own audience measurement and anonymous statistics, with no cross-referencing or onward transfer. Allowed measurements are listed "per page and aggregated daily" (pages, referrer, device type and screen size, clicks and selections, geographic area). Minimum guarantees: notice, and ≤ 25 months retention [S8]. | **Probably not needed**, if raw events are reduced to daily per-page aggregates | **Not needed** (exempt) with daily aggregation | Medium |
| **EU: Italy (it)** | Garante Guidelines 10 Jun 2021 §7.2: analytics treated like technical cookies (no consent) if they cannot single out the user, are used only for aggregate statistics for one site, and are not combined. §3: passive identifiers (fingerprinting) are in scope [S9]. | **Probably not needed** | **Not needed** | Low–medium. The guidance is written for cookies. Applying it to a cookieless memory id is my reading. |
| **EU: Finland (fi)** | Electronic Communications Services Act (917/2014) s. 205 (statute not fetched). Traficom guidance valid from 13 Sep 2021 covers "cookies or similar technologies" [S10]. Secondary sources and court reports say analytics needs consent and is not "essential" [S11]. I found **no** Finnish analytics exemption. | **Consent needed** (as far as I can tell) | **Consent needed.** No design change found that removes it except not measuring Finnish users (§2 C8). | Medium. Traficom's analytics text was not read in full. |
| **EU: Bulgaria (bg)** | Bulgarian Electronic Commerce Act / Electronic Communications Act transposition. Sources conflict (opt-in vs opt-out) and I found no CPDP analytics position [S12]. | **Unknown** | **Unknown** | Low |
| **EU: GDPR layer (all EU)** | If GDPR applies (Art. 3(2): offering services or monitoring behaviour in the EU; five EU locales point that way), the IP processed in transit makes this personal-data processing. Basis: legitimate interests, Art. 6(1)(f), with an LIA (§3). Art. 13 notice applies [S13]. Legitimate interests cannot replace Art. 5(3) consent where 5(3) requires it. | LI is plausible for the event data. It does **not** answer Art. 5(3). | Same | Medium (whether GDPR applies to us at all is a counsel question) |
| **Türkiye (tr)** | KVKK Law 6698. KVKK Cookie Guide (No. 69, July 2025) §5.9: first-party analytics "can be assessed under Criterion B" (strictly necessary for the requested service), so no explicit consent is needed if limited to audience measurement and anonymous statistics with no cross-site tracking. IP masking is recommended. If relying on legitimate interests, run a balance test. Cross-border transfer goes under Art. 9 and the transfer regulation [S14]. | **Probably not needed** for `site_event`. The **transfer to the US** is a separate open issue. | **Not needed** | Low–medium. Whether KVKK applies to a Canadian site with a Turkish locale is unknown. |
| **Arabic locale (ar)** | No single market. Speakers could be in any of more than 20 jurisdictions. | **Unknown** | **Unknown** | n/a |

**What this means in practice.** For the pilot's actual audience (Ontario farms), the design works without a banner, provided the notice is published. The residual exposure is EU visitors, Finland above all, plus the hidden attribution fields for any EU visitor who submits the form (§4).

## 2. Changes that cut consent risk (proposed; the CPO decides)

| # | Change | Effect | Cost |
|---|---|---|---|
| C1 | **Drop `country`.** Don't derive it from the IP at all. If geography matters, the form already holds the typed country and region. | Removes the Quebec s. 8.1 "locate" question and the EDPB ¶¶54–55 IP point. One fewer property derived from personal data. | Lose market split for anonymous visits. Low value: pilot is Ontario-only. |
| C2 | **Honour Global Privacy Control and Do Not Track.** If `navigator.globalPrivacyControl === true` or DNT = 1, send no events (the form still works). Reading the flag locally is not access under EDPB ¶44, because nothing leaves the device. | A persistent opt-out without us storing anything. Meets the OPC opt-out expectation and the AEPD/WP29 "option to refuse" low-risk factor. | Trivial |
| C3 | **Per-visit opt-out link** on the privacy page ("Turn off measurement for this visit"), in memory only. A *persistent* opt-out needs one device-stored flag. Storing a refusal is commonly treated as strictly necessary, but counsel should confirm. **Not recommended now:** C2 covers it. | Visible opt-out | Small |
| C4 | **Fast aggregation.** Raw `site_event` rows (with `view_id`) are kept **≤ 90 days**. A daily job then rolls them into per-day, per-page counts (`date, locale, path, event, property values, utm_*, referrer_host, device, count`), with no `view_id`, and deletes the raw rows. | Brings the stored data close to the "anonymous statistics, aggregated daily" model in CNIL/AEPD. Limits re-identification. | Small (one SQL job) |
| C5 | **Aggregates kept ≤ 25 months**, reviewed yearly (CNIL/AEPD ceiling) | Same | None |
| C6 | **No logging of IP, UA or body in the collector's app logs.** Railway's own HTTP logs are already disclosed as host technical logs (notice §3). | Keeps the "never stored" promise true in practice | Config check |
| C7 | **Hard whitelist plus suppression of small counts in reports.** Never report a cell where `utm_content` maps to one advisor and the count is below 5 next to anything that could single out a farm. | Prevents re-identification in reporting | Reporting rule only |
| C8 | **Finland/EU residual.** (a) Send no client events on the `fi` locale; or (b) use the IP *in transit only* to suppress events from EU/EEA origin, storing nothing; or (c) accept the residual risk (Farjad Iranmehr's decision, with counsel). (a) is weak because locale is not location. (b) needs a GeoIP source: MaxMind GeoLite2 has its own licence (check it), or a CDN header if one is ever added. | Removes or limits the Finland exposure | (a) trivial; (b) small; (c) none |
| C9 | **EU locales: no hidden attribution fields** (see §4) | Removes the Art. 5(3) question for named EU requests | Lose UTM on EU-locale requests; `heard_from` covers it |
| C10 | Keep `view_id` off `pilot_request`, and never add a join key between `site_event` and `pilot_request` (already in pilot-funnel §4.2) | Keeps events non-identifying | None |

Recommended minimum before go-live: **C1, C2, C4, C5, C6, C10** and the notice. C8 and C9 go to the CPO with this review. My recommendation is C8(b) if `cto` says it is cheap, otherwise C8(a) plus counsel.

### Retention proposal for `site_event` (Farjad Iranmehr to approve)
| Data | Retention |
|---|---|
| Raw events (row level, with `view_id`, `utm_*`, `referrer_host`, `device`) | 90 days, then aggregated and deleted. This covers the recruit window to 2027-01-15 plus the weekly reports. |
| Daily aggregates (no `view_id`) | 25 months, then deleted; reviewed every year |
| IP, UA | Never stored (used in transit only) |

## 3. Legitimate-interests assessment, short form (GDPR Art. 6(1)(f); also the KVKK balance test)
| Test | Answer |
|---|---|
| Purpose | Know which pages, links and outreach channels lead to pilot requests. Find where the check or form loses people. Fix the site. |
| Necessity | Least data that works: no identifiers that persist past a page load, no cookies, no third party, no PII, whitelist enforced by the collector. Aggregation is not possible at collection because funnel steps must be ordered within one view. |
| Balancing | Low intrusion. Visitors of a B2B farm-software site would reasonably expect basic first-party usage counts. No profiling, no cross-site tracking, no ads, no sale. Children are not targeted. Safeguards: C2, C4–C7. |
| Outcome | LI is plausible for the GDPR layer, but **it does not satisfy Art. 5(3)** where national law requires consent (Finland; Bulgaria unknown). Counsel to confirm. |

## 4. Attribution on `pilot_request` (UTM, `referrer_host`, `check_scope` tied to a named person)

These columns are personal information once they sit on the request row. That is already recorded in pilot-funnel §4.2.

| Question | Assessment |
|---|---|
| Canada/Ontario | The purpose must be identified at or before collection and be within what a reasonable person would expect (PIPEDA 4.2, 4.3, 4.4) [S1]. Today box A only covers "store these details and contact me about the pilot". It does not tell the person we record how they reached us or their check result. **Fix: add one sentence to the form intro line** (below). Separate consent is not needed: the use is non-sensitive and tied to the request purpose. |
| Quebec | P-39.1 s. 8 notice applies (purpose, means of collection). The same sentence covers it. Not s. 8.1 if C1 is applied. A cross-border communication to the US may require a PIA under s. 17 (not fetched; counsel). |
| EU | Art. 13 notice via the sentence plus notice §3a. **Art. 5(3):** reading `location.search` and the referrer by JS and sending them tied to a named person is outside the anonymous-audience exemptions (CNIL, AEPD). The "strictly necessary for the service requested" exemption likely does not cover attribution. `check_scope` is different: it is the visitor's own answers on the same page, so it is closer to user input and the requested service. Showing it visibly above the form ("Your field check: …") makes that clearer. **Recommendation C9:** on fr/it/es/bg/fi locales, post `check_scope` (visible) but not `utm_*`/`referrer_host`. Pilot is Ontario-only anyway. |
| UTM hygiene | Brief §6 already bans personal names in UTMs. Keep the advisor-code → organisation map in the CRM, with access limited. Mapping `utm_content=agr-007` reveals which advisor referred a named farmer, and that is personal information about both. Disclose it in the notice as "the campaign tag of the link". |

**Proposed addition to the form intro line** (`consent-wording.md` §1). This is text only: hand it to `cp-website` via the COO, and do not edit `website/` from here.
> The 2027 pilot is for farms in Ontario, Canada. We use these details only to review your pilot request and contact you about it. With your request we also keep the campaign tag of the link you followed, the name of the website that sent you, and your field-check result if you did the check, so we know how you found us. They are stored by our host, Railway, in the United States. [Privacy notice]([PRIVACY URL])

Box A wording can stay as it is, because "these details" now includes the attribution through the intro line. Counsel to confirm that is enough (Needs counsel 6).

## 5. Acceptance checks to add to the brief's §9 (for `cto` / `cp-qa`)
- With GPC on (Firefox, Brave or an extension), loading `/en` and completing the check sends **zero** requests to `/api/e`.
- Raw rows older than 90 days: zero, checked by the job. Aggregate table has no `view_id` column.
- Collector logs contain no IP, UA or body (grep the logs from a test run).
- `country` is absent from the schema (if C1 is adopted).

## Sources (checked 2026-11-16)
- S1 PIPEDA, S.C. 2000, c. 5, Sch. 1 principles 4.2–4.4. https://laws-lois.justice.gc.ca/eng/acts/P-8.6/ *(not fetched; principle numbers from the existing notice S1; verify)*
- S2 OPC, Guidelines on privacy and online behavioural advertising. https://www.priv.gc.ca/en/privacy-topics/advertising-and-marketing/behaviouraltargeted-advertising/gl_ba_1112/ *(fetch refused; search summary: browsing activity needs knowledge and consent; opt-out acceptable for non-sensitive information; tracking information is generally PI. Verify.)*
- S3 OPC website terms (IP address treated as PI; OPC anonymizes IP in its own analytics). https://priv.gc.ca/en/privacy-and-transparency-at-the-opc/terms-and-conditions-of-use/ *(search summary only)*
- S4 OPC, PIPEDA legislation and related regulations / provincial laws. https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/r_o_p/ *(search summary: AB, BC, QC general laws substantially similar; Ontario only for health information. Verify.)*
- S5 Quebec, Act respecting the protection of personal information in the private sector, CQLR c. P-39.1, ss. 8, 8.1, 8.2, 9.1. Official: https://www.legisquebec.gouv.qc.ca/en/document/cs/P-39.1 *(403 from here)*. Text read from the unofficial consolidation https://www.lavery.ca/upload/pdf/Publications/Amended-Private-Sector-Act-P-39-1.pdf *(fetched; "does not have official status")*. "Off by default" reading: commentary such as https://mccarthy.ca/en/insights/blogs/techlex/quebecs-law-25-and-cookies-not-so-cookie-cutter *(search only)*. s. 17 not read.
- S6 EDPB Guidelines 2/2023 on the Technical Scope of Art. 5(3) ePrivacy Directive, v2.0, adopted 7 Oct 2024. https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-22023-technical-scope-art-53-eprivacy-directive_en *(PDF fetched and read: ¶¶30–39, 40, 42–44, 51, 53–56, 62–63)*
- S7 CNIL, "Cookies : solutions pour les outils de mesure d'audience" (page dated 4 Jul 2025). https://www.cnil.fr/fr/cookies-et-autres-traceurs/regles/cookies-solutions-pour-les-outils-de-mesure-daudience *(fetched)*
- S8 AEPD, "Guía Uso de cookies para herramientas de medición de audiencia", v. Jan 2024. https://www.aepd.es/guias/guia-cookies-analiticas-externas.pdf *(fetched, §§II–III read)*. AEPD Guía sobre el uso de las cookies, May 2024. https://www.aepd.es/guias/guia-cookies.pdf *(fetched; analytics passage read)*
- S9 Garante, Linee guida cookie e altri strumenti di tracciamento, 10 Jun 2021 (doc. web 9677876). https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/9677876 *(fetched, §§3 and 7.2)*
- S10 Traficom, Guidance on the use of web cookies for service providers (valid from 13 Sep 2021). https://traficom.fi/en/regulations/guidance-use-web-cookies-service-providers *(landing page fetched; PDF with the analytics text not read)*
- S11 Finnish analytics positions, secondary: https://www.twobirds.com/en/trending-topics/global-cookie-review/finland ; https://finland.dlapiper.com/en/news/recent-court-rulings-emphasise-cookie-legislation-enforcement-finland *(search only)*. Act 917/2014 s. 205: https://www.finlex.fi *(not fetched)*
- S12 Bulgaria, conflicting secondary sources: https://www.mondaq.com/data-protection/1191920/cookies ; https://www.consentstack.io/regulations/bg-eca *(search only)*
- S13 GDPR, Regulation (EU) 2016/679, Arts. 3(2), 6(1)(f), 13. https://eur-lex.europa.eu/eli/reg/2016/679/oj *(fetched earlier on 2026-11-16 for the notice; Art. 3(2) and 6(1)(f) wording to verify)*
- S14 KVKK, Çerez Uygulamaları Hakkında Rehber, KVKK Yayınları No. 69, July 2025, §§4 and 5.9, and the transfer section. https://kvkk.gov.tr/Icerik/7353/Cerez-Uygulamalari-Hakkinda-Rehber *(PDF fetched and read)*

## Needs licensed counsel
1. Whether the anonymous `site_event` data is "personal information" under PIPEDA when the IP is used in transit only and never stored, and whether a privacy-notice disclosure plus a GPC/DNT opt-out meets PIPEDA consent for it.
2. Quebec: whether P-39.1 applies to an Ontario business collecting from Quebec visitors online; whether IP-derived `country` is a "locate" function under s. 8.1; and whether s. 17 (communication outside Quebec) needs a PIA for Quebec form submissions stored in the US.
3. EU: whether GDPR applies to us under Art. 3(2), and which Member State's Art. 5(3) transposition binds a non-EU publisher without an establishment. Whether the CNIL, AEPD and Garante exemptions extend to a memory-only, per-page-load id (they are drafted for cookies and "similar technologies").
4. Finland: whether any exemption exists for first-party, cookieless, non-identifying measurement, and whether C8(b) (suppressing EU-origin events in transit) is acceptable.
5. Bulgaria: the current rule (opt-in vs opt-out) and any CPDP position on analytics.
6. Hidden attribution fields: whether the intro-line sentence is enough notice in Canada and the EU, and whether reading UTM/referrer into a named request needs Art. 5(3) consent for EU visitors (C9).
7. Türkiye: whether KVKK applies to a Canadian site with a `tr` locale, and how the Art. 9 cross-border transfer rules affect US storage of Turkish visitors' data.
8. Whether a device-stored "measurement off" flag (C3, persistent version) is exempt as strictly necessary in each EU market.
9. Retention: 90 days raw and 25 months aggregate.


## Decision (CPO, 2026-11-16)
- Events are sent only from the en, fr, es, it and tr locales; nothing from fi, bg or ar (resolves C8 Finland, Bulgaria and Arabic unknowns by not measuring).
- No `country` property (resolves the Quebec s. 8.1 "locate" concern as far as we can tell).
- Still open: C9 (hidden UTM/referrer fields on EU locales), retention (Farjad Iranmehr to approve), GPC/DNT opt-out implementation (cp-website).
- Privacy notice v0.4.1 §3a + Part B reflect this.
