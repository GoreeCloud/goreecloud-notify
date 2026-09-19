from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "deploy" / "monitoring" / "validate_target_evidence.py"
CONTRACT_PATH = ROOT / "deploy" / "monitoring" / "notify_monitoring_contract.json"
HISTORICAL_CONTRACT_PATH = ROOT / "deploy" / "monitoring" / "notify_uptime_kuma_monitor.json"
SPEC = importlib.util.spec_from_file_location("notify_target_evidence", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

REVISION = "0123456789abcdef0123456789abcdef01234567"
MONITOR_REVISION = "89abcdef0123456789abcdef0123456789abcdef"


def valid_evidence() -> dict[str, object]:
    return {
        "schema_version": 3,
        "evidence_kind": "goreecloud-notify-monitoring-target-acceptance",
        "sanitized": True,
        "captured_at": "2026-09-18T23:58:00Z",
        "candidate": {
            "service_url": "https://notify.goreecloud.com",
            "build_revision": REVISION,
            "release_stage": "release_candidate",
            "production_accepted": False,
            "acceptance_status": "pending",
        },
        "monitor_provider": {
            "provider": "GoreeCloud Monitor",
            "provider_build_revision": MONITOR_REVISION,
            "provider_production_accepted": True,
            "monitor_id": "notify-health",
            "monitor_name": "GoreeCloud Notify",
            "type": "http",
            "url": "https://notify.goreecloud.com/healthz",
            "method": "GET",
            "active": True,
            "interval_seconds": 60,
            "max_retries": 2,
            "retry_interval_seconds": 30,
            "request_timeout_seconds": 20,
            "accepted_status_codes": [200],
            "tls_verification_enabled": True,
            "observed_at_gateway": True,
            "observed_remote_address": "100.71.27.119",
            "gateway_allowlist_values": ["100.64.0.0/10"],
            "final_private_https_route_verified": True,
            "backend_socket_only": False,
            "database_aware_health_verified": True,
        },
        "state_transitions": {
            "healthy_no_false_alert": True,
            "down_detected": True,
            "down_observed_status_code": 502,
            "recovered_detected": True,
            "recovered_observed_status_code": 200,
            "observed_order": ["DOWN", "RECOVERED"],
        },
        "administrator_receipt": {
            "recipient_approved": True,
            "down_received": True,
            "recovered_received": True,
            "content_minimized": True,
        },
        "rollback": {
            "procedure_recorded": True,
            "monitor_disable_or_remove_documented": True,
            "previous_notify_release_recovery_documented": True,
            "uptime_kuma_production_restore_required": False,
        },
        "independent_out_of_band": {
            "mechanism": "separate-provider email alert",
            "separate_failure_domain": True,
            "depends_on_notify": False,
            "depends_on_same_runtime_host": False,
            "controlled_notify_outage_tested": True,
            "approved_administrator_received_down": True,
        },
    }


def test_source_monitor_contract_is_post_retirement_and_revision_bound() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["schema_version"] == 3
    assert contract["primary_monitor_platform"] == "GoreeCloud Monitor"
    assert contract["historical_predecessors"]["active_dependency"] is False
    assert contract["historical_predecessors"]["production_rollback_target"] is False
    assert contract["target_acceptance_evidence"]["evidence_schema_version"] == 3
    assert contract["target_acceptance_evidence"]["exact_candidate_revision_required"] is True
    assert contract["target_acceptance_evidence"]["exact_monitor_revision_required"] is True


def test_old_uptime_kuma_contract_is_historical_only() -> None:
    historical = json.loads(HISTORICAL_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert historical["status"] == "historical-retired-predecessor-contract"
    assert historical["superseded_by"] == "deploy/monitoring/notify_monitoring_contract.json"
    assert historical["production_authority"] is False
    assert historical["production_rollback_target"] is False


def test_valid_target_monitoring_evidence_passes() -> None:
    validator.validate_evidence(valid_evidence(), REVISION)


def test_notify_candidate_revision_must_match_expected_revision() -> None:
    evidence = valid_evidence()
    other_revision = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    with pytest.raises(validator.EvidenceValidationError, match="expected deployed revision"):
        validator.validate_evidence(evidence, other_revision)


def test_monitor_provider_requires_exact_revision_and_production_acceptance() -> None:
    evidence = valid_evidence()
    evidence["monitor_provider"]["provider_build_revision"] = "development"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="exact 40-character"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["monitor_provider"]["provider_production_accepted"] = False  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="provider_production_accepted"):
        validator.validate_evidence(evidence, REVISION)


def test_retired_provider_cannot_be_substituted() -> None:
    evidence = valid_evidence()
    evidence["monitor_provider"]["provider"] = "Uptime Kuma"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="GoreeCloud Monitor"):
        validator.validate_evidence(evidence, REVISION)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("monitor_provider", "tls_verification_enabled", False),
        ("monitor_provider", "backend_socket_only", True),
        ("monitor_provider", "final_private_https_route_verified", False),
        ("administrator_receipt", "down_received", False),
        ("rollback", "uptime_kuma_production_restore_required", True),
        ("independent_out_of_band", "separate_failure_domain", False),
        ("independent_out_of_band", "depends_on_notify", True),
        ("independent_out_of_band", "depends_on_same_runtime_host", True),
        ("independent_out_of_band", "controlled_notify_outage_tested", False),
    ],
)
def test_incomplete_or_unsafe_target_evidence_fails(
    section: str,
    field: str,
    value: object,
) -> None:
    evidence = valid_evidence()
    evidence[section][field] = value  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError):
        validator.validate_evidence(evidence, REVISION)


def test_observed_monitor_source_must_be_authorized_by_gateway_allowlist() -> None:
    evidence = valid_evidence()
    evidence["monitor_provider"]["gateway_allowlist_values"] = ["10.0.0.0/8"]  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="must authorize the observed"):
        validator.validate_evidence(evidence, REVISION)


def test_placeholder_and_sensitive_evidence_fields_fail_closed() -> None:
    placeholder = valid_evidence()
    placeholder["independent_out_of_band"]["mechanism"] = "TBD"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="concrete recorded value"):
        validator.validate_evidence(placeholder, REVISION)

    sensitive = copy.deepcopy(valid_evidence())
    sensitive["monitor_provider"]["authorization_header"] = "Bearer synthetic"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="prohibited sensitive-data field"):
        validator.validate_evidence(sensitive, REVISION)
