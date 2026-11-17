from fastapi.testclient import TestClient

from cloverproof_app.main import create_app

from .support.fakes import NoDatabase, make_settings


def test_healthz_returns_ok() -> None:
    with TestClient(create_app(make_settings(), NoDatabase())) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
