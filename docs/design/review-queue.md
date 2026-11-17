# Review queue and review detail (internal tool, S2)

Matrix: NB-PRD-02, A1, RV-01..RV-05, S02-3, HV-06, HV-07 (also HV-11, U9, RK-X4, RK-X11, REC-D4).
Owner: `product-designer`. Builder: `cp-concierge-app`. Visual mockup: `docs/design/review-queue-mockup.html` (`cp-design`, written separately).
Stack: FastAPI + Jinja2 + HTMX, `app/cloverproof_app/static/app.css`, no build step. English only (CLAUDE.md: the internal tool stays English).
Base spec: `docs/design/webapp-ui.md` on `origin/webapp-step5-app` (tokens, layout, badges, notices, the explained-number macro). Everything here **extends** it. Where this file does not say otherwise, webapp-ui.md applies.

Every number in wireframes and copy examples is "—". Curly braces `{…}` are template values.

---

## 0. Job and flow

**JTBD:** "Each morning, show me the plans that need my decision, soonest due first, so I can check what changed against the engine, decide, record why, and move to the next one, with as few minutes per plan as possible."

```
Login ─► /review (queue, default filter "Awaiting decision", sorted by due date)
            │  filter / search / sort (URL keeps the state)
            ▼
         /plans/{plan_id}/review   (review detail: version chain + engine vs v{n} diff)
            ├─ Approve ──────────────► success notice ─► "Next in queue" ─► next detail
            ├─ Edit numbers ─► /plans/{plan_id}/edit ─► "Save as v{n+1}" ─► back to detail (diff now vs v{n+1})
            │                                         └► "Save as v{n+1} and approve" (human agronomist, RV-04)
            ├─ Reject (reason) ──────► rejected notice ─► "Next in queue"
            └─ AI account: "Record AI review" (notes) ─► plan stays In review, badge "AI-reviewed"
```
Exits: back to the queue (breadcrumb keeps filters), "Next in queue", or the plan page `/plans/{plan_id}` (full numbers view, unchanged from webapp-ui.md §3.5).

---

## 1. Decisions this spec rests on (read first)

| # | Decision | Why |
|---|---|---|
| S1 | One queue row per **crop plan**, showing its **latest version** (the leaf of the `parent_id` chain). Older versions appear only in the detail's version chain. | The decision is always on the latest version (existing `STALE_VERSION` rule). |
| S2 | "Awaiting decision" = latest version has no `approve`/`reject` review. An `ai_review` does **not** end the wait. | D4. |
| S3 | `ai_reviewed` is an **attribute** (a badge), never a status. Status values stay: In review, Approved, Rejected (Draft is not used in this tool: every engine run enters review). | D4: "never reads as approved". Keeps one status column. |
| S4 | The AI account never approves and never rejects, on real or sample plans. It may record an AI review (notes required) and may create an edited version. | D4 + rule 8. Reject is a professional decision too; an AI reject would also end the human's queue item. CPO to confirm (Q1). |
| S5 | Approve is not shown as a disabled button to non-approvers. The decision area is replaced by a notice explaining who can approve and why. | Disabled buttons cannot take focus and are not explained to screen readers; a notice carries the reason. Server-side checks stay the control. |
| S6 | Real farm is the **default** kind. Only rows explicitly marked sample are sample. | Fail safe: a missing flag must never relax D4. |
| S7 | Due date is a stored column, not computed in the template. | There is no due-date column today (§7, DB-1). |

### 1a. CPO product-team rulings (integration, 2026-11-16) — these override anything below

| # | Ruling | Effect on this spec |
|---|---|---|
| P1 | **D-7 data boundary (CPO, 2026-11-16):** `cp-agronomist` never receives real pilot farmers' personal or identifiable farm data — only published, synthetic or de-identified cases. | The AI account **cannot see real-farm plans at all**: queue rows, detail, edit and AI-review routes for `record_kind = 'real'` return 404 for `app_user.kind = 'ai'`, enforced by RLS (ADR 0008) and the route. In §2 the AI column reads "not visible (404)" for every real-farm row; notice N-AI-REAL is not needed. The AI works on sample plans only; its "Real farms" filter option is hidden. |
| P2 | Q1: the AI account never approves and never rejects, on any plan. | Adopted as S4 says. FI may revisit. |
| P3 | Without a soil test, the P/K "Soil test recommended" line is a **rule line**: not editable, carried into every version, shown on both sides of the diff (hard rule 3). | One-sided diff rows apply only to rate lines added or removed by an edit. |
| P4 | Q4, Q5, Q6, Q8: the recommendations in §7 are the S2 defaults (PLACEHOLDER acknowledgement checkbox; due date only; `APP_TIMEZONE=America/Toronto`; no claiming). | `REVIEW_DUE_DAYS` value is a product setting, not an agronomic constant; default to be set by the CPO. |
| P5 | Q2 (test PDF without a human approval) and Q3 (owner/org_admin 403) are **open** — escalated to the CPO. | cp-pdf must not render a PDF from an AI review until the CPO rules. |
| P7 | Column names in §7 (`farmer.record_kind`, `app_user.kind`) are proposals; the backlog uses `farm.data_class` and `app_user.is_human` (S2-DB-04, S2-DB-10). cp-database settles the names in the gap analysis (S2-DB-01); the behaviour is what is binding. | — |
| P6 | Where `docs/design/review-queue-mockup.html` and this spec differ, **this spec wins**. Known differences: the mockup's queue has a Minutes column (optional; keep if room) and a "Status" column separate from "Review" (allowed). | Build from this spec; use the mockup for look only. |

---

## 2. Roles: who sees what

Role sources today: `membership.role` (`owner`, `agronomist`, `staff`, `farmer`). Target (ADR 0008, RK-X11): `owner`→`org_admin`, `staff`/`superadmin` → platform roles. "Human agronomist" = `agronomist` membership in the org **and** `app_user.kind = 'human'` (DB-3). "AI agronomist" = the `cp-agronomist` account, `agronomist` membership, `app_user.kind = 'ai'`.

