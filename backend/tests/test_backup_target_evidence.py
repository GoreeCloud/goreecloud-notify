from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "deploy" / "recovery" / "validate_target_evidence.py"
CONTRACT_PATH = ROOT / "deploy" / "recovery" / "target_backup_restore_contract.json"
SPEC = importlib.util.spec_from_file_location("backup_target_evidence", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

REVISION = "0123456789abcdef0123456789abcdef01234567"
SHA256 = "a" * 64


def valid_evidence() -> dict[str, object]:
    return {
        "schema_version": 1,
        "evidence_kind": "goreecloud-notify-target-backup-restore-acceptance",
        "sanitized": True,
        "captured_at": "2026-08-18T22:45:00-05:00",
        "candidate": {
            "service_url": "https://notify-rc.goreecloud.com",
            "build_revision": REVISION,
            "release_stage": "release_candidate",
            "production_accepted": False,
            "acceptance_status": "pending",
        },
        "data_path": {
            "database_path": "/srv/docker/appdata/goreecloud-notify/goreecloud_notify.db",
            "owner": "goreecloud-notify",
            "group": "goreecloud-notify",
            "mode": "0600",
            "runtime_read_write_verified": True,
        },
        "backup_repository": {
            "repository_type": "Kopia encrypted repository",
            "destination_reference": "approved independent GoreeCloud recovery repository",
            "encrypted_or_provider_protected": True,
            "independent_from_primary_runtime": True,
            "independent_from_primary_storage": True,
            "credentials_recoverable_without_primary_host": True,
            "credential_reference": "Vaultwarden recovery record identifier only",
            "administrative_recovery_path": "approved NetBird recovery peer with provider-console fallback",
        },
        "backup_policy": {
            "backup_frequency_minutes": 60,
            "maximum_rpo_minutes": 120,
            "recovery_point_retention_days": 30,
            "minimum_recovery_point_count": 14,
            "pre_change_recovery_point_required": True,
        },
        "backup_monitoring": {
            "failed_backup_monitoring_enabled": True,
            "missed_backup_monitoring_enabled": True,
            "mechanism": "independent backup heartbeat monitor",
            "alert_path": "approved out-of-band administrator channel",
            "separate_failure_domain": True,
            "depends_on_notify": False,
            "depends_on_same_runtime_host": False,
            "controlled_failure_or_missed_backup_tested": True,
            "approved_administrator_received_alert": True,
        },
        "snapshot": {
            "method": "sqlite_online_backup_api",
            "captured_at": "2026-08-18T21:00:00-05:00",
            "build_revision": REVISION,
            "alembic_revision": "202608170001",
            "artifact_sha256": SHA256,
            "artifact_size_bytes": 1048576,
            "integrity_check_passed": True,
            "foreign_key_check_passed": True,
            "manifest_sanitized": True,
        },
        "alternate_restore": {
            "alternate_location": True,
            "production_overwritten": False,
            "location_reference": "isolated recovery validation host /srv/recovery/notify",
            "started_at": "2026-08-18T21:30:00-05:00",
            "completed_at": "2026-08-18T21:42:00-05:00",
            "observed_recovery_seconds": 720,
            "source_backup_sha256": SHA256,
            "restored_artifact_sha256": SHA256,
            "build_revision": REVISION,
            "alembic_revision_after_restore": "202608170001",
            "alembic_validation_passed": True,
            "file_ownership_permissions_verified": True,
            "healthz_passed": True,
            "human_authentication_passed": True,
            "expected_application_state_passed": True,
            "producer_authorization_passed": True,
            "inbox_isolation_passed": True,
            "read_ack_state_passed": True,
        },
        "security_reconciliation": {
            "restored_web_sessions_revoked": True,
            "producer_token_state_reviewed": True,
            "user_active_state_reviewed": True,
            "administrator_authority_reviewed": True,
            "password_reset_state_reviewed": True,
            "login_security_state_interpreted_as_historical": True,
            "current_authoritative_identity_records_used": True,
        },
        "disposition": {
            "restore_environment_state": "disposed",
            "rollback_or_disposition_recorded": True,
            "production_data_unchanged_by_routine_restore_test": True,
        },
        "privacy": {
            "raw_notification_content_recorded": False,
            "reusable_secrets_recorded": False,
            "repository_secret_values_recorded": False,
            "evidence_sanitized": True,
        },
    }


def test_source_contract_is_bound_to_issue_23() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["schema_version"] == 1
    assert contract["contract_kind"] == "goreecloud-notify-target-backup-restore-contract"
    assert contract["state"] == "target-evidence-required"
    assert contract["issue"] == 23
    assert contract["candidate_contract"]["production_accepted"] is False
    assert contract["snapshot_contract"]["method"] == "sqlite_online_backup_api"
    assert contract["restore_contract"]["alternate_location_required"] is True


def test_valid_complete_target_recovery_evidence_passes() -> None:
    validator.validate_evidence(valid_evidence(), REVISION)


def test_candidate_snapshot_and_restore_must_bind_to_expected_revision() -> None:
    evidence = valid_evidence()
    other_revision = "89abcdef0123456789abcdef0123456789abcdef"

    with pytest.raises(validator.EvidenceValidationError, match="expected deployed revision"):
        validator.validate_evidence(evidence, other_revision)

    evidence = valid_evidence()
    evidence["snapshot"]["build_revision"] = other_revision  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="snapshot.build_revision"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["alternate_restore"]["build_revision"] = other_revision  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="alternate_restore.build_revision"):
        validator.validate_evidence(evidence, REVISION)


