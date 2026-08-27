from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs" / "migration-readiness.json"


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_source_is_ready_for_rehearsal_without_authorizing_live_migration() -> None:
    contract = load_contract()
    assert contract["schema"] == "goreecloud-notify-migration-readiness/v1"
    readiness = contract["readiness"]
    assert readiness["source_ready_for_migration_rehearsal"] is True
    assert readiness["live_producer_migration_authorized"] is False
    assert readiness["production_cutover_authorized"] is False
    assert readiness["stable_eligible"] is False
    assert contract["authority"]["current_production_notification_service"] == "ntfy"


def test_required_source_evidence_exists() -> None:
    contract = load_contract()
    for relative_path in contract["required_source_evidence"]:
        assert (ROOT / relative_path).is_file(), relative_path


def test_live_migration_gates_remain_explicit() -> None:
    gates = set(load_contract()["pre_live_migration_gates"])
    assert "physical-android-background-delivery-and-production-signed-install-acceptance" in gates
    assert "live-monitoring-and-independent-notify-down-alert-path" in gates
    assert "representative-monitor-producer-runtime-delivery" in gates
    assert "coherent-pre-cutover-acceptance-bundle-with-rollback-exercised" in gates
    assert "fresh-pre-cutover-recovery-point" in gates
    assert "explicit-live-producer-migration-approval" in gates
