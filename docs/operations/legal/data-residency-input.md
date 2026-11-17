# Data residency — legal input to the CISO (NB-SEC-04 → decision OQ-06)

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> Prepared by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO and the CISO, 2026-11-16.
> **Decision owner: Farjad Iranmehr (OQ-06 / SC-08 / AR-17 / RK-X14).**
> Nothing was purchased, signed, submitted or sent. No vendor was contacted.

## OQ-06 — DECIDED 2026-11-16: real farmer data is stored in Canada
- **Decision (Farjad Iranmehr, 2026-11-16; source: `git diff origin/main origin/cpo-decisions-sa-fe-residency -- CLAUDE.md`, "Launch market + residency"):** real farmer data must be stored in Canada. Railway has no Canadian region, so a hosting ADR (owner `cto` + `devops-engineer`, with `ciso`) chooses the Canadian option: `[CANADIAN HOSTING PROVIDER, REGION]`. Until Canadian hosting is live, **only synthetic or de-identified data** in hosted environments.
- **My recommendation (Option A, Railway US) was not chosen.** §§1–6 below are kept as the analysis history; their option comparison and Railway-specific findings still help the hosting ADR (Options B/C, the Railway DPA checklist if the website stays on Railway).
- **Not decided by OQ-06:** where the website pilot-request form data lives — `[WEBSITE FORM DATA LOCATION — confirm in hosting ADR]`. Flag: those rows hold farmers' names and contact details. Leaving them in the US is lawful under PIPEDA with notice (L1–L3), but then no public text may say "your data is stored in Canada" without saying the request form is not (Competition Act general impression — `proof-pdf-wording.md` S6).
- **Legal points the decision does not settle (input to the hosting ADR):**
  1. "Stored in Canada" is not "out of reach of foreign law" if the provider is US-owned (S9). The notice must not imply otherwise; pilot-terms §7.6 and consent §2 carry a qualifier placeholder.
  2. Processing must also be in Canada for the claim "stored and processed in Canada" — Option B (app on Railway, DB in Canada) would store in Canada but process in the US; under the decision's wording ("stored") B may satisfy it, but the notice must then say "processed in the United States". ADR owners to choose consciously.
  3. Backups, logs, error tracking (Sentry), email delivery and the proof-PDF bucket must all be in scope of "stored in Canada", or listed as exceptions in the notice.
  4. The AI reviewer receives de-identified data only (D-7) and may be outside Canada. That fits the decision only while de-identification holds (counsel item 6).
  5. A Canadian-host DPA / terms replace the Railway DPA for farmer data; counsel review before Farjad signs.

Facts from the repo: ADR 0004 (Railway project `cloverproof`, services `Postgres` + `website`, "Railway has no Canadian region. The default region is used"); ADR 0005 (proof PDFs in a Railway bucket); `privacy-notice.md` §6–7 (Railway US disclosed; `[RAILWAY REGION]`, `[RESIDENCY DECISION]`, `[AI PROVIDER]` open). Launch = Ontario winter wheat, 5–10 farms, Feb–Apr 2027 (CLAUDE.md).

## 1. Short answer
1. **No law found that requires a private Ontario business to keep farm data in Canada.** PIPEDA regulates transfers through accountability + contract + notice, not location (S1, S4). Ontario's public-sector laws don't mandate residency either, and they don't bind us (S6). Quebec Law 25 adds a mandatory **privacy impact assessment** before data collected in Quebec leaves Quebec (S7) — not triggered while the pilot is Ontario-only.
2. **"Stored in Canada" does not mean "out of reach of US law."** Railway, AWS and DigitalOcean are US companies. The US CLOUD Act requires US providers to disclose data in their "possession, custody, or control" wherever it is stored (S9). Only a Canadian-owned provider changes that. I did not research Canadian-owned providers.
3. *(History — not chosen; see OQ-06 DECIDED above.)* **Recommendation: Option A for the 2027 pilot** (Railway US East + signed DPA + plain disclosure + no identifiers sent to the AI provider). Keep Option B ready as the exit if a co-op, lender or farmer makes Canadian storage a condition. Reasons are in §5.

