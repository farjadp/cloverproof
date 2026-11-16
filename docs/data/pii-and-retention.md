# PII classification, access, retention and deletion

Author: data-governance-specialist, for `head-of-data`; reviewers `ciso`, `legal-compliance-specialist` (via `coo`). Status: DRAFT. All retention periods are **PROPOSED** for Farjad Iranmehr to approve. Schema: `db/migrations/0001`–`0009`; columns in `docs/data/data-dictionary.md`.

**Principle.** Farmers own their farm data (fields, boundaries, soil tests, applications). CloverProof processes it to produce plans and proof documents. We keep it only as long as we need to serve the farmer and for the legal/audit reasons below. We never use it for another purpose, sell it, or share it without the farmer's agreement. No production personal data is copied into the repo or docs.

> Regulation notes in this file are **not legal advice — confirm with legal-compliance-specialist via coo**.

## 1. PII classes

| Class | Name | Definition | Examples here |
|---|---|---|---|
| P0 | Public | Safe to publish | schema_migrations, pack config, docs |
| P1 | Internal | Not personal on its own; business/technical data | ids, timestamps, enums, org name, engine/pack versions, kg/ha rates, confidence, status |
| P2 | Personal | Identifies a person or a small farm, or becomes identifying when joined to an identity | pilot_request name/email, farmer/farm/field names, app_user email/display_name, free-text notes, soil tests and plans (linked to a named farm), reviewer identity, proof PDFs |
| P3 | Sensitive | Location precision, credentials, or anything whose leak causes direct harm or enables takeover | field_geometry_version.geom, password_hash, totp_secret, session token hash |

Justification: four classes are enough for one small team. Split P2/P3 because P3 needs stricter access (no analytics export, encrypted backups, no logging) than ordinary personal data. Field boundaries are P3, not P2, because exact parcel shape identifies a farm and its owner even without a name, and is commercially sensitive. Soil values alone are P1 in isolation, but they sit under a named farm so the record is P2. Pilot sizes are small (5–10 farms), so re-identification from "anonymous" farm data is easy; treat anything tied to a farm as P2.

Rule: a row is classified by its highest column; a join is classified by its highest input.

## 2. Classification per table

| Table | Class | Personal / sensitive columns |
|---|---|---|
| pilot_request | P2 | full_name, email, notes, farm_size_text; consent_* are P1 evidence about a P2 person |
| organisation, membership, season | P1 | |
| app_user | P2, secrets P3 | email, display_name, external_subject; password_hash, totp_secret |
| user_session | P3 | token_sha256 |
| farmer | P2 | display_name, notes |
| farm | P2 | name, region |
| field | P2 | name |
| field_geometry_version | P3 | geom (area_ha is P2) |
| soil_test, soil_test_value | P2 | linked to a named field; lab is P1 |
| crop_plan | P2 | |
| recommendation | P2 | reason (free text), created_by; jsonb contains no names per engine model (to verify) |
| review | P2 | reviewer_id, reason |
| application_log | P2 | notes, rates/dates |
| proof_document row | P1 (hash, key) ; PDF object P2 | key holds org and recommendation ids only |
| recommendation_diff | P2 | approved_by, edit_reason, results |
| Proof PDF (bucket) | P2 | farmer/farm/field names |

## 3. Who may access

| Role / system | Access |
|---|---|
| Website server (own DB role) | INSERT pilot_request; no read of other tables. Public: nothing |
| `cp_app` (internal tool, org-scoped queries) | organisation-scoped read/write per grants; immutable tables SELECT+INSERT |
| agronomist, owner, staff (app_user) | own organisation's farm data; only `agronomist` approves; geometry/soil visible to org members |
| farmer (Phase 4) | own farmer record's data only (via `farmer.app_user_id`) |
| `cp_migrator`, DB superuser | operators only (Farjad Iranmehr, `cto`); no routine use; never in app config |
| Agents/analysts | never production P2/P3. Dev uses `db/seeds/dev.sql` fictional data. Calibration analysis uses a pseudonymised export (section 6) |
| P3 secrets | no one reads them; app only compares/encrypts; never logged or exported |

Proposed: PIPEDA-style accountability means a named person should be responsible; propose Farjad Iranmehr as privacy contact until a role is assigned.

## 4. Consent linkage

