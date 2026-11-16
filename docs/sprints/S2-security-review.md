# S2 security review + retro (ciso) — Nov 30 – Dec 11, 2026

Owner: `ciso` → `security-engineer` (×2), `devops-engineer`, `legal-compliance-specialist`.
Written 2026-11-16 (S2 work started early). Desk review only: no production, no Railway changes.

## What is now true (evidence in `docs/security/`)
| Deliverable | File | Status |
|---|---|---|
| Threat model (STRIDE, DFD, owners per sprint) | `threat-model-webapp.md` | done |
| Step 5 auth review (`webapp-step5-app` @ c720eec) | `S2-auth-review-step5.md` | done — 0 BLOCKER in diff, 8 SHOULD-FIX, 10 NOTE |
| Secret + dependency scan, all refs | `secret-and-dependency-scan-2026-11.md` | done — 0 secrets, 0 vulns, 1 Low |
| CI security checks | `.github/workflows/security.yml`, `.github/dependabot.yml` | proposed in this PR (gitleaks, pip-audit, npm audit, dependency-review; SHAs verified) |
| Railway hardening | `railway-hardening.md` | done (dashboard items "unknown") |
| Backup/restore test plan (S3–S5) | `backup-restore-test-plan.md` | done |
| Privacy posture | `privacy-posture.md` | done (gov sources marked [re-verify]) |
| Release gate checklist (S5) | `release-gate-checklist.md` | draft |

## Ranked findings for the CPO
**BLOCKER (outside the Step 5 diff)**
- B1 `docs/runbook-db-switch.md:24` — the website switches to `${{postgis.DATABASE_URL}}` = superuser. Public website compromise ⇒ all farm data + triggers disabled. Fix: `cp_website` role with INSERT on `pilot_request` only, before the switch. Owner: cto (`cp-database`, `cp-website`).

**SHOULD-FIX (Step 5, owner: web-app session)**
- S1 rate limit keyed on (email, proxy IP) ⇒ anyone can lock out the agronomist; XFF spoofing if proxy trust is `*` — `app/cloverproof_app/web.py:82-85`, `ratelimit.py:29-31`.
- S2 unauthenticated argon2 flood (64 MiB × 40 threads) — `security.py:15`, `web.py:122-139`.
- S3 CLI password reset keeps old sessions; no revoke-all — `cli.py:91-94`, `repo/sessions.py:54-58`.
- S4 nothing stops the app connecting as superuser — `db/pool.py:29-35`, `config.py:52-62`.
- S5 `cp_app` can write `membership` ⇒ can self-grant agronomist and pass the approval trigger — `db/migrations/0003_identity.sql:84`, `0007_review.sql:35-48`.
- S6 absolute `url_for` URLs break behind TLS proxy; no TrustedHost — `templates/base.html:8-10`.
- S7 CI does not run DB/auth tests — `.github/workflows/ci.yml:37`.
- S8 no HSTS — `main.py:29-37`.

**Other SHOULD-FIX (platform/website)**
- Website logs raw pg error incl. name/email — `website/src/app/[lang]/actions.ts:48`.
- `main` unprotected, secret scanning + push protection off (GitHub settings, Farjad Iranmehr).
- No independent backup of DB or proof PDFs; buckets have no versioning.
- `ci.yml` actions pinned by tag, not SHA (Low).

## Decisions for Farjad Iranmehr
1. Legal entity + privacy contact (blocks privacy notice, CASL consent, breach reports).
2. Backup destination: off-Railway object-lock storage (~<$1/mo, new vendor) vs second Railway project.
3. PostGIS image: plain `postgis/postgis` (no TLS/PITR) vs custom on Railway `postgres-ssl`.
4. Railway region (record in ADR 0004); staging environment from S3; plan tier (2FA enforcement).
5. GitHub: protect `main`, enable secret scanning + push protection + Dependabot alerts (free).
6. Deletion model: pseudonymise identity, keep immutable agronomic rows (counsel to confirm); proof PDF without farmer name/map.

## Retro
- Slowed us: Step 5 branch not pushed (reviewed locally); one specialist hit its turn limit before writing (re-briefed narrower from its artefacts); gov.ca sites blocked from this environment; no dashboard access ⇒ many "unknown".
- Change for S3: brief specialists with one deliverable each and "write the file first"; get a read-only Railway viewer check done by Farjad Iranmehr (15 min) to close the "unknown" items.
- Still open for S2 end: re-review Step 5B (approval route, reviewer_id from session) when it lands; run the 83 DB/auth tests against local PostGIS.

## Addendum — CPO backend-plan scope (section 2: REC-R8, NB-SEC-01/02/04, SC-11; with cto SC-02, SC-03, REC-D1, XD-07, DD-06)
| Item | File | Status |
|---|---|---|
| PR #7 delta review (c720eec→85814b6) | `docs/security/S2-review-pr7-delta.md` | 1 BLOCKER, 4 SHOULD-FIX, 6 NOTE; S1–S8: S3 fixed, 7 open (S5 worse) |
| Website least-privilege DB role (runbook BLOCKER) | `docs/security/website-db-role-spec.md` | spec + SQL for `0011_website_role.sql` (cp-database to adopt) |
| ADR 0006 RLS review criteria (NB-SEC-02) | `docs/security/adr-0006-rls-review-criteria.md` | ready; applied when cp-database drafts ADR 0006 |
| Licence check in CI (XD-07, DD-06) | `.github/workflows/security.yml` job `licenses` | passes locally (macOS); LGPL exceptions psycopg + sharp-libvips → ADR + lawyer |
| Secrets rotation (SC-03) | `docs/security/secrets-rotation.md` | done |

**New BLOCKER (D4):** no human/service distinction — an owner can create an AI account with `agronomist` role and the approval trigger accepts it (`db/migrations/0007_review.sql:43-47`, `app/cloverproof_app/account.py:225-261` @85814b6). Fix: `app_user.account_kind` (human|service, immutable), DB trigger rejects approve unless human agronomist, AI output as `ai_reviewed` only. Must land before any AI reviewer account or real-farm plan.
**Runbook:** step 4 must not run until `cp_website` exists, its checks pass, and the website pre-deploy `db:migrate` is removed (it will fail under `cp_website`; no migrator credential on the website service).
**Still waiting:** S1–S8/F1–F4 fixes on #7 (web-app session) → re-review; ADR 0006 draft (cp-database); S3 residency + DPA with coo; backup plan already covers the bucket gap.
