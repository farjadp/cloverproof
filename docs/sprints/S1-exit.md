# S1 exit test: 5 synthetic plans end to end

- **Date:** 2026-11-17
- **Run by:** cp-qa (AI agent), branch `s1-exit-test` from `origin/main` at `a4851ed`
- **Verdict:** **GO** for the S1 exit, with the conditions in "Verdict" at the end

All data in this test is synthetic ("Test Farmer 1" ... "Test Farmer 5", "Test Lab A (synthetic)", `*@example.test` accounts). No real farmer data was used. Agronomic numbers come from the **placeholder pack** and are not real agronomy.

## Scope

The concierge flow, driven over HTTP with a script (httpx, cookies and CSRF tokens, same requests the browser sends):

intake (farmer, farm, field, soil test or none) → engine run → agronomist edit with reason → human approve or reject → proof PDF generated and downloaded (SHA-256 checked again) → minutes recorded on every review.

Also checked: role gate (advisor), cross-organisation isolation, database immutability (grants and triggers), proof tamper detection, whether the ca-on v1 pack works from the UI today.

Out of scope: real agronomy, deployment, S3 storage, the farmer-facing app.

## Environment

| Item | Value |
|---|---|
| Machine | macOS (Darwin 25.3, arm64), Python 3.12 via `uv sync` |
| Database | local Postgres + PostGIS on `127.0.0.1:55432`, throwaway DB `cp_s1_exit_<random>` |
| Migrations | `make db-migrate`, 0001 to 0023 applied, "up to date" |
| DB logins | two temporary login roles: one in `cp_app` (the web app; not superuser, no BYPASSRLS, so RLS from 0021 applies) and one in `cp_admin` (CLI only) |
| Users | `make user-create` via the `cp_admin` login: agronomist (Test Org S1), advisor + platform role `superadmin` (Test Org S1), advisor (Test Org S1), agronomist (Other Test Org, for isolation) |
| App | uvicorn on `127.0.0.1:8137`, `ENV=development`, `COOKIE_SECURE=false`, random `SESSION_SECRET`, `PROOF_STORE_DIR` in a scratch dir, `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` |
| Pack | default `PACK_PATH` = `packs/placeholder/v0.yaml` (placeholder v0, status `placeholder`) |
| Engine | `cloverproof_engine` 0.3.0 |
| Cleanup | app stopped, DB dropped (`with (force)`), both temporary roles dropped, temporary passwords deleted. Checked: 0 databases and 0 roles named `cp_s1_exit%` left |

The walk script and its JSON output stayed in the agent's scratch directory; they are not committed.

## The 5 plans

Engine N and final N are kg N/ha (elemental). "Versions" counts the recommendation lineage for the delivered plan (1 = engine only, 2 = engine + one edit). Minutes are `review.minutes_spent` per review, in order.

