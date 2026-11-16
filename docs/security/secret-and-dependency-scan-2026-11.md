# Secret and dependency scan — 2026-11

Date: 2026-11-16. Author: security-engineer (reports to CISO). Branch: `myca/security-s2-bb8ef7`. Static, read-only, local only; no production host touched.

## Summary

| Severity | Count |
| --- | --- |
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 1 (CI actions pinned by tag, not SHA) |

No secrets found in the working tree or in any ref's history. No known vulnerabilities in Python (main, webapp-step5-app) or website npm production dependencies. Vendored htmx matches the npm registry tarball byte for byte and has no known advisory.

Most important fix: pin `actions/checkout` and `astral-sh/setup-uv` in `.github/workflows/ci.yml` to commit SHAs (same SHAs `security.yml` already uses).

## Method

| Step | Tool / version | Scope |
| --- | --- | --- |
| History secret scan | gitleaks (earlier run in this session; binary not on PATH now, version not recorded) | all refs at scan time: 63 commits |
| History secret scan | trufflehog (earlier run; `--no-verification` results only, 0 verified) | all refs, 506 chunks, ~1.17 MB |
| Added-file names | `git log --all --diff-filter=A --name-only` grep `\.env|secret|\.pem|\.key|credential` | all refs, 73 commits |
| Pattern grep | `git log --all -p` grep for `postgres(ql)?://user:pass@`, `RAILWAY_TOKEN`, `SESSION_SECRET=`, `AKIA[0-9A-Z]{16}`, `BEGIN .*PRIVATE KEY`, emails, North-American phone numbers | all refs, 73 commits (30,088 patch lines) |
| Python deps | pip-audit 2.10.1 (OSV/PyPI), `--no-deps --disable-pip` on `uv export --frozen --no-hashes --all-packages --all-groups` output | `main` (44 pins) and `webapp-step5-app` (51 pins), all groups incl. dev |
| npm deps | npm 11.6.1 `npm audit --omit=dev` and full `npm audit` | `website/` lockfile (28 prod, 379 dev, 448 total) |
| Vendored JS | sha256 compare + OSV API query (`htmx.org`, npm) | `webapp-step5-app:app/cloverproof_app/static/vendor/htmx-2.0.11.min.js` |
| CI | manual review of `uses:` lines | `.github/workflows/ci.yml`, `.github/workflows/security.yml` |

Refs covered: all local branches (`main`, `cpo-sprint-roadmap`, `data/open-data-sources`, `engine-external-refs`, `webapp-step4-db`, `webapp-step5-app`, `website-v1`, `myca/*`) and `origin/*` remotes including `origin/webapp-step3-engine`.

Note: the earlier gitleaks/trufflehog run saw 63 commits; `git rev-list --all` now returns 73 (other sessions committed since). The pattern grep in this run covered all 73; gitleaks/trufflehog did not re-run (by instruction). The new CI job in `security.yml` will cover them on push.

## Secret findings

None are real secrets. Values masked.

| # | Source | Location | Pattern | Classification | Action |
| --- | --- | --- | --- | --- | --- |
| 1 | trufflehog (unverified) | `app/tests/test_migrate_files.py:63` (commit 6ad5dc7) | Postgres URL `postgresql://u:***@db.example.internal:5432/db` | Test fixture. 1-char password, reserved `example.internal` host; tests that non-local hosts are refused. | None |
| 2 | trufflehog (unverified) | `app/tests/test_migrate_files.py:64` (6ad5dc7) | `postgresql://u:***@localhost,db.example.internal/db` | Test fixture (multi-host bypass case) | None |
| 3 | trufflehog (unverified) | `app/tests/test_migrate_files.py:82` (6ad5dc7) | `postgresql://u:***@db.example.internal:5432/db` via `monkeypatch.setenv` | Test fixture | None |
| 4 | grep | same test file, `127.0.0.1` / `localhost` cases | Postgres URL, 1-char password | Test fixture | None |
| 5 | grep | `Makefile` (local example comment) | `postgresql://postgres:***@127.0.0.1:5432/cloverproof` | Local docker default credential (`postgres`), localhost only. Not a secret. | None; keep it local-only |
| 6 | grep | `docs/runbook-db-switch.md` | `postgresql://${{POSTGRES_USER}}:***@${{RAILWAY_PRIVATE_DOMAIN}}...` | Railway variable reference, not a value | None |
| 7 | name scan | `.env.example` | only `.env*` file ever added | Template; per CLAUDE.md rule 10 values must stay empty | None |

