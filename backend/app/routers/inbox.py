from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..delivery_service import (
    acknowledge_delivery,
    get_inbox_delivery,
    list_inbox,
    mark_delivery_read,
    mark_delivery_unread,
)
from ..deps import get_db
from ..schemas import InboxDeliveryRead
from ..user_security import UserPrincipal, require_csrf_user_session, require_user_session

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
    q: str | None = Query(default=None, min_length=1, max_length=200),
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
        search_text=q,
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


@router.post("/inbox/{delivery_id}/read", response_model=InboxDeliveryRead)
def mark_read(
    delivery_id: int,
    principal: Annotated[UserPrincipal, Depends(require_csrf_user_session)],
    session: Annotated[Session, Depends(get_db)],
) -> InboxDeliveryRead:
    return mark_delivery_read(session, principal, delivery_id)


@router.delete("/inbox/{delivery_id}/read", response_model=InboxDeliveryRead)
def mark_unread(
    delivery_id: int,
    principal: Annotated[UserPrincipal, Depends(require_csrf_user_session)],
    session: Annotated[Session, Depends(get_db)],
) -> InboxDeliveryRead:
    return mark_delivery_unread(session, principal, delivery_id)


@router.post("/inbox/{delivery_id}/acknowledge", response_model=InboxDeliveryRead)
def acknowledge(
    delivery_id: int,
    principal: Annotated[UserPrincipal, Depends(require_csrf_user_session)],
    session: Annotated[Session, Depends(get_db)],
) -> InboxDeliveryRead:
    return acknowledge_delivery(session, principal, delivery_id)
