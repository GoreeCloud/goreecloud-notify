from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.datastructures import MutableHeaders

LOGGER = logging.getLogger("goreecloud.notify")

REQUEST_ID_HEADER = "X-Request-ID"
WARDVEIL_HEADER = "X-Wardveil-Security"
WARDVEIL_STATUS = "Protected by Wardveil"

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._:-]{0,62}[A-Za-z0-9])?$")
_QUIET_SUCCESS_PATHS = frozenset({"/healthz"})


def _header_value(scope: dict[str, Any], name: bytes) -> str | None:
    for key, value in scope.get("headers", ()):
        if key.lower() != name:
            continue
        try:
            return value.decode("ascii")
        except UnicodeDecodeError:
            return None
    return None


def _request_id(scope: dict[str, Any]) -> str:
    supplied = _header_value(scope, b"x-request-id")
    if supplied and _REQUEST_ID_PATTERN.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


def _route_label(scope: dict[str, Any]) -> str:
    route = scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return "<unmatched>"


def _json_event(**fields: object) -> str:
    return json.dumps(fields, separators=(",", ":"), sort_keys=True)


def _should_log_success(path: str) -> bool:
    return path not in _QUIET_SUCCESS_PATHS and not path.startswith("/assets/")


class RequestObservabilityMiddleware:
    """Privacy-minimized request correlation and structured operational logging.

    The middleware intentionally excludes query strings, request/response bodies, cookies,
    authorization headers, CSRF values, client IP addresses, and user-agent strings. Security
    and authentication audit state remains owned by the dedicated application security paths.
    """

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = time.perf_counter()
        request_id = _request_id(scope)
        method = scope.get("method", "")
        request_path = scope.get("path", "")
        response_started = False

        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        async def send_observed(message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
                headers[WARDVEIL_HEADER] = WARDVEIL_STATUS

                status_code = int(message["status"])
                if status_code >= 400 or _should_log_success(request_path):
                    LOGGER.info(
                        _json_event(
                            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
                            event="http_request",
                            method=method,
                            request_id=request_id,
                            route=_route_label(scope),
                            service="GoreeCloud Notify",
                            status=status_code,
                        )
                    )
            await send(message)

        try:
            await self.app(scope, receive, send_observed)
        except Exception as exc:
            LOGGER.error(
                _json_event(
                    duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
                    error_type=type(exc).__name__,
                    event="http_request_error",
                    method=method,
                    request_id=request_id,
                    route=_route_label(scope),
                    service="GoreeCloud Notify",
                    status=500,
                )
            )
            if response_started:
                raise

            body = json.dumps(
                {"detail": "Internal server error", "request_id": request_id},
                separators=(",", ":"),
            ).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"cache-control", b"no-store"),
                        (REQUEST_ID_HEADER.lower().encode("ascii"), request_id.encode("ascii")),
                        (WARDVEIL_HEADER.lower().encode("ascii"), WARDVEIL_STATUS.encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
