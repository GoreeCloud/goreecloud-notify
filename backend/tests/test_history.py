from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import AccessToken, Channel, ServiceIdentity, Source
from app.notification_service import (
    get_notification,
    list_notifications,
    persist_notification,
    resolve_route,
)
from app.schemas import NotificationCreate
from app.security import TokenPrincipal, token_digest


@pytest.fixture(autouse=True)
def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def principal(identity_id: int, name: str) -> TokenPrincipal:
    return TokenPrincipal(
        token_id=1,
        service_identity_id=identity_id,
        service_identity_name=name,
        scopes=frozenset({"notifications:read", "notifications:write"}),
    )


def create_fixture() -> tuple[int, int]:
    with SessionLocal() as session:
        owner = ServiceIdentity(name="Healthchecks")
        other = ServiceIdentity(name="Beszel")
        session.add_all([owner, other])
        session.flush()
        session.add_all(
            [
                Source(service_identity_id=owner.id, slug="healthchecks", name="Healthchecks"),
                Channel(slug="goreecloud-healthchecks", name="GoreeCloud Healthchecks"),
            ]
        )
        session.commit()
        return owner.id, other.id


def publish(session, identity_id: int, source_slug: str, title: str, severity: str = "normal"):
    route = resolve_route(
        session,
        principal(identity_id, source_slug.title()),
        source_slug=source_slug,
        channel_slug="goreecloud-healthchecks",
    )
    return persist_notification(
        session,
        route,
        NotificationCreate(
            source=source_slug,
            channel="goreecloud-healthchecks",
            title=title,
            body=title.lower(),
            severity=severity,
        ),
    )


def test_history_is_scoped_and_cross_identity_detail_is_hidden() -> None:
    owner_id, other_id = create_fixture()
    with SessionLocal() as session:
        publish(session, owner_id, "healthchecks", "Owned")
        session.add(Source(service_identity_id=other_id, slug="beszel", name="Beszel"))
        session.commit()
        other_notification = publish(session, other_id, "beszel", "Other", "warning")

        history = list_notifications(session, principal(owner_id, "Healthchecks"))
        assert [item.title for item in history] == ["Owned"]

        with pytest.raises(HTTPException) as exc_info:
            get_notification(session, principal(owner_id, "Healthchecks"), other_notification.id)
        assert exc_info.value.status_code == 404


def test_history_filters_and_cursor_are_deterministic() -> None:
    owner_id, _ = create_fixture()
    with SessionLocal() as session:
        first = publish(session, owner_id, "healthchecks", "First", "info")
        second = publish(session, owner_id, "healthchecks", "Second", "critical")

        critical = list_notifications(
            session,
            principal(owner_id, "Healthchecks"),
            severity="critical",
        )
        assert [item.id for item in critical] == [second.id]

        older = list_notifications(
            session,
            principal(owner_id, "Healthchecks"),
            before_id=second.id,
            limit=1,
        )
        assert [item.id for item in older] == [first.id]


def test_history_endpoint_requires_read_scope() -> None:
    owner_id, _ = create_fixture()
    raw_token = "gcn_test_write_only"
    with SessionLocal() as session:
        session.add(
            AccessToken(
                service_identity_id=owner_id,
                name="write-only",
                token_digest=token_digest(raw_token),
                scope="notifications:write",
            )
        )
        session.commit()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {raw_token}"},
        )

    assert response.status_code == 403


def test_history_endpoint_returns_only_owned_notifications() -> None:
    owner_id, other_id = create_fixture()
    raw_token = "gcn_test_reader"
    with SessionLocal() as session:
        publish(session, owner_id, "healthchecks", "Owned")
        session.add(Source(service_identity_id=other_id, slug="beszel", name="Beszel"))
        session.commit()
        publish(session, other_id, "beszel", "Not owned", "warning")
        session.add(
            AccessToken(
                service_identity_id=owner_id,
                name="reader",
                token_digest=token_digest(raw_token),
                scope="notifications:read",
            )
        )
        session.commit()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {raw_token}"},
        )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Owned"]
