from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.login_security as login_security
from app.database import SessionLocal
from app.main import app
from app.models import LoginRateBucket, LoginSecurityEvent, User
from app.user_security import hash_password

UTC = timezone.utc
PASSWORD = "correct horse battery staple"


def rate_settings(**overrides):
    values = {
        "trusted_proxy_cidrs": (),
        "login_rate_window_minutes": 5,
        "login_rate_account_attempts": 3,
        "login_rate_source_attempts": 4,
        "login_rate_cooldown_minutes": 5,
        "login_rate_state_ttl_hours": 24,
        "login_security_event_retention_days": 30,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def seed_user(username: str = "rateuser") -> None:
    with SessionLocal() as session:
        session.add(
            User(
                username=username,
                display_name="Rate User",
                password_hash=hash_password(PASSWORD),
            )
        )
        session.commit()


def request_with_client(client_host: str, forwarded_for: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode("ascii")))
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/api/v1/session",
            "raw_path": b"/api/v1/session",
            "query_string": b"",
            "headers": headers,
            "client": (client_host, 12345),
            "server": ("notify.goreecloud.com", 443),
        }
    )


def test_repeated_failures_return_429_with_retry_after(monkeypatch) -> None:
    monkeypatch.setattr(login_security, "settings", rate_settings())
    seed_user()

    with TestClient(app) as client:
        for _ in range(2):
            response = client.post(
                "/api/v1/session",
                json={"username": "rateuser", "password": "wrong password"},
            )
            assert response.status_code == 401
            assert response.json() == {"detail": "invalid credentials"}

        limited = client.post(
            "/api/v1/session",
            json={"username": "rateuser", "password": "wrong password"},
        )
        assert limited.status_code == 429
        assert limited.json() == {"detail": "login temporarily unavailable"}
        assert 1 <= int(limited.headers["Retry-After"]) <= 300

        still_limited = client.post(
            "/api/v1/session",
            json={"username": "rateuser", "password": PASSWORD},
        )
        assert still_limited.status_code == 429


def test_successful_login_after_cooldown_and_window_reset(monkeypatch) -> None:
    monkeypatch.setattr(login_security, "settings", rate_settings())
    seed_user()

    with TestClient(app) as client:
        for _ in range(3):
            response = client.post(
                "/api/v1/session",
                json={"username": "rateuser", "password": "wrong password"},
            )
        assert response.status_code == 429

        past = datetime.now(UTC) - timedelta(minutes=10)
        with SessionLocal() as session:
            buckets = session.scalars(select(LoginRateBucket)).all()
            assert buckets
            for bucket in buckets:
                bucket.window_started_at = past
                bucket.blocked_until = past
                bucket.updated_at = past
            session.commit()

        success = client.post(
            "/api/v1/session",
            json={"username": "rateuser", "password": PASSWORD},
        )

    assert success.status_code == 200
    with SessionLocal() as session:
        source_account = session.scalar(
            select(LoginRateBucket).where(LoginRateBucket.scope == "source_account")
        )
        assert source_account is not None
        assert source_account.failure_count == 0
        assert source_account.blocked_until is None
        outcomes = session.scalars(
            select(LoginSecurityEvent.outcome).order_by(LoginSecurityEvent.id)
        ).all()
        assert "success" in outcomes


def test_username_normalization_shares_one_source_account_bucket(monkeypatch) -> None:
    monkeypatch.setattr(login_security, "settings", rate_settings())
    seed_user()

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/session",
            json={"username": "RateUser", "password": "wrong password"},
        )
        second = client.post(
            "/api/v1/session",
            json={"username": " rateuser ", "password": "wrong password"},
        )
        third = client.post(
            "/api/v1/session",
            json={"username": "RATEUSER", "password": "wrong password"},
        )

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    with SessionLocal() as session:
        buckets = session.scalars(
            select(LoginRateBucket).where(LoginRateBucket.scope == "source_account")
        ).all()
        assert len(buckets) == 1


