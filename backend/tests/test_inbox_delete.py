from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Channel, Delivery, Notification, ServiceIdentity, Source, Subscription, User
from app.notification_service import persist_notification, resolve_route
from app.schemas import NotificationCreate
from app.security import TokenPrincipal
from app.user_security import CSRF_HEADER, hash_password


def _producer(identity_id: int) -> TokenPrincipal:
    return TokenPrincipal(
        token_id=1,
        service_identity_id=identity_id,
        service_identity_name="Acceptance",
        scopes=frozenset({"notifications:write"}),
    )


def _seed() -> tuple[int, int, int]:
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Acceptance")
        channel = Channel(slug="acceptance-test", name="Acceptance Test")
        first = User(
            username="first",
            display_name="First User",
            password_hash=hash_password("first user password 123"),
        )
        second = User(
            username="second",
            display_name="Second User",
            password_hash=hash_password("second user password 123"),
        )
        session.add_all([identity, channel, first, second])
        session.flush()
        source = Source(service_identity_id=identity.id, slug="acceptance-test", name="Acceptance Test")
        session.add(source)
        session.flush()
        session.add_all(
            [
                Subscription(user_id=first.id, channel_id=channel.id, enabled=True),
                Subscription(user_id=second.id, channel_id=channel.id, enabled=True),
            ]
        )
        session.commit()
        identity_id, first_id, second_id = identity.id, first.id, second.id

    with SessionLocal() as session:
        route = resolve_route(
            session,
            _producer(identity_id),
            source_slug="acceptance-test",
            channel_slug="acceptance-test",
        )
        notification = persist_notification(
            session,
            route,
            NotificationCreate(
                source="acceptance-test",
                channel="acceptance-test",
                title="Delete me",
                body="Owned inbox deletion acceptance fixture.",
                severity="normal",
            ),
        )
        first_delivery = session.scalar(
            select(Delivery).where(
                Delivery.notification_id == notification.id,
                Delivery.user_id == first_id,
            )
        )
        second_delivery = session.scalar(
            select(Delivery).where(
                Delivery.notification_id == notification.id,
                Delivery.user_id == second_id,
            )
        )
        assert first_delivery is not None and second_delivery is not None
        return first_delivery.id, second_delivery.id, notification.id


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/session", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.headers[CSRF_HEADER]


def test_owned_inbox_delete_removes_only_callers_delivery() -> None:
    first_delivery_id, second_delivery_id, notification_id = _seed()
    with TestClient(app) as client:
        csrf = _login(client, "first", "first user password 123")
        response = client.delete(
            f"/api/v1/inbox/{first_delivery_id}",
            headers={CSRF_HEADER: csrf},
        )
    assert response.status_code == 204

    with SessionLocal() as session:
        assert session.get(Delivery, first_delivery_id) is None
        assert session.get(Delivery, second_delivery_id) is not None
        assert session.get(Notification, notification_id) is not None


def test_inbox_delete_requires_valid_csrf() -> None:
    first_delivery_id, _, _ = _seed()
    with TestClient(app) as client:
        _login(client, "first", "first user password 123")
        missing = client.delete(f"/api/v1/inbox/{first_delivery_id}")
        invalid = client.delete(
            f"/api/v1/inbox/{first_delivery_id}",
            headers={CSRF_HEADER: "invalid"},
        )
    assert missing.status_code == 403
    assert invalid.status_code == 403


def test_cross_user_inbox_delete_is_hidden() -> None:
    _, second_delivery_id, _ = _seed()
    with TestClient(app) as client:
        csrf = _login(client, "first", "first user password 123")
        response = client.delete(
            f"/api/v1/inbox/{second_delivery_id}",
            headers={CSRF_HEADER: csrf},
        )
    assert response.status_code == 404


def test_deleted_delivery_disappears_from_inbox() -> None:
    first_delivery_id, _, _ = _seed()
    with TestClient(app) as client:
        csrf = _login(client, "first", "first user password 123")
        assert client.delete(
            f"/api/v1/inbox/{first_delivery_id}",
            headers={CSRF_HEADER: csrf},
        ).status_code == 204
        inbox = client.get("/api/v1/inbox")
    assert inbox.status_code == 200
    assert all(item["id"] != first_delivery_id for item in inbox.json())
