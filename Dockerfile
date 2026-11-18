# CloverProof internal tool (app/): one portable image for Railway or a Canadian host
# (ADR 0009 §4). Configuration through env vars only; see docs/runbook-webapp.md.
# Migrations are NOT run on start: an operator runs `make db-migrate` (runbook).

ARG PYTHON_IMAGE=python:3.12-slim

# ---- build: resolve the locked deps into /srv/app/.venv ----
FROM ${PYTHON_IMAGE} AS build
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.12 \
    UV_PROJECT_ENVIRONMENT=/srv/app/.venv
WORKDIR /srv/app

# Third-party deps first (cached layer). Every workspace member's pyproject.toml is needed
# to read uv.lock; only the app and the engine are installed (no data_sources, no dev group).
COPY pyproject.toml uv.lock ./
COPY app/pyproject.toml app/pyproject.toml
COPY engine/pyproject.toml engine/pyproject.toml
COPY data_sources/pyproject.toml data_sources/pyproject.toml
RUN \
    uv sync --frozen --no-dev --package cloverproof-app --no-install-workspace

# Our code. Workspace members stay editable, so the repo layout (packs/, db/migrations/)
# resolves the same way as in a checkout (cloverproof_app.db.migrate.REPO_ROOT).
COPY engine/cloverproof_engine engine/cloverproof_engine
COPY app/cloverproof_app app/cloverproof_app
COPY packs packs
COPY db/migrations db/migrations
RUN \
    uv sync --frozen --no-dev --package cloverproof-app

# ---- runtime ----
FROM ${PYTHON_IMAGE} AS runtime

# WeasyPrint system libraries (same set as CI) + fontconfig with one fallback font; the
# proof PDF embeds its own Source Sans/Serif (app/cloverproof_app/static/fonts).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fontconfig fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /srv/app --shell /usr/sbin/nologin app

WORKDIR /srv/app
COPY --from=build --chown=root:root /srv/app /srv/app
# Filesystem ProofStore default (./var/proofs) is writable but ephemeral in a container:
# deployed environments must use the bucket store (ADR 0005 B1).
RUN mkdir -p /srv/app/var/proofs && chown -R app:app /srv/app/var

ENV PATH=/srv/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/tmp/.cache \
    PORT=8000

USER app:app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-m", "cloverproof_app.healthcheck"]

# Shell form only to expand ${PORT}; exec keeps uvicorn as PID 1 (receives SIGTERM).
CMD ["sh", "-c", "exec uvicorn --factory cloverproof_app.main:create_app --host 0.0.0.0 --port ${PORT:-8000} --no-server-header"]
