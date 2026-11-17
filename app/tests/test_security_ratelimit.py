"""S1/S2 (security review S2-auth-review-step5): login counters and client IP, no database."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from cloverproof_app.config import ConfigError, Settings
from cloverproof_app.ratelimit import LoginDecision, LoginGuard, account_key
from cloverproof_app.web import client_ip

from .support.fakes import make_settings


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def guard(clock: Clock, **overrides: int) -> LoginGuard:
    values = {
        "pair_max": 5,
        "pair_window": 900,
        "ip_max": 10,
        "ip_window": 900,
        "account_max": 20,
        "account_window": 3600,
        "global_max": 1000,
        "global_window": 60,
    }
    values.update(overrides)
    return LoginGuard(**values, clock=clock)  # type: ignore[arg-type]


def test_ip_counter_blocks_across_emails() -> None:
    g = guard(Clock(), ip_max=3)
    for i in range(3):
        assert g.check(f"user{i}@x.org", "1.1.1.1") is LoginDecision.OK
        g.record_failure(f"user{i}@x.org", "1.1.1.1")
    assert g.check("fresh@x.org", "1.1.1.1") is LoginDecision.IP_BLOCKED
    assert g.check("fresh@x.org", "2.2.2.2") is LoginDecision.OK


def test_account_soft_limit_across_ips_then_expires() -> None:
    clock = Clock()
    g = guard(clock, account_max=4, ip_max=100, pair_max=100)
    for i in range(4):
        g.record_failure("farjad@x.org", f"10.0.0.{i}")
    assert g.check("Farjad@X.org ", "10.9.9.9") is LoginDecision.ACCOUNT_PAUSED
    assert g.check("other@x.org", "10.9.9.9") is LoginDecision.OK
    clock.now = 3601
    assert g.check("farjad@x.org", "10.9.9.9") is LoginDecision.OK


def test_account_unlock_clears_only_that_account() -> None:
    g = guard(Clock(), account_max=1, pair_max=100, ip_max=100)
    g.record_failure("a@x.org", "ip1")
    g.record_failure("b@x.org", "ip1")
    g.unlock_account(account_key("A@x.org"))
    assert g.check("a@x.org", "ip2") is LoginDecision.OK
    assert g.check("b@x.org", "ip2") is LoginDecision.ACCOUNT_PAUSED


def test_success_resets_pair_but_not_account_or_ip() -> None:
    g = guard(Clock(), pair_max=2, ip_max=3, account_max=3)
    g.record_failure("a@x.org", "ip")
    g.record_failure("a@x.org", "ip")
    assert g.check("a@x.org", "ip") is LoginDecision.PAIR_BLOCKED
    g.record_success("a@x.org", "ip")
    assert g.check("a@x.org", "ip") is LoginDecision.OK
    g.record_failure("a@x.org", "ip")
    assert g.check("a@x.org", "ip") is LoginDecision.IP_BLOCKED


def test_global_failure_budget_per_minute() -> None:
    clock = Clock()
    g = guard(clock, global_max=3, ip_max=100, account_max=100, pair_max=100)
    for i in range(3):
        g.record_failure(f"u{i}@x.org", f"ip{i}")
    assert g.check("new@x.org", "new-ip") is LoginDecision.GLOBAL_BUDGET
    clock.now = 61
    assert g.check("new@x.org", "new-ip") is LoginDecision.OK


def test_account_key_is_a_hash_not_the_email() -> None:
    key = account_key(" Farjad@Example.org ")
    assert key == account_key("farjad@example.org")
    assert "farjad" not in key and len(key) == 64


def _request(headers: dict[str, str], host: str = "203.0.113.9") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/login",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (host, 4000),
    }
    return Request(scope)


def test_client_ip_ignores_x_forwarded_for_by_default() -> None:
    settings = make_settings()
    request = _request({"X-Forwarded-For": "1.2.3.4"})
    assert client_ip(request, settings) == "203.0.113.9"


def test_client_ip_reads_only_the_configured_header() -> None:
    settings = make_settings(trusted_proxy_header="X-Real-IP")
    spoofed = _request({"X-Real-IP": "198.51.100.7", "X-Forwarded-For": "1.2.3.4"})
    assert client_ip(spoofed, settings) == "198.51.100.7"
    # Header missing: fall back to the peer address, never to another header.
    assert client_ip(_request({"X-Forwarded-For": "1.2.3.4"}), settings) == "203.0.113.9"


def test_client_ip_list_header_uses_the_rightmost_hop() -> None:
    settings = make_settings(trusted_proxy_header="X-Forwarded-For")
    request = _request({"X-Forwarded-For": "6.6.6.6, 198.51.100.7"})
    assert client_ip(request, settings) == "198.51.100.7"


@pytest.mark.parametrize("value", ["*", "X-Real-IP, X-Forwarded-For", "bad header"])
def test_trusted_proxy_header_rejects_wildcards_and_lists(value: str) -> None:
    with pytest.raises(ConfigError, match="TRUSTED_PROXY_HEADER"):
        Settings.from_env(
            {
                "DATABASE_URL": "postgresql://u@localhost/db",
                "SESSION_SECRET": "s" * 40,
                "TRUSTED_PROXY_HEADER": value,
            }
        )


def test_new_limits_read_from_env() -> None:
    settings = Settings.from_env(
        {
            "DATABASE_URL": "postgresql://u@localhost/db",
            "SESSION_SECRET": "s" * 40,
            "LOGIN_IP_MAX_FAILURES": "7",
            "LOGIN_ACCOUNT_MAX_FAILURES": "9",
            "LOGIN_ACCOUNT_WINDOW_MINUTES": "30",
            "TRUSTED_PROXY_HEADER": "X-Real-IP",
        }
    )
    assert settings.login_ip_max_failures == 7
    assert settings.login_account_max_failures == 9
    assert settings.login_account_window_minutes == 30
    assert settings.trusted_proxy_header == "X-Real-IP"