- `pilot_request.consent_text` stores the exact wording shown, `consent_at` the time. Consent is therefore provable per person and per wording. Keep both for as long as the row (or its anonymised stub, below) exists.
- Gaps: no consent *version id*, no separate purposes (pilot contact vs marketing), no withdrawal record, no link from pilot_request to a later `farmer` record. When a request becomes a farmer, the farmer's consent to process farm data should be a separate written agreement (outside this table) stating: farmer owns the data, CloverProof processes it to produce plans, retention, deletion rights.
- No IP address or user agent column exists; good, do not add.

## 5. Retention (PROPOSED)

| Data | Proposed retention | Trigger | Deletion method |
|---|---|---|---|
| pilot_request, status `new`/`contacted`, no reply | 12 months from created_at | age | hard delete |
| pilot_request, `declined` | 30 days after decision, then delete | status change | hard delete (keep nothing) |
| pilot_request, `accepted` | until farmer relationship ends; then follow farmer rule | | delete once converted to farmer record and onboarding done (60 days) |
| pilot_request with `deleted_at` set | PII scrubbed within 7 days of request; row purged within 30 days | deletion request | see 5.1 |
| consent evidence for contact/outreach | 3 years after last contact, as a minimal stub (id, consent_at, consent_text, no name/email) | | confirm period with legal |
| app_user (staff) | life of account + 12 months after `disabled_at` | | pseudonymise (section 5.3) |
| user_session | delete 30 days after expires_at/revoked_at | job | hard delete |
| membership, organisation, season | life of org | | cascade/none |
| farmer, farm, field, field_geometry_version, soil_test(+value), crop_plan, application_log | while active farmer relationship + 24 months after last activity, or on farmer request | request or age | hard delete per 5.2; geometry first |
| recommendation, review (immutable) | life of calibration programme (target: ≥ 7 years) in pseudonymised form | | cannot be deleted; make non-personal (5.3) |
| proof_document row | same as recommendation | | row stays; PDF object per 5.4 |
| proof PDF object | 7 years from approval (agronomic advice record; confirm against legal) | age or request | per 5.4 |
| backups | max 35 days; deletion propagates by expiry | | document in runbook; Railway volume backup setting to check |
| logs | no personal data in logs; 30 days | | |

Seven years is a deliberate guess based on common professional-record norms; **legal-compliance-specialist must confirm**.

### 5.1 Pilot request deletion flow (`deleted_at`)
Current schema: `deleted_at` is set on a request; "row purged by a later job". No job, no policy, no index exists yet. Proposed flow:
1. Person asks to delete (email to privacy contact, or website form later). Verify identity by replying to the email on file.
2. Website/ops sets `deleted_at = now()`. All website and outreach reads must filter `deleted_at is null`; no outreach to these rows.
3. Within 7 days a job (to be built by `cp-database`/`cp-website`) overwrites `full_name`, `email`, `notes`, `farm_size_text` with placeholders, or, because those columns are NOT NULL with checks (email regex), with a non-routable pseudonym such as `deleted-<id>@invalid.example`. Within 30 days it hard-deletes the row. Keep a minimal deletion log (id, date) without personal data.
4. If the person already became a farmer or app_user, the request also triggers section 5.2.
5. Also delete from any mail tool and the old pre-switch `Postgres` service/dumps (runbook step 5: keep until approved; the final `pg_dump` is a copy of personal data and needs a retention date, propose delete 30 days after).

### 5.2 Farmer erasure on request (mutable tables)
Order: delete `application_log`, then `crop_plan` rows whose recommendations have no calibration value to keep... but FKs from the immutable `recommendation` to `crop_plan` block deleting crop_plan, and `recommendation` blocks deleting `field`. So hard delete of the farm chain is **impossible today** once a recommendation exists for it. Proposal: in that case do not delete; anonymise in place (the mutable rows hold the identity): overwrite `farmer.display_name`, `farmer.notes`, `farm.name`, `farm.region`, `field.name` with pseudonyms (`Farmer ab12`), set `geom = NULL` (keep `area_ha`, or round), delete `soil_test` free text. Farms with no recommendations are hard-deleted.

### 5.3 Deletion against IMMUTABLE tables (recommendation, review, proof_document)
Fact: UPDATE/DELETE/TRUNCATE raise for every role; only a migration can drop the trigger. Good news: **these tables hold no direct identifiers**. Personal data is reachable only through the mutable chain (`crop_plan → field → farm → farmer`) and through `created_by` / `reviewer_id` → `app_user`, plus free-text `reason`, and the PDF. So:

Option A (recommended): **anonymisation by severing identity in the mutable tables** ("crypto-shredding by reference", no key needed). Pseudonymise `farmer`, `farm`, `field`, `app_user` rows as in 5.2 and 5.3-user. The immutable rows remain, linked only to pseudonymous ids. This preserves the calibration dataset (inputs_snapshot, results, deltas, confidence, minutes) with no personal data. Conditions: (i) check that `result`/`inputs_snapshot`/explanations never contain names or coordinates (golden test), (ii) the agronomist's free-text `reason` must be written without names (UI hint + lint), (iii) small-sample re-identification risk: with 5–10 farms, even pseudonymous plans may be identifiable by someone who knows the farm; legal-compliance-specialist to judge if this counts as anonymous or only pseudonymous. If only pseudonymous, the data remains personal data and the farmer can still ask for removal.

Option B: **Documented exception.** Keep immutable rows as records of professional advice and audit (legitimate interest / legal obligation / contract), tell the farmer in the agreement, and delete everything else. Needs legal sign-off.

Option C: a migration-controlled "erasure procedure" (a `SECURITY DEFINER` function that disables the trigger, nulls `reason`, logs the action). Not recommended: it breaks the "immutable" promise and audit story; use only for court-ordered cases, with Farjad Iranmehr approval.

Recommended: A first, B documented as fallback in the farmer agreement. In every case **the calibration dataset (engine vs agronomist, `recommendation_diff`) must survive deletion of personal data**: it is built from P1 columns plus jsonb that is non-personal if verified. Deleting the farmer must never delete recommendation rows.

app_user pseudonymisation: users are referenced by immutable rows (`created_by`, `reviewer_id` FK without cascade), so `app_user` can never be deleted once they authored anything. On leaving: set `disabled_at`, null `password_hash`/`totp_secret`, delete sessions, overwrite `email` with `deleted-<id>@invalid.example` and `display_name` with `Former user <short id>`. Loss: reviewer accountability becomes "a former agronomist"; keep a separate offline record of which person held which id if audit requires it (legal to confirm).

### 5.4 Proof PDFs
The row is immutable and the key must match `proof/{org}/{rec}/{sha256}.pdf`; the PDF contains personal data. Proposal: deleting the object is allowed (the DB row is just a pointer); the app then reports "document erased on request" when the bucket returns not found, and integrity check on download must treat a recorded erasure as expected, not tampering. This needs somewhere to record erasure (gap G5). Alternative: encrypt each PDF with a per-farmer key and destroy the key (crypto-shredding); the hash stays valid for the plaintext. Heavier; defer unless the farmer base grows.

## 6. Data for calibration / analysis
Use `recommendation_diff` through a pseudonymous export: drop `final_created_by`, `approved_by`, `edit_reason` (free text), and replace `*_result` with the numeric fields needed. Join keys are uuids, no farm names. P2/P3 stays in the database. No production data in notebooks or the repo.

## 7. Regulation notes (not legal advice — confirm with legal-compliance-specialist via coo)
- **PIPEDA (Canada; company based in Ontario).** Accountability, identified purposes, consent, limited collection and retention, safeguards, access and correction on request. Maps to: consent_text/consent_at, retention table, access rules, a privacy contact, and an export/correction process (not built). Breach reporting to the regulator/individuals where real risk of significant harm; ciso to define an incident process. Provincial laws may also apply per farm location.
- **GDPR (EU/UK locales of the website, EU farms later).** Likely applies to people in the EU who submit the form, even if we are in Canada (targeting). Needs a lawful basis (consent for the pilot form, contract for service), a privacy notice, rights (access, rectification, erasure, restriction, portability, objection), possible EU representative, international transfer basis (Railway region, check where the bucket and DB run), and a processor agreement with Railway. Erasure is limited where data is needed for legal claims, which supports Option B as fallback. Field geometry and farmer data are personal when linked to an individual (sole traders).
- **CASL (Canada, electronic outreach).** Commercial emails need consent (express or implied, strictly limited), sender identification and a working unsubscribe, and proof of consent (our consent record). The pilot form consent wording must explicitly cover being contacted about the pilot; a newsletter needs separate express consent. Keep consent evidence beyond deletion of the contact if legal advises.
- Also check: farm-data terms with farmers (ownership, use for calibration of our engine — explicit agreement is needed to use their anonymised data to improve the engine), and country-pack countries' local rules.