| Element | Human agronomist | AI agronomist (`cp-agronomist`) | staff | superadmin (not a human agronomist) | owner / org_admin | farmer |
|---|---|---|---|---|---|---|
| Header link "Review queue" | yes | yes | yes | yes | until PM-DR-oa: yes; target: no | no |
| `/review` queue | full | full | read | read | until PM-DR-oa: read; target 403 | 404 |
| Detail: diff, versions, timer | yes | yes | yes (no timer: §4.6) | yes (no timer) | until PM-DR-oa: yes (no timer); target 403 | 404 |
| Approve, **real farm** | **yes** | no → notice N-AI-REAL | no → notice N-VIEW | no → notice N-VIEW | no → notice N-VIEW | – |
| Approve, sample | yes ("Approve sample plan") | no → notice N-AI-SAMPLE | no → N-VIEW | no → N-VIEW | no → N-VIEW | – |
| Edit numbers (new version) | yes | yes (version labelled "AI edit") | no | no | no | – |
| Reject | yes | no | no | no | no | – |
| Record AI review | no | yes | no | no | no | – |
| Org notice N-NO-HUMAN | when shown, all roles see it | | | | | |

A superadmin who **also** holds a human `agronomist` membership in the org is a human agronomist for this screen. Platform roles alone never approve (RK-X11, PM-AP-sa).

Server enforcement is assumed (DB trigger on `review` + route check). The UI only mirrors it. If the UI renders a button the server would refuse, that is a bug in the UI; the server still refuses.

---

## 3. Screen A — Review queue `/review`

### 3.1 Purpose
List the plans in the current organisation that need a decision, soonest due first, overdue on top, with filters that let the reviewer cut the list to what they can do now.

### 3.2 Layout, wide (≥ 960px)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ [official logo]  | Ontario Pilot Org                 Review queue   Farjad · Agronomist ▾ │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ Review queue                                                       (h1, serif)        │
│ — awaiting decision · — overdue · — due today                     (ink-soft, sm)      │
│                                                                                       │
│ ┃ No human agronomist in this organisation yet                     (notice info, N-NO-HUMAN, only when true)
│ ┃ Real-farm plans stay In review until one is added. AI reviews are recorded but do not approve.
│                                                                                       │
│ Find farmer, farm or field [______________]   Status [Awaiting decision ▾]  Due [Any ▾]│
│ Crop [Any ▾]  Confidence [Any ▾]  Data [Real farms ▾]  AI review [Any ▾]  Sort [Due date, soonest first ▾] │
│ [Apply filters]  Clear filters                                     (Apply hidden when JS runs) │
│ ───────────────────────────────────────────────────────────────────────────────────── │
│ DUE            PLAN                          CROP · SEASON     VERSION   CONFIDENCE       REVIEW                         │
│ ───────────────────────────────────────────────────────────────────────────────────── │
│ Overdue        Hillside                      Winter wheat      v—        [MEDIUM CONF.]   [IN REVIEW] [AI-REVIEWED]        │
│ —              Dekker Farms · Home farm      —                 edited    [PLACEHOLDER]    Waiting for a human agronomist   │
│ Due today      Creek Road                    Winter wheat      v1        [LOW CONF.]      [IN REVIEW]                      │
│ —              Martin family · North farm    —                 engine    [PLACEHOLDER]                                     │
│ —              Back forty                    Winter wheat      v1        [MEDIUM CONF.]   [IN REVIEW] [SAMPLE]             │
│                Reference case · Sample farm  —                 engine                                                      │
│ No due date    Lower flats                   Winter wheat      v—        [HIGH CONF.]     [IN REVIEW]                      │
│                ...                                                                                                         │
│ ───────────────────────────────────────────────────────────────────────────────────── │
│ Showing all — plans.                                                                   │
└──────────────────────────────────────────────────────────────────────────────────────┘
```
- The page uses `--content` (60rem) max width like every other page. The table is the only wide element; at 60rem the six columns fit.
- Filters sit in one `<form class="filters">` above the table, two rows of inline label+control pairs, no box (sections are separated by rules, not panels).
- No row cards, no zebra striping (webapp-ui.md §4 Table).

### 3.3 Layout, narrow (< 720px)
```
Review queue
— awaiting decision · — overdue

▸ Filters (— active)            <details>, closed by default; open shows the same controls stacked, full width
Find farmer, farm or field [________]

