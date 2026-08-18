from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "deploy" / "monitoring" / "notify_uptime_kuma_monitor.json"
VALIDATOR_PATH = ROOT / "deploy" / "monitoring" / "validate_target_evidence.py"


def test_target_acceptance_contract_is_bound_to_fail_closed_validator() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    target = contract["target_acceptance_evidence"]

    assert VALIDATOR_PATH.is_file()
    assert target == {
        "validator": "deploy/monitoring/validate_target_evidence.py",
        "evidence_kind": "goreecloud-notify-monitoring-target-acceptance",
        "sanitized_evidence_only": True,
        "concrete_retry_timeout_values_required": True,
        "notification_assignment_required": True,
        "observed_caddy_source_required": True,
        "administrator_down_and_recovered_receipt_required": True,
        "ntfy_monitor_preservation_required": True,
        "rollback_documentation_required": True,
        "independent_out_of_band_notify_down_test_required": True,
    }