## 8. Schema gaps / proposals (migrations are not edited; for `cp-database` via `head-of-data`)
- G1. `pilot_request`: no job and no index on `deleted_at`; add partial index `where deleted_at is null` and the scrub/purge job; add a view or convention so website reads exclude deleted rows. NOT NULL + email regex block clean erasure; consider relaxing or use the `.invalid` pseudonym.
- G2. `pilot_request`: no consent version/purpose/withdrawal columns; no link to `farmer`. Add `consent_version`, `consent_purposes`, `withdrawn_at`, and a nullable `farmer_id`/`converted_at`. `consent_at` has no `<= created_at` check.
- G3. No `farmer` contact or consent fields; when added (email/phone), classify P2 and add an agreement reference (`agreement_version`, `agreement_signed_at`, `deletion_requested_at`).
- G4. No `deletion_requested_at`/`anonymised_at` on `farmer`, `farm`, `field`, `app_user`; needed to track 5.2/5.3. Add `anonymised_at` and make anonymisation an auditable function.
- G5. No place to record proof PDF erasure (`proof_document` immutable): add an insert-only `proof_document_erasure (proof_document_id, erased_at, reason)` table.
- G6. `recommendation.reason`, `review.reason`, `notes` fields are free text inside immutable data: either add a UI warning or a check forbidding the farmer's name (hard in SQL); address in the app.
- G7. `inputs_snapshot`/`result` are unvalidated jsonb: add a golden test that the keys contain no name/coordinate fields.
- G8. `soil_test` and `crop_plan` are mutable after a recommendation used them; `inputs_snapshot` preserves the truth, but consider `locked_at` or an edit audit table. Not a privacy problem, a data-integrity one.
- G9. `soil_test_value.extraction_method` is NOT NULL for N too; enum has no "not applicable". Low priority; proposal: allow `other` + detail "n/a" convention or add `not_applicable`.
- G10. `user_session` has no scheduled cleanup; `totp_secret` has no DB-level encryption check.
- G11. `field_geometry_version.area_ha` is not tied to `geom` area (`ST_Area(geom::geography)/10000`) when `area_source='geometry'`.
- G12. `proof_document.storage_key`/`sha256` use org ids in the key: fine (no names). Keep it that way.
- G13. Postgres roles: confirm `pilot_request` grants for the website role; `cp_app` has none on it (good, keep separation).

## 9. Data-quality checks to automate later (hand to `cp-database` as SQL/tests)
Each returns rows when violated.
1. Soil test sample_date in the future, or older than the pack's maximum age (value from the agronomist: `TODO(agronomist)`).
2. `source='lab'` with `lab is null`; `source='estimate'` with `lab is not null`.
3. Soil test with no values; value outside plausibility range per nutrient/method (ranges owned by agronomist, `PLACEHOLDER` until set).
4. P or K value stored with form `N`/`NO3-N` mismatch; unit `ppm` rows (normalise report).
5. Depth range outside 0–100 cm without `extraction_method_detail`; overlapping depths for the same field and date.
6. `crop_plan.soil_test_id` whose soil_test belongs to a different field.
7. Recommendation with `soil_test` absent in `inputs_snapshot` and `confidence = 'high'`; P/K recommended without a test (hard rules 3).
8. `result` P/K rate present while form missing (P vs P2O5, K vs K2O not explicit).
9. Review with `minutes_spent = 0` or > 480; approvals without a `proof_document` after N days (and vice-versa: impossible by trigger).
10. Edited recommendation whose `reason` is under 10 characters; edit chain depth > 3.
11. `application_log.actual_date` in the future; actual rate > 2 × planned (flag); `recommendation_id` that is not approved; `form` inconsistent with the recommendation.
12. `field_geometry_version.area_ha` differs from `ST_Area` by > 5% when `geom` set.
13. pilot_request with `deleted_at` older than 7 days still holding a real email; any `status='declined'` older than 30 days; any row older than 12 months in `new`/`contacted`.
14. user_session expired for > 30 days; app_user disabled > 12 months with real email.
15. Proof PDF in the bucket whose key has no row (orphan), and rows whose object hash does not match (excluding recorded erasures).
16. Enum drift test: engine StrEnum values equal DB enum labels (exists per ADR 0002); extend to `confidence`.
17. Identity check: no recommendation jsonb key named like name/email/phone/lat/lon/coordinates.
