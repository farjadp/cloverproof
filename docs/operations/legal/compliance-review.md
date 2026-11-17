# CloverProof compliance review — PIPEDA, CASL, GDPR, Ontario agronomy advice — 2026-11

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> Prepared by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO, 2026-11-16.
> Scope: public website (`website/`, only `en` enabled today; `fr, it, es, bg, fi, tr, ar` built but disabled until native review) and the 2027 pilot (internal tool, `db/migrations/0003–0009`).
> Nothing was filed, sent, signed or submitted.

**Repo vs my default brief:** my global agent file describes VisaRoads (Cloud Run, Prisma, five locales, immigration rules). CLAUDE.md overrides it: CloverProof is agri-tech on Railway + Railway Postgres, 8 locales; immigration/RCIC rules do not apply.

Status key: **OK** = met · **PARTIAL** · **GAP** · **UNKNOWN**.
Owners: **Farjad** (decisions/signing), **COO**, **CISO**, **cp-website**, **cp-database**, **cp-concierge-app**, **cp-platform**.

## 0. The three issues that matter
1. **No identified legal entity or contact.** Every regime below needs it (PIPEDA accountability, GDPR Art. 13(1)(a), CASL identification). Nothing can launch without `[LEGAL ENTITY]`, `[CONTACT EMAIL]`, `[ADDRESS]` and a named privacy officer.
2. **Write-once records vs deletion requests.** `recommendation`, `review` and `proof_document` raise on DELETE (`forbid_change()`, `db/migrations/0002`), and the parent rows (`farmer → farm → field → crop_plan`) cannot be deleted while they are referenced. Today a deletion request cannot be honoured. Fix: erase by **overwriting identifiers** (G2). This is fixable without breaking the immutability rule.
3. **US hosting + calibration secondary use are not disclosed.** The current privacy copy says "our database provider" only. Railway processes primarily in the US (Railway DPA §9.1) and has no Canadian region. The calibration dataset (engine vs agronomist) is a secondary use that has never been mentioned to anyone. Both are now covered in the drafts. Farjad also has to sign the Railway DPA.

---

## 1. PIPEDA (Canada — applies to the website and pilot as commercial activity, *to confirm*)

| # | Requirement | Source | Current state | Gap | Fix | Owner |
|---|---|---|---|---|---|---|
| P1 | Accountability: designate a person responsible; publish contact | Sch. 1, 4.1 (S1, S2) | No entity, no named officer | GAP | Name privacy officer (Farjad by default); fill placeholders | Farjad |
| P2 | Identify purposes at or before collection | Sch. 1, 4.2 | Website: purpose stated on form + privacy page. Pilot: no notice. Calibration: not stated | PARTIAL | Publish privacy-notice.md; pilot consent §2 | COO, cp-website |
| P3 | Meaningful consent; key elements up front; separate choice for non-essential purposes | Sch. 1, 4.3; OPC consent guidelines (S3) | One bundled box on the form; no marketing option; no calibration consent | PARTIAL | consent-wording.md boxes A/B, pilot §2, optional C/D/E | cp-website, COO |
| P4 | No consent required beyond what is necessary for the stated purpose | Sch. 1, 4.3.3 | n/a yet | — | Keep calibration-after-pilot optional (C) | COO |
| P5 | Limit collection | Sch. 1, 4.4 | Form collects only what is needed; free-text notes may attract extra data | OK (watch) | Hint text under notes: "Don't include sensitive personal details" | cp-website |
| P6 | Limit use, disclosure, retention; retention schedule; destroy when no longer needed | Sch. 1, 4.5 | `pilot_request.deleted_at` exists but "purged by a later job" — no job; no retention schedule | GAP | Approve proposed retention (privacy-notice §8); build purge job | Farjad, cp-database |
| P7 | Accuracy | Sch. 1, 4.6 | Farmer corrections → new versions (immutable) | OK | — | — |
| P8 | Safeguards appropriate to sensitivity | Sch. 1, 4.7 | Server-only DB access, argon2id, hashed session tokens, private bucket, org scoping (ADR 0004/0005) | PARTIAL | Confirm Railway backups encryption + access list; MFA on Railway/GitHub accounts; repo is public — confirm no data/secrets in it | CISO, cp-platform |
| P9 | Openness: policies available | Sch. 1, 4.8 | Draft privacy page live-ready, marked draft | PARTIAL | Replace with Part B copy | cp-website |
| P10 | Individual access; respond within 30 days | Sch. 1, 4.9; s. 8(3) (S1) | No documented process | GAP | Request inbox + 1-page DSAR runbook (log, verify identity, export, reply ≤30 days) | COO |
| P11 | Challenging compliance: complaint procedure | Sch. 1, 4.10 | None | GAP | Privacy-notice §12 + log complaints | COO |
| P12 | Transfers for processing: accountable; contractual comparable protection; tell people data may be accessed under foreign law | OPC cross-border guidelines 2009 (S4) | Railway DPA not signed (self-serve form on Railway compliance page); region `[RAILWAY REGION]` unknown; not disclosed | GAP | Farjad signs Railway DPA; confirm region in Railway dashboard; disclose (done in draft) | Farjad, cp-platform |
| P13 | Breach: record every breach 24 months; report to OPC + notify individuals if real risk of significant harm | PIPEDA s. 10.1; SOR/2018-64 (S5) | No breach register or procedure | GAP | 1-page breach procedure + register (date found, what, who, RROSH assessment, actions) | CISO |
| P14 | Erasure of identifying data on request / end of retention, compatible with immutable records | Sch. 1, 4.5.3 | Impossible today (see §0.2) | GAP | **G2 design** below | cp-database, CISO |

