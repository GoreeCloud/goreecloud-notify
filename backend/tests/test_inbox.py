from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.delivery_service import fanout_notification, list_inbox
from app.main import app
from app.models import (
    Channel,
    Delivery,
    Notification,
    ServiceIdentity,
    Source,
    Subscription,
    User,
)
from app.notification_service import persist_notification, resolve_route
from app.schemas import NotificationCreate
from app.security import TokenPrincipal
from app.user_security import UserPrincipal, hash_password


def producer(identity_id: int) -> TokenPrincipal:
    return TokenPrincipal(
        token_id=1,
        service_identity_id=identity_id,
        service_identity_name="Healthchecks",
        scopes=frozenset({"notifications:write"}),
    )


def seed_inbox_fixture() -> tuple[int, int, int, int]:
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Healthchecks")
        channel = Channel(slug="goreecloud-healthchecks", name="Healthchecks")
        first_user = User(
            username="first",
            display_name="First User",
            password_hash=hash_password("first user password 123"),
        )
        second_user = User(
            username="second",
            display_name="Second User",
            password_hash=hash_password("second user password 123"),
        )
        inactive = User(
            username="inactive",
            display_name="Inactive User",
            password_hash=hash_password("inactive user password 123"),
            is_active=False,
        )
        disabled_subscription_user = User(
            username="disabled-sub",
            display_name="Disabled Sub",
            password_hash=hash_password("disabled sub password 123"),
        )
        session.add_all([identity, channel, first_user, second_user, inactive, disabled_subscription_user])
        session.flush()
        source = Source(service_identity_id=identity.id, slug="healthchecks", name="Healthchecks")
        session.add(source)
        session.flush()
        session.add_all(
            [
                Subscription(user_id=first_user.id, channel_id=channel.id, enabled=True),
                Subscription(user_id=second_user.id, channel_id=channel.id, enabled=True),
                Subscription(user_id=inactive.id, channel_id=channel.id, enabled=True),
                Subscription(user_id=disabled_subscription_user.id, channel_id=channel.id, enabled=False),
            ]
        )
        session.commit()
        return identity.id, first_user.id, second_user.id, channel.id


def publish(identity_id: int, *, title: str = "Backup complete", severity: str = "normal") -> int:
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
                severity=severity,
            ),
        )
        return notification.id


def login(client: TestClient, username: str, password: str) -> None:
    response = client.post("/api/v1/session", json={"username": username, "password": password})
    assert response.status_code == 200


def test_notification_persistence_fans_out_only_to_active_enabled_subscribers() -> None:
    identity_id, first_user_id, second_user_id, _ = seed_inbox_fixture()
    notification_id = publish(identity_id)

    with SessionLocal() as session:
        deliveries = session.scalars(
            select(Delivery).where(Delivery.notification_id == notification_id).order_by(Delivery.user_id)
        ).all()
        assert [delivery.user_id for delivery in deliveries] == sorted([first_user_id, second_user_id])


def test_fanout_is_idempotent_for_existing_notification() -> None:
    identity_id, first_user_id, second_user_id, _ = seed_inbox_fixture()
    notification_id = publish(identity_id)

    with SessionLocal() as session:
        notification = session.get(Notification, notification_id)
        assert notification is not None
        assert fanout_notification(session, notification) == 0
        session.commit()
        user_ids = session.scalars(
            select(Delivery.user_id).where(Delivery.notification_id == notification_id)
        ).all()
        assert sorted(user_ids) == sorted([first_user_id, second_user_id])


def test_inbox_endpoint_requires_human_session_not_producer_auth() -> None:
    identity_id, _, _, _ = seed_inbox_fixture()
    publish(identity_id)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/inbox",
            headers={"Authorization": "Bearer gcn_not_a_user_session"},
        )
    assert response.status_code == 401


def test_inbox_lists_only_authenticated_users_deliveries_and_hides_other_detail() -> None:
    identity_id, first_user_id, second_user_id, _ = seed_inbox_fixture()
    notification_id = publish(identity_id)

    with SessionLocal() as session:
        first_delivery = session.scalar(
            select(Delivery).where(
                Delivery.notification_id == notification_id,
                Delivery.user_id == first_user_id,
            )
        )
        second_delivery = session.scalar(
            select(Delivery).where(
                Delivery.notification_id == notification_id,
                Delivery.user_id == second_user_id,
            )
        )
        assert first_delivery is not None and second_delivery is not None
        first_delivery_id = first_delivery.id
        second_delivery_id = second_delivery.id

    with TestClient(app) as client:
        login(client, "first", "first user password 123")
        listing = client.get("/api/v1/inbox")
        assert listing.status_code == 200
        assert [item["id"] for item in listing.json()] == [first_delivery_id]
        assert listing.json()[0]["notification_id"] == notification_id

        owned = client.get(f"/api/v1/inbox/{first_delivery_id}")
        assert owned.status_code == 200
        hidden = client.get(f"/api/v1/inbox/{second_delivery_id}")
        assert hidden.status_code == 404


def test_inbox_filters_read_acknowledgement_source_channel_severity_and_cursor() -> None:
    identity_id, first_user_id, _, _ = seed_inbox_fixture()
    first_notification = publish(identity_id, title="First", severity="info")
    second_notification = publish(identity_id, title="Second", severity="critical")
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        first_delivery = session.scalar(
            select(Delivery).where(
                Delivery.notification_id == first_notification,
                Delivery.user_id == first_user_id,
            )
        )
        second_delivery = session.scalar(
            select(Delivery).where(
                Delivery.notification_id == second_notification,
                Delivery.user_id == first_user_id,
            )
        )
        assert first_delivery is not None and second_delivery is not None
        first_delivery.read_at = now
        first_delivery.acknowledged_at = now
        session.commit()
        first_id = first_delivery.id
        second_id = second_delivery.id

    with TestClient(app) as client:
        login(client, "first", "first user password 123")
        unread = client.get("/api/v1/inbox?read=false")
        assert [item["id"] for item in unread.json()] == [second_id]

        acknowledged = client.get("/api/v1/inbox?acknowledged=true")
        assert [item["id"] for item in acknowledged.json()] == [first_id]

        critical = client.get("/api/v1/inbox?severity=critical&source=healthchecks&channel=goreecloud-healthchecks")
        assert [item["id"] for item in critical.json()] == [second_id]

        older = client.get(f"/api/v1/inbox?before_id={second_id}&limit=1")
        assert [item["id"] for item in older.json()] == [first_id]


def test_list_inbox_service_uses_principal_user_id_not_request_supplied_identity() -> None:
    identity_id, first_user_id, second_user_id, _ = seed_inbox_fixture()
    publish(identity_id)
    with SessionLocal() as session:
        first = list_inbox(
            session,
            UserPrincipal(
                user_id=first_user_id,
                session_id=1,
                username="first",
                display_name="First User",
            ),
        )
        second = list_inbox(
            session,
            UserPrincipal(
                user_id=second_user_id,
                session_id=2,
                username="second",
                display_name="Second User",
            ),
        )
        assert len(first) == 1
        assert len(second) == 1
        assert first[0].id != second[0].id
        assert first[0].notification_id == second[0].notification_id
