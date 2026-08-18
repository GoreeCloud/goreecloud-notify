from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "deploy" / "acceptance" / "validate_pre_cutover_acceptance.py"
SPEC = importlib.util.spec_from_file_location("pre_cutover_acceptance", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

REVISION = "0123456789abcdef0123456789abcdef01234567"
BASE_URL = "https://notify.goreecloud.com"


def _load_test_helper(filename: str, module_name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict[str, object]) -> str:
    payload = json.dumps(value, indent=2, sort_keys=True).encode()
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _valid_artifacts(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    backup_helper = _load_test_helper("test_backup_target_evidence.py", "aggregate_backup_test_helper")
    monitoring_helper = _load_test_helper("test_monitoring_target_evidence.py", "aggregate_monitoring_test_helper")
    manual_helper = _load_test_helper("test_manual_browser_evidence.py", "aggregate_manual_test_helper")

    backup = backup_helper.valid_evidence()
    backup["candidate"]["service_url"] = BASE_URL
    monitoring = monitoring_helper.valid_evidence()
    manual = manual_helper.valid_evidence()
    manual["candidate"]["service_url"] = BASE_URL
    for session in manual["sessions"]:
        session["service_url"] = BASE_URL

    preflight = {
        "schema": "goreecloud-notify-target-preflight-v2",
        "generated_at": "2026-08-18T22:55:00-05:00",
        "scope": "all",
        "base_url": BASE_URL,
        "expected_revision": REVISION,
        "container": "goreecloud-notify",
        "data_dir": "/srv/docker/appdata/goreecloud-notify",
        "env_file": "/srv/docker/stacks/goreecloud-notify/.env",
        "result": "pass",
        "checks": [
            {"name": "host-data-dir", "status": "pass", "detail": "Target data path validated."},
            {"name": "network-meta", "status": "pass", "detail": "Private HTTPS metadata contract validated."},
        ],
        "limitations": ["This report does not perform manual browser acceptance or cutover."],
    }

    values = {
        "backup_restore": backup,
        "monitoring": monitoring,
        "target_preflight": preflight,
        "manual_browser_os": manual,
    }
    evidence_files: dict[str, dict[str, str]] = {}
    for name, value in values.items():
        path = tmp_path / f"{name}.json"
        digest = _write_json(path, value)
        evidence_files[name] = {"path": path.name, "sha256": digest}

    manifest = {
        "schema_version": 1,
        "manifest_kind": "goreecloud-notify-pre-cutover-acceptance",
        "sanitized": True,
        "captured_at": "2026-08-18T23:00:00-05:00",
        "candidate": {
            "service_url": BASE_URL,
            "build_revision": REVISION,
            "release_stage": "release_candidate",
            "production_accepted": False,
            "acceptance_status": "pending",
        },
        "evidence_files": evidence_files,
        "migration_rollback": {
            "phase": "pre_cutover_ready",
            "recorded_at": "2026-08-18T22:58:00-05:00",
            "ntfy_active": True,
            "ntfy_retired": False,
            "parallel_producer_validation_passed": True,
            "parallel_consumer_validation_passed": True,
            "authorization_validation_passed": True,
            "rollback_exercised": True,
            "rollback_procedure_recorded": True,
            "cutover_performed": False,
            "evidence_summary": "Synthetic test record representing completed pre-cutover producer, consumer, authorization, and rollback validation while ntfy remains active.",
        },
        "privacy": {
            "sanitized": True,
            "raw_notification_content_recorded": False,
            "reusable_secrets_recorded": False,
            "embedded_evidence_files": False,
        },
    }
    manifest_path = tmp_path / "acceptance.json"
    _write_json(manifest_path, manifest)
    return manifest_path, manifest


def test_complete_same_candidate_acceptance_set_passes(tmp_path: Path) -> None:
    manifest_path, manifest = _valid_artifacts(tmp_path)
    validator.validate_manifest(manifest, manifest_path, REVISION)


def test_aggregate_candidate_revision_must_match_explicit_revision(tmp_path: Path) -> None:
    manifest_path, manifest = _valid_artifacts(tmp_path)
    other = "89abcdef0123456789abcdef0123456789abcdef"
    with pytest.raises(validator.AcceptanceValidationError, match="--expected-revision"):
        validator.validate_manifest(manifest, manifest_path, other)


def test_subordinate_evidence_revision_skew_fails_even_with_updated_digest(tmp_path: Path) -> None:
    manifest_path, manifest = _valid_artifacts(tmp_path)
    monitoring_path = tmp_path / manifest["evidence_files"]["monitoring"]["path"]
    monitoring = json.loads(monitoring_path.read_text())
    monitoring["candidate"]["build_revision"] = "89abcdef0123456789abcdef0123456789abcdef"
    manifest["evidence_files"]["monitoring"]["sha256"] = _write_json(monitoring_path, monitoring)

    with pytest.raises(validator.AcceptanceValidationError, match="candidate revision"):
        validator.validate_manifest(manifest, manifest_path, REVISION)


def test_evidence_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    manifest_path, manifest = _valid_artifacts(tmp_path)
    manifest["evidence_files"]["backup_restore"]["sha256"] = "b" * 64

    with pytest.raises(validator.AcceptanceValidationError, match="does not match"):
        validator.validate_manifest(manifest, manifest_path, REVISION)


def test_target_preflight_must_be_all_scope_pass_for_same_candidate(tmp_path: Path) -> None:
    manifest_path, manifest = _valid_artifacts(tmp_path)
    preflight_path = tmp_path / manifest["evidence_files"]["target_preflight"]["path"]
    preflight = json.loads(preflight_path.read_text())
    preflight["scope"] = "network"
    manifest["evidence_files"]["target_preflight"]["sha256"] = _write_json(preflight_path, preflight)

    with pytest.raises(validator.AcceptanceValidationError, match="scope"):
        validator.validate_manifest(manifest, manifest_path, REVISION)


def test_each_gate_must_reference_a_distinct_artifact(tmp_path: Path) -> None:
    manifest_path, manifest = _valid_artifacts(tmp_path)
    manifest["evidence_files"]["manual_browser_os"] = copy.deepcopy(manifest["evidence_files"]["monitoring"])

    with pytest.raises(validator.AcceptanceValidationError, match="distinct evidence artifact"):
        validator.validate_manifest(manifest, manifest_path, REVISION)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ntfy_active", False),
        ("ntfy_retired", True),
        ("parallel_producer_validation_passed", False),
        ("parallel_consumer_validation_passed", False),
        ("authorization_validation_passed", False),
        ("rollback_exercised", False),
        ("rollback_procedure_recorded", False),
        ("cutover_performed", True),
    ],
)
def test_pre_cutover_migration_and_rollback_contract_fails_closed(
    tmp_path: Path, field: str, value: object
) -> None:
    manifest_path, manifest = _valid_artifacts(tmp_path)
    manifest["migration_rollback"][field] = value

    with pytest.raises(validator.AcceptanceValidationError):
        validator.validate_manifest(manifest, manifest_path, REVISION)


def test_sensitive_manifest_fields_are_rejected(tmp_path: Path) -> None:
    manifest_path, manifest = _valid_artifacts(tmp_path)
    manifest["migration_rollback"]["token_value"] = "do-not-store"

    with pytest.raises(validator.AcceptanceValidationError, match="prohibited sensitive-data field"):
        validator.validate_manifest(manifest, manifest_path, REVISION)
