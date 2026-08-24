from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _adapter() -> dict:
    return json.loads((REPOSITORY_ROOT / "docs/privacy-shield.adapter.json").read_text(encoding="utf-8"))


def test_notify_privacy_shield_adapter_identity_is_explicit() -> None:
    adapter = _adapter()
    assert adapter["schema_version"] == 1
    assert adapter["adapter"] == {
        "id": "notify-application-privacy",
        "product": "GoreeCloud Notify",
        "runtime_authority": "GoreeCloud/goreecloud-notify",
        "contract_version": 1,
    }


def test_notify_claims_only_source_backed_privacy_capabilities() -> None:
    assert set(_adapter()["capabilities"]) == {"data-minimization", "deletion-controls"}
    for unsupported in (
        "content-blocking",
        "tracking-resistance",
        "url-cleaning",
        "dns-privacy",
        "network-privacy",
        "telemetry-minimization",
        "retention-controls",
        "portable-export",
        "privacy-status",
        "user-visible-exceptions",
    ):
        assert unsupported not in _adapter()["capabilities"]


def test_notify_adapter_preserves_local_first_status_safe_boundary() -> None:
    privacy = _adapter()["privacy"]
    assert privacy["local_first"] is True
    assert privacy["raw_private_activity_exported_for_status"] is False
    assert privacy["remote_tracker_learning"] is False
    assert privacy["remote_tracker_telemetry"] is False


def test_notify_adapter_is_not_production_approved() -> None:
    acceptance = _adapter()["acceptance"]
    assert acceptance["runtime_acceptance_required"] is True
    assert acceptance["production_approved"] is False


def test_claimed_capabilities_have_delivery_isolation_and_deletion_evidence() -> None:
    delivery_service = (REPOSITORY_ROOT / "backend/app/delivery_service.py").read_text(encoding="utf-8")
    deletion_tests = (REPOSITORY_ROOT / "backend/tests/test_inbox_delete.py").read_text(encoding="utf-8")
    assert "user_id" in delivery_service
    assert "delete_inbox_delivery" in delivery_service
    assert "removes_only_callers_delivery" in deletion_tests
    assert "cross_user_inbox_delete_is_hidden" in deletion_tests
