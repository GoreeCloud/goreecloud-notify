from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Channel, Delivery, ServiceIdentity, Source, Subscription, User
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


def seed_subscription_fixture() -> tuple[int, int, int, int]:
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Healthchecks")
        health = Channel(
            slug="goreecloud-healthchecks",
            name="Healthchecks",
            description="Healthchecks alerts",
        )
        netbird = Channel(
            slug="netbird-alerts",
            name="NetBird",
            description="NetBird alerts",
        )
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
        session.add_all([identity, health, netbird, first, second])
        session.flush()
        source = Source(
            service_identity_id=identity.id,
            slug="healthchecks",
            name="Healthchecks",
        )
        session.add(source)
        session.flush()
        session.add_all(
            [
                Subscription(user_id=first.id, channel_id=health.id, enabled=True),
                Subscription(user_id=second.id, channel_id=health.id, enabled=True),
            ]
        )
        session.commit()
        return identity.id, first.id, second.id, health.id


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/session", json={"username": username, "password": password})
    assert response.status_code == 200
    csrf_token = response.headers[CSRF_HEADER]
    assert csrf_token
    return csrf_token


def publish(identity_id: int, title: str) -> int:
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
                title=title,
                body=title.lower(),
                severity="normal",
            ),
        )
        return notification.id


def test_subscription_listing_shows_all_channels_with_owned_state() -> None:
    seed_subscription_fixture()
    with TestClient(app) as client:
        login(client, "first", "first user password 123")
        response = client.get("/api/v1/subscriptions")

    assert response.status_code == 200
    states = {item["channel"]: item["subscribed"] for item in response.json()}
    assert states == {
        "goreecloud-healthchecks": True,
        "netbird-alerts": False,
    }


def test_subscription_mutations_require_valid_csrf() -> None:
    seed_subscription_fixture()
    with TestClient(app) as client:
        csrf_token = login(client, "first", "first user password 123")
        missing = client.put("/api/v1/subscriptions/netbird-alerts")
        invalid = client.put(
            "/api/v1/subscriptions/netbird-alerts",
            headers={CSRF_HEADER: "wrong-token"},
        )
        valid = client.put(
            "/api/v1/subscriptions/netbird-alerts",
            headers={CSRF_HEADER: csrf_token},
        )

    assert missing.status_code == 403
    assert invalid.status_code == 403
    assert valid.status_code == 200
    assert valid.json()["subscribed"] is True


def test_subscribe_and_unsubscribe_are_idempotent() -> None:
    _, first_id, _, _ = seed_subscription_fixture()
    with TestClient(app) as client:
        csrf_token = login(client, "first", "first user password 123")
        headers = {CSRF_HEADER: csrf_token}
        first_enable = client.put("/api/v1/subscriptions/netbird-alerts", headers=headers)
        second_enable = client.put("/api/v1/subscriptions/netbird-alerts", headers=headers)
        first_disable = client.delete("/api/v1/subscriptions/netbird-alerts", headers=headers)
        second_disable = client.delete("/api/v1/subscriptions/netbird-alerts", headers=headers)

    assert first_enable.status_code == 200 and first_enable.json()["subscribed"] is True
    assert second_enable.status_code == 200 and second_enable.json()["subscribed"] is True
    assert first_disable.status_code == 200 and first_disable.json()["subscribed"] is False
    assert second_disable.status_code == 200 and second_disable.json()["subscribed"] is False

    with SessionLocal() as session:
        channel = session.scalar(select(Channel).where(Channel.slug == "netbird-alerts"))
        assert channel is not None
        rows = session.scalars(
            select(Subscription).where(
                Subscription.user_id == first_id,
                Subscription.channel_id == channel.id,
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].enabled is False


def test_subscription_mutation_cannot_change_another_users_row() -> None:
    _, first_id, second_id, health_channel_id = seed_subscription_fixture()
    with TestClient(app) as client:
        csrf_token = login(client, "first", "first user password 123")
        response = client.delete(
            "/api/v1/subscriptions/goreecloud-healthchecks",
            headers={CSRF_HEADER: csrf_token},
        )

    assert response.status_code == 200
    assert response.json()["subscribed"] is False
    with SessionLocal() as session:
        first = session.scalar(
            select(Subscription).where(
                Subscription.user_id == first_id,
                Subscription.channel_id == health_channel_id,
            )
        )
        second = session.scalar(
            select(Subscription).where(
                Subscription.user_id == second_id,
                Subscription.channel_id == health_channel_id,
            )
        )
        assert first is not None and first.enabled is False
        assert second is not None and second.enabled is True


def test_unknown_subscription_channel_returns_404() -> None:
    seed_subscription_fixture()
    with TestClient(app) as client:
        csrf_token = login(client, "first", "first user password 123")
        response = client.put(
            "/api/v1/subscriptions/not-a-channel",
            headers={CSRF_HEADER: csrf_token},
        )
    assert response.status_code == 404


def test_producer_bearer_token_cannot_authenticate_subscription_endpoints() -> None:
    seed_subscription_fixture()
    with TestClient(app) as client:
        listing = client.get(
            "/api/v1/subscriptions",
            headers={"Authorization": "Bearer gcn_not_a_user_session"},
        )
        mutation = client.put(
            "/api/v1/subscriptions/netbird-alerts",
            headers={
                "Authorization": "Bearer gcn_not_a_user_session",
                CSRF_HEADER: "not-relevant",
            },
        )
    assert listing.status_code == 401
    assert mutation.status_code == 401


def test_unsubscribe_stops_future_fanout_without_deleting_history_and_resubscribe_resumes() -> None:
    identity_id, first_id, _, _ = seed_subscription_fixture()
    first_notification_id = publish(identity_id, "First")

    with TestClient(app) as client:
        csrf_token = login(client, "first", "first user password 123")
        headers = {CSRF_HEADER: csrf_token}
        assert client.delete(
            "/api/v1/subscriptions/goreecloud-healthchecks",
            headers=headers,
        ).status_code == 200
        second_notification_id = publish(identity_id, "Second")

        assert client.put(
            "/api/v1/subscriptions/goreecloud-healthchecks",
            headers=headers,
        ).status_code == 200
        third_notification_id = publish(identity_id, "Third")

    with SessionLocal() as session:
        first_delivery = session.scalar(
            select(Delivery).where(
                Delivery.user_id == first_id,
                Delivery.notification_id == first_notification_id,
            )
        )
        second_delivery = session.scalar(
            select(Delivery).where(
                Delivery.user_id == first_id,
                Delivery.notification_id == second_notification_id,
            )
        )
        third_delivery = session.scalar(
            select(Delivery).where(
                Delivery.user_id == first_id,
                Delivery.notification_id == third_notification_id,
            )
        )
        assert first_delivery is not None
        assert second_delivery is None
        assert third_delivery is not None
