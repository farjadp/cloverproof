# CloverProof privacy notice (website + pilot) — DRAFT v0.5.2

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> Drafted by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO. v0.1 2026-11-16; v0.2 2026-11-16 (CPO decisions D4 + R4); v0.2.1 2026-11-16 (CPO decision D-7); v0.3 2026-11-16 (website measurement, CPO option A — see `website-measurement-review.md`); v0.4 2026-11-16 (Farjad Iranmehr decisions: OQ-06 residency + approval kinds — `origin/cpo-decisions-sa-fe-residency:CLAUDE.md` rule 8 and "Launch market + residency"); v0.5 2026-11-16 (Farjad Iranmehr decision: website form stays open, notes field removed, website data in the US on Railway until Canadian hosting is live); v0.5.1 2026-11-17 (Hebrew); v0.5.2 2026-11-17 (security log of the private website admin area — `origin/docs/website-admin-plan`, ADR 0011/0013 drafts).
> Status: draft. Do not publish until every `[PLACEHOLDER]` is filled and counsel has reviewed it (OQ-07, see `oq-07-decision-pack.md`).

**What changed in v0.2**
- D4: plan review is now described as *AI-assisted, human-approved*. An AI system (`cp-agronomist`) may check a plan; only a named human agronomist can approve a real farm's plan, and nothing reaches a farmer before that. The founder is **not** described as the agronomist anywhere.
- R4: pilot eligibility = farms in **Ontario, Canada** (another Canadian province only if we extend the pilot in writing; Quebec excluded). GDPR text is kept but reduced to EU/EEA **website visitors**.
- D-7 (CPO, 2026-11-16, policy): the AI reviewer `cp-agronomist` never receives real pilot farmers' personal data or identifiable farm data — only published sources, synthetic cases and de-identified case data (no names, contacts, addresses or exact field geometry). §4, §6, §8 and Part B updated. Any change needs a DPA with the AI provider AND an update to this notice, decided by Farjad Iranmehr.
- v0.3 (website measurement, CPO option A): new §3a and Part B section "Website measurement"; §2, §3, §6, §8 and Part B "Who sees it" updated, because the site will no longer be analytics-free. Written for the **recommended** design in `website-measurement-review.md` §2: no `country`, GPC/DNT honoured, raw events 90 days then daily totals 25 months. If the CPO keeps `country` or rejects C2/C4, this text must change before publication.

**What changed in v0.4**
- OQ-06 (decided 2026-11-16): **real pilot data** (farmer contacts, farms, fields, soil tests, plans, reviews, proof PDFs) **is stored in Canada**, at `[CANADIAN HOSTING PROVIDER, REGION]` (hosting ADR pending, owner `cto` + `devops-engineer` with `ciso`). The US/Canada either-or for pilot data is removed (§2, §6, §7, Part B). Until Canadian hosting is live, hosted environments hold only synthetic or de-identified data, so **no real pilot data is collected into hosted systems before then** — the notice says so.
- Website pilot-request form and website measurement data: location is `[WEBSITE DATA LOCATION — confirm in hosting ADR]`. A US-transfer sentence is kept only as a bracketed option (§7, Part B) until the ADR decides. *(Superseded by v0.5.)*
- Approvals (decided 2026-11-16): every plan is approved by a **named human** before a farmer sees it — either a human agronomist (`agronomist_approved`) or a CloverProof superadmin without agronomist credentials (`superadmin_approved`). The notice says each plan shows which kind, and never calls a superadmin approval an agronomist review (§1, §2, §3, §4, §9, §10, Part B). AI never approves (D-7 text unchanged). **Only agronomist-approved plans feed calibration** (§3, §5, Part B).
- v0.4.1 (coo, CPO decision 2026-11-16): §3a + Part B say events are recorded only on en/fr/es/it/tr; nothing from fi/bg/ar; no `country`; §3a storage aligned to `[WEBSITE DATA LOCATION — confirm in hosting ADR]` (Railway US text removed).
- v0.5.1 (coo, 2026-11-17): Hebrew (`he`) added to the versions that record nothing (§3a, Part B); Israel review in `website-measurement-review.md` §1a.
- Engineering dependency: the plan screen and proof PDF must actually display the approval kind and approver name as described in §4. *(Not verified in the repo — `cp-pdf` / `cp-concierge-app` to confirm before publication.)*

**What changed in v0.5** (decision by Farjad Iranmehr, 2026-11-16)
- The website pilot-request form stays open now.
- The free-text **notes** field is removed from the form; "notes" is removed from what we collect from the form (§3 table, Part B "What we collect"). "AI check notes" (§3, §5) and "notes" in the calibration removal list (§5) are unrelated and kept. *(Engineering dependency: on main, `website/src/app/[lang]/actions.ts` still reads and stores `notes`, `website/src/messages/en.json` still has `pilot.notes`, and `pilot_request.notes` exists in `website/db/migrations/0001_pilot_request.sql`. This notice must not be published until `cp-website` removes the field; what happens to notes already stored is a `cp-database` / `ciso` decision — not decided here.)*
- Website data location decided: **until Canadian hosting is live, pilot-request form data and website measurement data (same database) are stored in the United States by our website host, Railway** (Railway DPA: primary processing in the US — S15 §9.1; no Canadian region — S14). **When Canadian hosting is live, this data moves to Canada** at `[CANADIAN HOSTING PROVIDER, REGION]`, and we update this notice. `[WEBSITE DATA LOCATION — confirm in hosting ADR]`, `[WEBSITE HOST]` and the bracketed Railway options are replaced with definitive text (§2, §3a, §6, §7, §8, EU transfer line, Part B). `[RAILWAY REGION]` is not used: Railway's DPA gives the US as the primary processing location.
- Real pilot farm data unchanged: stored in Canada; not collected into hosted systems until Canadian hosting is live.