## 2. What the law requires (cross-border processing)

| # | Rule | Source (checked 2026-11-16) | What it means for us |
|---|---|---|---|
| L1 | Accountability: the organisation stays responsible for personal information it transfers to a third party for processing, and must use contractual or other means to get a comparable level of protection | PIPEDA Sch. 1, 4.1.3 (S1); OPC cross-border guidelines 2009 (S4) | We stay liable for Railway, the bucket backend and the AI provider. We need a signed processor contract with each (Railway DPA; AI provider terms). |
| L2 | No federal localisation rule. A transfer for processing is a **use**, not a disclosure; the 2009 guidelines stayed unchanged after the 2019 consultation | S4, S4a, S4b | We may host in the US. No separate consent for the transfer itself (counsel to confirm — L-1 below). |
| L3 | Openness / notice: tell people their information may be processed in a foreign jurisdiction and may be accessed by its courts, law enforcement and national-security authorities | S4 *(guideline text not fetched; priv.gc.ca refused connections; confirmed via S4a/S4b summaries)* | Already in `privacy-notice.md` §7. Must name the country, not "our provider". |
| L4 | Safeguards appropriate to sensitivity, applied by the processor too | PIPEDA Sch. 1, 4.7 (S1) | DPA security exhibit + our own controls (CISO). |
| L5 | Breach: record every breach 24 months; report to OPC and notify individuals on real risk of significant harm | PIPEDA s. 10.1; SOR/2018-64 (S2) | The processor must tell us fast enough for us to assess. Railway DPA §8.1 says only "without undue delay" (S10). |
| L6 | Ontario: no private-sector privacy statute; PIPEDA applies to commercial activity in Ontario. FIPPA/MFIPPA (public institutions) do not prohibit storage outside Ontario/Canada | S6 (IPC guidance via search; Toronto guideline: "no legislative requirement specifically mandating data residency") | Nothing extra for us. Only relevant if a **public** body (e.g. a municipality, OMAFA, a university) becomes a customer — its own procurement rules may then require residency by contract. |
| L7 | Quebec: an enterprise must do a privacy impact assessment before communicating personal information outside Quebec, and may communicate it only if the PIA shows adequate protection; written agreement required | Act respecting the protection of personal information in the private sector (CQLR c. P-39.1) s. 17 (S7, statute page refused connection; confirmed via practitioner summaries S7a, S7b); CAI PIA guide Sept 2023 (S7c, French; unofficial English) | **Not triggered while the pilot is Ontario-only.** If a Quebec farm joins: PIA required before its data goes to Railway (US) — and, per S7a, arguably even to another Canadian province. Compliance-review §5 already says exclude Quebec farms for agronomy-licensing reasons. |
| L8 | Other provinces with public-sector residency limits (Nova Scotia PIIDPA; BC FOIPPA residency rule relaxed in 2021) | S8 (search only) | Public bodies only. Not us. |
| L9 | GDPR (EU) | compliance-review.md G1/G6 | Pilot Ontario-only → only website form data. Railway DPA §9 has SCCs (S10). |
| L10 | Contractual residency | S8a (Blakes summary: residency "may be imposed by contract") | **The real driver for us.** Co-ops, lenders, input dealers or government grant programs may require Canadian storage in their contracts. Unknown until we ask them. |

**What farmers and co-ops may expect (opinion, labelled):** I found no Canadian agricultural-data code that requires residency, and I don't know whether one exists — check before relying on that. Expect three questions from farmers: *who can see my data, will you sell it, can I get it deleted.* "Stored in the US" is a common objection in Canadian ag-tech sales, but not a legal bar. A co-op or lender partner is more likely than a farmer to put residency in a contract (L10). Ask the first partners directly; that answer decides between A and B.

