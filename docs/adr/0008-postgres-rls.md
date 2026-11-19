# ADR 0008 — Postgres row-level security (RLS v0)

- Status: Proposed (2026-11-17) — needs `ciso` review against `docs/security/adr-0008-rls-review-criteria.md` and Farjad Iranmehr's acceptance (residual risk §1)
- Decider: Farjad Iranmehr
- Supersedes: the "No RLS" line of ADR 0004 / ADR 0002 (CLAUDE.md "Access control" already says org scoping in one data-access layer **plus** RLS)
- Related: ADR 0005 (auth, review gate), ADR 0007 (DB roles), ADR 0010 (site_event), migrations `0015`–`0022`, `db/rls_tables.yaml`, tests `app/tests/db/test_rls.py`, `app/tests/db/test_s2_model.py`

## 1. Context and scope
Org scoping lives in one data-access layer (`app/cloverproof_app/repo/*`, every query takes `org_id`). **Threat addressed:** a query in `app/` that forgets the org filter or passes the wrong id. RLS makes that query return 0 rows or fail with `42501` instead of leaking another organisation's farm data.

**Not addressed:** SQL injection or code execution in the app process. `app.*` settings are ordinary custom GUCs; any session of `cp_app` can `set_config('app.org_id', <other org>, true)`. The membership check in `app_ctx_org()` (§3) narrows this to "an org the forged `app.user_id` belongs to", which still needs a known user id. RLS is defence in depth, not a tenant boundary against an attacker with SQL. **Residual risk to be accepted in writing by Farjad Iranmehr.** The stronger design (context row written by a `SECURITY DEFINER` function that resolves `user_session.token_sha256`) is deferred to v1 (open question Q1).

## 2. Roles

| Role | Login | RLS | Notes |
|---|---|---|---|
| `cp_migrator` | none (migrations `set local role cp_migrator`) | `NOBYPASSRLS`; owns every app object; **filtered** by `FORCE ROW LEVEL SECURITY` and has no policy → sees 0 tenant rows | Backfills that must cross orgs run as the deploy superuser before `set local role cp_migrator` (0016 did, before 0021), in a reviewed migration. `cp_migrator` never gets `BYPASSRLS`. |
| `cp_app` | `cp_app_login` (web app) | `NOBYPASSRLS`, owns nothing, no TRUNCATE/REFERENCES/TRIGGER; every tenant policy is `TO cp_app` | Startup refuses a superuser, `BYPASSRLS`, non-`cp_app` or `cp_admin` login (`check_least_privilege`, `db/pool.py`). |
| `cp_admin` | `cp_admin_login` (CLI only) | member of `cp_app`, so **the same policies apply**; extra grants on identity tables and `farmer.record_kind` | No cross-org path in v0 (§6). |
| `cp_website` | `cp_website_login` | `NOBYPASSRLS`; INSERT-only policies on `pilot_request`, `site_event` (0022); no grant on any tenant table | |
| superuser (deploy/operator) | Railway `postgres` | bypasses RLS | Migrations and break-glass only; every session logged in the ops log (who, when, why); password rotated after any TCP-proxy session. |
| `cp_backup` | — | not created yet | Will be the only non-superuser `BYPASSRLS` role (pg_dump), when the backup role lands (open question Q5). |

## 3. Context contract
- Variables: `app.user_id` (uuid), `app.org_id` (uuid), `app.platform_role` (text, `superadmin` or empty).
- Set **only** by `db/pool.py:set_rls_context`, with `select set_config(k, %s, true), ...` and bind parameters — transaction-local, never `SET`, never `set_config(..., false)`. Called from `auth.py` after the session lookup: `app.user_id` = the session's user; `app.org_id` = an organisation the session user was verified to belong to (never a request parameter); `app.platform_role` = `app_user.platform_role`.
- Policies read the context only through four `stable` helpers (owned by `cp_migrator`, pinned `search_path`, invoker rights, EXECUTE to `cp_app` only):
  - `app_ctx_user()` = `nullif(current_setting('app.user_id', true), '')::uuid`
  - `app_ctx_org()` = `app.org_id` **only if** `app_ctx_user()` is an enabled member of it, else NULL (criterion 2.5)
  - `app_ctx_is_human()` = context user exists, enabled, `actor_kind = 'human'`
  - `app_ctx_platform_role()` = `app.platform_role` only if it equals the user's column (narrows, never elevates); used only by the `catalog` class policies (§5, migration 0027), by no tenant policy.
- **Deny by default:** unset, `''` (after a `SET LOCAL` ends) or a user/org mismatch all give NULL, which matches no row; a non-uuid raises `22P02`. No `coalesce` wildcard, no `app.*` in `ALTER ROLE/DATABASE ... SET`.

