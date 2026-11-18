# Runbook — website admin (`/admin`)

ADR 0012 (auth), 0013 (secrets), 0014 (system log). Plan: `docs/plans/website-admin.md`.
**Nothing here is done yet in production.** Each step needs Farjad Iranmehr's go and happens with his DB setup (after the DB switch).

## 1. Environment variables (website service)
Names only — values go in Railway variables, never in git. `.env.example` must list these names with empty values (to add: the env example files are not editable by agents).

| Name | Value |
|---|---|
| `ADMIN_DATABASE_URL` | URL for the `cp_website_admin_login` role (not the public site's `DATABASE_URL`) |
| `WEBSITE_SECRETS_KEK` | 32 random bytes, base64: `openssl rand -base64 32` |
| `WEBSITE_SECRETS_KEK_ID` | **required, no default**: short id for that key, e.g. `k2026a` (letters, digits, `_ . -`). Use a new id for every new key |
| `WEBSITE_ADMIN_HMAC_KEY` | 32 random bytes, base64 (rate-limit keys, CSRF, recovery codes) |
| `WEBSITE_SECRETS_KEK_PREVIOUS`, `WEBSITE_SECRETS_KEK_PREVIOUS_ID` | only during a KEK rotation; both or neither. The id must differ from `WEBSITE_SECRETS_KEK_ID` (the site refuses to start the admin otherwise) |
| `ADMIN_MFA_OPTIONAL` | **normally unset.** Only the exact value `true` makes two-step sign-in optional for accounts that have not enrolled (§7). Anything else keeps it required |
| `TRUSTED_PROXY_HEADER` | **leave empty** until the staging probe in §5 passes; then the one header Railway sets with the client IP (e.g. `X-Real-IP`) |

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
With `ADMIN_MFA_OPTIONAL=true` the QR step is skipped at sign-in; set it up from the dashboard (§7).
The CLI refuses a second admin unless `--additional` is given; later users are invited from the admin.

## 4. Lost phone / locked out
- Use a recovery code on the two-step screen (each works once).
- Editors and authors: an admin uses Users → "Reset two-step sign-in" and/or "Password reset link".
- Admins: only the operator CLI below (the admin UI never lets one admin reset another admin's sign-in).
- 5 wrong passwords in 15 minutes: that e-mail is throttled until the 15-minute window ends; the account is not locked.
- 5 wrong two-step codes (or recovery codes): the account locks (15 min, doubling up to 24 h) and every session ends. The lock lifts by itself.
- Last resort (only admin, no recovery codes), operator in the website shell:
  ```bash
  npm run admin:reset -- --email <email> --mfa
  ```
  Clears two-step sign-in and recovery codes, unlocks, ends all sessions, prints a 1-hour password link. Logged as `user.reset_mfa` via `cli`.

## 5. Client IP behind Railway
The admin reads the client IP from one header only, named in `TRUSTED_PROXY_HEADER` (A-S2). It is **empty by default**, which means:
- the per-IP sign-in limit (20 failures per 15 min per prefix) is off;
- the log stores no IP prefix;
- the per-e-mail throttle and the second-factor lock still apply.

To turn it on:
1. On staging, sign in with a wrong password while sending `X-Real-IP: 6.6.6.6` and `X-Forwarded-For: 6.6.6.6`.
2. In the system log, check that the prefix is your real `/24`, not `6.6.6.0/24`.
3. Only if it is, set `TRUSTED_PROXY_HEADER` to the header that carried your real address and redeploy.

With `X-Forwarded-For`, only the last entry is used. Any other header must hold exactly one IP; otherwise no IP is used. Production stays empty until the probe passes.

## 6. API keys and the master key (ADR 0013)
- Keys are entered on `/admin/keys` (admin, fresh code). After saving only the last 4 characters are shown. Removing a key here wipes its ciphertext; also revoke it in the provider's console.
- **Master-key rotation** (e.g. if `WEBSITE_SECRETS_KEK` may have leaked). It covers the API keys **and** every admin's two-step sign-in secret, in one transaction. Order:
  1. In Railway, set `WEBSITE_SECRETS_KEK_PREVIOUS` and `WEBSITE_SECRETS_KEK_PREVIOUS_ID` to the **current** key and id. Then set `WEBSITE_SECRETS_KEK` to a new key (`openssl rand -base64 32`) and `WEBSITE_SECRETS_KEK_ID` to a **new** id.
  2. **Redeploy** the website. The running site can then open values under either key, and every replica seals new values under the new key.
  3. In the website service shell, run `npm run secrets:rewrap`. Wait for "Rotation complete". The command re-seals everything under the new key in one transaction, then checks that no active value is still under the old id and that each opens with the new key alone. If not, it rolls back and changes nothing.
  4. Only after "Rotation complete": delete the two `_PREVIOUS` variables and redeploy. Keep the old key in the password manager for a few days.
  5. If a leak is suspected, also rotate the provider keys themselves.

## 7. Optional two-step sign-in (`ADMIN_MFA_OPTIONAL`, ADR 0012 amendment 2026-11-18)
Decided by Farjad Iranmehr on 2026-11-18, with the risks listed in the ADR. Required is the default. `ciso` proposes removing the flag by 2026-11-25, 2026-12-02 at the latest, or sooner on a second account, the first provider key, blog or media admin, or any pilot or farmer data in the admin. These are proposals: nothing expires by itself.

**Turn on:** set `ADMIN_MFA_OPTIONAL` to `true` (lower case, nothing else) on the website service and let it redeploy. Check:
1. Sign in: you land on the dashboard, which says "Two-step sign-in is off".
2. `/admin/keys` and `/admin/users` say "Closed for now". So does the export section of `/admin/log`.
3. System log: the sign-in shows as `login.password_only`, `via: mfa_optional`.

**While it is on:**
- Accounts with two-step sign-in enrolled still need their code at sign-in.
- Users, API keys and log export are closed for **every** account, enrolled or not. To use them, finish the exit below.
- There is no alert. Read the system log for `login.password_only` at unexpected times and for any `mfa.enrol` you did not do. Without `TRUSTED_PROXY_HEADER` (§5) the log has no IP prefix, so time and browser are all you have.
- An unexpected `mfa.enrol`, or being asked for a code you never set up, means someone else has the password: run the exit below now.
- Five wrong codes on the enrolment screen lock the account (15 min, doubling up to 24 h). `admin:reset` clears the lock.

**Turn off (the goal). Keep this order, without a pause between steps 1 and 2:**
1. Operator, in the website service shell: `npm run admin:reset -- --email <email> --mfa`. It clears two-step sign-in and any pending secret, unlocks the account, ends all sessions and prints a one-time password link (1 hour). The old password keeps working until the link is used, so use it at once.
2. Open the link and set a **new, unique** password from the password manager. Sign in, go straight to `/admin/mfa`, enrol, and save the recovery codes. If a code is requested before you have enrolled, stop and go back to step 1.
3. Sign out, then sign in with the password and a code.
4. Delete `ADMIN_MFA_OPTIONAL` and let the site redeploy. Users, API keys and log export open again, each behind a fresh code.

If the variable is removed before anyone has enrolled, the next page load goes to the forced enrolment screen, as before.
