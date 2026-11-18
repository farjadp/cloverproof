# Concierge tool UI spec (v1, internal)

For `cp-concierge-app`, Step 5 of `docs/plans/webapp-v1.md`. FastAPI + Jinja2 + HTMX, one plain CSS file
(`app/cloverproof_app/static/app.css`), no build step. Sole user: the agronomist. The goal is fewer minutes per plan, not visual polish.
Look: the website's paper and ink (`website/src/app/globals.css`), with no motion. Login reference:
`docs/design/stitch/auth-account-setup.jpg` (take its two-column sign-in idea only; ignore its numbers, sign-up tab, "Remember 30 days" and status badges).

## 1. Tokens

```css
:root {
  /* brand */
  --olive: #4C610B;  --olive-deep: #3B4B08;  --sage: #A7B58A;  --ivory: #FAF6EB;  --ink: #273125;
  /* derived (same values as the website) */
  --sage-soft: #E6EADB;  --sand: #F1ECDD;  --ink-soft: #4D5A4A;  --rule: #DDD6C3;  --paper: #FFFFFF;
  /* functional */
  --border-input: #8F8A78;   /* form control borders, non-text 3:1 */
  --focus: #4C610B;
  --error: #9A2A1E;  --error-bg: #F7E1DA;
  --warn: #6B5200;   --warn-bg: #F5E9C8;   /* low confidence, PLACEHOLDER */
  --success: #2F5E1A; --success-bg: #E6EADB;
  /* type */
  --font-serif: "Source Serif 4", "Iowan Old Style", Georgia, serif;
  --font-sans: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
  --fs-xs: .8125rem; --fs-sm: .9375rem; --fs-base: 1.0625rem; --fs-lg: 1.25rem;
  --fs-xl: 1.625rem; --fs-2xl: 2.125rem;     /* serif only for xl/2xl and screen titles */
  --lh-body: 1.55; --lh-head: 1.2;
  --num: tabular-nums;                       /* font-variant-numeric on every number */
  /* space (4px base) */
  --s1: .25rem; --s2: .5rem; --s3: .75rem; --s4: 1rem; --s5: 1.5rem; --s6: 2rem; --s7: 3rem;
  --radius: 4px; --radius-pill: 999px;
  --content: 60rem;  --measure: 42rem;      /* page max width; prose/form max width */
}
```

Contrast (WCAG 2.x, calculated):

| Text / foreground | On | Ratio | Use |
|---|---|---|---|
| ink #273125 | ivory | 12.53 | body |
| ink-soft #4D5A4A | ivory / sand / white | 6.76 / 6.18 / 7.30 | secondary text, labels |
| olive #4C610B | ivory / sand / sage-soft | 6.44 / 5.88 / 5.68 | links, headings accent |
| ivory on olive / olive-deep | | 6.44 / 8.86 | primary button (default / hover) |
| ink on sage #A7B58A | | 6.20 | medium badge (sage as fill only) |
| error #9A2A1E | ivory / error-bg / white | 7.14 / 6.59 / 7.71 | error text |
| warn #6B5200 | ivory / warn-bg | 6.87 / 6.13 | low + PLACEHOLDER badges |
| success #2F5E1A | ivory / success-bg | 7.11 / 6.27 | approved state |
| border-input #8F8A78 | white | 3.46 | input borders (3:1 non-text) |

Do not use sage #A7B58A as text (2.02 on ivory). `--rule` (1.34) is decorative only, never the sole boundary of a control.
Focus: `outline: 2px solid var(--focus); outline-offset: 2px` on `:focus-visible`, for everything.

### Fonts (self-hosted, SIL OFL 1.1)
Put these in `app/cloverproof_app/static/fonts/`. They are variable (wght axis) Latin subsets from Fontsource (jsDelivr); every URL returned 200 when checked.

