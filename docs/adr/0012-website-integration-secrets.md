# ADR 0012 — Website integration secrets (AI provider API keys) (DRAFT)

- Status: **Proposed** (2026-11-17) — needs `ciso` review and Farjad Iranmehr's decision
- Decider: Farjad Iranmehr · Author: `cp-website`
- Related: ADR 0011, `docs/plans/website-admin.md` (P2), CLAUDE.md rules 10 and 12
- Number provisional.

## Context
The admin must hold API keys for Anthropic (Claude), Google (Gemini), OpenAI and fal for future content agents (P4). Brief: encrypted at rest in Postgres with envelope encryption, master key in an env var (never git/DB), write-only UI (mask + last 4 + test connection), admin-only, every change logged, server-side use only, per-provider monthly budget cap.

## Options
### A — Envelope encryption in the app with `node:crypto` (recommended)
- Master key (KEK): 32 random bytes, base64, env `WEBSITE_SECRETS_KEK`, plus `WEBSITE_SECRETS_KEK_ID`. Set by Farjad Iranmehr in Railway variables and kept in his password manager. Never logged; `.env.example` has the empty name.
- Per secret: random 32-byte data key (DEK) → AES-256-GCM encrypts the API key (12-byte random IV, 16-byte tag, AAD = `provider|row id|version`) → DEK wrapped with the KEK by AES-256-GCM (own IV/tag). Store ciphertext, IVs, tags, wrapped DEK, `kek_id`, `last4`.
- Rotation: new KEK id in env alongside the old → CLI `npm run secrets:rewrap` re-wraps every DEK → remove old KEK. Tested.
- Write-only: no route, action, RSC prop or log ever returns plaintext. The UI shows `provider · ••••last4 · added by/at · last test result`. Replace = insert new version and revoke the old (history kept, no plaintext). Decrypt only in `src/lib/integrations/secret-store.ts` (`server-only`), used by "test connection" and later the agent worker.
- Test connection: one cheap authenticated read per provider (list models for Anthropic/OpenAI/Gemini; fal's lightest authenticated endpoint, confirmed in P2), 10 s timeout, result + HTTP status logged, never the key or response body.
- Budget: `monthly_budget_usd` per provider (nullable). Enforcement is P4 (`website_ai_usage` ledger; jobs refuse to start when the month's cost ≥ cap).
- Same envelope used for TOTP secrets (ADR 0011).
- + No new service, no cost, testable. − Key is in the app process memory when used; KEK in env is readable by anyone with Railway project access.

### B — External KMS / secret manager (AWS KMS, GCP KMS, Vault, Doppler)
+ KEK never in app env; audit in the KMS. − New (paid) service + credentials to manage anyway; overkill now. Revisit if staff with Railway access grows.

### C — Keys only as Railway env variables (no DB)
+ Simplest. − Not manageable from the admin, no history/audit, needs redeploy to change; doesn't meet the brief.

## Decision (proposed)
Option A. P2 timing decided (Farjad Iranmehr, 2026-11-17): built after P3, just before P4.

## Consequences
- Table `website_secret` (one active row per provider), grants: `cp_website_admin` only; `cp_website` no access.
- Every add/replace/revoke/test/budget change → `website_log` (`kind=secret`, provider, last4, outcome; never the key).
- Tests: round trip, tamper (ciphertext/tag/AAD) fails, wrong KEK fails, rewrap, key absent from HTML/RSC/network/logs/build output.
- Rule 12: the key is used only by jobs that never read farmer data (DB role has no grant on `pilot_request`, `site_event` or web-app tables).
