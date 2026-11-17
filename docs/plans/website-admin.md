# Website admin — plan (DRAFT, not approved)

- Owner: `cp-website` (via `cto`) · Requested by Farjad Iranmehr through the CPO, 2026-11-17
- Status: **plan approved with decisions (Farjad Iranmehr, 2026-11-17, §10)** — each phase still starts only on his go; `ciso` reviews ADR 0012–0014 before P1 code
- ADR drafts: [0012 admin auth](../adr/0012-website-admin-auth.md) · [0013 secrets encryption](../adr/0013-website-integration-secrets.md) · [0014 system log + 60-day retention](../adr/0014-website-system-log-retention.md) · [0015 blog editor + content model](../adr/0015-website-blog-content-model.md). Renumbered 0012–0015 → 0013–0015 on 2026-11-17 (0012 is the pyphen licence exception on `main`). `ciso` reviews 0012–0014 before P1 starts.
- Related: ADR 0003 (website stack, i18n), ADR 0005 (web-app auth — **separate** system), ADR 0007 (DB privileges), ADR 0010 (site_event), `docs/runbook-db-switch.md`, `docs/plans/website-v1.md`.

## 1. Goal
Give the CloverProof team a private admin inside the public website to manage **website** staff accounts, see a system log, hold AI-provider keys for later content agents, and publish a multi-locale blog built for search (SEO), Google AI Overviews (AIO) and generative engines (GEO). The content agents (P4) are planned, not built.

## 2. Non-goals (this epic)
- No farmer, advisor or agronomist accounts here — those live in the web app (`app/`, ADR 0005). A person who needs both has two accounts.
- No self sign-up, no social login, no managed identity provider.
- No outbound email service (invites and resets are one-time links the admin hands over; see ADR 0012). An email provider would be a new paid service → Farjad Iranmehr's go.
- No AI calls in P1–P3 except the "test connection" button in P2. No agents, no generation, no auto-publish.
- No access from the admin to `pilot_request` or `site_event` (ops/data own them; least privilege). Can be added later with its own decision.
- No third-party scripts on public pages (unchanged).

## 3. Hard rules that shape the design
| Rule | Effect here |
|---|---|
| CLAUDE.md rule 9 (no invented agronomy) | Blog pre-publish check flags agronomic numbers/units; publishing with one needs a named **human** agronomist's validation recorded on the post. |
| Rule 11 (AI never approves) | No copy, author field or reviewer field may present AI as approving or reviewing; "reviewed by" accepts only a human author profile. |
| Rule 12 / D-7 (no farmer data to AI) | The DB role used by admin + future agents has **no grant** on `pilot_request`, `site_event` or any web-app table. Agents (P4) only see published sources and our own posts. |
| Rule 10 (no secrets in git) | Master key in an env var only; API keys encrypted in DB; `.env.example` gets empty names. |
| Website content rules (ADR 0003 / glossary) | No third-party-approval claims; "no soil test = nitrogen only, max medium" stays exact; machine-translated posts carry `translation_status`. |
| "Human approval before anything is published" (CPO) | Only `editor`/`admin` can publish; `author` and (P4) agents can only create drafts / submit for review. Publishing is always a signed-in human action, logged. |
| Licences | No GPL/AGPL/EUPL. All proposed deps MIT/Apache/BSD (list per ADR). TipTap **open-source** extensions only (MIT); no TipTap Pro / Cloud. |
| Paid services | Railway Bucket already approved (usage cost); blog images reuse it under the separate prefix `website/blog/`. No new Railway service: admin stays in the website service (decided). |