**G2 — erasure design (proposal for `cp-database`, not implemented here):**
- `recommendation.inputs_snapshot` holds no direct identifiers (crop, yield, area, dates, soil-test values, lab name — `engine/cloverproof_engine/models.py`). Keep it.
- Identifiers live in mutable tables: `farmer.display_name/notes`, `farm.name/region`, `field.name`, `field_geometry_version.geom`, `app_user` (farmer login, Phase 4), `pilot_request`, `application_log.notes`. Erase by overwriting with `"[erased]"` / NULL geometry and recording an erasure event — rows stay so foreign keys and the immutable chain survive.
- Free-text `recommendation.reason` and `review.reason` are immutable: **rule for the agronomist — no personal names or contact details in reason text.** Add to the concierge-tool UI hint.
- Proof PDFs (bucket) contain farm/farmer names: delete the object on erasure; `proof_document` row keeps only hash + key (no PII). Document that the hash then proves nothing on our side; the farmer keeps their copy.
- Backups: erased data persists in backups until they rotate — state the backup rotation period in the notice.

## 2. CASL (commercial electronic messages)

| # | Requirement | Source | Current state | Gap | Fix | Owner |
|---|---|---|---|---|---|---|
| C1 | Consent (express or implied) before sending a CEM | CASL s. 6(1)(a) (S6) | No marketing emails sent; no mechanism | OK for now | Don't send news until Box B exists | COO |
| C2 | Express consent request: purpose, identity of requester, mailing address + phone/email/web, statement that consent can be withdrawn | ECPR (CRTC) SOR/2012-36 s. 4 (S6a); CRTC 2012-548 (S7) | Not present | GAP | Box B wording (consent-wording §1) | cp-website |
| C3 | No pre-checked boxes; separate from other consents | CRTC 2012-549 (S8); 2012-548 (S7) | Single unticked box (OK) | PARTIAL | Separate Box B; never pre-tick | cp-website |
| C4 | Every CEM: sender identification + contact info + unsubscribe mechanism | CASL s. 6(2); ECPR (S6a); ISED (S10) | No CEMs yet; no template | GAP | Footer template (consent-wording §5) | COO |
| C5 | Unsubscribe effective ≤ 10 business days; mechanism valid ≥ 60 days; no login | CASL s. 11 (S6); CRTC FAQ (S9); ISED (S10) | No email provider | GAP | Choose `[EMAIL PROVIDER]` with one-click unsubscribe; suppression list | COO, Farjad (paid service) |
| C6 | Burden of proving consent is on the sender → records | CASL s. 13 (S6) | Stores `consent_text`+`consent_at` for one consent | PARTIAL | `consent_event` table (consent-wording §4) | cp-database |
| C7 | Replies to a pilot inquiry | CASL s. 10(10) inquiry-based implied consent (S6, S9a) — *section number unverified* | Box A covers contact | OK (confirm) | Keep pilot replies non-promotional | COO |
| C8 | Requesting consent by email is itself a CEM | CRTC 2012-548 (S7) | — | — | Never email people "to ask if they want news" | COO |

