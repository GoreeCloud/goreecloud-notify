from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.security as security
from app.database import SessionLocal
from app.main import app
from app.models import User


def test_user_provisioning_requires_configured_admin_token(monkeypatch) -> None:
    monkeypatch.setattr(security, "settings", type("TestSettings", (), {"admin_token": None})())
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/users",
            json={
                "username": "ladamian",
                "display_name": "LaDamian",
                "password": "correct horse battery staple",
            },
        )
    assert response.status_code == 503


def test_admin_can_provision_user_without_storing_plaintext(monkeypatch) -> None:
    monkeypatch.setattr(security, "settings", type("TestSettings", (), {"admin_token": "admin-test-token"})())
    password = "correct horse battery staple"
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/users",
            headers={"X-GoreeCloud-Admin-Token": "admin-test-token"},
            json={
                "username": "LaDamian",
                "display_name": "LaDamian Goree",
                "password": password,
            },
        )

    assert response.status_code == 201
    assert response.json()["username"] == "ladamian"
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == "ladamian"))
        assert user is not None
        assert user.password_hash is not None
        assert user.password_hash.startswith("$argon2id$")
        assert password not in user.password_hash
