from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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


class NotificationCreate(BaseModel):
    source: str = Field(min_length=1, max_length=120)
    channel: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)
    severity: str = Field(default="normal", pattern=r"^(info|normal|warning|error|critical)$")
    expires_at: datetime | None = None


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


class UserRead(BaseModel):
    id: int
    username: str
    display_name: str
    is_active: bool


class SessionCreate(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)
