# Runbook — web app container (`app/`)

Status: image builds and passes the CI smoke; **not deployed**. Decisions: ADR 0004 (Railway), ADR 0005 (auth, ProofStore), ADR 0007 (DB roles), ADR 0009 §4 (build portable).
Never commit passwords, URLs with credentials or `.env` files.

## What the image is
`Dockerfile` (repo root), multi-stage:
- base `python:3.12-slim`; `uv` copied from the official `ghcr.io/astral-sh/uv` image;
- `uv sync --frozen --no-dev --package cloverproof-app`: only the app, the engine and their locked deps (no dev tools, no `data_sources`);
- WeasyPrint system libraries (`libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz-subset0`, fontconfig, DejaVu fallback); the proof PDF embeds its own fonts;
- runs as non-root `app` (uid 10001); `PORT` env (default 8000);
- `CMD`: `uvicorn --factory cloverproof_app.main:create_app --host 0.0.0.0 --port ${PORT:-8000}`;
- `HEALTHCHECK`: `python -m cloverproof_app.healthcheck` → `GET /healthz` on 127.0.0.1 with `Host` = first `ALLOWED_HOSTS` entry (the app refuses unknown hosts).

**Migrations are not run on container start.** The operator applies them with the superuser URL from their own shell, before deploying a new image:
`DATABASE_URL=<superuser URL> make db-migrate` (see `docs/runbook-db-switch.md` §2). The image also contains `db/migrations`, so `docker run --rm -e DATABASE_URL=... <image> python -m cloverproof_app.db.migrate up` works the same way. The superuser URL is never a variable of the app service.

No background worker yet (planned for S4).

## Build and run locally
```sh
docker build -t cloverproof-app:local .
docker run --rm -p 8000:8000 --env-file .env.docker cloverproof-app:local
```
`.env.docker` is your own untracked file (`.env.*` is gitignored and excluded from the build context). From inside a container, a database on your machine is `host.docker.internal`, not `127.0.0.1`; a non-local `DATABASE_URL` requires `ENV`.

Smoke test (what CI runs; starts a throwaway PostGIS, migrates it, checks that a superuser login is refused and that `cp_app_login` serves `/healthz`):
```sh
docker build -t cloverproof-app:ci . && .github/scripts/docker_smoke.sh cloverproof-app:ci
```

## Environment variables (names only; values live in the host's variable store)
Required:
- `DATABASE_URL` — the **`cp_app_login`** login (ADR 0007). In staging/production the app refuses to start if the role is a superuser, has `BYPASSRLS`, is not a member of `cp_app`, or is a member of `cp_admin`.
- `ENV` — `staging` or `production` on a host (required whenever the DB is not local).
- `SESSION_SECRET` — at least 32 characters, random (`openssl rand -base64 48`).
- `ALLOWED_HOSTS` — comma-separated host names the app answers to (required in staging/production, no `*`). The first entry is also used by the container healthcheck.

Recommended / optional:
- `COOKIE_SECURE` — leave unset (default true); cannot be false in staging/production.
- `TRUSTED_PROXY_HEADER` — the one header the proxy sets with the client IP (e.g. `X-Real-IP` on Railway). **Must be verified on staging before use (ciso NS1):** confirm the proxy overwrites a client-sent value; if unsure leave it empty (rate limits then key on the proxy's IP).
- `PACK_PATH` — country-pack YAML; default `packs/placeholder/v0.yaml` inside the image.
- `PORT` — listen port (default 8000; Railway sets it).
- `PROOF_STORE_DIR` — filesystem ProofStore root, default `./var/proofs`. **Inside a container this is ephemeral** (lost on redeploy): deployed environments must use the bucket store (`PROOF_STORE`, `BUCKET_ENDPOINT`, `BUCKET_NAME`, `BUCKET_REGION`, `BUCKET_ACCESS_KEY_ID`, `BUCKET_SECRET_ACCESS_KEY`; ADR 0005 B1, separate PR).
- Tuning (defaults in `app/cloverproof_app/config.py`): `HSTS_INCLUDE_SUBDOMAINS`, `SESSION_IDLE_MINUTES`, `SESSION_ABSOLUTE_HOURS`, `LOGIN_*`, `ARGON2_*`, `DB_POOL_MAX_SIZE`, `REVIEW_MINUTES_CAP`.

## Portability (ADR 0009 §4)
The same image runs on Railway or a Canadian host (DigitalOcean TOR1 / Google Cloud Toronto–Montréal): plain Postgres + PostGIS, env vars only, no Railway-specific variable references in code, no platform volume as a data store. On Railway, set variables per service (reference syntax such as `${{postgis.RAILWAY_PRIVATE_DOMAIN}}` belongs in the Railway variable, never in the repo). Elsewhere, pass the same names via the platform's secret store or `--env-file`.
Moving hosts = build/push the image, run `make db-migrate` against the new database, set the variables, deploy, check `/healthz`.
