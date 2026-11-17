# ADR 0012 — Website admin authentication and roles (DRAFT)

- Status: **Accepted** by Farjad Iranmehr (2026-11-17), option A (same service, `/admin`). `ciso` review: PASS with findings, fixes merged (#67–#70); see `docs/security/S3-review-website-admin-p1.md` and `S3-review-website-admin-p1-fixes.md`.
- Decider: Farjad Iranmehr · Author: `cp-website`
- Related: ADR 0003 (website stack), ADR 0005 (web-app auth, separate), ADR 0007 (DB privileges), `docs/plans/website-admin.md`

## Context
The website needs a private admin for staff (users, system log, API keys, blog). These accounts are **website** accounts, separate from the web app's farmers/agronomists (ADR 0005). Requirements from the CPO: app-owned auth, argon2id, server-side sessions, CSRF, rate limit, MFA required for admins, no self sign-up, first admin via CLI, Next.js 16 route handlers/server actions. ≤ 5 users for the foreseeable future. No email provider exists.

## Options
### A — App-owned auth inside the Next.js website (recommended; matches the brief)
- argon2id via `@node-rs/argon2` (MIT; prebuilt binaries) — m=19 MiB, t=2, p=1 (OWASP 2024 baseline), rehash on login when parameters change.
- DB sessions: 32-byte random token in cookie `__Host-cp_admin` (HttpOnly, Secure, SameSite=Strict, Path=/); only `sha256(token)` stored. Idle 30 min, absolute 12 h, rotate token on login and privilege change, revoke all on password/MFA reset or disable.
- MFA: TOTP (RFC 6238, SHA-1, 6 digits, 30 s, ±1 step) implemented on `node:crypto` and tested against RFC vectors (no dependency) or `otplib` (MIT); QR via `qrcode` (MIT). Enrolment forced at first login for **every** admin-area role (admin, editor, author) — simpler than per-role and the brief says admins must have it. 10 single-use recovery codes (hashed). Secret stored encrypted (ADR 0013 envelope).
- Step-up: actions on keys, roles, user delete and MFA reset need a fresh TOTP within 5 min (`step_up_at`).
- CSRF: per-session token (hash stored) in a hidden field on every form and checked in every server action/route handler, **plus** Next's built-in Origin/Host check and SameSite=Strict.
- Rate limit / lockout: Postgres counters keyed by HMAC(email) and HMAC(ip /24): wrong passwords: 5/15 min per e-mail → that e-mail is throttled for the rest of the window (no account lock, amended after the S3 review, A-S1); wrong second-factor codes: 5 → account lock 15 min (doubling, max 24 h) and every session ends; 20/15 min per IP prefix, only when the operator names the one trusted client-IP header (`TRUSTED_PROXY_HEADER`, empty by default = per-IP limit off; amended after the S3 review, A-S2). Same generic error for unknown user / wrong password / locked (no enumeration); constant-time compares.
- Every server action and route handler calls `requireRole()` from a `server-only` data-access layer (Next docs: actions are reachable by direct POST). `proxy.ts` does only an optimistic cookie-presence redirect.
- Invites/resets: admin creates a one-time link (32-byte token, hash stored; invite 72 h, password reset 1 h, MFA reset 1 h), shown once to the admin, handed over out of band. No email sending.
- CLI: `npm run admin:create -- --email … --name …` run in the Railway service shell; prints a one-time setup link; refuses if an admin already exists unless `--additional` and logs to `website_log`. First admin: Farjad Iranmehr only (decided 2026-11-17); no editors/authors yet.
- + No vendor, no cost, data in our DB, matches the brief. − We own security; duplicates the web-app auth design in a second language/framework.

### B — Reuse the FastAPI web-app auth (ADR 0005) for website staff
Website admin pages would be served by `app/`, or Next would trust an `app/` session. + One auth system to secure. − Mixes website staff with the farmer/agronomist identity system the brief wants separate; the editor (React) fits poorly in Jinja/HTMX; couples website releases to the web app.

### C — Managed IdP (Auth0/WorkOS/Clerk) or self-hosted OIDC
− New (potentially paid) service or a new Railway service; overkill for ≤ 5 users.

## Roles
| Action | admin | editor | author |
|---|---|---|---|
| Users: invite, role, disable/enable, reset, delete | ✓ | – | – |
| System log: view, export | ✓ | – | – |
| API keys: view mask, add/replace/revoke, test, budget | ✓ | – | – |
| Posts: create/edit own drafts, submit for review | ✓ | ✓ | ✓ |
| Posts: edit any, publish, schedule, unpublish | ✓ | ✓ | – |
| Authors, tags, media library | ✓ | ✓ | upload only |
The last active admin cannot be demoted, disabled or deleted. Delete = remove credentials, sessions, MFA, recovery codes; set `deleted_at`, null the email, keep `id` + display name so log rows and revisions still resolve (log rows age out after 60 days).

## Decision (proposed)
Option A.

## Consequences
- New tables `website_user`, `website_session`, `website_user_recovery_code`, `website_one_time_token`, `website_rate_limit` via `db/migrations/` (`cp-database`).
- New DB role `cp_website_admin` (+ login) and env `ADMIN_DATABASE_URL`; public pages keep `cp_website`.
- `/admin` excluded from locale redirect, sitemap, robots; `noindex`, `no-store`, strict CSP with nonce, `frame-ancestors 'none'`.
- `ciso` security checklist before P1 go (plan §8).
