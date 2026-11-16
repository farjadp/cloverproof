"""Login limits (security review S2, items S1 and S2).

Four sliding-window failure counters, checked before a password is verified:

- per client IP (hard, 429): one source cannot spray guesses across many emails;
- per (email, IP) (429): the original limit, a typo-friendly short block;
- per account (soft, 503 + log line): a distributed attacker cannot guess one account's
  password from many IPs. Unlocked by `cli user-unlock --email` (via `UnlockListener`) or by
  waiting for the window to pass;
- global (503): a ceiling on failed logins per minute across all keys, so a spray of new
  emails/IPs cannot keep the argon2 slots busy.

Accounts are keyed by the SHA-256 of the lowercased email, so no email sits in memory or
logs. The client IP comes from `web.client_ip` (TRUSTED_PROXY_HEADER, never X-Forwarded-For
by default).

The store is in memory, per process. That is enough for one app instance (Phase 0-3: one
Railway service, <= 4 users). With several instances or workers each keeps its own counts,
so the effective limits multiply; move the counters to Postgres before scaling out.
A restart clears all counts.
"""

from __future__ import annotations

import enum
import hashlib
import logging
import time
from collections.abc import Callable
from threading import Lock

import psycopg

log = logging.getLogger(__name__)

UNLOCK_CHANNEL = "cp_login_unlock"
_MAX_KEYS = 10_000  # bound memory under a spray of emails/IPs


def account_key(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


class SlidingWindow:
    """Failure timestamps per key within `window` seconds. Thread-safe."""

    def __init__(self, max_failures: int, window_seconds: float, clock: Callable[[], float]):
        self.max_failures = max_failures
        self.window = window_seconds
        self._clock = clock
        self._failures: dict[str, list[float]] = {}
        self._lock = Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        recent = [t for t in self._failures.get(key, []) if now - t < self.window]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def count(self, key: str) -> int:
        with self._lock:
            return len(self._recent(key, self._clock()))

    def is_blocked(self, key: str) -> bool:
        return self.count(key) >= self.max_failures

    def record(self, key: str) -> int:
        with self._lock:
            now = self._clock()
            self._failures[key] = [*self._recent(key, now), now]
            if len(self._failures) > _MAX_KEYS:
                for stale in [k for k in self._failures if not self._recent(k, now)]:
                    self._failures.pop(stale, None)
            return len(self._failures.get(key, []))

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


class LoginRateLimiter:
    """Per (email, client IP) limit; kept as its own class for the unit tests."""

    def __init__(
        self,
        max_failures: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._window = SlidingWindow(max_failures, window_seconds, clock)

    @staticmethod
    def key(email: str, ip: str) -> str:
        return f"{account_key(email)}|{ip}"

    def is_blocked(self, email: str, ip: str) -> bool:
        return self._window.is_blocked(self.key(email, ip))

    def record_failure(self, email: str, ip: str) -> None:
        self._window.record(self.key(email, ip))

    def reset(self, email: str, ip: str) -> None:
        self._window.reset(self.key(email, ip))


class LoginDecision(enum.Enum):
    OK = "ok"
    IP_BLOCKED = "ip"  # 429
    PAIR_BLOCKED = "pair"  # 429
    ACCOUNT_PAUSED = "account"  # 503
    GLOBAL_BUDGET = "global"  # 503


class LoginGuard:
    def __init__(
        self,
        *,
        pair_max: int,
        pair_window: float,
        ip_max: int,
        ip_window: float,
        account_max: int,
        account_window: float,
        global_max: int,
        global_window: float = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.pair = LoginRateLimiter(pair_max, pair_window, clock)
        self.ip = SlidingWindow(ip_max, ip_window, clock)
        self.account = SlidingWindow(account_max, account_window, clock)
        self.total = SlidingWindow(global_max, global_window, clock)
        self.unlock_listener: UnlockListener | None = None

    def check(self, email: str, ip: str) -> LoginDecision:
        if self.ip.is_blocked(ip):
            return LoginDecision.IP_BLOCKED
        if self.pair.is_blocked(email, ip):
            return LoginDecision.PAIR_BLOCKED
        key = account_key(email)
        if self.account.is_blocked(key) and self.unlock_listener is not None:
            self.unlock_listener.poll(self)  # a pending CLI unlock clears it now
        if self.account.is_blocked(key):
            return LoginDecision.ACCOUNT_PAUSED
        if self.total.is_blocked("*"):
            return LoginDecision.GLOBAL_BUDGET
        return LoginDecision.OK

    def record_failure(self, email: str, ip: str) -> None:
        self.ip.record(ip)
        self.pair.record_failure(email, ip)
        self.total.record("*")
        key = account_key(email)
        if self.account.record(key) == self.account.max_failures:
            # One line when the soft limit trips; the key prefix matches `cli user-unlock`.
            log.warning(
                "login paused for account %s after %d failures; unlock with"
                " `python -m cloverproof_app.cli user-unlock --email ...`",
                key[:12],
                self.account.max_failures,
            )

    def record_success(self, email: str, ip: str) -> None:
        # Only the (email, IP) pair: a success must not wipe an attacker's IP or account count.
        self.pair.reset(email, ip)

    def unlock_account(self, key: str) -> None:
        self.account.reset(key)
        log.warning("login unlocked for account %s", key[:12])


class UnlockListener:
    """Receives `cli user-unlock` notifications (Postgres LISTEN/NOTIFY, payload = account key).

    No background thread: `poll` drains pending notifications when a paused account tries to
    sign in. Notifications sent while the app is down or the connection is lost are dropped;
    a restart clears all counters anyway.
    """

    def __init__(self, database_url: str) -> None:
        self._url = database_url
        self._conn: psycopg.Connection | None = None
        self._lock = Lock()

    def open(self) -> None:
        with self._lock:
            self._connect()

    def _connect(self) -> None:
        if self._conn is not None and not self._conn.closed:
            return
        try:
            self._conn = psycopg.connect(self._url, autocommit=True, connect_timeout=5)
            self._conn.execute(f"listen {UNLOCK_CHANNEL}")
        except psycopg.Error:
            log.error("login unlock listener could not connect; CLI unlock will not apply")
            self._conn = None

    def poll(self, guard: LoginGuard) -> None:
        with self._lock:
            self._connect()
            if self._conn is None:
                return
            try:
                for notify in self._conn.notifies(timeout=0.01):
                    if len(notify.payload) == 64:
                        guard.unlock_account(notify.payload)
            except psycopg.Error:
                log.error("login unlock listener lost its connection", exc_info=True)
                self._conn = None

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None
