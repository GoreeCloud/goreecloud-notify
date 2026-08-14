from __future__ import annotations

from fastapi.testclient import TestClient

import app.security as security
from app.main import app

BOOTSTRAP = {"X-GoreeCloud-Admin-Token": "admin-test-token"}
ADMIN_PASSWORD = "correct horse battery staple"


def establish_admin(client: TestClient, monkeypatch) -> str:
    monkeypatch.setattr(
        security,
        "settings",
        type("TestSettings", (), {"admin_token": "admin-test-token"})(),
    )
    created = client.post(
        "/api/v1/bootstrap/administrator",
        headers=BOOTSTRAP,
        json={
            "username": "normalization-admin",
            "display_name": "Normalization Admin",
            "password": ADMIN_PASSWORD,
        },
    )
    assert created.status_code == 201
    logged_in = client.post(
        "/api/v1/session",
        json={"username": "normalization-admin", "password": ADMIN_PASSWORD},
    )
    assert logged_in.status_code == 200
    return logged_in.headers["X-CSRF-Token"]


def test_required_admin_names_reject_blank_and_trim_surrounding_whitespace(monkeypatch) -> None:
    with TestClient(app) as client:
        csrf = establish_admin(client, monkeypatch)
        headers = {"X-CSRF-Token": csrf}

        blank_user = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "username": "blank-user",
                "display_name": "   ",
                "password": "another correct horse battery staple",
            },
        )
        assert blank_user.status_code == 422

        user = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "username": "trimmed-user",
                "display_name": "  Trimmed User  ",
                "password": "another correct horse battery staple",
            },
        )
        assert user.status_code == 201
        assert user.json()["display_name"] == "Trimmed User"

        blank_identity = client.post(
            "/api/v1/service-identities",
            headers=headers,
            json={"name": "   "},
        )
        assert blank_identity.status_code == 422

        identity = client.post(
            "/api/v1/service-identities",
            headers=headers,
            json={"name": "  Trimmed Identity  "},
        )
        assert identity.status_code == 201
        assert identity.json()["name"] == "Trimmed Identity"
        identity_id = identity.json()["id"]

        blank_token = client.post(
            "/api/v1/tokens",
            headers=headers,
            json={
                "service_identity_id": identity_id,
                "name": "   ",
                "scopes": ["notifications:write"],
            },
        )
        assert blank_token.status_code == 422

        token = client.post(
            "/api/v1/tokens",
            headers=headers,
            json={
                "service_identity_id": identity_id,
                "name": "  Trimmed Token  ",
                "scopes": ["notifications:write"],
            },
        )
        assert token.status_code == 201
        assert token.json()["name"] == "Trimmed Token"

        blank_source = client.post(
            "/api/v1/sources",
            headers=headers,
            json={
                "service_identity_id": identity_id,
                "slug": "normalize",
                "name": "   ",
            },
        )
        assert blank_source.status_code == 422

        source = client.post(
            "/api/v1/sources",
            headers=headers,
            json={
                "service_identity_id": identity_id,
                "slug": "normalize",
                "name": "  Normalized Source  ",
            },
        )
        assert source.status_code == 201
        assert source.json()["name"] == "Normalized Source"

        blank_channel = client.post(
            "/api/v1/channels",
            headers=headers,
            json={"slug": "goreecloud-normalize", "name": "   "},
        )
        assert blank_channel.status_code == 422

        channel = client.post(
            "/api/v1/channels",
            headers=headers,
            json={"slug": "goreecloud-normalize", "name": "  Normalized Channel  "},
        )
        assert channel.status_code == 201
        assert channel.json()["name"] == "Normalized Channel"


def test_native_notification_title_normalizes_but_body_is_preserved(monkeypatch) -> None:
    with TestClient(app) as client:
        csrf = establish_admin(client, monkeypatch)
        headers = {"X-CSRF-Token": csrf}

        identity = client.post(
            "/api/v1/service-identities",
            headers=headers,
            json={"name": "Notification Producer"},
        )
        assert identity.status_code == 201
        identity_id = identity.json()["id"]

        source = client.post(
            "/api/v1/sources",
            headers=headers,
            json={
                "service_identity_id": identity_id,
                "slug": "normalize",
                "name": "Normalize",
            },
        )
        channel = client.post(
            "/api/v1/channels",
            headers=headers,
            json={"slug": "goreecloud-normalize", "name": "Normalize"},
        )
        token = client.post(
            "/api/v1/tokens",
            headers=headers,
            json={
                "service_identity_id": identity_id,
                "name": "Normalize Publisher",
                "scopes": ["notifications:write"],
            },
        )
        assert source.status_code == channel.status_code == token.status_code == 201
        producer_headers = {"Authorization": f"Bearer {token.json()['token']}"}

        blank = client.post(
            "/api/v1/notifications",
            headers=producer_headers,
            json={
                "source": "normalize",
                "channel": "goreecloud-normalize",
                "title": "   ",
                "body": "body",
            },
        )
        assert blank.status_code == 422

        preserved_body = "  keep these body spaces exactly  "
        created = client.post(
            "/api/v1/notifications",
            headers=producer_headers,
            json={
                "source": "normalize",
                "channel": "goreecloud-normalize",
                "title": "  Normalized title  ",
                "body": preserved_body,
            },
        )

    assert created.status_code == 201
    assert created.json()["title"] == "Normalized title"
    assert created.json()["body"] == preserved_body


def test_user_password_whitespace_is_not_trimmed(monkeypatch) -> None:
    padded_password = "  password spaces are intentional  "
    with TestClient(app) as admin_client, TestClient(app) as user_client:
        csrf = establish_admin(admin_client, monkeypatch)
        created = admin_client.post(
            "/api/v1/users",
            headers={"X-CSRF-Token": csrf},
            json={
                "username": "padded-password",
                "display_name": "  Padded Password User  ",
                "password": padded_password,
            },
        )
        assert created.status_code == 201
        assert created.json()["display_name"] == "Padded Password User"

        stripped = user_client.post(
            "/api/v1/session",
            json={
                "username": "padded-password",
                "password": padded_password.strip(),
            },
        )
        exact = user_client.post(
            "/api/v1/session",
            json={
                "username": "padded-password",
                "password": padded_password,
            },
        )

    assert stripped.status_code == 401
    assert stripped.json() == {"detail": "invalid credentials"}
    assert exact.status_code == 200