───────────────────────────
Overdue · —
Hillside                         (link, 600)
Dekker Farms · Home farm
Winter wheat · —  ·  v— edited
[MEDIUM CONF.] [PLACEHOLDER]
[IN REVIEW] [AI-REVIEWED]
Waiting for a human agronomist
───────────────────────────
Due today · —
Creek Road
...
```
- Uses the existing `table.stack` pattern (rows become blocks with `data-label`). The Due line goes first, the Plan link second, so the order of reading stays "when, what".
- Search stays outside the `<details>` (most used control). Touch targets 44px (existing button rule).
- 720–959px: same as wide; the CROP · SEASON column wraps; filters wrap to three rows.

### 3.4 Columns (exact)

| Column (header text) | Content | Sort / notes |
|---|---|---|
| **Due** | Line 1: due label. Line 2: date `{YYYY-MM-DD}` (tabular). Labels: "Overdue" (error colour, 600), "Due today" (ink, 600), date only (ink) for later dates, "No due date" (ink-soft) when null. | Colour is never the only signal: the word "Overdue"/"Due today" is always written. |
| **Plan** | Line 1: field name as a link to the detail (`<a>`, the row's only link). Line 2 (ink-soft, sm): `{farmer} · {farm}`. | Link text = field name; `aria-describedby` points to the Due cell so screen readers hear "Hillside, Overdue". |
| **Crop · season** | Line 1: crop label. Line 2: season label. | |
| **Version** | Line 1: `v{n}`. Line 2 (ink-soft, sm): "engine", "edited" (human edit) or "AI edit". | |
| **Confidence** | Confidence badge of the latest version (existing macro). Under it, the Placeholder badge if the version uses any PLACEHOLDER constant or `pack_status = placeholder`. | |
| **Review** | Status badge (In review / Approved / Rejected). After it: "AI-reviewed" badge if an AI review exists on this version; "Sample" badge if the farmer is sample. Line 2 (ink-soft, sm), only for real-farm rows in review that have an AI review: "Waiting for a human agronomist". | |

No "minutes" column: minutes live on the detail. No checkbox column: there are no bulk actions (every approval is a deliberate, individual act).

### 3.5 Filters (exact labels and values)

All are native controls inside one GET form. Query parameters in brackets.

| Label | Control | Options (label → value) | Default |
|---|---|---|---|
| Find farmer, farm or field | `input type=search` [`q`] | free text, max 100 chars, matched case-insensitively on farmer, farm and field names | empty |
| Status | select [`status`] | Awaiting decision → `awaiting` · Approved → `approved` · Rejected → `rejected` · All → `all` | `awaiting` |
| Due | select [`due`] | Any → `any` · Overdue → `overdue` · Due today → `today` · Due this week → `week` · Later → `later` · No due date → `none` | `any` |
| Crop | select [`crop`] | Any → `any`, then one option per distinct `crop_plan.crop` in the org (label from the pack crop label) | `any` |
| Confidence | select [`confidence`] | Any · Low · Medium · High (`any`/`low`/`medium`/`high`) | `any` |
| Data | select [`kind`] | Real farms → `real` · Sample plans → `sample` · All → `all` | `real` |
| AI review | select [`ai`] | Any → `any` · AI-reviewed → `yes` · Not AI-reviewed → `no` | `any` |
| Sort | select [`sort`] | Due date, soonest first → `due` · Due date, latest first → `due_desc` · Waiting longest → `waiting` · Lowest confidence first → `confidence` | `due` |

- "Due this week" = from tomorrow through the end of the current ISO week (Monday–Sunday) in the app time zone (Q6).
- Default sort `due`: `due_on asc nulls last`, then `submitted_at asc`, then `crop_plan.id`. Ascending puts overdue first by definition; no separate "overdue first" rule is needed.
- `confidence` sort: low, medium, high, then due as above.
- Unknown or invalid parameter values fall back to the default silently (no error; the server never echoes the raw value).
- "Clear filters" is a link to `/review` (defaults). It shows only when any filter differs from its default.
- Under 720px the `<summary>` reads "Filters" or "Filters (— active)" with the count of non-default filters.

Data default `real` is deliberate: the daily job is real farms. Sample plans (`cp-agronomist` published-reference cases) are one click away.

### 3.6 Pagination
None in S2. Expected volume is 5–10 farms in the concierge season. The query has a hard cap `REVIEW_QUEUE_LIMIT` (env var, default 200). When the cap is hit, the footer reads: "Showing the first {shown} of {total} plans. Narrow the filters to see the rest." Otherwise: "Showing all {total} plans." (singular: "Showing the only plan.")

### 3.7 States

| State | What renders |
|---|---|
| Loading (HTMX filter change) | `aria-busy="true"` on `#queue-results`; the old rows stay visible. No skeletons, no spinner except the existing HTMX opacity. |
| Empty, no filters active, nothing awaiting | In place of the table: title "No plans waiting for a decision." Body: "New plans appear here as soon as the engine runs. See every plan with Status: All." ("Status: All" is a link to `/review?status=all`.) |
| Empty, filters active | "No plans match these filters." + link "Clear filters". |
| Empty, Data = Real farms, sample plans exist | Add the line: "There are sample plans waiting. Show sample plans." (link sets `kind=sample`). |
| No human agronomist in the org (N-NO-HUMAN) | Info notice above the filters, for every role: title "No human agronomist in this organisation yet", body "Real-farm plans stay In review until one is added. AI reviews are recorded but do not approve." Not dismissable. |
| Server error | Existing error notice: "Something went wrong and nothing was saved. Try again. If it keeps happening, note the time: {HH:MM}." Filters keep their values. |
| Stale list | The list does not poll. A row whose plan was decided since load still links to the detail, which shows the current state (§4.7). |
| 403 (owner/org_admin after PM-DR-oa) | Existing error page, text: "Only agronomists and CloverProof staff can see plans waiting for review." |

### 3.8 HTMX and URLs
- `GET /review` → full page. With `HX-Request` → partial `_review_rows.html` (summary line, table body or empty state, footer) swapped into `#queue-results` (`hx-swap="outerHTML"`).
- Form: `hx-get="/review" hx-target="#queue-results" hx-push-url="true"`; `hx-trigger="change from:select, input changed delay:300ms from:input[type=search], submit"`. Back/forward restores filters from the URL (full page render, no history cache needed).
- The "Apply filters" button is present in the HTML and hidden with `.js-hide` once HTMX loads, so the page works without JS.
- Each Plan link: `/plans/{plan_id}/review?queue={urlencoded current query string}`. The server parses `queue` as the known filter params only (never as a URL), so there is no open redirect.
- `/` redirects to `/review` for users with an `agronomist` membership; others keep `/farmers`.
- Header: add one text link "Review queue" left of the user menu (olive, `aria-current="page"` on `/review`). The header "no nav bar" rule stays; this is one link to the main daily task. The user menu also gains "Review queue" as its first item.

### 3.9 Accessibility
- `<table>` with `<caption class="sr-only">Plans, sorted by {sort label}</caption>`; header cells `scope="col"`.
- The summary line (`— awaiting decision · …`) is in a `role="status"` element inside `#queue-results`, so filter results are announced once per change.
- Tab order: search → status → due → crop → confidence → data → AI review → sort → (Apply) → Clear filters → first Plan link → … One tab stop per row.
- No custom single-key shortcuts (WCAG 2.1.4). Native controls only.
- Badges always contain their words. The AI-reviewed badge carries a visually hidden suffix ", not an agronomist approval".
- Focus after an HTMX swap stays on the control that changed (HTMX default with `outerHTML` on the results container only, not the form).

