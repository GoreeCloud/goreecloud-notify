from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _json(path: str) -> dict:
    return json.loads(_read(path))


def test_notify_targets_exact_glaze_2_1_stable_as_adoption_candidate() -> None:
    ledger = _json("docs/glaze-ui-2.1-adoption.json")
    assert ledger["target_release"] == "2.1.0"
    assert ledger["canonical_repository"] == "GoreeCloud/goreecloud-glaze-ui"
    assert ledger["canonical_release_tag"] == "v2.1.0"
    assert ledger["canonical_revision"] == "c49113eb8b93c267613fdf1bbca1f814495acad7"
    assert ledger["adoption_status"] == "adoption-candidate"
    assert ledger["conformance_claim"] is False
    assert ledger["stable_eligible"] is False


def test_web_contract_implements_2_1_material_and_target_foundation() -> None:
    css = _read("frontend/src/glaze-contract.css")
    main = _read("frontend/src/main.tsx")
    for token in (
        '--glaze-ui-version: "2.1.0"',
        "--glaze-target-min: 48px",
        "--glaze-target-touch-assistance: 56px",
        "--glaze-target-far-view: 56px",
        "--glaze-material-canvas",
        "--glaze-material-surface",
        "--glaze-material-soft-glaze",
        "--glaze-material-glaze",
        "--glaze-material-deep-glaze",
        "--glaze-material-live-glaze",
        "--glaze-material-clarity: balanced",
        "--glaze-density-effective: standard",
    ):
        assert token in css
    assert "dataset.glazeUi = '2.1.0'" in main
    assert "dataset.glazeUiTarget = '2.1.0'" in main
    assert "dataset.glazeUiStatus = 'adoption-candidate'" in main


def test_web_accessibility_resolution_hooks_are_explicit() -> None:
    css = _read("frontend/src/glaze-contract.css")
    for marker in (
        'data-glaze-large-text="true"',
        'data-glaze-touch-assistance="true"',
        'data-glaze-far-view="true"',
        "prefers-reduced-transparency: reduce",
        "prefers-reduced-motion: reduce",
        "prefers-contrast: more",
        "forced-colors: active",
    ):
        assert marker in css


def test_flutter_mapping_uses_2_1_target_floors() -> None:
    dart = _read("client/lib/glaze_theme.dart")
    assert "stableVersion = '2.1.0'" in dart
    assert "targetMin = 48" in dart
    assert "targetTouchAssistance = 56" in dart
    assert "targetFarView = 56" in dart
    for role in ("softGlaze", "glaze", "deepGlaze", "liveGlaze"):
        assert role in dart


def test_glaze_does_not_replace_platform_authorities() -> None:
    authorities = _json("docs/glaze-ui-2.1-adoption.json")["platform_authority"]
    assert authorities == {
        "security": "Wardveil Security",
        "privacy": "Privacy Shield",
        "continuity": "Everkeep",
        "identity": "GoreeCloud Identity",
        "coordination": "GoreeCloud Mesh",
    }


def test_production_readiness_remains_fail_closed() -> None:
    platform = _json("docs/platform-conformance.json")
    ledger = _json("docs/glaze-ui-2.1-adoption.json")
    assert platform["stable_eligible"] is False
    assert "16_web_rendered_visual_excellence" in ledger["blocking_gates"]
    assert "18_flutter_native_accessibility" in ledger["blocking_gates"]
    assert "19_physical_device_acceptance" in ledger["blocking_gates"]
    assert "20_central_consumer_registry" in ledger["blocking_gates"]
