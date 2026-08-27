from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs" / "glaze-ui-1.4-gates.json"


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_glaze_1_4_gate_ledger_is_complete_and_fail_closed() -> None:
    ledger = _ledger()
    assert ledger["application"] == "goreecloud-notify"
    assert ledger["target_release"] == "1.4.0"
    assert len(ledger["gates"]) == 21
    assert ledger["conformance_claim"] is False
    assert ledger["stable_eligible"] is False
    assert ledger["gates"]["20_visual_acceptance"]["status"] == "pending"
    assert ledger["gates"]["21_stability_and_lifecycle"]["status"] == "pending"


def test_glaze_1_4_gate_evidence_paths_exist() -> None:
    for gate in _ledger()["gates"].values():
        for relative_path in gate.get("evidence", []):
            assert (ROOT / relative_path).exists(), relative_path


def test_glaze_1_4_manual_acceptance_is_preserved() -> None:
    ledger = _ledger()
    assert "manual-acceptance-required" in ledger["gates"]["08_accessibility"]["status"]
    assert "manual-acceptance-required" in ledger["gates"]["10_form_factor_fidelity"]["status"]
    assert "20_visual_acceptance" in ledger["blocking_gates"]
    assert "21_stability_and_lifecycle" in ledger["blocking_gates"]
    assert "do not constitute completed conformance" in ledger["acceptance_boundary"]
