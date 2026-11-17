"""Container HEALTHCHECK helper: Host header and port selection, and a live round trip."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from cloverproof_app.healthcheck import check, health_host, port


def test_health_host_defaults_to_localhost() -> None:
    assert health_host({}) == "localhost"
    assert health_host({"ALLOWED_HOSTS": " , "}) == "localhost"


def test_health_host_uses_first_allowed_host() -> None:
    assert health_host({"ALLOWED_HOSTS": "app.example.ca, other.example.ca"}) == "app.example.ca"


def test_health_host_wildcard_gets_a_label() -> None:
    assert health_host({"ALLOWED_HOSTS": "*.example.ca"}) == "healthcheck.example.ca"


def test_port_default_and_override() -> None:
    assert port({}) == 8000
    assert port({"PORT": "9123"}) == 9123
    assert port({"PORT": "not-a-port"}) == 8000


def _serve(status: int, seen: list[str]) -> HTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            seen.append(f"{self.path} {self.headers['Host']}")
            self.send_response(status)
            self.end_headers()

        def log_message(self, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_check_round_trip() -> None:
    seen: list[str] = []
    server = _serve(200, seen)
    try:
        env = {"PORT": str(server.server_port), "ALLOWED_HOSTS": "app.example.ca"}
        assert check(env) is True
    finally:
        server.shutdown()
        server.server_close()
    assert seen == ["/healthz app.example.ca"]


def test_check_fails_on_error_status_and_closed_port() -> None:
    server = _serve(400, [])
    closed_port = server.server_port
    try:
        assert check({"PORT": str(closed_port)}) is False
    finally:
        server.shutdown()
        server.server_close()
    assert check({"PORT": str(closed_port)}, timeout=0.5) is False