## 3. GDPR (EU/EEA visitors and any EU pilot applicant)

| # | Requirement | Source | Current state | Gap | Fix | Owner |
|---|---|---|---|---|---|---|
| G1 | Does GDPR apply? Art. 3(2)(a): offering goods or services to people in the EU, "irrespective of whether a payment … is required" | GDPR Art. 3(2) (S11) | Form accepts any country; EU-language locales planned. A free pilot offered to EU farms would likely be "offering services" | UNKNOWN → likely yes once EU farms are accepted | **Recommended: limit the 2027 pilot to Ontario/Canada and say so on the form.** Then GDPR exposure ≈ form submissions only | Farjad, cp-website |
| G2 | Transparency: identity, purposes + lawful basis, recipients, transfers, retention, rights, complaint right | Art. 13 (S11) | Current page lacks most | GAP | privacy-notice.md Part A | cp-website |
| G3 | Lawful basis per purpose | Art. 6 (S11) | Not stated | GAP | Table in privacy-notice §3 (6(1)(b) pilot; 6(1)(a) marketing + calibration-after-pilot; 6(1)(f) logs/audit trail) | COO |
| G4 | Consent conditions: demonstrable, distinguishable, withdrawable, not a condition of the service if unnecessary | Art. 7 (S11) | Partial | PARTIAL | consent-wording.md | cp-website |
| G5 | EU representative unless processing is occasional, not large-scale special-category, unlikely to result in risk | Art. 27(1)–(2)(a) (S11) | None | UNKNOWN | Exemption likely fits occasional form submissions; **counsel to confirm**; becomes doubtful if EU farms join the pilot | Counsel |
| G6 | Transfers: EU → Canada covered by adequacy (PIPEDA-regulated orgs); onward to US processor | Decision 2002/2/EC Art. 1 (S12); 2024 review kept it (S12b); Art. 44–46; EDPB Guidelines 05/2021 (S13); Railway DPA §9 SCCs/DPF (S15) | Not addressed | UNKNOWN | Sign Railway DPA (includes SCCs). Counsel to confirm whether direct collection by a Canadian controller is a "transfer" and what the onward-transfer position is | Farjad, Counsel |
| G7 | Processor contract | Art. 28 (S11) | Railway DPA available, not signed | GAP | Farjad signs | Farjad |
| G8 | Rights: access, rectification, erasure, restriction, portability, objection; reply within one month | Arts. 12, 15–21 (S11) | No process; erasure blocked (§1 P14) | GAP | DSAR runbook + G2 erasure design | COO, cp-database |
| G9 | Automated decision-making | Art. 22 (S11) | Every number is reviewed by the agronomist (DB-enforced, ADR 0005) | OK | State it in the notice (done) | — |
| G10 | Breach notification to authority within 72 hours where required | Art. 33 (S11) | No procedure | GAP | Same breach procedure as P13 with GDPR clock | CISO |
| G11 | Records of processing | Art. 30 (S11) | None | GAP (low) | Small-organisation exemption may apply; keep a one-page record anyway | COO |
| G12 | Cookies / ePrivacy | ePrivacy Directive (not researched) | No analytics; locale handling in `src/proxy.ts` sets no cookie (grep, 2026-11-16) | OK (verify on each release) | Re-check when any script is added | cp-website |