def test_backup_repository_must_be_independent_and_recoverable() -> None:
    for field in (
        "encrypted_or_provider_protected",
        "independent_from_primary_runtime",
        "independent_from_primary_storage",
        "credentials_recoverable_without_primary_host",
    ):
        evidence = valid_evidence()
        evidence["backup_repository"][field] = False  # type: ignore[index]
        with pytest.raises(validator.EvidenceValidationError, match=field):
            validator.validate_evidence(evidence, REVISION)


def test_backup_policy_requires_concrete_positive_rpo_retention_and_prechange_point() -> None:
    evidence = valid_evidence()
    evidence["backup_policy"]["backup_frequency_minutes"] = 180  # type: ignore[index]
    evidence["backup_policy"]["maximum_rpo_minutes"] = 120  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="must not exceed"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["backup_policy"]["recovery_point_retention_days"] = 0  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="positive integer"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["backup_policy"]["pre_change_recovery_point_required"] = False  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="must be True"):
        validator.validate_evidence(evidence, REVISION)


def test_backup_monitoring_must_be_independent_and_tested() -> None:
    evidence = valid_evidence()
    evidence["backup_monitoring"]["depends_on_notify"] = True  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="depends_on_notify"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["backup_monitoring"]["depends_on_same_runtime_host"] = True  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="depends_on_same_runtime_host"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["backup_monitoring"]["approved_administrator_received_alert"] = False  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="approved_administrator_received_alert"):
        validator.validate_evidence(evidence, REVISION)


def test_snapshot_must_use_verified_online_backup_artifact() -> None:
    evidence = valid_evidence()
    evidence["snapshot"]["method"] = "filesystem_cp"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="snapshot.method"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["snapshot"]["integrity_check_passed"] = False  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="integrity_check_passed"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["snapshot"]["artifact_sha256"] = "not-a-digest"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="SHA-256"):
        validator.validate_evidence(evidence, REVISION)


def test_restore_must_be_alternate_non_destructive_and_hash_bound() -> None:
    evidence = valid_evidence()
    evidence["alternate_restore"]["alternate_location"] = False  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="alternate_location"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["alternate_restore"]["production_overwritten"] = True  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="production_overwritten"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["alternate_restore"]["restored_artifact_sha256"] = "b" * 64  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="restored_artifact_sha256"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["alternate_restore"]["completed_at"] = "2026-08-18T21:20:00-05:00"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="after started_at"):
        validator.validate_evidence(evidence, REVISION)


def test_database_mode_must_be_restrictive_but_runtime_writable() -> None:
    evidence = valid_evidence()
    evidence["data_path"]["mode"] = "0644"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="other users"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["data_path"]["mode"] = "0400"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="read and write"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["data_path"]["runtime_read_write_verified"] = False  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="runtime_read_write_verified"):
        validator.validate_evidence(evidence, REVISION)


def test_security_reconciliation_is_mandatory() -> None:
    evidence = valid_evidence()
    evidence["security_reconciliation"]["restored_web_sessions_revoked"] = False  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="restored_web_sessions_revoked"):
        validator.validate_evidence(evidence, REVISION)

    evidence = valid_evidence()
    evidence["security_reconciliation"]["producer_token_state_reviewed"] = False  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="producer_token_state_reviewed"):
        validator.validate_evidence(evidence, REVISION)


def test_privacy_and_sensitive_fields_fail_closed() -> None:
    evidence = valid_evidence()
    evidence["privacy"]["reusable_secrets_recorded"] = True  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="must be False"):
        validator.validate_evidence(evidence, REVISION)

    sensitive = copy.deepcopy(valid_evidence())
    sensitive["backup_repository"]["token_value"] = "do-not-store"  # type: ignore[index]
    with pytest.raises(validator.EvidenceValidationError, match="prohibited sensitive-data field"):
        validator.validate_evidence(sensitive, REVISION)