## 4. Architecture (summary — details in the ADRs)
- **Where:** same Next.js service, under `/admin` (English only, not localised; excluded from `proxy.ts` locale redirect, sitemap and robots; `noindex`; strict CSP; `Cache-Control: no-store`).
- **Two DB pools, two roles:** public pages keep `cp_website_login` (INSERT pilot_request/site_event + SELECT on a `blog_published` view only). Admin code uses a new `cp_website_admin_login` with grants on the admin/blog tables only. Admin modules import `server-only` and the admin pool; a lint rule (no-restricted-imports) keeps public routes from importing it.
- **Auth (ADR 0012):** argon2id, DB sessions (`__Host-` cookie, SameSite=Strict, idle 30 min / absolute 12 h), TOTP MFA required for every admin-area role at first login, recovery codes, explicit CSRF token on every POST in addition to Next's Origin check, Postgres-backed rate limit + lockout, step-up MFA for sensitive actions (keys, roles, delete). First and only admin for now: Farjad Iranmehr, via CLI (`npm run admin:create`) in the Railway shell. No editors/authors yet.
- **Roles:** `admin` (users, keys, log, everything), `editor` (all posts, review, publish, authors, media), `author` (own drafts, submit for review, media upload).
- **System log (ADR 0014):** one append-only table; purge after 60 days by a daily in-process job (Next `instrumentation.ts` + Postgres advisory lock), with a "last purge" health row the admin dashboard checks; moves to the S4 Procrastinate worker when it exists.
- **Secrets (ADR 0013):** AES-256-GCM envelope encryption (per-secret data key wrapped by a master key from `WEBSITE_SECRETS_KEK`), write-only UI (mask + last 4 + test connection), admin-only, server-only decrypt module, every change logged, per-provider monthly budget field.
- **Blog (ADR 0015):** TipTap (ProseMirror JSON) editor with custom nodes (FAQ, HowTo, sources, callout); JSON is the source of truth; sanitised HTML rendered at publish; posts × 8 locales with per-translation status; revisions append-only; scheduled publish needs **no job** (`publish_at <= now()` filter + ISR revalidation); images in a private Railway Bucket served through `/media/…`; JSON-LD, hreflang, sitemap, RSS, `llms.txt`.

## 5. Data model (proposed schema — to `cloverproof-lead` / `cp-database` for `db/migrations/`)
I don't write migrations. Below is the schema I'm sending them. Names are prefixed `website_` to keep them apart from web-app tables.

```text
website_user            id uuid pk, email citext unique (null after delete), display_name, role enum(admin|editor|author),
                        password_hash text null (null until invite accepted), mfa_secret_enc bytea null (ADR 0013 envelope),
                        mfa_enabled_at, disabled_at, deleted_at, failed_logins int, locked_until, created_at, created_by,
                        password_changed_at
website_user_recovery_code   user_id fk, code_hash, used_at
website_session         id uuid pk, user_id fk, token_hash bytea unique, csrf_token_hash, created_at, last_seen_at,
                        expires_at, mfa_verified_at, step_up_at, ip_prefix, ua_family, revoked_at
website_one_time_token  id, user_id, kind enum(invite|password_reset|mfa_reset), token_hash, expires_at, used_at, created_by
website_rate_limit      key_hash bytea, window_start, count            -- login/reset throttling, purged daily
website_log             id bigserial, occurred_at, actor_user_id null, kind enum(auth|admin|content|secret|error|job),
                        action text, target_type, target_id, outcome enum(ok|denied|failed), ip_prefix, ua_family,
                        detail jsonb (whitelisted keys only, never secrets/bodies/passwords)  -- 60 days
website_job_run         job text pk, last_ok_at, last_error_at, last_error
website_secret          id uuid pk, provider enum(anthropic|google_gemini|openai|fal), version int, ciphertext, iv, tag,
                        wrapped_dek, dek_iv, dek_tag, kek_id, last4, monthly_budget_usd numeric(10,2) null,
                        created_at, created_by, revoked_at, revoked_by, last_test_at, last_test_ok
                        -- one active row per provider (partial unique index on provider where revoked_at is null)
website_author          id uuid pk, user_id null fk, name, slug, role_title, credentials, bio_md, profile_url, image_key,
                        is_human bool not null default true check (is_human)   -- E-E-A-T; AI can never be an author/reviewer
website_post            id uuid pk, created_at, created_by, origin enum(human|agent) default human, archived_at
website_post_translation  id uuid pk, post_id fk, locale (8 locales), slug, title, dek, body_json jsonb, body_html text,
                        meta_title, meta_description, canonical_url null, og_image_key, og_image_alt, primary_keyword,
                        author_id, reviewer_id null (human author), agronomy_validated_by null, agronomy_validated_at,
                        translation_status enum(source|human|machine_pending_review), status enum(draft|in_review|
                        scheduled|published|archived), publish_at, published_at, updated_at, current_revision_id
                        unique(locale, slug), unique(post_id, locale)
website_post_revision   id, translation_id, created_at, created_by, body_json, meta jsonb, note   -- append-only
website_post_source     translation_id, position, title, publisher, url, accessed_on      -- citations block
website_tag / website_post_tag
website_media           id, key, mime, width, height, bytes, sha256, alt_default, uploaded_by, created_at
-- P4 hooks (tables planned, NOT created now):
website_content_job     id, kind(research|draft|translate), brief jsonb, requested_by, provider, status, cost_usd,
                        result_post_id, created_at, finished_at
website_ai_usage        provider, month, tokens_in, tokens_out, cost_usd   -- for the budget cap
```

