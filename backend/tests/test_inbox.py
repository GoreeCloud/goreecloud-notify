from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.delivery_service import fanout_notification, get_inbox_state, list_inbox, list_inbox_after
from app.main import app
from app.models import (
    Channel,
    Delivery,
    Notification,
    ServiceIdentity,
    Source,
    Subscription,
    User,
    WebSession,
)
from app.notification_service import persist_notification, resolve_route
from app.routers import inbox as inbox_router
from app.routers.inbox import _inbox_event_stream, _stream_cursor
from app.schemas import NotificationCreate
from app.security import TokenPrincipal
from app.user_security import UserPrincipal, create_web_session, hash_password, utc_now


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


def principal_with_session(user_id: int) -> UserPrincipal:
    with SessionLocal() as session:
        user = session.get(User, user_id)
        assert user is not None
        record, _ = create_web_session(session, user)
        return UserPrincipal(
            user_id=user.id,
            session_id=record.id,
            username=user.username,
            display_name=user.display_name,
            is_admin=user.is_admin,
        )


class ConnectedRequest:
    async def is_disconnected(self) -> bool:
        return False


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
        state_response = client.get(
            "/api/v1/inbox/state",
            headers={"Authorization": "Bearer gcn_not_a_user_session"},
        )
        stream_response = client.get(
            "/api/v1/inbox/stream",
            headers={"Authorization": "Bearer gcn_not_a_user_session"},
        )
    assert response.status_code == 401
    assert state_response.status_code == 401
    assert stream_response.status_code == 401


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


def test_inbox_filters_read_acknowledgement_source_channel_severity_search_and_cursor() -> None:
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

        search_title = client.get("/api/v1/inbox?q=second")
        assert [item["id"] for item in search_title.json()] == [second_id]

        search_source_name = client.get("/api/v1/inbox?q=HEALTHCHECKS")
        assert [item["id"] for item in search_source_name.json()] == [second_id, first_id]

        search_composed = client.get("/api/v1/inbox?q=second&severity=critical&read=false")
        assert [item["id"] for item in search_composed.json()] == [second_id]

        literal_wildcard = client.get("/api/v1/inbox?q=%25")
        assert literal_wildcard.status_code == 200
        assert literal_wildcard.json() == []

        older = client.get(f"/api/v1/inbox?before_id={second_id}&limit=1")
        assert [item["id"] for item in older.json()] == [first_id]


def test_authoritative_inbox_state_is_user_scoped_and_tracks_mutations() -> None:
    identity_id, first_user_id, second_user_id, _ = seed_inbox_fixture()
    first_notification = publish(identity_id, title="State one")
    second_notification = publish(identity_id, title="State two")
    third_notification = publish(identity_id, title="State three")
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
        third_delivery = session.scalar(
            select(Delivery).where(
                Delivery.notification_id == third_notification,
                Delivery.user_id == first_user_id,
            )
        )
        second_user_latest = session.scalar(
            select(Delivery.id)
            .where(Delivery.user_id == second_user_id)
            .order_by(Delivery.id.desc())
            .limit(1)
        )
        assert first_delivery is not None and second_delivery is not None and third_delivery is not None
        assert second_user_latest is not None
        first_delivery.read_at = now
        first_delivery.acknowledged_at = now
        session.commit()
        expected_latest = third_delivery.id

        first_state = get_inbox_state(
            session,
            UserPrincipal(
                user_id=first_user_id,
                session_id=1,
                username="first",
                display_name="First User",
            ),
        )
        second_state = get_inbox_state(
            session,
            UserPrincipal(
                user_id=second_user_id,
                session_id=2,
                username="second",
                display_name="Second User",
            ),
        )

    assert first_state.latest_delivery_id == expected_latest
    assert first_state.total_count == 3
    assert first_state.unread_count == 2
    assert first_state.acknowledged_count == 1
    assert second_state.latest_delivery_id == second_user_latest
    assert second_state.total_count == 3
    assert second_state.unread_count == 3
    assert second_state.acknowledged_count == 0

    with TestClient(app) as client:
        login(client, "first", "first user password 123")
        response = client.get("/api/v1/inbox/state")
        assert response.status_code == 200
        assert response.json() == {
            "latest_delivery_id": expected_latest,
            "total_count": 3,
            "unread_count": 2,
            "acknowledged_count": 1,
        }


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


