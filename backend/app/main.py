from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.datastructures import MutableHeaders

from . import models  # noqa: F401 - registers SQLAlchemy metadata
from .config import settings
from .database import engine, verify_schema
from .observability import (
    REQUEST_ID_HEADER,
    WARDVEIL_HEADER,
    WARDVEIL_STATUS,
    RequestObservabilityMiddleware,
)
from .routers import admin, compatibility, inbox, notifications, retention, session, subscriptions

STATIC_ROOT = Path(__file__).resolve().parent / "static"
APP_ICON_RELATIVE_PATH = Path("brand") / "goreecloud-notify-icon.svg"
MANIFEST_RELATIVE_PATH = Path("manifest.webmanifest")
APP_ICON_URL = "/brand/goreecloud-notify-icon.svg"
MANIFEST_URL = "/manifest.webmanifest"
APP_ICON_CACHE_CONTROL = "public, max-age=86400, must-revalidate"
MANIFEST_CACHE_CONTROL = "public, max-age=3600, must-revalidate"
CACHEABLE_PUBLIC_PATHS = frozenset({APP_ICON_URL, MANIFEST_URL})
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


class ResponsePrivacyHeadersMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        is_immutable_asset_path = path.startswith("/assets/")
        is_public_identity_path = path in CACHEABLE_PUBLIC_PATHS

        async def send_with_privacy_headers(message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                status_code = int(message.get("status", 500))
                is_cacheable_success = status_code in {status.HTTP_200_OK, status.HTTP_304_NOT_MODIFIED} and (
                    is_immutable_asset_path or is_public_identity_path
                )
                if not is_cacheable_success:
                    headers["Cache-Control"] = "no-store"
                    headers["Pragma"] = "no-cache"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
                headers["X-Frame-Options"] = "DENY"
                headers["Permissions-Policy"] = PERMISSIONS_POLICY
                headers["Cross-Origin-Opener-Policy"] = "same-origin"
                headers["Cross-Origin-Resource-Policy"] = "same-origin"
                headers["Origin-Agent-Cluster"] = "?1"
                headers["X-Permitted-Cross-Domain-Policies"] = "none"
            await send(message)

        await self.app(scope, receive, send_with_privacy_headers)


class ImmutableStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == status.HTTP_200_OK:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    verify_schema()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="GoreeCloud-native centralized notification delivery service.",
    lifespan=lifespan,
)

app.add_middleware(RequestObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-GoreeCloud-Admin-Token"],
    expose_headers=["X-CSRF-Token", REQUEST_ID_HEADER, WARDVEIL_HEADER],
)
app.add_middleware(ResponsePrivacyHeadersMiddleware)

app.mount(
    "/assets",
    ImmutableStaticFiles(directory=STATIC_ROOT / "assets", check_dir=False),
    name="frontend-assets",
)


def _frontend_public_file(
    relative_path: Path,
    *,
    media_type: str,
    cache_control: str,
) -> FileResponse:
    target = STATIC_ROOT / relative_path
    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="frontend public artifact is not installed in this runtime",
        )
    return FileResponse(
        target,
        media_type=media_type,
        headers={"Cache-Control": cache_control},
    )


@app.get(APP_ICON_URL, include_in_schema=False)
def frontend_app_icon() -> FileResponse:
    return _frontend_public_file(
        APP_ICON_RELATIVE_PATH,
        media_type="image/svg+xml",
        cache_control=APP_ICON_CACHE_CONTROL,
    )


@app.get(MANIFEST_URL, include_in_schema=False)
def frontend_manifest() -> FileResponse:
    return _frontend_public_file(
        MANIFEST_RELATIVE_PATH,
        media_type="application/manifest+json",
        cache_control=MANIFEST_CACHE_CONTROL,
    )


@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse:
    index = STATIC_ROOT / "index.html"
    if not index.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="frontend artifact is not installed in this runtime",
        )
    return FileResponse(index, headers={"Cache-Control": "no-store"})


@app.get("/healthz", tags=["system"])
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name, "version": settings.version}


@app.get("/api/v1/meta", tags=["system"])
def api_meta() -> dict[str, object]:
    return {
        "service": settings.app_name,
        "version": settings.version,
        "build_revision": settings.build_revision,
        "milestone": 1,
        "development_milestone": 4,
        "production": settings.environment == "production",
        "release_stage": "production" if settings.environment == "production" else "release_candidate",
        "notification_writes_enabled": True,
        "security_identity": {
            "name": "Wardveil Security",
            "full_presentation": "Wardveil Security by GoreeCloud",
            "protection_status": WARDVEIL_STATUS,
            "authority": "GoreeCloud Notify application security controls remain authoritative",
        },
        "observability": {
            "request_correlation_header": REQUEST_ID_HEADER,
            "structured_http_events": True,
            "sensitive_request_data_logged": False,
        },
        "entities": [
            "User", "Device", "ServiceIdentity", "Source", "Channel",
            "Subscription", "Notification", "Delivery", "AccessToken", "Preference",
        ],
        "implemented_control_plane": [
            "bootstrap administrative authorization",
            "service identities",
            "scoped producer token issuance",
            "token revocation",
            "source administration",
            "channel administration",
        ],
        "implemented_engine": [
            "native notification ingestion",
            "notification persistence",
            "producer source ownership enforcement",
            "scoped producer notification history",
            "source-isolated notification detail access",
            "ntfy-compatible simple topic publishing",
            "administrator-provisioned human users",
            "opaque server-side user sessions",
            "subscription-based user Delivery fanout",
            "authenticated user inbox",
            "CSRF-protected Delivery read and acknowledgement mutations",
            "user-owned subscription administration",
            "non-destructive administrator retention preview",
            "authenticated SSE inbox stream",
            "database-backed SSE delivery cursor",
            "Last-Event-ID replay contract",
            "long-lived user-session revalidation",
            "authoritative inbox state snapshot",
            "SSE aggregate inbox state events",
        ],
        "implemented_experience": [
            "authenticated Glaze UI inbox",
            "server-backed notification search and filtering",
            "cursor-based inbox pagination",
            "Glaze UI channel subscription management",
            "source and severity presentation",
            "read and acknowledgement controls",
            "fail-visible logout behavior",
            "responsive layout and appearance controls",
            "Chromium browser interaction validation",
            "automated WCAG A and AA accessibility checks",
            "real-time Glaze inbox delivery",
            "live connection and reconnect status",
            "stream-handshake inbox reconciliation",
            "authoritative inbox navigation counters",
            "cursor-bootstrap inbox synchronization",
            "reconnecting session validation",
            "fail-closed realtime resynchronization",
            "immediate filtered mutation reconciliation",
            "explicit offline realtime state",
            "last-received Delivery cursor offline recovery",
            "online recovery stream reconciliation",
            "privacy-first browser notification opt-in",
            "generic redacted system notification content",
            "hidden-page browser notification delivery",
            "foreground system-alert suppression",
            "replay and backlog system-alert suppression",
            "browser-local system-alert preference",
            "realtime REST reconciliation race protection",
            "canonical cross-platform application identity",
            "installable-web identity manifest",
        ],
        "next_milestone": "Production Acceptance",
        "next_slice": "Target deployment, manual browser/OS acceptance, migration, and rollback validation",
    }


app.include_router(admin.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(session.router, prefix="/api/v1")
app.include_router(inbox.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(retention.router, prefix="/api/v1")
app.include_router(compatibility.router)
