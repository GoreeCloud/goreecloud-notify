from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Channel, Notification, ServiceIdentity, Source
from app.notification_service import persist_notification, resolve_route, to_read
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


def test_native_route_and_persistence_round_trip() -> None:
    owner_id, _ = create_route_fixture()
    with SessionLocal() as session:
        route = resolve_route(
            session,
            principal(owner_id, "Healthchecks"),
            source_slug="healthchecks",
            channel_slug="goreecloud-healthchecks",
        )
        payload = NotificationCreate(
            source="healthchecks",
            channel="goreecloud-healthchecks",
            title="Backup completed",
            body="Kopia snapshot completed successfully.",
            severity="info",
        )
        notification = persist_notification(session, route, payload)
        result = to_read(notification, route)

        assert result.source == "healthchecks"
        assert result.channel == "goreecloud-healthchecks"
        assert result.title == "Backup completed"
        assert session.scalar(select(Notification).where(Notification.id == notification.id)) is not None


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
