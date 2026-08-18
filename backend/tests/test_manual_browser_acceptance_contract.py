from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "deploy" / "acceptance" / "manual_browser_os_acceptance.json"


def test_manual_browser_acceptance_contract_is_bound_to_issue_55() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["schema_version"] == 1
    assert contract["contract_kind"] == "goreecloud-notify-manual-browser-os-acceptance-contract"
    assert contract["state"] == "manual-evidence-required"
    assert contract["issue"] == 55
    assert contract["candidate_contract"] == {
        "release_stage": "release_candidate",
        "production_accepted": False,
        "acceptance_status": "pending",
        "https_required": True,
        "exact_build_revision_required": True,
    }


def test_manual_browser_acceptance_contract_has_unique_required_checks() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    check_ids = [check["id"] for check in contract["required_checks"]]

    assert len(check_ids) == len(set(check_ids))
    assert {
        "keyboard.logout_login_round_trip",
        "screen_reader.status_errors_realtime_mutation_feedback",
        "reflow.zoom_200_percent_no_loss_or_horizontal_overflow",
        "appearance.auto_mode",
        "appearance.light_mode",
        "appearance.dark_mode",
        "filters.sidebar_unread",
        "filters.sidebar_read",
        "realtime.independent_selection",
        "alerts.external_revoke_reconciles_local_state",
        "alerts.os_generic_redacted_content",
        "alerts.reconnect_replay_backlog_no_storm_with_alerts_enabled",
    }.issubset(check_ids)


def test_manual_browser_acceptance_contract_requires_sanitized_synthetic_evidence() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["privacy_contract"] == {
        "synthetic_test_data_only": True,
        "raw_notification_content_recorded": False,
        "reusable_secrets_recorded": False,
        "screenshots_sanitized_or_not_retained": True,
    }
