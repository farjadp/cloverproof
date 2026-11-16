# CloverProof — privacy posture (S2)

> **This is not legal advice; a licensed Ontario lawyer should review before use.** Written by `legal-compliance-specialist` (not a lawyer) for `ciso`, 2026-11-16. Privacy half only: the privacy notice, terms and consent wording are drafted by the COO track; this file sets the requirements they must meet (§4).

Scope: repo state on branch `myca/security-s2-bb8ef7` (2026-11-16): `db/migrations/0001`–`0009`, `website/src` (pilot form), `db/seeds/dev.sql`, `app/tests`, `engine/tests`, ADR 0002/0004/0005. Related: `docs/security/threat-model-webapp.md`, `railway-hardening.md`, `backup-restore-test-plan.md`, `release-gate-checklist.md`.

**Source check, 2026-11-16.** `laws-lois.justice.gc.ca`, `priv.gc.ca`, `ised-isde.canada.ca` and `crtc.gc.ca` refused connections from this environment. Rules from those sites below are marked **[re-verify]**: cited from the primary URL, confirmed only through secondary search results or the Canada Gazette copy. Sources fetched directly are marked **[fetched]**. Re-open every [re-verify] link before the notice is published.

---

## 0. Facts that change the analysis

| # | Fact | Evidence | Effect |
|---|---|---|---|
| F1 | **No legal entity is named anywhere.** The controller ("organization" under PIPEDA) is unknown. | `docs/plans/website-v1.md:36` open item "Contact email and legal entity name" | Notice, consent (CASL ID), DPA with Railway and breach reports all need the entity. **Decision for Farjad Iranmehr.** |
| F2 | **Railway region not verified.** ADR 0004: "Railway has no Canadian region. The default region is used." Railway regions: US West (California), US East (Virginia), EU West (Amsterdam), Southeast Asia (Singapore); the default is the account's "preferred region". | ADR 0004; https://docs.railway.com/reference/deployment-regions [fetched]. The Railway CLI is not linked in this worktree. | The data may be in the US or the EU. Someone must read it off the dashboard (Postgres service, website service, bucket) and write it into ADR 0004. |
| F3 | Pilot form collects **name, email, country, farm size (free text), main crop, notes, locale**, plus `consent_at` and `consent_text`. **No phone and no IP/user agent.** Honeypot only, no analytics, no cookies set by the site. | `db/migrations/0001_pilot_request.sql`, `website/src/app/[lang]/actions.ts`, `website/src/proxy.ts` | Good minimisation. The consent record exists. |
| F4 | Only `en` is enabled; fr/it/es/bg/fi/tr/ar are built but disabled. | `website/src/i18n/config.ts` | EU targeting (GDPR Art. 3(2)) starts when an EU locale is enabled or an EU pilot farm is accepted. |
| F5 | `user_session` stores no IP or user agent; tokens are stored as SHA-256 only. | `db/migrations/0003_identity.sql` | Keep it that way, or set a retention period if IPs are added for rate limiting. |
| F6 | `recommendation.inputs_snapshot` holds only agronomic inputs (crop, yield, previous crop, area, plan date, soil test incl. `lab` name). No name, farm, location or geometry. | `engine/cloverproof_engine/models.py` (`RecommendationInput`, `SoilTest`) | Immutable rows hold no direct identifiers, so deletion by pseudonymisation is feasible (§5.4). The free-text `reason` columns are the exception. |
| F7 | Repo hygiene: seeds and tests are fictional (`Example Farmer`, `agronomist@example.org`, `Farmer {label}`, geometry at 0,0). No real emails or phone numbers in tracked files. The founder's name appears in docs (intended). | `db/seeds/dev.sql`, `app/tests/db/*.py`, grep of `git ls-files` 2026-11-16 | No gap today. Keep it enforced (§5.8). |
| F8 | **PII in logs.** `actions.ts` runs `console.error("requestPilot failed", error)`. A `pg` CHECK or NOT NULL violation puts the whole failing row (name, email, notes) in `detail`. Railway logs are kept 7 days (Hobby) or 30 days (Pro) and cannot be purged per record. | `website/src/app/[lang]/actions.ts`; also `docs/security/railway-hardening.md` row 5 | Gap (§5.1). |
| F9 | `pilot_request.deleted_at` exists, but **no purge job exists** anywhere in the repo. | grep for `deleted_at`/`purge` 2026-11-16 | A deletion "request" is only a flag. Gap. |

