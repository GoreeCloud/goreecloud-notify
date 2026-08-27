from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPOSITORY_ROOT / "docs" / "platform-conformance.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_platform_conformance_contract_is_fail_closed() -> None:
    contract = _contract()
    assert contract["application"] == "goreecloud-notify"
    assert contract["stable_eligible"] is False
    assert set(contract["platform_systems"]) == {
        "glaze_ui",
        "wardveil_security",
        "privacy_shield",
        "everkeep",
    }
    assert contract["platform_systems"]["glaze_ui"]["required_version"] == "1.4"


def test_platform_conformance_uses_canonical_identities() -> None:
    systems = _contract()["platform_systems"]
    assert systems["glaze_ui"]["identity"] == "Glaze UI"
    assert systems["wardveil_security"]["identity"] == "Wardveil Security by GoreeCloud"
    assert systems["privacy_shield"]["identity"] == "GoreeCloud Privacy Shield"
    assert systems["everkeep"]["identity"] == "Everkeep"


def test_platform_conformance_evidence_paths_exist() -> None:
    for system in _contract()["platform_systems"].values():
        evidence = system.get("evidence", [])
        assert evidence
        for relative_path in evidence:
            assert (REPOSITORY_ROOT / relative_path).exists(), relative_path


def test_incomplete_platform_contracts_cannot_be_represented_as_complete() -> None:
    contract = _contract()
    systems = contract["platform_systems"]
    assert systems["wardveil_security"]["source_status"] == "draft-application-adoption-candidate"
    wardveil_acceptance = json.loads(
        (REPOSITORY_ROOT / "docs" / "wardveil.adoption.json").read_text(encoding="utf-8")
    )["acceptance"]
    assert wardveil_acceptance["target_runtime_acceptance_required"] is True
    assert wardveil_acceptance["production_approved"] is False
    assert systems["privacy_shield"]["source_status"] == "draft-adapter-source-candidate"
    privacy_acceptance = json.loads(
        (REPOSITORY_ROOT / "docs" / "privacy-shield.adapter.json").read_text(encoding="utf-8")
    )["acceptance"]
    assert privacy_acceptance["runtime_acceptance_required"] is True
    assert privacy_acceptance["production_approved"] is False
    assert systems["everkeep"]["source_status"] == "draft-acceptance-policy-candidate"
    everkeep_adoption = json.loads(
        (REPOSITORY_ROOT / "docs" / "everkeep.adoption.json").read_text(encoding="utf-8")
    )
    assert everkeep_adoption["fail_closed"] is True
    assert everkeep_adoption["read_only"] is True
    everkeep_acceptance = json.loads(
        (REPOSITORY_ROOT / "docs" / "everkeep.acceptance.json").read_text(encoding="utf-8")
    )["acceptance"]
    assert everkeep_acceptance["everkeep_integrated"] is False
    assert everkeep_acceptance["everkeep_ready"] is False
    assert everkeep_acceptance["target_runtime_acceptance_required"] is True
    assert everkeep_acceptance["exact_revision_acceptance_required"] is True
    assert contract["stable_eligible"] is False
    assert contract["production_blockers"]
