"""App configuration, read from environment variables only.

Required: DATABASE_URL, SESSION_SECRET. Optional: PACK_PATH (country-pack YAML the engine
uses; default packs/placeholder/v0.yaml in the repo). Missing or invalid values stop the app
at startup (fail fast) with a message that names the variable but never prints its value.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

MIN_SECRET_LENGTH = 32
ALLOWED_ENVS = frozenset({"development", "test", "staging", "production"})


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
    db_pool_max_size: int = 5
    # Empty = the repo's packs/placeholder/v0.yaml (resolved in main.py).
    pack_path: str = ""

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

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        missing = [name for name in ("DATABASE_URL", "SESSION_SECRET") if not env.get(name)]
        if missing:
            raise ConfigError(f"missing required environment variables: {', '.join(missing)}")
        optional: dict[str, object] = {}
        if env.get("ENV"):
            optional["env"] = env["ENV"].strip().lower()
        if env.get("COOKIE_SECURE"):
            optional["cookie_secure"] = _bool("COOKIE_SECURE", env["COOKIE_SECURE"])
        if env.get("PACK_PATH"):
            optional["pack_path"] = env["PACK_PATH"].strip()
        for name, field in (
            ("SESSION_IDLE_MINUTES", "session_idle_minutes"),
            ("SESSION_ABSOLUTE_HOURS", "session_absolute_hours"),
            ("LOGIN_MAX_FAILURES", "login_max_failures"),
            ("LOGIN_WINDOW_MINUTES", "login_window_minutes"),
            ("DB_POOL_MAX_SIZE", "db_pool_max_size"),
        ):
            if env.get(name):
                optional[field] = _positive_int(name, env[name])
        return cls(
            database_url=env["DATABASE_URL"],
            session_secret=env["SESSION_SECRET"],
            **optional,  # type: ignore[arg-type]
        )