**What changed in v0.5.2** (coo, 2026-11-17; input `origin/docs/website-admin-plan:docs/plans/website-admin.md` §4–§5, §10 Q5 and draft ADRs 0011 + 0013 on that branch — **plan not approved**)
- Decision: **yes, the public notice needs it.** The `/admin` security log (`website_log`) keeps a shortened IP (IPv4 /24, IPv6 /48), browser family, time, action and outcome for 60 days, and records failed sign-ins by anyone, so members of the public can be in it. A /24 prefix with an exact timestamp, browser family and the host's own full-IP request logs (§3 "Technical logs kept by our host") can plausibly single out a person or household; under the OPC "serious possibility" test (S38) and the CJEU *Breyer* reasoning (S40) we treat it as personal information. The login-throttling table also keeps keyed hashes (HMAC) of the shortened IP and of the email typed (ADR 0011). Disclosure costs one paragraph; omission would make the §3a/Part B "we do not store your IP address" read as a site-wide promise that the admin breaks.
- New §3b; new rows in §3 and §8; §2 bullet; §3a "What we do not record" re-scoped to measurement ("our measurement records never contain your IP address") with a pointer to §3b; Part B: measurement sentence re-scoped, new section "Security log of our staff area", "Who sees it" and "How long we keep it" extended.
- Facts taken from the plan/ADRs: logged fields `occurred_at`, `actor_user_id` (null for anonymous), `kind`, `action`, `target_type/id`, `outcome` (ok/denied/failed), `ip_prefix`, `ua_family`, whitelisted `detail`; never passwords, tokens, keys, TOTP codes, post bodies, form values, emails of non-users, full URLs with query strings; **public-site errors carry no IP prefix** (ADR 0013). Only the `admin` role can view/export the log (ADR 0011 role table). Staff-side detail is in `admin-staff-notice.md`.
- Engineering dependencies (not verified — nothing is built): ship §3b and the Part B section **with** admin P1, not before; the rate-limit rows must be purged within 24 h or the "within a day" wording changes; the log viewer's CSV export creates copies outside the 60-day purge (staff notice rule; counsel item 14).

Open placeholders (Farjad Iranmehr must supply): `[LEGAL ENTITY]`, `[CONTACT EMAIL]`, `[ADDRESS]`, `[PRIVACY OFFICER NAME]`, `[CANADIAN HOSTING PROVIDER, REGION]` (also the future location of website data), `[AI PROVIDER]`, `[HUMAN AGRONOMIST NAME, CREDENTIALS]`, `[EMAIL PROVIDER]`, `[EFFECTIVE DATE]`, and the retention periods marked *proposed*.

Sources are listed at the end (S1–S23), with the date checked. Facts about our systems come from the repo (`website/db/migrations/0001_pilot_request.sql`, `db/migrations/0003–0009`, `website/src/app/[lang]/actions.ts`, ADR 0004, ADR 0005) and from `docs/plans/backend-plan-reconciliation.md` on `origin/backend-traceability` (D4, R4).

---

## Part A — Full privacy notice (publish as the long-form notice)

### 1. Who we are
CloverProof is operated by **[LEGAL ENTITY]**, [ADDRESS], Ontario, Canada ("we", "us"). We are responsible for the personal information described here.
Privacy contact: **[PRIVACY OFFICER NAME]**, [CONTACT EMAIL], [ADDRESS].

CloverProof is software that turns farm data into a field-specific fertilizer plan. An AI system may help check each plan; a named person approves every plan before you see it — either our human agronomist or a CloverProof administrator who is not an agronomist — and each plan says which (section 4). Each approved plan comes with a proof PDF that records how it was made.

### 2. The short version
- We collect only what we need to run the website and the pilot.
- The 2027 pilot is open to farms in **Ontario, Canada** only.
- **A person, not software, approves your plan.** An AI system may help check a plan, but no plan reaches you until a named person has approved it: either our human agronomist, [HUMAN AGRONOMIST NAME, CREDENTIALS], or a CloverProof administrator who is not an agronomist. Every plan shows which of the two approved it.
- We do not sell your information. We use no advertising trackers, no cookies and no analytics company. We count how the website is used ourselves, without identifying you (section 3a). *(Re-check before every release: no third-party analytics or tracking dependency in `website/package.json`; measurement matches §3a.)*
- Your pilot farm data is stored in **Canada**, at [CANADIAN HOSTING PROVIDER, REGION]. We do not collect real pilot data into our hosted systems until that Canadian hosting is live. Until Canadian hosting is live, your website pilot request and our website measurement data are stored in the **United States** by our website host, Railway. When Canadian hosting is live, this data moves to Canada and we will update this notice. See section 7.
- If anyone tries to sign in to our private staff area, a security log keeps a shortened IP address and the browser type for 60 days, then deletes it automatically (section 3b).
- With your permission, we use **de-identified** results from agronomist-approved plans to improve our engine.
- You can ask to see, correct or delete your information at any time: [CONTACT EMAIL].

### 3. What we collect and why

