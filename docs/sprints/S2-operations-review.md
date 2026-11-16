# S2 — Operations review + retro (coo)

Sprint: S2, Nov 30 – Dec 11, 2026 (work started early, 2026-11-16). Owner: `coo`. Branch: `myca/ops-s2-f4aad3` (not merged).
Status: drafts only. Nothing sent, signed or filed. Not reviewed by a lawyer. Not approved by Farjad Iranmehr yet.

## What is now true (evidence)
| Goal | Output | Specialist | COO check |
|---|---|---|---|
| S2-1 Pilot SOP | `docs/operations/pilot-sop.md` | operations-manager | Gates G1–G7 match CLAUDE.md; all time targets labelled PROPOSED |
| S2-2 Intake checklist | `docs/operations/intake-checklist.md` | customer-onboarding-specialist | No invented constants; engine-unused items marked `TODO(agronomist)` |
| S2-3 Privacy / terms / consent | `docs/operations/legal/` (privacy-notice, pilot-terms, consent-wording, compliance-review) | legal-compliance-specialist | No third-party acceptance claim; lawyer list present; website copy in privacy-notice Part B |
| S2-4 Support FAQ + macros | `docs/operations/support-faq.md`, `support-macros.md` | customer-support-specialist | No rates/thresholds/prices; bank question never answered "yes" |
| S3 Workload model | `docs/operations/agronomist-workload-model.md` | operations-manager | Minutes are ops-time ASSUMPTIONS, to be replaced by measured `minutes_spent` from Dec 18 cases |
| S3 Onboarding messages | `docs/operations/onboarding-messages.md` | customer-onboarding-specialist | Transactional only; no numbers; placeholders for entity/contact |
| S3 Grants radar | `docs/operations/grants-radar.md` | grants-specialist | Cited; IRAP rows unverified (site blocked); entity question blocks most verdicts |

## Key findings
1. **Deletion requests cannot be honoured today.** Immutable `recommendation`/`review`/`proof_document` block deletes of parent rows. Proposed: overwrite identifiers in editable tables, delete PDF objects, keep `inputs_snapshot`, and no names in `reason`. Needs `cp-database` + `ciso` (compliance-review §1, P14).
2. **US hosting not disclosed.** Railway processes in the US; current website privacy copy does not say so. New copy discloses it. Railway DPA must be signed by Farjad Iranmehr.
3. **Pilot scope recommendation: Ontario (or Canada) only.** It avoids most GDPR exposure and the Quebec OAQ question; the website form accepts any country today.
4. **Ontario licensing is unknown** for crop-only fertilizer advice outside NMA plans → lawyer question; pilot terms state our plan is not an NMS/NMP/NASM plan.
5. **Capacity:** with likely assumptions, one agronomist holds ~5 farms × ≤5 fields or 10 farms × ~2 fields at 12 h/week; 10 × 6 does not fit. No backup reviewer exists.
6. **Grants:** start SR&ED records now; Mitacs (Guelph) and an IRAP advisor call are the next two. CDAP, Ontario Together Fund and OCI C2C are closed or not eligible.
7. **Engine gaps seen from intake:** wheat only; previous crops outside the pack list (fallow, forage legumes, barley, potato, other) block a plan; soil units other than mg/kg / ppm are rejected.

## Decisions needed from Farjad Iranmehr
1. Legal entity, contact email, mailing address, privacy officer.
2. Pilot eligibility: Ontario / Canada / worldwide.
3. Retention periods (proposed: 12 months unaccepted requests; season + 2 years pilot records; 3 years consent records).
4. Hire an Ontario lawyer for the list in `legal/compliance-review.md` (paid; needs his go). E&O insurance quote?
5. Backup reviewer when he is unavailable (today: deliveries stop).
6. Where pilot-farm status lives: app column vs ops sheet.
7. Agronomy items from intake → `docs/agronomist-todo.md` (soil-test age, previous-crop list, non-mg/kg units, estimate source allowed?).

