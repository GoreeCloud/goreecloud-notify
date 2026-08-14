from __future__ import annotations

import time
from datetime import datetime, timezone

import app.security as security
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.datetime_utils import as_utc
from app.main import app
from app.models import AccessToken, Channel, Notification, ServiceIdentity, Source
from app.security import token_digest

UTC = timezone.utc
ADMIN_HEADER = {"X-GoreeCloud-Admin-Token": "admin-test-token"}


def configure_admin(monkeypatch) -> None:
    monkeypatch.setattr(
        security,
        "settings",
        type("TestSettings", (), {"admin_token": "admin-test-token"})(),
    )


def seed_producer(*, scopes: str = "notifications:read notifications:write") -> str:
    raw_token = "gcn_datetime_contract"
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Datetime Producer")
        session.add(identity)
        session.flush()
        session.add_all(
            [
                Source(service_identity_id=identity.id, slug="datetime", name="Datetime"),
                Channel(slug="goreecloud-datetime", name="GoreeCloud Datetime"),
                AccessToken(
                    service_identity_id=identity.id,
                    name="datetime-test",
                    token_digest=token_digest(raw_token),
                    scope=scopes,
                ),
            ]
        )
        session.commit()
    return raw_token


def parse_api_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_native_notification_expiration_requires_explicit_timezone() -> None:
    token = seed_producer()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "source": "datetime",
                "channel": "goreecloud-datetime",
                "title": "Naive expiry",
                "body": "Must be rejected",
                "expires_at": "2026-08-14T12:00:00",
            },
        )

    assert response.status_code == 422
    assert "explicit timezone offset" in response.text


def test_native_notification_expiration_is_persisted_and_returned_in_utc() -> None:
    token = seed_producer()
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "source": "datetime",
                "channel": "goreecloud-datetime",
                "title": "Offset expiry",
                "body": "Normalize me",
                "expires_at": "2026-08-14T12:00:00-05:00",
            },
        )

        assert created.status_code == 201
        payload = created.json()
        assert parse_api_datetime(payload["created_at"]).utcoffset() == timezone.utc.utcoffset(None)
        assert parse_api_datetime(payload["expires_at"]) == datetime(2026, 8, 14, 17, tzinfo=UTC)

        history = client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert history.status_code == 200
    history_item = history.json()[0]
    assert parse_api_datetime(history_item["created_at"]).utcoffset() == timezone.utc.utcoffset(None)
    assert parse_api_datetime(history_item["expires_at"]) == datetime(2026, 8, 14, 17, tzinfo=UTC)

    with SessionLocal() as session:
        record = session.scalar(select(Notification))
        assert record is not None
        assert record.expires_at == datetime(2026, 8, 14, 17)


def test_admin_token_expiration_requires_explicit_timezone(monkeypatch) -> None:
    configure_admin(monkeypatch)
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Token Datetime")
        session.add(identity)
        session.commit()
        identity_id = identity.id

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tokens",
            headers=ADMIN_HEADER,
            json={
                "service_identity_id": identity_id,
                "name": "naive-expiry",
                "scopes": ["notifications:read"],
                "expires_at": "2026-08-14T12:00:00",
            },
        )

    assert response.status_code == 422
    assert "explicit timezone offset" in response.text


def test_admin_token_expiration_is_persisted_and_returned_in_utc(monkeypatch) -> None:
    configure_admin(monkeypatch)
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Token Datetime")
        session.add(identity)
        session.commit()
        identity_id = identity.id

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tokens",
            headers=ADMIN_HEADER,
            json={
                "service_identity_id": identity_id,
                "name": "offset-expiry",
                "scopes": ["notifications:read"],
                "expires_at": "2026-08-14T12:00:00-05:00",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert parse_api_datetime(payload["expires_at"]) == datetime(2026, 8, 14, 17, tzinfo=UTC)

    with SessionLocal() as session:
        record = session.get(AccessToken, payload["id"])
        assert record is not None
        assert record.expires_at == datetime(2026, 8, 14, 17)


def test_ntfy_epoch_conversion_does_not_depend_on_process_local_timezone(monkeypatch) -> None:
    token = seed_producer(scopes="notifications:write")

    with monkeypatch.context() as timezone_context:
        timezone_context.setenv("TZ", "America/Chicago")
        time.tzset()
        with TestClient(app) as client:
            response = client.post(
                "/goreecloud-datetime",
                content="Timezone-independent epoch",
                headers={"Authorization": f"Bearer {token}"},
            )
    time.tzset()

    assert response.status_code == 200
    with SessionLocal() as session:
        notification = session.scalar(select(Notification))
        assert notification is not None
        expected_epoch = int(as_utc(notification.created_at).timestamp())

    assert response.json()["time"] == expected_epoch


def test_retention_expiry_count_uses_normalized_absolute_instant(monkeypatch) -> None:
    configure_admin(monkeypatch)
    with SessionLocal() as session:
        payload_expiry = datetime.fromisoformat("2026-01-09T20:00:00-05:00").astimezone(UTC)
        session.add(
            Notification(
                title="Offset crosses cutoff",
                body="The absolute expiry is after the UTC cutoff.",
                severity="normal",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                expires_at=payload_expiry,
            )
        )
        session.commit()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/admin/retention/preview",
            headers=ADMIN_HEADER,
            params={"cutoff": "2026-01-10T00:00:00Z"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_notifications"] == 1
    assert payload["candidate_explicitly_expired_notifications"] == 0
