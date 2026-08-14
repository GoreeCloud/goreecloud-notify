from __future__ import annotations

import os
from dataclasses import dataclass
from ipaddress import ip_network


_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False

    accepted = ", ".join(sorted(_TRUE_VALUES | _FALSE_VALUES))
    raise ValueError(f"{name} must be one of: {accepted}")


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = int(raw)
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


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
    session_cookie_name: str = os.getenv(
        "GOREECLOUD_NOTIFY_SESSION_COOKIE_NAME",
        "goreecloud_notify_session",
    )
    session_cookie_secure: bool = _env_bool("GOREECLOUD_NOTIFY_SESSION_COOKIE_SECURE", False)
    session_lifetime_minutes: int = _env_int(
        "GOREECLOUD_NOTIFY_SESSION_LIFETIME_MINUTES", 720, minimum=15
    )
    session_idle_minutes: int = _env_int(
        "GOREECLOUD_NOTIFY_SESSION_IDLE_MINUTES", 60, minimum=5
    )
    session_touch_minutes: int = _env_int(
        "GOREECLOUD_NOTIFY_SESSION_TOUCH_MINUTES", 5, minimum=1
    )
    trusted_proxy_cidrs: tuple[str, ...] = _split_csv(
        os.getenv("GOREECLOUD_NOTIFY_TRUSTED_PROXY_CIDRS", "")
    )
    login_rate_window_minutes: int = _env_int(
        "GOREECLOUD_NOTIFY_LOGIN_RATE_WINDOW_MINUTES", 5, minimum=1
    )
    login_rate_account_attempts: int = _env_int(
        "GOREECLOUD_NOTIFY_LOGIN_RATE_ACCOUNT_ATTEMPTS", 5, minimum=1
    )
    login_rate_source_attempts: int = _env_int(
        "GOREECLOUD_NOTIFY_LOGIN_RATE_SOURCE_ATTEMPTS", 20, minimum=1
    )
    login_rate_cooldown_minutes: int = _env_int(
        "GOREECLOUD_NOTIFY_LOGIN_RATE_COOLDOWN_MINUTES", 5, minimum=1
    )
    login_rate_state_ttl_hours: int = _env_int(
        "GOREECLOUD_NOTIFY_LOGIN_RATE_STATE_TTL_HOURS", 24, minimum=1
    )
    login_security_event_retention_days: int = _env_int(
        "GOREECLOUD_NOTIFY_LOGIN_SECURITY_EVENT_RETENTION_DAYS", 30, minimum=1
    )

    def __post_init__(self) -> None:
        if "*" in self.cors_origins:
            raise ValueError(
                "GOREECLOUD_NOTIFY_CORS_ORIGINS cannot contain '*' when credentialed web sessions are enabled"
            )
        if self.session_touch_minutes >= self.session_idle_minutes:
            raise ValueError(
                "GOREECLOUD_NOTIFY_SESSION_TOUCH_MINUTES must be less than "
                "GOREECLOUD_NOTIFY_SESSION_IDLE_MINUTES"
            )
        for cidr in self.trusted_proxy_cidrs:
            try:
                ip_network(cidr, strict=False)
            except ValueError as exc:
                raise ValueError(
                    f"GOREECLOUD_NOTIFY_TRUSTED_PROXY_CIDRS contains invalid network: {cidr}"
                ) from exc


settings = Settings()
