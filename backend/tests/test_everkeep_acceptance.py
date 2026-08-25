from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _json(path: str) -> dict:
    return json.loads((REPOSITORY_ROOT / path).read_text(encoding="utf-8"))


def test_everkeep_policy_covers_every_declared_dimension() -> None:
    policy = _json("docs/everkeep.acceptance.json")
    adoption = _json("docs/everkeep.adoption.json")
    assert policy["application"] == "goreecloud-notify"
    assert policy["producer"] == "GoreeCloud/goreecloud-notify"
    assert set(adoption["dimensions"]) == set(policy["required_ready_evidence"])


def test_everkeep_policy_fails_closed() -> None:
    policy = _json("docs/everkeep.acceptance.json")
    failure = policy["failure_behavior"]
    assert failure["producer_unavailable"] == "unknown"
    assert failure["malformed_evidence"] == "unknown"
    assert failure["missing_required_evidence"] == "unknown"
    assert failure["failed_restore_validation"] == "degraded"
    assert "never be more favorable" in failure["summary_rule"]


def test_everkeep_freshness_is_required_for_ready() -> None:
    freshness = _json("docs/everkeep.acceptance.json")["freshness"]
    assert freshness["required_for_ready"] is True
    assert "fresh_until" in freshness["rule"]
    assert "unknown" in freshness["rule"]


def test_everkeep_backup_and_restore_are_distinct() -> None:
    ready = _json("docs/everkeep.acceptance.json")["required_ready_evidence"]
    assert "artifact integrity was verified" in ready["backup_coverage"]
    assert "restore was tested" in ready["restore_capability"]
    assert "restored Notify state was verified" in ready["restore_capability"]


def test_everkeep_sensitive_evidence_is_forbidden() -> None:
    forbidden = set(_json("docs/everkeep.acceptance.json")["sensitive_evidence"]["forbidden"])
    assert {"passwords", "tokens", "recovery codes", "private keys", "secret values"} <= forbidden


def test_everkeep_source_policy_does_not_claim_acceptance() -> None:
    acceptance = _json("docs/everkeep.acceptance.json")["acceptance"]
    assert acceptance["everkeep_integrated"] is False
    assert acceptance["everkeep_ready"] is False
    assert acceptance["target_runtime_acceptance_required"] is True
    assert acceptance["exact_revision_acceptance_required"] is True