def test_existing_and_unknown_accounts_share_generic_failure_shape(monkeypatch) -> None:
    monkeypatch.setattr(login_security, "settings", rate_settings())
    seed_user()

    with TestClient(app) as client:
        existing = client.post(
            "/api/v1/session",
            json={"username": "rateuser", "password": "wrong password"},
        )
        unknown = client.post(
            "/api/v1/session",
            json={"username": "does-not-exist", "password": "wrong password"},
        )

    assert existing.status_code == unknown.status_code == 401
    assert existing.json() == unknown.json() == {"detail": "invalid credentials"}


def test_source_wide_limit_cannot_be_bypassed_with_many_usernames(monkeypatch) -> None:
    monkeypatch.setattr(login_security, "settings", rate_settings())

    with TestClient(app) as client:
        statuses = []
        for index in range(4):
            response = client.post(
                "/api/v1/session",
                json={
                    "username": f"unknown-{index}",
                    "password": "wrong password",
                },
            )
            statuses.append(response.status_code)

    assert statuses == [401, 401, 401, 429]


def test_untrusted_peer_cannot_spoof_forwarded_for(monkeypatch) -> None:
    monkeypatch.setattr(login_security, "settings", rate_settings(trusted_proxy_cidrs=()))
    request = request_with_client("203.0.113.10", "198.51.100.77")

    assert login_security.resolve_client_signal(request) == "203.0.113.10"


def test_trusted_proxy_chain_uses_rightmost_untrusted_client(monkeypatch) -> None:
    monkeypatch.setattr(
        login_security,
        "settings",
        rate_settings(trusted_proxy_cidrs=("10.0.0.0/8",)),
    )
    request = request_with_client(
        "10.0.0.5",
        "198.51.100.77, 10.0.0.4",
    )

    assert login_security.resolve_client_signal(request) == "198.51.100.77"


def test_malformed_forwarded_chain_falls_back_to_trusted_peer(monkeypatch) -> None:
    monkeypatch.setattr(
        login_security,
        "settings",
        rate_settings(trusted_proxy_cidrs=("10.0.0.0/8",)),
    )
    request = request_with_client("10.0.0.5", "not-an-ip")

    assert login_security.resolve_client_signal(request) == "10.0.0.5"


def test_security_events_store_only_digested_client_and_account_signals(monkeypatch) -> None:
    monkeypatch.setattr(login_security, "settings", rate_settings())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/session",
            json={"username": "SensitiveName", "password": "super secret wrong password"},
        )
    assert response.status_code == 401

    with SessionLocal() as session:
        event = session.scalar(select(LoginSecurityEvent))
        assert event is not None
        assert event.outcome == "failure"
        assert len(event.client_digest) == 64
        assert len(event.account_digest) == 64
        assert event.account_digest != "sensitivename"
        assert not hasattr(event, "password")
        assert not hasattr(event, "username")
        assert not hasattr(event, "client_ip")


def test_stale_rate_state_and_security_events_are_cleaned(monkeypatch) -> None:
    monkeypatch.setattr(login_security, "settings", rate_settings())
    old = datetime.now(UTC) - timedelta(days=40)
    with SessionLocal() as session:
        session.add(
            LoginRateBucket(
                key_digest="a" * 64,
                scope="source",
                window_started_at=old,
                failure_count=1,
                updated_at=old,
            )
        )
        session.add(
            LoginSecurityEvent(
                outcome="failure",
                client_digest="b" * 64,
                account_digest="c" * 64,
                created_at=old,
            )
        )
        session.commit()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/session",
            json={"username": "cleanup-test", "password": "wrong password"},
        )
    assert response.status_code == 401

    with SessionLocal() as session:
        assert session.scalar(
            select(LoginRateBucket).where(LoginRateBucket.key_digest == "a" * 64)
        ) is None
        assert session.scalar(
            select(LoginSecurityEvent).where(LoginSecurityEvent.client_digest == "b" * 64)
        ) is None
