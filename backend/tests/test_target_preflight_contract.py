from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = ROOT / "deploy" / "target" / "preflight.py"
SPEC = importlib.util.spec_from_file_location("notify_target_preflight", PREFLIGHT_PATH)
assert SPEC is not None and SPEC.loader is not None
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


def valid_headers() -> dict[str, str]:
    return {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": preflight.CSP,
        "X-Frame-Options": "DENY",
        "Permissions-Policy": preflight.PERMISSIONS_POLICY,
        "Strict-Transport-Security": preflight.STRICT_TRANSPORT_SECURITY,
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Origin-Agent-Cluster": "?1",
        "X-Permitted-Cross-Domain-Policies": "none",
        preflight.WARDVEIL_HEADER: preflight.WARDVEIL_STATUS,
        preflight.REQUEST_ID_HEADER: "target-preflight-0123456789",
    }


def valid_meta() -> dict[str, object]:
    return {
        "runtime_environment": "production",
        "production": True,
        "production_configuration": True,
        "build_revision": "a" * 40,
        "release_stage": "release_candidate",
        "production_accepted": False,
        "acceptance_status": "pending",
        "acceptance_gates": {
            "backup_restore": "pending",
            "independent_monitoring": "pending",
            "target_runtime_publication": "pending",
            "manual_browser_os": "pending",
        },
        "security_identity": {
            "name": "Wardveil Security",
            "full_presentation": "Wardveil Security by GoreeCloud",
            "protection_status": "Protected by Wardveil",
            "authority": "GoreeCloud Notify application security controls remain authoritative",
        },
        "observability": {
            "request_correlation_header": "X-Request-ID",
            "structured_http_events": True,
            "sensitive_request_data_logged": False,
        },
    }


def test_current_response_security_contract_passes() -> None:
    preflight.response_security_headers(valid_headers())
    preflight.private_headers(
        {
            **valid_headers(),
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        }
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("X-Wardveil-Security", None),
        ("X-Wardveil-Security", "Protected by Something Else"),
        ("X-Request-ID", "bad request id"),
        ("Cross-Origin-Opener-Policy", None),
        ("Cross-Origin-Resource-Policy", "cross-origin"),
        ("Origin-Agent-Cluster", None),
        ("X-Permitted-Cross-Domain-Policies", "all"),
    ],
)
def test_response_security_contract_fails_closed(field: str, value: str | None) -> None:
    headers = valid_headers()
    if value is None:
        headers.pop(field)
    else:
        headers[field] = value

    with pytest.raises(AssertionError):
        preflight.response_security_headers(headers)


def test_current_release_candidate_metadata_passes() -> None:
    preflight.validate_release_meta(valid_meta(), "a" * 40)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("runtime_environment", "development"),
        ("production", False),
        ("production_configuration", False),
        ("release_stage", "production"),
        ("production_accepted", True),
        ("acceptance_status", "accepted"),
    ],
)
def test_release_metadata_cannot_silently_promote_or_weaken_candidate_state(
    field: str,
    value: object,
) -> None:
    meta = valid_meta()
    meta[field] = value

    with pytest.raises(AssertionError):
        preflight.validate_release_meta(meta, "a" * 40)


def test_acceptance_gate_set_must_match_current_source_contract() -> None:
    meta = valid_meta()
    meta["acceptance_gates"] = {
        "backup_restore": "pending",
        "independent_monitoring": "pending",
        "target_runtime_publication": "accepted",
        "manual_browser_os": "pending",
    }

    with pytest.raises(AssertionError, match="acceptance gates"):
        preflight.validate_release_meta(meta, "a" * 40)


def test_wardveil_and_observability_metadata_must_match_current_contract() -> None:
    meta = valid_meta()
    meta["security_identity"] = {
        "name": "Wardveil Security",
        "full_presentation": "Wardveil Security by GoreeCloud",
        "protection_status": "Protected by Wardveil",
        "authority": "",
    }
    with pytest.raises(AssertionError, match="authority"):
        preflight.validate_release_meta(meta, "a" * 40)

    meta = valid_meta()
    meta["observability"] = {
        "request_correlation_header": "X-Trace-ID",
        "structured_http_events": True,
        "sensitive_request_data_logged": False,
    }
    with pytest.raises(AssertionError, match="observability"):
        preflight.validate_release_meta(meta, "a" * 40)


def test_target_preflight_self_test_covers_current_contract(capsys: pytest.CaptureFixture[str]) -> None:
    preflight.self_test()
    captured = capsys.readouterr()
    assert captured.out.strip() == "target preflight self-test passed"


def test_target_identity_and_report_contract_constants_are_current() -> None:
    assert preflight.APP_ICON_PATH == "/brand/goreecloud-notify-icon.svg"
    assert preflight.MANIFEST_PATH == "/manifest.webmanifest"
    assert preflight.CURRENT_RELEASE_STAGE == "release_candidate"
    assert preflight.CURRENT_ACCEPTANCE_STATUS == "pending"
    assert preflight.CURRENT_ACCEPTANCE_GATES == {
        "backup_restore": "pending",
        "independent_monitoring": "pending",
        "target_runtime_publication": "pending",
        "manual_browser_os": "pending",
    }
