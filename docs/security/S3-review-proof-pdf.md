# S3 security review: proof PDF v0 (PR #40, merge 49f6c17)

Reviewer: security-engineer (reports to CISO). Date: 2026-11-17. Target: `origin/main` a4851ed, diff `49f6c17^1..49f6c17`.
Scope: `app/cloverproof_app/pdf/`, `templates/pdf/`, `proof_web.py`, `repo/proofs.py`, `storage/__init__.py`, `_proof_panel.html`, `proof_document.html`, config/CI changes; DB objects from migrations 0008/0012/0021 that this code relies on. PR #40 adds **no migration**: `proof_document`, its approval trigger, and its immutability triggers were already on main.

## Verdict

**PASS. No code BLOCKER.** The renderer cannot fetch anything except the four allow-listed static assets (probe below). User strings are autoescaped. The approval gate holds in both the app and the DB. Every query is org-scoped. Integrity (hash of stored bytes, write-once key, re-hash on download) is implemented and tested.

**One deploy gate (F1)** must close before the first real proof is generated on Railway: proofs currently go to the container filesystem. There are four SHOULD-FIX items and a few NOTEs.

## Findings

### BLOCKER (deploy gate, not code): F1. Proof files sit on the container's ephemeral filesystem, and a lost file cannot be recovered
- Evidence: `storage/__init__.py:115-145` (`BucketProofStore` is a stub; `store_from_env`/`filesystem_store` always return `FilesystemProofStore`, default `./var/proofs`). `proof_web.py:71-77`, `proof_web.py:143-145` (an existing row means the app never renders again), `proof_web.py:200-202` (missing file returns 500).
- How it happens: on Railway, a redeploy or restart without a mounted volume wipes `var/proofs`. The `proof_document` row survives because it is insert-only. After that, the download returns 500 "file missing", and the generate POST redirects to the dead document, so no replacement can ever be produced for that approved version.
- Impact: immutable evidence (rule 4, ADR 0005) is permanently lost for real farms.
- Fix: before any deployed environment generates a proof, do one of the following. (a) Mount a Railway volume and set `PROOF_STORE_DIR` to it; add a startup check in deployed envs that refuses to start when the directory is not on a persistent mount, or at least when `PROOF_STORE_DIR` is unset. (b) Wire `BucketProofStore` with `If-None-Match: *`, which needs Farjad's go for boto3 and the Bucket cost. Also add a recovery path: rendering is deterministic for a fixed `document_id`, so an admin-only "re-materialise" action can rebuild the `ProofInput` from the stored row, render again, and store only if `sha256` equals `proof_document.sha256`.
- Not verified: whether any deployed environment currently routes `/plans/*/proof`. I don't know the Railway service config.

### SHOULD-FIX

**F2. The CPU-bound render runs while holding the plan row lock and one of the 5 pooled DB connections, with no concurrency cap or timeout**
- Evidence: `proof_web.py:141` (`locked_plan`, `SELECT ... FOR UPDATE`, `repo/plans.py:168-175`), then `proof_web.py:150` (`run_in_threadpool(render_pdf)`). Pool `max_size=5` at `db/pool.py:111`.
- Exploit: a signed-in human member (any INTERNAL role) fires about 5 parallel generate POSTs on different approved plans. Each holds a connection for the length of its render. Measured: 0.4 s for a normal plan, 1.3 s with 10 versions, 3.9 s with 100 versions carrying 4000-character reasons. While those renders run, every other request waits for a connection. The pool is exhausted and the app stalls. The attacker must be authenticated, so the risk is low; impact is availability only.
- Fix: put a process-wide `asyncio.Semaphore(1-2)` around the render and return 503 "busy, try again" when it cannot be acquired within about 2 s. Better: render before taking the lock. Read the view without the lock, render, then `locked_plan` again and verify that `view.latest.id` and the final review are unchanged before the insert. Optionally cap lineage length on the PDF.

**F3. The DB allows more than one `proof_document` per recommendation (the app lock is the only guard)**
- Evidence: `db/migrations/0008_application_log_and_proof_document.sql:29-42`. The only index is the non-unique `proof_document_recommendation_idx`; `storage_key` is unique, but `document_id` is printed in the PDF, so every render has a different SHA and a different key. The app-side check is at `proof_web.py:143-145`.
- Exploit: any code path, or a future one, that inserts without `lock_plan`, or a `cp_app` session run by hand, creates a second "proof" for the same approved version. That gives two different PDFs and hashes for one approval.
- Fix: new migration `create unique index proof_document_one_per_recommendation on proof_document (recommendation_id);`. Map the 23505 to "redirect to the existing document" in `proof_generate`. This is consistent with rule 4 ("enforced in the database").

