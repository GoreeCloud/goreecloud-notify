from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import (
    AccessToken,
    Channel,
    Delivery,
    Notification,
    ServiceIdentity,
    Source,
    Subscription,
    User,
)
from app.security import token_digest


@pytest.fixture(autouse=True)
def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def setup_producer(*, scope: str = "notifications:write", extra_source: bool = False) -> str:
    raw_token = "gcn_compat_test"
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Healthchecks")
        session.add(identity)
        session.flush()
        session.add(Source(service_identity_id=identity.id, slug="healthchecks", name="Healthchecks"))
        if extra_source:
            session.add(Source(service_identity_id=identity.id, slug="secondary", name="Secondary"))
        session.add(Channel(slug="goreecloud-healthchecks", name="GoreeCloud Healthchecks"))
        session.add(
            AccessToken(
                service_identity_id=identity.id,
                name="compat",
                token_digest=token_digest(raw_token),
                scope=scope,
            )
        )
        session.commit()
    return raw_token


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_simple_post_body_persists_to_topic_channel() -> None:
    token = setup_producer()
    with TestClient(app) as client:
        response = client.post(
            "/goreecloud-healthchecks",
            content="Backup successful",
            headers=auth(token),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["event"] == "message"
    assert payload["topic"] == "goreecloud-healthchecks"
    assert payload["message"] == "Backup successful"
    assert payload["title"] == "goreecloud-healthchecks"
    assert payload["priority"] == 3

    with SessionLocal() as session:
        notification = session.scalar(select(Notification))
        assert notification is not None
        assert notification.severity == "normal"


def test_put_title_and_priority_headers_translate_safely() -> None:
    token = setup_producer()
    headers = auth(token) | {"X-Title": "Service degraded", "X-Priority": "5"}
    with TestClient(app) as client:
        response = client.put(
            "/goreecloud-healthchecks",
            content="Investigate the source system.",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json()["title"] == "Service degraded"
    assert response.json()["priority"] == 5
    with SessionLocal() as session:
        notification = session.scalar(select(Notification))
        assert notification is not None
        assert notification.severity == "critical"


def test_query_message_title_and_priority_are_supported() -> None:
    token = setup_producer()
    with TestClient(app) as client:
        response = client.post(
            "/goreecloud-healthchecks?message=Recovered&title=Healthchecks&priority=low",
            headers=auth(token),
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Recovered"
    assert response.json()["title"] == "Healthchecks"
    assert response.json()["priority"] == 2


def test_min_priority_preserves_ntfy_priority_one() -> None:
    token = setup_producer()
    with TestClient(app) as client:
        response = client.post(
            "/goreecloud-healthchecks",
            content="Low urgency",
            headers=auth(token) | {"X-Priority": "min"},
        )

    assert response.status_code == 200
    assert response.json()["priority"] == 1
    with SessionLocal() as session:
        notification = session.scalar(select(Notification))
        assert notification is not None
        assert notification.severity == "info"


def test_compatibility_route_requires_scoped_bearer_authentication() -> None:
    setup_producer()
    with TestClient(app) as client:
        response = client.post("/goreecloud-healthchecks", content="Denied")
    assert response.status_code == 401


def test_compatibility_route_requires_write_scope() -> None:
    token = setup_producer(scope="notifications:read")
    with TestClient(app) as client:
        response = client.post(
            "/goreecloud-healthchecks",
            content="Denied",
            headers=auth(token),
        )
    assert response.status_code == 403


def test_unsupported_ntfy_features_are_rejected_not_silently_dropped() -> None:
    token = setup_producer()
    with TestClient(app) as client:
        response = client.post(
            "/goreecloud-healthchecks",
            content="Tagged",
            headers=auth(token) | {"X-Tags": "warning"},
        )
    assert response.status_code == 422
    assert "unsupported ntfy compatibility option" in response.json()["detail"]


def test_compatibility_message_limit_matches_current_ntfy_policy() -> None:
    token = setup_producer()
    with TestClient(app) as client:
        response = client.post(
            "/goreecloud-healthchecks",
            content="x" * 4097,
            headers=auth(token),
        )
    assert response.status_code == 413


def test_ambiguous_multi_source_identity_requires_native_api() -> None:
    token = setup_producer(extra_source=True)
    with SessionLocal() as session:
        source = session.scalar(select(Source).where(Source.slug == "healthchecks"))
        assert source is not None
        source.slug = "primary"
        session.commit()

    with TestClient(app) as client:
        response = client.post(
            "/goreecloud-healthchecks",
            content="Ambiguous",
            headers=auth(token),
        )
    assert response.status_code == 409


def test_compatibility_publish_uses_the_same_subscription_fanout() -> None:
    token = setup_producer()
    with SessionLocal() as session:
        channel = session.scalar(select(Channel).where(Channel.slug == "goreecloud-healthchecks"))
        assert channel is not None
        user = User(username="compat-reader", display_name="Compat Reader")
        session.add(user)
        session.flush()
        session.add(Subscription(user_id=user.id, channel_id=channel.id, enabled=True))
        session.commit()
        user_id = user.id

    with TestClient(app) as client:
        response = client.post(
            "/goreecloud-healthchecks",
            content="Compatibility fanout",
            headers=auth(token),
        )
    assert response.status_code == 200

    with SessionLocal() as session:
        notification = session.scalar(select(Notification))
        assert notification is not None
        delivery = session.scalar(
            select(Delivery).where(
                Delivery.notification_id == notification.id,
                Delivery.user_id == user_id,
            )
        )
        assert delivery is not None