## 4. Pool contract
- Tenant queries run only inside `Database.connection()` (psycopg pool, non-autocommit; commit on success, rollback on error). Context is set per transaction; a request that opens a second transaction sets it again.
- The pool's `reset` callback (`reset_connection`) runs `RESET ALL` and checks that no `app.*` value survives; if one does it raises `ContextLeak` and the pool discards the connection.
- An external pooler (PgBouncer) is allowed only in transaction mode and re-opens this ADR.

## 5. Policies
Table classes are listed in `db/rls_tables.yaml`; every `public` table must appear exactly once (test C-0).

| Class | Tables | Pattern |
|---|---|---|
| tenant | `farmer`, `farm`, `field`, `season`, `field_geometry_version`, `soil_test`, `soil_test_value`, `soil_estimate` (0031), `crop_plan`, `recommendation`, `recommendation_line` (0026), `review`, `application_log`, `proof_document`, `access_grant` | `ENABLE` + `FORCE`. `T_org_boundary`: RESTRICTIVE, FOR ALL, TO `cp_app`, `org = (select app_ctx_org())` in USING and WITH CHECK. Permissive `T_select/_insert/_update/_delete`, one per granted command, same predicate; INSERT also binds the author column (`created_by`, `reviewer_id`, `granted_by`) to `app_ctx_user()`. Index led by the org column on every table. |
| identity | `organisation`, `app_user`, `user_session`, `membership`, `admin_event` | Grants + SECURITY DEFINER functions (ADR 0007). **RLS disabled until v1 (S3)**; the catalog test pins that state so a half-done change shows. |
| website | `pilot_request`, `site_event` | `ENABLE` (not FORCE; global tables, the owner is the operator). One INSERT policy TO `cp_website` each; no SELECT policy. |
| website_admin | `website_user`, `website_user_recovery_code`, `website_session`, `website_one_time_token`, `website_rate_limit`, `website_log`, `website_job_run` (migration 0024) | Grants to `cp_website_admin` only + SECURITY DEFINER `website_log_purge()`. RLS disabled; never organisation-scoped, not part of identity RLS v1 (ADR 0012, 0014). |
| catalog | `fertilizer_product` (migration 0027) | Global reference data, deliberately **not** organisation-scoped: no organisation column, no org boundary. `ENABLE` + `FORCE`. Active rows: any context with an existing, enabled `app.user_id`. Drafts, INSERT (draft only) and UPDATE (drafts only; may activate): human superadmin context via `app_ctx_platform_role()`, or `cp_admin` (no context, or a human one). DELETE (drafts only, migration 0030): the same two. Active rows can be neither changed nor deleted. Tests: `app/tests/db/test_fertilizer_product.py`. |
| global | `schema_migrations`, `spatial_ref_sys` | No RLS. |

Special cases:
- `access_grant`: the owning org reads and writes; a grantee org or grantee user may **read** its grants from its own valid context. A member whose only role in the context organisation is `farmer` reads only grants about their own farmer record or naming them as grantee user (0028, restrictive `access_grant_farmer_scope`). Revoke = UPDATE by the owner side with `revoked_by = app_ctx_user()`. Grants give **no** read path to farm data until the S9 portal (DM-R1).
- Rule 12 (AI data boundary): RESTRICTIVE `*_ai_boundary` on `farmer`, `farm`, `field`, `field_geometry_version`: a non-human context sees and writes only rows of farmers with `record_kind <> 'real'` (0017).
- Views (`recommendation_diff`, `recommendation_state`) are `security_invoker`; no materialized views.
- Triggers that read other tables (`review_check_reviewer`, `proof_document_check_approved`, record_kind, soil-test lock, access_grant guard) run as the invoker and so read **through** the policies. From the wrong context they see nothing and fail closed (e.g. `proof_document` insert into another org → `23514` before the policy check).

