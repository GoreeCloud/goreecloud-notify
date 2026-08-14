from __future__ import annotations

import asyncio
import json
import time
from typing import Annotated, AsyncIterator, Literal

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..delivery_service import (
    acknowledge_delivery,
    get_inbox_delivery,
    latest_inbox_delivery_id,
    list_inbox,
    list_inbox_after,
    mark_delivery_read,
    mark_delivery_unread,
)
from ..deps import get_db
from ..schemas import InboxDeliveryRead
from ..user_security import (
    UserPrincipal,
    principal_session_is_active,
    require_csrf_user_session,
    require_user_session,
)

router = APIRouter(tags=["inbox"])
Severity = Literal["info", "normal", "warning", "error", "critical"]
STREAM_POLL_SECONDS = 1.0
STREAM_HEARTBEAT_SECONDS = 15.0
STREAM_BATCH_LIMIT = 100


def _stream_cursor(after_id: int | None, last_event_id: str | None) -> int | None:
    if last_event_id is None:
        return after_id
    try:
        parsed = int(last_event_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last-Event-ID must be a non-negative integer",
        ) from exc
    if parsed < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last-Event-ID must be a non-negative integer",
        )
    return parsed


def _sse_event(*, event: str, data: dict[str, object], event_id: int | None = None) -> str:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, separators=(',', ':'), ensure_ascii=False)}")
    return "\n".join(lines) + "\n\n"


async def _inbox_event_stream(
    request: Request,
    principal: UserPrincipal,
    initial_cursor: int | None,
) -> AsyncIterator[str]:
    with SessionLocal() as session:
        if not principal_session_is_active(session, principal):
            return
        cursor = (
            initial_cursor
            if initial_cursor is not None
            else latest_inbox_delivery_id(session, principal)
        )

    yield "retry: 3000\n" + _sse_event(event="ready", data={"cursor": cursor})
    last_heartbeat = time.monotonic()

    while True:
        if await request.is_disconnected():
            return

        with SessionLocal() as session:
            if not principal_session_is_active(session, principal):
                return
            deliveries = list_inbox_after(
                session,
                principal,
                after_id=cursor,
                limit=STREAM_BATCH_LIMIT,
            )

        if deliveries:
            for delivery in deliveries:
                cursor = delivery.id
                yield _sse_event(
                    event="inbox",
                    event_id=delivery.id,
                    data=delivery.model_dump(mode="json"),
                )
            last_heartbeat = time.monotonic()
        elif time.monotonic() - last_heartbeat >= STREAM_HEARTBEAT_SECONDS:
            yield ": keepalive\n\n"
            last_heartbeat = time.monotonic()

        await asyncio.sleep(STREAM_POLL_SECONDS)


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


@router.get("/inbox/stream")
async def inbox_stream(
    request: Request,
    raw_token: Annotated[
        str | None,
        Cookie(alias=settings.session_cookie_name),
    ] = None,
    after_id: int | None = Query(default=None, ge=0),
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    cursor = _stream_cursor(after_id, last_event_id)
    # Authenticate in a short-lived session so a request-scoped yield dependency
    # cannot pin a SQLAlchemy Session for the lifetime of the SSE connection.
    with SessionLocal() as auth_session:
        principal = require_user_session(auth_session, raw_token)

    return StreamingResponse(
        _inbox_event_stream(request, principal, cursor),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
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
