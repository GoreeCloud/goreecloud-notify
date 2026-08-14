from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import User, WebSession
from app.user_security import CSRF_HEADER, hash_password, session_digest, utc_now


def create_user(*, username: str = "ladamian", password: str = "correct horse battery staple") -> int:
    with SessionLocal() as session:
        user = User(
            username=username,
            display_name="LaDamian",
            password_hash=hash_password(password),
        )
        session.add(user)
        session.commit()
        return user.id


def test_login_sets_http_only_session_cookie_and_me_resolves_user() -> None:
    user_id = create_user()
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/session",
            json={"username": "LADAMIAN", "password": "correct horse battery staple"},
        )
        assert login.status_code == 200
        assert login.json()["id"] == user_id
        cookie = login.headers["set-cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=strict" in cookie
        assert settings.session_cookie_name in client.cookies
        csrf_token = login.headers[CSRF_HEADER]
        assert csrf_token

        csrf = client.get("/api/v1/csrf")
        assert csrf.status_code == 200
        assert csrf.json()["csrf_token"] == csrf_token

        me = client.get("/api/v1/me")
        assert me.status_code == 200
        assert me.json()["username"] == "ladamian"

    with SessionLocal() as session:
        record = session.scalar(select(WebSession))
        assert record is not None
        raw_cookie = login.cookies.get(settings.session_cookie_name)
        assert raw_cookie is not None
        assert record.session_digest == session_digest(raw_cookie)
        assert raw_cookie not in record.session_digest
        assert record.csrf_token == login.headers[CSRF_HEADER]


def test_invalid_credentials_are_generic_and_do_not_create_session() -> None:
    create_user()
    with TestClient(app) as client:
        wrong_password = client.post(
            "/api/v1/session",
            json={"username": "ladamian", "password": "wrong password"},
        )
        missing_user = client.post(
            "/api/v1/session",
            json={"username": "missing", "password": "wrong password"},
        )

    assert wrong_password.status_code == 401
    assert missing_user.status_code == 401
    assert wrong_password.json()["detail"] == missing_user.json()["detail"] == "invalid credentials"
    with SessionLocal() as session:
        assert session.scalar(select(WebSession)) is None


def test_logout_revokes_server_session_and_clears_cookie() -> None:
    create_user()
    with TestClient(app) as client:
        assert client.post(
            "/api/v1/session",
            json={"username": "ladamian", "password": "correct horse battery staple"},
        ).status_code == 200
        csrf_token = client.get("/api/v1/csrf").json()["csrf_token"]
        assert client.delete("/api/v1/session").status_code == 403
        assert client.get("/api/v1/me").status_code == 200
        logout = client.delete("/api/v1/session", headers={CSRF_HEADER: csrf_token})
        assert logout.status_code == 204
        assert settings.session_cookie_name not in client.cookies
        assert client.get("/api/v1/me").status_code == 401

    with SessionLocal() as session:
        record = session.scalar(select(WebSession))
        assert record is not None
        assert record.revoked_at is not None


def test_idle_session_is_rejected_and_revoked() -> None:
    user_id = create_user()
    raw_token = "gcs_expired_test"
    now = utc_now()
    with SessionLocal() as session:
        session.add(
            WebSession(
                user_id=user_id,
                session_digest=session_digest(raw_token),
                csrf_token="idle-session-csrf",
                created_at=now - timedelta(hours=2),
                last_seen_at=now - timedelta(minutes=settings.session_idle_minutes + 1),
                expires_at=now + timedelta(hours=1),
            )
        )
        session.commit()

    with TestClient(app) as client:
        client.cookies.set(settings.session_cookie_name, raw_token)
        response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "user session expired"
    with SessionLocal() as session:
        record = session.scalar(select(WebSession))
        assert record is not None
        assert record.revoked_at is not None


def test_inactive_user_cannot_login() -> None:
    user_id = create_user()
    with SessionLocal() as session:
        user = session.get(User, user_id)
        assert user is not None
        user.is_active = False
        session.commit()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/session",
            json={"username": "ladamian", "password": "correct horse battery staple"},
        )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid credentials"


def test_deactivated_user_existing_session_is_rejected_and_persistently_revoked() -> None:
    user_id = create_user()
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/session",
            json={"username": "ladamian", "password": "correct horse battery staple"},
        )
        assert login.status_code == 200
        raw_token = client.cookies.get(settings.session_cookie_name)
        assert raw_token is not None

        with SessionLocal() as session:
            user = session.get(User, user_id)
            assert user is not None
            user.is_active = False
            session.commit()

        first = client.get("/api/v1/me")
        second = client.get("/api/v1/me")

    assert first.status_code == 401
    assert first.json()["detail"] == "user session unavailable"
    assert second.status_code == 401
    assert second.json()["detail"] == "invalid user session"

    with SessionLocal() as session:
        record = session.scalar(
            select(WebSession).where(WebSession.session_digest == session_digest(raw_token))
        )
        assert record is not None
        assert record.user_id == user_id
        assert record.revoked_at is not None


def test_absolute_expiration_is_enforced() -> None:
    user_id = create_user()
    raw_token = "gcs_absolute_expired_test"
    now = utc_now()
    with SessionLocal() as session:
        session.add(
            WebSession(
                user_id=user_id,
                session_digest=session_digest(raw_token),
                csrf_token="absolute-session-csrf",
                created_at=now - timedelta(days=1),
                last_seen_at=now,
                expires_at=now - timedelta(seconds=1),
            )
        )
        session.commit()

    with TestClient(app) as client:
        client.cookies.set(settings.session_cookie_name, raw_token)
        response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "user session expired"


def test_each_successful_login_issues_a_new_opaque_session() -> None:
    create_user()
    with TestClient(app) as first_client, TestClient(app) as second_client:
        first = first_client.post(
            "/api/v1/session",
            json={"username": "ladamian", "password": "correct horse battery staple"},
        )
        second = second_client.post(
            "/api/v1/session",
            json={"username": "ladamian", "password": "correct horse battery staple"},
        )
        assert first.status_code == second.status_code == 200
        assert first_client.cookies.get(settings.session_cookie_name) != second_client.cookies.get(
            settings.session_cookie_name
        )

    with SessionLocal() as session:
        assert len(session.scalars(select(WebSession)).all()) == 2
