from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .deps import get_db
from .models import User, WebSession

SESSION_PREFIX = "gcs_"
CSRF_HEADER = "X-CSRF-Token"
PASSWORD_HASHER = PasswordHasher()
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash("goreecloud-notify-dummy-password")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return PASSWORD_HASHER.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def session_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session_token() -> str:
    return f"{SESSION_PREFIX}{secrets.token_urlsafe(32)}"


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


@dataclass(frozen=True, slots=True)
class UserPrincipal:
    user_id: int
    session_id: int
    username: str
    display_name: str


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    normalized = username.strip().lower()
    user = session.scalar(select(User).where(User.username == normalized))
    candidate_hash = user.password_hash if user is not None and user.password_hash else DUMMY_PASSWORD_HASH
    valid = verify_password(password, candidate_hash)

    if user is None or not user.is_active or not user.password_hash or not valid:
        return None

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        session.commit()
        session.refresh(user)

    return user


def create_web_session(session: Session, user: User) -> tuple[WebSession, str]:
    now = utc_now()
    raw_token = issue_session_token()
    record = WebSession(
        user_id=user.id,
        session_digest=session_digest(raw_token),
        csrf_token=issue_csrf_token(),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(minutes=settings.session_lifetime_minutes),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record, raw_token


def revoke_web_session(session: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    record = session.scalar(
        select(WebSession).where(WebSession.session_digest == session_digest(raw_token))
    )
    if record is None or record.revoked_at is not None:
        return
    record.revoked_at = utc_now()
    session.commit()


def require_user_session(
    session: Annotated[Session, Depends(get_db)],
    raw_token: Annotated[
        str | None, Cookie(alias=settings.session_cookie_name)
    ] = None,
) -> UserPrincipal:
    if not raw_token or not raw_token.startswith(SESSION_PREFIX):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user session required")

    record = session.scalar(
        select(WebSession).where(WebSession.session_digest == session_digest(raw_token))
    )
    if record is None or record.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid user session")

    now = utc_now()
    last_seen = as_utc(record.last_seen_at)
    if as_utc(record.expires_at) <= now or last_seen + timedelta(
        minutes=settings.session_idle_minutes
    ) <= now:
        record.revoked_at = now
        session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user session expired")

    user = session.get(User, record.user_id)
    if user is None or not user.is_active:
        record.revoked_at = now
        session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user session unavailable")

    if last_seen + timedelta(minutes=settings.session_touch_minutes) <= now:
        record.last_seen_at = now
        session.commit()

    return UserPrincipal(
        user_id=user.id,
        session_id=record.id,
        username=user.username,
        display_name=user.display_name,
    )


def csrf_token_for_principal(session: Session, principal: UserPrincipal) -> str:
    record = session.get(WebSession, principal.session_id)
    if record is None or record.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid user session")
    return record.csrf_token


def require_csrf_user_session(
    principal: Annotated[UserPrincipal, Depends(require_user_session)],
    session: Annotated[Session, Depends(get_db)],
    csrf_token: Annotated[str | None, Header(alias=CSRF_HEADER)] = None,
) -> UserPrincipal:
    if not csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token required")

    expected = csrf_token_for_principal(session, principal)
    if not secrets.compare_digest(expected, csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid CSRF token")
    return principal
