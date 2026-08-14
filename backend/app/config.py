from __future__ import annotations

import os
from dataclasses import dataclass


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "GoreeCloud Notify"
    version: str = "0.2.0-dev"
    database_url: str = os.getenv(
        "GOREECLOUD_NOTIFY_DATABASE_URL",
        "sqlite:///./data/goreecloud_notify.db",
    )
    cors_origins: tuple[str, ...] = _split_csv(
        os.getenv(
            "GOREECLOUD_NOTIFY_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        )
    )
    admin_token: str | None = os.getenv("GOREECLOUD_NOTIFY_ADMIN_TOKEN")


settings = Settings()
