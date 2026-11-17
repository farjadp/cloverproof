# ADR 0010 — `site_event`: first-party website events

- Status: Accepted (2026-11-16) — retention approved by Farjad Iranmehr (2026-11-16)
- Decider: Farjad Iranmehr (CPO chose option A in the growth brief)
- Related: `docs/growth/landing-tracking-brief.md` §3/§5/§9, `docs/plans/website-v1.md` item 4, `docs/operations/legal/website-measurement-review.md` (C2, C4, C5, C10), ADR 0007, `db/migrations/0013_site_event.sql`

## Context
The pilot funnel before the form (page view → field check → form steps) is not measured. The CPO chose first-party events in our own Postgres (no vendor, no cookies, no device storage). The website plan adds: no `country`, events only from `en`, `fr`, `es`, `it`, `tr`, the server drops every non-whitelisted field.

## Decision
One table `site_event`, owned by `cp_migrator`, with a column only for each property in the brief's §5 whitelist:
`id`, `occurred_at` (server `now()`), `view_id` (uuid, nullable), `event`, `locale`, `path`, `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `referrer_host`, `device`, and the per-event extras `question`, `answer`, `step`, `result_type` (spec `type`), `gaps`, `cta_location` (spec `location`), `form_step` (spec `n`), `check_scope`, `error_reason` (spec `reason`), plus `is_test` (data M7, team traffic).

- CHECK constraints: `event` in the 13 spec names; `locale` in en/fr/es/it/tr; `path` ≤ 200 chars, starts with `/`, no query/fragment/scheme; `utm_*` ≤ 100 chars, lowercase `[a-z0-9._-]`; `referrer_host` a lowercase DNS name ≤ 253 (no scheme, port, path, bare IP); `device` mobile/desktop; every extra is an enum or a small range and is allowed only on its own event (required where the event needs it).
- No column for IP, country, user-agent string, full referrer URL, email, names, form values or `pilot_request.id`. No join key to `pilot_request` (legal C10).
- Grants: `cp_website` column-level INSERT on the whitelisted columns only (not `id`, not `occurred_at`). No SELECT, UPDATE, DELETE or TRUNCATE. `cp_app` and `cp_admin`: nothing. Reports will read through a future read-only analytics role (not created now); until then an operator queries as the owner.

## Privacy rationale
Nothing stored can identify, locate or profile a person: `view_id` dies with the page, the IP is used in transit for bot filtering only, country is not collected (Quebec P-39.1 s. 8.1 risk), and the locale gate keeps fi/bg/ar out until legal confirms. The database enforces this, so a collector bug cannot widen what is stored. The website cannot read events back, so a compromised website leaks nothing.

## Retention (approved by Farjad Iranmehr, 2026-11-16)
Decision: 90 days raw, daily counts up to 25 months. Matches the legal review (C4/C5) and the draft privacy notice: raw rows **90 days** from `occurred_at`, then rolled into daily counts (no `view_id`) and deleted; daily counts kept **up to 25 months**, reviewed yearly. Data's M7 proposed 12 months raw; 90 days is the stricter option and covers the recruit window to 2027-01-15. The rollup + purge will be a scheduled worker job (future; not built). Index `site_event_occurred_at_idx` supports it. Until that job exists nothing is deleted: it must ship before day 90 of live events.

## Consequences for `cp-website`
- Connect as `cp_website_login`. Use plain `INSERT` without `RETURNING` (no SELECT grant; `RETURNING` fails with permission denied). Do not send `id` or `occurred_at`.
- The collector keeps only whitelisted keys, maps spec names to columns (`type`, `location`, `n`, `reason`), lowercases UTM values, trims the referrer to its host, strips the query string from `path`, and drops everything else before the insert. A CHECK violation means the payload was bad: answer 204 or 400 and never log the payload.
- No events from fi/bg/ar (the CHECK refuses them); honour GPC/DNT client-side (legal C2).
- `form_submit_success` / `form_submit_error` are inserted server-side in `requestPilot`, after the `pilot_request` insert; never on honeypot hits.

## Consequences
- New events or properties need a migration (deliberate: the whitelist lives in the schema).
- Reports and the purge job need the analytics role and the worker; both are open.
