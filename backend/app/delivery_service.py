from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from .models import Channel, Delivery, Notification, Source, Subscription, User
from .schemas import InboxDeliveryRead
from .user_security import UserPrincipal


def fanout_notification(session: Session, notification: Notification) -> int:
    """Create missing per-user Delivery rows for enabled subscriptions.

    The caller owns the surrounding transaction. This function intentionally does
    not commit so notification persistence and initial fanout can succeed or fail
    as one unit.
    """
    if notification.id is None or notification.channel_id is None:
        return 0

    subscribed_user_ids = session.scalars(
        select(User.id)
        .join(Subscription, Subscription.user_id == User.id)
        .where(
            Subscription.channel_id == notification.channel_id,
            Subscription.enabled.is_(True),
            User.is_active.is_(True),
        )
        .order_by(User.id)
    ).all()
    if not subscribed_user_ids:
        return 0

    existing_user_ids = set(
        session.scalars(
            select(Delivery.user_id).where(
                Delivery.notification_id == notification.id,
                Delivery.user_id.in_(subscribed_user_ids),
            )
        ).all()
    )

    created = 0
    for user_id in subscribed_user_ids:
        if user_id in existing_user_ids:
            continue
        session.add(Delivery(notification_id=notification.id, user_id=user_id))
        created += 1

    if created:
        session.flush()
    return created


def _inbox_query(user_id: int) -> Select[tuple[Delivery, Notification, Source, Channel]]:
    return (
        select(Delivery, Notification, Source, Channel)
        .join(Notification, Delivery.notification_id == Notification.id)
        .join(Source, Notification.source_id == Source.id)
        .join(Channel, Notification.channel_id == Channel.id)
        .where(Delivery.user_id == user_id)
    )


def _to_inbox_read(
    delivery: Delivery,
    notification: Notification,
    source: Source,
    channel: Channel,
) -> InboxDeliveryRead:
    return InboxDeliveryRead(
        id=delivery.id,
        notification_id=notification.id,
        source=source.slug,
        channel=channel.slug,
        title=notification.title,
        body=notification.body,
        severity=notification.severity,
        notification_created_at=notification.created_at,
        delivered_at=delivery.created_at,
        expires_at=notification.expires_at,
        read_at=delivery.read_at,
        acknowledged_at=delivery.acknowledged_at,
    )


def list_inbox(
    session: Session,
    principal: UserPrincipal,
    *,
    is_read: bool | None = None,
    is_acknowledged: bool | None = None,
    source_slug: str | None = None,
    channel_slug: str | None = None,
    severity: str | None = None,
    before_id: int | None = None,
    limit: int = 50,
) -> list[InboxDeliveryRead]:
    statement = _inbox_query(principal.user_id)
    if is_read is True:
        statement = statement.where(Delivery.read_at.is_not(None))
    elif is_read is False:
        statement = statement.where(Delivery.read_at.is_(None))
    if is_acknowledged is True:
        statement = statement.where(Delivery.acknowledged_at.is_not(None))
    elif is_acknowledged is False:
        statement = statement.where(Delivery.acknowledged_at.is_(None))
    if source_slug is not None:
        statement = statement.where(Source.slug == source_slug)
    if channel_slug is not None:
        statement = statement.where(Channel.slug == channel_slug)
    if severity is not None:
        statement = statement.where(Notification.severity == severity)
    if before_id is not None:
        statement = statement.where(Delivery.id < before_id)

    rows = session.execute(statement.order_by(Delivery.id.desc()).limit(limit)).all()
    return [_to_inbox_read(*row) for row in rows]


def get_inbox_delivery(
    session: Session,
    principal: UserPrincipal,
    delivery_id: int,
) -> InboxDeliveryRead:
    row = session.execute(
        _inbox_query(principal.user_id).where(Delivery.id == delivery_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="delivery not found")
    return _to_inbox_read(*row)
