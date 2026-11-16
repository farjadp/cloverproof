# ADR 0006 — Database roles and privileges

- Status: Proposed (2026-11-16) — decided by the lead for Sprint 2 security fixes; needs Farjad Iranmehr's acceptance
- Decider: Farjad Iranmehr
- Related: ADR 0002 (data model, grants instead of RLS), ADR 0005 (review gate), security review S2 findings S5 and A1, threat model T-W3 / T-H6 / T-O2, `db/migrations/0011_least_privilege_roles.sql`, `docs/runbook-db-switch.md`

## Context
The review gate in the database (trigger on `review`, migration 0007) decides "is this reviewer an agronomist?" from `membership`. Until 0011 the app role `cp_app` could insert and update `membership`, `organisation` and every `app_user` column, so one app bug could make a staff user an approver: the database half of the gate was only as strong as the app (S5). The runbook also gave the public website the PostGIS superuser URL (A1 / T-W3).

## Decision
Four NOLOGIN roles live in git; LOGIN roles are created by an operator outside git (`create role X_login login password '...' in role X`), passwords only in Railway variables.

| Role | Who logs in as it | Privileges |
|---|---|---|
| `cp_migrator` | nobody; migrations `set local role cp_migrator` as the deploy user (superuser, operator only) | owns every app object |
| `cp_app` | web app → `cp_app_login` | farm data as in ADR 0002; SELECT on `organisation`, `membership`; on `app_user` INSERT (email, display_name, password_hash, password_change_required) and UPDATE (password_hash, password_change_required, display_name, disabled_at) only; EXECUTE on `web_grant_member_role` / `web_revoke_member_role` |
| `cp_admin` | admin CLI → `cp_admin_login` | member of `cp_app`, plus INSERT/UPDATE/DELETE on `organisation`, `membership`, INSERT/UPDATE on `app_user` |
| `cp_website` | website → `cp_website_login` | USAGE on schema `public`, INSERT on `pilot_request` (the nine form columns); no SELECT, nothing else |

- Owner pages change roles only through the two SECURITY DEFINER functions (owned by `cp_migrator`, `search_path = ''`, EXECUTE revoked from PUBLIC). They allow only `staff` and `farmer`, require the actor to be an enabled `owner` of that organisation, and refuse adding a user who already belongs to another organisation.
- `agronomist` and `owner` are granted and removed only by the CLI (`cp_admin`). The web pages show them read-only ("change via CLI"); the app also refuses to reset the password of an agronomist/owner account (that would let an owner take over the approver's login).
- Last-owner protection stays in the app: disabling locks the owners' `app_user` rows (`for update of u`); demoting an owner is no longer possible on the web.

## Consequences
- An app bug or injection can no longer create an approver or a new organisation; immutable tables keep their triggers + grants (ADR 0002).
- Adding an agronomist or owner needs operator access (CLI with `cp_admin_login`). The CLI has no "remove role" command yet: until it does, removal is SQL run as `cp_admin_login`.
- The actor id passed to the functions comes from the app session; the database bounds what a compromised app can do but does not authenticate the actor. A compromised app can still set `reviewer_id` to a real agronomist on a review row (see threat model T-R2); binding reviews to a database-verified identity is not solved here.
- A compromised website can only add pilot requests (spam), not read PII or touch farm data.
- The superuser URL is never a service variable, so the app cannot run migrations in its pre-deploy step; an operator runs them until a dedicated deploy role exists.
- New tables need explicit grants for each role; a test (`app/tests/db/test_grants.py`) pins the identity and website grants.
