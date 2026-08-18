from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import (
    APP_ICON_CACHE_CONTROL,
    APP_ICON_URL,
    MANIFEST_CACHE_CONTROL,
    MANIFEST_URL,
    app,
)


def _write_identity_artifacts(root: Path) -> None:
    icon = root / "brand" / "goreecloud-notify-icon.svg"
    icon.parent.mkdir(parents=True, exist_ok=True)
    icon.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512"/></svg>',
        encoding="utf-8",
    )
    (root / "manifest.webmanifest").write_text(
        json.dumps(
            {
                "id": "/",
                "name": "GoreeCloud Notify",
                "icons": [{"src": APP_ICON_URL, "sizes": "any", "type": "image/svg+xml"}],
            }
        ),
        encoding="utf-8",
    )


def _assert_browser_security_headers(response) -> None:
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["origin-agent-cluster"] == "?1"


def test_canonical_icon_and_manifest_are_served_by_the_application(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main_module, "STATIC_ROOT", tmp_path)
    _write_identity_artifacts(tmp_path)

    with TestClient(app) as client:
        manifest_response = client.get(MANIFEST_URL)
        icon_response = client.get(APP_ICON_URL)

    assert manifest_response.status_code == 200
    assert manifest_response.headers["content-type"].startswith("application/manifest+json")
    assert manifest_response.headers["cache-control"] == MANIFEST_CACHE_CONTROL
    assert "pragma" not in manifest_response.headers
    assert manifest_response.json()["icons"][0]["src"] == APP_ICON_URL
    _assert_browser_security_headers(manifest_response)

    assert icon_response.status_code == 200
    assert icon_response.headers["content-type"].startswith("image/svg+xml")
    assert icon_response.headers["cache-control"] == APP_ICON_CACHE_CONTROL
    assert "pragma" not in icon_response.headers
    assert icon_response.text.startswith("<svg")
    _assert_browser_security_headers(icon_response)


def test_missing_identity_artifacts_fail_private_and_uncached(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main_module, "STATIC_ROOT", tmp_path)

    with TestClient(app) as client:
        manifest_response = client.get(MANIFEST_URL)
        icon_response = client.get(APP_ICON_URL)

    for response in (manifest_response, icon_response):
        assert response.status_code == 404
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["pragma"] == "no-cache"
        _assert_browser_security_headers(response)


def test_identity_routes_do_not_create_a_general_static_file_surface(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main_module, "STATIC_ROOT", tmp_path)
    _write_identity_artifacts(tmp_path)
    (tmp_path / "brand" / "unexpected.txt").write_text("must not be exposed", encoding="utf-8")

    with TestClient(app) as client:
        response = client.get("/brand/unexpected.txt")

    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
