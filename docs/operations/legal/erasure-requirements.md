# Erasure, retention and access-request requirements for `cp-database` (NB-OPS-06)

> **This is not legal advice; a licensed Ontario lawyer should review before use.**
> Prepared by `legal-compliance-specialist` (not a lawyer) for the CloverProof COO → `cto/cp-database` + CISO, 2026-11-16.
> Requirements only — no schema code. Design due S4, build S13 (`backend-traceability.md` NB-OPS-06, RK-X3). Satisfies SC-07 ("export/delete ≤ 30 days"), compliance-review.md P6, P10, P14, C6, G8.
> Schema facts are from `origin/main` `db/migrations/0001–0009` and ADR 0002. Nothing was committed, sent or signed.

## 0. Principles (why the design looks like this)
1. **Erase identity, keep the agronomy.** Immutable rows (`recommendation`, `review`, `proof_document`) never hold identifiers; identifiers live only in mutable rows, which can be overwritten. The engine-vs-agronomist diff survives an erasure as pseudonymous data.
2. **Pseudonymous is not anonymous.** After erasure, a plan row still links (via ids) to field area, soil values, region and dates. Whether that remaining data is still personal information is a **counsel question** (N-1). Until answered, treat it as personal information: keep it only on a stated ground (§2) and only for consented calibration in de-identified form.
3. **Legal timings:** PIPEDA s. 8(3) gives 30 days to answer an **access** request (S1, *not fetched — verify*). PIPEDA has no fixed deletion clock; Principle 4.5.3 requires destroying, erasing or anonymising information no longer needed (S1). GDPR: erasure "without undue delay", answer within one month (Arts. 12(3), 17; S3). **Internal target for all requests: 30 calendar days** (SC-07).

Terms: **subject** = a farmer (or pilot applicant, or staff user) who asks. **Erase** = overwrite or delete so the value cannot be recovered from the live database. **Tombstone** = keep the row (for foreign keys/immutability), with identifiers removed and an erasure marker.

## 1. Erasable on request (within 30 days)

| ID | Requirement | Data (migration) | Testable by |
|---|---|---|---|
| ER-01 | On a verified request, all direct identifiers of the subject are erased from the live database within 30 days of verification. | see ER-02…ER-08 | AT-01 |
| ER-02 | `pilot_request`: the whole row is hard-deleted (no tombstone needed; nothing references it). | `0001_pilot_request.sql` | AT-02 |
| ER-03 | `farmer`: `display_name` overwritten with a fixed marker (e.g. `[erased]`), `notes` set to NULL, `app_user_id` handled per ER-05. Row stays (FKs). | `0004_farm_structure.sql` | AT-01 |
| ER-04 | `farm.name` → marker; `farm.region` → NULL or province-level only; `field.name` → marker; `field_geometry_version.geom` → NULL. Geometry rows whose `area_source = 'geometry'` must still be erasable (see V-04). `area_ha` may stay (agronomic, needed for calibration). | `0004` | AT-01, AT-04 |
| ER-05 | Farmer login (`app_user` with a `farmer` membership, Phase 4): `email` → unique non-routable placeholder, `display_name` → marker, `password_hash`, `totp_secret`, `external_subject` → NULL, `disabled_at` set; all `user_session` rows deleted; memberships deleted. Row stays (referenced by `created_by`). | `0003_identity.sql` | AT-05 |
| ER-06 | `application_log.notes` → NULL; `product` → NULL if it is free text that could hold identifiers (decision for `cp-database`; product names are not identifiers by themselves). | `0008_application_log_and_proof_document.sql` | AT-01 |
| ER-07 | Proof PDF objects in the bucket for the subject's recommendations are **permanently deleted** (all versions/replicas the bucket keeps). The `proof_document` row stays unchanged (it holds `sha256` + `storage_key` only, no identifiers), and an append-only erasure record marks it as "object deleted on <date>". | `0008`; ADR 0005 B1 | AT-06 |
| ER-08 | `organisation.name`, if the organisation *is* the subject (e.g. a sole-proprietor farm as its own organisation), → marker. | `0003` | AT-01 |
| ER-09 | Any copy sent to a third party (AI provider if D-7 = b, email provider, contractor agronomist) is deleted or its deletion requested in writing; the request date is logged. | `data-residency-input.md` §3 | AT-12 |
| ER-10 | Calibration consent withdrawal: from the withdrawal timestamp the subject's rows are excluded from every calibration export, **and** previously exported de-identified rows that can still be linked (by id) are removed from the calibration store. | `0009_recommendation_diff_view.sql` | AT-08 |
| ER-11 | Marketing withdrawal / unsubscribe stops messages within 10 business days (CASL s. 11(3); S5) — target: immediately. The consent record is kept (ER-20), not erased. | `consent-wording.md` §5 | AT-09 |