### 3.10 Data per element (field → table.column)

| Element | Source | Exists? |
|---|---|---|
| Plan row scope | `crop_plan` where `organisation_id = current org` | yes |
| Latest version | leaf of `recommendation` by `parent_id` per `crop_plan_id` | yes (computed, as `load_plan`) |
| Status | `recommendation_state.status` view (RK-X4), today computed from `review` | view missing (DB-5) |
| AI-reviewed | exists `review` with `decision = 'ai_review'` on latest version | missing (DB-4) |
| Due date | `crop_plan.review_due_on` | **missing (DB-1)** |
| Submitted (for "Waiting longest") | `recommendation.created_at` of the latest version | yes |
| Field / farm / farmer names | `field.name`, `farm.name`, `farmer.display_name` | yes |
| Sample flag | `farmer.record_kind` (`real`/`sample`) | **missing (DB-2)** |
| Crop | `crop_plan.crop` (label from pack) | yes |
| Season | `season.label` via `crop_plan.season_id` | yes |
| Version number, origin | position in chain; `recommendation.kind` + `app_user.kind` of `created_by` | number yes; AI edit needs DB-3 |
| Confidence | `recommendation.confidence` | yes |
| Placeholder flag | `recommendation.pack_status = 'placeholder'` or any `uses_placeholder` in `result` | jsonb scan works at this volume; a stored generated column `uses_placeholder` is cleaner (DB-6, optional) |
| No-human notice | exists `membership` role `agronomist` join `app_user` `kind='human'`, `disabled_at is null` | needs DB-3 |

---

## 4. Screen B — Review detail `/plans/{plan_id}/review`

Replaces webapp-ui.md §3.7 as the decision screen. `/plans/{plan_id}` (the numbers view, §3.5) stays; its bottom "Review" section becomes a link "Review this plan" to this page for anyone who can see it.

### 4.1 Purpose
Show what the engine said, what the latest version says, exactly which values changed and why, then let the right person decide. The diff is the screen; everything else supports it.

### 4.2 Layout, wide (≥ 960px)

```
Review queue / Dekker Farms / Hillside / Plan v—                       (breadcrumb; first item keeps queue filters)

┃ Placeholder pack: these numbers are not agronomic advice. Do not send to a farmer.   (existing banner, only if pack_status = placeholder)

Review: nitrogen plan for Hillside                         [IN REVIEW] [AI-REVIEWED]
Dekker Farms · Home farm · Real farm                        Minutes on this plan: —
Winter wheat · season — · target — t/ha · after soybean ·  Started —:—
— ha · plan date — · due — (Overdue)

┃ Approval needs a human agronomist                         (N-NO-HUMAN variant for the detail, only if no human agronomist)
┃ This is a real farm. Its plan stays In review until a human agronomist approves it.

[MEDIUM CONFIDENCE]  Why medium: No soil test on file. C6          (existing confidence block)

┃ Placeholder constants                                     (existing warn notice when any placeholder)
┃ Some numbers use PLACEHOLDER constants ... Check or replace them before approving.

─ Versions ────────────────────────────────────────────────────────────────────────────
 v1  Engine · — · engine — · pack ca-on — (placeholder)
 v—  Edited by Farjad Iranmehr · — · from v1
     “Field had manure last fall; farmer asked for a lower first split.”
 v—  AI edit by cp-agronomist (AI) · — · from v—       ← this version is under review
     “Published guide lists a lower rate after soybean.”

─ Engine v1 compared with v— ──────────────────────────────────────────────────────────
 Compare v— with [Engine (v1) ▾]     [ ] Show changed lines only
 — of — lines changed

 LINE                ENGINE (v1)                         v— (UNDER REVIEW)                    CHANGE
 ──────────────────────────────────────────────────────────────────────────────────────
 Nitrogen, season    — kg N/ha [PLACEHOLDER]             ▌— kg N/ha  CHANGED                  Changed: rate
 total               — kg N for — ha                     ▌— kg N for — ha  CHANGED
                     Why: Base rate for target yield…    Why: Agronomist edit: …
                     [MEDIUM CONFIDENCE]                 [MEDIUM CONFIDENCE]
 ──────────────────────────────────────────────────────────────────────────────────────
 Nitrogen, split —   — kg N/ha · — % of season           ▌— kg N/ha  CHANGED                  Changed: rate
 At planting         Product: No product matched yet     Product: No product matched yet
                     Timing: At planting (no dates yet)  Timing: At planting (no dates yet)
                     Why: Share from pack split rule.    Why: …
                     [MEDIUM CONFIDENCE]                 [MEDIUM CONFIDENCE]
 ──────────────────────────────────────────────────────────────────────────────────────
 Nitrogen, split —   — kg N/ha · — %                     — kg N/ha · — %                      No change
 Spring green-up     ...                                 ...
 ──────────────────────────────────────────────────────────────────────────────────────
 Phosphorus (P₂O₅)   Soil test recommended               Soil test recommended                No change
                     No rate without a soil test.        No rate without a soil test.
 Potassium (K₂O)     Soil test recommended               Soil test recommended                No change

 ▸ How the engine calculated, constants used, provenance        (<details>, closed; reuses plan.html sections 4–8)

─ Decision ────────────────────────────────────────────────────────────────────────────
 ┌ panel (the only panel on the page) ───────────────────────────────────────┐
 │ Decision for v—                                                            │
 │ ( ) Approve as shown                                                       │
 │ ( ) Reject                                                                 │
 │ Edit numbers instead → (link; saves v—, then comes back here)             │
 │ Reason  [________________________________]                                 │
 │ Required to reject. Optional to approve.                                   │
 │ Approving releases these numbers for the proof document. You are the       │
 │ reviewer of record.                                                        │
 │ [Save decision]                                                            │
 └────────────────────────────────────────────────────────────────────────────┘

─ History ─────────────────────────────────────────────────────────────────────────────
 — · — · Farjad Iranmehr · Edited · — min · “Field had manure…”
 — · — · cp-agronomist (AI) · AI review · — min · “…”
```