| # | Farmer / field (area) | Soil test | Plan id | Recommendation versions (ids) | Engine N | Final N | Edit reason | Final review | Minutes per review | Proof document | Stored SHA-256 = download SHA-256 | PDF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Test Farmer 1 / Test Field 1A (40 ha) | Lab: P 12 mg/kg Olsen, K 110 mg/kg ammonium acetate, 0–15 cm, sampled 2026-10-01 | `e28a8e5f` | 2 (`9593dfe9` → `c947315c`) | 175.0 | 150.0 | "SYNTHETIC: lower N, high residual N expected after dry season" | approve, Test Agronomist, `agronomist_approved` | edit 1, approve 0 | `0c6eab90` | `a6d03c986845824c7e101896d6818331f180f4d0b67e11c6dcf0ab9988c2a3e5`, match | 5 pages, 42,643 B |
| 2 | Test Farmer 2 / Test Field 2A (25 ha) | Lab: P₂O₅ 40 mg/kg Mehlich-3, K₂O 180 ppm Mehlich-3, 0–20 cm, sampled 2026-09-15 | `496bbf5f` | 2 (`38ba3787` → `cdd7eca1`) | 137.5 | 170.0 | "SYNTHETIC: raise N, target yield history supports it" | approve, Test Agronomist, `agronomist_approved` | edit 0, approve 0 | `0771efe3` | `4f661e6bd7093f7f97c5a05251da896b367e96fb112e7321ac03e0a4ab87c51f`, match | 5 pages, 42,680 B |
| 3 | Test Farmer 3 / Test Field 3A (60 ha) | None (N only; P/K: "Recommend a lab soil test") | `4150de39` | 2 (`f9c86408` → `a74d02b1`) | 118.75 | 120.0 | "SYNTHETIC: no soil test, cautious N" | approve, Test Agronomist, `agronomist_approved` | edit 0, approve 0 | `b02a09e8` | `e1318b5cdcfc56344cb90f161b884c095c32edee2ecf5ec6ccbbf6ddf5d06ca1`, match | 5 pages, 42,432 B |
| 4 | Test Farmer 4 / Test Field 4A (12.5 ha) | None (N only; P/K: "Recommend a lab soil test") | `fe769be0` | 1 (`f1e7b063`) | 156.25 | 156.25 | none (approved as shown) | approve, Test Agronomist, `agronomist_approved` | approve 0 | `aa1817e4` | `aece9eb19796e7cc3d3e8795f2179617960e3dc935a381b4bc1e8f09753c3760`, match | 4 pages, 40,461 B |
| 5a | Test Farmer 5 / Test Field 5A (30 ha) | Lab: P 12 mg/kg Olsen, K 110 mg/kg ammonium acetate, 0–15 cm, sampled 2026-10-01 | `f811942b` | 1 (`3adcd24c`) | 175.0 | n/a | n/a | **reject**, Test Agronomist, reason "SYNTHETIC: wrong previous crop entered" | reject 0 | none (refused, 409) | n/a | n/a |
| 5b | same field, new plan after the reject | Lab, same values entered again | `c9b356a2` | 2 (`bcbe9f7f` → `b0dfa565`) | 175.0 | 140.0 | "SYNTHETIC: superadmin edit after reject, corrected previous crop" | approve, Test Superadmin, `superadmin_approved` (label shown on plan page and in PDF) | edit 0, approve 0 | `21b61cc0` | `66f002272113d3f4e909630fe39d155a72ab6defebd9e9c1fd7b4c3742e54095`, match | 4 pages, 39,871 B |

Mix requested vs done: 3 plans with a lab soil test (1, 2, 5), 2 without (3, 4), 4 agronomist/superadmin edits with reason (1, 2, 3, 5b), 1 reject followed by a new plan, 1 superadmin approval.

For every proof: the SHA-256 of the downloaded bytes equals `proof_document.sha256`, the `Repr-Digest` header carries the same hash, the storage key is `proof/{org}/{recommendation}/{sha256}.pdf`, and a second "Generate" POST returned the same document (no second render). Page counts by `pypdf`. Every PDF shows the PLACEHOLDER label, confidence, the approver's role and the edit reason.

### Average agronomist minutes per plan

Total recorded: 1 minute over 10 reviews (5 delivered plans plus the rejected one) = **0.2 minutes per delivered plan**. This is **not a real measure**: a script drove the forms in seconds. The single non-zero value comes from a deliberate 65-second wait on plan 1, to show that the timer counts whole minutes. The real number comes from the Feb–Apr 2027 concierge plans.

## Checks per CLAUDE.md rule

