import pytest

from cloverproof_app.config import ConfigError, Settings

SECRET = "s" * 40
BASE = {"DATABASE_URL": "postgresql://u@h/db", "SESSION_SECRET": SECRET}


def test_defaults_are_secure() -> None:
    settings = Settings.from_env(BASE)
    assert settings.cookie_secure is True
    assert settings.env == "development"


@pytest.mark.parametrize("missing", ["DATABASE_URL", "SESSION_SECRET"])
def test_missing_required_var_fails_fast(missing: str) -> None:
    env = {k: v for k, v in BASE.items() if k != missing}
    with pytest.raises(ConfigError, match=missing):
        Settings.from_env(env)


def test_error_never_contains_the_value() -> None:
    with pytest.raises(ConfigError) as error:
        Settings.from_env({**BASE, "SESSION_SECRET": "short-secret-value"})
    assert "short-secret-value" not in str(error.value)


def test_cookie_secure_false_rejected_in_production() -> None:
    with pytest.raises(ConfigError, match="COOKIE_SECURE"):
        Settings.from_env({**BASE, "ENV": "production", "COOKIE_SECURE": "false"})


def test_cookie_secure_false_allowed_in_development() -> None:
    assert Settings.from_env({**BASE, "COOKIE_SECURE": "false"}).cookie_secure is False


@pytest.mark.parametrize("raw", ["maybe", ""])
def test_bad_values_are_explicit(raw: str) -> None:
    if not raw:
        assert Settings.from_env({**BASE, "COOKIE_SECURE": raw}).cookie_secure is True
        return
    with pytest.raises(ConfigError, match="COOKIE_SECURE"):
        Settings.from_env({**BASE, "COOKIE_SECURE": raw})


def test_bad_number_is_explicit() -> None:
    with pytest.raises(ConfigError, match="SESSION_IDLE_MINUTES"):
        Settings.from_env({**BASE, "SESSION_IDLE_MINUTES": "0"})
