# ADR 0009 — answers from `ciso` / `coo` (questions 1, 2, 4, 5, 6)

**This is not legal advice; a licensed Ontario lawyer should review before use.**

- Date: 2026-11-16. Author: `legal-compliance-specialist` for `ciso` (privacy) with the `coo` legal track.
- Answers: `docs/adr/0009-production-data-residency-canada.md` § "Questions for `ciso` / `coo`". Q3 (backups location) belongs to `devops-engineer`; placeholder below.
- Context: Farjad Iranmehr decided on 2026-11-16: Railway (US) now, holding synthetic or de-identified data only, plus the website pilot form with its US storage disclosed. Production moves to a Canadian host before the first real farmer data (S5, from Jan 18 2027). ADR 0009 recommends DigitalOcean TOR1, with an AWS S3 ca-central-1 Object Lock copy for backups.
- Sources are listed at the end. I read each one on 2026-11-16 unless it is marked [verify]. Nothing here was signed, accepted, sent or filed.

## Answer table

| Q | Position | Action | Owner | Due |
|---|---|---|---|---|
| 1 DPA | **DO's DPA is not enough on its own.** It has no Canada clause and no commitment to keep data in the chosen region (AWS DPA §12.1 has one). It also has no deletion deadline for backups, and its transfer basis is the EU-US DPF, which is irrelevant to us. DO's own sub-processor list names **AWS (USA) for "server backups and infrastructure"** across all DO services, plus Cloudflare (USA) in front of App Platform and Traversal (USA) for support. That directly contradicts "backups stay in Canada". | Send the written questions in §1.3 to DO. Accept only if DO confirms in writing that managed-PG backups, PITR WAL, Spaces and App Platform logs for TOR1 stay in Canada, or tells us which ones leave. If it refuses or is silent, switch to option C (ADR rule). Counsel reviews the DPA and ToS before Farjad accepts. | `coo` drafts, Farjad Iranmehr sends; `ciso` assesses the reply | Questions sent by **Nov 27**; answer by **Dec 11** (ADR gate); DPA accepted before **Jan 4** |
| 2 Breach | **The providers give no fixed clock.** DO DPA §7.5 says "without undue delay", by email to the account address. AWS DPA §9.1 says the same, and AWS assesses only incidents that succeeded (§9.3). PIPEDA's duty runs from when **we** determine a breach happened, so a slow provider delays our clock but does not excuse us. Under 4.1.3 accountability the contract is weak; we compensate with our own detection. | Internal clock (§2.3): T+1 h triage, T+24 h containment and a first RROSH call, **T+72 h a recorded RROSH decision**. If RROSH: report to the OPC and notify individuals "as soon as feasible" (target within 72 h of the decision). Every breach goes into the 24-month register. Ask DO and AWS for a 72 h commitment (expect a no). Route provider notices to a monitored alias. | `ciso` | Runbook and register template by **Jan 4**; alias and alerts live before **Jan 18** |
| 4 Sentry | **Acceptable, with conditions.** Events go out of Canada in scrubbed form, so this is a disclosed exception and not a residency breach. Use the **EU (Frankfurt)** organisation: the region can't be changed later, and some metadata stays in the US either way. Scrub **in the SDK** (`before_send`), not only server-side. Developer plan, so errors are kept 30 days. List Sentry in the notice. Fallback if a partner requires all-Canada: **log-only** (DO logs in TOR1) or self-hosted GlitchTip in TOR1. | Apply the config in §4.3 and add a unit test that a scrubbed event contains no PII. Create the org in the EU region. Turn on server-side scrubbing plus "prevent storing IP". Add Sentry to notice §6/§7/§8. | `cp-platform` (config, test); `ciso` (review); `coo` (notice) | Before Sentry gets its first DSN on any real-data environment; no later than **Jan 4** |
| 5 CLOUD Act | **Disclose. Don't change provider for the 5–10 farm pilot.** No statute requires a non-US-owned provider for private-sector farm data in Ontario. The risk is a **contract clause** from a co-op, lender or public body. If a partner requires non-US ownership, re-open ADR 0009 and move to F (OVH, French parent; still needs research) or a Canadian-owned host. | Before each partner contract, the COO asks in writing whether the partner requires (a) Canadian storage or (b) a non-US-owned provider. Add the notice wording in §5.3. Counsel confirms the wording is not misleading. | `coo` (partner question, notice); counsel | Partner question before the first partner contract or MOU; notice wording before **Jan 11–15** fill-in |
| 6 Backups vs erasure | **Every copy is gone within 35 days.** DO 7-day PITR plus daily backups (DO retention [verify], must be ≤ 35 days). `age` dumps: hourly kept 72 h, daily kept 35 days. **Drop the 12-month monthly tier.** S3 Object Lock in **compliance mode, 35 days**, then a lifecycle rule expires objects on day 36. L5 cold copy: keep only the newest copy and destroy the previous one each month. Erasure does not touch locked copies; ER-31 replays erasures after any restore. Notice text: "deleted from backups within 35 days". Proof-PDF copies (L4) under compliance lock conflict with erasure; see §6.4. | `devops-engineer` / `cp-database`: change L3 retention in `backup-restore-test-plan.md` and set the bucket default retention (35 d, COMPLIANCE) plus lifecycle. `coo`: notice §8 and §10 and the ER-30 reply text. Counsel: is 35 days acceptable, and does "beyond use" in locked backups meet PIPEDA principle 4.5.3 and GDPR Art. 17. | `devops-engineer`, `cp-database`, `coo`, counsel | Retention set before the bucket is created (**Jan 4–8**); first real data **Jan 18** |
| 3 Backups location | Answered by `devops-engineer`. Note for them: DO's sub-processor list names AWS (USA) for backups (§1.2). | See `backup-restore-test-plan.md` §ADR 0009 Q3 | `devops-engineer` | Dec 11 |

