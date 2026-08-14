from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from .models import Channel, Notification, Source
from .schemas import NotificationCreate, NotificationRead
from .security import TokenPrincipal


@dataclass(frozen=True, slots=True)
class ResolvedRoute:
    source: Source
    channel: Channel


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


def persist_notification(
    session: Session,
    route: ResolvedRoute,
    payload: NotificationCreate,
) -> Notification:
    notification = Notification(
        source_id=route.source.id,
        channel_id=route.channel.id,
        title=payload.title.strip(),
        body=payload.body,
        severity=payload.severity,
        expires_at=payload.expires_at,
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


def to_read(notification: Notification, route: ResolvedRoute) -> NotificationRead:
    return NotificationRead(
        id=notification.id,
        source=route.source.slug,
        channel=route.channel.slug,
        title=notification.title,
        body=notification.body,
        severity=notification.severity,
        created_at=notification.created_at,
        expires_at=notification.expires_at,
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
