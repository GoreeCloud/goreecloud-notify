from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..deps import get_db
from ..retention_service import build_retention_preview
from ..schemas import RetentionPreviewRead
from ..security import require_admin

router = APIRouter(
    prefix="/admin/retention",
    tags=["administration"],
    dependencies=[Depends(require_admin)],
)


@router.get("/preview", response_model=RetentionPreviewRead)
def retention_preview(
    cutoff: Annotated[
        datetime,
        Query(description="Explicit UTC cutoff; candidates use notification.created_at < cutoff"),
    ],
    session: Annotated[Session, Depends(get_db)],
) -> RetentionPreviewRead:
    if cutoff.tzinfo is None or cutoff.utcoffset() != timedelta(0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="cutoff must include an explicit UTC offset (Z or +00:00)",
        )

    cutoff = cutoff.astimezone(timezone.utc)
    preview = build_retention_preview(session, cutoff)
    return RetentionPreviewRead(
        mode="preview_only",
        cutoff=cutoff,
        cutoff_basis="notification_created_at_before_cutoff",
        destructive_action_enabled=False,
        candidate_notifications=preview.candidate_notifications,
        candidate_deliveries=preview.candidate_deliveries,
        candidate_read_deliveries=preview.candidate_read_deliveries,
        candidate_unread_deliveries=preview.candidate_unread_deliveries,
        candidate_acknowledged_deliveries=preview.candidate_acknowledged_deliveries,
        candidate_unacknowledged_deliveries=preview.candidate_unacknowledged_deliveries,
        candidate_explicitly_expired_notifications=(
            preview.candidate_explicitly_expired_notifications
        ),
        oldest_candidate_created_at=preview.oldest_candidate_created_at,
        newest_candidate_created_at=preview.newest_candidate_created_at,
    )