**Must be true before Jan 4 (production build):** DO written answers in hand (Q1). Counsel has reviewed the DO and AWS DPAs and Farjad has accepted them, with a dated copy saved (Q1). The breach runbook and register exist (Q2). The Sentry config and scrub test are merged, or Sentry is not connected (Q4). The 35-day retention is designed into the backup job and bucket (Q6).

**Must be true before first real data (Jan 18):** the provider-notice alias is monitored (Q2). Notice §6/§7/§8/§10 is filled with DO TOR1, US-ownership wording, Sentry EU and "35 days" (Q4–Q6). Object Lock retention and lifecycle are verified on the live bucket (Q6). The ER-31 replay has been tested on a restore (AT-14). No partner has asked for non-US ownership, or the ADR has been re-opened (Q5).

---

## 1. DPA — DigitalOcean (and AWS for the backup bucket)

### 1.1 What DO's DPA says (DPA "Last Updated on October 14, 2026", fetched)
| Topic | DO DPA text | Gap for us |
|---|---|---|
| Parties | DigitalOcean, LLC; addendum to the Customer Terms of Service (§1.1) | US entity. Canadian contracting entity: none found. The controller (`[LEGAL ENTITY]`, privacy-posture F1) must exist before we accept. |
| Canada / region | No mention of Canada. No clause that keeps data in the region we choose. Schedule 2 §3 only says sub-processors must "not change the location where personal data is processed". | **Main gap.** AWS DPA §12.1 commits AWS not to move data out of the chosen Region except to provide the service or to comply with the law. DO has no equivalent. |
| Transfers | §4.1 relies on DO's EU-U.S. Data Privacy Framework certification; §4.2 falls back to the SCCs | Written for the EU. Says nothing about Canada → US transfers. |
| Sub-processors | List on the Subprocessors page (Sch. 3 §1). **At least 30 days** to object to a new one (§7.4.3). On a reasonable objection DO "immediately cease[s]" using it, and either side may terminate if it isn't resolved in 15 days. DO decides alone whether an objection is reasonable. | Acceptable mechanism. The **content** of the list is the problem (§1.2). |
| Breach | §7.5: "without undue delay", by email to the account address | No fixed clock (Q2). |
| Deletion | §7.6: everything deleted "no later than 30 days following the date of de-activation". Backups: DO may keep data "archived on back-up systems subject to automated retention and disposal", isolated from processing; also "as required by applicable law". | Gives a 30-day deadline, but **no expiry date for backups**. |
| Audit | §7.7.1 documentation or questionnaire, at most once a year. §7.7.2 on-site audit only under the SCCs. | Acceptable for our size. |
| Governing law | Defers to the Agreement; the SCC schedules name the Netherlands or an EU state | Counsel should check the ToS governing law and liability cap. |

