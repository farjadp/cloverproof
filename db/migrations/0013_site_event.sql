-- site_event: first-party website measurement (ADR 0010; CPO option A, growth brief
-- landing-tracking-brief.md §3/§5; website plan: no country, events only from en/fr/es/it/tr).
--
-- Only the brief's §5 whitelist has a column. There is deliberately NO column for an IP
-- address, country, user-agent string, full referrer URL, email, name, form values or
-- pilot_request.id, and no join key to pilot_request (view_id never goes on that table).
-- The collector (website POST /api/e) drops every other property before inserting.
--
-- Writers: cp_website (column INSERT only; no SELECT, so no RETURNING; id and occurred_at
-- are server defaults it cannot set). cp_app and cp_admin: nothing. Reads for reports go
-- through a future read-only analytics role (not created here).
--
-- Retention (approved by Farjad Iranmehr 2026-11-16; ADR 0010): raw rows 90 days from
-- occurred_at, then rolled into daily counts without view_id and deleted; daily counts kept
-- up to 25 months. The purge/rollup is a future worker job; nothing deletes rows yet.
set local role cp_migrator;

create table site_event (
  id            uuid primary key default gen_random_uuid(),
  occurred_at   timestamptz not null default now(),
  -- Random uuid v4 made in browser memory per page load; never stored on the device.
  -- Null for server-side events that were not given one.
  view_id       uuid,
  event         text not null check (event in (
                  'page_view', 'check_view', 'check_start', 'check_answer', 'check_back',
                  'check_result', 'check_restart', 'check_cta_click', 'cta_click',
                  'form_step', 'form_back', 'form_submit_success', 'form_submit_error')),
  -- Locale gate: fi, bg, ar send nothing until legal confirms (website plan item 4).
  locale        text not null check (locale in ('en', 'fr', 'es', 'it', 'tr')),
  -- Path only: no scheme, host, query string or fragment.
  path          text not null check (char_length(path) <= 200 and path ~ '^/[A-Za-z0-9/._-]*$'),
  -- UTM codes: lowercase, no spaces (brief §6), at most 100 chars.
  utm_source    text check (char_length(utm_source) <= 100 and utm_source ~ '^[a-z0-9._-]+$'),
  utm_medium    text check (char_length(utm_medium) <= 100 and utm_medium ~ '^[a-z0-9._-]+$'),
  utm_campaign  text check (char_length(utm_campaign) <= 100
                            and utm_campaign ~ '^[a-z0-9._-]+$'),
  utm_content   text check (char_length(utm_content) <= 100 and utm_content ~ '^[a-z0-9._-]+$'),
  -- Referrer host only (lowercase DNS name; no scheme, port, path or bare IP address).
  referrer_host text check (
                  char_length(referrer_host) <= 253
                  and referrer_host ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$'
                  and referrer_host !~ '^[0-9.]+$'),
  -- From viewport width; no user-agent string is stored.
  device        text check (device in ('mobile', 'desktop')),
  -- Per-event extras (brief §5). Spec names: type -> result_type, location -> cta_location,
  -- n -> form_step, reason -> error_reason.
  question      text check (question in ('soilTest', 'method', 'previousCrop', 'target')),
  answer        text check (answer in ('yes', 'no', 'unsure', 'skip')),
  step          smallint check (step between 0 and 3),
  result_type   text check (result_type in ('full', 'confirm', 'nOnly')),
  gaps          smallint check (gaps between 0 and 4),
  cta_location  text check (cta_location in ('hero_primary', 'hero_secondary', 'hero_chip', 'nav')),
  form_step     smallint check (form_step between 1 and 3),
  check_scope   text check (check_scope in ('full', 'confirm', 'nOnly')),
  error_reason  text check (error_reason in ('invalid', 'notConnected', 'error')),
  -- Team test traffic, excluded from reports (data M7).
  is_test       boolean not null default false,

  -- Extras only on their own event, and required where the event is meaningless without them.
  constraint site_event_check_answer check (
    (event = 'check_answer') = (question is not null and answer is not null and step is not null)
    and (event = 'check_answer' or (question is null and answer is null))),
  constraint site_event_step check (step is null or event in ('check_answer', 'check_back')),
  constraint site_event_result_type check (
    (result_type is null or event in ('check_result', 'check_restart', 'check_cta_click'))
    and (event <> 'check_result' or result_type is not null)),
  constraint site_event_gaps check ((event = 'check_result') = (gaps is not null)),
  constraint site_event_cta_location check ((event = 'cta_click') = (cta_location is not null)),
  constraint site_event_form_step check (
    (form_step is null or event in ('form_step', 'form_back'))
    and (event not in ('form_step', 'form_back') or form_step is not null)),
  constraint site_event_check_scope check (check_scope is null or event = 'form_submit_success'),
  constraint site_event_error_reason check (
    (event = 'form_submit_error') = (error_reason is not null))
);

-- For the retention purge and the daily rollup.
create index site_event_occurred_at_idx on site_event (occurred_at);

grant insert (view_id, event, locale, path, utm_source, utm_medium, utm_campaign, utm_content,
              referrer_host, device, question, answer, step, result_type, gaps, cta_location,
              form_step, check_scope, error_reason, is_test)
  on site_event to cp_website;

comment on table site_event is
  'First-party website events (ADR 0010). Whitelisted columns only; no IP, country, UA, PII.'
  ' cp_website INSERT only. Retention (approved): raw 90 days, then daily counts 25 months'
  ' (future worker job).';
comment on column site_event.view_id is
  'Per-page-load random id held in browser memory. Never a join key to pilot_request.';