## 6. Superadmin, service and AI contexts (CLAUDE.md rules 8, 11, 12)
- `app.platform_role = 'superadmin'` grants no organisation data through `cp_app`: only `catalog` class policies name it (catalog test, which excludes that class by an explicit list), and a superadmin in another org's context sees 0 rows (`test_missing_or_wrong_context_sees_nothing[superadmin_wrong_org]`). A superadmin acts on an org's data only as a member of that org.
- `cp_admin` (CLI) is a member of `cp_app` and gets the same policies. Changing `farmer.record_kind` needs a human superadmin in `app.user_id` **and** an org context they belong to. The design in criterion 5.1 (cp_admin with no table privileges, `admin_*` SECURITY DEFINER functions writing `audit_event` in the same transaction) is **not built** (open question Q2).
- Approval stays human-only (ADR 0005, migration 0012): `review_check_reviewer` refuses `approve` by a non-human or non-agronomist, whatever the platform role. `ai_reviewed` reviews never change `recommendation_state.status` (0019) and never appear in `recommendation_diff`.
- Service/AI accounts (`actor_kind = 'service'`, e.g. `cp-agronomist`) see no identifying rows of real farmers (rule 12) and cannot grant or revoke access (0020: actor must be the farmer's own login or a **human** org_admin).

## 7. How to add a table
1. Add it to `db/rls_tables.yaml` in its class (C-0 fails otherwise).
2. Tenant table: in its migration, `enable` + `force row level security`, a restrictive `<t>_org_boundary` to `cp_app`, permissive per-command policies for the commands granted, author-column binding on INSERT if it has one, and an index led by the org column. Any function or view reading it must run as the invoker (or be a reviewed SECURITY DEFINER per criterion 6.2).
3. Add an entry to `TENANT_CASES` in `app/tests/db/test_rls.py` (fresh-row builder, updatable column, deletable). `test_every_rls_table_has_a_case` fails until you do; the entry then runs every allow/deny/no-context test for the table.
4. Any migration that changes RLS state (`DISABLE`, `NO FORCE`, dropping a policy) needs `ciso` review; the catalog test C-1 runs on every `make db-test`.

## 8. Rollout and rollback
Forward-only migrations. v0 = 0021 (tenant) and 0022 (website). Rollback is a new migration, never an edit of an applied one. 0015–0022 have not been applied to any shared database yet.

## 9. Mapping to the ciso review criteria (`docs/security/adr-0008-rls-review-criteria.md`)

Tests are in `app/tests/db/test_rls.py` unless noted.

| # | Status | Where |
|---|---|---|
| 0.1, 0.2 | Written | §1. 0.2 residual risk: **awaiting Farjad Iranmehr's written acceptance**; token-bound context deferred (Q1). |
| 0.3 | Met | `db/rls_tables.yaml`; `test_c0_every_public_table_is_classified_once`. |
| 1.1 | Met | `test_cp_app_owns_nothing` (pg_class, pg_proc, pg_type). |
| 1.2 | Met for the four app roles | `test_roles_cannot_bypass`. `cp_backup` not created yet (Q5). |
| 1.3 | Met | `test_roles_cannot_bypass` (not in `cp_migrator`, `pg_read_all_data`, `pg_write_all_data`). |
| 1.4 | Met for tenant tables; identity = v1 | `test_c1_catalog_state_matches_class`. Identity tables stay without RLS until S3 (Q3). |
| 1.5 | Partly | C-1 runs in `make db-test`. CODEOWNERS on `db/migrations/` not added yet (Q4). |
| 1.6 | Met | `test_cp_app_has_no_truncate_references_trigger`. |
| 1.7, 1.8 | Written | §2. |
| 2.1 | Met in code; CI grep not added | `set_rls_context` is the only setter (`db/pool.py`). Grep gate open (Q4). |
| 2.2 | Met in code | `auth.py` sets the org from the verified membership; existing org-scoping tests (`test_org_scoping.py`). |
| 2.3 | Met | `test_missing_or_wrong_context_sees_nothing[none,user_only]`, `test_insert_without_context_is_refused`, `test_context_does_not_survive_the_transaction`, `test_garbage_context_raises`, `test_no_app_settings_in_role_or_database_defaults`. |
| 2.4 | Met | `test_no_cp_app_policy_grants_by_platform_role`; T-SA-1 = `...[superadmin_wrong_org]`. |
| 2.5 | Met | `app_ctx_org()` membership check; `...[wrong_org]`. |
| 3.1 | Met in code | routes use `Database.connection()`; grep gate open (Q4). |
| 3.2 | Partly | `test_autocommit_set_config_lasts_one_statement` (T-POOL-2). T-POOL-1 not written. |
| 3.3 | Partly | `reset_connection` + `test_pool_reset_clears_a_session_level_context`. Full T-POOL-3 with a real pool and a real `cp_app_login` not written: it needs a LOGIN role, which the shared test server must not get from tests (Q6). |
| 3.4, 3.5 | Written / met | §4; `test_context_does_not_survive_the_transaction` (T-POOL-4). |
| 4.1 | Met | `test_policies_never_to_public_and_insert_update_have_check`, `test_insert_into_other_org_is_refused`, `test_row_cannot_move_to_other_org`, `test_update_and_delete_of_other_org_touch_nothing`. |
| 4.2 | Met | `test_tenant_table_has_restrictive_org_boundary`. |
| 4.3 | Met | `test_policies_never_to_public_and_insert_update_have_check`. |
| 4.4 | Met | INSERT policies bind `created_by` / `reviewer_id` / `granted_by`; `test_review_author_cannot_be_forged`. |
| 4.5 | Not yet (v1, S3) | Identity RLS + pre-auth `SECURITY DEFINER` lookups (Q3). |
| 4.6 | Met / accepted | Composite FKs; `test_cross_org_reference_fails`. Residual: FK/unique errors are an existence oracle; UUIDv4 ids, email uniqueness accepted at the login UI. |
| 4.7 | Met | 0022; `test_website_policies_are_insert_only_to_cp_website`; spec tests in `test_grants.py`, `test_site_event.py` still pass. |
| 5.1 | **Not met** | Superadmin has no cross-org path at all in v0 (safer default); the `admin_*` + audit design is open (Q2). T-SA-2 not applicable yet (`cp_admin` is a `cp_app` member). |
| 5.2 | Not yet | `audit_event` table not built (gap analysis); `admin_event` covers role/account changes only. |
| 5.3 | Planned S5 | MFA (ADR 0005). |
| 5.4 | Met | Review gate unchanged by platform role (0012; `test_superadmin.py`, `test_review_gate.py`). No definer function writes `review`/`proof_document`. |
| 6.1 | Met | `test_views_are_security_invoker`; `test_other_org_rows_invisible_in_views` (T-V-1). |
| 6.2 | Existing definer functions from 0011/0015 pin `search_path = ''` and revoke PUBLIC; no new definer function in 0016–0022. A catalog test over all `prosecdef` functions is not written yet (Q4). |
| 6.3 | Met | The whole suite runs under RLS: approvals by the org's agronomist succeed (`test_review_gate.py`); from another org's context the review insert fails `42501`; `proof_document_check_approved` sees the approval in-org and fails closed cross-org. |
| 6.4 | Met | `test_context_helpers_are_stable_pinned_and_owned_by_migrator`. |
| 7.1–7.3, 7.6 | Met earlier | `actor_kind` (0012) — named `actor_kind` with values `human` / `service`, not `account_kind`; `test_actor_kind.py`, `test_app_s2_delta.py`, `test_review_integrity.py`. |
| 7.4 | Met, on `farmer` | `farmer.record_kind` (`real` default, `demo`, `reference`), set only by a human superadmin, frozen once a recommendation exists (0017; `test_s2_model.py`). Never gates approval. |
| 7.5 | Query documented here | `select count(*) from review r join app_user u on u.id = r.reviewer_id where r.decision = 'approve' and r.review_kind <> 'ai_reviewed' and u.actor_kind <> 'human'` = 0. Weekly run: ops runbook (Q4). |
| 7.7 | Met | `*_ai_boundary` policies, including `soil_estimate` (0033: its values could locate a farm's map pixel); `test_service_context_sees_no_real_farmer_rows`. Other tenant tables (soil tests, plans, recommendations) carry no names or geometry and stay visible to a service member of the org. |
| 8.1 | Met | 0021 indexes; `test_tenant_table_has_index_led_by_org_column`. |
| 8.2 | Met in policy text | Helpers called as `(select app_ctx_org())`. `EXPLAIN` test on 100k rows not written. |
| 8.3 | Not yet | Budget proposed: p95 within +20 % of RLS off; benchmark before the S5 gate. |

## 10. Open questions for `ciso`
- **Q1** Accept GUC-based context for v0 (residual risk §1), with the token-bound context as v1?
- **Q2** Superadmin cross-org access: keep "none" until a support case needs it, then build `admin_*` definer functions + `audit_event`?
- **Q3** Identity-table RLS and pre-auth lookups in S3 — acceptable to ship v0 with identity tables protected by grants only?
- **Q4** CI gates still missing: grep for context setters and raw `.connection()`, `prosecdef` catalog test, CODEOWNERS on `db/migrations/`, weekly 7.5 query. Owner and sprint?
- **Q5** `cp_backup` (`BYPASSRLS`) — create with the backup/restore plan, or use the superuser for `pg_dump`?
- **Q6** T-POOL-3 needs a real `cp_app_login`: create a per-run login in the disposable test database (dropped at the end), or test only in CI where the server is throwaway?
- **Q7** A `farmer` membership currently sees the whole organisation's tenant rows (only the org boundary applies). Farmer accounts are S9 and feature-flagged; their narrower policies must land before the flag is turned on.
