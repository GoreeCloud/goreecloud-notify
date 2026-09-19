from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "deploy" / "monitoring" / "notify_monitoring_contract.json"
HISTORICAL_CONTRACT_PATH = ROOT / "deploy" / "monitoring" / "notify_uptime_kuma_monitor.json"
VALIDATOR_PATH = ROOT / "deploy" / "monitoring" / "validate_target_evidence.py"


def test_target_acceptance_contract_is_bound_to_fail_closed_validator() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    target = contract["target_acceptance_evidence"]

    assert VALIDATOR_PATH.is_file()
    assert target == {
        "validator": "deploy/monitoring/validate_target_evidence.py",
        "evidence_schema_version": 3,
        "evidence_kind": "goreecloud-notify-monitoring-target-acceptance",
        "sanitized_evidence_only": True,
        "exact_candidate_revision_required": True,
        "exact_monitor_revision_required": True,
        "concrete_retry_timeout_values_required": True,
        "final_private_https_route_required": True,
        "administrator_down_and_recovered_receipt_required": True,
        "rollback_documentation_required": True,
        "independent_out_of_band_notify_down_test_required": True,
    }


def test_post_retirement_monitoring_authority_is_explicit() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["primary_monitor_platform"] == "GoreeCloud Monitor"
    assert contract["monitor"]["monitor_provider_must_be_production_accepted"] is True
    assert contract["outage_alerting"]["notify_down_delivery_must_not_depend_on_notify"] is True
    assert contract["outage_alerting"]["must_use_separate_failure_domain"] is True
    assert contract["outage_alerting"]["must_not_depend_on_same_runtime_host"] is True
    assert contract["historical_predecessors"]["active_dependency"] is False
    assert contract["historical_predecessors"]["production_rollback_target"] is False


def test_uptime_kuma_contract_is_historical_only() -> None:
    historical = json.loads(HISTORICAL_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert historical["status"] == "historical-retired-predecessor-contract"
    assert historical["superseded_by"] == "deploy/monitoring/notify_monitoring_contract.json"
    assert historical["production_authority"] is False
    assert historical["production_rollback_target"] is False
