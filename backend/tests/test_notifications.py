from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Channel, Delivery, Notification, ServiceIdentity, Source, Subscription, User
from app.notification_service import (
    persist_notification,
    persist_notification_idempotent,
    resolve_route,
    to_read,
)
from app.schemas import NotificationCreate
from app.security import TokenPrincipal


@pytest.fixture(autouse=True)
def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def create_route_fixture():
    with SessionLocal() as session:
        owner = ServiceIdentity(name="Healthchecks")
        other = ServiceIdentity(name="Beszel")
        session.add_all([owner, other])
        session.flush()
        source = Source(service_identity_id=owner.id, slug="healthchecks", name="Healthchecks")
        channel = Channel(slug="goreecloud-healthchecks", name="GoreeCloud Healthchecks")
        session.add_all([source, channel])
        session.commit()
        return owner.id, other.id


def principal(identity_id: int, name: str) -> TokenPrincipal:
    return TokenPrincipal(
        token_id=1,
        service_identity_id=identity_id,
        service_identity_name=name,
        scopes=frozenset({"notifications:write"}),
    )


def _payload(
    *,
    source: str = "healthchecks",
    body: str = "Kopia snapshot completed successfully.",
) -> NotificationCreate:
    return NotificationCreate(
        source=source,
        channel="goreecloud-healthchecks",
        title="Backup completed",
        body=body,
        severity="info",
    )


def test_native_route_and_persistence_round_trip() -> None:
    owner_id, _ = create_route_fixture()
    with SessionLocal() as session:
        route = resolve_route(
            session,
            principal(owner_id, "Healthchecks"),
            source_slug="healthchecks",
            channel_slug="goreecloud-healthchecks",
        )
        notification = persist_notification(session, route, _payload())
        result = to_read(notification, route)

        assert result.source == "healthchecks"
        assert result.channel == "goreecloud-healthchecks"
        assert result.title == "Backup completed"
        assert session.scalar(select(Notification).where(Notification.id == notification.id)) is not None


def test_idempotent_ingestion_replays_one_notification_and_one_fanout() -> None:
    owner_id, _ = create_route_fixture()
    with SessionLocal() as session:
        route = resolve_route(
            session,
            principal(owner_id, "Healthchecks"),
            source_slug="healthchecks",
            channel_slug="goreecloud-healthchecks",
        )
        user = User(username="operator", display_name="Operator", is_active=True)
        session.add(user)
        session.flush()
        session.add(Subscription(user_id=user.id, channel_id=route.channel.id, enabled=True))
        session.commit()

        first = persist_notification_idempotent(
            session,
            route,
            _payload(),
            idempotency_key="monitor:incident:42:down",
        )
        replay = persist_notification_idempotent(
            session,
            route,
            _payload(),
            idempotency_key="monitor:incident:42:down",
        )

        assert first.replayed is False
        assert replay.replayed is True
        assert replay.notification.id == first.notification.id
        notifications = session.scalars(select(Notification)).all()
        deliveries = session.scalars(select(Delivery)).all()
        assert len(notifications) == 1
        assert len(deliveries) == 1
        assert notifications[0].idempotency_digest is not None
        assert notifications[0].idempotency_digest != "monitor:incident:42:down"


def test_same_external_idempotency_key_is_independent_across_sources() -> None:
    owner_id, other_id = create_route_fixture()
    with SessionLocal() as session:
        channel = session.scalar(select(Channel).where(Channel.slug == "goreecloud-healthchecks"))
        assert channel is not None
        session.add(Source(service_identity_id=other_id, slug="beszel", name="Beszel"))
        session.commit()

        healthchecks_route = resolve_route(
            session,
            principal(owner_id, "Healthchecks"),
            source_slug="healthchecks",
            channel_slug=channel.slug,
        )
        beszel_route = resolve_route(
            session,
            principal(other_id, "Beszel"),
            source_slug="beszel",
            channel_slug=channel.slug,
        )
        external_key = "shared-external-transition-id"

        healthchecks = persist_notification_idempotent(
            session,
            healthchecks_route,
            _payload(source="healthchecks"),
            idempotency_key=external_key,
        )
        beszel = persist_notification_idempotent(
            session,
            beszel_route,
            _payload(source="beszel"),
            idempotency_key=external_key,
        )

        assert healthchecks.replayed is False
        assert beszel.replayed is False
        assert healthchecks.notification.id != beszel.notification.id
        notifications = session.scalars(select(Notification).order_by(Notification.id)).all()
        assert len(notifications) == 2
        assert notifications[0].idempotency_digest == notifications[1].idempotency_digest
        assert notifications[0].source_id != notifications[1].source_id


def test_idempotency_key_reuse_with_different_payload_is_rejected() -> None:
    owner_id, _ = create_route_fixture()
    with SessionLocal() as session:
        route = resolve_route(
            session,
            principal(owner_id, "Healthchecks"),
            source_slug="healthchecks",
            channel_slug="goreecloud-healthchecks",
        )
        persist_notification_idempotent(
            session,
            route,
            _payload(),
            idempotency_key="monitor:incident:42:down",
        )

        with pytest.raises(HTTPException) as exc_info:
            persist_notification_idempotent(
                session,
                route,
                _payload(body="A different event accidentally reused the same key."),
                idempotency_key="monitor:incident:42:down",
            )
        assert exc_info.value.status_code == 409
        assert len(session.scalars(select(Notification)).all()) == 1


def test_native_route_rejects_source_impersonation() -> None:
    _, other_id = create_route_fixture()
    with SessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            resolve_route(
                session,
                principal(other_id, "Beszel"),
                source_slug="healthchecks",
                channel_slug="goreecloud-healthchecks",
            )
        assert exc_info.value.status_code == 403


def test_native_route_requires_existing_channel() -> None:
    owner_id, _ = create_route_fixture()
    with SessionLocal() as session:
        with pytest.raises(HTTPException) as exc_info:
            resolve_route(
                session,
                principal(owner_id, "Healthchecks"),
                source_slug="healthchecks",
                channel_slug="missing-channel",
            )
        assert exc_info.value.status_code == 404
