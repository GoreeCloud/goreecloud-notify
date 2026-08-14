from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from . import models  # noqa: F401 - registers SQLAlchemy metadata
from .config import settings
from .database import engine, verify_schema
from .routers import admin, compatibility, inbox, notifications, retention, session, subscriptions

STATIC_ROOT = Path(__file__).resolve().parent / "static"


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
    description="Milestone 4 real-time delivery development for GoreeCloud Notify.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-GoreeCloud-Admin-Token"],
    expose_headers=["X-CSRF-Token"],
)

app.mount(
    "/assets",
    ImmutableStaticFiles(directory=STATIC_ROOT / "assets", check_dir=False),
    name="frontend-assets",
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
        "milestone": 1,
        "development_milestone": 4,
        "production": settings.environment == "production",
        "notification_writes_enabled": True,
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
        ],
        "next_milestone": "Real-Time Delivery",
        "next_slice": "Milestone 4 browser notification permission and privacy design",
    }


app.include_router(admin.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(session.router, prefix="/api/v1")
app.include_router(inbox.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(retention.router, prefix="/api/v1")
app.include_router(compatibility.router)
