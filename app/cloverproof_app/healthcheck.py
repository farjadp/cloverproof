"""Container HEALTHCHECK: `python -m cloverproof_app.healthcheck` (exit 0 = healthy).

GETs /healthz on 127.0.0.1:$PORT. The app's TrustedHostMiddleware refuses unknown Host
headers, so the request carries the first ALLOWED_HOSTS entry (a `*.` wildcard gets a
`healthcheck.` label); without ALLOWED_HOSTS (development/test) Host is `localhost`.
Standard library only: the image has no curl.
"""

from __future__ import annotations

import http.client
import os
import sys
from collections.abc import Mapping

HEALTH_PATH = "/healthz"
DEFAULT_PORT = 8000


def health_host(environ: Mapping[str, str]) -> str:
    hosts = [h.strip() for h in environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
    if not hosts:
        return "localhost"
    host = hosts[0]
    return "healthcheck." + host[2:] if host.startswith("*.") else host


def port(environ: Mapping[str, str]) -> int:
    raw = environ.get("PORT", "").strip()
    return int(raw) if raw.isdigit() else DEFAULT_PORT


def check(environ: Mapping[str, str] | None = None, timeout: float = 3.0) -> bool:
    env = os.environ if environ is None else environ
    conn = http.client.HTTPConnection("127.0.0.1", port(env), timeout=timeout)
    try:
        conn.request("GET", HEALTH_PATH, headers={"Host": health_host(env)})
        return conn.getresponse().status == 200
    except OSError:
        return False
    finally:
        conn.close()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(0 if check() else 1)
