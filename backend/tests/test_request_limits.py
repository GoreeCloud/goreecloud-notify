from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import CONTENT_SECURITY_POLICY, PERMISSIONS_POLICY, app
from app.models import AccessToken, Channel, ServiceIdentity, Source
from app.observability import (
    REQUEST_ID_HEADER,
    WARDVEIL_HEADER,
    WARDVEIL_STATUS,
    RequestObservabilityMiddleware,
)
from app.request_limits import (
    DEFAULT_MAX_REQUEST_BODY_BYTES,
    NATIVE_NOTIFICATION_MAX_REQUEST_BODY_BYTES,
    NTFY_COMPAT_MAX_REQUEST_BODY_BYTES,
    RequestBodyLimitMiddleware,
)
from app.security import token_digest


def _setup_producer() -> str:
    raw_token = "gcn_issue_82_request_limits"
    with SessionLocal() as session:
        identity = ServiceIdentity(name="Issue 82 Producer")
        session.add(identity)
        session.flush()
        session.add(
            Source(
                service_identity_id=identity.id,
                slug="issue-82",
                name="Issue 82",
            )
        )
        session.add(Channel(slug="goreecloud-issue-82", name="GoreeCloud Issue 82"))
        session.add(
            AccessToken(
                service_identity_id=identity.id,
                name="Issue 82 publisher",
                token_digest=token_digest(raw_token),
                scope="notifications:write",
            )
        )
        session.commit()
    return raw_token


def _assert_protected_too_large(response, request_id: str) -> None:
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body exceeds the allowed size."}
    assert response.headers[REQUEST_ID_HEADER] == request_id
    assert response.headers[WARDVEIL_HEADER] == WARDVEIL_STATUS
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["content-security-policy"] == CONTENT_SECURITY_POLICY
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["permissions-policy"] == PERMISSIONS_POLICY


def test_real_application_installs_request_body_limiter_inside_observability() -> None:
    middleware = [entry.cls for entry in app.user_middleware]

    assert RequestBodyLimitMiddleware in middleware
    assert middleware.index(RequestObservabilityMiddleware) < middleware.index(RequestBodyLimitMiddleware)


def test_default_oversized_request_fails_before_route_parsing() -> None:
    request_id = "issue-82-default-limit"
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/session",
            content=b"{" * (DEFAULT_MAX_REQUEST_BODY_BYTES + 1),
            headers={"Content-Type": "application/json", REQUEST_ID_HEADER: request_id},
        )

    _assert_protected_too_large(response, request_id)


def test_native_notification_keeps_the_larger_valid_unicode_envelope() -> None:
    raw_token = _setup_producer()
    body = "\U0001f514" * 20_000
    payload = {
        "source": "issue-82",
        "channel": "goreecloud-issue-82",
        "title": "Large Unicode notification",
        "body": body,
        "severity": "warning",
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert DEFAULT_MAX_REQUEST_BODY_BYTES < len(encoded) <= NATIVE_NOTIFICATION_MAX_REQUEST_BODY_BYTES

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/notifications",
            content=encoded,
            headers={
                "Authorization": f"Bearer {raw_token}",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 201
    assert response.json()["body"] == body


def test_native_notification_rejects_an_oversized_envelope() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/notifications",
            content=b"x" * (NATIVE_NOTIFICATION_MAX_REQUEST_BODY_BYTES + 1),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 413


def test_real_ntfy_compatibility_topic_keeps_the_tighter_envelope() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/goreecloud-issue-82",
            content=b"x" * (NTFY_COMPAT_MAX_REQUEST_BODY_BYTES + 1),
        )

    assert response.status_code == 413
