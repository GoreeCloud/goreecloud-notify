from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs" / "integrations" / "monitor-producer.json"


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_monitor_producer_contract_is_narrow_and_fail_closed() -> None:
    contract = load_contract()

    assert contract["schema_version"] == 2
    assert contract["producer"] == {
        "id": "goreecloud-monitor",
        "repository": "GoreeCloud/goreecloud-monitor",
        "source_slug": "goreecloud-monitor",
        "channel_slug": "monitoring",
    }
    assert contract["notify_contract"] == {
        "endpoint": "/api/v1/notifications",
        "method": "POST",
        "required_scope": "notifications:write",
        "authentication": "notify-producer-token",
        "transport": "https",
        "idempotency_header": "Idempotency-Key",
        "idempotency_scope": "source",
        "first_write_status": 201,
        "exact_replay_status": 200,
        "replay_response_header": "Idempotency-Replayed",
        "conflicting_reuse_status": 409,
        "raw_idempotency_key_persisted": False,
    }
    assert contract["producer_replay_identity"] == {
        "required": True,
        "version": "gcm-v1",
        "inputs": ["event-type", "stable-transition-id"],
        "presentation_fields_excluded": [
            "monitor-display-label",
            "minimized-transition-summary",
        ],
        "wire_value": "sha256-derived-opaque-key",
    }
    assert contract["events"] == {
        "DOWN": "critical",
        "RECOVERED": "normal",
        "DEGRADED": "warning",
        "TLS_EXPIRING": "warning",
        "HEARTBEAT_MISSED": "error",
    }

    acceptance = contract["acceptance"]
    assert acceptance["runtime_acceptance_required"] is True
    assert acceptance["representative_transition_validation_required"] is True
    assert acceptance["representative_retry_validation_required"] is True
    assert acceptance["conflicting_replay_validation_required"] is True
    assert acceptance["rollback_to_existing_notification_path_required"] is True
    assert acceptance["production_approved"] is False


def test_monitor_producer_contract_excludes_sensitive_and_authority_broadening() -> None:
    contract = load_contract()
    forbidden = set(contract["privacy"]["forbidden_content"])
    assert {
        "target-url",
        "target-ip-address",
        "raw-diagnostics",
        "stack-trace",
        "producer-token",
        "credentials",
        "private-monitoring-configuration",
        "recovery-secret",
        "raw-transition-id",
    } <= forbidden
    assert contract["privacy"]["notify_idempotency_storage"] == "sha256-digest-only"

    delivery = contract["delivery"]
    assert delivery["notify_is_authoritative_for_delivery"] is True
    assert delivery["monitor_is_authoritative_for_monitoring_state"] is True
    assert delivery["publication_success_is_not_health_evidence"] is True
    assert delivery["notify_must_not_be_sole_outage_alert_path_for_notify"] is True
    assert delivery["exact_retries_must_not_duplicate_delivery_fanout"] is True