## 2. May be retained — and on what ground

| ID | What may stay | Ground | Limit |
|---|---|---|---|
| ER-12 | Immutable `recommendation`, `review`, `proof_document` rows, **after** ER-03…ER-08 have removed every identifier they link to | (a) Defence of legal claims about advice given — GDPR Art. 17(3)(e) (S3); Ontario Limitations Act, 2002 basic 2-year period (S6, *not fetched — counsel to confirm the period and start date*); (b) integrity of the proof record the farmer may rely on (hard rule 4) | Pilot season + 2 years (`privacy-notice.md` §8, *proposed*), then de-identify further or delete via a documented, counsel-approved migration. |
| ER-13 | Calibration dataset (engine vs final, per line) | **Only** (a) de-identified per `privacy-notice.md` §5 **and** (b) the subject's calibration consent is recorded and not withdrawn. Without consent → excluded (ER-10). | Until engine retired or consent withdrawn. |
| ER-14 | Staff identities on reviews (`review.reviewer_id`, `created_by` → `app_user`) of **staff/agronomists** | Accountability for professional sign-off; legal claims (ER-12). A staff erasure request is answered with this ground. | Same as ER-12. |
| ER-15 | Erasure log entries (ER-24) | Proof that we honoured the request (PIPEDA 4.1 accountability; GDPR Art. 5(2)) | 3 years (`privacy-notice.md` §8, *proposed*). |
| ER-16 | Consent records (ER-20) after withdrawal | Burden of proving consent is on the sender (CASL s. 13; S5) | 3 years after the consent ends (*proposed; counsel to confirm*). |
| ER-17 | Breach records | PIPEDA s. 10.3 + SOR/2018-64: 24 months (S2) | 24 months min. |
| ER-18 | Information subject to an **open access request or complaint** must not be erased until recourse is exhausted | PIPEDA s. 8(8) (S1, *section from memory — verify*) | Until the request/complaint is closed. |
| ER-19 | Every retained item above must be listed, with its ground, in the reply to the subject. | PIPEDA 4.9; GDPR Art. 12(4) | AT-10 |

## 3. Coexistence with immutability (rules for the schema)

| ID | Requirement |
|---|---|
| ER-20 | **`consent_event`** is append-only (no UPDATE/DELETE for `cp_app`; trigger like `forbid_change()`): one row per grant or withdrawal, with subject reference (pseudonymous id, not email), consent type (pilot contact / marketing / calibration / pilot terms), exact wording or wording version, notice version, locale, channel, timestamp, and source. Current state = latest event per (subject, type). It must not contain the email or name (so it survives erasure); the link to a person sits in the mutable table and is cut by erasure. Backfill from `pilot_request.consent_text/consent_at`. |
| ER-21 | **No identifiers in immutable rows.** `recommendation.inputs_snapshot` and `result` must contain only engine model fields (engine models use `extra="forbid"`, `engine/cloverproof_engine/models.py`; no name/contact/location fields today). Add a database-level or test-level guard so a new key with an identifier cannot be written (e.g. allow-list of top-level keys, checked in tests against the engine models). |
| ER-22 | **Free-text `reason` rule.** `recommendation.reason` and `review.reason` (and any future AI note field) must not contain personal names, contact details, farm/field names or addresses. Enforced by (a) UI hint in the concierge tool, (b) a server-side check that rejects text matching the subject's known identifiers (name, farm name, field names, email, phone) before insert, (c) a quarterly audit query. A reason that slipped through cannot be fixed in place → the documented exception path is a counsel-approved migration (ER-23). |
| ER-23 | **Break-glass correction path.** If an identifier is found in an immutable row, there is a written, reviewed procedure (migration that disables the trigger for one row in one transaction, logs before/after hashes, re-enables) — used only with CISO + Farjad approval and logged in ER-24. Never used for agronomic numbers. |
| ER-24 | **Erasure audit log** (append-only): request id, subject pseudonymous id, request received / identity verified / completed timestamps, scope (tables, bucket objects, third parties), operator, items retained + ground (ER-19), and a non-reversible fingerprint of the subject ids — **no erased values**. Mirrored outside the primary database (so a restore cannot lose it — ER-31). |
| ER-25 | Erasure is one transaction per subject for the database part; bucket deletion and third-party requests are tracked steps in ER-24 with status. Partial failure leaves the request open and visible, never silently "done". |
| ER-26 | The review gate and the `ai_reviewed` vs human-approval distinction must survive erasure: erasing a farmer never removes or alters review rows, decision, minutes_spent or approver. (`ai_reviewed` is planned in migrations 0011+ — `backend-distribution.md`; not on `origin/main` today.) |
| ER-27 | Erasure must not change any value in `recommendation_diff` except fields derived from erased identifiers (there are none today). |