Other regimes **not assessed**: UK GDPR (English visitors from the UK), Turkey KVKK (`tr` locale), Quebec Law 25 (if a Quebec farm joins), Arabic-speaking jurisdictions (`ar`). I don't know their requirements well enough to state them; assess before enabling those locales or accepting farms there.

## 4. Data inventory (from the repo, 2026-11-16)

| Data | Table / location | Contains PII? | Store |
|---|---|---|---|
| Pilot request | `pilot_request` | Name, email, notes | Railway Postgres `[RAILWAY REGION]` |
| Internal users (agronomist/staff) | `app_user`, `user_session` | Email, name; hashed password; encrypted TOTP | Railway Postgres |
| Farmer, farm, field, geometry | `farmer`, `farm`, `field`, `field_geometry_version` | Names, notes, region, field boundaries | Railway Postgres |
| Soil tests | `soil_test`, values | Lab name, results (linked to field) | Railway Postgres |
| Crop plans, recommendations, reviews | `crop_plan`, `recommendation`, `review` | Indirect; free-text `reason` may contain names | Railway Postgres (immutable) |
| Application logs | `application_log` | Notes | Railway Postgres |
| Proof PDFs | Railway Bucket `proof/{org}/{rec}/{sha}.pdf` | Farm/farmer names in PDF | Railway Bucket (region fixed at creation) |
| Host logs | Railway | IP, user agent | Railway |
| Calibration view | `0009_recommendation_diff_view.sql` | Indirect (via joins) | Railway Postgres |
| Repo | GitHub `farjadp/cloverproof` (**public**) | Must contain none | GitHub — CISO to confirm seeds/fixtures use fake data only |

## 5. Ontario agronomy-advice licensing note

Question: does CloverProof (software + agronomist review) need a licence or certificate to give nutrient recommendations to Ontario farms?

| Item | What I found | Source | Confidence |
|---|---|---|---|
| NMA documents (NMS / NMP / NASM plan) | Required only for "phased-in" farms: e.g. NMS on building permit for livestock/manure facilities with >5 NU, livestock ≥300 NU; NMP when ≥300 NU or NMS farm within 100 m of a municipal well; NASM plan for off-farm materials. An NMS/NMP must be prepared by "a certified nutrient management consultant" or the farmer with the Agricultural Operation Planning Certificate; a NASM plan needs a NASM Plan Developer Certificate. | OMAFRA Factsheet 21-025 (S16, fetched and read); NMA 2002 (S17); O. Reg. 267/03 (S18, not read — e-Laws needs JavaScript) | Medium (factsheet dated April 2021) |
| Crop-only farm using commercial fertilizer, no livestock, no NASM | The factsheet lists no trigger for such farms. I found no rule requiring a certificate to give fertilizer rate advice outside NMA documents. | S16 | **Unknown — likely no licence needed, not confirmed.** Confirm with OMAFA Nutrient Management (Agricultural Information Contact Centre) or counsel |
| Certified Crop Adviser (CCA-ON) | Described as a **voluntary** certification program (since 1996). No source found making it mandatory for advice. | CCA Ontario performance objectives (S19, search) | Medium |
| "Agrologist" / P.Ag. | Ontario Institute of Professional Agrologists Act, 2013 (private Act) protects the titles P.Ag., T.Ag., A.Ag.; one secondary source claims it is also right-to-practice, contradicted by the Act's described purpose. | S20 (search only, not read) | **Unknown** on practice; titles are protected → don't use them unless held |
| Quebec | Phytoprotection recommendations are a reserved act of OAQ agronomists; PAEF (fertilization plan) has OAQ standards; whether fertilizer recommendations are reserved acts is **unconfirmed**. | OAQ documents (S21, search) | Unknown → exclude Quebec farms from the pilot or get advice first |
| 4R Nutrient Stewardship | Voluntary industry certification (Fertilizer Canada); staff giving recommendations in 4R-certified retailers need 4R training. Not law. | S22 (search) | Medium |

