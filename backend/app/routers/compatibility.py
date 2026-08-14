from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Channel, Source
from ..notification_service import ResolvedRoute, persist_notification, to_read
from ..schemas import NotificationCreate
from ..security import TokenPrincipal, require_scope

router = APIRouter(tags=["ntfy compatibility"])

MAX_COMPAT_MESSAGE_BYTES = 4096

PRIORITY_MAP = {
    "1": ("info", 1),
    "min": ("info", 1),
    "2": ("info", 2),
    "low": ("info", 2),
    "3": ("normal", 3),
    "default": ("normal", 3),
    "4": ("warning", 4),
    "high": ("warning", 4),
    "5": ("critical", 5),
    "max": ("critical", 5),
    "urgent": ("critical", 5),
}

HEADER_ALIASES = {
    "message": ("x-message", "message", "m"),
    "title": ("x-title", "title", "t"),
    "priority": ("x-priority", "priority", "prio", "p"),
}
QUERY_ALIASES = {
    "message": ("message", "m"),
    "title": ("title", "t"),
    "priority": ("priority", "prio", "p"),
}
UNSUPPORTED_HEADERS = {
    "x-tags", "tags", "tag", "ta",
    "x-actions", "actions", "action",
    "x-click", "click",
    "x-attach", "attach", "a",
    "x-markdown", "markdown", "md",
    "x-icon", "icon",
    "x-filename", "filename", "file", "f",
    "x-delay", "delay", "x-at", "at", "x-in", "in",
    "x-email", "x-e-mail", "email", "e-mail", "mail", "e",
    "x-call", "call",
    "x-cache", "cache",
    "x-firebase", "firebase",
    "x-unifiedpush", "unifiedpush", "up",
    "x-poll-id", "poll-id",
}
UNSUPPORTED_QUERY = {
    "tags", "tag", "ta", "actions", "action", "click", "attach", "a",
    "markdown", "md", "icon", "filename", "file", "f", "delay", "at", "in",
    "email", "e-mail", "mail", "e", "call", "cache", "firebase", "unifiedpush", "up",
    "poll-id",
}


class NtfyCompatibilityResponse(BaseModel):
    id: str
    time: int
    event: Literal["message"] = "message"
    topic: str
    message: str
    title: str
    priority: int


def _first_header(request: Request, aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        value = request.headers.get(alias)
        if value is not None:
            return value
    return None


def _first_query(request: Request, aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        value = request.query_params.get(alias)
        if value is not None:
            return value
    return None


def _compat_value(request: Request, field: str) -> str | None:
    return _first_header(request, HEADER_ALIASES[field]) or _first_query(request, QUERY_ALIASES[field])


def _reject_unsupported_options(request: Request) -> None:
    used_headers = sorted(name for name in UNSUPPORTED_HEADERS if request.headers.get(name) is not None)
    used_query = sorted(name for name in UNSUPPORTED_QUERY if name in request.query_params)
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() == "text/markdown":
        used_headers.append("content-type:text/markdown")
    if used_headers or used_query:
        options = used_headers + used_query
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"unsupported ntfy compatibility option(s): {', '.join(options)}",
        )


def _priority(value: str | None) -> tuple[str, int]:
    normalized = (value or "3").strip().lower()
    mapped = PRIORITY_MAP.get(normalized)
    if mapped is None:
        raise HTTPException(status_code=400, detail="invalid ntfy priority")
    return mapped


def _resolve_compat_route(
    session: Session,
    principal: TokenPrincipal,
    topic: str,
) -> ResolvedRoute:
    channel = session.scalar(select(Channel).where(Channel.slug == topic))
    if channel is None:
        raise HTTPException(status_code=404, detail="topic is not an approved channel")

    sources = session.scalars(
        select(Source)
        .where(Source.service_identity_id == principal.service_identity_id)
        .order_by(Source.id)
    ).all()
    if not sources:
        raise HTTPException(status_code=404, detail="producer source is not configured")

    exact = next((source for source in sources if source.slug == topic), None)
    if exact is not None:
        return ResolvedRoute(source=exact, channel=channel)

    short_topic = topic.removeprefix("goreecloud-")
    short = next((source for source in sources if source.slug == short_topic), None)
    if short is not None:
        return ResolvedRoute(source=short, channel=channel)

    if len(sources) == 1:
        return ResolvedRoute(source=sources[0], channel=channel)

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="topic cannot be mapped unambiguously to a producer source; use the native API",
    )


@router.api_route(
    "/{topic}",
    methods=["POST", "PUT"],
    response_model=NtfyCompatibilityResponse,
    status_code=status.HTTP_200_OK,
)
async def publish_ntfy_compatible(
    request: Request,
    topic: Annotated[str, Path(pattern=r"^[-_A-Za-z0-9]{1,64}$")],
    principal: Annotated[TokenPrincipal, Depends(require_scope("notifications:write"))],
    session: Annotated[Session, Depends(get_db)],
) -> NtfyCompatibilityResponse:
    _reject_unsupported_options(request)

    body_bytes = await request.body()
    header_or_query_message = _compat_value(request, "message")
    if header_or_query_message is None:
        try:
            message = body_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="message body must be UTF-8") from exc
    else:
        message = header_or_query_message

    message = message if message else "triggered"
    if len(message.encode("utf-8")) > MAX_COMPAT_MESSAGE_BYTES:
        raise HTTPException(status_code=413, detail="message exceeds the 4 KiB compatibility limit")

    title = (_compat_value(request, "title") or topic).strip()
    if not title:
        title = topic
    if len(title) > 300:
        raise HTTPException(status_code=422, detail="title exceeds 300 characters")

    severity, priority = _priority(_compat_value(request, "priority"))
    route = _resolve_compat_route(session, principal, topic)
    payload = NotificationCreate(
        source=route.source.slug,
        channel=route.channel.slug,
        title=title,
        body=message,
        severity=severity,
    )
    notification = persist_notification(session, route, payload)
    result = to_read(notification, route)

    created_at: datetime = result.created_at
    return NtfyCompatibilityResponse(
        id=f"gcn-{result.id}",
        time=int(created_at.timestamp()),
        topic=topic,
        message=result.body,
        title=result.title,
        priority=priority,
    )
