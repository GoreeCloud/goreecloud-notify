from __future__ import annotations

import http.cookiejar
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://notify.goreecloud.com"
CA_CERT = Path("/readiness/root.crt")
USERNAME = "readiness-admin"
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "base-uri 'none'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "frame-src 'none'",
        "form-action 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "media-src 'none'",
        "worker-src 'none'",
        "manifest-src 'self'",
    )
)
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
STRICT_TRANSPORT_SECURITY = "max-age=31536000"


def build_opener() -> urllib.request.OpenerDirector:
    if not CA_CERT.is_file():
        raise RuntimeError("Caddy readiness CA was not provided")
    context = ssl.create_default_context(cafile=str(CA_CERT))
    cookies = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context),
        urllib.request.HTTPCookieProcessor(cookies),
    )


def request(
    opener: urllib.request.OpenerDirector,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    expected: int = 200,
) -> tuple[bytes, object]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = dict(headers or {})
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        response = opener.open(req, timeout=5)
    except urllib.error.HTTPError as exc:
        if exc.code != expected:
            raise AssertionError(f"{method} {path} returned {exc.code}, expected {expected}") from exc
        return exc.read(), exc.headers

    with response:
        if response.status != expected:
            raise AssertionError(f"{method} {path} returned {response.status}, expected {expected}")
        return response.read(), response.headers


def assert_browser_security_headers(headers: object) -> None:
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("Referrer-Policy") == "no-referrer"
    assert headers.get("Content-Security-Policy") == CONTENT_SECURITY_POLICY
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Permissions-Policy") == PERMISSIONS_POLICY
    assert headers.get("Strict-Transport-Security") == STRICT_TRANSPORT_SECURITY


def assert_private_response_headers(headers: object) -> None:
    assert headers.get("Cache-Control") == "no-store"
    assert headers.get("Pragma") == "no-cache"
    assert_browser_security_headers(headers)


def assert_public_surface(opener: urllib.request.OpenerDirector) -> None:
    health_body, health_headers = request(opener, "/healthz")
    assert_private_response_headers(health_headers)
    health = json.loads(health_body)
    assert health["status"] == "ok"
    assert "build_revision" not in health

    meta_body, meta_headers = request(opener, "/api/v1/meta")
    assert_private_response_headers(meta_headers)
    meta = json.loads(meta_body)
    assert meta["production"] is True
    assert meta["build_revision"] == os.environ[
        "GOREECLOUD_NOTIFY_READINESS_EXPECTED_BUILD_REVISION"
    ]

    _, unauthorized_headers = request(opener, "/api/v1/me", expected=401)
    assert_private_response_headers(unauthorized_headers)

    index_body, index_headers = request(opener, "/")
    assert_private_response_headers(index_headers)
    index = index_body.decode("utf-8")
    asset_match = re.search(r'(?:src|href)="(/assets/[^"]+)"', index)
    assert asset_match is not None, "production index did not reference a built asset"
    _, asset_headers = request(opener, asset_match.group(1))
    cache_control = asset_headers.get("Cache-Control", "")
    assert "immutable" in cache_control and "max-age=31536000" in cache_control
    assert asset_headers.get("Pragma") is None
    assert_browser_security_headers(asset_headers)

    _, cors_headers = request(
        opener,
        "/api/v1/meta",
        method="OPTIONS",
        headers={
            "Origin": BASE_URL,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert cors_headers.get("Access-Control-Allow-Origin") == BASE_URL
    assert cors_headers.get("Access-Control-Allow-Credentials") == "true"
    assert_private_response_headers(cors_headers)


def login_and_assert_admin(opener: urllib.request.OpenerDirector, password: str) -> None:
    _, login_headers = request(
        opener,
        "/api/v1/session",
        method="POST",
        payload={"username": USERNAME, "password": password},
    )
    assert_private_response_headers(login_headers)
    cookie_headers = login_headers.get_all("Set-Cookie") or []
    session_cookie = next(value for value in cookie_headers if "goreecloud_notify_session=" in value)
    assert "Secure" in session_cookie
    assert "HttpOnly" in session_cookie
    assert "SameSite=strict" in session_cookie
    assert login_headers.get("X-CSRF-Token")

    me_body, me_headers = request(opener, "/api/v1/me")
    assert_private_response_headers(me_headers)
    me = json.loads(me_body)
    assert me["username"] == USERNAME
    assert me["is_admin"] is True

    channels_body, channel_headers = request(opener, "/api/v1/channels")
    assert_private_response_headers(channel_headers)
    assert isinstance(json.loads(channels_body), list)


def bootstrap(opener: urllib.request.OpenerDirector, password: str) -> None:
    bootstrap_token = os.environ["GOREECLOUD_NOTIFY_READINESS_BOOTSTRAP_TOKEN"]
    _, headers = request(
        opener,
        "/api/v1/bootstrap/administrator",
        method="POST",
        headers={"X-GoreeCloud-Admin-Token": bootstrap_token},
        payload={
            "username": USERNAME,
            "display_name": "Readiness Administrator",
            "password": password,
            "is_admin": True,
        },
        expected=201,
    )
    assert_private_response_headers(headers)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "bootstrap"
    if mode not in {"bootstrap", "persisted"}:
        raise SystemExit(f"unsupported readiness mode: {mode}")

    password = os.environ["GOREECLOUD_NOTIFY_READINESS_ADMIN_PASSWORD"]
    opener = build_opener()
    assert_public_surface(opener)
    if mode == "bootstrap":
        bootstrap(opener, password)
    login_and_assert_admin(opener, password)
    print(f"approved-source readiness checks passed ({mode})")


if __name__ == "__main__":
    main()
