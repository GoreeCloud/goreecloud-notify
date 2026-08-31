from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from ..deps import get_db
from ..notification_service import (
    get_notification,
    list_notifications,
    persist_notification_idempotent,
    resolve_route,
    to_read,
)
from ..schemas import NotificationCreate, NotificationRead
from ..security import TokenPrincipal, require_scope

router = APIRouter(tags=["notifications"])
Severity = Literal["info", "normal", "warning", "error", "critical"]


@router.post(
    "/notifications",
    response_model=NotificationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_notification(
    payload: NotificationCreate,
    response: Response,
    principal: Annotated[TokenPrincipal, Depends(require_scope("notifications:write"))],
    session: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=1, max_length=512),
    ] = None,
) -> NotificationRead:
    route = resolve_route(
        session,
        principal,
        source_slug=payload.source,
        channel_slug=payload.channel,
    )
    persisted = persist_notification_idempotent(
        session,
        route,
        payload,
        idempotency_key=idempotency_key,
    )
    if persisted.replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotency-Replayed"] = "true"
    return to_read(persisted.notification, route)


@router.get("/notifications", response_model=list[NotificationRead])
def notification_history(
    principal: Annotated[TokenPrincipal, Depends(require_scope("notifications:read"))],
    session: Annotated[Session, Depends(get_db)],
    source: str | None = Query(default=None, min_length=1, max_length=120),
    channel: str | None = Query(default=None, min_length=1, max_length=120),
    severity: Severity | None = None,
    before_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[NotificationRead]:
    return list_notifications(
        session,
        principal,
        source_slug=source,
        channel_slug=channel,
        severity=severity,
        before_id=before_id,
        limit=limit,
    )


@router.get("/notifications/{notification_id}", response_model=NotificationRead)
def notification_detail(
    notification_id: int,
    principal: Annotated[TokenPrincipal, Depends(require_scope("notifications:read"))],
    session: Annotated[Session, Depends(get_db)],
) -> NotificationRead:
    return get_notification(session, principal, notification_id)