| File | Source |
|---|---|
| `source-serif-4-latin-wght-normal.woff2` | https://cdn.jsdelivr.net/fontsource/fonts/source-serif-4:vf@latest/latin-wght-normal.woff2 |
| `source-sans-3-latin-wght-normal.woff2` | https://cdn.jsdelivr.net/fontsource/fonts/source-sans-3:vf@latest/latin-wght-normal.woff2 |
| `source-sans-3-latin-wght-italic.woff2` | https://cdn.jsdelivr.net/fontsource/fonts/source-sans-3:vf@latest/latin-wght-italic.woff2 |
| `OFL-source-serif.txt` | https://raw.githubusercontent.com/adobe-fonts/source-serif/release/LICENSE.md |
| `OFL-source-sans.txt` | https://raw.githubusercontent.com/adobe-fonts/source-sans/release/LICENSE.md |

Optional: if farm or lab names need accents beyond Latin-1, add `latin-ext-wght-normal.woff2` for both families from the same URLs (`unicode-range` U+0100-024F, U+1E00-1EFF).

```css
@font-face { font-family: "Source Serif 4"; font-style: normal; font-weight: 200 900; font-display: swap;
  src: url("/static/fonts/source-serif-4-latin-wght-normal.woff2") format("woff2"); }
@font-face { font-family: "Source Sans 3"; font-style: normal; font-weight: 200 900; font-display: swap;
  src: url("/static/fonts/source-sans-3-latin-wght-normal.woff2") format("woff2"); }
@font-face { font-family: "Source Sans 3"; font-style: italic; font-weight: 200 900; font-display: swap;
  src: url("/static/fonts/source-sans-3-latin-wght-italic.woff2") format("woff2"); }
```
Preload the two normal files in `<head>` (`<link rel="preload" as="font" type="font/woff2" crossorigin>`).

## 2. Layout
- `body`: ivory background, ink text, sans, `--fs-base`, `--lh-body`. No shadows, no gradients, no animation (except the HTMX spinner opacity).
- **App shell** (`base.html`, links from `nav.py`): always visible, no JS, no hidden menu. From 960px a sticky left column (`--sidebar`, sand) holds the clover mark plus "CloverProof", the organisation (with "Switch organisation" or "Choose organisation" when relevant), the primary navigation, then the user's name and role, "My account" and "Sign out" (POST + CSRF). Below 960px the same content is a compact header with the navigation wrapping under it. The current page is an olive fill with `aria-current="page"`.
- **Navigation by role**: Farmers and My account for internal roles, Review queue for those who may review, Products for everyone signed in, Users for org admins. Without an organisation: Products and Change password. While a temporary password must be replaced: Sign out only. Links mirror the route rules; the routes still enforce them.
- **Breadcrumb** above the page title on every page below the top level: `Farmers / {farmer} / {field} / Plan v{n}`, `--fs-sm` ink-soft, with olive links.
- **Main**: left-aligned beside the shell, `max-width: var(--content)`, padding `--s6` (`--s4` under 720px). Forms and prose are capped at `--measure`. Pages with a list plus short forms use `.split`: the list on the left and form panels in a 22rem column from 1120px, stacked below that.
- **Sections** are separated by `border-top: 1px solid var(--rule)` and `--s6` of space, not by boxes. The only boxed surface is a **panel** (white, 1px `--rule`, `--radius`). Never put a panel inside a panel.
- Tablet (≥ 768px): no changes. Under 720px, tables become stacked rows (label above value) and side-by-side columns stack.

## 3. Screens
Every page has `<title>{Screen} · CloverProof</title>`, one `h1` (serif `--fs-2xl`) and a skip link "Skip to content".
Loading: any HTMX request sets `aria-busy="true"` on its target and disables the button, whose label changes to the "…ing" form shown below. There are no skeletons.
Server error (any screen): an error notice reading "Something went wrong and nothing was saved. Try again. If it keeps happening, note the time: {HH:MM}." Values the user typed stay in the form.

