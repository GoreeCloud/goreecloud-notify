from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs" / "glaze-ui-v1.5.1-adoption.json"


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_notify_requires_current_glaze_v1_5_1_without_claiming_adoption() -> None:
    ledger = _ledger()
    assert ledger["application"] == "goreecloud-notify"
    assert ledger["required_target_release"] == "1.5.1"
    assert ledger["current_source_mapping_release"] == "1.3.0"
    assert ledger["canonical_repository"] == "GoreeCloud/goreecloud-glaze-ui"
    assert ledger["reviewed_implementation_anchor"] == "ee1032a0822ab8e103f8afe48e5c1859fde65cc9"
    assert ledger["source_qualification_anchor"] == "5b59d0e36950d737dba35b58ae58058684e0831b"
    assert ledger["adoption_status"] == "adoption-required"
    assert ledger["conformance_claim"] is False
    assert ledger["production_eligible"] is False


def test_current_glaze_ledger_preserves_required_supported_surfaces() -> None:
    assert set(_ledger()["supported_surfaces"]) == {"web", "flutter-linux", "flutter-android"}


def test_current_glaze_ledger_is_fail_closed_on_missing_acceptance() -> None:
    ledger = _ledger()
    assert "representative-application-performance-budget" in ledger["required_acceptance"]
    assert "governed-consumer-registry-acceptance" in ledger["required_acceptance"]
    assert "exact-revision-production-approval" in ledger["required_acceptance"]
    assert ledger["blockers"]


def test_historical_v1_3_ledger_is_explicitly_superseded() -> None:
    historical = json.loads(
        (ROOT / "docs" / "glaze-ui-v1.3-adoption.json").read_text(encoding="utf-8")
    )
    assert historical["adoption_status"] == "historical-source-mapping-superseded"
    assert historical["superseded_by"] == "docs/glaze-ui-v1.5.1-adoption.json"
    assert historical["stable_eligible"] is False
