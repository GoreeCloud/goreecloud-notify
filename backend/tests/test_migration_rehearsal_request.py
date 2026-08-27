from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "docs" / "migration-rehearsal-request.json"


def load_request() -> dict:
    return json.loads(REQUEST.read_text(encoding="utf-8"))


def test_request_is_bound_to_reviewed_migration_ready_base() -> None:
    request = load_request()
    assert request["schema"] == "goreecloud-notify-migration-rehearsal-request/v1"
    assert request["reviewed_base_revision"] == "c41928209f4274c480d9cd2377bc25c7a0e1a8d7"
    assert request["requested_mode"] == "same-candidate-parallel-acceptance"


def test_rehearsal_request_cannot_authorize_live_migration_cutover_or_retirement() -> None:
    request = load_request()
    authority = request["authority"]
    authorizations = request["authorizations"]
    assert authority["current_production_notification_service"] == "ntfy"
    assert authority["ntfy_must_remain_active"] is True
    assert authorizations["rehearsal_preparation"] is True
    assert authorizations["sanitized_evidence_collection"] is True
    assert authorizations["isolated_candidate_validation"] is True
    assert authorizations["live_producer_migration"] is False
    assert authorizations["production_cutover"] is False
    assert authorizations["ntfy_retirement"] is False


def test_required_acceptance_evidence_stays_explicit() -> None:
    evidence = set(load_request()["required_session_evidence"])
    for required in {
        "exact-candidate-git-revision",
        "exact-candidate-target-runtime-private-publication-evidence",
        "exact-candidate-backup-restore-and-security-reconciliation",
        "live-monitoring-and-independent-notify-down-alert-path",
        "manual-browser-os-accessibility-acceptance",
        "physical-android-background-delivery-and-production-signed-install-acceptance",
        "representative-monitor-producer-runtime-delivery",
        "coherent-pre-cutover-acceptance-bundle-with-rollback-exercised",
        "fresh-pre-cutover-recovery-point",
    }:
        assert required in evidence
