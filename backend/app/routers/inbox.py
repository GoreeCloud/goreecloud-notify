from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..delivery_service import get_inbox_delivery, list_inbox
from ..deps import get_db
from ..schemas import InboxDeliveryRead
from ..user_security import UserPrincipal, require_user_session

router = APIRouter(tags=["inbox"])
Severity = Literal["info", "normal", "warning", "error", "critical"]


@router.get("/inbox", response_model=list[InboxDeliveryRead])
def inbox(
    principal: Annotated[UserPrincipal, Depends(require_user_session)],
    session: Annotated[Session, Depends(get_db)],
    read: bool | None = None,
    acknowledged: bool | None = None,
    source: str | None = Query(default=None, min_length=1, max_length=120),
    channel: str | None = Query(default=None, min_length=1, max_length=120),
    severity: Severity | None = None,
    before_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[InboxDeliveryRead]:
    return list_inbox(
        session,
        principal,
        is_read=read,
        is_acknowledged=acknowledged,
        source_slug=source,
        channel_slug=channel,
        severity=severity,
        before_id=before_id,
        limit=limit,
    )


@router.get("/inbox/{delivery_id}", response_model=InboxDeliveryRead)
def inbox_detail(
    delivery_id: int,
    principal: Annotated[UserPrincipal, Depends(require_user_session)],
    session: Annotated[Session, Depends(get_db)],
) -> InboxDeliveryRead:
    return get_inbox_delivery(session, principal, delivery_id)
