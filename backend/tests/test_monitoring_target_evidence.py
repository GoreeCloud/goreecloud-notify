from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "deploy" / "monitoring" / "validate_target_evidence.py"
CONTRACT_PATH = ROOT / "deploy" / "monitoring" / "notify_uptime_kuma_monitor.json"
SPEC = importlib.util.spec_from_file_location("notify_target_evidence", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

REVISION = "0123456789abcdef0123456789abcdef01234567"


def valid_evidence() -> dict[str, object]:
    return {
        "schema_version": 2,
        "evidence_kind": "goreecloud-notify-monitoring-target-acceptance",
        "sanitized": True,
        "captured_at": "2026-08-18T20:49:00Z",
        "candidate": {
            "service_url": "https://notify.goreecloud.com",
            "build_revision": REVISION,
            "release_stage": "release_candidate",
            "production_accepted": False,
            "acceptance_status": "pending",
        },
        "notify_monitor": {
            "id": 31,
            "name": "GoreeCloud Notify",
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
            "notification_assignment_identifiers": [1],
        },
        "source_path": {
            "observed_at_caddy": True,
            "observed_remote_address": "172.19.0.50",
            "caddy_allowlist_values": ["100.64.0.0/10", "172.19.0.50/32"],
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
        "ntfy_preservation": {
            "monitor_present": True,
            "monitor_active": True,
            "name": "ntfy",
            "type": "http",
            "url": "http://ntfy:80/v1/health",
            "interval_seconds": 60,
            "max_retries": 3,
            "retry_interval_seconds": 60,
            "request_timeout_seconds": 48,
            "notification_assignment_present": True,
        },
        "rollback": {
            "procedure_recorded": True,
            "ntfy_monitor_state_preserved": True,
            "notify_monitor_removal_or_disable_documented": True,
            "ntfy_route_restore_documented": True,
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


def test_source_monitor_contract_requires_revision_bound_evidence() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["schema_version"] == 2
    assert contract["candidate_contract"] == {
        "service_url": "https://notify.goreecloud.com",
        "release_stage": "release_candidate",
        "production_accepted": False,
        "acceptance_status": "pending",
        "exact_build_revision_required": True,
    }
    assert contract["target_acceptance_evidence"]["evidence_schema_version"] == 2
    assert contract["target_acceptance_evidence"]["exact_candidate_revision_required"] is True


def test_valid_target_monitoring_evidence_passes() -> None:
    validator.validate_evidence(valid_evidence(), REVISION)


def test_candidate_revision_must_match_explicit_expected_revision() -> None:
    evidence = valid_evidence()
    other_revision = "89abcdef0123456789abcdef0123456789abcdef"

    with pytest.raises(validator.EvidenceValidationError, match="expected deployed revision"):
        validator.validate_evidence(evidence, other_revision)

    evidence["candidate"]["build_revision"] = "development"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="exact 40-character"):
        validator.validate_evidence(evidence, REVISION)


def test_candidate_identity_and_acceptance_state_must_match_source_contract() -> None:
    for field, value in (
        ("service_url", "https://notify-old.goreecloud.com"),
        ("release_stage", "production"),
        ("production_accepted", True),
        ("acceptance_status", "accepted"),
    ):
        evidence = valid_evidence()
        evidence["candidate"][field] = value  # type: ignore[index]
        with pytest.raises(validator.EvidenceValidationError, match=f"candidate.{field}"):
            validator.validate_evidence(evidence, REVISION)


def test_legacy_schema_one_monitoring_evidence_is_rejected() -> None:
    evidence = valid_evidence()
    evidence["schema_version"] = 1

    with pytest.raises(validator.EvidenceValidationError, match="schema_version must be 2"):
        validator.validate_evidence(evidence, REVISION)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("notify_monitor", "tls_verification_enabled"), False),
        (("notify_monitor", "notification_assignment_identifiers"), []),
        (("notify_monitor", "request_timeout_seconds"), 0),
        (("source_path", "backend_socket_only"), True),
        (("administrator_receipt", "down_received"), False),
        (("independent_out_of_band", "separate_failure_domain"), False),
        (("independent_out_of_band", "controlled_notify_outage_tested"), False),
        (("ntfy_preservation", "monitor_present"), False),
    ],
)
def test_incomplete_or_unsafe_target_evidence_fails(path: tuple[str, str], value: object) -> None:
    evidence = valid_evidence()
    section, field = path
    evidence[section][field] = value  # type: ignore[index]

    with pytest.raises(validator.EvidenceValidationError):
        validator.validate_evidence(evidence, REVISION)


def test_observed_source_must_be_authorized_by_recorded_caddy_allowlist() -> None:
    evidence = valid_evidence()
    evidence["source_path"]["caddy_allowlist_values"] = ["100.64.0.0/10"]  # type: ignore[index]

    with pytest.raises(validator.EvidenceValidationError, match="must authorize the observed"):
        validator.validate_evidence(evidence, REVISION)


def test_ntfy_monitor_must_match_preserved_documented_baseline() -> None:
    evidence = valid_evidence()
    evidence["ntfy_preservation"]["request_timeout_seconds"] = 12  # type: ignore[index]

    with pytest.raises(validator.EvidenceValidationError, match="documented baseline"):
        validator.validate_evidence(evidence, REVISION)


def test_placeholder_and_sensitive_evidence_fields_fail_closed() -> None:
    placeholder = valid_evidence()
    placeholder["independent_out_of_band"]["mechanism"] = "TBD"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="concrete recorded value"):
        validator.validate_evidence(placeholder, REVISION)

    sensitive = copy.deepcopy(valid_evidence())
    sensitive["notify_monitor"]["authorization_header"] = "Bearer synthetic"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="prohibited sensitive-data field"):
        validator.validate_evidence(sensitive, REVISION)
