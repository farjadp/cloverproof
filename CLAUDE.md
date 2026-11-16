# CLAUDE.md — CloverProof (formerly Rootwise)

## What this repo is
CloverProof turns farm data (field + soil test, or no test) into a complete, field-specific fertilizer decision (what, how much, when, why) plus a proof PDF. Vendor-neutral. Software only. Global core + country packs.

## Current goal (Phase 0–3, until Feb 1, 2027)
Build the INTERNAL concierge tool for our agronomist (Farjad Iranmehr). He must produce plans for 5–10 farms in Feb–Apr 2027. The farmer-facing app is NOT in scope yet.

Every plan must record: the engine output AND the agronomist's final numbers + reason. That difference is our calibration dataset. Never lose it.

## Hard rules (do not break)
1. Software only. No hardware, no sensor code.
2. Every recommendation shows a confidence level: `high` / `medium` / `low` (enum, rule-based).
3. Without a soil test: recommend N only (max `medium` confidence). For P/K, recommend a test.
4. Recommendations are IMMUTABLE. An edit creates a new version (`parent_id` + `reason`).
5. Every recommendation stores: input snapshot, engine version, country-pack version.
6. Country pack = versioned config + golden tests. Never fork code per country.
7. Internal canonical units: kg/ha, mg/kg, elemental form tracked explicitly. Always store P/K form (P vs P2O5, K vs K2O) and soil-test extraction method (Olsen / Bray-1 / Mehlich-3 / other), sampling depth and date.
8. No number goes to a farmer without agronomist approval (review gate).
9. Never invent agronomic constants. If a value is missing, use a clearly labelled `PLACEHOLDER` and add a `TODO(agronomist)` to validate.
10. No secrets in git. Use `.env` (and `.env.example` with empty values).

## Stack (Phase 0–3)
- **Hosting + database:** Railway (ADR 0004). Railway Postgres; server-only DB access. Auth/storage for the web app decided in its own ADR. (Supabase was the original choice.)
- **Engine:** pure Python package (`engine/`), no I/O, no DB calls. Fully unit-tested.
- **Internal tool:** one Python service — FastAPI + Jinja2 + HTMX (`app/`).
- **PDF:** HTML templates → WeasyPrint (`app/pdf/`), SHA-256 hash stored per document.
- **Next.js farmer app:** LATER (Phase 4). Do not create it now.
- **Out of scope now:** OCR/LLM report reading, Sentinel-2, map drawing, weather APIs, payments. Multi-language applies to the public website only (ADR 0003); the internal tool stays English.

## Build order (Farjad Iranmehr, 2026-11-16)
Website (`website/`, Next.js, 8 locales, en first) → web app portal (internal concierge tool, then farmer portal) → mobile app. One step at a time; each step is planned and approved before code. Plan: `docs/plans/website-v1.md`.

## Repo layout
```
engine/                 pure calculation library
  cloverproof_engine/
    models.py           input/output dataclasses (pydantic)
    methods/            pluggable nutrient methods (interface + implementations)
    confidence.py       rule-based confidence
    explain.py          plain-language reason for every number
    units.py            conversions (P<->P2O5, K<->K2O, lb/ac<->kg/ha)
  tests/
    golden/             agronomist-approved cases (YAML: input -> expected)
packs/
  placeholder/v0.yaml   NOT real agronomy; labelled placeholder
website/db/migrations/  SQL migrations (moves to a shared location when the web app arrives)
app/                    FastAPI internal tool + PDF templates
docs/
  adr/                  architecture decision records (one file per decision)
  sprints/              sprint plans and kickoff prompts
  audit-existing-mvp.md
```

## Data model (core)
- organisation ↔ farmer (many-to-many via `membership` with role)
- farmer → farm → field → field_geometry_version (per season)
- field → soil_test (date, depth, method, units, form, lab, source: `lab` | `estimate`)
- season → crop_plan → recommendation (immutable, `parent_id`, versions, inputs snapshot)
- recommendation → review (approve / edit / reject + reason, reviewer, `minutes_spent`)
- crop_plan → application_log (planned vs actual)
- recommendation → proof_document (pdf path, sha256, created_at)

## Key metric for the internal tool
Agronomist minutes per plan. Record it on every review.

## How to work in this repo
- Start every non-trivial task in plan mode. Show the plan before writing code.
- Small commits, one concern each. Run tests before every commit.
- Engine changes: write/extend a golden test first, then code.
- Write an ADR in `docs/adr/` for any stack or data-model decision.
- Ask before: deleting files, changing migrations already applied, adding a paid service.
- Keep code and comments in English.

## Design
UI source: Google Stitch project https://stitch.google.com/projects/16684636636144399285. Brand: #4C610B, #A7B58A, #FAF6EB, #273125.

## Agent team
Farjad Iranmehr talks to **`product-manager`** (CPO / VP Product) in a Claude desktop chat. The CPO briefs the group heads (`cto`, `head-of-mobile`, `cro`, `coo`, `head-of-data`, `cso`, `ciso`); heads brief specialists; every head reports to `documentation-manager` (Notion). Full roster and cascade: `docs/org.md`. Project agents in `.claude/agents/` override global ones with the same name.
