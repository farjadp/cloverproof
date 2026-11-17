# ADR 0013 — Website system log and 60-day retention (DRAFT)

- Status: **Proposed** (2026-11-17) — needs `ciso` review and Farjad Iranmehr's decision; `coo` for privacy wording
- Decider: Farjad Iranmehr · Author: `cp-website`
- Related: ADR 0010 (site_event, separate), ADR 0011, ADR 0012, `docs/plans/website-admin.md` (P1)
- Number provisional.

## Context
The admin needs a system log of logins, admin actions, content changes, API-key changes and errors, kept **60 days then deleted automatically** by a tested, scheduled job. No new Railway service (cost) without Farjad Iranmehr's go; the S4 Procrastinate worker doesn't exist yet.

## What is logged
One table `website_log`: `occurred_at`, `actor_user_id` (null for anonymous/system), `kind` (auth | admin | content | secret | error | job), `action`, `target_type/id`, `outcome` (ok | denied | failed), `ip_prefix` (IPv4 /24, IPv6 /48 — not the full IP), `ua_family` (e.g. "Firefox"), `detail` jsonb with **whitelisted keys only**. Never: passwords, tokens, keys, TOTP codes, post bodies, form values, emails of non-users, full URLs with query strings. Errors use the existing `safeError()` redaction (name, SQLSTATE, table/constraint, masked message) and record path only. Public-site errors carry no IP prefix.

Append-only: `cp_website_admin` has INSERT and SELECT only. Deletion only via `website_log_purge()` (`security definer`, owned by a purge role): `delete from website_log where occurred_at < now() - interval '60 days'`, returns the count. Also purges expired sessions, used/expired one-time tokens and old rate-limit rows.

## Scheduling options
### A — In-process daily job in the Next.js service (recommended now)
`instrumentation.ts` `register()` (Node runtime only) starts an hourly timer; each tick takes `pg_try_advisory_lock`, runs the purge if the last successful run was > 23 h ago, writes `website_job_run` (`last_ok_at` / `last_error`) and a `kind=job` log row with the count. Admin dashboard warns if `last_ok_at` > 26 h. The log viewer also filters to the last 60 days, so an overdue purge never shows older rows.
+ No new service, no cost. − Runs only while the website runs (always-on on Railway); timer per replica (advisory lock prevents double runs).

### B — S4 Procrastinate worker (Python, web app)
+ Proper periodic job infrastructure shared with site_event rollup. − Not available until S4; cross-team dependency. **Planned move** when it exists (same SQL function, so only the caller changes).

### C — Railway cron service / pg_cron
− Cron service = new Railway service (cost → ask); `pg_cron` isn't in the `postgis/postgis` image by default.

## Decision (proposed)
A now, B when the worker lands.

## Tests
Purge deletes rows at 60 d + 1 s, keeps 59 d 23 h; idempotent; lock prevents concurrent runs; health row updated on success and failure; `cp_website_admin` cannot DELETE/UPDATE directly; `detail` whitelist drops unknown keys; no secret/token appears in any log row in the e2e suite.

## Privacy
Holds staff personal data (user id, truncated IP, browser family) and, for failed `/admin` logins, a truncated IP of whoever tried. Truncated IP kept as designed (Farjad Iranmehr, 2026-11-17). `coo` decides whether the public privacy notice needs a sentence ("security logs of the private admin area, kept 60 days") and drafts an internal staff notice. Not shipped until worded.
