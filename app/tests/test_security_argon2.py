"""S2 (security review S2-auth-review-step5): argon2 runs at most N at a time."""

from __future__ import annotations

import threading

import pytest

from cloverproof_app import security
from cloverproof_app.main import create_app

from .support.fakes import NoDatabase, make_settings

PASSWORD = "correct horse battery staple"


def test_slots_bound_concurrent_verifies() -> None:
    security.configure_hashing(max_concurrency=2, acquire_timeout_seconds=5)
    active = 0
    peak = 0
    lock = threading.Lock()
    real = security._hasher.verify_and_update

    def counting(password: str, hashed: str):  # type: ignore[no-untyped-def]
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            return real(password, hashed)
        finally:
            with lock:
                active -= 1

    hashed = security.hash_password(PASSWORD)
    security._hasher.verify_and_update = counting  # type: ignore[method-assign]
    try:
        threads = [
            threading.Thread(target=security.verify_password, args=(PASSWORD, hashed))
            for _ in range(6)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        security._hasher.verify_and_update = real  # type: ignore[method-assign]
    assert 1 <= peak <= 2


def test_slot_timeout_raises_busy() -> None:
    security.configure_hashing(max_concurrency=1, acquire_timeout_seconds=0.05)
    held = security.hash_slots()
    assert held.acquire(timeout=1)
    try:
        with pytest.raises(security.HashingBusy):
            security.verify_password(PASSWORD, None)
        with pytest.raises(security.HashingBusy):
            security.hash_password(PASSWORD)
    finally:
        held.release()
        security.configure_hashing(max_concurrency=2, acquire_timeout_seconds=5)


def test_create_app_applies_hashing_settings() -> None:
    create_app(make_settings(argon2_max_concurrency=3), NoDatabase())
    slots = security.hash_slots()
    got = [slots.acquire(timeout=0) for _ in range(4)]
    for ok in got:
        if ok:
            slots.release()
    assert got == [True, True, True, False]
    create_app(make_settings(), NoDatabase())  # back to the default (2)