### 3.1 Login `/login`
- Two columns at ≥ 960px, one column below. **Left** (ink-soft, `--measure`): the kicker "Internal tool" (xs caps), the h1 "Fertilizer plans, reviewed by an agronomist", and the line "Sign in to prepare and review field plans. Accounts are created by an administrator." **Right**: a panel containing the h2 "Sign in", the fields "Email" and "Password", and a full-width primary button "Sign in".
- There is no "create account", no "forgot password" (accounts are created by CLI) and no "remember me".
- Errors (one generic message, so nobody can tell whether an account exists): "Email or password is incorrect." Rate-limited: "Too many attempts. Wait 15 minutes and try again." Session expired, shown as an info notice after a redirect: "You were signed out. Sign in again to continue." CSRF failure: "This form expired. Reload the page and sign in again."
- Loading: "Signing in…".
- Footer line (xs, ink-soft): "CloverProof · internal concierge tool".

### 3.2 Farmers `/farmers`
- h1 "Farmers". Right of the title: a secondary button "Add farmer" (only if the add flow is in scope; otherwise omit it).
- A table with the columns **Farmer**, **Farm**, **Fields**, **Last plan**, **Status**. The Fields cell lists field names as links, one per line, each with its area ("{field} · — ha"). Last plan is the date plus a status badge (Draft / In review / Approved / Rejected).
- A search input above the table filters as you type (`hx-get`, debounce 300 ms): label "Find farmer or field".
- Empty: "No farmers yet. Farmers are added with the admin command; see the runbook." Empty search: "Nothing matches "{q}"."

### 3.3 Field detail `/fields/{id}`
- h1 = field name. Below it, a definition list (inline, ink-soft): Farmer · Farm · Area — ha · Soil test: "{date}, {top}–{bottom} cm, {lab|estimate}" or "No soil test on file".
- A primary button "New plan".
- Section "Plans": a table with the columns **Season**, **Crop**, **Version**, **Confidence**, **Status**, **Updated**. Each row links to its suggestion. Superseded versions show in a nested indent under their latest version as plain rows (same table, not a card), with ink-soft text and "v{n} · replaced by v{m}".
- Empty: "No plans for this field yet." followed by the "New plan" button again.

### 3.4 New plan `/fields/{id}/plans/new`
One form, `--measure` wide, with fieldsets that have a serif `legend`. Labels sit above the inputs, units sit as suffix text inside the field row, and hints are xs ink-soft.
1. **Crop and target**
   - Crop: a select, "Wheat" only for now.
   - Target yield: a number with suffix "t/ha", hint "Realistic yield for this field, not the best year."
   - Previous crop: a select built from the pack `previous_crop_credits` labels.
   - Area: a number with suffix "ha", hint "Entered by hand. Map drawing comes later."
   - Plan date: a date input, defaulting to today.
2. **Soil test (optional)**: a radio group "Do you have a soil test for this field?", with the options "No soil test" (default) and "Yes, enter it".
   - Choosing "No soil test" shows an info notice: "Without a soil test the plan gives nitrogen only, at medium confidence at most. Phosphorus and potassium need a test."
   - Choosing "Yes" reveals the fields below with `hx-get`; the server re-renders the fieldset, so it also works without JS.
   - Sample date (a date input); the error "Sample date is after the plan date." must match the engine rule.
   - Depth: two numbers in one row, "Top" and "Bottom", with suffix "cm"; error "Bottom must be deeper than top."
   - Source: a radio with "Lab" or "Estimate". Estimate hint: "Estimates cap confidence at medium."
   - Lab name: text, shown when Source is Lab.
3. **Values**: a repeatable row; "Add value" appends a row via `hx-get`, and each row has a "Remove" text button. The row's fields are:
   - Nutrient form (P, P2O5, K, K2O, NO3-N; render as P₂O₅, K₂O, NO₃-N but submit the enum)
   - Value (number)
   - Unit (mg/kg, ppm)
   - Extraction method (Olsen, Bray-1, Mehlich-3, Other)
   - Method detail (text, required when Other)

   Errors:
   - "Each nutrient can appear once. You entered P twice (as P and P₂O₅)."
   - "Name the extraction method."
   - "Enter a value of zero or more."

Actions: the primary "Run engine" (loading "Running…") and the text button "Cancel".
Validation is server-side. The errors sit under each field (§4) and an error summary at the top says "Fix {n} fields before running the engine." with links to each field.