---

## 1. Data inventory

Classes: **P** = personal information (identifiable individual, directly or indirectly); **P-ind** = indirectly identifying when linked to a farmer who is an individual (most pilot farms are family or sole-proprietor operations); **FC** = farm-confidential (commercially sensitive, may also be P-ind); **S** = staff/internal; **Pub** = non-personal.

Legal basis column: PIPEDA uses **consent** (Principle 4.3) for everything. The GDPR basis shown applies only if GDPR applies (§2.2). Retention values are **proposals** for Farjad Iranmehr and counsel, not rules.

| Data (column) | Table / store | Class | Purpose | PIPEDA basis / GDPR basis (if applicable) | Retention proposal | Access |
|---|---|---|---|---|---|---|
| `full_name`, `email` | `pilot_request` | P | assess and contact pilot applicants | express consent (checkbox) / Art. 6(1)(a) consent or 6(1)(b) pre-contract steps — **counsel to pick** | Not selected: 12 months after the pilot selection closes, then hard delete. Selected: move to `farmer`, delete the `pilot_request` row 30 days after conversion. Deletion request: hard delete within 30 days. | Farjad Iranmehr + named staff; website service writes only |
| `country`, `farm_size_text`, `main_crop`, `locale` | `pilot_request` | P (linked to name) | eligibility | as above | as above | as above |
| `notes` (free text, 2000 chars) | `pilot_request` | P, may contain anything | context | as above | as above | as above |
| `consent_at`, `consent_text`, `status` | `pilot_request` | P (consent record) | prove consent (CASL s.13 burden of proof) | legal obligation / Art. 6(1)(c)/(f) | Keep the consent record for 3 years after the last commercial electronic message (CEM) sent on it, even after the contact data is deleted: keep a hashed email + consent text + timestamps. **Counsel**: the period is a proposal; I don't know of a statutory period. | Farjad Iranmehr |
| `display_name`, `notes` | `farmer` | P | client record | consent (pilot agreement) / Art. 6(1)(b) contract | Life of the client relationship + limitation period (§5.4). Pseudonymise on a deletion request. | org members (agronomist, staff) |
| `app_user_id` | `farmer` | P (link) | Phase 4 login | contract | with the account | org members |
| `name`, `country_code`, `region` | `farm` | P-ind | plan context | contract | as `farmer` | org members |
| `name` | `field` | P-ind | plan context | contract | as `farmer` | org members |
| `geom` (MultiPolygon, WGS84), `area_ha` | `field_geometry_version` | **P-ind, high**: a parcel outline resolves to a land-registry owner | area and future maps | contract | as `farmer`. On deletion: set `geom` NULL (the table is mutable), keep `area_ha`. | org members |
| soil tests (date, depth, lab, values, method) | `soil_test`, `soil_test_value` | FC / P-ind | engine input | contract | as `farmer`; keep values after pseudonymisation (calibration) — **counsel** | org members |
| `crop`, `target_yield_t_ha`, `previous_crop`, `plan_date` | `crop_plan` | FC / P-ind | engine input | contract | as above | org members |
| `inputs_snapshot`, `result`, typed columns | `recommendation` (immutable) | FC / P-ind via `crop_plan → field → farm → farmer` | evidence + calibration dataset | contract; calibration is a secondary use (§2.1 purpose) | Kept; de-linked by pseudonymising the parents (§5.4) | org members; calibration via `recommendation_diff` |
| `reason` (free text) | `recommendation`, `review` (immutable) | **risk: P if staff type names into it** | edit/reject reasons | contract | cannot be erased → **must never contain personal data** (§5.5) | org members |
| `reviewer_id`, `minutes_spent`, `decision` | `review` (immutable) | S (agronomist identity + time) | review gate, key metric | legitimate business purpose; employee/contractor data | Kept with the recommendation | owner, agronomist |
| `product`, dates, rates, `notes` | `application_log` | FC / P-ind; `notes` free text | planned vs actual | contract | as `farmer`; clear `notes` on deletion | org members |
| `storage_key`, `sha256` | `proof_document` (immutable) | Pub on its own (hash) | integrity | contract | Kept | org members |
| **Proof PDF bytes** | Railway Bucket (ADR 0005 B1) | **P** if the PDF prints farmer/farm/field names or a map | evidence given to the farmer | contract | **Undecided (§5.4, counsel)** | via the app only |
| `email`, `display_name` | `app_user` | S / P | staff login | employment/contract | Disable on exit (`disabled_at`). Delete or pseudonymise 24 months after exit unless the user is a reviewer (then keep `display_name` for evidence). | owner |
| `password_hash` (argon2id), `totp_secret` (to be app-encrypted) | `app_user` | S, secret | authentication | security | with the account | none in the UI |
| `token_sha256`, timestamps | `user_session` | S | sessions | security | purge 30 days after expiry (S2 review N5) | none |
| Railway HTTP/app logs | Railway | P if PII leaks into them (F8). The HTTP logs may hold client IPs — **verify** | ops | legitimate purpose | Platform-fixed 7 or 30 days | Railway members |
| Backups / dumps | Railway volume backups; planned `age`-encrypted dumps | copies of all the above | recovery | safeguards | Proposal in `backup-restore-test-plan.md` (≤12 months monthly). **Deletion completes only when the last backup holding the row expires; the notice must say so.** | Farjad Iranmehr |
| Repo (public GitHub) | git | must be none | — | — | Fictional data only | public |