| What | When | Why |
|---|---|---|
| Name, email, country, farm size (as typed), main crop, the language you used, the exact consent wording you agreed to and the time | You send the pilot request form | Decide whether we can include your farm in the pilot and contact you about it |
| With your request: the campaign tag of the link you followed (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`), the name of the website that sent you (host only, e.g. `google.com`), and your field-check result if you did the check | You send the pilot request form | Know how you found us and which outreach works; prepare for your farm. These are linked to you once stored with your request |
| Website measurement: page, language, time, button clicks, field-check answers, form steps, link campaign tag, referring site name, mobile/desktop | Each page load, unless your browser sends Global Privacy Control or Do Not Track | Improve the website and our outreach — not linked to you (section 3a) |
| Contact details (name, email, phone if given), farm name, region | You join the pilot | Run the pilot and talk to you |
| Field names, field area, field boundary or location (if given), crop, target yield, previous crop, plan dates | During the pilot | Calculate the plan for each field |
| Soil-test results (lab, date, depth, method, values) | During the pilot | Calculate P and K advice; without a soil test we give nitrogen advice only |
| Engine output, AI check notes, the approver's final numbers, the reason for any change, review time, and who approved the plan (name and kind: agronomist or CloverProof administrator) | During the pilot | Check and approve every number before it reaches you; show you who approved it; keep an unchangeable record of how each plan was made |
| What you actually applied (product, rate, date) | If you choose to tell us | Compare plan with practice |
| Proof PDF and its fingerprint (SHA-256) | When a plan is approved by a named person (agronomist or CloverProof administrator) | Give you a record of the plan and let anyone check the file has not been changed |
| De-identified comparison of engine output vs the human agronomist's final numbers ("calibration data") — agronomist-approved plans only | During and after the pilot | Improve the engine's accuracy for future users — **with your separate consent** (section 5) |
| Technical logs kept by our host (IP address, browser, time, page) | Every website visit | Keep the site running and secure |
| Security log of our private staff area (`/admin`): time, what was attempted (e.g. sign-in) and the result, shortened IP address (IPv4: last of four parts removed; IPv6: only the first 48 bits kept), browser type (e.g. "Firefox"); for staff, also the staff account | Someone signs in to, or tries to sign in to or use, the staff area — this can be a member of the public | Protect the website and its staff area from break-ins and abuse; investigate incidents (section 3b) |
| Sign-in throttling counters: a keyed, one-way scrambled form (HMAC) of the shortened IP and of the email typed on the staff sign-in page, with a count | Someone tries to sign in to the staff area | Slow down password guessing (section 3b) |
| News or marketing emails | Only if you tick the separate box | Send you CloverProof news (CASL express consent) |

Information about your farm and fields is treated as personal information when it can be linked to you (for example, a sole-proprietor farm). *(Assumption — counsel to confirm; S1, S11 Art. 4(1).)*

We do not ask for and do not want: government ID numbers, bank details, health information, or information about children.

### 3a. Website measurement
We count how our website is used, so we can see which pages and links help farmers find the pilot and where people get stuck. We do this ourselves, on our own database. No analytics company, advertising network or social-media pixel is involved.

**What we record for each page load:** the page and language; the time; which of our buttons and links you click; your answers in the field check (for example "soil test: yes / no / not sure") and its result; which step of the pilot form you reach, and whether sending it worked; the campaign tag in the link you followed (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`); the name of the website that sent you (for example `google.com`, never the full address); and whether your screen is mobile- or desktop-sized. Each page load gets a random number that exists only in your browser's memory while the page is open, so we can put the clicks of that one page view in order. It disappears when you leave or reload the page.

**What we do not record:** we put no cookies or anything else on your device (no local storage); we do not record your name, email or anything you type into the form; our measurement records never contain your IP address (we use it only while your request travels to us, to filter out automated traffic) or your full browser identifier; we do not fingerprint your device; we do not link one visit to another or to you; we do not follow you on other websites; and we do not share or sell this data.

(Separately, if you try to sign in to our private staff area, a security log keeps a shortened IP address for 60 days — section 3b. Ordinary visits to our public pages are not in that log.)

**Which pages:** we record this only on the English, French, Spanish, Italian and Turkish versions of the website. The Finnish, Bulgarian, Arabic and Hebrew versions record nothing.

**Where and how long:** in our own database, which until Canadian hosting is live is stored in the United States by our website host, Railway; when Canadian hosting is live it moves to Canada (section 7). Detailed records are kept for 90 days, then combined into daily totals and deleted; daily totals are kept for up to 25 months. *(Proposed — Farjad to approve.)*

**Turning it off:** if your browser sends a Global Privacy Control or Do Not Track signal, we record nothing about your visit. The website and the pilot form work the same either way.

**If you send a pilot request**, the campaign tag of the link you followed, the name of the website that sent you and your field-check result are stored with your request (section 3) and are then linked to you. We use them to know how you found us and to prepare for your farm, and keep them for as long as your request (section 8).

*Why no consent banner (for reviewers, not for publication): see `website-measurement-review.md` §1 — Canada/Ontario: notice + opt-out; EU: CNIL/AEPD/Garante audience-measurement exemptions as far as we can tell; Finland (consent likely needed), Bulgaria and Arabic-speaking markets (unknown): resolved by CPO decision 2026-11-16 — no events are sent from the fi, bg, ar or he locales (he: CPO decision 2026-11-17, pending Israel review acceptance — `website-measurement-review.md` §1a), and no `country` property is recorded; Türkiye scope: unknown, events sent (tr). Hidden attribution fields on EU locales (C9): open. EU/EEA legal basis: legitimate interests (GDPR Art. 6(1)(f)); you can object (section 10).*

