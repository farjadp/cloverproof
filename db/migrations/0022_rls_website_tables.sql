-- 0022: RLS on the website tables (ADR 0008; ciso criterion 4.7,
-- docs/security/website-db-role-spec.md). Global tables, not tenant data.
--
--   pilot_request  cp_website may only INSERT a fresh request (status 'new', not deleted).
--                  No SELECT policy for anyone in git: the staff read path is defined
--                  separately (spec §1). Owner = the deploy user (0001), so ENABLE runs
--                  before `set local role cp_migrator`. Not FORCEd (global table; the owner
--                  is the operator).
--   site_event     cp_website may only INSERT. Owner cp_migrator; not FORCEd (global; the
--                  future rollup job and reports use a separate role, ADR 0010).
-- cp_website's column grants (0011, 0013) are unchanged; with no SELECT grant it already
-- cannot use RETURNING, so RLS does not change what the website can do.

alter table pilot_request enable row level security;

create policy pilot_request_website_insert on pilot_request for insert to cp_website
  with check (status = 'new' and deleted_at is null);

set local role cp_migrator;

alter table site_event enable row level security;

create policy site_event_website_insert on site_event for insert to cp_website
  with check (occurred_at is not null);
