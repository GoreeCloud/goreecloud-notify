from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.security as security
from app.database import SessionLocal
from app.main import app
from app.models import AccessToken, AdminAuditEvent, ServiceIdentity, User, WebSession
from app.security import token_digest

BOOTSTRAP = {"X-GoreeCloud-Admin-Token": "admin-test-token"}
ADMIN_PASSWORD = "correct horse battery staple"
OLD_PASSWORD = "target correct horse battery"
NEW_PASSWORD = "replacement correct horse battery"


def configure_bootstrap(monkeypatch) -> None:
    monkeypatch.setattr(
        security,
        "settings",
        type("TestSettings", (), {"admin_token": "admin-test-token"})(),
    )


def establish_admin(client: TestClient, monkeypatch) -> tuple[int, str]:
    configure_bootstrap(monkeypatch)
    created = client.post(
        "/api/v1/bootstrap/administrator",
        headers=BOOTSTRAP,
        json={
            "username": "recovery-admin",
            "display_name": "Recovery Admin",
            "password": ADMIN_PASSWORD,
        },
    )
    assert created.status_code == 201
    logged_in = client.post(
        "/api/v1/session",
        json={"username": "recovery-admin", "password": ADMIN_PASSWORD},
    )
    assert logged_in.status_code == 200
    return created.json()["id"], logged_in.headers["X-CSRF-Token"]


def create_target(client: TestClient, csrf: str, *, username: str = "target-user") -> int:
    response = client.post(
        "/api/v1/users",
        headers={"X-CSRF-Token": csrf},
        json={
            "username": username,
            "display_name": "Target User",
            "password": OLD_PASSWORD,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_admin_password_reset_revokes_all_sessions_and_replaces_password(monkeypatch) -> None:
    with (
        TestClient(app) as admin_client,
        TestClient(app) as first_user_client,
        TestClient(app) as second_user_client,
    ):
        admin_id, csrf = establish_admin(admin_client, monkeypatch)
        target_id = create_target(admin_client, csrf)

        first_login = first_user_client.post(
            "/api/v1/session",
            json={"username": "target-user", "password": OLD_PASSWORD},
        )
        second_login = second_user_client.post(
            "/api/v1/session",
            json={"username": "target-user", "password": OLD_PASSWORD},
        )
        assert first_login.status_code == second_login.status_code == 200
        assert first_user_client.get("/api/v1/me").status_code == 200
        assert second_user_client.get("/api/v1/me").status_code == 200

        reset = admin_client.post(
            f"/api/v1/users/{target_id}/password-reset",
            headers={"X-CSRF-Token": csrf},
            json={"password": NEW_PASSWORD},
        )
        assert reset.status_code == 204

        assert first_user_client.get("/api/v1/me").status_code == 401
        assert second_user_client.get("/api/v1/me").status_code == 401

        with SessionLocal() as session:
            target_sessions = session.scalars(
                select(WebSession).where(WebSession.user_id == target_id)
            ).all()
            assert len(target_sessions) == 2
            assert all(record.revoked_at is not None for record in target_sessions)
            audit = session.scalar(
                select(AdminAuditEvent).where(AdminAuditEvent.action == "user.password_reset")
            )
            assert audit is not None
            assert audit.actor_user_id == admin_id
            assert audit.target_type == "user"
            assert audit.target_id == target_id
            assert not hasattr(audit, "password")

        old_password = first_user_client.post(
            "/api/v1/session",
            json={"username": "target-user", "password": OLD_PASSWORD},
        )
        new_password = first_user_client.post(
            "/api/v1/session",
            json={"username": "target-user", "password": NEW_PASSWORD},
        )

    assert old_password.status_code == 401
    assert old_password.json() == {"detail": "invalid credentials"}
    assert new_password.status_code == 200


def test_password_reset_does_not_reactivate_inactive_user(monkeypatch) -> None:
    with TestClient(app) as admin_client:
        _admin_id, csrf = establish_admin(admin_client, monkeypatch)
        target_id = create_target(admin_client, csrf, username="inactive-target")

        with SessionLocal() as session:
            target = session.get(User, target_id)
            assert target is not None
            target.is_active = False
            session.commit()

        reset = admin_client.post(
            f"/api/v1/users/{target_id}/password-reset",
            headers={"X-CSRF-Token": csrf},
            json={"password": NEW_PASSWORD},
        )
        assert reset.status_code == 204

        with SessionLocal() as session:
            target = session.get(User, target_id)
            assert target is not None
            assert target.is_active is False

        login = admin_client.post(
            "/api/v1/session",
            json={"username": "inactive-target", "password": NEW_PASSWORD},
        )

    assert login.status_code == 401
    assert login.json() == {"detail": "invalid credentials"}


def test_password_reset_requires_existing_target(monkeypatch) -> None:
    with TestClient(app) as client:
        _admin_id, csrf = establish_admin(client, monkeypatch)
        response = client.post(
            "/api/v1/users/999999/password-reset",
            headers={"X-CSRF-Token": csrf},
            json={"password": NEW_PASSWORD},
        )

    assert response.status_code == 404


def test_producer_token_cannot_authorize_password_reset(monkeypatch) -> None:
    configure_bootstrap(monkeypatch)
    raw_token = "gcn_password_reset_boundary"
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Password Reset Producer")
        user = User(
            username="producer-target",
            display_name="Producer Target",
            password_hash="not-used",
        )
        session.add_all([identity, user])
        session.flush()
        session.add(
            AccessToken(
                service_identity_id=identity.id,
                name="reset-boundary",
                token_digest=token_digest(raw_token),
                scope="*",
            )
        )
        session.commit()
        target_id = user.id

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/users/{target_id}/password-reset",
            headers={"Authorization": f"Bearer {raw_token}"},
            json={"password": NEW_PASSWORD},
        )

    assert response.status_code == 401


def test_admin_self_reset_revokes_current_admin_session(monkeypatch) -> None:
    with TestClient(app) as client:
        admin_id, csrf = establish_admin(client, monkeypatch)
        reset = client.post(
            f"/api/v1/users/{admin_id}/password-reset",
            headers={"X-CSRF-Token": csrf},
            json={"password": NEW_PASSWORD},
        )
        assert reset.status_code == 204
        assert client.get("/api/v1/me").status_code == 401

        old_password = client.post(
            "/api/v1/session",
            json={"username": "recovery-admin", "password": ADMIN_PASSWORD},
        )
        new_password = client.post(
            "/api/v1/session",
            json={"username": "recovery-admin", "password": NEW_PASSWORD},
        )

    assert old_password.status_code == 401
    assert new_password.status_code == 200
    assert new_password.json()["is_admin"] is True
