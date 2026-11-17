"""S6, S8, N6 (security review S2-auth-review-step5): hosts, asset URLs, HSTS, htmx cache.

No lifespan runs here (TestClient without `with`), so no database or role check is needed.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from cloverproof_app.config import ConfigError, Settings
from cloverproof_app.main import create_app

from .support.fakes import NoDatabase, make_settings

SECRET = "s" * 40
HTML = {"accept": "text/html"}


def client(base_url: str = "http://testserver", **overrides: object) -> TestClient:
    return TestClient(create_app(make_settings(**overrides), NoDatabase()), base_url=base_url)


def test_asset_urls_are_path_only() -> None:
    # Behind a TLS-terminating proxy the app sees http://; absolute URLs would be mixed content.
    page = client().get("/missing", headers=HTML)
    assert page.status_code == 404
    assets = re.findall(r'(?:href|src)="([^"]+)"', page.text)
    static = [a for a in assets if "static" in a]
    assert static and all(a.startswith("/static/") for a in static), static
    assert "http://" not in page.text and "testserver" not in page.text


def test_htmx_history_cache_disabled() -> None:
    page = client().get("/missing", headers=HTML)
    assert '"historyCacheSize": 0' in page.text


def test_unknown_host_is_rejected() -> None:
    app = client(env="production", allowed_hosts=("plans.example.org",))
    assert app.get("/healthz", headers={"host": "evil.example"}).status_code == 400
    ok = app.get("/healthz", headers={"host": "plans.example.org"})
    assert ok.status_code == 200


def test_development_default_hosts() -> None:
    settings = Settings.from_env(
        {"DATABASE_URL": "postgresql://u@localhost/db", "SESSION_SECRET": SECRET}
    )
    assert settings.allowed_hosts == ("localhost", "127.0.0.1")
    dev = TestClient(create_app(settings, NoDatabase()), base_url="http://localhost")
    assert dev.get("/healthz").status_code == 200
    assert dev.get("/healthz", headers={"host": "evil.example"}).status_code == 400


@pytest.mark.parametrize("env", ["staging", "production"])
def test_allowed_hosts_required_when_deployed(env: str) -> None:
    base = {"DATABASE_URL": "postgresql://u@db.internal/db", "SESSION_SECRET": SECRET, "ENV": env}
    with pytest.raises(ConfigError, match="ALLOWED_HOSTS"):
        Settings.from_env(base)
    with pytest.raises(ConfigError, match="ALLOWED_HOSTS"):
        Settings.from_env({**base, "ALLOWED_HOSTS": "*"})
    settings = Settings.from_env({**base, "ALLOWED_HOSTS": " plans.example.org , x.up.railway.app"})
    assert settings.allowed_hosts == ("plans.example.org", "x.up.railway.app")


@pytest.mark.parametrize("env", ["staging", "production"])
def test_hsts_when_deployed(env: str) -> None:
    app = client("https://testserver", env=env, allowed_hosts=("testserver",))
    assert app.get("/healthz").headers["strict-transport-security"] == "max-age=31536000"


def test_hsts_include_subdomains_is_opt_in() -> None:
    app = client(
        "https://testserver",
        env="production",
        allowed_hosts=("testserver",),
        hsts_include_subdomains=True,
    )
    value = app.get("/healthz").headers["strict-transport-security"]
    assert value == "max-age=31536000; includeSubDomains"


def test_no_hsts_in_development() -> None:
    dev = client("http://localhost", env="development")
    assert "strict-transport-security" not in dev.get("/healthz").headers


def test_hsts_flag_read_from_env() -> None:
    settings = Settings.from_env(
        {
            "DATABASE_URL": "postgresql://u@localhost/db",
            "SESSION_SECRET": SECRET,
            "HSTS_INCLUDE_SUBDOMAINS": "true",
        }
    )
    assert settings.hsts_include_subdomains is True