### 1.2 DO sub-processors (page "Last updated June 10, 2026", fetched)
- **All DO services:** Amazon Web Services, USA (WA), "Server backups and infrastructure". Cloudflare, USA (CA), "Platform security". Traversal, USA (NY), "Customer troubleshooting and support".
- **Optional add-ons:** "DBaaS" by Aiven (Finland), Google GCP (USA), MongoDB, Percona (USA). Cloudflare for "App Platform, load balancing, CDN". Storage by Oracle, Wasabi (cold storage) and VAST (all USA).
- No sub-processor lists a Canadian location. Data-centre locations are on a separate page (not checked) [verify].
- **Consequence:** on DO's own documents, managed-PG backups or WAL, Spaces replicas, App Platform traffic (TLS at Cloudflare) and support sessions **may be processed in the US**. ADR 0009 already treats this as the main risk. The list makes it concrete. DO's PG features page says backups are taken daily with 7-day PITR, but not **where** they are stored. A DO tutorial and a community post suggest the same region or a separate data centre (search results only, not contractual) [verify].

### 1.3 Ask DO in writing (Farjad sends; keep the reply with the DPA copy)
1. For Managed PostgreSQL in TOR1: where are daily backups and PITR WAL stored (country and city)? Does the AWS backup sub-processor ever hold them? Which DBaaS sub-processor, if any, operates our cluster?
2. For Spaces TOR1 and App Platform TOR1: where are object replicas, build logs, runtime logs and the container registry stored? Does Cloudflare terminate TLS for App Platform outside Canada?
3. How long are managed-DB backups kept: our daily backups, DO's internal backups, and the time to purge after we delete a cluster or deactivate the account?
4. Will DO sign a written addendum that keeps Customer Data for TOR1 resources in Canada (wording like AWS DPA §12.1), with notice before any change?
5. A breach notice clock. We ask for 72 h from awareness, plus the security contact to use.
6. Can support staff (Traversal, DO) access customer content? From which countries? Is there a logged approval step?
7. Which DO entity contracts with a Canadian customer? Is there a Canadian DPA or PIPEDA addendum?

### 1.4 AWS (S3 ca-central-1, backup bucket)
AWS DPA §12.1 commits AWS to the chosen Region. §14 lets the customer return or delete data up to 90 days after termination using the Service Controls. §9 covers breaches. The PDF metadata is dated 2023-07-27, so check AWS's current version before accepting [verify]. AWS's sub-processor list was not checked [verify]. AWS is the stronger contract of the two on residency.

### 1.5 GCP (runner-up C)
I did not review the Cloud Data Processing Addendum (CDPA) this session [verify]. Do it only if DO fails the Dec 11 gate.

## 2. Breach notice

### 2.1 Provider commitments
- DO DPA §7.5: "without undue delay", email to the account address; no hours.
- AWS DPA §9.1: "without undue delay after becoming aware". §9.2 adds information "as AWS is able to disclose". §9.3: unsuccessful attempts (scans, failed logins, DoS) are not reported. §9.4: notices go to the administrators' contact details, which we must keep current. §9.5: the customer decides on its own legal notices.
- Sentry DPA §4.2: "promptly and without undue delay" (page date not shown) [verify].

### 2.2 Is that enough for PIPEDA?
- s.10.1: report to the OPC and notify individuals "as soon as feasible" after we determine that a breach creates a real risk of significant harm (RROSH). RROSH depends on how sensitive the information is and how likely it is to be misused. s.10.3 and SOR/2018-64 s.6: keep a record of **every** breach for 24 months after the determination. Sources: privacy-posture.md §2.1 (statute marked [re-verify]; regulations fetched there). I could not reach laws-lois.justice.gc.ca or priv.gc.ca this session [verify].
- "Without undue delay" doesn't break the law: our duty starts when we determine the breach, not when it happened. But PIPEDA principle 4.1.3 makes us use "contractual or other means" to get comparable protection, and an open-ended notice period is weak there. **Position:** ask for 72 h, accept "without undue delay" if refused (likely for self-serve accounts), and compensate with our own detection. The contract gives us no early warning. Counsel to confirm.
- Our scale makes RROSH assessment quick (≤ 10 farms, ~100s of rows). What delays us is detection, not analysis.

