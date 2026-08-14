from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Delivery, Notification


@dataclass(frozen=True, slots=True)
class RetentionPreview:
    candidate_notifications: int
    candidate_deliveries: int
    candidate_read_deliveries: int
    candidate_unread_deliveries: int
    candidate_acknowledged_deliveries: int
    candidate_unacknowledged_deliveries: int
    candidate_explicitly_expired_notifications: int
    oldest_candidate_created_at: datetime | None
    newest_candidate_created_at: datetime | None


def _count(session: Session, statement) -> int:
    return int(session.scalar(statement) or 0)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_retention_preview(session: Session, cutoff: datetime) -> RetentionPreview:
    candidate_notification_ids = select(Notification.id).where(Notification.created_at < cutoff)
    candidate_delivery_filter = Delivery.notification_id.in_(candidate_notification_ids)

    candidate_notifications = _count(
        session,
        select(func.count()).select_from(Notification).where(Notification.created_at < cutoff),
    )
    candidate_deliveries = _count(
        session,
        select(func.count()).select_from(Delivery).where(candidate_delivery_filter),
    )
    candidate_read_deliveries = _count(
        session,
        select(func.count()).select_from(Delivery).where(
            candidate_delivery_filter,
            Delivery.read_at.is_not(None),
        ),
    )
    candidate_unread_deliveries = _count(
        session,
        select(func.count()).select_from(Delivery).where(
            candidate_delivery_filter,
            Delivery.read_at.is_(None),
        ),
    )
    candidate_acknowledged_deliveries = _count(
        session,
        select(func.count()).select_from(Delivery).where(
            candidate_delivery_filter,
            Delivery.acknowledged_at.is_not(None),
        ),
    )
    candidate_unacknowledged_deliveries = _count(
        session,
        select(func.count()).select_from(Delivery).where(
            candidate_delivery_filter,
            Delivery.acknowledged_at.is_(None),
        ),
    )
    candidate_explicitly_expired_notifications = _count(
        session,
        select(func.count()).select_from(Notification).where(
            Notification.created_at < cutoff,
            Notification.expires_at.is_not(None),
            Notification.expires_at <= cutoff,
        ),
    )
    oldest_created_at, newest_created_at = session.execute(
        select(func.min(Notification.created_at), func.max(Notification.created_at)).where(
            Notification.created_at < cutoff
        )
    ).one()

    return RetentionPreview(
        candidate_notifications=candidate_notifications,
        candidate_deliveries=candidate_deliveries,
        candidate_read_deliveries=candidate_read_deliveries,
        candidate_unread_deliveries=candidate_unread_deliveries,
        candidate_acknowledged_deliveries=candidate_acknowledged_deliveries,
        candidate_unacknowledged_deliveries=candidate_unacknowledged_deliveries,
        candidate_explicitly_expired_notifications=candidate_explicitly_expired_notifications,
        oldest_candidate_created_at=_as_utc(oldest_created_at),
        newest_candidate_created_at=_as_utc(newest_created_at),
    )