Order is fixed: header strip → org/D4 notice → confidence → placeholder notice → versions → diff → details → decision → history. The diff comes before the decision so the reader cannot reach the button without passing it (keyboard and screen reader order too).

### 4.3 Layout, narrow (< 720px)
- Header strip stacks (existing `.strip` rule): title, badges, meta, timer.
- Version chain stays a list.
- Diff: each line is a block, not a table row:
```
Nitrogen, split — · At planting
Changed: rate
  Engine (v1)
    — kg N/ha · — % of season [PLACEHOLDER]
    Product: No product matched yet
    Timing: At planting (no dates yet)
    Why: Share from pack split rule.
    [MEDIUM CONFIDENCE]
  v— (under review)
    ▌— kg N/ha  CHANGED
    ...
───────────────────────────
```
  "Change" moves to the top of the block (most useful first). The two sides are labelled sub-lists, separated by a rule, not boxes.
- Decision panel is full width; buttons 44px high; not sticky (the sticky action bar of §3.5 does not apply here, because the reason field must be visible with the button).

### 4.4 Components with exact copy

**Header strip**
- h1: "Review: nitrogen plan for {field}". Once P/K lines exist (S3) the h1 becomes "Review: fertilizer plan for {field}".
- Meta line 1: `{farmer} · {farm} · Real farm` or `· Sample plan` (text, plus the Sample badge in the badge row).
- Meta line 2: `{crop} · season {season} · target — t/ha · after {previous crop} · — ha · plan date {date} · due {date}` with " (Overdue)" or " (Due today)" appended in words; "· no due date" when null.
- Badges right: status badge, then AI-reviewed, then Sample. Timer under them (§4.6).

**Version chain** (`<ol class="versions">`, h2 "Versions")
- Engine row: "v1 Engine · {date HH:MM} · engine {engine_version} · pack {pack_id} {pack_version} ({pack_status})".
- Edit row, human: "v{n} Edited by {name} · {date HH:MM} · from v{parent n}", reason quoted below in a `blockquote.reason`.
- Edit row, AI: "v{n} AI edit by {name} (AI) · {date HH:MM} · from v{parent n}", reason quoted.
- The version under review carries the trailing text "this version is under review" (ink, 600). Approved/rejected final version: "approved by {name} on {date}" / "rejected by {name} on {date}".
- Each `v{n}` is a link that sets the right-hand side of the diff to that version (`?v={rec_id}`). The chain is one list, indentation shows `parent_id` depth (existing `by_lineage` order), no boxes.

**Diff controls**
- h2: "Engine v1 compared with v{n}" (or "v{a} compared with v{n}" when another base is chosen).
- Select "Compare v{n} with" [`base`]: "Engine (v1)" (default) and every other ancestor "v{k} ({origin})". Only ancestors of the shown version are offered.
- Checkbox "Show changed lines only" [`changed=1`]. Default off (a plan has few lines; showing all keeps the unchanged context visible).
- Summary: "{c} of {t} lines changed" or "No lines changed. This version has the engine's numbers." (for v1 vs v1, i.e. an unedited plan; in that case the right column title is "v1 (engine, unchanged)" and the Change column reads "No change" on every line.)

**Diff table** (`table.diff`, columns **Line**, **Engine (v1)** / **v{base}**, **v{n} (under review)**, **Change**)
- Line key = `(nutrient, split_no)`; plus one summary line per nutrient ("Nitrogen, season total"). Order: N season total, N splits by `split_no`, P, K, then any other nutrient in pack order.
- Line cell: "{Nutrient}, split {split_no}" + stage label on line 2; nutrient forms written explicitly ("Phosphorus (P₂O₅)", "Potassium (K₂O)", per webapp-ui.md §5.5).
- Side cell, in this order, each on its own line:
  1. Rate: explained-number macro (value + unit + Placeholder badge; explanation is item 5). Splits add " · — % of season" via the `share` macro.
  2. "Product: {product} at — {unit}" or "Product: No product matched yet" (until A4/S02-4 lands).
  3. "Timing: {window start}–{window end} ({basis: GDD | calendar | set by agronomist})" or "Timing: {stage label} (no dates yet)" (until S04-1).
  4. Confidence badge (line confidence).
  5. "Why: {explanation}". If missing: "Why: No explanation recorded" (bug state per webapp-ui.md §5.1).
- **Changed attribute** (right side only): the cell gets the existing `td.changed` 3px olive left rule **and** each changed attribute ends with the xs caps tag "CHANGED" (`<span class="tag-changed">Changed</span>`, ink text, 1px ink-soft border, ivory fill). Screen readers hear "Changed, was {old value}" via a visually hidden span. Three signals: position, rule, word.
- **Change** cell: "No change" (ink-soft) · "Changed: {list of attributes}" (ink, 600; e.g. "Changed: rate, timing") · "Only in v{n}" · "Only in the engine version" · "Removed in v{n}".
- **One side only.** The missing side renders a single line "Not in {version label}" (ink-soft, italic not used), never an empty cell.
- **No soil test.** P and K lines render on both sides as "Soil test recommended" + "No rate without a soil test." No rate, no product, no timing, no confidence badge on those lines. N confidence never shows higher than Medium (engine rule; the UI only displays it). If a version ever contains a P/K rate on a plan with no soil test, render the rate cell as error text "P/K rate on a plan without a soil test. Do not approve; report this." and hide the Approve option (defensive; should be impossible per hard rule 3).
- **Placeholder.** Any number with `uses_placeholder` gets the dashed "Placeholder" badge in its cell, on both sides.

