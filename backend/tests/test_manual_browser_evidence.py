from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "deploy" / "acceptance" / "validate_manual_browser_evidence.py"
CONTRACT_PATH = ROOT / "deploy" / "acceptance" / "manual_browser_os_acceptance.json"
SPEC = importlib.util.spec_from_file_location("manual_browser_evidence", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

REVISION = "0123456789abcdef0123456789abcdef01234567"


def valid_evidence() -> dict[str, object]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    session_id = "firefox-zorin-desktop-01"
    return {
        "schema_version": 1,
        "evidence_kind": "goreecloud-notify-manual-browser-os-acceptance",
        "sanitized": True,
        "captured_at": "2026-08-18T21:45:00-05:00",
        "candidate": {
            "service_url": "https://notify-rc.goreecloud.com",
            "build_revision": REVISION,
            "release_stage": "release_candidate",
            "production_accepted": False,
            "acceptance_status": "pending",
        },
        "sessions": [
            {
                "id": session_id,
                "captured_at": "2026-08-18T21:30:00-05:00",
                "browser_name": "Firefox",
                "browser_version": "153.0.4",
                "operating_system": "Zorin OS",
                "operating_system_version": "17.3 Pro",
                "device_class": "desktop-laptop",
                "viewport_css_pixels": {"width": 1366, "height": 768},
                "screen_reader": {"name": "Orca", "version": "47.0"},
                "service_url": "https://notify-rc.goreecloud.com",
                "build_revision": REVISION,
            }
        ],
        "checks": [
            {
                "id": check["id"],
                "session_id": session_id,
                "status": "pass",
                "evidence": f"Manually verified {check['id']} with synthetic acceptance data.",
                "defect_issue_url": None,
            }
            for check in contract["required_checks"]
        ],
        "privacy": {
            "synthetic_test_data_only": True,
            "raw_notification_content_recorded": False,
            "reusable_secrets_recorded": False,
            "screenshots_sanitized_or_not_retained": True,
        },
    }


def find_check(evidence: dict[str, object], check_id: str) -> dict[str, object]:
    for result in evidence["checks"]:  # type: ignore[index]
        if result["id"] == check_id:
            return result
    raise AssertionError(f"missing test check {check_id}")


def test_valid_complete_manual_browser_evidence_passes() -> None:
    validator.validate_evidence(valid_evidence(), REVISION)


def test_expected_revision_must_match_candidate_and_sessions() -> None:
    evidence = valid_evidence()
    other_revision = "89abcdef0123456789abcdef0123456789abcdef"

    with pytest.raises(validator.EvidenceValidationError, match="expected deployed revision"):
        validator.validate_evidence(evidence, other_revision)


def test_missing_required_manual_check_fails_closed() -> None:
    evidence = valid_evidence()
    evidence["checks"] = evidence["checks"][:-1]  # type: ignore[index]

    with pytest.raises(validator.EvidenceValidationError, match="incomplete"):
        validator.validate_evidence(evidence, REVISION)


def test_failed_check_requires_dedicated_defect_and_still_blocks_acceptance() -> None:
    evidence = valid_evidence()
    result = find_check(evidence, "appearance.auto_mode")
    result["status"] = "fail"

    with pytest.raises(validator.EvidenceValidationError, match="dedicated issue"):
        validator.validate_evidence(evidence, REVISION)

    result["defect_issue_url"] = "https://github.com/GoreeCloud/goreecloud-notify/issues/99"
    with pytest.raises(validator.EvidenceValidationError, match="failed checks"):
        validator.validate_evidence(evidence, REVISION)


def test_screen_reader_results_must_reference_real_screen_reader_session() -> None:
    evidence = valid_evidence()
    evidence["sessions"][0]["screen_reader"] = {"name": None, "version": None}  # type: ignore[index]

    with pytest.raises(validator.EvidenceValidationError, match="actual screen reader"):
        validator.validate_evidence(evidence, REVISION)


def test_session_metadata_must_be_concrete_and_candidate_bound() -> None:
    evidence = valid_evidence()
    evidence["sessions"][0]["browser_version"] = "TBD"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="concrete recorded value"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["sessions"][0]["service_url"] = "https://other.goreecloud.com"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="candidate.service_url"):
        validator.validate_evidence(evidence, REVISION)


def test_candidate_url_must_be_https_without_query_or_credentials() -> None:
    evidence = valid_evidence()
    evidence["candidate"]["service_url"] = "http://notify-rc.goreecloud.com"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="absolute HTTPS URL"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["candidate"]["service_url"] = "https://notify-rc.goreecloud.com/?key=example"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="query parameters"):
        validator.validate_evidence(evidence, REVISION)


def test_privacy_contract_and_sensitive_fields_fail_closed() -> None:
    evidence = valid_evidence()
    evidence["privacy"]["raw_notification_content_recorded"] = True  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="must be False"):
        validator.validate_evidence(evidence, REVISION)

    sensitive = copy.deepcopy(valid_evidence())
    sensitive["candidate"]["api_token"] = "synthetic-do-not-store"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="prohibited sensitive-data field"):
        validator.validate_evidence(sensitive, REVISION)
