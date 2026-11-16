# ADR 0005 — Web app auth (agronomist role, review gate) and proof-PDF storage

- Status: PROPOSED (2026-11-16) — waiting for Farjad Iranmehr
- Decider: Farjad Iranmehr
- Related: ADR 0004 (Railway, no Supabase Auth/Storage/RLS), `docs/plans/webapp-v1.md`

## Context
ADR 0004 removed Supabase, so the internal concierge tool (`app/`, FastAPI + Jinja2 + HTMX) needs its own authentication and a place to keep proof PDFs.

Constraints:
- Phase 0–3 users: Farjad Iranmehr (agronomist + admin) and at most 2–3 staff. No farmer logins before Phase 4.
- Hard rule 8: no number reaches a farmer without agronomist approval → only the `agronomist` role can approve.
- Every review records reviewer and `minutes_spent`, so identity must be reliable and auditable.
- Proof PDFs are immutable evidence; SHA-256 is stored in `proof_document`.
- No new paid service without Farjad Iranmehr's OK. No secrets in git.

## Part A — Authentication

### Option A1 — App-owned auth in FastAPI (recommended)
`app_user` table (email, argon2id hash via `pwdlib`/`argon2-cffi`, optional TOTP secret, `disabled_at`), server-side sessions in Postgres (`user_session`, random token, HttpOnly + Secure + SameSite=Lax cookie, idle + absolute expiry), CSRF token on every HTMX POST, login rate limit. Accounts created by a CLI command (`make user-create`), no self sign-up, no email sending.
- + Free, no vendor, ~1–2 days of work, all data in our DB, easy to test.
- + Roles live where the review gate is enforced (same DB).
- − We own security: password reset (CLI only for now), lockout, session revocation. Needs a security review before Feb 1.
- − For the Phase 4 farmer portal (Next.js) we'd add OIDC or share sessions — kept possible by `app_user.auth_provider` + `external_subject` columns.

### Option A2 — Managed identity provider (Auth0 / WorkOS / Clerk) via OIDC
App redirects to the provider; we store `external_subject` → `app_user`.
- + MFA, passwordless, resets, breach detection out of the box; scales to farmers in Phase 4.
- − New vendor account and dependency on login; free tiers change; Clerk is JS-first. Overkill for ≤4 internal users. Counts as "adding a (potentially) paid service".

### Option A3 — Self-hosted OIDC (Authentik / Keycloak / Zitadel) on Railway
- + Full-featured, no vendor lock, data stays in our Railway project.
- − Another service to run, patch and back up (≈0.5–1 GB RAM, extra monthly cost); most ops for the least benefit at this size.

### Roles and the review gate (same for every option)
- Role is per organisation on `membership.role` ∈ {`owner`, `agronomist`, `staff`, `farmer`} (enum; `farmer` unused until Phase 4).
- Approving a recommendation requires `agronomist` in that recommendation's organisation, checked in the service layer **and** in the database (trigger on `review` insert with `decision = 'approve'` that checks the reviewer's membership).
- `review` rows are insert-only; `reviewer_id` comes from the session, never from the form.
- Proof PDFs can only be generated from an approved recommendation.

## Part B — Proof-PDF storage

### Option B1 — Railway Bucket (recommended)
S3-compatible private object storage inside the existing Railway project, used through `boto3`. Key: `proof/{org_id}/{recommendation_id}/{sha256}.pdf`; the app never overwrites a key; on download the app re-hashes and compares with `proof_document.sha256`. Files are served through the app (auth-checked) or short-lived presigned URLs.
- + Same platform and bill; $0.015/GB-month, S3 operations and egress free; our volume (hundreds of ~200 KB PDFs) costs cents.
- + Standard S3 API → easy to move to R2/S3 later.
- − Private only (fine — we want that); region fixed at creation; adds usage cost on the Railway bill (needs OK under the "paid service" rule).
- Source: https://docs.railway.com/storage-buckets, https://docs.railway.com/storage-buckets/billing

### Option B2 — PDF bytes in Postgres (`bytea` on `proof_document`)
- + Zero new infrastructure; file and hash written in one transaction; included in DB backups.
- − Bloats the database and backups as volume grows; must move out before Phase 4 farmer downloads.

### Option B3 — Railway volume on the app service
- − Ties files to one service instance, blocks replicas, backups are manual. Not recommended.

Local dev and tests use a filesystem implementation behind the same `ProofStore` interface (`put(key, bytes) -> sha256`, `get(key)`), so the backend can change without touching PDF code.

## Recommendation
**A1 + B1.** App-owned auth fits ≤4 internal users at zero cost and keeps the review gate next to the data; Railway Bucket keeps PDFs on the platform we already use. Revisit auth (A2 or A3) when the Phase 4 farmer portal opens.

## Consequences
- New tables: `app_user`, `user_session` (Step 4 migrations, ADR 0002).
- New env vars (empty in `.env.example`): `SESSION_SECRET`, `BUCKET_ENDPOINT`, `BUCKET_NAME`, `BUCKET_ACCESS_KEY_ID`, `BUCKET_SECRET_ACCESS_KEY`, `BUCKET_REGION`.
- Security review of login, sessions and CSRF is part of the Step 7 release gate.
- `cp-concierge-app` and `cp-platform` agent files must drop "Supabase auth".