**Decision area** — see §4.5 per role. Shared copy:
- h2 "Decision". Panel title (600): "Decision for v{n}".
- Radios (human agronomist): "Approve as shown" (real) / "Approve sample plan" (sample) / "Approve for testing only" (placeholder pack, existing); "Reject".
- Link under the radios: "Edit numbers instead" + hint "(saves v{n+1}, then comes back here)" → `/plans/{plan_id}/edit?return=review`.
- Reason label: "Reason". Hint: "Required to reject. Optional to approve." Errors: "Add a reason for rejecting." · "Choose Approve or Reject."
- Placeholder acknowledgement (real farm, human agronomist, any PLACEHOLDER in the version): required checkbox "I checked every Placeholder value on this plan for this field." Error: "Confirm you checked the Placeholder values, or edit them first." (Q4: CPO may prefer to block approval outright.)
- Confirm line (real farm): "Approving releases these numbers for the proof document. You are the reviewer of record." Sample: "This is a sample plan. Approval is recorded for testing; the numbers never go to a farmer." Placeholder pack: existing testing-only line.
- Button: "Save decision" (primary); label changes with the radio: "Approve plan" / "Reject plan" (danger variant). Loading "Saving decision…". Double-submit guard: button disabled after first submit + server idempotency (existing `review_one_approval_idx`).

**Edit page delta** (`/plans/{plan_id}/edit`, plan_edit.html)
- Wording stays "Edit plan v{n}" / "Saving creates v{n+1}. The engine numbers stay on record." Never "edit", "update" or "change" the plan in place.
- Human agronomist gets two submit buttons: "Save as v{n+1}" (secondary) and "Save as v{n+1} and approve" (primary, RV-04). The second shows the same confirm line and placeholder checkbox as the decision panel.
- AI account: only "Save as v{n+1}". Sub-line adds: "Your version is marked as an AI edit. A human agronomist must still approve it."
- No-soil-test plans: the edit table has no P/K rows (hard rule 3).
- After saving, redirect to `/plans/{plan_id}/review` with success notice "Saved as v{n+1}. Compare it with the engine below." and focus on the diff h2.

### 4.5 Decision area by role (D4)

| Viewer / plan | Renders in the Decision section |
|---|---|
| Human agronomist, latest version, not decided | The panel in §4.4. |
| AI agronomist, **real farm** (N-AI-REAL) | Info notice, title "Approval needs a human agronomist", body "This is a real farm. Only a human agronomist can approve or reject its plan. Your sign-off is saved as an AI review and the plan stays In review." Then the panel with: textarea "AI review notes (required)", hint "What you checked and anything the human agronomist should look at.", button "Record AI review" (secondary), link "Edit numbers instead". Error: "Write your review notes." |
| AI agronomist, **sample** (N-AI-SAMPLE) | Same, body: "This is a sample plan. Your sign-off is saved as an AI review. It is not an approval." |
| AI agronomist, AI review already recorded on this version | Line "You recorded an AI review of v{n} on {date}." + the notes quoted. No second AI review on the same version. |
| staff, superadmin (not a human agronomist), owner/org_admin (N-VIEW) | Info notice, title "View only", body "Only a human agronomist can approve, edit or reject plans. Real-farm plans stay In review until one does." No form, no buttons, no disabled controls. |
| Anyone, plan already approved | Success notice "Approved by {name} on {date}. — minutes recorded." + reason if any. Version is read-only. Link "Back to the queue". |
| Anyone, plan rejected | Error notice "Rejected by {name} on {date}." + reason. Read-only. |
| Anyone, viewing an older version (`?v=` not the latest) | Notice "You are viewing v{k}. Decisions apply to the latest version, v{n}." + link "Show v{n}". No form. |

The `ai_reviewed` badge text is always "AI-reviewed". It never uses the success colours, never sits in the status position, and no copy anywhere says "approved", "reviewed by an agronomist" or "signed off" for an AI review. History lists it as "AI review", reviewer "{name} (AI)".

### 4.6 Timer (RV-02)
- Existing `_timer.html` and `/plans/{plan_id}/timer` (`every 60s`), text "Minutes on this plan: —". Add under it (xs ink-soft): "Started {HH:MM}" from the signed start.
- Runs only for users who can record a review row (human agronomist, AI agronomist). Others see no timer (their viewing is not plan work).
- On any decision, edit, or AI review, the server writes `review.started_at` (from the signed start) and `review.finished_at` (server now); `minutes_spent` = whole minutes between them (DB-7).
- After the final decision: "Started {date HH:MM} · finished {HH:MM} · — minutes recorded."

### 4.7 States

| State | What renders |
|---|---|
| Loading (diff base change, changed-only toggle) | `aria-busy="true"` on `#diff`; previous diff stays visible. |
| Decision submit | Button disabled, "Saving decision…". Full POST, not HTMX. |
| Validation error | Error summary at the top of the panel ("Fix — fields before saving the decision.") + field errors; values kept; focus moves to the summary. |
| **Concurrent: someone decided first** | On submit, 409 re-render with error notice: "{name} {approved|rejected} v{n} at {HH:MM}. Nothing was saved." (extends existing `ALREADY_REVIEWED`). |
| **Concurrent: a newer version exists** | On submit: "A newer version, v{m}, was saved by {name} at {HH:MM}. Nothing was saved. Review v{m}." with link (extends `STALE_VERSION`). |
| **Concurrent, detected while open** | The 60 s timer request sends `rec={latest_rec_id}`. If the latest version or its decision changed, the response adds an out-of-band warn notice at the top of `#decision`: "This plan changed since you opened it: {what}. Reload before deciding." with button "Reload". The form stays (server still rejects stale posts). |
| Timer missing | Existing `TIMER_MISSING` message. |
| Plan not found / other org | 404 "Plan not found." (no leak of existence). |
| No engine result | Existing 409 "This plan has no engine result yet." |
| Server error | Existing generic error notice; reason text kept. |
| After a decision | 303 back to this URL, notice per §4.5, plus link "Next in queue: {field} ({due label})" built from the `queue` param (first awaiting row excluding this plan), or "The queue is empty for these filters. Back to the queue." |

