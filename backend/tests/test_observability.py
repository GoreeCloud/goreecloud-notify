import json
import logging
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app
from app.observability import (
    LOGGER,
    REQUEST_ID_HEADER,
    WARDVEIL_HEADER,
    WARDVEIL_STATUS,
    RequestObservabilityMiddleware,
)


_GENERATED_REQUEST_ID = re.compile(r"^[0-9a-f]{32}$")


def test_request_correlation_and_wardveil_status_are_returned() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta")

    assert response.status_code == 200
    assert _GENERATED_REQUEST_ID.fullmatch(response.headers[REQUEST_ID_HEADER])
    assert response.headers[WARDVEIL_HEADER] == WARDVEIL_STATUS
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["origin-agent-cluster"] == "?1"
    assert response.headers["x-permitted-cross-domain-policies"] == "none"

    payload = response.json()
    assert payload["security_identity"] == {
        "name": "Wardveil Security",
        "full_presentation": "Wardveil Security by GoreeCloud",
        "protection_status": "Protected by Wardveil",
        "authority": "GoreeCloud Notify application security controls remain authoritative",
    }
    assert payload["observability"] == {
        "request_correlation_header": "X-Request-ID",
        "structured_http_events": True,
        "sensitive_request_data_logged": False,
    }


def test_valid_caller_request_id_is_preserved() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta", headers={REQUEST_ID_HEADER: "client-request-123"})

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "client-request-123"


def test_invalid_caller_request_id_is_replaced() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta", headers={REQUEST_ID_HEADER: "invalid request id"})

    assert response.status_code == 200
    request_id = response.headers[REQUEST_ID_HEADER]
    assert request_id != "invalid request id"
    assert _GENERATED_REQUEST_ID.fullmatch(request_id)


def test_structured_http_log_minimizes_sensitive_request_data(caplog) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER.name)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/meta?token=query-secret",
            headers={
                "Authorization": "Bearer authorization-secret",
                "Cookie": "session=cookie-secret",
                "User-Agent": "sensitive-user-agent",
            },
        )

    assert response.status_code == 200
    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == LOGGER.name and record.getMessage().startswith("{")
    ]
    request_event = next(event for event in events if event.get("event") == "http_request")

    assert request_event["method"] == "GET"
    assert request_event["route"] == "/api/v1/meta"
    assert request_event["status"] == 200
    assert request_event["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert "duration_ms" in request_event

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "query-secret" not in log_text
    assert "authorization-secret" not in log_text
    assert "cookie-secret" not in log_text
    assert "sensitive-user-agent" not in log_text


def test_unhandled_error_is_generic_correlated_and_secret_safe(caplog) -> None:
    isolated_app = FastAPI()
    isolated_app.add_middleware(RequestObservabilityMiddleware)

    @isolated_app.get("/explode")
    def explode() -> None:
        raise RuntimeError("sensitive exception detail")

    caplog.set_level(logging.ERROR, logger=LOGGER.name)
    with TestClient(isolated_app, raise_server_exceptions=False) as client:
        response = client.get("/explode")

    assert response.status_code == 500
    request_id = response.headers[REQUEST_ID_HEADER]
    assert _GENERATED_REQUEST_ID.fullmatch(request_id)
    assert response.headers[WARDVEIL_HEADER] == WARDVEIL_STATUS
    assert response.json() == {"detail": "Internal server error", "request_id": request_id}
    assert "sensitive exception detail" not in response.text

    error_events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == LOGGER.name and record.getMessage().startswith("{")
    ]
    error_event = next(event for event in error_events if event.get("event") == "http_request_error")
    assert error_event["route"] == "/explode"
    assert error_event["error_type"] == "RuntimeError"
    assert error_event["request_id"] == request_id
    assert "sensitive exception detail" not in "\n".join(record.getMessage() for record in caplog.records)
