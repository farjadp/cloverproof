"""Password hashing, session tokens and CSRF / cookie signing (ADR 0005 A1)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

# argon2id with pwdlib defaults (t=3, m=64 MiB, p=4), above OWASP's minimum profile.
log = logging.getLogger(__name__)
_hasher = PasswordHash((Argon2Hasher(),))
MIN_PASSWORD_LENGTH = 12

# Verified against when the email is unknown, so a miss costs the same time as a hit.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


class HashingBusy(RuntimeError):
    """No argon2 slot free within the timeout (security review S2): answer 503."""


# Each argon2 call uses 64 MiB and 4 lanes; without a bound, concurrent logins on the
# 40-thread pool can exhaust memory. Set from ARGON2_MAX_CONCURRENCY in create_app.
_slots = threading.BoundedSemaphore(2)
_acquire_timeout = 5.0


def configure_hashing(*, max_concurrency: int, acquire_timeout_seconds: float) -> None:
    global _slots, _acquire_timeout
    _slots = threading.BoundedSemaphore(max_concurrency)
    _acquire_timeout = acquire_timeout_seconds


def hash_slots() -> threading.BoundedSemaphore:
    return _slots


@contextmanager
def _slot() -> Iterator[None]:
    slots = _slots
    if not slots.acquire(timeout=_acquire_timeout):
        log.warning("argon2 busy: no slot within %.1f s", _acquire_timeout)
        raise HashingBusy("password hashing is busy")
    try:
        yield
    finally:
        slots.release()


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    with _slot():
        return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """(ok, new_hash). new_hash is set when the stored hash uses outdated parameters.

    Raises HashingBusy when no argon2 slot frees up in time.
    """
    with _slot():
        if not password_hash:
            _hasher.verify(password, _DUMMY_HASH)
            return False, None
        try:
            return _hasher.verify_and_update(password, password_hash)
        except Exception:  # malformed stored hash: a failed login, never a success
            log.error("stored password hash could not be verified (malformed?)", exc_info=True)
            return False, None


def new_token() -> str:
    """Random cookie token (256 bits)."""
    return secrets.token_urlsafe(32)


def token_sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def sign(secret: str, purpose: str, value: str) -> str:
    message = f"{purpose}:{value}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def csrf_token(secret: str, session_token_sha256: str) -> str:
    """Per-session CSRF token: derived from the session, so nothing extra is stored."""
    return sign(secret, "csrf", session_token_sha256)


def same(a: str | None, b: str | None) -> bool:
    return bool(a) and bool(b) and hmac.compare_digest(str(a), str(b))
