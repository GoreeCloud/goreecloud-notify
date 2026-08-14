from fastapi.testclient import TestClient

from app.main import app


def test_healthz() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "GoreeCloud Notify"


def test_meta_keeps_notification_writes_disabled_in_milestone_1() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["milestone"] == 1
    assert payload["production"] is False
    assert payload["notification_writes_enabled"] is False
    assert len(payload["entities"]) == 10