### 3.5 Suggestion `/plans/{id}`
The order is fixed. Every number shown appears as an **explained number** (§4).
1. **Header strip**: the h1 "Nitrogen plan for {field}" and the line "Wheat · target — t/ha · after {previous crop} · — ha · plan date {date}". On the right are a status badge and the timer (§3.7).
2. **Confidence**: the confidence badge and, under it, the list "Why {level}:" with one line per `confidence_reasons[].reason` (show rule id xs ink-soft at the end, e.g. "C6"). When there are no reasons: "No rule lowered confidence."
3. **Placeholder notice** (warn notice, shown if any number has `uses_placeholder`): "Some numbers use PLACEHOLDER constants that are not yet validated. They are marked below. Check or replace them before approving."
4. **Nitrogen**
   - The rate (large: serif `--fs-xl`, "— kg N/ha") and the total ("— kg N for — ha"), each with its explanation directly under it.
   - If `bound_applied`, show a notice: "Rate limited to the pack {min|max}."
   - "How it was calculated": the `components`, as a table with the columns **Step**, **Value**, **Explanation**.
   - "Split applications": a table with the columns **Stage**, **Share**, **Rate**, **Total**. Each number cell has its explanation on the next line in xs ink-soft.
5. **Phosphorus and potassium**: the `phosphorus_potassium.text`. When there is no soil test, show the info notice titled "Get a soil test for P and K", with the body "This plan covers nitrogen only. Send a sample to a lab to get phosphorus and potassium advice."
6. **Notes**: the `notes[].text` items as a list.
7. **Constants used** (a `<details>` that is closed by default, summary "Constants used (—)"): a table with the columns Path, Value, Unit, Status (badge), Source ("No source yet" if null).
8. **Provenance** (xs ink-soft, monospace for hashes): "Engine {engine_version} · Pack {pack_id} {pack_version} ({pack_status}) · Pack hash {first 12 of sha256}". The full hash goes in `title` and a copy button.
9. **Actions** (agronomist only, sticky to the bottom of the viewport on tablets): "Approve", "Edit numbers", "Reject". Reviewers and viewers see the line "Waiting for agronomist review." instead.

### 3.6 Edit with reason `/plans/{id}/edit`
- h1 "Edit plan v{n}", with the sub-line "Saving creates v{n+1}. The engine numbers stay on record."
- A table with the columns **Item**, **Engine**, **Your number**, **Unit**. The rows are N rate, N total and each split rate. The Engine cell shows the read-only value with its explanation under it. "Your number" is an input pre-filled with the engine value. Changed rows get a 3px olive left rule and the text "Changed" (xs).
- Under 720px, Engine and Your number stack.
- Reason: a required textarea (the label is "Reason for the change (required)", with hint "Kept with the plan. Example: field history, local trial, farmer constraint."). Error: "Write why you changed the numbers."
- If nothing changed: "No numbers changed. Edit at least one number, or go back."
- Actions: the primary "Save as v{n+1}" (loading "Saving…") and the text "Cancel".
- After saving, the suggestion view shows a two-column comparison band ("Engine" | "Final (v{n+1})") for every edited number, with the reason quoted below it. Both columns stay visible on every later version.

### 3.7 Review `/plans/{id}/review`
- Timer: the text "Minutes on this plan: —" sits in the header strip and updates once a minute via `hx-trigger="every 60s"` from server time. It is not a ticking clock and has no seconds. It starts when the plan is first opened and stops on review, and the stored value is shown read-only after review.
- The decision is a radio group:
  - "Approve as shown"
  - "Approve with edits" (a link to §3.6 that returns here)
  - "Reject"
- Reason: a textarea. It is required for Reject and for Approve with edits, and optional for Approve. Error: "Add a reason for rejecting."
- Confirm line, above the button: "Approving releases these numbers for the proof document. You are the reviewer of record."
- Button labels follow the choice: "Approve plan" (primary), "Save edits and approve" or "Reject plan" (danger). Loading: "Saving review…".
- After the review, a success notice reads "Approved by {name} on {date}. — minutes recorded." For a rejection, an error notice reads "Rejected by {name} on {date}." followed by the reason. The plan becomes read-only.
- Non-agronomist on this URL: a 403 page with the text "Only the agronomist can review plans."