### 4.8 HTMX and URLs

| Action | Method + URL | Params | Response |
|---|---|---|---|
| Open | GET `/plans/{plan_id}/review` | `v` (rec id, default latest), `base` (rec id, default root), `changed`, `queue` | full page; sets timer cookie if absent (existing) |
| Change diff base / toggle | GET same URL with `HX-Request` | same | partial `_diff.html` into `#diff`, `hx-push-url="true"` |
| Timer + staleness | GET `/plans/{plan_id}/timer?rec={id}` | `rec` | `_timer.html` + optional `hx-swap-oob` notice |
| Approve / reject | POST `/plans/{plan_id}/review` | `csrf_token`, `recommendation_id`, `decision` = `approve`/`reject`, `reason`, `placeholders_checked`, `queue` | 303 to detail; 409 / 422 re-render |
| AI review | POST `/plans/{plan_id}/review` | `decision=ai_review`, `reason` (required) | same |
| Edit | GET/POST `/plans/{plan_id}/edit` | existing + `then=approve` | 303 to detail |

The server decides what is allowed from the session user, org role and `app_user.kind`, never from form fields. A `decision=approve` from an AI or non-agronomist user returns 403 "Only a human agronomist can approve a real-farm plan." / "Only a human agronomist can approve plans." and writes an `audit_event`. The JSON API (`/api/v1/review/*`, RV-01..05) reuses the same service functions later; not in this S2 HTML scope.

### 4.9 Accessibility
- One h1; h2 for Versions, the diff, Details, Decision, History.
- Diff table: `<caption class="sr-only">Each plan line, the engine value and the value in v{n}</caption>`; Line cells are `th scope="row"`; side column headers `scope="col"`. DOM order is Line → base side → shown side → Change on every width. The row `th` also carries a visually hidden summary ("Nitrogen, split {k}, changed: rate") so screen-reader users hear the change first. Under 720px the Change text is shown visually at the top of the block by repeating it as a visible line in the `th` (the last `td` is hidden there with `display:none`), never by CSS `order`. No CSS reordering of focusable content.
- "Changed" is text, not colour; the olive rule is decorative.
- Radios in a `fieldset` with legend "Decision for v{n}"; reason linked with `aria-describedby` to its hint and error.
- The D4 notices are plain notices (not `role="alert"`); they are present on load, not events.
- The OOB staleness notice uses `role="status"` (polite), not alert, so it does not interrupt typing.
- Focus: after a 409/422 re-render, focus the notice/summary (`tabindex="-1"`). After "Next in queue", focus the h1.
- Contrast: all text pairs are from webapp-ui.md's table; new pairs in §5 are checked.

### 4.10 Data per element

| Element | Source | Exists? |
|---|---|---|
| Versions, parent chain | `recommendation.id, parent_id, kind, reason, created_by, created_at` | yes |
| Version origin AI vs human | `app_user.kind` of `recommendation.created_by` | **missing (DB-3)** |
| Engine/pack provenance | `recommendation.engine_version, pack_id, pack_version, pack_status, pack_sha256` | yes |
| Line values | `recommendation_line` (nutrient, rate_kg_ha, product_id, product_rate, product_unit, split_no, timing_window_start/end, timing_basis, explanation, confidence) | **missing (DM-14)**. Until it lands, derive N lines from `result.nitrogen` (`rate`, `total`, `splits[]`) and P/K from `result.phosphorus_potassium` — same row shape, so the template does not change later. |
| Line placeholder flag | `uses_placeholder` per explained number in `result` | yes (jsonb) — `recommendation_line` needs a `uses_placeholder boolean` too (DB-8) |
| Diff computation | per-line join of base and shown version on `(nutrient, split_no)` | today `recommendation_diff` view is N-only; per-line delta is DM-16 |
| Soil test present | `crop_plan.soil_test_id is not null` | yes |
| Status / decided by | `review.decision, reviewer_id, reason, created_at` → `recommendation_state` view | view missing (RK-X4, DB-5) |
| AI review | `review.decision = 'ai_review'` | **missing enum value (DB-4)** |
| Timer start / finish | `review.started_at, finished_at` | **missing (DM-15, DB-7)** |
| Real vs sample | `farmer.record_kind` | **missing (DB-2)** |
| Due date | `crop_plan.review_due_on` | **missing (DB-1)** |
| Human agronomist exists | `membership` × `app_user.kind` | needs DB-3 |

---

## 5. Design system deltas

All in `app/cloverproof_app/static/app.css` and `templates/_macros.html`. No new colours; every pair below uses existing tokens.

| Item | Spec | Contrast |
|---|---|---|
| `.badge.ai` "AI-reviewed" | ivory fill, 1px solid `--ink`, ink text, same pill/type as other badges | ink on ivory 12.53 |
| `.badge.sample` "Sample" | `--sand` fill, `--ink-soft` text, no border | 6.18 |
| `.tag-changed` "Changed" | xs 700 caps, ivory fill, 1px `--ink-soft` border, ink text, radius 2px (not a pill, so it is not read as a status) | 12.53 |
| `.due-overdue` | `--error` text, 600 | 7.14 on ivory |
| `.due-today` | ink, 600 | 12.53 |
| `table.diff` | existing table rules; `td.changed` already exists (3px olive left rule); column widths Line 18%, sides 34% each, Change 14% | — |
| `.filters` | flex-wrap row of `.field.inline` (label above control, 40px controls), gap `--s4`; under 720px inside `<details>` | border-input 3.46 on white |
| `ol.versions` | no bullets; `v{n}` in tabular 600; nested depth indent `--s5` | — |
| `.site-header .nav-link` | olive text link, underline on hover, `aria-current` underlined always | 6.44 |
| Macros | `ai_badge()`, `sample_badge()`, `due(date, today)`, `diff_side(line)`, `change_summary(row)`, `kind_label(farmer)` | — |