**F4. The DB does not stop a service account (the AI reviewer) from creating a proof**
- Evidence: `proof_document_check_approved` (`0012_review_gate_integrity_and_admin_audit.sql:214-228`) checks only the review. `created_by` is any `app_user`. The human-only check exists only in the app (`proof_web.py:80-82`).
- Impact: rules 11 and 12 rely on app code alone for proof creation and reading by the AI account.
- Fix: in the same trigger, add `if not exists (select 1 from app_user where id = new.created_by and actor_kind = 'human') then raise ... check_violation`. Read access for service accounts is an RLS question; flag it to ADR 0008 owners.

**F5. The approval trigger uses a denylist (`review_kind <> 'ai_reviewed'`) instead of an allowlist**
- Evidence: `0012_review_gate_integrity_and_admin_audit.sql:219-220`.
- Impact: today it is equivalent, because `review_kind_check` allows only three values. If a fourth kind is added (for example `external_reviewed`), it would silently unlock proofs. The app side (`APPROVAL_KINDS`, `HUMAN_REVIEWS`) is already an allowlist.
- Fix: `and r.review_kind in ('agronomist_approved','superadmin_approved')`. Do it in the same migration as F3 and F4.

### NOTE
- **N1. PII on the PDF (current state).** The farmer name, farm name and field name are printed (`templates/pdf/proof.html:77-79`, verified in the extracted text). Approver and editor display names are printed as well (`proof.html:237,249`). The field name also goes into the PDF `/Title` metadata (`proof.html:31`; probe: `/Title: 'Fertilizer plan · <field> · <doc id>'`). This does not match the privacy recommendation (no farmer name or map on the PDF). It is a product/privacy decision for Farjad. If it is adopted, drop `farmer_name` and use the field name only in the body, or put the document ID alone in `<title>`. There is no map on the PDF.
- **N2. PDF metadata.** `/Producer: WeasyPrint 70.0` (version disclosure, negligible) and `/Creator: CloverProof proof-v0`. No CreationDate or ModDate, no local paths, no usernames, no `/JavaScript`, `/EmbeddedFile` or `/URI` (probe).
- **N3. Orphan files.** `store_once` runs before the request transaction commits (`proof_web.py:163`). If the commit fails, the file stays without a row. It is content-addressed and never served, so it is harmless; a periodic sweep is optional.
- **N4. Tamper alerting.** A hash mismatch only logs at `error` (`proof_web.py:203-205`). T-P1 asks for an alert. Route this log line to Railway alerting when monitoring lands.
- **N5. Failure handling.** `PdfRenderError` (refused resource) is not caught in `proof_generate` and becomes a generic 500. It fails closed with nothing stored, which is acceptable; a 500 with a clear message would be cleaner.
- **N6. Process-wide environment change.** `load_weasyprint` sets `os.environ["SOURCE_DATE_EPOCH"]` for the whole process (`render.py:106`). This is benign today. Note it if any other library starts reading that variable.
- **N7. Who can generate.** Any human member with an INTERNAL role can generate or download, not only agronomist or superadmin. The approval is already fixed in the DB, so this is acceptable for v0; restrict it if non-agronomist internal roles appear.
- **N8. Local dev setup.** On macOS, `uv run pytest` (and therefore `make test`) loses `DYLD_FALLBACK_LIBRARY_PATH` because SIP strips it through the script shebang. The PDF tests then fail with `CP_PDF_TESTS_REQUIRED=1`. `uv run python -m pytest` works. Update the hint in `render.py:111` or the Makefile. CI (Linux) is unaffected.

## Verified OK
- **SSRF / local file read (T-P5).** `render.py:117-134`: the custom `URLFetcher` subclass sets `fail_on_errors=True` and overrides `fetch`. It allows only `file:` URLs whose resolved path is in the exact 4-entry `ALLOWED_ASSETS` set; everything else raises, and that raise becomes `FatalURLFetchingError`, which aborts the render. WeasyPrint 70 sends **every** URL through `url_fetcher`, including `data:` (`weasyprint/urls.py:417-430`). `base_url` is `static/`. Probe results:
  - Malicious farmer, farm, field, season and previous-crop strings (`<img src="file:///etc/passwd">`, `<link href="http://169.254.169.254/">`, `@import`, `url(file:///etc/hosts)`, `data:`) appear only as escaped text. The only fetches were the 4 allow-listed assets. No socket or urllib calls.
  - Defence in depth with raw, unescaped HTML through the same fetcher: `file:///etc/passwd`, `http://169.254.169.254/...` (link and `@import`), CSS `url(file:///etc/hosts)`, `data:` image, `../` traversal, a non-allow-listed static file, and `%2e%2e` encoded traversal were all **REFUSED**, with zero network calls.
