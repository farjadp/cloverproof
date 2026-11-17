# S3 review — RLS v0 (PR #48, merge 100ccbb)

Owner: `security-engineer` for `ciso`. Date: 2026-11-17. Reviewed tree: `origin/main` a4851ed (read-only checkout).
Scope: migrations `0015`–`0022`, `app/cloverproof_app/db/pool.py`, `auth.py` context setting, `app/tests/db/test_rls.py`, `test_s2_model.py`, ADR 0008, `db/rls_tables.yaml`.
Criteria: `docs/security/adr-0008-rls-review-criteria.md`. CLAUDE.md rules 8, 11, 12 applied.

## Verdict

**Code: PASS — no BLOCKER.** The WIP commits were checked against a running database. On every tenant table the policies, the FORCE setting, deny when no context is set, and the pool reset all behave as the ADR says. The full DB suite passes (518 passed, 1 skipped). My own probes on a real pool with a real `cp_app` login found no leak and no cross-org read or write.

**ADR 0008: NOT YET PASSING the criteria.** Several criteria are FAIL or PARTIAL (4.5, 5.1, 5.2, 1.4 for identity tables, 3.3 test, 2.1/3.1 CI grep, 1.5 CODEOWNERS, 6.2 catalog test, 8.3). For each one, either the gap is closed or `ciso` writes an exception. Farjad Iranmehr must also sign off the 0.2 residual risk. Until then the ADR stays `Proposed`. Applying 0015–0022 to Railway is not blocked: RLS only removes access.

Counts: BLOCKER 0, SHOULD-FIX 4, NOTE 7.

## Findings

### SHOULD-FIX