Grants (sketch for `cp-database`): `cp_website_admin` gets SELECT/INSERT/UPDATE on the `website_*` tables it manages, INSERT-only on `website_log` and `website_post_revision`, no UPDATE/DELETE on them; DELETE on `website_log` only through a `security definer` function `website_log_purge()` that deletes `occurred_at < now() - interval '60 days'`. `cp_website` gets SELECT on view `blog_published` (published translations, `publish_at <= now()`, no draft fields). Neither role sees `pilot_request` SELECT, `site_event` SELECT or web-app tables.

## 6. Phases (each approved before it starts)
Effort = focused dev days for `cp-website` (+ reviewers), excluding waiting time.

| Phase | Scope | Exit criteria | Effort | Depends on |
|---|---|---|---|---|
| **P0** plan | This doc + ADR drafts, `ciso` review of 0012–0014, design spec from `product-designer`/`cp-design` (Stitch) for the admin shell, users, log, keys, post list, editor | Farjad Iranmehr approves plan + ADRs | 1 | — |
| **P1** users + log + retention | CLI first admin; login, MFA enrol/verify, recovery codes, sessions, CSRF, rate limit, step-up; users list, invite link, role change, disable/enable, password/MFA reset link, delete (pseudonymise); system log viewer (filter by kind/actor/date, CSV export logged); 60-day purge job + health; security headers/CSP for `/admin` | All P1 tests green (§8); `ciso` go; pen-style checklist (§8) passed on staging; log purge demonstrated with back-dated rows | 7–9 | DB switch to `PostGIS-cXKk` done; `cp-database` migration for P1 tables |
| **P2** API integrations | Providers page (Anthropic, Gemini, OpenAI, fal): add/replace/revoke key, mask + last 4, test connection, monthly budget field, history (no plaintext) | Key never in any response/log/HTML (tested); rotation of master key documented + tested; `ciso` go | 3 | P1; `WEBSITE_SECRETS_KEK` set in Railway by Farjad Iranmehr |
| **P3** blog | Editor, posts × locales, revisions + diff, review → publish, schedule, authors, sources, FAQ/HowTo blocks, internal-link picker, media upload to Bucket, public `/[lang]/blog` + post pages, JSON-LD, hreflang, sitemap, RSS, `llms.txt`, pre-publish content checks | SEO/AIO/GEO checklist (§7) ticked on a sample post in en + 1 locale; Lighthouse mobile ≥ 90 on post page; axe 0; 375/1280 no horizontal scroll; content-rule checks block a test post with an agronomic rate | 10–14 | P1; Railway Bucket go (paid usage); `content-seo-strategist` checklist |
| **P4** content agents (later) | Plan only now: research/draft/translate jobs → drafts with `origin=agent`; human publish; budget cap; D-7 data boundary | Separate plan + ADR when Farjad Iranmehr opens it | — | P2, P3 |

**Order (decided 2026-11-17): P1 → P3 → P2 → P4.** P2 is built just before P4, so keys aren't stored months before any use.

Schedule (decided): Hebrew locale (done 2026-11-17) → S2 items (funnel events once `site_event` is reachable, DB switch) → P1. The P1 schema goes to `cloverproof-lead` via the CPO for `db/migrations/`.

## 7. Blog SEO / AIO / GEO requirements
Full checklist from `content-seo-strategist`: [website-admin-seo-checklist.md](website-admin-seo-checklist.md). Must-haves built into P3:
- Per-translation meta title/description, slug, canonical, OG image + alt; author + human reviewer with credentials (E-E-A-T); published/updated dates shown and in JSON-LD.
- `BlogPosting` + `BreadcrumbList` + `Organization`/`Person` JSON-LD. FAQ and HowTo blocks render as visible semantic HTML; Google no longer shows FAQ rich results (stopped 2026-05-07) and deprecated HowTo in 2023, so their JSON-LD is behind a flag as optional, unproven GEO value.
- Google says AI Overviews/AI Mode need no special markup or "AI text file" — only an indexed, snippet-eligible page. So `llms.txt` is optional and low priority, never treated as a lever.
- `reviewer_id` / JSON-LD `reviewedBy` only for a human author profile (DB check); agronomic posts without a human agronomist review stay `noindex` with "Agronomist review pending".
- `published_at` set by the server, not editable (no backdating); `updated_at` changes only on a substantive edit with a change note; sitemap `lastmod` from those fields.
- hreflang between all published translations (+ `x-default`). **Decided (Farjad Iranmehr, 2026-11-17): machine-translated posts are indexable** (in hreflang and sitemap) with a visible "machine translation" label in the post template, JSON-LD `inLanguage` + `translationOfWork` (source post) and a translation note, and the native-review status kept per translation (`translation_status`). The SEO checklist's noindex recommendation is overridden; risk (Google's scaled-content policy names translation) accepted and revisited if Search Console shows problems.
- Sitemap per locale, RSS per locale. Hard CSP (`default-src 'self'`) on public pages; Search Console/Bing verification via DNS or meta tag.
- Existing-code fixes found (separate small `website-v1` change, not this epic): `sitemap.ts` sets `lastModified: new Date()` on every build and sends ignored `priority`/`changeFrequency`; posts need a `languageAlternates()` variant listing only existing translations.
- Answer-first summary, sources block, clean headings (one h1, no skipped levels), tables as real `<table>`, images with width/height/alt.

