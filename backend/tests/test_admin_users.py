from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.security as security
from app.database import SessionLocal
from app.main import app
from app.models import AccessToken, AdminAuditEvent, ServiceIdentity, User
from app.security import token_digest

BOOTSTRAP = {"X-GoreeCloud-Admin-Token": "admin-test-token"}
ADMIN_PASSWORD = "correct horse battery staple"


def configure_bootstrap(monkeypatch, token: str | None = "admin-test-token") -> None:
    monkeypatch.setattr(security, "settings", type("TestSettings", (), {"admin_token": token})())


def bootstrap_admin(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/bootstrap/administrator",
        headers=BOOTSTRAP,
        json={
            "username": "ladamian",
            "display_name": "LaDamian Goree",
            "password": ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 201
    return response.json()


def login_admin(client: TestClient) -> str:
    response = client.post(
        "/api/v1/session",
        json={"username": "ladamian", "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["is_admin"] is True
    return response.headers["X-CSRF-Token"]


def test_bootstrap_requires_configured_admin_token(monkeypatch) -> None:
    configure_bootstrap(monkeypatch, None)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/bootstrap/administrator",
            json={
                "username": "ladamian",
                "display_name": "LaDamian",
                "password": ADMIN_PASSWORD,
            },
        )
    assert response.status_code == 503


def test_bootstrap_creates_first_admin_without_storing_plaintext(monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    with TestClient(app) as client:
        payload = bootstrap_admin(client)

    assert payload["username"] == "ladamian"
    assert payload["is_admin"] is True
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == "ladamian"))
        assert user is not None
        assert user.is_admin is True
        assert user.password_hash is not None
        assert user.password_hash.startswith("$argon2id$")
        assert ADMIN_PASSWORD not in user.password_hash
        audit = session.scalar(select(AdminAuditEvent))
        assert audit is not None
        assert audit.actor_user_id is None
        assert audit.mechanism == "bootstrap"
        assert audit.action == "administrator.bootstrap"
        assert audit.target_id == user.id


def test_bootstrap_is_disabled_after_first_admin_exists(monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    with TestClient(app) as client:
        bootstrap_admin(client)
        response = client.post(
            "/api/v1/bootstrap/administrator",
            headers=BOOTSTRAP,
            json={
                "username": "second-admin",
                "display_name": "Second Admin",
                "password": "another correct horse battery staple",
            },
        )
    assert response.status_code == 409


def test_bootstrap_stays_disabled_after_admin_privilege_is_removed(monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    with TestClient(app) as client:
        bootstrap_admin(client)

    with SessionLocal() as session:
        admin = session.scalar(select(User).where(User.username == "ladamian"))
        assert admin is not None
        admin.is_admin = False
        session.commit()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/bootstrap/administrator",
            headers=BOOTSTRAP,
            json={
                "username": "replacement-admin",
                "display_name": "Replacement Admin",
                "password": "another correct horse battery staple",
            },
        )
    assert response.status_code == 409


def test_static_bootstrap_header_cannot_call_routine_admin_api(monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    with TestClient(app) as client:
        bootstrap_admin(client)
        response = client.post(
            "/api/v1/users",
            headers=BOOTSTRAP,
            json={
                "username": "ordinary",
                "display_name": "Ordinary User",
                "password": "another correct horse battery staple",
            },
        )
    assert response.status_code == 401


def test_producer_bearer_token_cannot_call_routine_admin_api(monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    raw_token = "gcn_admin_boundary"
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Admin Boundary Producer")
        session.add(identity)
        session.flush()
        session.add(
            AccessToken(
                service_identity_id=identity.id,
                name="admin-boundary",
                token_digest=token_digest(raw_token),
                scope="*",
            )
        )
        session.commit()

    with TestClient(app) as client:
        bootstrap_admin(client)
        response = client.get(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
    assert response.status_code == 401


def test_admin_mutation_requires_csrf_and_records_actor(monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    with TestClient(app) as client:
        bootstrap_admin(client)
        csrf = login_admin(client)

        missing_csrf = client.post(
            "/api/v1/users",
            json={
                "username": "ordinary",
                "display_name": "Ordinary User",
                "password": "another correct horse battery staple",
            },
        )
        assert missing_csrf.status_code == 403

        created = client.post(
            "/api/v1/users",
            headers={"X-CSRF-Token": csrf},
            json={
                "username": "ordinary",
                "display_name": "Ordinary User",
                "password": "another correct horse battery staple",
            },
        )

    assert created.status_code == 201
    assert created.json()["is_admin"] is False
    with SessionLocal() as session:
        admin = session.scalar(select(User).where(User.username == "ladamian"))
        user = session.scalar(select(User).where(User.username == "ordinary"))
        assert admin is not None and user is not None
        audit = session.scalar(
            select(AdminAuditEvent).where(AdminAuditEvent.action == "user.create")
        )
        assert audit is not None
        assert audit.actor_user_id == admin.id
        assert audit.mechanism == "session"
        assert audit.target_id == user.id


def test_ordinary_user_is_denied_administrator_access(monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    with TestClient(app) as client:
        bootstrap_admin(client)
        csrf = login_admin(client)
        created = client.post(
            "/api/v1/users",
            headers={"X-CSRF-Token": csrf},
            json={
                "username": "ordinary",
                "display_name": "Ordinary User",
                "password": "another correct horse battery staple",
            },
        )
        assert created.status_code == 201

        client.delete("/api/v1/session", headers={"X-CSRF-Token": csrf})
        ordinary_login = client.post(
            "/api/v1/session",
            json={"username": "ordinary", "password": "another correct horse battery staple"},
        )
        assert ordinary_login.status_code == 200
        assert ordinary_login.json()["is_admin"] is False
        ordinary_csrf = ordinary_login.headers["X-CSRF-Token"]
        denied = client.post(
            "/api/v1/channels",
            headers={"X-CSRF-Token": ordinary_csrf},
            json={"slug": "denied", "name": "Denied"},
        )
    assert denied.status_code == 403


def test_existing_admin_session_loses_privilege_immediately(monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    with TestClient(app) as client:
        bootstrap_admin(client)
        login_admin(client)

        allowed = client.get("/api/v1/channels")
        assert allowed.status_code == 200

        with SessionLocal() as session:
            admin = session.scalar(select(User).where(User.username == "ladamian"))
            assert admin is not None
            admin.is_admin = False
            session.commit()

        denied = client.get("/api/v1/channels")

    assert denied.status_code == 403


def test_existing_admin_session_is_rejected_after_deactivation(monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    with TestClient(app) as client:
        bootstrap_admin(client)
        login_admin(client)

        with SessionLocal() as session:
            admin = session.scalar(select(User).where(User.username == "ladamian"))
            assert admin is not None
            admin.is_active = False
            session.commit()

        denied = client.get("/api/v1/channels")

    assert denied.status_code == 401