## 4. Components
- **Button**: sans 600 `--fs-sm`, 40px high (44px under 720px), padding `0 var(--s4)`, `--radius`. The variants are:
  - *primary*: olive fill with ivory text; hover olive-deep.
  - *secondary*: a 1px ink-soft border with ink text on transparent; hover sand fill.
  - *danger*: an error border and error text; hover error-bg.
  - *text*: olive, underlined on hover.

  Disabled: 50% opacity with `cursor: not-allowed`. Transitions are `background-color 120ms ease-out` only.
- **Form field**:
  - The `label` is 600 `--fs-sm` ink. The input is white, with a 1px `--border-input` border, `--radius`, a height of 40px and `--fs-base`.
  - The suffix unit sits in ink-soft inside the right padding.
  - In the error state the border is 2px `--error`, the text below starts with "Error:" (visually an icon-less prefix), and it is linked with `aria-describedby` and `aria-invalid="true"`.
  - Number inputs use `inputmode="decimal"` and tabular numerals.
- **Badge**: a pill, xs 700 caps with 0.06em tracking, padding `2px 8px`. The variants are:
  - Confidence *high*: olive fill, ivory text, label "High confidence".
  - *medium*: sage fill, ink text, label "Medium confidence".
  - *low*: warn-bg fill, warn text, 1px warn border, label "Low confidence".
  - **PLACEHOLDER**: transparent, a 1px *dashed* warn border, warn text, label "Placeholder". It sits inline right after the value and gets `title="Uses an unvalidated constant"`.
  - Status: Draft (sand/ink-soft), In review (sage-soft/ink), Approved (success-bg/success), Rejected (error-bg/error).

  Colour is never the only signal: the word is always written.
- **Explained number** (the core unit):
  - The value and unit sit on one line (tabular numbers, 600), followed by any PLACEHOLDER badge.
  - The explanation is directly below in `--fs-sm` ink-soft, max `--measure`. It is never hidden in a tooltip.
  - In templates this is one macro, `explained(n)`, which takes an `ExplainedNumber`, so it cannot render without the explanation.
- **Table**: full width, `--fs-sm`, a header row in xs caps ink-soft with a 1px rule top and bottom, row rules in `--rule`, numbers right-aligned and tabular. No zebra striping and no row cards.
- **Notice**: a 3px left rule and a tinted background, with a title (600) and a body. There is no icon font, no rounded box inside another, and no dismiss for warnings. The variants are:
  - info: sage rule on sage-soft.
  - warn: warn rule on warn-bg.
  - error: error rule on error-bg, with `role="alert"`.
  - success: success rule on success-bg.
- **Panel**: white, 1px rule, `--radius`, padding `--s5`. Used for the login form only (and optionally the review form). Never nested.

Forbidden: gradients, shadows deeper than none, nested cards, bounce/spring easing, Inter/Arial, emoji, decorative illustrations and grey text on coloured fills.

## 5. Content rules
1. Never show a number without its explanation, on screen and in the edit table. If a value has no explanation, show "—" plus "No explanation recorded" and treat it as a bug.
2. Every number with `uses_placeholder` (and every PLACEHOLDER constant) carries the dashed "Placeholder" badge. If any exist, the plan-level warn notice appears.
3. Nothing implies third-party acceptance: no "certified", "verified", "compliant", "approved by" other than our own named reviewer, no regulator or standard names, and no seals. The word "proof" refers only to our own document and hash.
4. No-soil-test plans show N only, plus the "Get a soil test for P and K" notice. P/K numbers never render in that case.
5. Units are always written out (kg N/ha, t/ha, mg/kg, cm) with the form explicit (P vs P₂O₅, K vs K₂O).
6. Mockups and screenshots for this spec use "—" for every number.
