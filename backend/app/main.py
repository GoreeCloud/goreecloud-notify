from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import models  # noqa: F401 - registers SQLAlchemy metadata
from .config import settings
from .database import Base, engine
from .routers import admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
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
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-GoreeCloud-Admin-Token"],
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
        "milestone": 2,
        "production": False,
        "notification_writes_enabled": False,
        "implemented": [
            "bootstrap administrative authorization",
            "service identities",
            "scoped producer token issuance",
            "token revocation",
            "source administration",
            "channel administration",
        ],
        "next_slice": "notification ingestion and persistence",
    }


app.include_router(admin.router, prefix="/api/v1")
