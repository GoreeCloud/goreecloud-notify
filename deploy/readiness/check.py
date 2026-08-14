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


def assert_public_surface(opener: urllib.request.OpenerDirector) -> None:
    health_body, _ = request(opener, "/healthz")
    health = json.loads(health_body)
    assert health["status"] == "ok"

    meta_body, _ = request(opener, "/api/v1/meta")
    meta = json.loads(meta_body)
    assert meta["production"] is True

    request(opener, "/api/v1/me", expected=401)

    index_body, index_headers = request(opener, "/")
    assert index_headers.get("Cache-Control") == "no-store"
    index = index_body.decode("utf-8")
    asset_match = re.search(r'(?:src|href)="(/assets/[^"]+)"', index)
    assert asset_match is not None, "production index did not reference a built asset"
    _, asset_headers = request(opener, asset_match.group(1))
    cache_control = asset_headers.get("Cache-Control", "")
    assert "immutable" in cache_control and "max-age=31536000" in cache_control

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


def login_and_assert_admin(opener: urllib.request.OpenerDirector, password: str) -> None:
    _, login_headers = request(
        opener,
        "/api/v1/session",
        method="POST",
        payload={"username": USERNAME, "password": password},
    )
    cookie_headers = login_headers.get_all("Set-Cookie") or []
    session_cookie = next(value for value in cookie_headers if "goreecloud_notify_session=" in value)
    assert "Secure" in session_cookie
    assert "HttpOnly" in session_cookie
    assert "SameSite=strict" in session_cookie
    assert login_headers.get("X-CSRF-Token")

    me_body, _ = request(opener, "/api/v1/me")
    me = json.loads(me_body)
    assert me["username"] == USERNAME
    assert me["is_admin"] is True

    channels_body, _ = request(opener, "/api/v1/channels")
    assert isinstance(json.loads(channels_body), list)


def bootstrap(opener: urllib.request.OpenerDirector, password: str) -> None:
    bootstrap_token = os.environ["GOREECLOUD_NOTIFY_READINESS_BOOTSTRAP_TOKEN"]
    request(
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
