# ADR 0013 — Website integration secrets (AI provider API keys) (DRAFT)

- Status: **Accepted** by Farjad Iranmehr (2026-11-17). `ciso` review: PASS with findings, fixes merged (#69, #70). No `WEBSITE_SECRETS_KEK` and no provider keys in production until P4 opens (CPO decision 2026-11-17, build order P1 → P3 → P2 → P4).
- Decider: Farjad Iranmehr · Author: `cp-website`
- Related: ADR 0012, `docs/plans/website-admin.md` (P2), CLAUDE.md rules 10 and 12

## Context
The admin must hold API keys for Anthropic (Claude), Google (Gemini), OpenAI and fal for future content agents (P4). Brief: encrypted at rest in Postgres with envelope encryption, master key in an env var (never git/DB), write-only UI (mask + last 4 + test connection), admin-only, every change logged, server-side use only, per-provider monthly budget cap.

## Options
### A — Envelope encryption in the app with `node:crypto` (recommended)
- Master key (KEK): 32 random bytes, base64, env `WEBSITE_SECRETS_KEK`, plus `WEBSITE_SECRETS_KEK_ID`. Set by Farjad Iranmehr in Railway variables and kept in his password manager. Never logged; `.env.example` has the empty name.
- Per secret: random 32-byte data key (DEK) → AES-256-GCM encrypts the API key (12-byte random IV, 16-byte tag, AAD = `provider|row id|version`) → DEK wrapped with the KEK by AES-256-GCM (own IV/tag). Store ciphertext, IVs, tags, wrapped DEK, `kek_id`, `last4`.
- Rotation: new KEK as `WEBSITE_SECRETS_KEK` (+ `_ID`), old one as `WEBSITE_SECRETS_KEK_PREVIOUS` (+ `_ID`) → `npm run secrets:rewrap` re-seals every *active* key under the new KEK in one transaction → remove the old KEK. The DB allows re-sealing only together with a new `kek_id`. Tested. Amended after the S3 review (D-S2): both KEK ids are required with no default and must differ; the rewrap runs after a redeploy and refuses to commit unless every active value is under the new id and opens with the new KEK alone. The same rewrap also re-seals every `website_user.mfa_secret_enc` (TOTP secrets, enrolled or pending) in the same transaction (D-S1); the CLI reports both counts.
- Write-only: no route, action, RSC prop or log ever returns plaintext. The UI shows `provider · ••••last4 · added by/at · last test result`. Replace = insert new version and revoke the old; a revoked row keeps its metadata but its sealed bytes are replaced by a tombstone in the same statement (enforced by trigger), so nothing is recoverable even with the KEK. Decrypt only in `src/lib/admin/keys.ts` (`server-only`), used by "test connection" and later the agent worker.
- Test connection: one cheap authenticated read per provider (list models for Anthropic/OpenAI/Gemini; fal's lightest authenticated endpoint, confirmed in P2), 10 s timeout, result + HTTP status logged, never the key or response body.
- Budget: `monthly_budget_usd` per provider (nullable). Enforcement is P4 (`website_ai_usage` ledger; jobs refuse to start when the month's cost ≥ cap).
- Same envelope used for TOTP secrets (ADR 0012).
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
