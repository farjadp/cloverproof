# S2 — CPO product team: sprint review + retro

Date: 2026-11-16 (S2 exit due Dec 11). Owner: CPO product team (`agile-manager`, `product-designer`, `cp-design`, `cp-product-manager`), integrated for `product-manager`.
Scope: distribution §8 — REC-D3, REC-R5, REC-CL, DR-01..03, AR-34, NB-PRD-01, NB-PRD-02, RK-02.
Branch: `myca/product-backlog-s2-157734`, stacked on `backend-traceability` (farjadp/cloverproof#9).

## Review — what is now true (evidence)

| Exit item | Matrix IDs | Evidence | Status |
|---|---|---|---|
| S2–S3 backlog: 73 stories (4 S1 carry-over, 53 S2, 16 S3), Given/When/Then, data-model + permission/RLS impact, matrix IDs, sprint, blocked-by | AR-34, NB-PRD-01, DR-01, DR-02, DR-03 | `docs/backlog.md` | done (draft for CPO review) |
| Coverage: every ID in distribution 1A–1H + Standing mapped to ≥ 1 story | — | Script check by CPO team: 159 unique IDs, 0 missing | done; distribution says 153 → cto to explain the +6 |
| Review queue (due-date sort, 8 filters) + side-by-side engine-vs-edit diff with reason, role × element table, states, HTMX, a11y, data per element | NB-PRD-02 (A1, RV-01..05, S02-3) | `docs/design/review-queue.md`, look: `docs/design/review-queue-mockup.html` | done (spec); Stitch frames not made — static HTML mockup instead |
| Every number in mockups is "—"; brand colours, Source Serif 4 + Source Sans 3, official logo `<img>` | — | Script check: only version labels / screen numbers contain digits | done |
| Approve on a real farm only for a human agronomist (D4); AI account cannot see real farms (D-7) | REC-D4 | Spec §1a P1–P2, §2; backlog S2-DB-10 | done |
| `webapp-v1.md` §2 scope note per R5 | REC-R5 | `docs/plans/webapp-v1.md` §2 | done |
| CLAUDE.md update draft (28 changes, full text, 6 questions) incl. CPO additions: D4 agronomist wording, D-7 rule 12, LGPL-by-name + NASA POWER licence | REC-CL | `docs/product/claude-md-draft.md` | done — **awaits Farjad Iranmehr** (needed by Dec 11) |
| REC-D3 (calendar) | REC-D3 | Backlog uses S1–S30 dates; roadmap header already superseded on `main` | done |
| RK-02 (agronomist time bottleneck) | RK-02 | Review queue optimised for minutes per plan (default filter, "Next in queue", timer start/finish); human-agronomist gap visible (N-NO-HUMAN notice) | partial — real fix is OQ-04 |

Integration fixes made by the CPO team (specialists' outputs disagreed):
1. Spec + mockup let the AI account open and edit real-farm plans → contradicts D-7. Fixed: AI sees sample plans only (RLS 404), never approves or rejects; mockup row and detail page changed; backlog S2-DB-10 gained RLS criteria.
2. Mockup showed P/K "Soil test recommended" only in v1 → an edit could drop hard rule 3. Ruled: it is a non-editable rule line carried into every version.
3. Licence story allowed no LGPL → aligned with CPO rule (LGPL by name only: psycopg, libvips/sharp; NASA POWER internal-only until S8).
4. Column-name drift (`farmer.record_kind` vs `farm.data_class`, `app_user.kind` vs `is_human`) → cp-database settles names in the gap analysis; behaviour binding.

## Decisions needed

**From the CPO (by Nov 27, with cto's RK-X decisions):**
- Q2 — S2 DoD asks for "1 full PDF", but PDFs come only from approved plans, and no human agronomist exists. Options: (a) a human approves a sample plan, (b) a watermarked "Sample — not reviewed by an agronomist" test PDF from an AI review on sample plans (needs coo PD-05 wording). Recommend (b) for S2 only.
- Q3 — owner/org_admin: 403 on queue/detail after ADR 0006 (recommended).
- `REVIEW_DUE_DAYS` default and business vs calendar days.
- Backlog: S3 is ~30 % of S2 by points, not 50 % — accept, or pull S2 overflow (S2-ENG-05, S2-APP-12/11/09, S2-DB-16) into S3.
- Where review due date lives (not on immutable `recommendation`) — gap analysis S2-DB-01.

**From Farjad Iranmehr:** approve the CLAUDE.md draft; Q1 is he the human agronomist (OQ-04); superadmin-approves-only-if-human; S9 farmer front-end stack (Next.js vs FastAPI pages); data residency; S4 worker cost.

## Retro

- **Slowed us:** the source docs live on three unmerged branches (`backend-traceability`, `website-v1` for `brand/`, `webapp-step5-app` for `webapp-ui.md` + templates), so specialists read via `git show` and the mockup's logo path only resolves after `website-v1` merges. A rule (D-7) arrived mid-sprint and invalidated part of two finished outputs.
- **Worked:** parallel specialists on disjoint files; CPO-team integration pass caught 4 cross-document conflicts before the PR.
- **Rework:** spec and mockup made opposite calls on AI reject and the P/K line — two designers in parallel without a shared decision list.
- **One change for S3:** before briefing parallel specialists on the same feature, write the binding rulings list first (like spec §1a) and give it to all of them; mockup follows the spec, not in parallel.
- **Flagged to cp-concierge-app:** `base.html` draws the clover as hand-made SVG; brand says never redraw → swap to the official logo after `website-v1` merges.
