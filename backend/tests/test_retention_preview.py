from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.security as security
from app.database import SessionLocal
from app.main import app
from app.models import Delivery, Notification, User

UTC = timezone.utc
ADMIN_PASSWORD = "correct horse battery staple"


def utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


def configure_bootstrap(monkeypatch) -> None:
    monkeypatch.setattr(
        security,
        "settings",
        type("TestSettings", (), {"admin_token": "admin-test-token"})(),
    )


def establish_admin(client: TestClient, monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    created = client.post(
        "/api/v1/bootstrap/administrator",
        headers={"X-GoreeCloud-Admin-Token": "admin-test-token"},
        json={
            "username": "retention-admin",
            "display_name": "Retention Admin",
            "password": ADMIN_PASSWORD,
        },
    )
    assert created.status_code == 201
    logged_in = client.post(
        "/api/v1/session",
        json={"username": "retention-admin", "password": ADMIN_PASSWORD},
    )
    assert logged_in.status_code == 200


def seed_retention_preview() -> None:
    with SessionLocal() as session:
        first = User(username="first", display_name="First", password_hash=None)
        second = User(username="second", display_name="Second", password_hash=None)
        session.add_all([first, second])
        session.flush()

        old_expired = Notification(
            title="Old expired",
            body="old expired",
            severity="warning",
            created_at=utc(2026, 1, 1),
            expires_at=utc(2026, 1, 5),
        )
        old_future_expiry = Notification(
            title="Old future expiry",
            body="old future expiry",
            severity="normal",
            created_at=utc(2026, 1, 2),
            expires_at=utc(2026, 1, 20),
        )
        boundary = Notification(
            title="Boundary",
            body="boundary",
            severity="normal",
            created_at=utc(2026, 1, 10),
        )
        newer = Notification(
            title="Newer",
            body="newer",
            severity="info",
            created_at=utc(2026, 1, 11),
        )
        session.add_all([old_expired, old_future_expiry, boundary, newer])
        session.flush()

        session.add_all(
            [
                Delivery(
                    notification_id=old_expired.id,
                    user_id=first.id,
                    read_at=utc(2026, 1, 3),
                    acknowledged_at=utc(2026, 1, 4),
                ),
                Delivery(notification_id=old_expired.id, user_id=second.id),
                Delivery(
                    notification_id=old_future_expiry.id,
                    user_id=first.id,
                    read_at=utc(2026, 1, 3),
                ),
                Delivery(notification_id=boundary.id, user_id=first.id),
            ]
        )
        session.commit()


def table_counts() -> tuple[int, int, int]:
    with SessionLocal() as session:
        return (
            int(session.scalar(select(func.count()).select_from(Notification)) or 0),
            int(session.scalar(select(func.count()).select_from(Delivery)) or 0),
            int(session.scalar(select(func.count()).select_from(User)) or 0),
        )


def test_retention_preview_requires_admin_authorization() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/admin/retention/preview",
            params={"cutoff": "2026-01-10T00:00:00Z"},
        )
    assert response.status_code == 401


def test_retention_preview_requires_explicit_utc_cutoff(monkeypatch) -> None:
    with TestClient(app) as client:
        establish_admin(client, monkeypatch)
        missing = client.get("/api/v1/admin/retention/preview")
        naive = client.get(
            "/api/v1/admin/retention/preview",
            params={"cutoff": "2026-01-10T00:00:00"},
        )
        non_utc = client.get(
            "/api/v1/admin/retention/preview",
            params={"cutoff": "2026-01-10T00:00:00-06:00"},
        )

    assert missing.status_code == 422
    assert naive.status_code == 422
    assert non_utc.status_code == 422


def test_retention_preview_reports_candidate_state_without_mutation(monkeypatch) -> None:
    with TestClient(app) as client:
        establish_admin(client, monkeypatch)
        seed_retention_preview()
        before = table_counts()
        response = client.get(
            "/api/v1/admin/retention/preview",
            params={"cutoff": "2026-01-10T00:00:00Z"},
        )

    after = table_counts()
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "preview_only"
    assert payload["cutoff_basis"] == "notification_created_at_before_cutoff"
    assert payload["destructive_action_enabled"] is False
    assert payload["candidate_notifications"] == 2
    assert payload["candidate_deliveries"] == 3
    assert payload["candidate_read_deliveries"] == 2
    assert payload["candidate_unread_deliveries"] == 1
    assert payload["candidate_acknowledged_deliveries"] == 1
    assert payload["candidate_unacknowledged_deliveries"] == 2
    assert payload["candidate_explicitly_expired_notifications"] == 1
    assert payload["oldest_candidate_created_at"].startswith("2026-01-01T00:00:00")
    assert payload["newest_candidate_created_at"].startswith("2026-01-02T00:00:00")
    assert before == (4, 4, 3)
    assert after == before


def test_retention_preview_cutoff_is_strictly_before(monkeypatch) -> None:
    with TestClient(app) as client:
        establish_admin(client, monkeypatch)
        seed_retention_preview()
        response = client.get(
            "/api/v1/admin/retention/preview",
            params={"cutoff": "2026-01-02T00:00:00Z"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_notifications"] == 1
    assert payload["candidate_deliveries"] == 2
