from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "wardveil.adoption.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_wardveil_adoption_identity_and_fail_closed_state() -> None:
    manifest = _manifest()
    assert manifest["schema_version"] == 1
    assert manifest["project"] == "GoreeCloud Notify"
    assert manifest["repository"] == "GoreeCloud/goreecloud-notify"
    assert manifest["identity"] == "Wardveil Security by GoreeCloud"
    assert manifest["presentation_claim"] == "Protected by Wardveil"
    assert manifest["source_status"] == "draft-application-adoption-candidate"
    assert manifest["fail_closed"] is True
    assert manifest["unknown_when_evidence_missing"] is True


def test_wardveil_claims_have_explicit_scope_producer_and_evidence() -> None:
    controls = _manifest()["authoritative_controls"]
    assert controls
    for control in controls:
        assert control["scope"]
        assert control["producer"]
        evidence = ROOT / control["evidence"]
        assert evidence.is_file(), control["evidence"]


def test_wardveil_does_not_claim_unowned_security_authority() -> None:
    excluded = set(_manifest()["excluded_authority"])
    assert {"firewall", "vpn", "backup", "vulnerability-management"} <= excluded


def test_wardveil_adoption_remains_unapproved_until_target_acceptance() -> None:
    acceptance = _manifest()["acceptance"]
    assert acceptance["exact_revision_ci_required"] is True
    assert acceptance["target_runtime_acceptance_required"] is True
    assert acceptance["production_approved"] is False


def test_security_policy_preserves_accessible_text_identity_and_evidence_boundary() -> None:
    policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "Wardveil Security by GoreeCloud" in policy
    assert "Protected by Wardveil" in policy
    assert "presentation metadata only" in policy
    assert "not proof" in policy