**SF-1. Identity tables have no RLS, and `cp_app` can SELECT every column, including `password_hash` and `totp_secret`, for every user in every org (criteria 1.4 and 4.5; rule 12 partial).**
Evidence: `db/migrations/0003_identity.sql:84` (table-level `grant select ... on organisation, app_user, user_session, membership to cp_app`), not narrowed by `0011_least_privilege_roles.sql`. In the catalog, `organisation`, `app_user`, `user_session`, `membership` and `admin_event` all have `relrowsecurity = f`. `membership` and `admin_event` hold an `organisation_id`. `db/rls_tables.yaml:32-37` pins this state on purpose (ADR 0008 §5, Q3).
Probe P5: a **service** context (`actor_kind = 'service'`) in org A read all 5 `app_user` rows with email (all orgs) and org B's membership rows. With no context at all, it also read all 5 `app_user` rows.
Exploit path: an app bug in an identity query, e.g. a user list without an org filter, or `select *` rendered in a template. The query returns other orgs' users and, through `app_user`, the password hash and TOTP secret columns. Later, any service or AI path that gets DB access reads personal data. Rule 12 is enforced only on `farmer/farm/field/field_geometry_version`.
Fix (new migration, e.g. `0024_identity_column_grants.sql`; RLS on identity tables can follow in v1):
```sql
set local role cp_migrator;
revoke select on app_user from cp_app;
grant select (id, email, display_name, actor_kind, platform_role, disabled_at,
              password_change_required, temp_password_expires_at, auth_provider,
              external_subject, created_at) on app_user to cp_app;
-- login: the only reader of the hash (pre-auth, criterion 4.5)
create function auth_credentials_by_email(p_email text)
returns table (id uuid, password_hash text, can_sign_in boolean)
language sql stable security definer set search_path = '' as $$
  select u.id, u.password_hash,
         u.disabled_at is null and u.actor_kind = 'human'
  from public.app_user u where u.email = lower(p_email) $$;
revoke execute on function auth_credentials_by_email(text) from public;
grant execute on function auth_credentials_by_email(text) to cp_app;
-- same pattern for totp_secret when MFA lands (S5)
```
In v1, add `enable`/`force` RLS to `membership` and `admin_event` with `organisation_id = (select app_ctx_org())`, and give `app_user` the "self or shared org" policy. `app_ctx_org()` reads `membership`, so it must become `SECURITY DEFINER` (pinned, argument-free, reading only `app_ctx_user()`'s rows) before `membership` gets RLS. Otherwise it recurses or denies everything.

**SF-2. `web_grant_member_role` / `web_revoke_member_role` (SECURITY DEFINER) trust a caller-supplied actor and ignore the RLS context (criterion 6.2: "validates its arguments against the context").**
Evidence: `db/migrations/0015_membership_role_rename.sql:25-58, 60-80`. The actor is checked only as "`p_actor_id` is an org_admin of `p_organisation_id`". Nothing ties it to `app_ctx_user()` / `app_ctx_org()`.
Probe P9: as `cp_app` with context user UB / org B, `select web_grant_member_role(<UA, org_admin of A>, A, <membership-less user>, 'advisor')` **succeeded**. The same call with **no context** also succeeded. `cp_app` can also INSERT `app_user` (`0011:43`). An app bug that passes the wrong actor, or SQL access, can therefore attach a fresh user to any organisation as advisor or farmer. That user then gets a valid `app_ctx_org()` for that org. This is the one SQL path where context is not required.
Fix (new migration; both functions):
```sql
create or replace function web_grant_member_role(p_actor_id uuid, p_organisation_id uuid,
  p_user_id uuid, p_role public.membership_role) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if p_actor_id is distinct from public.app_ctx_user()
     or p_organisation_id is distinct from public.app_ctx_org() then
    raise exception 'actor/organisation must match the RLS context' using errcode = '42501';
  end if;
  -- ... existing body unchanged ...
end $$;
```
(`app_ctx_*` read GUCs and `membership`, and work inside a definer function. `cp_migrator` owns them, and `membership` has no RLS yet.) Test: the P9 calls must raise `42501`.

**SF-3. No pool-leak test with a real pool and a real login (T-POOL-3 / T-POOL-1); the reset callback is load-bearing.**
Evidence: `app/tests/db/test_rls.py:693-730` covers transaction scope, autocommit and `reset_connection` on its own, but not a real `ConnectionPool` with a `cp_app` LOGIN role (ADR §9 3.2/3.3 "Partly", Q6).
Probe P1e: with a pool that has **no** `reset` callback, a session-level `set_config(..., false)` in checkout 1 leaked into checkout 2 (2 farmer rows visible with no context). With `reset=reset_connection` (`db/pool.py:55-68, 119`) the leak is gone (P1). The code is correct today. A regression to `pool.py:119` would not be caught.
Fix: answer Q6 = per-run login in the disposable test database. The test does `create role cp_test_login_<rand> login password <random> in role cp_app`, drops it in a finalizer, and runs P1/P1b/P1c/P1d from this report as tests, including `pg_backend_pid()` equality.

**SF-4. CI gates promised by the criteria are missing (2.1, 3.1, 1.5, 6.2 catalog).**
Evidence: ADR 0008 §9 rows 1.5, 2.1, 3.1, 6.2 and Q4. There is no `CODEOWNERS` file in the repo root or `.github/`. There is no grep gate. There is no `prosecdef` catalog test. Today's state is clean: `set_config` appears only in `db/pool.py:44-48`; `.connection()` appears only in `auth.py:93` (the request dependency) and `main.py:119` (startup check); all 4 definer functions pin `search_path=""` and have `has_function_privilege('public', ..., 'EXECUTE') = f`. The gates protect the next PR, not this one.
Fix: add to `app/tests/db/test_rls.py`:
```sql
select proname from pg_proc where prosecdef and pronamespace = 'public'::regnamespace
  and (proconfig is null or not exists (select 1 from unnest(proconfig) c where c like 'search_path=%')
       or has_function_privilege('public', oid, 'EXECUTE'));  -- expect 0 rows
```
Also add a CI step that runs `! grep -rnE "set_config\([^)]*,\s*false\)|\bSET( LOCAL)?\s+app\." app/cloverproof_app`, plus a check that `.connection()` appears only in `db/` and `auth.py:db_conn`. Add `.github/CODEOWNERS` with `db/migrations/ @<ciso-owner>`.

### NOTE

- **N-1. Residual risk 0.2 is not signed off.** ADR 0008:11, :76. Any `cp_app` SQL can forge `app.user_id` to a known member id. `app_ctx_org()` (`0021:47-59`) narrows access to orgs of that user and nothing more. Farjad Iranmehr has to accept this in writing, or approve the token-bound context (Q1).
- **N-2. No superadmin cross-org path and no `audit_event` (5.1, 5.2 FAIL).** This is the safer default. P3 showed that a superadmin in org B's context and outside its membership sees 0 rows. It needs a `ciso` exception until Q2 is built.
- **N-3. `access_grant` has no maximum lifetime, and a grant to a user who is already a member of the owning org is allowed.** `0020:34-38`. Probe P8 accepted a 100-year expiry and a self-org user grantee. Grants give no data access yet (P8: grantee org B read the grant row, but 0 farmer rows of A). Before S9 (DM-R1), add `check (expires_at is not null and expires_at <= granted_at + interval '<product max>')` and a trigger that refuses a `grantee_user_id` who is a member of `owner_organisation_id`. Org B cannot insert a grant owned by A (42501) and cannot revoke one (0 rows). A service account cannot grant (42501). Only the owner org can write, so cross-org widening is not possible.
- **N-4. A `farmer` membership sees the whole org's tenant rows** (ADR Q7). `app_ctx_org()` accepts any membership role (`0021:51-58`). Narrower farmer policies are needed before the S9 flag is turned on.
- **N-5. Rule 12 covers four tables only.** `0021:188-227`. A service context still reads `season`, `soil_test`, `crop_plan`, `recommendation` (with `inputs_snapshot`), `review`, `proof_document`, `application_log` and the views. ADR 0008:112 says these hold no names or geometry. I did not verify that `inputs_snapshot` and `proof_document` (PDF path, PDF content) carry no farm or farmer name or location. Confirm this before a service path gets DB access, or extend `*_ai_boundary` to those tables.
- **N-6. Hardening: `TEMP` on the database for PUBLIC.** Invoker trigger functions without a pinned `search_path` (e.g. `review_check_reviewer`, read with `pg_get_functiondef`, which names `app_user` unqualified) resolve relations through `pg_temp` first. A session with SQL could shadow `app_user` with a temp table. This sits in the 0.2 SQL-execution scope, so it is not a finding. The cheap fix is `revoke temporary on database <db> from public;` plus pinning `search_path` on the trigger functions in the next migration that touches them.
- **N-7. Doc drift.** `db/rls_tables.yaml:2` names `app/tests/db/test_rls_catalog.py`, which does not exist (the tests are in `test_rls.py`). ADR 0008:109 says criterion 7.1 is met with `actor_kind` (`human`/`service`), while the criterion text says `account_kind` with `ai_agent`. Equivalent; record it in the ADR as the accepted naming.

## Criteria table

| # | Result | Evidence |
|---|---|---|
| 0.1 | PASS | ADR 0008:9 |
| 0.2 | PARTIAL | ADR 0008:11 written; Farjad sign-off pending (N-1) |
| 0.3 | PASS | `db/rls_tables.yaml:17-45`; catalog: all 22 `public` tables classified; C-0 test passes |
| 1.1 | PASS | catalog: 0 `pg_class`/`pg_proc` owned by non-superuser `cp_app` members; `test_rls.py:417` |
| 1.2 | PASS (cp_backup N/A) | catalog: `rolbypassrls and not rolsuper` = 0 rows |
| 1.3 | PASS | `test_roles_cannot_bypass` green |
| 1.4 | PARTIAL | 13 tenant tables `rls=t force=t` with policies; identity tables `rls=f` (SF-1) |
| 1.5 | PARTIAL | C-1 in `make db-test`; no CODEOWNERS (SF-4) |
| 1.6 | PASS | catalog: no TRUNCATE/REFERENCES/TRIGGER for `cp_app` on any table |
| 1.7, 1.8 | PASS (written) | ADR 0008:17, :21 |
| 2.1 | PARTIAL | `pool.py:44-48` only setter, bind params, `true`; CI grep missing (SF-4) |
| 2.2 | PASS | `auth.py:163-177` org comes from `users.user_organisations` + signed cookie (`auth.py:152-161`) |
| 2.3 | PASS | `0021:42-59` `nullif(current_setting(..., true), '')`; P1/P2/P3: no ctx = 0 rows, garbage = `22P02`; `pg_db_role_setting` has no `app.*` |
| 2.4 | PASS | no policy names `platform_role` (catalog); `0021:69-77` narrows only; P3: forged `superadmin` returns NULL; superadmin in org A context sees 0 org B rows |
| 2.5 | PASS | `0021:47-59`; P3: UA with org B context = 0 rows on all tables |
| 3.1 | PARTIAL | routes use `db_conn` (`auth.py:90-94`); CI gate missing (SF-4) |
| 3.2 | PASS | P2: autocommit `set local` = 0 rows; `set_config(true)` then second statement = 0 rows |
| 3.3 | PARTIAL | `pool.py:55-68,119` works (P1, P1e); real-pool test missing (SF-3) |
| 3.4 | PASS | ADR 0008:37 |
| 3.5 | PASS | P1d: second transaction on the same checkout = 0 rows; `test_rls.py:693` |
| 4.1 | PASS | catalog: no INSERT/UPDATE/ALL policy without `with_check`; P3 move/insert to B = `42501`, update of B = 0 rows |
| 4.2 | PASS | restrictive `*_org_boundary` on all 13 tenant tables (`0021:134-137, 162-168`) |
| 4.3 | PASS | catalog: roles only `{cp_app}` / `{cp_website}` |
| 4.4 | PASS | `0021:142-145` binds `created_by`/`reviewer_id`/`granted_by`; `access_grant_update` binds `revoked_by` (`0021:177-180`) |
| 4.5 | FAIL | no identity RLS, no pre-auth definer lookups; `password_hash`/`totp_secret` selectable (SF-1) |
| 4.6 | PASS | composite FKs; `test_cross_org_reference_fails` green |
| 4.7 | PASS | `0022:14-17`; P12: `cp_website` SELECT `pilot_request`/`farmer` = `42501`; `test_grants.py`/`test_site_event.py` green |
| 5.1 | FAIL (exception needed) | not built; no cross-org path (N-2) |
| 5.2 | FAIL (exception needed) | no `audit_event` |
| 5.3 | N/A (S5) | — |
| 5.4 | PASS | `review_check_reviewer` (DB def): `superadmin_approved` needs `is_human_superadmin` + org member; else human agronomist; no definer function writes `review`/`proof_document` (catalog: 4 definer functions, none do) |
| 6.1 | PASS | catalog: `recommendation_diff`, `recommendation_state` (`0019:19`), `ai_review` all `security_invoker=true`; no matviews |
| 6.2 | PARTIAL | all 4 definer functions pinned and PUBLIC-revoked; web_grant/revoke not bound to context (SF-2); no catalog test (SF-4) |
| 6.3 | PASS | `test_review_gate.py`, `test_rls.py` green under RLS; P8: cross-org grant insert fails closed in trigger |
| 6.4 | PASS | `0021:42-88` stable, pinned, owner `cp_migrator`; `cp_app` has no CREATE on `public` |
| 7.1–7.3, 7.6 | PASS | earlier migrations; `test_actor_kind.py`, `test_review_integrity.py` green |
| 7.4 | PASS | `0017:21-77`; `cp_app` column grants exclude `record_kind` (`0017:30-32`) |
| 7.5 | PARTIAL | query in ADR 0008:111; weekly run not scheduled |
| 7.7 | PARTIAL | P5: service sees only the demo farmer/farm and cannot insert a real farmer (`42501`); but reads `app_user` emails across orgs (SF-1) and the non-identity tenant tables (N-5) |
| 8.1 | PASS | `0021:95-98`; test green |
| 8.2 | PARTIAL | `(select app_ctx_org())` initplans in policy text; EXPLAIN test not written |
| 8.3 | FAIL (not measured) | ADR 0008:115 |
| Migrations forward-only | PASS | PR #48 only adds 0015–0022 (`git diff --name-status`); no first-parent commit on main modifies an existing migration; 0018/0020 were changed inside the PR branch before merge (not applied anywhere, ADR 0008:68) |

## Tests run (local throwaway `postgis/postgis:18-3.7` on 127.0.0.1:55499, removed afterwards; never Railway)

- `make db-test` in a scratch copy of a4851ed: **518 passed, 1 skipped** (WeasyPrint pango missing locally, `test_proof_flow.py:209`).
- Catalog SQL over a migrated DB (0001–0023): RLS/FORCE/policy count per table, BYPASSRLS, ownership, views, definer functions, `pg_policies`, identity grants, `cp_website` grants, `pg_db_role_setting`, TRUNCATE/REFERENCES/TRIGGER, schema CREATE.
- Probes with a real LOGIN role in `cp_app` (created and dropped with the container):
  - P1: real `ConnectionPool(max_size=1, reset=reset_connection)`, same `pg_backend_pid()`. Leak checked after commit, after rollback, after a session-level `set_config(false)`, and with two transactions on one checkout: 0 rows on all 13 tables + 3 views.
  - P1e: pool without the reset callback: leak reproduced (2 rows).
  - P2: autocommit paths.
  - P3: cross-org read/insert/move/update, wrong org, superadmin narrowing, garbage uuid.
  - P5: service context and rule 12.
  - P7: `cp_migrator` filtered by FORCE (0 rows).
  - P8: `access_grant` cross-org insert/revoke, service grant, expiry, self grant.
  - P9: definer function with forged actor.
  - P12: `cp_website` select denied.

## Not verified

- T-POOL-3 inside the repo's suite (my probe only; SF-3).
- Contents of `recommendation.inputs_snapshot` and the proof PDF for identifying data (N-5).
- EXPLAIN / p95 performance (8.2, 8.3).
- CLI paths as `cp_admin`. They set no context, so they see 0 tenant rows; I did not check whether any CLI command needs tenant rows.
- Behaviour on Railway's Postgres version (tested on PG 18 / PostGIS 3.7 locally).
- `website/` (Next.js) and its own DB access beyond the `cp_website` grants.
