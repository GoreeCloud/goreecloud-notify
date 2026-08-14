from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .deps import get_db
from .models import AccessToken, ServiceIdentity


TOKEN_PREFIX = "gcn_"


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token() -> str:
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def scopes_from_string(value: str) -> set[str]:
    return {scope for scope in value.split() if scope}


def scopes_to_string(scopes: list[str]) -> str:
    return " ".join(sorted(set(scopes)))


def require_admin(
    supplied_token: Annotated[str | None, Header(alias="X-GoreeCloud-Admin-Token")] = None,
) -> None:
    if not settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="administrative API is not configured",
        )
    if supplied_token is None or not hmac.compare_digest(supplied_token, settings.admin_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")


@dataclass(frozen=True, slots=True)
class TokenPrincipal:
    token_id: int
    service_identity_id: int
    service_identity_name: str
    scopes: frozenset[str]


def _is_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


def require_scope(scope: str) -> Callable[..., TokenPrincipal]:
    def dependency(
        session: Annotated[Session, Depends(get_db)],
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    ) -> TokenPrincipal:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bearer token required")
        raw_token = authorization.removeprefix("Bearer ").strip()
        if not raw_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bearer token required")

        record = session.scalar(
            select(AccessToken).where(AccessToken.token_digest == token_digest(raw_token))
        )
        if record is None or not record.enabled or _is_expired(record.expires_at):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token")

        identity = session.get(ServiceIdentity, record.service_identity_id)
        if identity is None or not identity.enabled:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="service identity disabled")

        scopes = scopes_from_string(record.scope)
        if scope not in scopes and "*" not in scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="token scope denied")

        return TokenPrincipal(
            token_id=record.id,
            service_identity_id=identity.id,
            service_identity_name=identity.name,
            scopes=frozenset(scopes),
        )

    return dependency
