import pytest

from cloverproof_app import security
from cloverproof_app.ratelimit import LoginRateLimiter


def test_password_hash_is_argon2id_and_verifies() -> None:
    hashed = security.hash_password("correct horse battery")
    assert hashed.startswith("$argon2id$")
    assert security.verify_password("correct horse battery", hashed) == (True, None)
    assert security.verify_password("wrong password!!", hashed)[0] is False


def test_short_password_rejected() -> None:
    with pytest.raises(ValueError, match="at least"):
        security.hash_password("short")


def test_missing_or_malformed_hash_never_verifies() -> None:
    assert security.verify_password("anything at all", None) == (False, None)
    assert security.verify_password("anything at all", "$argon2id$garbage") == (False, None)


def test_token_hash_is_sha256_hex() -> None:
    token = security.new_token()
    digest = security.token_sha256(token)
    assert len(digest) == 64 and token not in digest


def test_csrf_token_bound_to_secret_and_session() -> None:
    a = security.csrf_token("s" * 40, "a" * 64)
    assert a == security.csrf_token("s" * 40, "a" * 64)
    assert a != security.csrf_token("s" * 40, "b" * 64)
    assert a != security.csrf_token("t" * 40, "a" * 64)
    assert security.same(a, a) and not security.same(a, None) and not security.same("", "")


def test_rate_limiter_blocks_after_max_failures_then_expires() -> None:
    now = [0.0]
    limiter = LoginRateLimiter(3, 60, clock=lambda: now[0])
    for _ in range(3):
        assert not limiter.is_blocked("A@x.org", "1.1.1.1")
        limiter.record_failure("a@x.org", "1.1.1.1")
    assert limiter.is_blocked("a@X.org ", "1.1.1.1")
    assert not limiter.is_blocked("a@x.org", "2.2.2.2")  # other IP
    assert not limiter.is_blocked("b@x.org", "1.1.1.1")  # other email
    now[0] = 61
    assert not limiter.is_blocked("a@x.org", "1.1.1.1")


def test_rate_limiter_reset_on_success() -> None:
    limiter = LoginRateLimiter(1, 60)
    limiter.record_failure("a@x.org", "ip")
    assert limiter.is_blocked("a@x.org", "ip")
    limiter.reset("a@x.org", "ip")
    assert not limiter.is_blocked("a@x.org", "ip")
