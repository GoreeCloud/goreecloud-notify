from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

ASGIApp = Callable[[dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[None]]

# Small control-plane requests do not need large bodies. Native notification
# ingestion receives the widest allowance because NotificationCreate.body supports
# 20,000 Unicode characters; common JSON encoders can expand non-ASCII input.
DEFAULT_MAX_REQUEST_BODY_BYTES = 64 * 1024
NATIVE_NOTIFICATION_MAX_REQUEST_BODY_BYTES = 256 * 1024
NTFY_COMPAT_MAX_REQUEST_BODY_BYTES = 8 * 1024
BODY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
NTFY_COMPAT_TOPIC_PATH = re.compile(r"^/[-_A-Za-z0-9]{1,64}$")


def request_body_limit(scope: dict[str, Any]) -> int:
    path = str(scope.get("path", "")).rstrip("/") or "/"
    if path.startswith("/compat/ntfy/") or NTFY_COMPAT_TOPIC_PATH.fullmatch(path):
        return NTFY_COMPAT_MAX_REQUEST_BODY_BYTES
    if path == "/api/v1/notifications":
        return NATIVE_NOTIFICATION_MAX_REQUEST_BODY_BYTES
    return DEFAULT_MAX_REQUEST_BODY_BYTES


def _declared_content_length(scope: dict[str, Any]) -> int | None:
    for name, value in scope.get("headers", []):
        if bytes(name).lower() != b"content-length":
            continue
        try:
            length = int(bytes(value).decode("ascii"))
        except (UnicodeDecodeError, ValueError):
            return None
        return length if length >= 0 else None
    return None


async def _send_too_large(send: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
    body = json.dumps(
        {"detail": "Request body exceeds the allowed size."},
        separators=(",", ":"),
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})


class RequestBodyLimitMiddleware:
    """Bound request bodies before FastAPI/Starlette parses them.

    The middleware buffers only body-bearing mutation requests, caps memory before
    request parsing, and replays the bounded ASGI messages unchanged to the
    application. GET/SSE and other read requests bypass the buffer entirely.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope.get("type") != "http" or str(scope.get("method", "GET")).upper() not in BODY_METHODS:
            await self.app(scope, receive, send)
            return

        limit = request_body_limit(scope)
        declared_length = _declared_content_length(scope)
        if declared_length is not None and declared_length > limit:
            await _send_too_large(send)
            return

        buffered: list[dict[str, Any]] = []
        total = 0
        while True:
            message = await receive()
            buffered.append(message)

            message_type = message.get("type")
            if message_type == "http.request":
                body = message.get("body", b"")
                if not isinstance(body, bytes):
                    body = bytes(body)
                total += len(body)
                if total > limit:
                    await _send_too_large(send)
                    return
                if not message.get("more_body", False):
                    break
            elif message_type == "http.disconnect":
                break

        index = 0

        async def replay_receive() -> dict[str, Any]:
            nonlocal index
            if index < len(buffered):
                message = buffered[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)
