from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..deps import get_db
from ..notification_service import persist_notification, resolve_route, to_read
from ..schemas import NotificationCreate, NotificationRead
from ..security import TokenPrincipal, require_scope

router = APIRouter(tags=["notifications"])


@router.post(
    "/notifications",
    response_model=NotificationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_notification(
    payload: NotificationCreate,
    principal: Annotated[TokenPrincipal, Depends(require_scope("notifications:write"))],
    session: Annotated[Session, Depends(get_db)],
) -> NotificationRead:
    route = resolve_route(
        session,
        principal,
        source_slug=payload.source,
        channel_slug=payload.channel,
    )
    notification = persist_notification(session, route, payload)
    return to_read(notification, route)