## 4. Purge job, backups, logs

| ID | Requirement |
|---|---|
| ER-28 | **Purge job for `pilot_request`**: rows with `deleted_at` set are hard-deleted within 30 days of `deleted_at` (target: next daily run). Rows not accepted / no reply are hard-deleted 12 months after the decision (`privacy-notice.md` §8, *proposed*). Job is idempotent, logs counts (not content) to ER-24, and alerts on failure. |
| ER-29 | **Retention job for pilot records**: at retention end (ER-12) runs the same erasure as a request, for every subject whose period has ended. |
| ER-30 | **Backups**: erased data may persist only in backups and only until they expire. Railway volume backups we configure: daily kept 6 days, weekly 27 days, monthly 89 days (S7). **Maximum window = the longest schedule enabled** — state it in the privacy notice and the erasure reply. Railway's own platform backups ("backed up daily … across multiple sites and regions", DPA Exh. C) have **unknown** retention — ask Railway (`data-residency-input.md` D7). |
| ER-31 | **Restore rule**: after any restore, the erasure log (ER-24, from its outside mirror) is replayed before the app serves traffic or any export runs. A restore runbook step and a test cover it. |
| ER-32 | **Logs**: application logs must not contain request bodies, names, emails, notes or reason text. Railway log view retention is 7 days (Hobby) / 30 days (Pro) / up to 90 days (Enterprise), but "Upgrading plans will immediately restore logs that were previously outside of the retention period" (S8) — actual storage is longer and unknown; ask Railway. Because of that, the logging rule (no identifiers) is the control, not the retention. |
| ER-33 | Calibration exports (files outside the DB) are listed in an inventory with location and the subject ids they contain, so ER-10 can remove them. |

## 5. Access requests (export)