### 3b. Security log of our private staff area
Our website has a private area where CloverProof staff manage the site (`/admin`). It is not meant for the public, but anyone can reach its sign-in page.

**What we record:** when someone signs in, tries to sign in, or tries to use the staff area, our security log records the time, what was attempted (for example a sign-in or a password reset) and whether it worked, was refused or failed, a **shortened** version of the IP address (for IPv4 we remove the last of its four parts; for IPv6 we keep only the first 48 bits), and the browser type (for example "Firefox", not the full browser identifier). For our staff it also records which staff account acted and what it did. The log never contains passwords, sign-in codes, keys, anything typed into a form, or the email address typed by someone who is not on our staff. Ordinary visits to our public pages, and errors on them, are not recorded in this log.

**Sign-in throttling:** to slow down password guessing we count recent sign-in attempts using a keyed, one-way scrambled form of the shortened IP address and of the email typed. These counters are deleted within a day.

**Why:** only to keep the website and its staff area secure — to detect and block break-in attempts and abuse, and to investigate a security incident. We do not use it for marketing or measurement, and we do not try to find out who is behind a shortened IP address unless we need to for a security incident or the law requires it.

**Who sees it:** only CloverProof administrators, and Railway as our website host.

**Where and how long:** in our website database, which until Canadian hosting is live is stored in the United States by Railway (section 7). The log is deleted automatically after **60 days**. *(Proposed — Farjad to approve with the admin plan.)*

**EU/EEA:** our legal basis is our legitimate interest in keeping our network and website secure (GDPR Art. 6(1)(f); Recital 49 — S39). You can object (section 10). Because the log holds only a shortened IP address, we may not be able to find records about you unless you tell us roughly when and from which network you tried to sign in (GDPR Art. 11 — S41).

*(Reviewer note, not for publication: Quebec P-39.1 s. 8.1 — we derive no location from the prefix and build no profile, so s. 8.1 likely does not bite (S5 in `website-measurement-review.md`; counsel). Israel — Amendment 13 lists IP addresses as personal information (S15 there); the admin is English-only and not aimed at Israel; same scope question as `website-measurement-review.md` counsel item 10.)*

### 4. How plans are reviewed — AI assists, a person decides
1. Our software (the engine) calculates a proposed plan from your data.
2. An **AI system** may check a **de-identified** copy of the proposal (for example, consistency of the numbers and the plain-language explanation) and leave notes. Before the AI sees it, we remove your name, contact details, address, farm and field names, and exact field boundaries or coordinates; it sees only the region (county level), crop, previous crop, target yield, soil-test values and plan date. The AI system never receives information that identifies you or your farm. *(D-7, `oq-07-decision-pack.md`; whether county-level region plus field values could still identify a farm is a counsel question — Needs licensed counsel item 3.)*
3. A **named person** approves, changes or rejects every number. That person is either:
   - our **human agronomist**, [HUMAN AGRONOMIST NAME, CREDENTIALS] — the plan is marked "Approved by agronomist"; or
   - a **CloverProof administrator who is not an agronomist** — the plan is marked "Approved by CloverProof administrator (not an agronomist review)".
   Your plan and its proof PDF show which kind of approval it received and the approver's name. We never describe an administrator approval as an agronomist review. An AI check alone can never approve a plan for your farm; our system blocks it.
4. Only an approved plan is sent to you. You keep the final decision about what you apply. If you want an agronomist's review of a plan approved by an administrator, ask us at [CONTACT EMAIL]. *(Whether to offer this is a business decision — Farjad Iranmehr; delete the sentence if not offered.)*

No decision about you is made by software or AI alone (S11 Arts. 13(2)(f), 22; S23). You can ask us how a number in your plan was produced; every plan shows the reason for each number and its confidence level.

### 5. Using pilot results to improve the engine (calibration)
The difference between what the engine proposed and what the human agronomist approved tells us where the engine is wrong. We use **only plans approved by our human agronomist** for this; plans approved by a CloverProof administrator are not used. With your consent we keep a **de-identified** copy of this comparison:
- removed: your name, email, phone, farm name, field names, notes, exact field boundaries and coordinates;
- generalised: location to province or a coarse region, dates to season (month or year);
- kept: crop, previous crop, target yield, soil-test values and method, engine version, engine output, the human agronomist's final numbers and reason (with any names removed from the text).

AI check notes and administrator approvals are not counted as agronomist decisions in this comparison.

De-identified data can sometimes be re-identified when combined with other information. We keep it access-restricted, do not publish it at field level, and do not try to re-identify anyone. You can say no to this use and still take part in the pilot. You can withdraw later; we will then stop adding your data and remove what can still be linked to you. *(Whether calibration can be a condition of the pilot instead of optional is a counsel question — `oq-07-decision-pack.md` §3 Q8.)*

