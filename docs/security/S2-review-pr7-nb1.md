# S2 review, PR #7: NB1 delta check at 77df916

Reviewer: security-engineer (for ciso). Date: 2026-11-16. Scope: fix commit 77df916 (NB1), plus a skim of e981555 (0013 site_event) and ccb2a16 (MIT-0 allowlist). Read-only checkout; nothing committed.

## Verdict: ACCEPT WITH NOTES

NB1 as reported is closed. An owner can no longer reset, disable or enable a superadmin, agronomist or owner account on the web, and the database refuses the same writes from cp_app (0014). One Medium residual (N1) reaches the same end state, an owner signing in as a superadmin, by a different route that depends on the operator's CLI step. Fix it before the first superadmin is promoted from an existing staff account.

Counts: Critical 0, High 0, Medium 1, Low 1.

## Findings

### N1 (Medium): an owner-known temporary password survives CLI promotion to agronomist, owner or superadmin
- Evidence: `app/cloverproof_app/cli.py:121` (`add_membership`) and `:123` / `:139` (`set_platform_role`) promote an existing account and leave `password_hash`, `password_change_required` and `temp_password_expires_at` as they are. 0014 checks the target's role only at the moment the password is written (`db/migrations/0014_app_user_cli_only_guard.sql:39-41`), not when a role is granted later.
- Exploit: the owner creates a staff account (`repo/admin_users.py:145`, temporary password shown to the owner) or resets one (`:249`, allowed for staff). Within 72 h the operator runs `user-create --role agronomist` or `--platform-role superadmin` (or `user-set-platform-role`) for that person without `--reset-password`. The intended setup puts the superadmin in the org as staff, so this is the normal path. The owner then signs in with the temporary password. The forced password change is allowed because it counts as the holder's own change (`0014:36-37`), so the owner now holds the account and can approve as `superadmin_approved` or as the agronomist.
- Reproduced on a throwaway DB (probe 13): after an owner reset followed by a cp_admin grant of agronomist and superadmin, the owner's temporary hash was still in place, `password_change_required` was true and expiry was set. Probe 14: the "own" change as that user then succeeded.
- Fix (pick one, test it in `test_nb1_cli_only_accounts.py`):
  1. CLI: in `user_create` and `user_set_platform_role`, when the role or platform role being granted is approver-level and the account has `password_change_required`, refuse unless `--reset-password` is given. Preferred: it is simple and puts the decision in front of the operator.
  2. DB (stronger): add an AFTER INSERT trigger on `membership` (role in agronomist/owner) and an UPDATE OF platform_role trigger on `app_user`. If a temporary password is pending, set `password_hash = null`, which forces a CLI reset.
- Fixed: no. Out of scope for this read-only check.

### N2 (Low): cp_app can rename any account, superadmins included
- Evidence: `db/migrations/0011_least_privilege_roles.sql` grants cp_app `update (display_name)` with no row bound. 0014 does not cover `display_name`. Probe 6: cp_app_login renamed the superadmin. Today the app writes it only for the caller (`account.py:129`).
- Impact: a compromised app, or a future route bug, can change the approver name shown on screens and possibly in proof records. This is not a takeover. Email is not writable (probe 7: 42501), so the login identity is safe.
- Fix: add `display_name` to the 0014 column list and the self-exception, or record it in admin_event. Fixed: no.

## What was checked (results)
| Check | Result |
|---|---|
| Route: reset, disable and enable of a superadmin, agronomist or another owner refused | Pass. `repo/admin_users.py:245` and `:257`. Template hides the actions (`admin_user.html` at 77df916). Tests cover all three. |
| Own-account disable by an owner is still allowed; last-owner rule intact | Pass. `:257` allows `member.id == actor_id`. |
| DB trigger as cp_app_login (INHERIT member of cp_app) | Refused, 42501 (probes 1, 2, 11 with no actor) |
| NOINHERIT login plus `SET ROLE cp_app` | Refused (probe 3). `pg_has_role(..., 'member')` counts membership regardless of INHERIT, and current_user becomes cp_app. |
| Trigger not SECURITY DEFINER, so current_user is the real invoker; search_path pinned | Confirmed: `prosecdef = false`, `search_path=""` |
| SECURITY DEFINER functions cp_app can call that write app_user (a bypass route) | None. The web_* functions write membership only. |
| Self-exception via app.user_id | The app sets it only from a verified session (`auth.py:125`) or after the password check (`web.py:163`). A compromised cp_app can still set any UUID (probe 5 passes). This is the accepted N-A1 limit, documented in 0014's header. |
| Column coverage | password_hash, password_change_required, disabled_at: guarded. email and temp_password_expires_at: not writable by cp_app (probes 7, 8). platform_role and actor_kind: no grant. display_name: see N2. |
| Trigger order (BEFORE) | `app_user_cli_only_guard` runs before `app_user_temp_password_expiry`. Neither changes the other's columns, so order does not matter. |
| CLI (cp_admin_login) reset of a superadmin | Allowed (probe 9). The test checks that admin_event `password_reset` is written. |
| A refused attempt leaves no change and no audit row | Pass. Covered by `test_refused_web_reset_leaves_no_audit_row`. |
| Staff reset by an owner (regression check) | Allowed (probe 10 plus tests) |
| 0013 site_event | cp_website has INSERT only on whitelisted columns. Strict CHECKs, no IP, UA or PII columns. No security weakening. Flood control belongs to the website endpoint (not reviewed here). |
| ccb2a16 | Adds MIT-0 to the Python licence allowlist. MIT-0 is more permissive than MIT. No security effect. |

## Tests run
- `make db-test` in the read-only checkout, against a throwaway `postgis/postgis:18-3.7` container on 127.0.0.1:55991 (never Railway): **339 passed**.
- `uv run pytest -q`: **318 passed, 336 skipped** (the DB tests skip without TEST_DATABASE_URL).
- Probe script outside the repo, against a separate database on the same throwaway container: 14 probes, results as cited above.
- The container was stopped and removed (`--rm`).