Recommendations (no counsel needed to act on them, but counsel should confirm the conclusion):
1. Never call a CloverProof plan an NMS, NMP or NASM plan; say so in pilot terms (done, clause 4.3) and on the PDF.
2. Intake question: "Does your farm have, or need, an NMS, NMP or NASM plan under the Nutrient Management Act?" If yes, our plan must be consistent with it and the farmer's certified planner stays responsible for it.
3. Pilot eligibility: Ontario only, crop farms preferred.
4. Farjad confirms his own credentials (P.Ag.? CCA? NMA certificate?) — this decides what titles we can print on the proof PDF.
5. Get professional-liability (E&O) insurance before the first plan.

## 6. Prioritised fix list
| Pri | Fix | Owner | Blocks |
|---|---|---|---|
| 1 | Supply `[LEGAL ENTITY]`, `[CONTACT EMAIL]`, `[ADDRESS]`, privacy officer | Farjad | Everything |
| 2 | Sign Railway DPA; confirm Railway region for Postgres + bucket | Farjad, cp-platform | Privacy notice §7 |
| 3 | Decide pilot eligibility (Ontario/Canada only?) | Farjad | GDPR scope, form copy |
| 4 | Approve retention periods | Farjad | Privacy notice §8 |
| 5 | Privacy page copy (Part B) + consent boxes A/B on the form | cp-website | Launch of form |
| 6 | `consent_event` table; erasure procedure (G2); purge job | cp-database | Pilot start |
| 7 | Breach procedure + register; DSAR runbook | CISO, COO | Pilot start |
| 8 | Counsel review of all four drafts | Farjad | Pilot start |
| 9 | E&O insurance quote | Farjad, COO | First plan delivered |

## Sources (checked 2026-11-16)
Government of Canada (priv.gc.ca, laws-lois.justice.gc.ca) and CRTC sites refused connections from this environment; e-Laws (ontario.ca/laws) needs JavaScript. Where marked *search*, I relied on search-result summaries of the official page — verify on the page before relying on it. Section numbers marked "unverified" are from memory.