### 2.3 Proposed internal clock (T0 = first sign: provider email, alert, report from a person, or our own finding)
| Time | Step |
|---|---|
| T0 + 1 h | Triage: is it a breach of security safeguards involving personal information? Open a register entry. Preserve logs and snapshots. Name an incident lead (`ciso`; Farjad Iranmehr informed). |
| T0 + 24 h | Containment: rotate keys and secrets, revoke sessions, lock accounts. Scope: which tables and rows, which farmers. Make a first RROSH call. Ask the provider for details in writing. |
| T0 + 72 h | **Recorded RROSH decision**, with reasons, signed off by Farjad Iranmehr. This also meets GDPR Art. 33's 72 h for any EU website-form data. |
| If RROSH | Report to the OPC (SOR/2018-64 s.2 contents). Direct notice to the affected people (s.3–4) and to any organisation that can reduce the harm, "as soon as feasible". Target: within 72 h of the decision. Counsel reviews the letters. |
| Always | Register entry (date, circumstances, information involved, RROSH reasons) kept **≥ 24 months** from the determination date, outside the main DB (notice §8 already says 24 months). |

Prerequisites: DO and AWS account contacts point to a monitored alias, not one personal inbox. DO status and security emails are on. DB connection and role alerts (see `threat-model-webapp.md`). Runbook, register template and letter templates stored privately (not in this public repo; see privacy-posture §5.8).

