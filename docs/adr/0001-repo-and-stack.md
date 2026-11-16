# ADR 0001 — Start fresh in this monorepo

- Status: Accepted (2026-11-16)
- Decider: Farjad Iranmehr

## Context
Sprint 1 Step 1 was to audit the existing Rootwise MVP and decide whether to reuse it or start this monorepo.

## Decision
There is no existing Rootwise MVP code to reuse. CloverProof starts fresh in `farjadp/cloverproof`. The Step 1 audit is skipped; no `docs/audit-existing-mvp.md` is produced.

Stack is as in CLAUDE.md, with hosting per ADR 0004 (Railway, Railway Postgres) and web-app auth/storage per ADR 0005.

## Consequences
- No legacy code, constants or data to port; every agronomic constant starts as `PLACEHOLDER` + `TODO(agronomist)`.
- Step 2 (scaffold) is the first build step of the web app plan (`docs/plans/webapp-v1.md`).
