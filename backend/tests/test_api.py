from fastapi.testclient import TestClient

from app.main import app


def test_healthz() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "GoreeCloud Notify"


def test_meta_tracks_glaze_ui_inbox_development() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["milestone"] == 1
    assert payload["production"] is False
    assert payload["notification_writes_enabled"] is True
    assert payload["development_milestone"] == 3
    assert payload["next_milestone"] == "Glaze UI Inbox"
    assert payload["next_slice"] == "Milestone 3 manual browser and accessibility acceptance"
    assert len(payload["entities"]) == 10
    assert "opaque server-side user sessions" in payload["implemented_engine"]
    assert "user-owned subscription administration" in payload["implemented_engine"]
    assert "non-destructive administrator retention preview" in payload["implemented_engine"]
    assert "authenticated Glaze UI inbox" in payload["implemented_experience"]
    assert "server-backed notification search and filtering" in payload["implemented_experience"]
    assert "cursor-based inbox pagination" in payload["implemented_experience"]
    assert "Glaze UI channel subscription management" in payload["implemented_experience"]
    assert "fail-visible logout behavior" in payload["implemented_experience"]
    assert "responsive layout and appearance controls" in payload["implemented_experience"]
    assert "Chromium browser interaction validation" in payload["implemented_experience"]
    assert "automated WCAG A and AA accessibility checks" in payload["implemented_experience"]
