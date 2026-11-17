# Runbook — website admin (`/admin`)

ADR 0012 (auth), 0013 (secrets), 0014 (system log). Plan: `docs/plans/website-admin.md`.
**Nothing here is done yet in production.** Each step needs Farjad Iranmehr's go and happens with his DB setup (after the DB switch).

## 1. Environment variables (website service)
Names only — values go in Railway variables, never in git. `.env.example` must list these names with empty values (to add: the env example files are not editable by agents).

| Name | Value |
|---|---|
| `ADMIN_DATABASE_URL` | URL for the `cp_website_admin_login` role (not the public site's `DATABASE_URL`) |
| `WEBSITE_SECRETS_KEK` | 32 random bytes, base64: `openssl rand -base64 32` |
| `WEBSITE_SECRETS_KEK_ID` | short id for that key, e.g. `k2026a` |
| `WEBSITE_ADMIN_HMAC_KEY` | 32 random bytes, base64 (rate-limit keys, CSRF, recovery codes) |
| `WEBSITE_SECRETS_KEK_PREVIOUS`, `WEBSITE_SECRETS_KEK_PREVIOUS_ID` | only during a KEK rotation |

Keep a copy of `WEBSITE_SECRETS_KEK` in Farjad Iranmehr's password manager. Losing it means every enrolled two-step sign-in (and later every API key) must be set up again.
Without these variables `/admin` shows "Admin not configured" and the public site is unaffected.

## 2. Database login (operator, once, after migration 0024)
```sql
create role cp_website_admin_login login password '<generated>' connection limit 10 in role cp_website_admin;
alter role cp_website_admin_login set statement_timeout = '10s';
alter role cp_website_admin_login set lock_timeout = '2s';
alter role cp_website_admin_login set idle_in_transaction_session_timeout = '30s';
```

## 3. First admin (Farjad Iranmehr only, decided 2026-11-17)
In the website service shell:
```bash
npm run admin:create -- --email <his email> --name "Farjad Iranmehr"
```
It prints a one-time link (72 h; the token is in the `#fragment`, so it never reaches server logs). Open it, set a password (≥ 12 characters), sign in, scan the QR code, save the 10 recovery codes.
The CLI refuses a second admin unless `--additional` is given; later users are invited from the admin.

## 4. Lost phone / locked out
- Use a recovery code on the two-step screen (each works once).
- Editors and authors: an admin uses Users → "Reset two-step sign-in" and/or "Password reset link".
- Admins: only the operator CLI below (the admin UI never lets one admin reset another admin's sign-in).
- Locked after 5 wrong passwords or codes: the lock lifts by itself (15 min, doubling up to 24 h); every session ends when codes lock it.
- Last resort (only admin, no recovery codes), operator in the website shell:
  ```bash
  npm run admin:reset -- --email <email> --mfa
  ```
  Clears two-step sign-in and recovery codes, unlocks, ends all sessions, prints a 1-hour password link. Logged as `user.reset_mfa` via `cli`.

## 5. Client IP behind Railway
The log stores only an IP prefix. `X-Real-IP` is used, else the last `X-Forwarded-For` entry. Before relying on the per-IP limit, check on staging that a spoofed `X-Forwarded-For: 6.6.6.6` does not appear as `6.6.6.0/24` in the log.

## 6. API keys and the master key (ADR 0013)
- Keys are entered on `/admin/keys` (admin, fresh code). After saving only the last 4 characters are shown. Removing a key here wipes its ciphertext; also revoke it in the provider's console.
- Master-key rotation (e.g. if `WEBSITE_SECRETS_KEK` may have leaked): set the new key as `WEBSITE_SECRETS_KEK`/`_ID`, the old one as `WEBSITE_SECRETS_KEK_PREVIOUS`/`_ID`, run `npm run secrets:rewrap` in the website shell, then delete the `_PREVIOUS` variables. Also rotate the provider keys themselves if a leak is suspected.
