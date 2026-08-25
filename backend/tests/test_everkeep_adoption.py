from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "docs" / "everkeep.adoption.json"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_everkeep_adoption_identity_and_fail_closed_contract() -> None:
    manifest = _manifest()
    assert manifest["schema_version"] == 1
    assert manifest["project"] == "GoreeCloud Notify"
    assert manifest["repository"] == "GoreeCloud/goreecloud-notify"
    assert manifest["role"] == "producer"
    assert manifest["read_only"] is True
    assert manifest["fail_closed"] is True
    assert manifest["status_schema"] == "contracts/continuity.status.schema.json"


def test_everkeep_dimensions_are_limited_to_source_backed_continuity() -> None:
    assert set(_manifest()["dimensions"]) == {
        "backup_coverage",
        "restore_capability",
        "migration",
        "documentation",
        "provenance",
    }


def test_everkeep_authoritative_sources_exist() -> None:
    sources = _manifest()["authoritative_sources"]
    assert sources
    for relative_path in sources:
        assert (REPOSITORY_ROOT / relative_path).exists(), relative_path


def test_everkeep_manifest_does_not_claim_ready_state() -> None:
    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8").lower()
    assert '"ready": true' not in manifest_text
    assert "target-native restore/recovery evidence" in manifest_text
    assert "exact-revision acceptance" in manifest_text