def test_realtime_cursor_query_is_user_scoped_and_oldest_first() -> None:
    identity_id, first_user_id, second_user_id, _ = seed_inbox_fixture()
    first_notification = publish(identity_id, title="First realtime")
    second_notification = publish(identity_id, title="Second realtime")

    with SessionLocal() as session:
        first_principal = UserPrincipal(
            user_id=first_user_id,
            session_id=1,
            username="first",
            display_name="First User",
        )
        second_principal = UserPrincipal(
            user_id=second_user_id,
            session_id=2,
            username="second",
            display_name="Second User",
        )
        first_items = list_inbox_after(session, first_principal, after_id=0)
        second_items = list_inbox_after(session, second_principal, after_id=0)

    assert [item.notification_id for item in first_items] == [first_notification, second_notification]
    assert [item.notification_id for item in second_items] == [first_notification, second_notification]
    assert [item.id for item in first_items] != [item.id for item in second_items]
    assert [item.id for item in first_items] == sorted(item.id for item in first_items)


def test_stream_cursor_prefers_valid_last_event_id_and_rejects_invalid_values() -> None:
    assert _stream_cursor(7, None) == 7
    assert _stream_cursor(7, "9") == 9
    assert _stream_cursor(None, "0") == 0

    for invalid in ("-1", "not-an-integer"):
        with pytest.raises(HTTPException) as error:
            _stream_cursor(7, invalid)
        assert error.value.status_code == 400


def test_sse_generator_replays_owned_delivery_after_cursor_and_stops_after_revocation() -> None:
    identity_id, first_user_id, _, _ = seed_inbox_fixture()
    notification_id = publish(identity_id, title="Realtime delivery")
    principal = principal_with_session(first_user_id)

    async def collect_initial_events() -> tuple[str, str]:
        generator = _inbox_event_stream(ConnectedRequest(), principal, 0)  # type: ignore[arg-type]
        ready = await anext(generator)
        inbox_event = await anext(generator)
        await generator.aclose()
        return ready, inbox_event

    ready, inbox_event = asyncio.run(collect_initial_events())
    assert "event: ready" in ready
    assert '"cursor":0' in ready
    assert '"total_count":1' in ready
    assert '"unread_count":1' in ready
    assert "event: inbox" in inbox_event
    data_line = next(line for line in inbox_event.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload["notification_id"] == notification_id
    assert payload["title"] == "Realtime delivery"

    with SessionLocal() as session:
        record = session.get(WebSession, principal.session_id)
        assert record is not None
        record.revoked_at = utc_now()
        session.commit()

    async def assert_revoked_stream_stops() -> None:
        generator = _inbox_event_stream(ConnectedRequest(), principal, 0)  # type: ignore[arg-type]
        with pytest.raises(StopAsyncIteration):
            await anext(generator)
        await generator.aclose()

    asyncio.run(assert_revoked_stream_stops())


def test_sse_generator_emits_state_change_without_new_delivery(monkeypatch: pytest.MonkeyPatch) -> None:
    identity_id, first_user_id, _, _ = seed_inbox_fixture()
    notification_id = publish(identity_id, title="State transition")
    principal = principal_with_session(first_user_id)
    monkeypatch.setattr(inbox_router, "STREAM_POLL_SECONDS", 0.0)
    monkeypatch.setattr(inbox_router, "STREAM_STATE_SECONDS", 0.0)

    with SessionLocal() as session:
        delivery = session.scalar(
            select(Delivery).where(
                Delivery.notification_id == notification_id,
                Delivery.user_id == first_user_id,
            )
        )
        assert delivery is not None
        delivery_id = delivery.id

    async def collect_state_change() -> tuple[str, str, str]:
        generator = _inbox_event_stream(ConnectedRequest(), principal, 0)  # type: ignore[arg-type]
        ready = await anext(generator)
        inbox_event = await anext(generator)

        with SessionLocal() as session:
            delivery = session.get(Delivery, delivery_id)
            assert delivery is not None
            delivery.read_at = utc_now()
            session.commit()

        state_event = await anext(generator)
        await generator.aclose()
        return ready, inbox_event, state_event

    ready, inbox_event, state_event = asyncio.run(collect_state_change())
    assert "event: ready" in ready
    assert '"unread_count":1' in ready
    assert "event: inbox" in inbox_event
    assert "event: state" in state_event
    assert '"total_count":1' in state_event
    assert '"unread_count":0' in state_event
