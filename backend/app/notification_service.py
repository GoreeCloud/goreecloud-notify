from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
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