## 3. Options

Prices are list prices from the vendor's own page on 2026-11-16, USD, before tax; **monthly figures are my estimates** (hourly × 730). No purchase was made.

### Option A — stay on Railway (US), disclose, sign the DPA
| Item | Detail |
|---|---|
| Set-up | Postgres + bucket + app in **US East (Virginia)** (closest Railway region to Ontario; S11). EU West (Amsterdam) is no better legally: Railway is still a US company (S9) and its DPA says primary processing is in the US (S10 §9.1). |
| Legal fit | Meets L1–L5 **if** the DPA is signed and the notice names the US. Same position as almost every Canadian SaaS on US clouds. |
| Effort | None for engineering. Farjad: sign DPA (DocuSign form, S10 §14) after counsel review; set region; fill `[RAILWAY REGION]`. |
| Cost | Current Railway plan; Pro is $20/month per workspace incl. $20 usage; volume ≈ $0.15/GB-month; object storage $0.015/GB-month (S12). No new cost. |
| Risk | US-law access (S9); weak DPA terms (§4 below: undated, no fixed breach-notice clock, Tigris not on the sub-processor list, log retention unclear); sales objection from residency-sensitive partners. |

### Option B — app on Railway, database (and bucket) in Canada
| Item | Detail |
|---|---|
| Set-up | Managed Postgres in Canada, e.g. **AWS RDS ca-central-1** (Canada Central) or **DigitalOcean Managed PostgreSQL TOR1** (Toronto). The proof-PDF bucket must move too (S3 ca-central-1 or DO Spaces TOR1), or PDFs stay in the US. |
| Legal fit | Data **at rest** in Canada. Data is still **processed** in the US (the Railway app reads it, holds it in memory, writes logs), so the notice must still say "processed in the United States". All three vendors are US companies (S9). Gains are contractual/marketing, not a legal requirement. |
| Effort (estimate) | Medium: new DB provider account + ADR; PostGIS on the chosen service (**unverified for DO** — ADR 0002 requires PostGIS); TLS between Railway and the DB over the public internet; IP allow-listing (Railway egress IPs need checking); cross-border latency on every query; a second DPA (AWS or DO) to review; backups now split across two vendors. |
| Cost (estimate) | **AWS RDS PostgreSQL, ca-central-1** (AWS price list, publication 2026-11-13, S13): db.t4g.micro Single-AZ $0.018/h (≈ $13/month), db.t4g.small Single-AZ $0.035/h (≈ $26/month), Multi-AZ small $0.070/h (≈ $51/month); gp3 storage $0.127/GB-month (20 GB ≈ $2.50). **DigitalOcean Managed PostgreSQL**: smallest plan 1 GiB / 1 vCPU / 10–30 GiB, $15.15/month; page does not say whether prices differ by region or what a standby node costs (S14); TOR1 supports Managed PostgreSQL and Spaces (S15). **Crunchy Bridge**: I could not confirm a Canadian region (docs page 404; S16) — don't consider it until verified. Plus Railway as today. |
| Risk | More moving parts for a 5–10 farm pilot; split incident handling; latency; still US-law reachable. |

### Option C — full move to a Canadian region
| Item | Detail |
|---|---|
| Set-up | App + DB + bucket in one Canadian region: DO App Platform (TOR) + Managed PostgreSQL TOR1 + Spaces TOR1 (all listed for TOR in S15), or AWS ca-central-1 (compute + RDS + S3). Optionally a Canadian-owned provider to remove US-law reach (not researched). |
| Legal fit | Best story: stored **and** processed in Canada. Still US-law reachable with a US vendor (S9). |
| Effort (estimate) | High: reverses ADR 0004; new deploy pipeline, migrations runner, secrets, health checks, monitoring; website moves too or stays split. Weeks of `cp-platform` time during S2–S5 when the concierge tool is the priority. |
| Cost (estimate) | DB as in B + compute (DO App Platform / AWS compute prices not fetched — **unknown**). |
| Risk | Schedule risk to the Feb 2027 pilot; migration of data and immutable tables (triggers block TRUNCATE; dump/restore only). |

