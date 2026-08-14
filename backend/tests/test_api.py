from fastapi.testclient import TestClient

from app.main import app


def test_healthz() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "GoreeCloud Notify"
    assert "build_revision" not in response.json()


def test_meta_tracks_realtime_delivery_development() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["build_revision"] == "development"
    assert payload["milestone"] == 1
    assert payload["production"] is False
    assert payload["notification_writes_enabled"] is True
    assert payload["development_milestone"] == 4
    assert payload["next_milestone"] == "Real-Time Delivery"
    assert payload["next_slice"] == "Milestone 4 manual realtime and browser notification acceptance"
    assert len(payload["entities"]) == 10
    assert "opaque server-side user sessions" in payload["implemented_engine"]
    assert "user-owned subscription administration" in payload["implemented_engine"]
    assert "non-destructive administrator retention preview" in payload["implemented_engine"]
    assert "authenticated SSE inbox stream" in payload["implemented_engine"]
    assert "database-backed SSE delivery cursor" in payload["implemented_engine"]
    assert "Last-Event-ID replay contract" in payload["implemented_engine"]
    assert "long-lived user-session revalidation" in payload["implemented_engine"]
    assert "authoritative inbox state snapshot" in payload["implemented_engine"]
    assert "SSE aggregate inbox state events" in payload["implemented_engine"]
    assert "authenticated Glaze UI inbox" in payload["implemented_experience"]
    assert "server-backed notification search and filtering" in payload["implemented_experience"]
    assert "cursor-based inbox pagination" in payload["implemented_experience"]
    assert "Glaze UI channel subscription management" in payload["implemented_experience"]
    assert "fail-visible logout behavior" in payload["implemented_experience"]
    assert "responsive layout and appearance controls" in payload["implemented_experience"]
    assert "Chromium browser interaction validation" in payload["implemented_experience"]
    assert "automated WCAG A and AA accessibility checks" in payload["implemented_experience"]
    assert "real-time Glaze inbox delivery" in payload["implemented_experience"]
    assert "live connection and reconnect status" in payload["implemented_experience"]
    assert "stream-handshake inbox reconciliation" in payload["implemented_experience"]
    assert "authoritative inbox navigation counters" in payload["implemented_experience"]
    assert "cursor-bootstrap inbox synchronization" in payload["implemented_experience"]
    assert "reconnecting session validation" in payload["implemented_experience"]
    assert "fail-closed realtime resynchronization" in payload["implemented_experience"]
    assert "immediate filtered mutation reconciliation" in payload["implemented_experience"]
    assert "explicit offline realtime state" in payload["implemented_experience"]
    assert "last-received Delivery cursor offline recovery" in payload["implemented_experience"]
    assert "online recovery stream reconciliation" in payload["implemented_experience"]
    assert "privacy-first browser notification opt-in" in payload["implemented_experience"]
    assert "generic redacted system notification content" in payload["implemented_experience"]
    assert "hidden-page browser notification delivery" in payload["implemented_experience"]
    assert "foreground system-alert suppression" in payload["implemented_experience"]
    assert "replay and backlog system-alert suppression" in payload["implemented_experience"]
    assert "browser-local system-alert preference" in payload["implemented_experience"]
    assert "realtime REST reconciliation race protection" in payload["implemented_experience"]