## Cross-group hand-offs (via CPO)
- `cp-website`: privacy-page copy (privacy-notice Part B) + consent boxes A/B (consent-wording) — after placeholders filled and Farjad Iranmehr approves.
- `cp-database` / `ciso`: erasure design; `consent_event` table; purge job for `pilot_request.deleted_at`.
- `head-of-data`: ops-sheet fields + time-in-stage definitions (workload model §4, onboarding-messages); one or two review rows per edit?
- `cro`: message 3 ("not selected") keeps contact only with marketing opt-in; form has no opt-in yet.

## Retro
- **Went well:** 7 deliverables in one pass by running specialists in parallel; each checked against CLAUDE.md gates before acceptance.
- **Slowed us:** official sites (priv.gc.ca, crtc.gc.ca, laws-lois, agriculture.canada.ca, nrc.canada.ca) refused fetches → some citations rest on search summaries, marked. Entity question unresolved → blocks legal text and grants verdicts. Specialist agent files point to other output sub-folders than the brief (flat `docs/operations/` used).
- **One change for S3:** get the entity/contact facts from Farjad Iranmehr before any further legal or grants work; otherwise every document keeps placeholders.

## Update 2026-11-16 (pm) — CPO decisions D4, D-7, launch; backend-plan scope §3
Applied to all ops docs: the reviewer for now is the AI agent `cp-agronomist` (`ai_reviewed` only); no real-farm plan reaches a farmer without a named **human** agronomist's approval; Farjad Iranmehr is founder/operator, not the reviewer. D-7: the AI gets de-identified data only (SOP gate G8). Launch = Ontario winter wheat; pilot open to Ontario farms only.

| ID | Output | Status |
|---|---|---|
| NB-OPS-01 / SC-07 | SOP (G0 no human → no delivery, G1 human approval, G8 de-identified AI input; REC-D4 ref), intake (winter wheat, Ontario county), legal v0.2, FAQ/macros (+ "Is an AI making my plan?") | Drafts ready for Farjad Iranmehr + lawyer (OQ-07) |
| PD-05 | `legal/proof-pdf-wording.md` — ai_reviewed "NOT FOR FARMER USE" banner; human reviewer line; banned phrases; disclaimer `[COUNSEL]` | For cto/cp-pdf + cp-agronomy-guard |
| OQ-07 | `legal/oq-07-decision-pack.md` — 8 documents, 12 decisions, 16 lawyer questions | Waiting on Farjad Iranmehr |
| NB-OPS-03 / OQ-04 | `legal/ontario-agronomist-credentials.md` — Ontario: title-protected only (P.Ag.), no practice licence found for crop fertilizer advice outside NMA plans (counsel to confirm); SK/MB require registration → no Prairie farms until the approver is registered there; minimum hire = CCA-ON or P.Ag.; E&O before first real plan | Done (S3 item, early) |
| NB-OPS-02 | Workload model split: AI pre-review (machine) vs human minutes (key metric); human hours/week = ASSUMPTION for hiring brief | Done |
| NB-SEC-04 | `legal/data-residency-input.md` — recommend Railway US for pilot with DPA (counsel-reviewed) + notice; Canadian Postgres if a partner requires it | Input to ciso; OQ-06 is Farjad Iranmehr's |
| NB-OPS-06 | `legal/erasure-requirements.md` — ER-01..37, AT-01..17, 10 current violations (V-01..10) | To cp-database (design S4) |
| NB-WEB-05 | Privacy-page copy v0.2 in shared notes `coo-website-privacy-copy.md` | Ships only after placeholders filled + approval |
| (CPO ask) | `docs/agronomy/ontario-winter-wheat-season-note.md` (ai_reviewed, sourced) + `docs/agronomist-todo.md` row #11 | For the human agronomist |

**Finding for the CPO (season shape, ai_reviewed, sourced to OMAFA):** for Ontario winter wheat, P/K for the 2027 crop is decided at fall seeding (2026), and OMAFA advises against fall N. A Feb–Apr 2027 pilot therefore fits the **spring N decision only**, and the real deadline per farm is before green-up. In 2026 the south of the province was at GS30 by Apr 23, so the crunch is likely **March to early April**, not spread to Apr 30. This rests on one season of crop reports and is marked UNVERIFIED as a general rule. It affects pilot recruitment timing (cro), the workload peak, and P/K scope for 2027.