Zero hits for `RAILWAY_TOKEN`, `SESSION_SECRET=` with a value, `AKIA…`, or PEM private keys in any ref. No `.pem`, `.key` or credential files ever committed.

Personal data:
- All emails in seeds/tests/docs are on `example.org` / `x.org` / `b.org` placeholder domains, or `p@db.example.internal` (a URL fragment). Fixtures, not real people.
- No phone numbers found.
- Commit author emails (`farjad@live.com`, a GitHub noreply address) and `noreply@anthropic.com` co-author trailers are expected, not findings. Author emails become public in git history once the repo is pushed to GitHub. If that matters, set `user.email` to the GitHub noreply address for future commits; rewriting history is not recommended.

Rotation: nothing to rotate.

## Dependency findings

Ranked by severity, then reachability.

| Ecosystem | Scope | Result |
| --- | --- | --- |
| Python, `main` | 44 pins (engine, app, dev tools) | No known vulnerabilities (pip-audit / OSV) |
| Python, `webapp-step5-app` | 51 pins (adds argon2-cffi and others for the app) | No known vulnerabilities |
| npm, `website/` prod | 28 packages (next 16.4.6, react / react-dom 19.3.0) | 0 vulnerabilities |
| npm, `website/` all | 448 packages incl. dev | 0 vulnerabilities |
| Vendored htmx 2.0.11 | `static/vendor/htmx-2.0.11.min.js` | sha256 `d6fdc75f…f717` matches `package/dist/htmx.min.js` from `htmx.org-2.0.11.tgz` downloaded twice on its own (tarball sha256 `165a2655…408e`, both identical), and matches the README integrity table. OSV has no advisories for `htmx.org` on npm. A web search found no official GHSA/CVE for htmx 2.x; one page on htmx.org (`cve-2026-3682-1`) reads as satire and is not a library CVE. |

Caveats:
- pip-audit ran `--no-deps` on a fully pinned export. Pins are not hashed in that input (hashes are in `uv.lock`), so this checks versions, not integrity.
- htmx is invisible to npm audit and Dependabot because it is vendored. It has to be re-checked by hand on every bump. The README procedure covers integrity but not advisories.
- No lockfile diff review was done in this run; there were no dependency changes to compare.

## GitHub Actions pinning

| File | Action | Pin | Finding |
| --- | --- | --- | --- |
| `.github/workflows/ci.yml:23` | `actions/checkout@v7` | tag | Low |
| `.github/workflows/ci.yml:25` | `astral-sh/setup-uv@v7` | tag | Low |
| `.github/workflows/security.yml` (new, untracked) | checkout, setup-uv, setup-node, dependency-review-action | full SHA + version comment | OK |

**L1: CI actions pinned by mutable tag.** If the upstream tag is retagged (as in the tj-actions/changed-files compromise), malicious code runs in CI. Impact is limited: `permissions: contents: read`, and the job uses no secrets. It could still tamper with test results or read the checkout. Fix: pin both actions to SHAs. Use the SHAs already verified in `security.yml` and let Dependabot (`.github/dependabot.yml`, github-actions ecosystem) bump them. Also note the drift: ci.yml uses `setup-uv@v7` and security.yml uses `v10.3.3`; align them. Not fixed in this run (report-only brief).

## Recommendations

1. Pin `ci.yml` actions to SHAs and align the setup-uv major version (L1).
2. Merge `security.yml` + `dependabot.yml` so gitleaks, pip-audit and npm audit run on every push. They would have covered the 10 commits made after this session's history scan.
3. Add a `.gitleaks.toml` allowlist for `app/tests/test_migrate_files.py` `example.internal` URLs so trufflehog/gitleaks noise doesn't train people to ignore hits. Scope it to that path, not to a regex.
4. Add a line to `static/vendor/README.md`: check the GitHub advisory database / OSV for `htmx.org` before each upgrade.
5. Optional: commit with the GitHub noreply email so a personal address doesn't go into public history.
6. Before the Railway deploy, confirm `SESSION_SECRET` / `DATABASE_URL` exist only as Railway variables. Railway's dashboard was not inspected here; see `docs/security/railway-hardening.md`.

## Not covered

- gitleaks/trufflehog over the 10 commits made after the earlier run (the pattern grep did cover them).
- Container/base-image scanning (no Dockerfile scanned), OS packages, WeasyPrint native libraries (Pango, cairo).
- Railway project variables, GitHub repo settings (secret scanning, push protection, branch protection).
- Stashes, reflog-only objects and other clones/worktrees outside this repo's refs.
- License compliance, and abandoned-package or typosquat review of the 448 npm packages beyond npm audit.
- Runtime/DAST testing of any kind.