### Cross-cutting: the AI reviewer
The AI reviewer (`ai_reviewed`; `privacy-notice.md` §6 `[AI PROVIDER]`) sends plan data to an AI provider, almost certainly in the US. **Residency of the database is undone if identifiable data goes to the AI provider.** D-7 is DECIDED (CPO, 2026-11-16): the AI reviewer receives de-identified case data only, never identifiers. Therefore, whatever option is chosen: send only pseudonymous plan inputs/outputs (no names, contacts, farm/field names, coordinates, free-text notes), sign or accept the provider's commercial/data terms (counsel to review), confirm retention and no-training terms, and list it in the notice.

## 4. Railway DPA review checklist (for counsel before Farjad signs)
Source: Railway Data Processing Addendum, https://railway.com/legal/dpa (S10), fetched 2026-11-16. **The DPA shows no version or effective date** — save a PDF copy of the exact text on the day it is signed.

| # | Check | What the DPA says | Gap / question for Railway or counsel |
|---|---|---|---|
| D1 | Roles | Railway = processor (§2.1, per compliance-review S15) | OK. |
| D2 | Processing location | "Company's primary processing operations take place in the United States" (§9.1); Railway "may provide options for certain local data storage" for paid customers (§9.1) | Ask Railway whether any Canadian storage option exists for paid/Enterprise plans. Exhibit C says "Railway infrastructure is run on Google Cloud Platform" while the regions page lists "Metal" regions (S11) — ask which is current and which entities touch our data. |
| D3 | Sub-processors | List at trust.railway.com (§6.2); ≥10 days' notice by list update + email before a new one; objection within 10 days on reasonable data-protection grounds; remedy = discontinue the affected service (§6.2–6.3) | The list (S17) shows only Fathom Analytics, Cloudflare, Causal, Customer.io, Stripe — no purposes, no locations. **Tigris** (bucket backend per Railway support, S18) and any infrastructure provider are not listed. Ask for the full list with purpose + location. Subscribe to change emails. |
| D4 | Transfer mechanism | EU SCCs deemed entered into (Modules 1–3) and DPF where certified (§9.2); UK SCCs/Addendum (§9.4, Exh. D); Swiss (§9.5) | Nothing Canada-specific (none needed under L2). Railway DPF certification **not found** earlier — check https://www.dataprivacyframework.gov. |
| D5 | Breach notice | Inform "without undue delay" (§8.1); assist with notifying regulators and individuals (§8.2); no hour count; no list of notice contents | Ask for a fixed clock (e.g. 48–72 h) and minimum contents (what, whose, when, containment). We need enough to make the RROSH assessment (L5). |
| D6 | Deletion on termination | "Upon the termination or expiration of the Agreement, at Customer's choice, Company shall return or delete Personal Data" (§12); account deletion → Railway "purges or anonymizes" (Exh. C) | **No deadline**, nothing on backups. Ask: deletion period, backup expiry, written confirmation. |
| D7 | Backups | "All customer data is backed up daily", "across multiple sites and regions" (Exh. C); volume backups we control: daily kept 6 days, weekly 27 days, monthly 89 days (S19) | Railway's own platform backups: where (regions) and how long? Needed for the erasure notice (`erasure-requirements.md` ER-30). |
| D8 | Logs | Log view retention: Hobby 7 days, Pro 30 days, Enterprise up to 90 days; "Upgrading plans will immediately restore logs that were previously outside of the retention period" (S20) | **Logs are kept longer than shown.** Ask the actual log retention. Log content may include IPs and request data. |
| D9 | Data-subject requests | Railway refers data subjects to us; assists where needed, at our cost (§11) | OK. We run requests ourselves. |
| D10 | Audits | Once per calendar year, business hours, at our cost; certifications/reports may be offered first (§5.1) | Ask for the SOC 2 report (if any) under NDA — CISO. |
| D11 | Liability | No cap in the DPA; claims subject to the main Agreement's exclusions and limits (preamble) | Counsel to read the Terms of Service limits alongside the DPA. |
| D12 | Execution | Becomes binding on Railway's countersignature of the DocuSign form (§14) | Farjad signs, not an agent. Keep the countersigned copy in the company records. |

