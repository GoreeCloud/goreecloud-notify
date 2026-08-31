from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .datetime_utils import as_utc
from .delivery_service import fanout_notification
from .models import Channel, Notification, Source
from .schemas import NotificationCreate, NotificationRead
from .security import TokenPrincipal


@dataclass(frozen=True, slots=True)
class ResolvedRoute:
    source: Source
    channel: Channel


@dataclass(frozen=True, slots=True)
class NotificationPersistenceResult:
    notification: Notification
    replayed: bool


def resolve_route(
    session: Session,
    principal: TokenPrincipal,
    *,
    source_slug: str,
    channel_slug: str,
) -> ResolvedRoute:
    source = session.scalar(select(Source).where(Source.slug == source_slug))
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="source not found")
    if source.service_identity_id != principal.service_identity_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="source is not owned by token identity",
        )

    channel = session.scalar(select(Channel).where(Channel.slug == channel_slug))
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="channel not found")

    return ResolvedRoute(source=source, channel=channel)


def _idempotency_digest(idempotency_key: str) -> str:
    # Persist only a one-way digest. Idempotency keys can encode producer-local
    # identifiers and do not need to become notification history or export data.
    return sha256(idempotency_key.encode("utf-8")).hexdigest()


def _existing_idempotent_notification(
    session: Session,
    route: ResolvedRoute,
    digest: str,
) -> Notification | None:
    return session.scalar(
        select(Notification).where(
            Notification.source_id == route.source.id,
            Notification.idempotency_digest == digest,
        )
    )


def _assert_idempotent_payload_matches(
    existing: Notification,
    route: ResolvedRoute,
    payload: NotificationCreate,
) -> None:
    existing_expires = as_utc(existing.expires_at) if existing.expires_at is not None else None
    requested_expires = as_utc(payload.expires_at) if payload.expires_at is not None else None
    if (
        existing.channel_id != route.channel.id
        or existing.title != payload.title.strip()
        or existing.body != payload.body
        or existing.severity != payload.severity
        or existing_expires != requested_expires
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key has already been used for a different notification",
        )


def _replayed_result(
    existing: Notification,
    route: ResolvedRoute,
    payload: NotificationCreate,
) -> NotificationPersistenceResult:
    _assert_idempotent_payload_matches(existing, route, payload)
    return NotificationPersistenceResult(notification=existing, replayed=True)


def persist_notification_idempotent(
    session: Session,
    route: ResolvedRoute,
    payload: NotificationCreate,
    *,
    idempotency_key: str | None,
) -> NotificationPersistenceResult:
    digest = _idempotency_digest(idempotency_key) if idempotency_key is not None else None
    if digest is not None:
        existing = _existing_idempotent_notification(session, route, digest)
        if existing is not None:
            return _replayed_result(existing, route, payload)

    notification = Notification(
        source_id=route.source.id,
        channel_id=route.channel.id,
        title=payload.title.strip(),
        body=payload.body,
        severity=payload.severity,
        expires_at=payload.expires_at,
        idempotency_digest=digest,
    )
    session.add(notification)
    try:
        session.flush()
    except IntegrityError:
        # A concurrent request with the same source-scoped key may have won the
        # unique constraint. Roll back our failed transaction and converge on
        # the already-persisted notification instead of producing a duplicate.
        session.rollback()
        if digest is not None:
            existing = _existing_idempotent_notification(session, route, digest)
            if existing is not None:
                return _replayed_result(existing, route, payload)
        raise

    fanout_notification(session, notification)
    session.commit()
    session.refresh(notification)
    return NotificationPersistenceResult(notification=notification, replayed=False)


def persist_notification(
    session: Session,
    route: ResolvedRoute,
    payload: NotificationCreate,
) -> Notification:
    """Persist legacy/non-idempotent ingestion paths without changing behavior."""
    return persist_notification_idempotent(
        session,
        route,
        payload,
        idempotency_key=None,
    ).notification


def to_read(notification: Notification, route: ResolvedRoute) -> NotificationRead:
    return NotificationRead(
        id=notification.id,
        source=route.source.slug,
        channel=route.channel.slug,
        title=notification.title,
        body=notification.body,
        severity=notification.severity,
        created_at=as_utc(notification.created_at),
        expires_at=as_utc(notification.expires_at) if notification.expires_at is not None else None,
    )


def _history_query(principal: TokenPrincipal) -> Select[tuple[Notification, Source, Channel]]:
    return (
        select(Notification, Source, Channel)
        .join(Source, Notification.source_id == Source.id)
        .join(Channel, Notification.channel_id == Channel.id)
        .where(Source.service_identity_id == principal.service_identity_id)
    )


def list_notifications(
    session: Session,
    principal: TokenPrincipal,
    *,
    source_slug: str | None = None,
    channel_slug: str | None = None,
    severity: str | None = None,
    before_id: int | None = None,
    limit: int = 50,
) -> list[NotificationRead]:
    statement = _history_query(principal)
    if source_slug is not None:
        statement = statement.where(Source.slug == source_slug)
    if channel_slug is not None:
        statement = statement.where(Channel.slug == channel_slug)
    if severity is not None:
        statement = statement.where(Notification.severity == severity)
    if before_id is not None:
        statement = statement.where(Notification.id < before_id)

    rows = session.execute(statement.order_by(Notification.id.desc()).limit(limit)).all()
    return [
        to_read(notification, ResolvedRoute(source=source, channel=channel))
        for notification, source, channel in rows
    ]


def get_notification(
    session: Session,
    principal: TokenPrincipal,
    notification_id: int,
) -> NotificationRead:
    row = session.execute(
        _history_query(principal).where(Notification.id == notification_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")

    notification, source, channel = row
    return to_read(notification, ResolvedRoute(source=source, channel=channel))
