"""Login rate limit per (email, client IP).

In memory, per process. That is enough for one app instance (Phase 0-3: one Railway
service, <= 4 users). With several instances or workers each keeps its own counts, so
the effective limit multiplies; move this to Postgres before scaling out.
A restart clears the counts.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from threading import Lock


class LoginRateLimiter:
    def __init__(
        self,
        max_failures: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_failures = max_failures
        self.window = window_seconds
        self._clock = clock
        self._failures: dict[tuple[str, str], list[float]] = {}
        self._lock = Lock()

    @staticmethod
    def key(email: str, ip: str) -> tuple[str, str]:
        return (email.strip().lower(), ip)

    def _recent(self, key: tuple[str, str], now: float) -> list[float]:
        recent = [t for t in self._failures.get(key, []) if now - t < self.window]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def is_blocked(self, email: str, ip: str) -> bool:
        with self._lock:
            return len(self._recent(self.key(email, ip), self._clock())) >= self.max_failures

    def record_failure(self, email: str, ip: str) -> None:
        with self._lock:
            now = self._clock()
            key = self.key(email, ip)
            self._failures[key] = [*self._recent(key, now), now]
            if len(self._failures) > 10_000:  # bound memory under a spray of emails
                for stale in [k for k in self._failures if not self._recent(k, now)]:
                    self._failures.pop(stale, None)

    def reset(self, email: str, ip: str) -> None:
        with self._lock:
            self._failures.pop(self.key(email, ip), None)
