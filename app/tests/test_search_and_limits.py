"""N13 (password-change limiter key) and N15 (LIKE wildcards in search), no database."""

from __future__ import annotations

from cloverproof_app.ratelimit import LoginRateLimiter
from cloverproof_app.repo.farms import like_pattern


def test_like_pattern_escapes_wildcards() -> None:
    assert like_pattern("  North ") == "%north%"
    assert like_pattern("50%") == "%50\\%%"
    assert like_pattern("a_b") == "%a\\_b%"
    assert like_pattern("back\\slash") == "%back\\\\slash%"


def test_password_change_limiter_has_its_own_keys() -> None:
    login = LoginRateLimiter(2, 900)
    password = LoginRateLimiter(2, 900, prefix="password-change")
    assert login.key("a@example.org", "1.2.3.4") != password.key("a@example.org", "1.2.3.4")
    for _ in range(2):
        password.record_failure("a@example.org", "1.2.3.4")
    assert password.is_blocked("a@example.org", "1.2.3.4")
    assert not login.is_blocked("a@example.org", "1.2.3.4")