---

## 2. Obligations and gaps

### 2.1 PIPEDA (federal; applies to CloverProof's commercial activity in Ontario)

Ontario has no general private-sector privacy statute, so PIPEDA applies to commercial collection in Ontario and in other provinces without a "substantially similar" law. **Alberta, BC and Quebec farmers** fall under their provincial laws. **Quebec (Law 25) is the strictest**: it requires a privacy impact assessment before personal information is communicated outside Quebec (s.17, https://www.legisquebec.gouv.qc.ca/en/document/cs/P-39.1 [re-verify]). **Counsel** if any pilot farm is in Quebec.

Main sources: PIPEDA https://laws-lois.justice.gc.ca/eng/acts/P-8.6/FullText.html [re-verify]; OPC meaningful consent guidelines https://www.priv.gc.ca/en/privacy-topics/collecting-personal-information/consent/gl_omc_201805/ [re-verify]; Breach of Security Safeguards Regulations SOR/2018-64, https://gazette.gc.ca/rp-pr/p2/2018/2018-04-18/html/sor-dors64-eng.html [fetched].

**Pending law.** Bill C-36 (Protecting Privacy and Consumer Data Act) was tabled on 2026-06-15. It would replace Part 1 of PIPEDA and move enforcement to a new regulator. It would also add a "disposal" right (deletion or anonymization), treat de-identified data as personal information, and allow AMPs up to the greater of CAD 10M or 3% of revenue. It is not law. Source: https://www.bakermckenzie.com/en/insight/publications/2026/06/canada-private-sector-privacy-reform-returns [fetched, secondary]. Design the deletion flow (§5.4) so it also satisfies "disposal".

| Requirement | Source | Current state | Gap | Fix | Owner |
|---|---|---|---|---|---|
| Accountability: a designated person responsible for compliance; protection by contract when a third party processes the data | Sch.1 Principle 4.1, 4.1.3 [re-verify] | none named; Railway terms/DPA not reviewed | **G** | Name the privacy officer (Farjad Iranmehr by default) in the notice. Check that Railway's DPA (https://railway.com/legal/dpa, not fetched) covers our plan. | Farjad Iranmehr; counsel to review the DPA |
| Identify purposes at or before collection | 4.2 | Form + draft notice state "assess / contact about the pilot" | Partial: no purpose stated for the farm data (plans, **calibration dataset**, proof PDF) | The pilot agreement/notice for selected farms must name calibration/model improvement as a purpose (§4) | COO track |
| Meaningful consent (what, with whom, purposes, risks); separate consent for non-essential purposes | 4.3; OPC consent guidelines | Checkbox, required, `consent_text` stored verbatim | Partial: the notice doesn't say where the data is stored (foreign jurisdiction) or name the entity. Consent covers the pilot only. | §4 requirements | COO track |
| Limit collection | 4.4 | minimal (F3) | none | Keep the phone number out unless needed | — |
| Limit use, disclosure, retention; destroy/erase/anonymize when no longer needed | 4.5, 4.5.3 | No retention schedule. `deleted_at` flag but no purge (F9). | **G** | Retention schedule (§1) + purge job (§5.3) | Farjad Iranmehr (decide); `cp-platform` |
| Safeguards appropriate to sensitivity | 4.7 | Strong DB design (org scoping, least-privilege roles). PII leaks to logs (F8). | **G** (logs) | §5.1 | `cp-website` |
| Openness: policy available | 4.8 | Draft notice live, marked "Draft" | **G**: entity, contact, location and retention specifics missing | §4 | COO track |
| Individual access: respond within 30 days | 4.9; s.8(3) [re-verify] | No procedure, no export | **G** | §5.6 DSAR runbook + SQL export | `cp-database`; Farjad Iranmehr answers |
| Challenging compliance: complaint route | 4.10 | none | **G** | Contact address in notice | COO track |
| **Breach: report to OPC and notify individuals "as soon as feasible" when a breach creates a real risk of significant harm (RROSH)** | s.10.1(1)–(3) [re-verify]; report contents SOR/2018-64 s.2; notice contents s.3; direct notice s.4; indirect notice s.5 [fetched] | No incident procedure | **G** | §5.7 | `ciso` |
| **Keep a record of every breach** (not only RROSH ones) **for 24 months** after the day the organization determines a breach occurred, with enough to verify compliance with 10.1(1) and (3) | s.10.3(1) [re-verify]; SOR/2018-64 s.6(1)–(2) [fetched] | none | **G** | Private breach register (Notion, not the public repo) | `ciso` |

### 2.2 GDPR (only if it applies)

Source: Regulation (EU) 2016/679, https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng [fetched for Art. 3(2), 27, 30(5), 33; other articles [re-verify]].

- **Applicability.** Art. 3(2) covers a non-EU controller processing personal data of people in the Union when it is "the offering of goods or services, irrespective of whether a payment … is required" or monitoring their behaviour. A Canadian site in English with no EU targeting is probably outside scope (estimate). It is **inside** scope once an EU locale is enabled with EU-facing content, or once an EU farm joins the pilot. No tracking runs today, so the "monitoring" limb doesn't apply. **Counsel** to confirm before any EU locale goes live.
- **If it applies:**
  - Lawful basis per purpose (Art. 6). Proposed: pilot requests = consent or pre-contract steps; plans = contract; calibration = legitimate interests or compatible further processing (Art. 6(4)). **Counsel.**
  - Notice content (Art. 13), including the transfer mechanism and retention.
  - Rights (Art. 15–21), answered within one month (Art. 12(3)).
  - Processor contract with Railway (Art. 28).
  - **EU representative (Art. 27)**, unless the Art. 27(2) "occasional, low risk" exemption applies. **Counsel.**
  - Records of processing (Art. 30). The Art. 30(5) small-organisation exemption does not cover processing that is "not occasional". **Counsel.**
  - **Breach: notify the supervisory authority "without undue delay and, where feasible, not later than 72 hours after having become aware of it"** (Art. 33(1)). Document all breaches (Art. 33(5)). Notify individuals when there is high risk (Art. 34).
- **Pseudonymised data is still personal data** under GDPR (Recital 26). The deletion design in §5.4 is pseudonymisation, not anonymisation.
- **Transfers.** The EU recognises Canada as adequate for organizations subject to PIPEDA (Decision 2002/2/EC, confirmed in the Commission's 2024-01-15 review; https://www.weirfoulds.com/canadas-privacy-protections-stand-strong [secondary]). Onward transfer to a **US** Railway region needs Railway's transfer mechanism (DPF/SCCs per its DPA, not fetched). An **EU West** region avoids that for EU data. **Counsel.**

### 2.3 CASL (emails to pilot requesters)

Sources: CASL https://laws-lois.justice.gc.ca/eng/acts/E-1.6/FullText.html [re-verify]; Electronic Commerce Protection Regulations (CRTC) SOR/2012-36 https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-36/ [re-verify]; CRTC guidance https://crtc.gc.ca/eng/com500/guide.htm [403 from here, re-verify]; ISED https://ised-isde.canada.ca/site/canada-anti-spam-legislation/en/node/7 [re-verify].

- **Is a follow-up a CEM?** Probably yes: inviting someone into a pilot of a commercial product encourages participation in a commercial activity, even when the pilot is free (estimate). **Counsel.**
- **Consent we have:**
  - **Implied consent from an inquiry.** CASL s.10(9)(a) with 10(10) (existing business relationship) covers someone who made an inquiry or application within the previous **six months** [re-verify]. The window starts from the inquiry date.
  - **Express consent.** The checkbox says "contact me about the pilot". CASL express consent requests must state the purpose, **identify the person seeking consent (name + mailing address + phone, email or web address)** and state that consent can be withdrawn (CRTC Regs s.4 [re-verify]). The current text does not identify the entity or give a mailing address, so it may not qualify as CASL express consent. Treat it as **implied consent, six months**, until the wording is fixed.
- **Every CEM must:**
  - identify the sender: name, mailing address, and phone, email or web contact (s.6(2) + Regs);
  - include a working unsubscribe that is honoured within **10 business days** (s.11(3)) and works for 60 days after sending [re-verify].
- **Scope.** Pilot emails only. A newsletter or product-update list needs a **separate, unticked** opt-in. Don't bundle it into the pilot consent.
- **Records.** Whoever claims consent must prove it (s.13). `consent_at` + `consent_text` + `locale` already do this; add the email and send log (§5.3).
- **Personal one-to-one replies** written by Farjad Iranmehr are still CEMs if they promote. Use a signature with entity, mailing address and an "unsubscribe: reply STOP" line (estimate of a compliant minimum; counsel).

---

## 3. Cross-border transfer note (Railway)

- **Where the data is:** unknown until F2 is checked: US (CA/VA) or EU (Amsterdam). Railway: "Services and volumes run in the region you choose… All application data stays within that region"; "Railway's own processing mainly takes place in the United States." Source: https://docs.railway.com/enterprise/security [fetched]. The bucket region is fixed at creation (ADR 0005).
- **PIPEDA view:** sending data to a provider for processing is a *use*, not a disclosure. The organization stays accountable, must protect the data by contract, and must tell people their information may be processed in a foreign jurisdiction and be accessible to that country's courts and authorities. Source: OPC Guidelines for processing personal data across borders (2009), https://www.priv.gc.ca/en/privacy-topics/airports-and-borders/gl_dab_090127/ [re-verify]. Data residency is not required by PIPEDA. It may be required by **Quebec** (s.17 PIA) and by a **pilot contract** if a farmer or co-op demands it.
- **Choice:**
  - **EU West** gives an adequacy-friendly path for EU farms and no US CLOUD Act exposure for the stored data, though Railway (a US company) still processes metadata.
  - **US** is acceptable under PIPEDA with notice and contract.
  - Moving region later means migrating the database and recreating the bucket. Decide before real farmer data arrives (Feb 2027). **Decision for Farjad Iranmehr; counsel on US-provider exposure.**
- Write the verified region of each service (website, Postgres/PostGIS, app, bucket, backups) into ADR 0004.

---

## 4. Requirements for the privacy notice and consent wording (COO track)

The notice and consent must:

1. Name the **legal entity** (F1), its mailing address, and a **privacy contact** (email + named person) for access, correction, deletion, withdrawal and complaints. Give the OPC complaint route (https://www.priv.gc.ca).
2. List what is collected **per audience**:
   - website visitors: none beyond hosting logs (state whether IPs are logged; verify F2/§1);
   - pilot applicants: the six form fields + consent record;
   - pilot farms: farmer contact, farm/field names, region, **field boundaries**, soil tests, crop plans, recommendations, application logs, proof PDFs;
   - staff: account data.
3. State the **purposes** per audience. For pilot farms that includes **using de-linked agronomic data (engine vs agronomist numbers) to calibrate and improve the engine**. Say whether that is a condition of the pilot or optional; making it a condition needs counsel.
4. Say the data is stored with **Railway (US company) in [verified region]**, may be accessible to that jurisdiction's authorities, and list the processors used (Railway; later email provider, etc.).
5. Give **retention** in plain terms per audience (§1), including that deleted data persists in encrypted backups until they expire (state the maximum, e.g. 12 months).
6. Describe **rights** and how to use them, with response times: 30 days PIPEDA; one month GDPR where it applies.
7. Explain the **deletion vs evidence rule**: on deletion, identifying details are removed; recommendations and reviews are kept without identifiers as tamper-evident records and calibration data. This wording needs **counsel** (§6).
8. **Pilot-form consent text:**
   - name the entity + contact (CASL ID);
   - state the purpose "contact you about the 2027 pilot";
   - say "you can withdraw at any time" with how;
   - link the notice.
   - No marketing in the same box. Any newsletter gets its own unticked box.
   - Each locale's text is stored verbatim in `consent_text` (already done); bump a version label when it changes.
9. **Translations:** every enabled locale gets the notice in that language before the locale goes live. The consent stored must be the text actually shown.
10. Remove the "Draft" banner only after counsel review (release gate §5).
11. Make no security claims that aren't verified (e.g. "encrypted" — see §5.2). No vague "access limited to the team" without naming roles.
12. **Pilot agreement (separate document, COO + counsel):** who owns farm data, licence to use de-linked data for calibration, data return/deletion at the end, liability for recommendations.

---

## 5. Security-control requirements for engineering

### 5.1 Logging minimisation

- **Fix F8 now:** log `error.code` / `constraint` / a request id only, never `error.detail`, the error object, or form values. Owner: `cp-website`.
- FastAPI app: no request bodies, no form values, no emails in logs; log user/org/record **IDs** only. Add a test that renders a failing insert and asserts the log line has no email. Owner: `cp-concierge-app`.
- Find out whether Railway HTTP logs record client IP and for how long. Put the answer in the notice (§4.2).

### 5.2 Encryption claims to verify before they go into the notice

| Claim | Status | Evidence needed |
|---|---|---|
| At rest AES-256 (volumes, backups, buckets, variables) | Railway states it [fetched, docs.railway.com/enterprise/security] | Confirm the page applies to our plan, not only Enterprise |
| In transit, public: HTTPS TLS 1.2/1.3 | Railway states it | `curl -sI` on prod |
| In transit, service → DB | WireGuard private network if the internal hostname is used | Confirm `DATABASE_URL` uses `*.railway.internal`, not the TCP proxy. If the TCP proxy is enabled, require `sslmode=require` or disable the proxy. |
| `totp_secret` app-level encryption | planned (ADR 0002) | code + test |
| Offsite dumps encrypted with `age` | planned (`backup-restore-test-plan.md`) | restore test |

### 5.3 Retention and deletion jobs

- `pilot_request` purge:
  - hard delete rows where `deleted_at < now() - 30 days`;
  - hard delete `status='declined'` / non-selected rows 12 months after selection closes;
  - keep a CASL consent stub (hashed email, consent_text, timestamps) if CEMs were sent.
- `user_session` purge (S2 review N5).
- Log every purge run (counts only).
- Owner: `cp-platform`, after Farjad Iranmehr approves the periods.

### 5.4 Deletion vs immutability (proposal; **needs counsel**)

The rule stays: `recommendation`, `review` and `proof_document` are never updated or deleted (ADR 0002 triggers). A deletion request from a farmer is honoured by **de-linking the identity from the mutable parent rows in one transaction**:

1. `farmer.display_name` → `'deleted-' || left(id::text, 8)`; `farmer.notes` → NULL; `farmer.app_user_id` → NULL. Disable and pseudonymise the linked `app_user`.
2. `farm.name` → `'farm-' || short id`; `farm.region` → NULL; keep `country_code` (coarse) or NULL it (**decide**).
3. `field.name` → `'field-' || short id`.
4. `field_geometry_version.geom` → NULL. Keep `area_ha`; `area_source` stays `manual`/`geometry`. A CHECK forbids `geometry` with NULL geom, so set `area_source='manual'` too. This is a mutable table; it changes nothing in recommendations.
5. `application_log.notes` → NULL. `soil_test.lab` → keep (a lab name is not personal) or NULL (**decide**).
6. **Proof PDFs:** if the template prints farmer/farm names or a map, the PDF is personal data in the bucket. Options:
   - (a) PDFs carry **no direct identifiers**: farm/field by code; the farmer gets a cover letter outside the immutable PDF. Deletion is then a no-op. **Recommended.**
   - (b) Delete the bucket object on request and keep the `proof_document` row + `sha256` as evidence that a document existed.
   - **Decide before `cp-pdf` builds the template.**
7. Delete the `pilot_request` row.
8. Write a `privacy_request` log row: request type, received, completed, by whom, with no identifying content beyond an internal ticket ref.
9. Backups: the identity survives until the oldest backup expires. State this in the notice and the response letter.

What remains: agronomic inputs, engine/agronomist numbers, confidence, reviewer and minutes. **Residual risk:** with 5–10 pilot farms, crop + yield + area + plan date + country can re-identify a farm. That makes it **pseudonymised, not anonymised** under GDPR Recital 26 and probably under PIPEDA/C-36 (estimate). Counsel must confirm that keeping it is lawful:
- PIPEDA 4.5.3 allows "anonymize", which this is not;
- possible grounds are legal-claims evidence (Ontario Limitations Act 2002, 2-year basic / 15-year ultimate: https://www.ontario.ca/laws/statute/02l24 [re-verify]) and/or a contractual licence in the pilot agreement;
- GDPR Art. 17(3)(e) legal claims, and possibly Art. 17(3)(d) with Art. 89 research safeguards.

Engineering:
- a tested `make privacy-erase FARMER_ID=…` (CLI, owner role, dry-run first);
- a test that the snapshot/result schema contains no identifying keys, which fails if someone adds `farmer_name` to `RecommendationInput`.

### 5.5 Free text in immutable tables

`recommendation.reason` and `review.reason` cannot be erased.
- UI hint next to each: "Agronomic reasons only. No names, phone numbers or personal details."
- Optional server check rejecting emails and phone-number patterns.
- Staff rule in the internal handbook.
- Owner: `cp-concierge-app`.

### 5.6 Access/correction requests (DSAR)

- Runbook: verify identity (reply from the email on file), log the request, export, answer within 30 days.
- Export: a SQL script producing a farmer's rows (farmer, farms, fields, geometry, soil tests, plans, approved recommendations, PDFs) as JSON/CSV.
- Corrections to mutable rows are normal edits. Corrections to recommendations follow the "new version" rule.

### 5.7 Breach handling

- One-page procedure in `docs/security/`:
  - triage;
  - RROSH assessment, which considers the sensitivity of the information and the probability of misuse (s.10.1(8) [re-verify]);
  - who decides: Farjad Iranmehr;
  - OPC report contents (SOR/2018-64 s.2);
  - individual notice contents (s.3);
  - GDPR 72-hour clock if EU data;
  - Quebec CAI notice if Quebec data [re-verify].
- Breach register: kept privately, 24 months minimum, every breach including non-reportable ones.
- Pre-fill the contact person.
- Owner: `ciso`.

### 5.8 Public-repo hygiene

- Keep the rule: seeds, tests, fixtures and golden files are fictional. Use `example.org`/`.test` emails, `Example …` names, geometry near 0,0 (never a real parcel), and no real lab report scans or PDFs.
- Add a CI check (pattern grep for emails outside the allowlist and for phone numbers; `gitleaks` already proposed in `secret-and-dependency-scan-2026-11.md`).
- Never commit DB dumps, CSV exports or real proof PDFs.
- Owner: `security-engineer`.

### 5.9 Access control

- Production DB access limited to named people (list in Notion).
- No agents with Railway seats (railway-hardening.md).
- The `website` DB role can only INSERT into `pilot_request`. Verify, so a website compromise cannot read the applicant list.

---

## 6. Needs licensed counsel

1. **Entity and controller:** which corporation operates CloverProof, and whether it is the PIPEDA organization / GDPR controller for pilot data.
2. **Deletion by pseudonymisation** (§5.4): is keeping de-linked recommendations, reviews and soil data lawful after a deletion request under PIPEDA 4.5.3, Bill C-36 "disposal" (if enacted), GDPR Art. 17 and Quebec Law 25? On what ground: legal claims, contract licence or research?
3. **Calibration use of farm data:** can it be a condition of the pilot, or must it be optional? Pilot agreement clause on data ownership and licence.
4. **Retention periods** in §1, including the CASL consent-record period and the backup retention.
5. **GDPR applicability** when EU locales or EU pilot farms start: Art. 27 representative, Art. 30 records, lawful bases.
6. **Cross-border:** acceptability of a US Railway region for Canadian, Quebec and EU data. Review Railway's DPA, subprocessors and transfer mechanism, and whether our plan tier is covered.
7. **Quebec:** a s.17 PIA if any Quebec farm joins.
8. **CASL:** whether pilot follow-ups are CEMs; whether the revised checkbox is valid express consent; the minimum footer for personal replies.
9. **Breach:** sign-off on the RROSH assessment template and the notification letters.
10. **Agronomy record-keeping:** I don't know whether a professional body (e.g. CCA code, the Ontario Institute of Agrologists) or Ontario nutrient-management rules impose retention on plans. Counsel or the agronomist to confirm.
11. Final review of the privacy notice, consent wording and pilot agreement before the "Draft" banner is removed.