## 8. Test plan
- **Unit (node:test):** argon2 verify + rehash; TOTP against RFC 6238 vectors; session expiry (idle/absolute); CSRF token check; rate-limit windows; role matrix (every action × role → allow/deny); envelope encrypt/decrypt round trip, tamper (tag/AAD) fails, wrong KEK fails, KEK rotation re-wraps; mask/last-4; log `detail` whitelist drops unknown keys; content checker (agronomic number/unit regex, banned approval phrases, AI-approval wording); slug rules; JSON-LD builders; sanitiser strips script/style/event handlers/javascript: URLs.
- **DB (against a throwaway Postgres + the real migrations):** `cp_website_admin` cannot UPDATE/DELETE `website_log`; purge function deletes only > 60 days; `cp_website` cannot read drafts or `website_secret`; `website_author.is_human` check; one active secret per provider.
- **Route/e2e (Playwright, scratch):** login → forced MFA enrol → dashboard; wrong password ×N → lockout; author cannot publish or see keys; editor cannot see keys/users; admin key page never contains the key (HTML, network, RSC payload, logs); scheduled post appears after `publish_at`; draft URL 404 for public; hreflang/sitemap/RSS/llms.txt correct; 8 locales + RTL post page; 375/1280; axe; Lighthouse.
- **Security checklist before P1 go (`ciso`):** session fixation, CSRF on every POST, open redirect on `next=`, user enumeration on login/reset, timing-safe compares, headers (CSP, frame-ancestors none, HSTS), server-action auth check in every action, secrets absent from client bundles (`grep` build output), error messages redacted (`safeError`).

## 9. Risks
| Risk | Mitigation |
|---|---|
| Admin on the public site widens its attack surface | Separate DB role/pool, `/admin` noindex + strict CSP, MFA, rate limit, `ciso` review; option to move admin to its own service later (cost → ask). |
| Two auth systems (web app FastAPI + website Next) to maintain | Same parameters/policies documented in both ADRs; shared test checklist; revisit when the farmer-portal front-end ADR lands (S9). |
| Retention job silently stops | `website_job_run` health row, dashboard warning if last purge > 26 h, log viewer filters to 60 days regardless. |
| Master key loss = all keys unreadable | Keys are re-enterable from provider consoles; KEK stored in Railway variables + Farjad Iranmehr's password manager; rotation runbook. |
| Machine-translated posts hurt quality/trust | Per-translation status, label on page, optional `noindex` until reviewed. |
| Agronomic claims slip into posts | Automated pre-publish check + human agronomist validation field; `cp-agronomy-guard` reviews the checker rules. |
| No email provider → invites/resets are manual links | Acceptable for ≤ 5 staff; links single-use, 72 h / 1 h expiry, logged. |
| Scope creep into a CMS product | P4 stays plan-only; no generic page builder; blog only. |
| Blocks S2 / DB switch | P1 sequenced after both. |

## 10. Decisions (Farjad Iranmehr, 2026-11-17, via the CPO)
| # | Question | Decision |
|---|---|---|
| 1 | Phase order | P1 (users + log + 60-day retention) → P3 (blog) → P2 (API keys) just before P4 (agents) |
| 2 | Where the admin runs | Same Next.js service under `/admin`; no new service |
| 3 | Bucket for blog images | Existing approved Railway Bucket, separate prefix `website/blog/` |
| 4 | Machine-translated posts | Indexable, visible "machine translation" label, JSON-LD `inLanguage` + translation note, native-review status per translation |
| 5 | IP in the system log | Truncated IP as designed; `coo` decides the privacy-notice line (pending) |
| 6 | First admin | Farjad Iranmehr only, via CLI; no editors yet |
