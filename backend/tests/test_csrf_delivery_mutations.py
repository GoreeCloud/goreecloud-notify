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


def producer(identity_id: int) -> TokenPrincipal:
    return TokenPrincipal(
        token_id=1,
        service_identity_id=identity_id,
        service_identity_name="Healthchecks",
        scopes=frozenset({"notifications:write"}),
    )


def seed_mutation_fixture() -> tuple[int, int, int]:
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Healthchecks")
        channel = Channel(slug="goreecloud-healthchecks", name="Healthchecks")
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
        source = Source(service_identity_id=identity.id, slug="healthchecks", name="Healthchecks")
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
            producer(identity_id),
            source_slug="healthchecks",
            channel_slug="goreecloud-healthchecks",
        )
        notification = persist_notification(
            session,
            route,
            NotificationCreate(
                source="healthchecks",
                channel="goreecloud-healthchecks",
                title="Backup complete",
                body="Backup completed successfully.",
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


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/session", json={"username": username, "password": password})
    assert response.status_code == 200
    token = response.headers[CSRF_HEADER]
    assert token
    return token


def test_csrf_token_is_session_bound_and_recoverable_for_authenticated_spa() -> None:
    seed_mutation_fixture()
    with TestClient(app) as first_client, TestClient(app) as second_client:
        first_token = login(first_client, "first", "first user password 123")
        second_token = login(second_client, "second", "second user password 123")
        assert first_token != second_token
        recovered = first_client.get("/api/v1/csrf")
        assert recovered.status_code == 200
        assert recovered.json()["csrf_token"] == first_token


def test_delivery_mutation_rejects_missing_and_invalid_csrf_tokens() -> None:
    first_delivery_id, _, _ = seed_mutation_fixture()
    with TestClient(app) as client:
        csrf_token = login(client, "first", "first user password 123")
        missing = client.post(f"/api/v1/inbox/{first_delivery_id}/read")
        invalid = client.post(
            f"/api/v1/inbox/{first_delivery_id}/read",
            headers={CSRF_HEADER: "wrong-token"},
        )
        valid = client.post(
            f"/api/v1/inbox/{first_delivery_id}/read",
            headers={CSRF_HEADER: csrf_token},
        )

    assert missing.status_code == 403
    assert missing.json()["detail"] == "CSRF token required"
    assert invalid.status_code == 403
    assert invalid.json()["detail"] == "invalid CSRF token"
    assert valid.status_code == 200
    assert valid.json()["read_at"] is not None


def test_owned_read_unread_and_acknowledgement_transitions() -> None:
    first_delivery_id, _, _ = seed_mutation_fixture()
    with TestClient(app) as client:
        csrf_token = login(client, "first", "first user password 123")
        headers = {CSRF_HEADER: csrf_token}

        marked_read = client.post(f"/api/v1/inbox/{first_delivery_id}/read", headers=headers)
        assert marked_read.status_code == 200
        first_read_at = marked_read.json()["read_at"]
        assert first_read_at is not None
        assert marked_read.json()["acknowledged_at"] is None

        repeated_read = client.post(f"/api/v1/inbox/{first_delivery_id}/read", headers=headers)
        assert repeated_read.status_code == 200
        assert repeated_read.json()["read_at"] == first_read_at

        marked_unread = client.delete(f"/api/v1/inbox/{first_delivery_id}/read", headers=headers)
        assert marked_unread.status_code == 200
        assert marked_unread.json()["read_at"] is None
        assert marked_unread.json()["acknowledged_at"] is None

        acknowledged = client.post(
            f"/api/v1/inbox/{first_delivery_id}/acknowledge",
            headers=headers,
        )
        assert acknowledged.status_code == 200
        assert acknowledged.json()["acknowledged_at"] is not None
        assert acknowledged.json()["read_at"] is not None
        first_ack = acknowledged.json()["acknowledged_at"]

        repeated_ack = client.post(
            f"/api/v1/inbox/{first_delivery_id}/acknowledge",
            headers=headers,
        )
        assert repeated_ack.status_code == 200
        assert repeated_ack.json()["acknowledged_at"] == first_ack

        unread_after_ack = client.delete(f"/api/v1/inbox/{first_delivery_id}/read", headers=headers)
        assert unread_after_ack.status_code == 200
        assert unread_after_ack.json()["read_at"] is None
        assert unread_after_ack.json()["acknowledged_at"] == first_ack


def test_cross_user_mutation_is_hidden_even_with_valid_csrf() -> None:
    _, second_delivery_id, _ = seed_mutation_fixture()
    with TestClient(app) as client:
        csrf_token = login(client, "first", "first user password 123")
        response = client.post(
            f"/api/v1/inbox/{second_delivery_id}/read",
            headers={CSRF_HEADER: csrf_token},
        )
    assert response.status_code == 404


def test_producer_bearer_token_cannot_satisfy_human_mutation_authentication() -> None:
    first_delivery_id, _, _ = seed_mutation_fixture()
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/inbox/{first_delivery_id}/read",
            headers={
                "Authorization": "Bearer gcn_not_a_human_session",
                CSRF_HEADER: "not-relevant",
            },
        )
    assert response.status_code == 401


def test_acknowledgement_state_persists_in_delivery_row() -> None:
    first_delivery_id, _, notification_id = seed_mutation_fixture()
    with TestClient(app) as client:
        csrf_token = login(client, "first", "first user password 123")
        assert client.post(
            f"/api/v1/inbox/{first_delivery_id}/acknowledge",
            headers={CSRF_HEADER: csrf_token},
        ).status_code == 200

    with SessionLocal() as session:
        delivery = session.get(Delivery, first_delivery_id)
        notification = session.get(Notification, notification_id)
        assert delivery is not None and notification is not None
        assert delivery.read_at is not None
        assert delivery.acknowledged_at is not None
