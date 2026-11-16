# ADR 0006 (RLS on Railway) — CISO review criteria

Owner: `security-engineer` for `ciso`. Date: 2026-11-16. Applies to: `cp-database`'s draft ADR 0006 and the S3 RLS test suite.
Source decisions: `docs/plans/backend-plan-reconciliation.md` (branch `cpo-backend-plan`) **D1** (Postgres RLS on Railway, keyed on per-transaction `app.user_id` / `app.org_id` / `app.platform_role` set from the server-side session) and **D4** (the AI agronomist can never approve a real farm's plan).

**Authoritative since PR #22:** `CLAUDE.md` rules 8 (human agronomist only, enforced in service AND database; `superadmin` cannot approve unless also a human agronomist; any farm not flagged synthetic is real), 11 (AI sign-off is `ai_reviewed` only, never the gate, never in the calibration dataset) and 12 (AI agronomist gets no personal or identifiable farm data). Where this checklist and CLAUDE.md differ, CLAUDE.md wins.
Current state read: `db/migrations/0002`–`0009` (no RLS anywhere; `cp_app` gets table grants; `cp_migrator` owns objects; `recommendation_diff` already `security_invoker = true`; `review_check_reviewer` is the approve gate), `app/cloverproof_app/db/pool.py` on `origin/webapp-step5-app` (psycopg `ConnectionPool`, non-autocommit, no `reset` callback, no context setting yet).

Postgres facts this checklist relies on (https://www.postgresql.org/docs/17/ddl-rowsecurity.html):
- "Superusers and roles with the `BYPASSRLS` attribute always bypass the row security system."
- "Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with `ALTER TABLE ... FORCE ROW LEVEL SECURITY`."
- "If no policy exists for the table, a default-deny policy is used."
- "Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security."
- "`TRUNCATE` and `REFERENCES` are not subject to row security."
- Permissive policies combine with `OR`, restrictive with `AND`.
- psycopg pool: on return, an open transaction is committed or rolled back; the only cleanup hook is the optional `reset` callback; session settings are not reset by the pool (https://www.psycopg.org/psycopg3/docs/advanced/pool.html).

**How to use:** the ADR passes only if every item is PASS or has a written, CISO-accepted exception. Each item names the evidence the ADR or PR must show and the test that proves it. "Test" = automated in `make db-test` unless marked "catalog" (a SQL assertion in the same suite).

---

## 0. Scope statement the ADR must make (blocking)

| # | Criterion | Pass | Proof |
|---|---|---|---|
| 0.1 | State the threat RLS addresses: a query in `app/` that forgets the org filter, or uses the wrong id. | Written in the ADR. | Review. |
| 0.2 | State what it does **not** address: SQL injection or code execution in the app process. `app.*` settings are ordinary custom GUCs; any role can `set_config('app.org_id', <other org>, true)`. RLS keyed on them is defence in depth, not a tenant boundary against an attacker with SQL. | Written, with residual risk accepted by Farjad Iranmehr. | Review. Optional stronger design to consider: context row written only by a `SECURITY DEFINER` function that resolves the session token hash (`user_session.token_sha256`) and keyed on `txid_current()`, so a forged context needs a valid session token. |
| 0.3 | List every table with its class: **tenant** (has `organisation_id`), **identity** (`organisation`, `app_user`, `user_session`, `membership`), **global** (catalogs, `schema_migrations`, `pilot_request`). Each class has a policy pattern. | Table in the ADR covers 100 % of `public` tables. | Catalog test C-0: every table in `public` is in the ADR's allowlist file (e.g. `db/rls_tables.yaml`); a new table without an entry fails CI. |

## 1. Roles and bypass paths

| # | Criterion | Pass | Test |
|---|---|---|---|
| 1.1 | The app role does not own any table, view, function or sequence. | 0 objects owned by `cp_app` or any login in `cp_app`. | catalog: `select count(*) from pg_class where relowner in (select oid from pg_roles where pg_has_role(oid,'cp_app','member'))` = 0; same for `pg_proc`, `pg_type`. |
| 1.2 | No `BYPASSRLS` except the backup role (`cp_backup`, needed by `pg_dump`) and superusers. `cp_app`, `cp_migrator`, `cp_website`, `cp_admin` are `NOBYPASSRLS`. | Exact set. | catalog: `select rolname from pg_roles where rolbypassrls and not rolsuper` = `{cp_backup}`. |
| 1.3 | `cp_app` (and its logins) is not a member of `cp_migrator`, `cp_backup`, any superuser or `pg_*` predefined role that reads data (`pg_read_all_data`, `pg_write_all_data`). | `pg_has_role(..., 'member')` false for each. | catalog. |
| 1.4 | `FORCE ROW LEVEL SECURITY` on every tenant and identity table, so `cp_migrator` (owner) is filtered too. | `relrowsecurity and relforcerowsecurity` for 100 % of tenant + identity tables. | catalog C-1 (below). |
| 1.5 | Owner can still `ALTER TABLE ... DISABLE/NO FORCE ROW LEVEL SECURITY`. The ADR says: only migrations do this; any migration that touches RLS state needs CISO review (CODEOWNERS on `db/migrations/`), and C-1 runs on every CI build so a disabled table fails the build. | Written + CODEOWNERS. | C-1 in CI. |
| 1.6 | `cp_app` has no `TRUNCATE`, `REFERENCES` or `TRIGGER` on any table (TRUNCATE ignores RLS). | All false. | catalog: `has_table_privilege('cp_app', c.oid, 'TRUNCATE')` false for every table. |
| 1.7 | Superuser use is limited to role/ACL migrations and break-glass; every superuser session is logged by the operator (who, when, why) in the ops log. Superuser password rotated after any TCP-proxy session (T-H2). | Written in ADR + runbook. | Review. |
| 1.8 | Data migrations that must cross orgs (backfills) run as `cp_migrator` under FORCE by setting a documented context or are done by the operator as superuser in a reviewed, one-off script. `cp_migrator` never gets `BYPASSRLS` for convenience. | Written. | 1.2 catalog test. |

## 2. Context setting (`app.user_id`, `app.org_id`, `app.platform_role`)

| # | Criterion | Pass | Test |
|---|---|---|---|
| 2.1 | Context is set **only** with `select set_config('app.org_id', %s, true), set_config('app.user_id', %s, true), ...` with bind parameters, as the first statement of the transaction. Not `SET LOCAL app.org_id = '<f-string>'` (`SET` cannot take bind parameters, so it invites string interpolation), never `SET` (session) and never `set_config(..., false)`. | One function in `app/` sets context; no other occurrence. | CI grep: fail on `set_config\([^)]*,\s*false\)`, `\bSET\s+app\.`, `SET LOCAL app\.` in `app/` (except tests that prove the failure modes). |
| 2.2 | Values come from the server-side session row (`user_session` → `app_user` → verified `membership`), never from a request parameter, header or form field. The org is chosen by the user only among orgs the session's user is a member of. | Code review + test. | App test: request with a forged `org_id` parameter for an org the user is not in → 403/404 and no query runs with that org. |
| 2.3 | Missing context ⇒ deny. Policies read context through `stable` helpers: `app_ctx_org()` = `nullif(current_setting('app.org_id', true), '')::uuid`, same for `app_ctx_user()`. `current_setting(..., true)` returns NULL when the setting was never defined; after a `SET LOCAL` ends, the placeholder stays defined with value `''` — hence `nullif`. A NULL compares to nothing, so no row passes. No `coalesce` to a wildcard, no "if unset then all orgs" branch, no default value in `ALTER ROLE/DATABASE ... SET app.*`. | Helpers as written; `pg_db_role_setting` has no `app.*`. | T-CTX-1: fresh connection, no context: `select count(*)` on every tenant table = 0; `insert` into every tenant table → `42501` ("new row violates row-level security policy"). T-CTX-2: same after a previous transaction on the same connection set and committed context (proves `''` handling). T-CTX-3: `app.org_id = 'garbage'` → error `22P02`, no rows. Catalog: no `app.%` in `pg_db_role_setting.setconfig`. |
| 2.4 | `app.platform_role` can only **narrow** what `cp_app` sees, never widen it. No `cp_app` policy contains `or app_ctx_platform_role() = 'superadmin'`. Cross-org access is a separate design (§5). | No permissive policy for `cp_app` references `platform_role` as a grant. | catalog: `select * from pg_policies where 'cp_app' = any(roles) and qual ilike '%platform_role%'` reviewed (expected: none, or only inside restrictive policies). T-SA-1: as `cp_app` with `app.platform_role = 'superadmin'` and org A context → cannot see org B rows. |
| 2.5 | Defence in depth on the org: the base restrictive policy checks both the org setting and that the user setting is an active member of that org (`app_ctx_org() in (select member_organisation_ids(app_ctx_user()))`), so an app bug that sets the wrong org for a valid user still fails. | Present on tenant tables, or a documented performance exception with numbers. | T-CTX-4: user U (member of A only), context `org_id = B` → 0 rows, inserts `42501`. |

## 3. Pooled connections (psycopg 3 `ConnectionPool`)

| # | Criterion | Pass | Test |
|---|---|---|---|
| 3.1 | Tenant queries run only inside the pool's transaction block (`with pool.connection() as conn:` is non-autocommit; the pool commits/rolls back on exit). The context-setting function is the only way routes obtain a tenant connection (e.g. `Database.tenant(session)`); raw `pool.connection()` is not used by routes. | Code + lint. | CI grep: no `.connection()` outside `db/` module. |
| 3.2 | No autocommit connection ever runs tenant queries. In autocommit, `SET LOCAL` outside a transaction block emits a warning and has no effect; `set_config(..., true)` applies to that one statement only. Both must lead to deny, never to a stale context. | Behaviour proven. | T-POOL-1: autocommit connection: `set local app.org_id = A` then `select count(*) from farm` → 0. T-POOL-2: autocommit: `select set_config('app.org_id', A, true)` then a second statement → 0 rows. |
| 3.3 | Pool `reset` callback clears context belt-and-braces: runs `RESET ALL` (or `set_config('app.*', '', false)` for each key) and asserts `app_ctx_org() is null`; on failure the connection is discarded. | Callback present. | T-POOL-3 (leak test, real pool, `max_size=1`, real `cp_app` login, not the rolled-back test harness): request 1 sets context org A, reads, commits, returns; request 2 takes the same connection (assert same `pg_backend_pid()`), sets **no** context → 0 rows on every tenant table. Repeat with request 1 ending in an exception (rollback path) and with request 1 using session `SET app.org_id` deliberately (proves the reset callback, since that is the case 3.3 exists for). |
| 3.4 | If PgBouncer or any external pooler is added later: transaction pooling only, and the ADR is re-reviewed. | Written. | Review. |
| 3.5 | Context is per transaction: a long request that runs several transactions sets context in each. | Code. | T-POOL-4: two transactions on one checkout, context set in the first only → second sees 0 rows. |

## 4. Policies

| # | Criterion | Pass | Test |
|---|---|---|---|
| 4.1 | Separate policies per command (`for select`, `for insert`, `for update`, `for delete`) or `for all` with an explicit `with check`. Every `INSERT` and `UPDATE` policy has `WITH CHECK (organisation_id = app_ctx_org())`; `UPDATE` has both `USING` and `WITH CHECK` so a row cannot be moved to another org. | 100 % of insert/update policies have non-null `with_check`. | catalog: `select * from pg_policies where cmd in ('INSERT','UPDATE','ALL') and with_check is null and qual is null` = 0 rows. T-W-1: org A context: `update farm set organisation_id = B where ...` → `42501`. T-W-2: insert with `organisation_id = B` → `42501`. |
| 4.2 | The org boundary is a **restrictive** policy (`as restrictive`) on every tenant table; role-specific permissions (e.g. farmer read-only) are permissive policies on top. A later broad permissive policy then cannot widen past the org. | Restrictive base policy on every tenant table. | catalog: each tenant table has ≥1 policy with `permissive = 'RESTRICTIVE'` whose `qual` and `with_check` reference `app_ctx_org()`. |
| 4.3 | Policies are scoped `TO cp_app` (and `cp_website` for `pilot_request` insert only), never `TO public`. | No `public` in `pg_policies.roles`. | catalog. |
| 4.4 | Authorship columns are bound to the context: `WITH CHECK (created_by = app_ctx_user())` on `recommendation`, `application_log`, `proof_document`; `WITH CHECK (reviewer_id = app_ctx_user())` on `review`. | Present. | T-W-3: context user U inserts a review with `reviewer_id = V` → `42501`. |
| 4.5 | Identity tables: `app_user` — self, plus users sharing an org (columns limited; `password_hash`, `totp_secret` never selectable by the generic app path, column grants). `membership` — rows of the current org. `user_session` — own rows. The **pre-auth paths** (login by email, session lookup by `token_sha256`, which run before a user context exists) are explicit `SECURITY DEFINER` functions returning the minimum (e.g. `session_lookup(token_sha256) returns (user_id, expires_at, revoked_at)`), not a policy hole like `using (app_ctx_user() is null)`. | Written + implemented. | T-ID-1: no context: `select * from app_user` / `user_session` → 0 rows. T-ID-2: `session_lookup` with a wrong hash → no row; with a right hash → only that user's id. T-ID-3: user of org A cannot list users of org B. |
| 4.6 | FK and unique checks bypass RLS (docs), so errors are an existence oracle across orgs. Composite FKs on `(organisation_id, id)` (already in 0004–0008) mean a cross-org reference fails as "no such key" for the attacker's own org; the ADR accepts the residual (UUIDv4 ids are not guessable; `app_user.email` uniqueness reveals that an email exists — accepted or mitigated at the login UI). | Written. | T-FK-1: org A context, insert `field` referencing a `farm` id of org B → fails (FK or RLS), never succeeds. |
| 4.7 | `pilot_request`: RLS enabled, one insert policy `to cp_website with check (status = 'new' and deleted_at is null)`, no select policy for `cp_website`; staff read path defined separately (`docs/security/website-db-role-spec.md` §1). | As written. | Spec tests T1–T16 still pass with RLS on. |

## 5. Superadmin / `platform_role`

| # | Criterion | Pass | Test |
|---|---|---|---|
| 5.1 | Cross-org access (support, ops) does not run through `cp_app`. Preferred: a separate NOLOGIN role `cp_admin` (login used only by an admin CLI or a separate admin process, never by the public web app) with **no direct table privileges**; it reads/writes only through `SECURITY DEFINER` `admin_*` functions. | ADR picks a design; if it keeps superadmin inside `cp_app`, it records that SQL injection in the app = full cross-tenant access, and Farjad Iranmehr accepts it in writing. | T-SA-2: as `cp_admin`, `select * from farm` → `42501`. |
| 5.2 | Every superadmin access writes an `audit_event` row (actor, action, target org/table/id, reason text non-empty, timestamp) **in the same transaction** as the access; reads included (via the `admin_*` functions, since triggers do not fire on SELECT). `audit_event` is insert-only (`forbid_change` triggers, no UPDATE/DELETE/TRUNCATE grant to anyone but the owner). | Implemented. | T-SA-3: `admin_read_farm(id, 'support ticket 12')` returns the row and `audit_event` count +1 with the reason; empty reason → error, no data returned. T-SA-4: `update/delete/truncate audit_event` as `cp_app`/`cp_admin` → `42501`. |
| 5.3 | MFA required for superadmin accounts (R3) and superadmin role grants are themselves audited. | Written. | App test (S5). |
| 5.4 | `superadmin` / `platform_role` gives **no** approval right (rule 8). Approval still requires `account_kind = 'human'` and an active `agronomist` membership in the recommendation's organisation; no `admin_*` function can insert an `approve` review or a `proof_document`. | DB trigger unchanged by platform role; no definer function writes `review`/`proof_document`. | T-SA-5: superadmin without agronomist membership inserts `approve` (directly and via every `admin_*` function) → `42501`. T-SA-6: superadmin who is also a human agronomist of that org → allowed and audited. |

## 6. SECURITY DEFINER functions, views, triggers

| # | Criterion | Pass | Test |
|---|---|---|---|
| 6.1 | Every view in `public` has `security_invoker = true` (PG 15+), otherwise it runs with the owner's rights and, if the owner is exempt or the table is not FORCEd, skips RLS. `recommendation_diff` already complies (0009). No materialized views over tenant data granted to `cp_app` (RLS does not apply to matview contents). | 100 %. | catalog: `select relname from pg_class where relkind = 'v' and relnamespace = 'public'::regnamespace and not coalesce('security_invoker=true' = any(reloptions), false)` = 0 rows (exclude PostGIS `geometry_columns`/`geography_columns` by name); `relkind = 'm'` with `cp_app` SELECT = 0. T-V-1: org A context: `select count(*) from recommendation_diff where organisation_id = B` = 0. |
| 6.2 | Every `SECURITY DEFINER` function is listed in the ADR with a reason, has `set search_path = pg_catalog, public` (pinned; `pg_temp` not first), `revoke execute ... from public`, `grant execute` only to the role that needs it, validates its arguments against the context (no "give me any org's X"), and returns the minimum columns. | 100 % of `prosecdef` functions in `public` meet this. | catalog: `select proname from pg_proc where prosecdef and pronamespace = 'public'::regnamespace and (proconfig is null or not exists (select 1 from unnest(proconfig) c where c like 'search_path=%'))` = 0 rows; and `has_function_privilege('public', oid, 'EXECUTE')` false for each. |
| 6.3 | Trigger functions run as the invoking role, so under RLS `review_check_reviewer` → `has_org_role` / `member_organisation_ids` read `membership` and `app_user` **through the policies**. The ADR shows they still work for the legitimate case and fail closed otherwise. If they are turned into `SECURITY DEFINER` to see past RLS, 6.2 applies and the argument must equal `app_ctx_user()`. | Behaviour proven. | T-TR-1: agronomist of org A approves a recommendation of org A under RLS → succeeds. T-TR-2: same user, context org B → `42501`. T-TR-3: `proof_document_check_approved` under RLS still sees the approval row. |
| 6.4 | Helpers used in policies (`app_ctx_*`, `member_organisation_ids`) are `stable`, have pinned `search_path`, and are owned by `cp_migrator`; `cp_app` cannot replace them (no `CREATE` on schema, not owner). | As stated. | catalog: owner + `provolatile = 's'` + `proconfig`. |

## 7. AI agronomist (D4) — enforced in the database

| # | Criterion | Pass | Test |
|---|---|---|---|
| 7.1 | `app_user` gets `account_kind` (`human` / `ai_agent` / `service`), `not null`, **no default** (every insert states it), and immutable after insert (trigger raising on change). `cp_app` gets column-level `UPDATE` on `app_user` that excludes `account_kind`, `password_hash` is handled per T-O2. | Forward migration. | T-AI-1: `update app_user set account_kind = 'human' where account_kind = 'ai_agent'` as `cp_app` → `42501`; as `cp_migrator` → trigger error. |
| 7.2 | `review_check_reviewer` rejects `decision = 'approve'` unless the reviewer is `account_kind = 'human'` **and** an active `agronomist` member of the org (existing check kept). AI output is recorded as a distinct decision/label `ai_reviewed`, never `approve`. | Trigger + enum change. | T-AI-2: `ai_agent` user with an `agronomist` membership inserts `approve` → `42501`. T-AI-3: `ai_reviewed` insert succeeds and does **not** satisfy `proof_document_check_approved` (proof insert → `23514`). |
| 7.3 | An `ai_agent` cannot hold the `agronomist` membership role at all (trigger on `membership` insert/update), so it can also not satisfy any app-level role check. | Trigger. | T-AI-4: insert `membership(role = 'agronomist')` for an `ai_agent` user → error. |
| 7.4 | No AI approval anywhere (rule 11): no demo/synthetic exception. Separately, rule 8 needs a real/synthetic flag on `farm` (e.g. `is_synthetic boolean not null default false`, immutable after insert, settable only by the migrator/seed) so "real" is the default; it may gate test fixtures, never AI approval. | ADR records it. | T-AI-5: AI `approve` on a synthetic farm → `42501`. T-AI-5b: `update farm set is_synthetic = true` as `cp_app` → error. |
| 7.5 | Audit query in the ops runbook: approvals by non-human reviewers = 0. | Query documented and run weekly. | T-AI-6 (catalog-style): `select count(*) from review r join app_user u on u.id = r.reviewer_id where r.decision = 'approve' and u.account_kind <> 'human'` = 0 on seeded data. |
| 7.6 | Rule 11: `ai_reviewed` rows are excluded from `recommendation_diff` / the calibration dataset and from the 90 % agreement metric. | View/query filter on reviewer `account_kind = 'human'` and decision. | T-AI-7: an `ai_reviewed` row never appears in `recommendation_diff`. |
| 7.7 | Rule 12 (data boundary): accounts with `account_kind <> 'human'` get no read access to personal or identifiable farm data (names, contacts, `field_geometry`, free-text notes) — only synthetic farms or de-identified views. Enforced in RLS/policies, not only in the app. | Restrictive policy on identifying tables for non-human context; de-identified view if AI needs real-case shapes (requires DPA + notice per rule 12). | T-AI-8: with an `ai_agent` user context, `select` from `farmer`, `farm`, `field_geometry` for a real farm → 0 rows / `42501`. |

## 8. Performance

| # | Criterion | Pass | Test |
|---|---|---|---|
| 8.1 | Every tenant table has an index whose **leading** column is `organisation_id`. | 100 %. | catalog: tenant tables without an index where `indkey[0]` = the `organisation_id` attnum = 0 rows. |
| 8.2 | Policies call context helpers as `(select app_ctx_org())` so they are evaluated once per statement (initplan), not per row; membership check in 2.5 likewise. | Policy text. | T-PERF-1: `explain` of `select * from field where id = $1` and of a list query on a seeded 100k-row table shows an index scan and an `InitPlan` for the context; no seq scan on tenant tables > 10k rows. |
| 8.3 | Budget: p95 of the S3 route set with RLS on is within +20 % of RLS off on the seed dataset (estimate; the ADR may set its own number but must set one). | Measured. | Benchmark script output attached to the PR. |

## 9. Required negative test list (S3 suite, all must exist and assert SQLSTATE)

| Test | Proves |
|---|---|
| Cross-org read: org A context, `select` every tenant table + `recommendation_diff` filtered to org B ids → 0 rows | 4.2, 6.1 |
| Cross-org write: insert/update/delete with org B ids or moving rows to org B → `42501` / 0 rows affected | 4.1 |
| Missing context: T-CTX-1, T-CTX-2, T-CTX-3 | 2.3 |
| Wrong org for valid user: T-CTX-4 | 2.5 |
| Pooled-connection leak: T-POOL-1 … T-POOL-4 with a real pool and real login | §3 |
| Owner is filtered: as `cp_migrator` with no context → 0 rows (FORCE) | 1.4 |
| No bypass roles: catalog 1.1–1.3, 1.6 | §1 |
| Superadmin: T-SA-1 … T-SA-4 | §5 |
| AI approve rejected + data boundary: T-AI-1 … T-AI-8, superadmin no-approve T-SA-5/6 | §5, §7 |
| Authorship forging: T-W-3 | 4.4 |
| Pre-auth paths: T-ID-1 … T-ID-3 | 4.5 |
| Definer/view/trigger: T-V-1, T-TR-1 … T-TR-3, catalog 6.2 | §6 |
| Coverage: C-0, C-1 | 0.3, 1.4 |

Catalog C-1 (runs in CI on every build):

```sql
select c.relname
from pg_class c
where c.relnamespace = 'public'::regnamespace and c.relkind in ('r', 'p')
  and c.relname not in ('schema_migrations', 'spatial_ref_sys')   -- allowlist from db/rls_tables.yaml
  and not (c.relrowsecurity and c.relforcerowsecurity
           and exists (select 1 from pg_policy p where p.polrelid = c.oid));
-- expect 0 rows
```

Test-harness note: `app/tests/db/conftest.py` runs each test as superuser with `set local role cp_app` inside one rolled-back transaction. That is fine for policy tests (`cp_app` is subject to RLS), but §3 tests must open a real `ConnectionPool` with a real `cp_app_login`, or they prove nothing about leaks.

## 10. What the ADR text must contain (checklist for the reviewer)
- [ ] Scope and non-goals (§0), residual risk signed off.
- [ ] Table classification + allowlist file (0.3).
- [ ] Role matrix: owner, app, website, admin, backup, migrator; who bypasses and why (§1).
- [ ] Context contract: names, types, who sets them, `set_config(..., true)` only, deny-by-default (§2).
- [ ] Pool contract: transaction-only, reset callback, no autocommit tenant queries (§3).
- [ ] Policy patterns per table class (§4), pre-auth functions listed.
- [ ] Superadmin design + audit (§5).
- [ ] Definer function inventory (§6).
- [ ] AI-agronomist DB enforcement (§7).
- [ ] Index plan + performance budget (§8).
- [ ] Rollout: forward-only migrations; enable RLS table by table with the suite green; rollback = a new migration, never editing an applied one.
