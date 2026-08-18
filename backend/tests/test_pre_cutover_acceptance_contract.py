from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "deploy" / "acceptance" / "pre_cutover_acceptance_contract.json"
VALIDATOR_PATH = ROOT / "deploy" / "acceptance" / "validate_pre_cutover_acceptance.py"


def test_pre_cutover_contract_is_source_bound_and_fail_closed() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert VALIDATOR_PATH.is_file()
    assert contract["schema_version"] == 1
    assert contract["contract_kind"] == "goreecloud-notify-pre-cutover-acceptance-contract"
    assert contract["state"] == "evidence-required"
    assert contract["candidate_contract"] == {
        "release_stage": "release_candidate",
        "production_accepted": False,
        "acceptance_status": "pending",
        "exact_build_revision_required": True,
        "https_required": True,
    }

    assert contract["required_evidence"] == {
        "backup_restore": {
            "issue": 23,
            "validator": "deploy/recovery/validate_target_evidence.py",
            "evidence_kind": "goreecloud-notify-target-backup-restore-acceptance",
        },
        "monitoring": {
            "issue": 24,
            "validator": "deploy/monitoring/validate_target_evidence.py",
            "schema_version": 2,
            "evidence_kind": "goreecloud-notify-monitoring-target-acceptance",
        },
        "target_preflight": {
            "issue": 25,
            "schema": "goreecloud-notify-target-preflight-v2",
            "scope": "all",
            "result": "pass",
        },
        "manual_browser_os": {
            "issue": 55,
            "validator": "deploy/acceptance/validate_manual_browser_evidence.py",
            "evidence_kind": "goreecloud-notify-manual-browser-os-acceptance",
        },
    }

    assert contract["migration_rollback_contract"] == {
        "phase": "pre_cutover_ready",
        "ntfy_active_required": True,
        "ntfy_retired": False,
        "parallel_producer_validation_required": True,
        "parallel_consumer_validation_required": True,
        "authorization_validation_required": True,
        "rollback_exercise_required": True,
        "rollback_procedure_recorded_required": True,
        "cutover_performed": False,
    }

    assert contract["privacy_contract"] == {
        "sanitized": True,
        "raw_notification_content_recorded": False,
        "reusable_secrets_recorded": False,
        "embedded_evidence_files": False,
    }