## 5. Recommendation *(history — not chosen 2026-11-16)*
**A for the 2027 pilot, with three conditions; revisit at S13 or the first partner contract.**
1. Legal fit is the same as B under PIPEDA (L1–L3); B's gain is a sales/contract argument, and B still processes in the US.
2. Pilot size (5–10 Ontario farms, mostly pseudonymous agronomic data after ER-design) doesn't justify the C schedule risk to Feb 2027.
3. Conditions: (a) Railway DPA reviewed by counsel and signed by Farjad; (b) notice names the US and US-law access (done in draft); (c) D-7 as decided: the AI provider receives no direct identifiers.
4. Switch to B if any of: a co-op/lender/grant contract requires Canadian storage; a Quebec farm is accepted; Railway can't answer D3/D6/D7 satisfactorily. Do the B ADR only then.

## 6. Must be decided before the first real farmer data (owner: Farjad unless stated)
1. ~~OQ-06: A, B or C~~ — DECIDED 2026-11-16: Canada. Hosting ADR picks B or C and the provider (`cto` + `devops-engineer`, with `ciso`); fills `[CANADIAN HOSTING PROVIDER, REGION]`.
2. Website form data location — `[WEBSITE FORM DATA LOCATION — confirm in hosting ADR]`. If it stays on Railway, choose the region (bucket region is permanent once created, S18).
3. Canadian host's DPA / data terms: counsel review, then Farjad signs. Railway DPA (§4): needed only for whatever stays on Railway (website, synthetic/de-identified environments).
4. AI provider: which one, its data terms, what fields it receives (D-7 decided: de-identified only; a change needs a DPA + notice, Farjad Iranmehr decides).
5. Pilot eligibility stays Ontario-only (keeps Quebec PIA and GDPR out).
6. Privacy notice §7: delete the US option for farmer data; owner of `privacy-notice.md` (not edited here).
7. Ask the first partner co-ops/lenders whether they require Canadian storage (COO, before contracts).