| ID | Requirement |
|---|---|
| ER-34 | Export for a verified subject within 30 days: one ZIP containing (a) a JSON file per table with every row linked to the subject (farmer → farm → field → geometry → soil_test/values → crop_plan → recommendation (all versions) → review → application_log → proof_document metadata), (b) the proof PDFs still held, (c) `consent_event` history, (d) a plain-language README (what each file is, where it is stored, who it was shared with, retention and ground), (e) a CSV of the engine-vs-final diff for the subject's plans. |
| ER-35 | Machine-readable (JSON/CSV, UTF-8, ISO 8601 dates, units as stored) — also meets GDPR Art. 20 portability for EU subjects (S3). |
| ER-36 | Staff names in the export: show role (`agronomist`, `AI review`) and, for the approving human agronomist, their name and credentials (the farmer is entitled to know who approved — `privacy-notice.md` §10); other staff ids pseudonymised. Internal `minutes_spent` included (it is about the subject's plan) unless counsel says otherwise. |
| ER-37 | Identity check before export or erasure: reply from the email on record, or a matching pilot-agreement contact; log the method in ER-24. No extra identity data collected. |

## 6. Acceptance tests (Given / When / Then)

- **AT-01 Farmer erasure.** Given a farmer with farm, two fields, a soil test, a crop plan, an engine recommendation, an agronomist edit with reason, an approval review, an application log with notes and a proof PDF — When the erasure procedure runs for that farmer — Then `farmer.display_name`, `farm.name`, `field.name` equal the marker; `farmer.notes`, `farm.region` (or reduced to province), `field_geometry_version.geom`, `application_log.notes` are NULL; a search of every text and jsonb column in the database for the original name, farm name, field names and email returns zero rows; the transaction committed without disabling any trigger.
- **AT-02 Pilot request.** Given a `pilot_request` row — When an erasure request for its email is processed — Then the row no longer exists and ER-24 has an entry without the email in clear.
- **AT-03 Immutability intact.** Given AT-01 has run — When counting `recommendation`, `review`, `proof_document` rows and hashing their contents — Then counts and hashes equal the values before erasure.
- **AT-04 Geometry-sourced area.** Given a `field_geometry_version` with `area_source = 'geometry'` and a polygon — When the farmer is erased — Then `geom` is NULL and the row still satisfies all constraints (fails today — V-04).
- **AT-05 Farmer login.** Given a farmer `app_user` with sessions and a membership — When erased — Then sessions and memberships are gone, email/name are placeholders, login is impossible, and rows referencing the user via `created_by` still resolve.
- **AT-06 Proof PDF.** Given an approved recommendation with a proof PDF object — When the farmer is erased — Then a GET on the storage key returns not-found (including any version listing the bucket supports), the `proof_document` row is unchanged, and an erasure record shows the object deletion date.
- **AT-07 Calibration survives.** Given AT-01 and the farmer had calibration consent — When querying `recommendation_diff` — Then engine N rate, final N rate, delta, confidence, edit reason and approval minutes are identical to before erasure.
- **AT-08 Calibration withdrawal.** Given a farmer with calibration consent and rows in an exported calibration file — When a `consent_event` withdrawal is recorded — Then the next calibration export excludes the farmer's plans and the inventoried earlier export no longer contains them (ER-33).
- **AT-09 Unsubscribe.** Given a subscribed contact — When they click unsubscribe — Then a withdrawal `consent_event` is written within the request and no marketing send after that timestamp includes them.
- **AT-10 Reply lists retention.** Given a completed erasure — When the reply is generated — Then it lists each retained category with its ground (ER-12…ER-18) and the backup window (ER-30).
- **AT-11 Reason guard.** Given a farmer named "X" with farm "Y" — When the agronomist submits an edit whose reason contains "X" or "Y" — Then the insert is rejected with a message and nothing is written.
- **AT-12 Third parties.** Given a farmer whose data went to a third party — When erased — Then ER-24 shows a dated deletion request to each listed third party and the request stays open until each is confirmed or 30 days pass with escalation.
- **AT-13 Purge job.** Given `pilot_request` rows with `deleted_at` 31 days ago and 1 day ago — When the purge job runs — Then neither row remains (target next run), and the job log holds counts only.
- **AT-14 Restore replay.** Given an erasure completed after the latest backup — When that backup is restored in staging — Then before the app starts the replay re-applies the erasure and AT-01's search returns zero rows.
- **AT-15 Export.** Given a farmer as in AT-01 — When an access request is fulfilled — Then the ZIP contains every row reachable from the farmer (row counts match DB queries), all proof PDFs held, consent history and a README; delivered within 30 days of verification.
- **AT-16 Snapshot guard.** Given an attempt to insert a recommendation whose `inputs_snapshot` has a key not in the engine model (e.g. `farmer_name`) — When inserted — Then it is rejected.
- **AT-17 Open request hold.** Given an open access request or OPC complaint for a subject — When the retention job runs — Then that subject's data is skipped and the skip is logged.

## 7. Where the current schema violates these requirements (`origin/main`)

| V | Table / object | Migration | Violation | Req |
|---|---|---|---|---|
| V-01 | `recommendation`, `review`, `proof_document` — DELETE/UPDATE/TRUNCATE raise for every role | `0002_roles_and_extensions.sql` (`forbid_change()`), `0006`, `0007`, `0008` | Correct by design; becomes a violation only if any identifier reaches these rows. No guard prevents it today (`reason` is free text; `inputs_snapshot`/`result` are unconstrained jsonb at DB level). | ER-21, ER-22 |
| V-02 | `pilot_request.deleted_at` — "row purged by a later job"; no job exists | `0001_pilot_request.sql` | No purge; also only one consent (`consent_text`, `consent_at`) — no history, no marketing/calibration consent | ER-28, ER-20 |
| V-03 | `farmer`, `farm`, `field` — `name`/`display_name` NOT NULL; children reference parents with no `ON DELETE` | `0004_farm_structure.sql` | Rows can't be deleted while referenced (expected); no erasure marker/column, no `erased_at` | ER-03, ER-04 |
| V-04 | `field_geometry_version` — `check (area_source <> 'geometry' or geom is not null)` | `0004` | Geometry cannot be erased for geometry-sourced areas without also changing `area_source`, which misstates provenance. Needs an erasure-aware provenance value or rule. | ER-04, AT-04 |
| V-05 | `app_user` — `email`, `display_name` NOT NULL, unique lower(email); referenced by `created_by`/`reviewer_id` everywhere without `ON DELETE` | `0003_identity.sql`, `0004`–`0008` | Users can't be deleted; no placeholder convention; no erased marker | ER-05, ER-14 |
| V-06 | `organisation.name` NOT NULL | `0003` | No erasure path if the organisation is a sole proprietor | ER-08 |
| V-07 | `proof_document` immutable; no place to record that the object was deleted | `0008` | Needs a separate append-only erasure record | ER-07 |
| V-08 | `recommendation_diff` exposes `edit_reason`, `approved_by`, `final_created_by` and full jsonb | `0009_recommendation_diff_view.sql` | No consent filter; calibration export would include reasons and staff ids un-reviewed | ER-10, ER-13 |
| V-09 | No `consent_event`, no erasure log, no export function | — | Missing | ER-20, ER-24, ER-34 |
| V-10 | `ai_reviewed` flag not in schema | — (planned 0011+) | Can't prove AI reviews are excluded from calibration/approval after erasure | ER-26 |

Mutable tables that already allow erasure by UPDATE (`cp_app` has UPDATE): `farmer`, `farm`, `field`, `field_geometry_version` (except V-04), `soil_test` (`lab` is not an identifier), `application_log`, `app_user`, `pilot_request`.

## Sources (checked 2026-11-16)
- S1 PIPEDA, S.C. 2000, c. 5 (ss. 8(3), 8(8), 10.3; Sch. 1 4.1, 4.5.3, 4.9) — https://laws-lois.justice.gc.ca/eng/acts/P-8.6/ *(connection refused; section numbers from compliance-review.md and memory — verify)*
- S2 SOR/2018-64 — https://canadagazette.gc.ca/rp-pr/p2/2018/2018-04-18/html/sor-dors64-eng.html *(search: 24-month record keeping)*
- S3 GDPR (EU) 2016/679, Arts. 5(2), 12, 17, 20 — https://eur-lex.europa.eu/eli/reg/2016/679/oj *(fetched in compliance-review; Arts. 17 and 20 not re-read today)*
- S5 CASL, S.C. 2010, c. 23, ss. 11, 13 — https://laws-lois.justice.gc.ca/eng/acts/E-1.6/ *(not fetched; CRTC FAQ search-confirmed 10 business days)*
- S6 Limitations Act, 2002, S.O. 2002, c. 24, Sch. B — https://www.ontario.ca/laws/statute/02l24 *(not fetched; e-Laws needs JavaScript)*
- S7 Railway backups — https://docs.railway.com/reference/backups *(fetched)*
- S8 Railway logs — https://docs.railway.com/guides/logs *(fetched)*
- S9 Railway DPA, Exh. C and §12 — https://railway.com/legal/dpa *(fetched)*
- Repo: `git show origin/main:db/migrations/0001…0009`; `docs/adr/0002-data-model.md`; `docs/operations/legal/compliance-review.md` §1 P14/G2; `privacy-notice.md` §5, §8, §10.

## Needs licensed counsel
- N-1 Is a plan row that remains linked (by id) to area, soil values, province and season still personal information after identifiers are overwritten?
- N-2 Is overwriting identifiers + deleting PDFs + keeping immutable rows enough to honour a PIPEDA/GDPR deletion request?
- N-3 Retention for legal-claims defence (ER-12): period and start date under the Limitations Act, 2002; whether it survives a deletion request.
- N-4 Staff erasure requests (ER-14) — may we refuse on accountability grounds?
- N-5 Consent-record retention after withdrawal (ER-16) and the CASL limitation period.
- N-6 Whether `minutes_spent` and reviewer identity must be included in an access-request export (ER-36).
- N-7 Backup window disclosure wording (ER-30) and whether 89 days is acceptable.