- **Autoescape.** `select_autoescape(["html"], default_for_string=True, default=True)` with `StrictUndefined` (`render.py:75-81`). There is no `|safe`, `Markup` or `autoescape false` in `templates/pdf/`, `_proof_panel.html` or `proof_document.html`. No user value is placed in a `style` attribute or the CSS. `class="badge conf-{{ doc.confidence }}"` is escaped and comes from an enum, so there is no CSS injection.
- **Approval-only proofs (rules 8 and 11).**
  - App: `approval_of` requires `status == approved`, `decision == approve`, `review_kind in HUMAN_REVIEWS`, and the review on the latest version (`proof_web.py:85-96`).
  - Model: `Approval.__post_init__` refuses `ai_reviewed` (`pdf/model.py`).
  - DB: `proof_document_check_approved` before-insert trigger, with CheckViolation mapped to 409 (`proof_web.py:160-161`).
  - Tests: `test_unapproved/rejected/ai_reviewed_plan_is_refused`.
- **Approval wording.** An `agronomist_approved` review gets "Reviewed and approved by agronomist X". A `superadmin_approved` review gets "(platform administrator; not an agronomist review)". The review kind is printed (`proof.html:63-64,236`). The PLACEHOLDER banner appears whenever the pack is not validated or any constant or number is a placeholder. Forbidden certification phrases are checked by the tests.
- **Org scoping / IDOR.** Every `repo/proofs.py` query filters by `organisation_id` and joins the recommendation on `(organisation_id, id)`. The plan is loaded via org-scoped `locked_plan`/`load_plan`. RLS is on `proof_document` (0021). `test_cross_org_is_404` passes.
- **CSRF.** The app-wide `csrf_guard` covers every non-GET (`auth.py:201-219`); `test_csrf_required` passes.
- **Download auth.** `InternalOrg` plus `require_human`; service accounts get 403.
- **Integrity (T-P1).**
  - The SHA-256 is computed over the exact `data` bytes that are stored (`proof_web.py:154,163`).
  - The key `proof/{org}/{rec}/{sha}.pdf` is checked in both the app and the DB (`storage_key` CHECK and UNIQUE).
  - Writes are write-once: `os.link` from a temp file is atomic and refuses an existing name, and the file is set to 0440 (`storage/__init__.py:84-102`).
  - `store_once` accepts an existing key only when the bytes are identical.
  - Download re-hashes the bytes and refuses a mismatch with 500 (`proof_web.py:203-205`); `test_tampered_file_is_not_served` passes.
  - `proof_document` has insert-only grants plus UPDATE, DELETE and TRUNCATE triggers (0008).
  - A store failure raises inside the request transaction, so the row is rolled back.
- **Retry / double click.** `lock_plan` serialises requests, and a second POST redirects to the first document (tested). The DB backstop is missing; see F3.
- **Download headers.** `Content-Type: application/pdf`; `Content-Disposition: attachment; filename="cloverproof-proof-<uuid>.pdf"` (UUID only, safe); `Repr-Digest`. The global middleware adds `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` (non-`/static/`), CSP and `X-Frame-Options` (`main.py:66-74,159-167`). Files are streamed through the app, with no presigned URLs (T-P2).
- **Path traversal in the filesystem store.** `check_key` uses segments `^[a-z0-9_-][a-z0-9._-]*$` and rejects `.`, `..`, empty segments and a leading `/`; `is_relative_to(root)` is a second check. Keys come only from `proof_key(UUID, UUID, sha-regex)`. `test_unsafe_keys_are_refused` passes.
- **Input size.** Names are at most 200 characters (DB CHECK), reasons and notes at most 4000 (`plan_web.text` limit / DB). Measured render cost is in F2.
- **Secrets.** No secrets in the diff. `var/` is gitignored.

## Tests run (scratch copy of a4851ed; nothing in the repo was modified)
- `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib CP_PDF_TESTS_REQUIRED=1 uv run python -m pytest -q`: **534 passed**, 516 skipped (DB tests opt-in), 0 failed.
- `uv run --with pypdf python -m pytest -q app/tests/test_pdf_render.py app/tests/test_pdf_store.py`: **38 passed** (pypdf text checks included).
- DB suite against a throwaway `postgis/postgis:18-3.7` container on `127.0.0.1:55517` (never Railway): `CP_DB_TESTS_REQUIRED=1 uv run --with pypdf python -m pytest -q app/tests/db`: **519 passed**, including all 10 tests in `test_proof_flow.py`. The container was stopped and removed afterwards. Port 55499 belonged to another session's container (`s3-rls-review-pg`), which was left untouched.
- Probes (scratchpad, not committed): `probe_ssrf.py` (escaping plus fetcher refusal plus no network), `probe_meta.py` (metadata, paths, PII), `probe_size.py` (render time against input size).

## Not verified
- Railway deployment: whether a volume backs `PROOF_STORE_DIR` and whether proofs are reachable in any deployed env (F1).
- `BucketProofStore` conditional-write behaviour: it is a stub.
- Behaviour under a real multi-worker uvicorn (F2 numbers are from a single-process local render on Apple Silicon; label: estimate).
- RLS read access to `proof_document` for service accounts (F4 tail).
- `npm`/`pip` audit of new dependencies: only `weasyprint>=66` was added (locked 70.0, plus transitive packages in `uv.lock`); no CVE lookup was done.