## Sources (checked 2026-11-16)
priv.gc.ca, laws-lois.justice.gc.ca and legisquebec.gouv.qc.ca refused connections from this environment; items marked *search* rely on search-result summaries — verify on the official page before reliance.
- S1 PIPEDA, S.C. 2000, c. 5, Sch. 1 — https://laws-lois.justice.gc.ca/eng/acts/P-8.6/ *(not fetched)*
- S2 Breach of Security Safeguards Regulations, SOR/2018-64 — https://canadagazette.gc.ca/rp-pr/p2/2018/2018-04-18/html/sor-dors64-eng.html *(search, see compliance-review S5)*
- S4 OPC, Guidelines for processing personal data across borders (2009) — https://www.priv.gc.ca/en/privacy-topics/airports-and-borders/gl_dab_090127/ *(not fetched — connection refused)*; S4a Torys, "OPC not changing guidelines on transfers for processing" (2019) — https://www.torys.com/insights/publications/2019/09/opc-not-changing-guidelines-on-transfers-for-processing *(search)*; S4b Goodmans — https://goodmans.ca/insights/article/Privacy_Commissioner_Retains_Original_Policy_on_Cross_Border_Transfers_of_Personal_Information *(search: transfer = use, not disclosure)*
- S6 IPC Ontario guidance on contracting with third parties — https://www.ipc.on.ca/media/4297/download *(search)*; City of Toronto Data Residency for Cloud Technology Guideline — https://www.toronto.ca/wp-content/uploads/2023/08/966e-Data-Residency-for-Cloud-Technology-Guidelinev1.0.pdf *(search)*
- S7 CQLR c. P-39.1 s. 17 — https://www.legisquebec.gouv.qc.ca/en/document/cs/P-39.1 *(403, not fetched)*; S7a Hilo summary — https://hilotech.ca/en/wiki/law-25/cross-border-transfers *(search)*; S7b IAB Canada cross-border guidance — https://iabcanada.com/wp-content/uploads/2022/06/IAB-Canada_BPG-Que-Cross-Border-Transfer-Guidance_June-2022.pdf *(search)*; S7c CAI PIA guide, Dentons unofficial translation — https://www.dentonsdata.com/wp-content/uploads/2024/01/CAI_PIA_Guide_Dentons-Unofficial-Translation76150102.3.pdf *(search)*
- S8 Nova Scotia PIIDPA FAQ — https://novascotia.ca/just/IAP/PIIDPAquest.asp *(search)*; UBC on BC FOIPPA Bill 22 — https://privacymatters.ubc.ca/resources/bill22 *(search)*; S8a Blakes Data Governor May 2025 — https://www.blakes.com/insights/blakes-data-governor-may-2025/ *(search)*
- S9 US CLOUD Act, 18 U.S.C. § 2713 — DOJ white paper https://www.justice.gov/criminal/media/999601/dl and FAQ https://www.justice.gov/criminal/media/999616/dl *(search)*
- S10 Railway Data Processing Addendum — https://railway.com/legal/dpa *(fetched; §§5.1, 6.2–6.3, 8.1–8.2, 9.1–9.5, 11, 12, 14, Exh. C read)*
- S11 Railway deployment regions — https://docs.railway.com/reference/deployment-regions *(fetched: US West Metal, US East Metal, EU West Metal, Southeast Asia Metal; no Canada)*
- S12 Railway pricing — https://railway.com/pricing *(fetched)*
- S13 AWS Price List, AmazonRDS ca-central-1 offer file (publication 2026-11-13) — https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/ca-central-1/index.json *(fetched)*; human-readable: https://aws.amazon.com/rds/postgresql/pricing/
- S14 DigitalOcean Managed Databases pricing — https://www.digitalocean.com/pricing/managed-databases *(fetched)*
- S15 DigitalOcean regional availability — https://docs.digitalocean.com/platform/regional-availability/ *(fetched)*
- S16 Crunchy Bridge regions — https://docs.crunchybridge.com/concepts/regions *(404; region list not verified)*
- S17 Railway sub-processors — https://trust.railway.com/item/subprocessors *(fetched; names only)*
- S18 Railway Storage Buckets — https://docs.railway.com/guides/storage-buckets *(search: region chosen at creation, cannot change)*; Tigris backend — https://station.railway.com/questions/storage-buckets-eu-west-and-tigris-as-67a8d930 *(search; community thread, not a contract)*
- S19 Railway backups — https://docs.railway.com/reference/backups *(fetched)*
- S20 Railway logs — https://docs.railway.com/guides/logs *(fetched)*

## Needs licensed counsel
1. Confirm PIPEDA needs no separate consent for transfer to a US processor (L2) and that our notice wording meets L3 — now relevant only to website form data and any non-Canadian sub-processor.
1a. Wording of the Canadian-storage commitment if the Canadian host is US-owned, and whether "stored in Canada" is misleading if the app processes in the US (Option B).
2. Railway DPA (§4) and Railway Terms of Service liability limits — before Farjad signs.
3. AI provider's data terms (retention, training, sub-processors, location).
4. Quebec s. 17 scope (does hosting in another province count?) if Quebec is ever opened.
5. Whether any partner/grant contract clause on residency binds us (review each contract when it arrives).
6. Whether pseudonymous plan data sent to the AI provider is still personal information under PIPEDA.