- S1 PIPEDA, S.C. 2000, c. 5 — https://laws-lois.justice.gc.ca/eng/acts/P-8.6/ *(not fetched)*
- S2 OPC fair information principles — https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/p_principle/ *(not fetched)*
- S3 OPC meaningful consent guidelines — https://www.priv.gc.ca/en/privacy-topics/collecting-personal-information/consent/gl_omc_201805/ *(search)*
- S4 OPC cross-border processing guidelines (2009) — https://www.priv.gc.ca/en/privacy-topics/airports-and-borders/gl_dab_090127/ *(search: unchanged after 2019 consultation; transferring org stays accountable)*
- S5 OPC breach guidance — https://www.priv.gc.ca/en/privacy-topics/business-privacy/safeguards-and-breaches/privacy-breaches/respond-to-a-privacy-breach-at-your-business/gd_pb_201810/ ; SOR/2018-64 — https://canadagazette.gc.ca/rp-pr/p2/2018/2018-04-18/html/sor-dors64-eng.html *(search: RROSH test; 24-month records)*
- S6 CASL, S.C. 2010, c. 23 — https://laws-lois.justice.gc.ca/eng/acts/E-1.6/ *(not fetched)*; S6a ECPR (CRTC) SOR/2012-36 — https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-36/ *(not fetched)*
- S7 CRTC 2012-548 — https://crtc.gc.ca/eng/archive/2012/2012-548.htm *(search)*
- S8 CRTC 2012-549 — https://crtc.gc.ca/eng/archive/2012/2012-549.htm *(search)*
- S9 CRTC CASL FAQ — https://crtc.gc.ca/eng/com500/faq500.htm ; S9a implied-consent guidance — https://crtc.gc.ca/eng/com500/guide.htm *(search)*
- S10 ISED CASL guidance — https://ised-isde.canada.ca/site/canada-anti-spam-legislation/en *(search)*
- S11 GDPR — https://eur-lex.europa.eu/eli/reg/2016/679/oj *(fetched; Arts. 3, 4, 7, 13, 21, 27, 45 read)*
- S12 Decision 2002/2/EC — https://eur-lex.europa.eu/eli/dec/2002/2/oj *(fetched)*; S12b 2024 adequacy review (secondary) — https://www.hunton.com/privacy-and-cybersecurity-law-blog/european-commission-reviews-and-reaffirms-adequacy-decisions-for-11-jurisdictions
- S13 EDPB Guidelines 05/2021 v2 — https://edpb.europa.eu/system/files/2023-02/edpb_guidelines_05-2021_interplay_between_the_application_of_art3-chapter_v_of_the_gdpr_v2_en_0.pdf *(not read; search)*
- S14 Railway regions — https://docs.railway.com/reference/deployment-regions *(fetched)*
- S15 Railway DPA — https://railway.com/legal/dpa *(fetched)*; subprocessors — https://trust.railway.com/item/subprocessors *(not fetched)*; Railway DPF certification status: **not found** — check https://www.dataprivacyframework.gov
- S16 OMAFRA Factsheet 21-025 — https://files.ontario.ca/pdf1/omafra-when-a-farm-needs-an-nms-nmp-nasm-21-025-en-27-05-21.pdf *(fetched and read)*
- S17 Nutrient Management Act, 2002 — https://www.ontario.ca/laws/statute/02n04 *(not read)*
- S18 O. Reg. 267/03 — https://www.ontario.ca/laws/regulation/030267 *(not read)*; Ontario nutrient management page — https://www.ontario.ca/page/nutrient-management *(search)*
- S19 CCA Ontario performance objectives — https://www.certifiedcropadviser.org/files/certifiedcropadviser/ontario-performance-objectives.pdf *(search)*
- S20 Ontario Institute of Professional Agrologists Act, 2013 — https://www.ontario.ca/laws/statute/pr13009 *(search)*
- S21 OAQ PAEF reference grid — https://oaq.qc.ca/wp-content/uploads/2016/01/Grille_PAEF_2021_04_20.pdf *(search)*
- S22 Fertilizer Canada 4R Certification Standards 2026 — https://fertilizercanada.ca/wp-content/uploads/2026/07/4R-Certification-Standards-2026.pdf *(search)*

## Needs a real lawyer
1. **Limitation of liability and disclaimers** in pilot-terms.md §9 — enforceability for a free pilot with agronomist review; Consumer Protection Act, 2002 if any participant is an individual consumer.
2. **Professional-advice exposure**: whether Ontario law requires any licence/certificate to give fertilizer rate advice outside NMA documents; whether the Agrologists Act restricts practice or only titles; what Farjad may call himself on the PDF.
3. **NMA interaction**: risk if a phased-in farm uses our plan alongside (or instead of) its NMP.
4. **PIPEDA scope**: free pilot = commercial activity?; farm data of incorporated vs sole-proprietor farms as personal information.
5. **Calibration**: can in-pilot calibration be part of the core purpose; is post-pilot use valid on optional consent; is our de-identification adequate.
6. **GDPR**: Art. 3(2) applicability to the website and any EU applicant; Art. 27 representative exemption; transfer analysis for a Canadian controller using a US processor.
7. **CASL**: inquiry-based implied consent for pilot replies (s. 10(10), unverified); consent-record retention.
8. **Erasure vs immutability**: is overwriting identifiers + deleting PDFs enough to meet a deletion request; can we keep immutable plan records for legal-claims defence, and for how long.
9. **Railway DPA**: review before Farjad signs (US processing, "without undue delay" breach notice, subprocessor objection right).
10. **Translations**: legal equivalence of the notice and consent text in each locale before enabling them; KVKK / UK GDPR / Law 25 if those markets open.
11. **Insurance**: E&O coverage scope before the first plan.
