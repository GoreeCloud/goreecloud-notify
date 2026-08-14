from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import models  # noqa: F401 - registers SQLAlchemy metadata
from .config import settings
from .database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Milestone 1 foundation API for GoreeCloud Notify.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
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
        "production": False,
        "notification_writes_enabled": False,
        "entities": [
            "User",
            "Device",
            "ServiceIdentity",
            "Source",
            "Channel",
            "Subscription",
            "Notification",
            "Delivery",
            "AccessToken",
            "Preference",
        ],
        "next_milestone": "Notification Engine",
    }
