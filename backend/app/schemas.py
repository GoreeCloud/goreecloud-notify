from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from .datetime_utils import require_explicit_timezone_utc


class ServiceIdentityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)


class ServiceIdentityRead(BaseModel):
    id: int
    name: str
    description: str | None
    enabled: bool


class TokenCreate(BaseModel):
    service_identity_id: int
    name: str = Field(min_length=1, max_length=200)
    scopes: list[str] = Field(min_length=1, max_length=20)
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def normalize_scopes(cls, scopes: list[str]) -> list[str]:
        normalized = sorted({scope.strip() for scope in scopes if scope.strip()})
        if not normalized:
            raise ValueError("at least one scope is required")
        return normalized

    @field_validator("expires_at")
    @classmethod
    def normalize_expires_at(cls, value: datetime | None) -> datetime | None:
        return require_explicit_timezone_utc(value)


class TokenCreated(BaseModel):
    id: int
    name: str
    token: str
    scopes: list[str]
    expires_at: datetime | None


class SourceCreate(BaseModel):
    service_identity_id: int
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,119}$")
    name: str = Field(min_length=1, max_length=200)


class SourceRead(BaseModel):
    id: int
    service_identity_id: int
    slug: str
    name: str


class ChannelCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,119}$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ChannelRead(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None


class SubscriptionRead(BaseModel):
    channel_id: int
    channel: str
    name: str
    description: str | None
    subscribed: bool


class NotificationCreate(BaseModel):
    source: str = Field(min_length=1, max_length=120)
    channel: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)
    severity: str = Field(default="normal", pattern=r"^(info|normal|warning|error|critical)$")
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def normalize_expires_at(cls, value: datetime | None) -> datetime | None:
        return require_explicit_timezone_utc(value)


class NotificationRead(BaseModel):
    id: int
    source: str
    channel: str
    title: str
    body: str
    severity: str
    created_at: datetime
    expires_at: datetime | None


class InboxDeliveryRead(BaseModel):
    id: int
    notification_id: int
    source: str
    channel: str
    title: str
    body: str
    severity: str
    notification_created_at: datetime
    delivered_at: datetime
    expires_at: datetime | None
    read_at: datetime | None
    acknowledged_at: datetime | None


class UserCreate(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,119}$")
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12, max_length=256)
    is_admin: bool = False


class UserRead(BaseModel):
    id: int
    username: str
    display_name: str
    is_active: bool
    is_admin: bool


class SessionCreate(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class CsrfTokenRead(BaseModel):
    csrf_token: str


class RetentionPreviewRead(BaseModel):
    mode: str
    cutoff: datetime
    cutoff_basis: str
    destructive_action_enabled: bool
    candidate_notifications: int
    candidate_deliveries: int
    candidate_read_deliveries: int
    candidate_unread_deliveries: int
    candidate_acknowledged_deliveries: int
    candidate_unacknowledged_deliveries: int
    candidate_explicitly_expired_notifications: int
    oldest_candidate_created_at: datetime | None
    newest_candidate_created_at: datetime | None
