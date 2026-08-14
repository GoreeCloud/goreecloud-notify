from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import models  # noqa: F401 - registers SQLAlchemy metadata
from .config import settings
from .database import engine, verify_schema
from .routers import admin, compatibility, inbox, notifications, session


@asynccontextmanager
async def lifespan(_: FastAPI):
    verify_schema()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Milestone 2 identity and routing foundation for GoreeCloud Notify.",
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
        "development_milestone": 2,
        "production": False,
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
        ],
        "next_milestone": "Notification Engine",
        "next_slice": "subscription administration and Milestone 2 hardening",
    }


app.include_router(admin.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(session.router, prefix="/api/v1")
app.include_router(inbox.router, prefix="/api/v1")
app.include_router(compatibility.router)
