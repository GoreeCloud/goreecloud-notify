from fastapi.testclient import TestClient

from app.main import app


def test_healthz() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "GoreeCloud Notify"


def test_meta_tracks_native_ingestion_development() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["milestone"] == 1
    assert payload["production"] is False
    assert payload["notification_writes_enabled"] is True
    assert payload["development_milestone"] == 2
    assert payload["next_slice"] == "retention policy and Milestone 2 hardening"
    assert len(payload["entities"]) == 10
    assert "opaque server-side user sessions" in payload["implemented_engine"]
    assert "user-owned subscription administration" in payload["implemented_engine"]