**Logo.** `base.html` currently draws the clover mark as hand-made SVG circles. `brand/README.md` (origin/website-v1) says the logo must not be redrawn and that no official SVG exists yet. Replace it with the official `cloverproof-horizontal-olive.webp` (or the mark file) copied into `static/` until the SVG arrives. This affects every page, not just these two; flagging for `cp-concierge-app`.

Analytics: no client-side analytics in the internal tool. The measurable events are DB rows: `review` (with `started_at`, `finished_at`, `minutes_spent`) and `audit_event` for every decision and every refused approve attempt.

---

## 6. Hand-off notes for `cp-concierge-app`

**Do not change**
- D4 behaviour in §2 and §4.5, including that non-approvers get a notice, not a disabled button, and that "AI-reviewed" never shares the approved style or wording.
- The diff comes before the decision, in the DOM and visually.
- "Changed" is text + rule, never colour alone. One-side lines always say which side is missing.
- No P/K rate ever renders on a plan without a soil test.
- Immutable wording: "Save as v{n+1}", "creates", never "update"/"edit in place".
- Every number through the explained-number macro.

**Flexible**
- Exact column widths, the changed-only threshold, whether "Due this week" uses ISO weeks or a rolling window (keep the label honest).
- Whether "Next in queue" also appears on the queue page as a "Start with the first overdue plan" link.

**Build order suggestion:** DB-1/2/3/4 migrations (cp-database) → queue page on current jsonb → detail diff on jsonb lines → switch the line source to `recommendation_line` when DM-14 lands.

---

## 7. Open questions and data-model needs

### For `cp-database`
| ID | Need | Proposal |
|---|---|---|
| DB-1 | **No due-date column exists.** | `crop_plan.review_due_on date null` (mutable table; changes audited). Set at plan creation = plan date + `REVIEW_DUE_DAYS` (config; value is a CPO/ops decision, Q5). Editable by agronomist/owner on the field page later; not on this screen in S2. Index `(organisation_id, review_due_on)`. |
| DB-2 | **No real vs sample flag.** | `farmer.record_kind enum('real','sample') not null default 'real'`. Trigger: cannot change once any recommendation exists for that farmer (a human-approved sample plan must never become a real plan). |
| DB-3 | **No human vs AI marker on users** (REC-D4, PM-AP-ag). | `app_user.kind enum('human','ai') not null`, no default for new rows (the CLI must state it); backfill existing users as `human` after checking each. |
| DB-4 | **No `ai_reviewed` path.** | Add `ai_review` to `review_decision`. Trigger: `kind='ai'` reviewer → decision in (`ai_review`, `edit`); `approve`/`reject` require `kind='human'` + `agronomist` membership (all plans, per S4; at minimum real farms per D4). `reason` required for `ai_review`. One `ai_review` per (recommendation, reviewer). |
| DB-5 | Status on an immutable row (RK-X4). | `recommendation_state` view: per latest version `status` (`in_review`/`approved`/`rejected`/`superseded`), `ai_reviewed boolean`, `decided_by`, `decided_at`. The queue reads only this view. |
| DB-6 | Placeholder flag for the list (optional). | `recommendation.uses_placeholder boolean generated always as (...) stored` or computed in the view. |
| DB-7 | Timer persistence (DM-15). | `review.started_at timestamptz not null`, `finished_at timestamptz not null default now()`, check `minutes_spent = floor(extract(epoch from finished_at - started_at)/60)`. |
| DB-8 | Line-level diff (DM-14, DM-16). | `recommendation_line` as §6.4 + `uses_placeholder boolean` + `stage_label text`; line key `(recommendation_id, nutrient, split_no)` unique; per-line delta view. |
| DB-9 | AI edits in calibration. | `recommendation_diff` / `calibration_delta` must exclude or separately tag versions created by `kind='ai'` users (head-of-data: AI never counts toward the agreement gate). |

### For the CPO (decisions)
| ID | Question | My recommendation |
|---|---|---|
| Q1 | May the AI account reject, or approve **sample** plans? | No to both (S4). AI records `ai_review` and may propose an edited version. |
| Q2 | S02-DoD needs "1 full PDF", but PDF v0 is generated from **approved** recommendations only, and AI cannot approve. Who approves the 5 published-reference sample cases? | Either a human agronomist approves a sample (allowed, "Approve sample plan"), or cp-pdf accepts `ai_review` on **sample** plans for a test PDF watermarked "Sample, not reviewed by an agronomist". Needs a CPO + cp-pdf call. |
| Q3 | owner/org_admin seeing drafts (PM-DR-oa) | Follow §3.2: 403 on queue and detail after ADR 0008. Until then, view-only notice. |
| Q4 | Real-farm approval while PLACEHOLDER constants are present | Require the acknowledgement checkbox (§4.4) in S2; block outright once the human agronomist has validated pack v1 constants. CLAUDE.md rule 9 + webapp-ui.md "check or replace them before approving". |
| Q5 | Due-date rule (`REVIEW_DUE_DAYS`, business vs calendar days) and whether "priority" (A1 says "due date/priority") is needed | Due date only in S2; priority adds a second ordering nobody will maintain for 5–10 farms. |
| Q6 | App time zone for "Overdue"/"Due today" | `APP_TIMEZONE` env var, `America/Toronto` for the Ontario pilot; no per-org zone yet. |
| Q7 | Does Farjad Iranmehr count as the human agronomist (RK-X1, OQ-04)? | Until answered, the N-NO-HUMAN notice shows in every org and no real-farm plan can leave In review. That is correct per D4, and visible by design. |
| Q8 | Review claiming ("being reviewed by X") | Not in S2; the staleness check (§4.7) covers the risk at this volume. |
