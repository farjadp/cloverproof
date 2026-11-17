"""App configuration, read from environment variables only.

Required: DATABASE_URL, SESSION_SECRET; ENV too when DATABASE_URL is not on localhost.
Optional: PACK_PATH (country-pack YAML the engine uses; default packs/placeholder/v0.yaml
in the repo), login limits, proxy header, hosts and HSTS (see the fields below).
Missing or invalid values stop the app at startup (fail fast) with a message that names
the variable but never prints its value.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

import psycopg
from psycopg.conninfo import conninfo_to_dict

MIN_SECRET_LENGTH = 32
ALLOWED_ENVS = frozenset({"development", "test", "staging", "production"})
_HEADER_NAME = re.compile(r"^[A-Za-z0-9-]+$")
LOCAL_DB_HOSTS = frozenset({"", "localhost", "127.0.0.1", "::1"})
DEPLOYED_ENVS = frozenset({"staging", "production"})
DEV_ALLOWED_HOSTS = ("localhost", "127.0.0.1")
TEST_ALLOWED_HOSTS = ("testserver", *DEV_ALLOWED_HOSTS)  # Starlette TestClient's host


class ConfigError(RuntimeError):
    """A required environment variable is missing or invalid."""


def _bool(name: str, raw: str) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be true or false")


def _positive_int(name: str, raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as error:
        raise ConfigError(f"{name} must be a whole number") from error
    if value <= 0:
        raise ConfigError(f"{name} must be greater than 0")
    return value


def is_local_database(url: str) -> bool:
    """True when every host in the connection string is this machine (or a unix socket)."""
    try:
        params = conninfo_to_dict(url)
    except psycopg.ProgrammingError:
        return False
    hosts = str(params.get("host") or "").split(",")
    return all(h.strip() in LOCAL_DB_HOSTS or h.strip().startswith("/") for h in hosts)


@dataclass(frozen=True)
class Settings:
    database_url: str
    session_secret: str
    env: str = "development"
    cookie_secure: bool = True
    session_idle_minutes: int = 120
    session_absolute_hours: int = 12
    login_max_failures: int = 5
    login_window_minutes: int = 15
    # S1: per client IP (429) and per account (soft, 503; unlock via `cli user-unlock`).
    login_ip_max_failures: int = 30
    login_account_max_failures: int = 20
    login_account_window_minutes: int = 60
    # Empty = the TCP peer (request.client.host). Set to the one header the proxy controls,
    # e.g. X-Real-IP on Railway. Never "*"; a list header uses its rightmost entry.
    trusted_proxy_header: str = ""
    # S2: at most N argon2 computations at once; wait this long for a slot, else 503.
    argon2_max_concurrency: int = 2
    argon2_acquire_timeout_seconds: int = 5
    # S2: failed logins per minute across all accounts and IPs before every login gets 503.
    login_global_max_failures_per_minute: int = 30
    db_pool_max_size: int = 5
    # Empty = the repo's packs/placeholder/v0.yaml (resolved in main.py).
    pack_path: str = ""
    # S6: Host header allow-list (TrustedHostMiddleware). Required in staging/production;
    # empty in development/test = localhost and 127.0.0.1 (+ testserver for tests).
    allowed_hosts: tuple[str, ...] = ()
    # S8: HSTS max-age=31536000 in staging/production; includeSubDomains only when every
    # subdomain of the custom domain serves HTTPS.
    hsts_include_subdomains: bool = False
    # F4: minutes stored per review are capped here (a tab left open); capped reviews are
    # flagged in the review reason.
    review_minutes_cap: int = 240

    def __post_init__(self) -> None:
        if not self.database_url.strip():
            raise ConfigError("DATABASE_URL is required")
        if len(self.session_secret) < MIN_SECRET_LENGTH:
            raise ConfigError(
                f"SESSION_SECRET is required and must be at least {MIN_SECRET_LENGTH} characters"
            )
        if self.env not in ALLOWED_ENVS:
            raise ConfigError(f"ENV must be one of {', '.join(sorted(ALLOWED_ENVS))}")
        if self.env in {"staging", "production"} and not self.cookie_secure:
            raise ConfigError("COOKIE_SECURE cannot be false in staging or production")
        if self.env in DEPLOYED_ENVS:
            if not self.allowed_hosts or "*" in self.allowed_hosts:
                raise ConfigError(
                    "ALLOWED_HOSTS is required in staging or production"
                    " (comma-separated host names, no *)"
                )
        elif not self.allowed_hosts:
            default = TEST_ALLOWED_HOSTS if self.env == "test" else DEV_ALLOWED_HOSTS
            object.__setattr__(self, "allowed_hosts", default)
        if self.trusted_proxy_header and not _HEADER_NAME.match(self.trusted_proxy_header):
            raise ConfigError("TRUSTED_PROXY_HEADER must be one header name, e.g. X-Real-IP")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        missing = [name for name in ("DATABASE_URL", "SESSION_SECRET") if not env.get(name)]
        if missing:
            raise ConfigError(f"missing required environment variables: {', '.join(missing)}")
        optional: dict[str, object] = {}
        if env.get("ENV", "").strip():
            optional["env"] = env["ENV"].strip().lower()
        elif not is_local_database(env["DATABASE_URL"]):
            # N7: production-only checks (S4, S6, S8) must not be skipped by a missing ENV.
            raise ConfigError(
                "ENV is required when DATABASE_URL is not a local database"
                " (set ENV=production, staging or development)"
            )
        if env.get("COOKIE_SECURE"):
            optional["cookie_secure"] = _bool("COOKIE_SECURE", env["COOKIE_SECURE"])
        if env.get("HSTS_INCLUDE_SUBDOMAINS"):
            optional["hsts_include_subdomains"] = _bool(
                "HSTS_INCLUDE_SUBDOMAINS", env["HSTS_INCLUDE_SUBDOMAINS"]
            )
        hosts = tuple(h.strip() for h in env.get("ALLOWED_HOSTS", "").split(",") if h.strip())
        if hosts:
            optional["allowed_hosts"] = hosts
        if env.get("TRUSTED_PROXY_HEADER"):
            optional["trusted_proxy_header"] = env["TRUSTED_PROXY_HEADER"].strip()
        if env.get("PACK_PATH"):
            optional["pack_path"] = env["PACK_PATH"].strip()
        for name, field in (
            ("SESSION_IDLE_MINUTES", "session_idle_minutes"),
            ("SESSION_ABSOLUTE_HOURS", "session_absolute_hours"),
            ("LOGIN_MAX_FAILURES", "login_max_failures"),
            ("LOGIN_WINDOW_MINUTES", "login_window_minutes"),
            ("LOGIN_IP_MAX_FAILURES", "login_ip_max_failures"),
            ("LOGIN_ACCOUNT_MAX_FAILURES", "login_account_max_failures"),
            ("LOGIN_ACCOUNT_WINDOW_MINUTES", "login_account_window_minutes"),
            ("ARGON2_MAX_CONCURRENCY", "argon2_max_concurrency"),
            ("ARGON2_ACQUIRE_TIMEOUT_SECONDS", "argon2_acquire_timeout_seconds"),
            ("LOGIN_GLOBAL_MAX_FAILURES_PER_MINUTE", "login_global_max_failures_per_minute"),
            ("DB_POOL_MAX_SIZE", "db_pool_max_size"),
            ("REVIEW_MINUTES_CAP", "review_minutes_cap"),
        ):
            if env.get(name):
                optional[field] = _positive_int(name, env[name])
        return cls(
            database_url=env["DATABASE_URL"],
            session_secret=env["SESSION_SECRET"],
            **optional,  # type: ignore[arg-type]
        )
