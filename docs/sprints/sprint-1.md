# Sprint 1 — Nov 16–27, 2026

Run in order. One session per step. Plan mode first for each step. Owner agent in brackets; `cloverproof-lead` dispatches.

| # | Step | Owner | Exit |
|---|------|-------|------|
| 1 | Audit the existing MVP (read-only) | `cp-auditor` | `docs/audit-existing-mvp.md` + Farjad Iranmehr's decision in `docs/adr/0001-repo-and-stack.md` |
| 2 | Scaffold the monorepo | `cp-platform` | `make test` and CI green on an empty test |
| 3 | Engine v0 (test-first) | `cp-engine` + `cp-agronomy-guard` | Unit tests pass; golden report runs; sample cases replaced by Farjad Iranmehr's 5 real cases |
| 4 | Database schema | `cp-database` | Migrations apply on local Supabase; RLS tested with two users; ADR 0002 |
| 5 | Internal concierge tool | `cp-concierge-app` | Farjad Iranmehr enters one case end to end without help |
| 6 | Proof PDF v0 | `cp-pdf` | 5 plans done; engine-vs-agronomist diff saved for each; avg minutes/plan measured |

## Step 1 — Audit the existing MVP (read-only)
Read CLAUDE.md. Then audit the existing codebase. Do NOT change any code. Produce `docs/audit-existing-mvp.md` with:
1. Stack, structure, and how to run it locally.
2. Table of the 11 MVP features in CLAUDE.md scope + the brief: exists / partial / missing, with file paths.
3. Any nutrient calculation: method, constants, and where each number comes from. Flag every constant with no source.
4. Data model vs the core model in CLAUDE.md: gaps and conflicts.
5. Keep / rewrite / drop table with a one-line reason each.
6. Recommendation: reuse that repo, or start this monorepo and port specific parts.

Exit: Farjad Iranmehr reads the audit and decides keep vs new repo → `docs/adr/0001-repo-and-stack.md`.

> Open input: path or GitHub URL of the existing MVP (Rootwise) codebase.

## Step 2 — Scaffold the monorepo
Python 3.12, uv, ruff, pytest, pre-commit. `.env.example`, Makefile (`make test`, `make dev`, `make lint`), GitHub Actions CI (lint + tests). No business logic.

## Step 3 — Engine v0 (test-first)
Wheat, nitrogen only, simple mass-balance method behind a `NutrientMethod` interface. Inputs: crop, target yield, previous crop, soil test (optional), area. Outputs: N rate (kg/ha), total quantity, split plan, explanation for every number, confidence enum, engine version, pack version. Constants from `packs/placeholder/v0.yaml`, every one marked PLACEHOLDER. `units.py` with tested conversions. Golden-test loader reads `tests/golden/*.yaml` and reports the difference vs expected (report, don't fail, for now).

## Step 4 — Database schema
Supabase migrations for the core model. PostGIS for geometry. Recommendations immutable (no UPDATE policy; edits = new row with `parent_id`). RLS by organisation via membership. Seed: 1 org, 1 farmer, 2 fields. ADR 0002.

## Step 5 — Internal concierge tool
FastAPI + Jinja + HTMX: farmer/field list → new plan form (area manual, soil test incl. method/depth/form/units, crop, target yield, previous crop) → run engine → suggestion with explanations + confidence → agronomist edits numbers + reason → saved as new version → review status. Minutes-per-plan timer. Supabase auth. Only the agronomist role can approve.

## Step 6 — Proof PDF v0
WeasyPrint from HTML: field, inputs, recommendation, splits, timing window (text), explanation per number, confidence, engine + pack versions, reviewer and date; SHA-256 stored in `proof_document`. English only. Brand colours #4C610B, #A7B58A, #FAF6EB, #273125. No claims that third parties "accept" the document.
