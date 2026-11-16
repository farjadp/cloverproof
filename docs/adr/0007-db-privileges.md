# ADR 0007 — Database roles and privileges

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

## Addendum — migration 0012: human vs service actors, version invariants, admin audit (2026-11-16)
Source: security review `S2-review-pr7-delta` (B1, F1, F2, F4, N11, N16) and CPO decision D4 (`docs/plans/backend-plan-reconciliation.md`). Decided by the lead; needs Farjad Iranmehr's acceptance.

- **Actor kind (B1, D4).** `app_user.actor_kind` is `human` (default, every existing row) or `service`. Only `cp_admin` (CLI) writes it; `cp_app` has no column grant. A service account cannot hold a password (`app_user_service_no_password`). The review trigger requires a **human agronomist** for `approve`, `edit` and `reject` (N16 extends the database check beyond `approve`); `recommendation_check_author` refuses `kind='agronomist'` rows by a service account. New decision `ai_reviewed` is accepted only from a service account. It is never final: `proof_document_check_approved`, `recommendation_diff` and the F1 rules look only at `approve`/`reject`. The gap analysis names the value `ai`; the lead chose `service` (an AI agent is one kind of service account).
- **Version invariants (F1).** One child per recommendation, one final review (approve or reject) per recommendation, and never both. Unique indexes cover the same-type races; two BEFORE INSERT triggers cover child-vs-final and take `pg_advisory_xact_lock(12012, hashtext(id))` so concurrent requests serialise under READ COMMITTED. Every violation is SQLSTATE `23505`; the app maps the constraint name to HTTP 409: `recommendation_one_child_idx`, `review_final_after_child` (stale version); `review_one_final_idx`, `review_one_approval_idx`, `recommendation_child_after_final` (already reviewed). `review_one_edit_idx` keeps one edit review per new version. Under REPEATABLE READ or SERIALIZABLE the trigger checks would see the old snapshot; the app uses READ COMMITTED.
- **Admin audit (F2).** `admin_event` is append-only (`forbid_change` on UPDATE/DELETE/TRUNCATE). It is written only by SECURITY DEFINER AFTER triggers on `membership` (insert, update, delete) and `app_user` (insert, delete, and changes of `password_hash`, `password_change_required`, `actor_kind`, `disabled_at`), so web functions, the CLI and manual SQL are all covered. `cp_app` has SELECT only. Actor: `actor_user_id` from `SET LOCAL app.user_id = '<uuid>'` (the web app sets it in admin transactions; a non-uuid value aborts the change), plus `actor_db_role = session_user` (the login role; `current_user` would be the definer). No email, names or hashes are stored. The gap analysis plans a wider `audit_event` (0020); `admin_event` is the identity subset and can be folded into it then.
- **Timer start (F4).** `review.started_at` (nullable) stores the signed timer start so minutes can be recomputed; `minutes_spent` stays the metric.
- **Temporary password expiry (N11).** `app_user.temp_password_expires_at` is set by trigger to now() + 72 h whenever an admin-set temporary password is stored and cleared when the user sets their own; `cp_app` cannot write it, `cp_admin` may extend it. Existing temporary passwords got 72 h from migration time. The app must treat an expired temporary password as an invalid login.
- **Residual risk.** This stops a dedicated service account, not an AI agent driving a human agronomist's session; that stays a policy matter (and MFA, ADR 0005 / R3).