## 3. Q3 backups — see backup-restore-test-plan.md §ADR 0009 Q3 (§12)
*(Placeholder. Answered by `devops-engineer`. Input from this review: DO's sub-processor list names AWS (USA) for "server backups and infrastructure" (§1.2), so the written location confirmation from DO has to name managed-DB backups and WAL specifically.)*

## 4. Sentry

### 4.1 Facts (fetched)
- Sentry SaaS offers two storage regions: **US (Iowa)** and **EU (Frankfurt)**. No Canada. "Once selected, your data storage location can't be changed"; switching means a new organisation.
- Events, logs, replays and their backups stay in the chosen region. Accounts, org settings, audit logs, project metadata, usage data and **support tickets** stay in the US whatever region you pick.
- Server-side scrubbing is on by default. Advanced Data Scrubbing rules redact before storage. Both run **after** the data reaches Sentry. Only SDK hooks or a local Relay stop data leaving us.
- Python SDK: before 3.0, `send_default_pii` (keep `False`) plus `EventScrubber`; in 3.x the option is `data_collection`, and the old scrubber "has no effect" there. Check the pinned SDK version [verify exact 3.x option names].
- Retention: errors 30 days on Developer, 90 days on Team and Business; logs 30 days on all plans. The page names no customer setting to shorten retention.
- Sentry DPA: breach notice "promptly and without undue delay" (§4.2); 30 days' notice of new sub-processors (§7.2); no fixed deletion deadline (§3.2).
- Repo: ADR 0009 lists Sentry free tier as a remaining out-of-Canada processor. I did not confirm whether an SDK is already installed.

### 4.2 Position
- PIPEDA has no residency rule (data-residency-input L2). The Canadian-storage commitment is our own policy (OQ-06), so Sentry is an **exception we disclose**, not a breach of law. It stays acceptable only if events carry **no farmer-identifying data**, enforced before they leave the process.
- **EU over US.** Event data is then not stored in the US (though Sentry is still a US company, so the CLOUD Act still applies). Canada has EU adequacy, so this stays clean for EU website visitors. The region can't be changed later, so decide once. The US metadata (accounts, audit logs) holds staff data only.
- **Developer plan:** 30-day error retention, which fits the 35-day backup window in Q6.

### 4.3 Required config (app, worker; website if a browser SDK is added)
1. `send_default_pii=False` (SDK < 3.0), or the 3.x `data_collection` equivalent with user, IP, cookies and bodies excluded [verify names].
2. `max_request_body_size="never"`. No request bodies, ever: form posts carry soil tests, names and notes.
3. `include_local_variables=False` (3.x: `stack_frame_variables` off). Local variables in tracebacks are the most likely leak of farm data.
4. `before_send`: delete `request.data`, `request.cookies` and `request.query_string`. Keep headers only from an allowlist (no `Authorization`, `Cookie`, `X-Forwarded-For`). Set `user` = pseudonymous id only. Drop `extra` and `contexts` keys not on an allowlist. Replace exception messages that may embed values (pydantic validation errors echo input) with type and field name only.
5. `before_breadcrumb`: drop logging breadcrumbs with message bodies and SQL breadcrumbs carrying parameters. Or set breadcrumbs to none.
6. `traces_sample_rate=0` and no profiling or session replay in the pilot. Spans carry SQL and URLs.
7. In Sentry: server-side scrubbing **on**, "Prevent storing of IP addresses" **on**, Advanced Data Scrubbing rules for email, phone, postal code, lat/long and `$http.cookies`. These are a second layer, not the control.
8. Test: a unit test builds an event from a request carrying a fake farmer name, email and soil value, runs `before_send`, and asserts none survive. Required to merge.
9. Environments: only `production` and `staging` send. Never point CI or dev at the DSN with real data.

### 4.4 Privacy notice
**Yes, list it.** Notice L3 (data-residency-input) requires naming the foreign location. §6 now: "**Sentry (Functional Software, Inc., US), error reports, stored in the EU (Germany)**: technical error reports about our software; we remove names, contact details and farm information before they are sent; kept 30 days." Add it to the §7 out-of-Canada list and the §8 retention table.

### 4.5 Alternative if refused (by a partner or by counsel)
- **Log-only:** structured logs to DO App Platform runtime logs in TOR1 (location to confirm in the Q1 letter), a "5xx in last hour" alert, no third party. This is the cheapest option and enough for 1 internal user.
- **Self-hosted GlitchTip** (Sentry-SDK compatible) as a small TOR1 app with Postgres: errors stay in Canada, at the cost of one more service to patch. I would not run self-hosted Sentry for a team of 1–2.

## 5. CLOUD Act

### 5.1 Facts
DO, AWS, Google, Microsoft, Fly.io and Sentry are US-owned. 18 U.S.C. §2713 reaches data in a US provider's "possession, custody, or control" wherever it is stored (data-residency-input S9; DOJ papers via search) [verify]. OVH has a French parent and a Canadian subsidiary (ADR 0009 F), which reduces US exposure but has not been researched. No statute applicable to us requires a non-US-owned provider (data-residency-input L2, L6). Public bodies and contracts can impose one (L6, L10).

### 5.2 Position for the 5–10 farm pilot
- **Do partners likely need it?** I don't know; nobody has been asked. My estimate: most Ontario co-ops and lenders ask for Canadian storage at most, not non-US ownership. Federal or provincial bodies (e.g. a grant program, a university) are the likelier source of a stricter clause. This is an estimate, not evidence.
- **Position:** keep D (or C). Disclose the US ownership. The COO asks every prospective partner in writing before signing: "Do you require that farm data be (a) stored in Canada, (b) held by a provider not owned by a US company?" If (b) is yes for a partner we need, **re-open ADR 0009** (OVH BHS or a Canadian-owned host). Budget one sprint; OVH has no PaaS (ADR: high ops burden).
- Our own mitigation, independent of the provider: encryption at rest by the provider, `age`-encrypted dumps with keys we hold, and a policy to tell the affected farmer about any government demand where the law allows. Counsel to confirm that this wording is lawful to promise.

### 5.3 Notice wording (fills §7 and Part B "Where it is stored")
> "Your pilot farm data is stored in Canada, in Toronto, by DigitalOcean, our hosting provider. DigitalOcean is a US company. Even though your data is stored in Canada, US authorities may be able to require DigitalOcean to give them access to it under US law. Encrypted backup copies are kept in Canada, in Montréal, by Amazon Web Services, also a US company. Technical error reports, with names, contact details and farm information removed, are stored in Germany by Sentry, a US company."

Hold this text until DO confirms the Q1 locations. If DO says backups, logs or support access reach the US, the notice must say so ("some backup copies and support access may be in the United States"), or we switch to C. Do not publish "your data never leaves Canada": support access, Cloudflare and Sentry make that false. Counsel item.

## 6. Backup retention vs erasure (ER-30)

### 6.1 Copies and proposed maximum age
| Copy | Today's plan | Proposed | Source |
|---|---|---|---|
| DO managed-PG daily backups | Daily | ≤ 35 days. DO's retention is **not stated** on the features page; ask (Q1 item 3) [verify] | DO PG features page |
| DO PITR WAL | 7 days | 7 days | same |
| DO internal backups after cluster or account deletion | Unknown | Ask; DPA §7.6 says 30 days for active data, no figure for backups | DO DPA §7.6 |
| L3 `age` dumps (S3 ca-central-1) | hourly 72 h / daily 35 d / **monthly 12 months** | hourly 72 h / daily 35 d / **no monthly tier** | backup-restore-test-plan L3 |
| L4 proof-PDF copy | kept "as long as the evidence must be kept" | see §6.4 | L4 |
| L5 cold copy (Farjad's encrypted disk) | monthly, retention unstated | keep only the latest copy; destroy the previous one when the new one is written (max age about 35 days) | L5 |
| Sentry events | — | 30 days (Developer) | Sentry retention page |

**Result:** the longest life of erased data in any backup is **35 days** after the erasure date, or 36 days counting the lifecycle sweep. Dropping the 12-month monthly tier costs us restore points older than 35 days. For a pilot where L5 and the immutable `recommendation` history exist, that is an acceptable loss (my judgement; `ciso` and `devops-engineer` to confirm).

### 6.2 Object Lock compliance mode vs erasure
- AWS: in compliance mode no user, root included, can delete or overwrite a locked version or shorten its retention. The only early delete is deleting the AWS account. Governance mode can be bypassed with `s3:BypassGovernanceRetention`.
- So an erasure request **cannot** reach locked dumps before they expire. To reconcile:
  1. Bucket default retention **COMPLIANCE, 35 days**. Bucket policy caps retention with `s3:object-lock-remaining-retention-days ≤ 35` so nobody can lock longer by mistake. Lifecycle rule expires noncurrent versions after 36 days. **No legal holds** unless counsel asks for one (a hold has no end date).
  2. Erasure (ER-24) is logged outside the DB. Any restore from L3 or L5 replays the erasure log before serving (ER-31, test AT-14). This keeps erased data "beyond use" while it waits to expire.
  3. The erasure reply (AT-10) states the 35-day window.
- Why not governance mode, which would allow targeted deletion? Whoever can bypass the lock can also destroy the backups, which defeats D1 (protection against account compromise). And a `pg_dump` file can't be partially deleted anyway. Keep compliance mode with a short period.

### 6.3 Notice and reply wording
- Notice §8 row: "Backups: encrypted backup copies are kept for up to 35 days and then deleted automatically."
- Notice §10: "When we delete your information, it is removed from our live systems right away and from all backup copies within 35 days. Until then, backups are encrypted, locked against change, and used only to recover from a failure. If we ever restore one, we re-apply your deletion before using it."
- ER-30 text and privacy-posture §1 ("≤12 months monthly") must change to 35 days. The owners of those files make the edit; I did not edit them.

### 6.4 Proof PDFs (L4) — open conflict
Proof PDFs are write-once evidence and probably show farmer, farm and field names. A 35-day compliance-locked copy is fine. A copy locked for "as long as the evidence must be kept" would put names in WORM storage for years, beyond the reach of erasure. Proposal: the L4 copy uses the same 35-day compliance lock, and evidence retention for the full period (season + 2 years) lives in the primary Spaces bucket, under app-controlled erasure or de-identification. Alternatively, generate the PDF so identity sits in a separate cover page. Product and `cp-platform` decide; counsel confirms the "legal claims" exception (privacy-notice counsel item 9).

## Needs licensed counsel
1. DO DPA and ToS (liability cap, governing law, transfer basis, missing residency clause) and the AWS DPA/Customer Agreement, before Farjad accepts either.
2. Whether 4.1.3 "comparable level of protection" is met by a DPA with no residency commitment and US sub-processors for backups and support. Whether DO's written answers need to be a signed addendum rather than an email.
3. Breach: the RROSH assessment template, the OPC report and notification letters, and whether "without undue delay" from processors is acceptable.
4. Sentry as an out-of-Canada processor: notice wording, and whether scrubbed error data is still personal information.
5. CLOUD Act wording in the notice (§5.3), whether "stored in Canada" is misleading given support access, Cloudflare and Sentry, and whether we may promise to tell farmers about government demands.
6. Backup window: is 35 days reasonable under PIPEDA principle 4.5.3 (destroy when no longer needed) and GDPR Art. 17 for EU website data? Does compliance-mode locking plus the restore replay meet "beyond use"?
7. Proof-PDF retention vs erasure (§6.4) and the "legal claims" exception.
8. Any partner, lender or grant clause on residency or ownership (per contract, when received).

## Sources (accessed 2026-11-16)
- DigitalOcean Data Processing Agreement, "Last Updated on October 14, 2026": https://www.digitalocean.com/legal/data-processing-agreement (fetched; §§1.1, 4.1–4.2, 7.4–7.7, Sch. 2–3)
- DigitalOcean Subprocessors, "Last updated June 10, 2026": https://www.digitalocean.com/trust/subprocessors (fetched)
- DigitalOcean Managed PostgreSQL features (daily backups, 7-day PITR, LUKS at rest): https://docs.digitalocean.com/products/databases/postgresql/details/features/ (fetched)
- DO backup location: tutorial https://www.digitalocean.com/community/tutorials/how-to-build-multi-region-disaster-recovery-strategy and community thread https://digitalocean.com/community/questions/backups-and-point-in-time-restore-pitr (search results only) [verify]
- AWS Data Processing Addendum: https://d1.awsstatic.com/legal/aws-dpa/aws-dpa.pdf (fetched; §§9, 12.1, 14; PDF metadata 2023-07-27) [verify current version]
- Amazon S3 Object Lock: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html (fetched)
- Sentry data storage location: https://docs.sentry.io/organization/data-storage-location/ (fetched)
- Sentry Python sensitive data: https://docs.sentry.io/platforms/python/data-management/sensitive-data/ (fetched)
- Sentry server-side scrubbing: https://docs.sentry.io/security-legal-pii/scrubbing/server-side-scrubbing/ ; advanced: https://docs.sentry.io/security-legal-pii/scrubbing/advanced-datascrubbing/ (search summaries) [verify]
- Sentry data retention periods: https://docs.sentry.io/security-legal-pii/security/data-retention-periods/ (fetched)
- Sentry DPA: https://sentry.io/legal/dpa/ (fetched; §§3.2, 4.2, 7.2; date not shown)
- PIPEDA s.10.1, s.10.3, Sch. 1 4.1.3 and 4.5.3: https://laws-lois.justice.gc.ca/eng/acts/P-8.6/FullText.html [verify; not reachable this session, relied on privacy-posture.md §2.1 and data-residency-input.md L1/L5]
- Breach of Security Safeguards Regulations SOR/2018-64: https://canadagazette.gc.ca/rp-pr/p2/2018/2018-04-18/html/sor-dors64-eng.html (per privacy-posture.md, fetched there)
- US CLOUD Act 18 U.S.C. §2713, DOJ white paper: https://www.justice.gov/criminal/media/999601/dl [verify; via data-residency-input S9]
- Repo: ADR 0009; data-residency-input.md; erasure-requirements.md (ER-24, ER-30, ER-31, AT-10, AT-14); privacy-notice.md v0.4; privacy-posture.md; backup-restore-test-plan.md (L1–L5)


## CISO integration note (2026-11-16)
- Retention: the Q6 position (35 days max, no monthly tier) is adopted; `backup-restore-test-plan.md` L3 is updated to match. Proof-PDF backup copies are locked for 35 days too, and long-term evidence stays in the primary bucket (counsel to confirm).
- The DigitalOcean sub-processor finding (AWS USA for backups) comes from the specialist. The CISO could not re-load the page (404 at /legal/sub-processors). It is the first thing to confirm in DO's written answers (Q1/Q3). If confirmed, option D does not meet "stored in Canada" for backups unless DO contractually pins them to Canada. In that case, choose option C with a Canadian backup location and the `gcp.resourceLocations` org policy.
- Timing: deciding the host on Jan 4 leaves about 2 weeks to build, run drills and cut over before the first real farm data (Jan 18). The CISO recommends deciding by Dec 11, as soon as DO answers.