| Rule | Check | Result | Evidence |
|---|---|---|---|
| 2 Confidence on every recommendation | `recommendation.confidence` is NOT NULL and a CHECK requires it to equal `result.confidence`; shown on the page and in the PDF | PASS | All 10 recommendation rows (6 engine, 4 edits) have `confidence = low`. Expected: the placeholder pack caps confidence. The `high` and `medium` paths are not reachable from the UI with this pack (see Gaps) |
| 3 No soil test → N only, P/K "get a test", max medium | Plans 3 and 4 | PASS | `phosphorus_potassium.code = PK_SOIL_TEST_RECOMMENDED`, text "No soil test: phosphorus (P) and potassium (K) are not recommended. Recommend a lab soil test for P and K ...". Confidence `low` (≤ medium). With a test (plans 1, 2, 5), engine v0 still does no P/K (`PK_NOT_CALCULATED_V0`) |
| 4 Immutable, edit = new version | As the `cp_app` login, with the RLS context set for the owning org: UPDATE and DELETE on `recommendation`, `review`, `proof_document` | PASS | All six: `ERROR: permission denied for table ...`. UPDATE on a used `soil_test`: `soil test ... was used by a recommendation and is locked`. Even as superuser, UPDATE on `recommendation` is stopped by trigger `forbid_change()`. Edits created children with `parent_id` and a non-empty `reason`. Edit or second review after a final decision: 409 |
| 5 Snapshot and versions stored | `inputs_snapshot`, `engine_version`, `pack_id`, `pack_version`, `pack_status`, `pack_sha256` | PASS | Every row: engine `0.3.0`, pack `placeholder v0 placeholder`, non-empty snapshot. CHECK constraints tie each column to the `result` document |
| 7 Units, form, method, depth, date | `soil_test` + `soil_test_value` rows | PASS | Form stored per line (P, K, P2O5, K2O), unit (mg/kg, ppm), extraction method (olsen, ammonium-acetate, mehlich-3), depth top/bottom cm, sample date, source `lab`, lab name. N in kg N/ha elemental. One display defect, D2 |
| 8 Review gate: human agronomist or superadmin | Advisor tries to edit or approve; proof before approval; proof for a rejected plan | PASS | Advisor: GET edit 403, POST review 403. Proof before approval: 409. Proof for the rejected plan: 409. Superadmin (advisor role + platform `superadmin`) can approve → `superadmin_approved` |
| 11 AI review never approves; calibration only from agronomist | Calibration view `recommendation_diff`; proof rule | PASS (DB tests + code; no service account was used in this walk) | `recommendation_diff` holds plans 1–4 with engine vs final N, reason, approver and minutes. Plan 5b (superadmin) is left out, by design (only `agronomist_approved` is calibration data). The proof route refuses anything but a human approval (`app/cloverproof_app/proof_web.py:88-95`). `ai_reviewed` cases are covered by `make db-test` |

Other checks:

| Check | Result | Evidence |
|---|---|---|
| Org isolation over HTTP (Other Test Org agronomist) | PASS | Another org's plan, field, proof download and proof POST: all 404 |
| Proof tamper detection | PASS | Bytes appended to the stored file → download 500 "does not match the SHA-256", logged; file restored → 200 |
| Edit without reason / reject without reason | PASS | both 422, nothing saved |
| No secrets in git | PASS | `git log -p origin/main` scan for assigned keys/passwords/tokens: no hits outside tests and examples. This doc holds no credentials; DB passwords and the session secret were random, kept outside the repo, and deleted |
| `make lint` | PASS | `All checks passed!`, `260 files already formatted` |
| `make test` | PASS | `531 passed, 519 skipped, 1 warning in 17.88s` (DB tests skip without a test DB; WeasyPrint tests skip under `make` on macOS, see D3) |
| `make db-test` (TEST_DATABASE_URL = local `postgres`) | PASS | `518 passed, 1 skipped, 1 warning in 86.41s`. The skipped test is the WeasyPrint one (D3). Run directly with `uv run pytest`: `test_proof_flow.py` 10 passed, `test_pdf_render.py` 22 passed, 2 skipped (pypdf not installed) |
| `make golden` | PASS | `4 case(s), 0 error(s), 15/15 numbers within tolerance, 8/8 labels match`; agreement gate 0/0, not enforced yet |

## Defects found