### 6. Who we share it with
We do **not** sell, rent or trade personal information. We use no analytics or advertising company; website measurement (section 3a) runs on our own database. We share personal information only with:
- **[CANADIAN HOSTING PROVIDER]** — stores pilot farm data (contacts, farms, fields, soil tests, plans, reviews, proof PDFs) in [REGION], Canada, as our service provider under a data-processing agreement. *(Provider and contract set by the hosting ADR.)*
- **Railway Corporation (United States)** — hosts our website and, until Canadian hosting is live, stores pilot-request form data, website measurement data and the staff-area security log (section 3b) in the United States, as our service provider under its Data Processing Addendum (S15). When Canadian hosting is live, this data moves to [CANADIAN HOSTING PROVIDER, REGION].
- **No AI provider receives information that identifies you or your farm.** The AI system that may check plans ([AI PROVIDER]) receives only de-identified case data as described in section 4 — no names, contact details, addresses, farm or field names, or exact field geometry. We will not send identifiable pilot data to any AI provider unless we first sign a data-processing agreement with it and update this notice. *(D-7. Confirm the provider's retention and no-training terms for the de-identified data before use.)*
- **[EMAIL PROVIDER]** — if we use one to send email. *(None in the repo today; fill or delete.)*
- **[HUMAN AGRONOMIST NAME]** — if the agronomist is a contractor rather than an employee, under a written confidentiality and data-processing agreement. *(Fill or delete.)*
- **Anyone you ask us to share with** — for example, if you give a proof PDF to your lender or certifier, you choose to share it.
- **Authorities** — only where the law requires it.

The proof PDF records how a plan was made. It is not accepted, approved or endorsed by any lender, certifier, insurer, buyer or regulator.

### 7. Where your information is stored
**Pilot farm data.** Your pilot data — contact details, farm, field and soil-test information, plans, reviews and proof PDFs — is stored in **Canada**, at [CANADIAN HOSTING PROVIDER, REGION]. Until that Canadian hosting is live, our hosted systems hold only made-up test data or de-identified data, and we do not collect real pilot data into them. *(Decision 2026-11-16; hosting ADR pending. Update this paragraph if the ADR adds any non-Canadian processing, e.g. backups, support access or sub-processors.)*

*[If the chosen provider is US-owned, keep:]* Our provider is owned by a US company. Even though your data is stored in Canada, the provider may be required to give access to it under US law (S4).

**Website form and website measurement data.** Until Canadian hosting is live, pilot-request form data and website measurement data (they are in the same database) are stored in the **United States** by our website host, Railway. Railway states that its primary processing is in the United States (S15 §9.1); Railway has no Canadian region (S14). Your website request may be stored and accessed in the United States, where it may be available to US courts, law enforcement and national-security authorities under US law (S4). When Canadian hosting is live, this data moves to Canada, at [CANADIAN HOSTING PROVIDER, REGION], and we will update this notice.

We stay responsible for your information when our providers process it, and we use contracts to require comparable protection (S4).

*EU/EEA visitors to our website:* we collect your form data directly from you in Canada, which the EU recognises as adequate (S12). Until Canadian hosting is live, Railway processes it in the United States; for that transfer, Railway's DPA provides the EU Standard Contractual Clauses (S15 §9). *(Counsel to confirm — `oq-07-decision-pack.md` §3 Q9.)*

### 8. How long we keep it (*proposed — Farjad to approve*)
| Data | Proposed retention |
|---|---|
| Pilot request not accepted, or no reply | 12 months after the decision, then deleted |
| Pilot farm, field, soil-test, plan, review and proof records | Pilot season + 2 years (so you can use your plan records), then deleted or de-identified |
| Calibration data (de-identified, with consent) | Until the engine is retired or you withdraw consent, whichever is first |
| Marketing consent record | While you are subscribed + 3 years (proof of consent) |
| Deletion request record (who, what, when — no farm data) | 3 years |
| Host technical logs | As set by our hosts — Railway (United States) for the website until Canadian hosting is live, then [CANADIAN HOSTING PROVIDER]; *[confirm log retention for Railway and [CANADIAN HOSTING PROVIDER]]* |
| Security log of the private staff area (shortened IP, browser type, time, action, result) | 60 days, then deleted automatically by a daily job |
| Sign-in throttling counters (keyed hashes of shortened IP and typed email) | Deleted within a day |
| Website measurement, detailed records (not linked to you) | 90 days, then combined into daily totals and deleted |
| Website measurement, daily totals | Up to 25 months |
| Link campaign tag, referring site, field-check result stored with a pilot request | Same as the pilot request |
| AI provider copies (de-identified case data only; no identifiable pilot data — D-7) | *[confirm provider retention; target: none beyond the request]* |
| Breach records | At least 24 months after we determine a breach occurred (S5) |

### 9. How we protect it
Server-only database access; private file storage; passwords hashed (argon2id); session tokens stored only as hashes; access limited to the CloverProof team members who need it; every plan record is write-once so it cannot be silently changed; only a named human — our agronomist or a CloverProof administrator — can approve a real farm's plan, and AI or automated accounts never can; pilot farm data is stored in Canada. No system is perfectly secure. If a breach creates a real risk of significant harm to you, we will tell you and report it to the Privacy Commissioner of Canada as required (S5), and to EU authorities where GDPR requires it (S11 Arts. 33–34).

### 10. Your rights
You can ask us to:
- tell you what we hold about you and give you a copy;
- correct it;
- delete it;
- explain how a number in your plan was produced, who approved it, and whether that person is an agronomist;
- stop using it for calibration or marketing (withdraw consent);
- *(EU/EEA website visitors)* restrict or object to processing, and receive your data in a portable format.

Email [CONTACT EMAIL] or write to [ADDRESS]. We may ask you to confirm your identity. We reply within 30 days (S1 s.8(3), to verify) and, for EU/EEA requests, within one month (S11 Art. 12(3)).

**Deletion and the plan record.** Approved plans and proof PDFs are stored write-once so nobody can alter them. When you ask for deletion we remove or irreversibly de-identify everything that links those records to you (names, contacts, farm and field names, location). If we must keep anything (for example, to defend a legal claim), we will tell you what and why. *(Engineering gap: the database currently blocks deletion of these records — compliance-review.md G2.)*

### 11. Unsubscribing
Every marketing email has an unsubscribe link. We act on it within 10 business days at most (S6 s.11(3), S9) — in practice, straight away.

### 12. Complaints
Contact us first. You can also complain to:
- the **Office of the Privacy Commissioner of Canada**: https://www.priv.gc.ca;
- *(EU/EEA website visitors)* the data-protection authority where you live or work.

### 13. Children
CloverProof is for farm businesses and is not directed to anyone under 18. *(Age threshold to be confirmed by counsel.)*

### 14. Changes
We will post changes here with a new date and tell pilot farms by email before a material change takes effect (for example, if we change who approves plans or where data is stored).

Effective date: [EFFECTIVE DATE]. Version: 0.5.2-draft.

---

## Part B — Website privacy-page copy (hand to `cp-website`, NB-WEB-05)

Shape matches `website/src/messages/en.json` → `privacy` (keys `title`, `draft`, `updated`, `sections[] {h, p}`). English only; other locales only after native review (ADR 0003). Replace placeholders before release; keep `draft` until counsel signs off. Copy of this Part B: `side-session-notes/.../coo-website-privacy-copy.md`.

```json
{
  "title": "Privacy notice",
  "draft": "Draft — under review before launch.",
  "updated": "Last updated: [EFFECTIVE DATE]",
  "sections": [
    {
      "h": "Who we are",
      "p": "CloverProof is operated by [LEGAL ENTITY], [ADDRESS], Ontario, Canada. Privacy questions: [CONTACT EMAIL]."
    },
    {
      "h": "Who can join the pilot",
      "p": "The 2027 pilot is open to farms in Ontario, Canada. You can send a request from anywhere, but we can only include Ontario farms."
    },
    {
      "h": "What we collect",
      "p": "When you request a pilot plan we collect what you enter: name, email, country, approximate farm size, main crop, plus the language you used and the exact consent wording you agreed to, with the time. If you join the pilot we also collect farm, field and soil-test information and the plans we make for you."
    },
    {
      "h": "Why we collect it",
      "p": "To decide whether we can include your farm in the pilot, to contact you about it and, if you join, to make and record your fertilizer plans. We send news emails only if you tick the separate box for them."
    },
    {
      "h": "Website measurement",
      "p": "We count how this website is used, ourselves, with no analytics company and no cookies or other storage on your device. We do this only on the English, French, Spanish, Italian and Turkish versions of the site; the Finnish, Bulgarian, Arabic and Hebrew versions record nothing. For each page load we record the page, language and time, the buttons you click, your field-check answers and result, the form step you reach and whether sending worked, the campaign tag of the link you followed, the name of the website that sent you (not the full address) and whether your screen is mobile or desktop size. A random number held only in your browser's memory groups the clicks of one page view and disappears when you leave. We do not record your name, email or anything you type, these measurement records never contain your IP address, and we do not link visits to each other or to you. Detailed records are kept 90 days, then turned into daily totals kept up to 25 months. If your browser sends Global Privacy Control or Do Not Track, we record nothing. If you send a pilot request, the link's campaign tag, the referring website and your field-check result are stored with your request, so we know how you found us."
    },
    {
      "h": "Security log of our staff area",
      "p": "Our website has a private area for CloverProof staff. If anyone, including a member of the public, signs in, tries to sign in or tries to use it, our security log records the time, what was attempted and whether it worked, a shortened IP address (the end of it removed) and the browser type (for example Firefox). It never records passwords, codes or anything typed into a form. To slow down password guessing we also keep counters based on a scrambled form of the shortened IP address and the email typed; they are deleted within a day. We use this only to keep the website secure. Only CloverProof administrators can see the log, and it is deleted automatically after 60 days. Until Canadian hosting is live it is stored in the United States by Railway. Ordinary visits to our public pages are not in this log. If you are in the EU, we rely on our legitimate interest in keeping the site secure, and you can object."
    },
    {
      "h": "How plans are reviewed",
      "p": "Our software proposes each plan. An AI system may help check it. The AI system never receives your name, contact details, address or exact field boundaries; it sees only de-identified case data. A named person then approves, changes or rejects every number before you see it: either our human agronomist or a CloverProof administrator who is not an agronomist. Your plan and its proof PDF show which of the two approved it and their name; we never call an administrator approval an agronomist review. An AI check alone never approves a plan. You make the final decision about what you apply."
    },
    {
      "h": "Improving the engine",
      "p": "If you agree, we keep a de-identified copy of pilot results (the engine's proposal vs the human agronomist's final numbers) to make the engine more accurate. We use only plans approved by our human agronomist, not plans approved by an administrator. Names, contact details, farm and field names and exact locations are removed. You can say no and still take part."
    },
    {
      "h": "Who sees it",
      "p": "Only the CloverProof team members who need it, our human agronomist, [CANADIAN HOSTING PROVIDER], which stores pilot data in Canada, and Railway, a US company that hosts our website and, until Canadian hosting is live, stores website requests, website measurement data and the staff-area security log in the United States, as our service providers. No AI provider receives information that identifies you or your farm. We do not sell your information and we do not use advertising trackers or any analytics company."
    },
    {
      "h": "Where it is stored",
      "p": "Pilot farm data (contacts, farms, fields, soil tests, plans, reviews and proof PDFs) is stored in Canada, at [CANADIAN HOSTING PROVIDER, REGION]. We do not collect real pilot data into our hosted systems until that Canadian hosting is live. [IF US-OWNED PROVIDER: Our provider is owned by a US company, so it may be required to give access under US law even though the data is in Canada.] Until Canadian hosting is live, website requests and website measurement data are stored in the United States by our website host, Railway, a US company, where US authorities may be able to access them under US law. When Canadian hosting is live, this data moves to Canada and we will update this notice. We use data-processing contracts to protect your information."
    },
    {
      "h": "How long we keep it",
      "p": "Pilot requests we can't accept: 12 months. Pilot records: the pilot season plus 2 years. De-identified engine data: until you withdraw consent or we retire the engine. Staff-area security log: 60 days. You can ask us to delete your details at any time."
    },
    {
      "h": "Your rights",
      "p": "You can ask to see, correct or delete your information, ask how a number in your plan was produced and who approved it, and withdraw consent at any time, by emailing [CONTACT EMAIL]. We reply within 30 days. You can complain to the Office of the Privacy Commissioner of Canada (priv.gc.ca) or, if you are in the EU, to your local data-protection authority."
    }
  ]
}
```

Notes for `cp-website`:
- Do not ship while any `[...]` remains. "Where it is stored": keep the bracketed US-owned-provider sentence only if the hosting ADR makes it true; delete it otherwise. Pilot data in Canada and website data in the US on Railway until Canadian hosting is live are decided (Farjad Iranmehr, 2026-11-16); when the website data moves to Canada, this section and "Who sees it" must be updated the same day.
- Notes field removed (Farjad Iranmehr, 2026-11-16): do not ship this copy until the form, `actions.ts` and the stored data no longer collect `notes`.
- Approval kind: the "How plans are reviewed" text promises the plan and proof PDF show "agronomist" vs "CloverProof administrator (not an agronomist review)" and the approver's name. Do not ship until the app and PDF do that.
- D-7 (decided): the AI system gets de-identified data only; do not add an AI provider to "Who sees it" unless Farjad approves a change (DPA + notice update).
- Retention figures are *proposed*; do not ship until Farjad approves them.
- "No advertising trackers or any analytics company" and the "Website measurement" text must match what the site actually does; re-check whenever a dependency, script or event is added. Do not ship the measurement text until C1/C2/C4 (`website-measurement-review.md` §2) are decided — it describes the recommended design (no `country`, GPC/DNT honoured, 90-day raw / 25-month totals).
- Do not ship the measurement code before this notice is published (brief §9 criterion 10).
- The pilot form must say "Ontario farms only" next to the country field; a non-Ontario request is stored and answered, not enrolled.
- Link this page from the pilot form (already done: `pilot.privacyLink`).
- "Security log of our staff area" (v0.5.2): ship it **with** website admin P1 (`docs/plans/website-admin.md`), not before, and drop it if P1 is cancelled. It must stay true: no IP prefix on public-site errors or page views; log purge at 60 days; rate-limit rows purged within 24 h; no typed email of non-staff and no form values in `website_log`. Any change to `website_log`, `website_rate_limit` or `website_session` fields → `coo` re-checks this text.

---

## Sources (checked 2026-11-16; S38–S43 checked 2026-11-17)
Some Government of Canada and CRTC pages refused connections from this environment; those are marked *(not fetched — confirmed via search summaries only; verify before reliance)*.

- S1 PIPEDA, S.C. 2000, c. 5, incl. Schedule 1 and s. 8(3) — https://laws-lois.justice.gc.ca/eng/acts/P-8.6/ *(not fetched)*
- S2 OPC, PIPEDA fair information principles — https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/p_principle/ *(not fetched)*
- S3 OPC, Guidelines for obtaining meaningful consent (2018) — https://www.priv.gc.ca/en/privacy-topics/collecting-personal-information/consent/gl_omc_201805/ *(not fetched; search-confirmed)*
- S4 OPC, Guidelines for processing personal data across borders (2009) — https://www.priv.gc.ca/en/privacy-topics/airports-and-borders/gl_dab_090127/ *(not fetched; search-confirmed)*
- S5 OPC breach guidance — https://www.priv.gc.ca/en/privacy-topics/business-privacy/safeguards-and-breaches/privacy-breaches/respond-to-a-privacy-breach-at-your-business/gd_pb_201810/ ; SOR/2018-64 — https://canadagazette.gc.ca/rp-pr/p2/2018/2018-04-18/html/sor-dors64-eng.html *(search-confirmed: 24-month record keeping)*
- S6 CASL, S.C. 2010, c. 23 — https://laws-lois.justice.gc.ca/eng/acts/E-1.6/ *(not fetched)*
- S9 CRTC CASL FAQ — https://crtc.gc.ca/eng/com500/faq500.htm *(not fetched; search-confirmed 10 business days)*
- S11 GDPR, Regulation (EU) 2016/679 — https://eur-lex.europa.eu/eli/reg/2016/679/oj *(fetched earlier 2026-11-16; Arts. 3, 4, 7, 13, 21, 27, 45 read; Art. 22 and 13(2)(f) cited from the same text — verify)*
- S12 Commission Decision 2002/2/EC (Canada adequacy) — https://eur-lex.europa.eu/eli/dec/2002/2/oj *(fetched)*
- S14 Railway deployment regions — https://docs.railway.com/reference/deployment-regions *(fetched)*
- S15 Railway Data Processing Addendum — https://railway.com/legal/dpa *(fetched)*
- S23 Federal/provincial/territorial privacy regulators, *Principles for responsible, trustworthy and privacy-protective generative AI technologies* (7 Dec 2023) — listed at https://www.priv.gc.ca/en/privacy-topics/ai-technology-and-innovation/artificial-intelligence/leadership-ai/ ; text at https://oipc.bc.ca/documents/guidance-documents/2811 *(search only: transparency principle — tell individuals how AI uses their information and its role in decisions; full text not read — verify)*
- Decisions: `origin/backend-traceability:docs/plans/backend-plan-reconciliation.md` D4, R4 (CPO, 2026-11-16).
- S38 OPC, Interpretation Bulletin: Personal Information ("serious possibility" test, *Gordon v. Canada (Health)* 2008 FC 258; IP address can be personal information where it can be associated with an identifiable individual) — https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/pipeda-compliance-help/pipeda-interpretation-bulletins/interpretations_02/ *(search summary only; full text not read — verify)*. Commentary: Norton Rose Fulbright, "IP addresses as personal information: the Canadian and EU positions contrasted" — https://www.nortonrosefulbright.com/en/knowledge/publications/2b463345/ip-addresses-as-personal-information-the-canadian-and-eu-positions-contrasted *(search only)*
- S39 GDPR Recital 49 (network and information security, to the extent strictly necessary and proportionate, is a legitimate interest) — https://gdpr-info.eu/recitals/no-49/ *(fetched 2026-11-17; unofficial site — official text S11)*
- S40 CJEU C-582/14 *Breyer* (19 Oct 2016): dynamic IP address is personal data for a website operator with legal means to identify the user; website security as a legitimate interest — https://curia.europa.eu/juris/liste.jsf?num=C-582/14 *(not fetched; search summary only)*
- S41 GDPR Art. 11 (processing that does not require identification) — S11 *(cited from search summary; verify)*
- S42 PIPEDA s. 4(1)(a)–(b) (applies to commercial activities, and to employee information only in connection with a federal work, undertaking or business) — https://laws-lois.justice.gc.ca/eng/acts/P-8.6/page-1.html *(fetched 2026-11-17)*
- S43 Ontario, *Your guide to the Employment Standards Act*: written policy on electronic monitoring (ESA s. 41.1.1; 25+ employees on 1 January → policy by 1 March) — https://www.ontario.ca/document/your-guide-employment-standards-act-0/written-policy-electronic-monitoring-employees *(search summary only; verify)*
- Website admin: `origin/docs/website-admin-plan:docs/plans/website-admin.md`, `docs/adr/0011-website-admin-auth.md`, `docs/adr/0013-website-system-log-retention.md` (drafts, read 2026-11-17).
- S24–S37 (website measurement, §3a): see the source list in `website-measurement-review.md` (EDPB Guidelines 2/2023 v2.0; CNIL; AEPD; Garante; Traficom; KVKK; Quebec P-39.1 s. 8.1; OPC).

## Needs licensed counsel
1. Whether PIPEDA applies to a free pilot (commercial activity) and whether farm/field data is personal information for incorporated vs sole-proprietor farms.
2. Whether the §4 wording is adequate transparency about AI-assisted review under PIPEDA openness/consent and the 2023 generative-AI principles (S23), and under GDPR Arts. 13(2)(f)/22 for website visitors.
3. D-7: whether our de-identification for the AI reviewer (county-level region, crop, previous crop, target yield, soil-test values, plan date kept) makes the data non-personal under PIPEDA, so no transfer-for-processing contract is needed; and what a DPA must contain if Farjad later allows identifiable data.
4. Whether calibration use can be a condition of the pilot or must stay optional (PIPEDA 4.3.3; GDPR Art. 7(4)).
5. Whether our de-identification standard is enough to treat calibration data as non-personal.
6. Residency (pilot data in Canada decided 2026-11-16; website data in the US on Railway until Canadian hosting is live, decided 2026-11-16): whether a US-owned provider's Canadian region needs the US-law access disclosure and what wording; whether the provider's backups, support access or sub-processors outside Canada must be disclosed; whether the US website-data wording in §7 and Part B is adequate under PIPEDA openness/accountability (S4); and whether moving the data to Canada later needs notice to people who already sent a request.
7. EU website-visitor transfer analysis and whether an Art. 27 EU representative is needed.
8. If the pilot extends to a Prairie province: whether a provincial private-sector privacy law applies instead of PIPEDA (not assessed).
9. Retention periods and the "legal claims" exception to deletion of immutable plan records.
10. Minimum age wording.
11. Website measurement (§3a): every item in `website-measurement-review.md` "Needs licensed counsel" — in particular Finland consent, the Art. 5(3) status of hidden attribution fields for EU visitors, and Quebec s. 8.1.
12. Administrator (`superadmin_approved`) approvals: whether sending fertilizer rate recommendations approved by a person without agronomic credentials creates liability, professional-title or nutrient-management regulatory issues in Ontario, and whether the §4 disclosure ("not an agronomist review") is enough for farmers to rely on it. Not researched here — no rule is stated.
13. Staff-area security log (§3b): whether a shortened IP (/24, /48) with timestamp and browser family is personal information under PIPEDA and GDPR; whether legitimate interests (Recital 49) and a 60-day period are proportionate; whether the HMAC of a typed email from a non-staff person is personal data; whether Quebec s. 8.1 or Israeli law adds any duty.
14. Whether admin CSV exports of the log (copies outside the 60-day purge) need their own retention rule in this notice, and whether the "within a day" throttling-counter promise is safe to publish before engineering proves it.