| ID | Severity | Where | Defect | Repro |
|---|---|---|---|---|
| D1 | Medium (blocks ca-on from the UI; not hit with the default pack) | `app/cloverproof_app/plan_web.py:301` (`planning.run_engine` without error handling); form `app/cloverproof_app/planning.py:96-129` | With `PACK_PATH=packs/ca-on/v1.yaml` the app starts and the plan form validates, but the engine raises `MissingInputError: pack ca-on v1 covers pastry (soft) wheat only, Table 4-14: input wheat_class (pastry \| hard) is required`. The route does not catch it, so every new plan returns HTTP 500 instead of a form error. Startup does not check that the form can supply what the pack requires | Load ca-on v1, build a `PlanForm` (wheat, 5 t/ha, previous crop `corn`, 10 ha, no soil test), `validate_plan_form` → no errors, `run_engine` → `MissingInputError`. Reproduced at function level; the HTTP 500 follows from the code path |
| D2 | Low | `app/cloverproof_app/pdf/render.py:43` | The PDF's `METHOD_LABELS` has no `ammonium-acetate` (added in migration 0023), so the proof prints the raw key "ammonium-acetate" while the app (`planning.METHOD_LABELS`) shows "Ammonium acetate" | Plan 1 PDF, soil test table: `K 110 mg/kg ammonium-acetate` |
| D3 | Low (tooling) | `Makefile` targets `test` / `db-test` | On macOS, `make` is a SIP-protected binary, so it drops `DYLD_FALLBACK_LIBRARY_PATH`, and the WeasyPrint tests skip under `make test` / `make db-test` even with the variable exported. The real PDF render is untested in the standard commands on a Mac | `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib make db-test` → `SKIPPED test_proof_flow.py:209 WeasyPrint system libraries unavailable`; the same test with `uv run pytest` passes |

No high-severity defects. No defect touched immutability, the review gate, org isolation or proof integrity.

## Gaps (not defects; recorded, nothing built)

1. **ca-on v1 cannot be used from the UI today.** The plan form (`PlanForm`) has no fields for `n_price` (N price per kg N + grain price per kg), `wheat_class` (pastry or hard) or `manure_applied`. ca-on v1 requires them, so only the placeholder pack works end to end. This is the gate for real Ontario plans in Feb 2027.
2. **Confidence `high`/`medium` paths are not exercised from the UI.** The placeholder pack gives `low` on every plan, even with a lab test.
3. **No version link after a reject.** A rejected plan is final; the next attempt is a new `crop_plan` (5a `f811942b` → 5b `c9b356a2`), not a `parent_id` child. Nothing links the two, and the soil test has to be typed again, which creates a second `soil_test` row with the same values. Fine for the audit trail; costs agronomist minutes.
4. **S3 ProofStore not built.** Proofs go to the filesystem store (`PROOF_STORE_DIR`). `BucketProofStore` is a stub. On Railway this needs a volume or the bucket store before real plans.
5. **Deploy not done.** Nothing runs on Railway yet: no hosted DB with the `cp_app_login` / `cp_admin_login` roles, no `ALLOWED_HOSTS`/`COOKIE_SECURE` production config tested, no hosted WeasyPrint libraries.
6. **Minutes per plan has no real value yet.** The timer works (whole minutes, one value per review), but a scripted run cannot measure agronomist effort.
7. **AI review (`ai_reviewed`) not walked over HTTP.** No service account in this run; covered by the DB test suite only.

## Verdict

**GO** for the S1 exit: the full concierge loop works end to end on a migrated database under the least-privilege app role. Five synthetic plans went from intake to a hash-checked proof PDF. The hard rules held in the database, not only in the app: immutability, review gate, org isolation, snapshot and versions, engine-vs-final diff, minutes on every review.

Conditions before the first real farm plan (not S1 exit blockers):

- Fix D1 and close Gap 1 (ca-on inputs in the form), so a real pack can run. The placeholder pack must never produce a real plan.
- Fix D2 (one-line label).
- Close Gap 4 and Gap 5 (proof storage and deploy).
- Make the PDF tests run in CI or under `make` (D3), so a WeasyPrint break is not silently skipped.

## Status of the conditions (2026-11-18)

| Condition | Status | Where |
|---|---|---|
| D1 + Gap 1: Ontario inputs in the plan form | Closed | PR #61 |
| D2: PDF method label | Closed | PR #61 |
| Gap 4: proof storage | Closed in code (S3-compatible store); no bucket connected yet | PR #59 |
| D3: PDF tests under `make` and in CI | Closed: `make` sets the library path on macOS; a PDF skip now fails both CI test jobs | this change |
| Gap 5: deploy | **Open.** Image is built and smoke-tested in CI (PR #58); no hosted app, no Railway change made | needs Farjad Iranmehr's go |
