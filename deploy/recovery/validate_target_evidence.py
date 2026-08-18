from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

CONTRACT_PATH = Path(__file__).with_name("target_backup_restore_contract.json")
EVIDENCE_KIND = "goreecloud-notify-target-backup-restore-acceptance"
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OCTAL_MODE_RE = re.compile(r"^0[0-7]{3}$")
SAFE_SENSITIVE_ASSERTION_KEYS = {
    "repository_secret_values_recorded",
    "reusable_secrets_recorded",
}
SENSITIVE_KEY_FRAGMENTS = (
    "authorization",
    "cookie",
    "csrf",
    "database_url",
    "password",
    "private_key",
    "recovery_code",
    "secret",
    "session_cookie",
    "token_value",
)
PLACEHOLDER_VALUES = {
    "change-me",
    "example",
    "pending",
    "placeholder",
    "replace-me",
    "tbd",
    "todo",
    "unknown",
    "unset",
}


class EvidenceValidationError(ValueError):
    pass


def _require_exact_keys(value: dict[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing}")
        if unexpected:
            details.append(f"unexpected={unexpected}")
        raise EvidenceValidationError(f"{path} has invalid fields ({', '.join(details)})")


def _require_bool(value: Any, expected: bool, path: str) -> None:
    if value is not expected:
        raise EvidenceValidationError(f"{path} must be {expected!r}")


def _require_non_placeholder_text(value: Any, path: str, *, max_length: int = 1000) -> str:
    if not isinstance(value, str):
        raise EvidenceValidationError(f"{path} must be a string")
    normalized = value.strip()
    if not normalized:
        raise EvidenceValidationError(f"{path} must not be empty")
    if normalized.lower() in PLACEHOLDER_VALUES:
        raise EvidenceValidationError(f"{path} must contain a concrete recorded value")
    if len(normalized) > max_length:
        raise EvidenceValidationError(f"{path} must be <= {max_length} characters")
    return normalized


def _require_positive_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise EvidenceValidationError(f"{path} must be a positive integer")
    return value


def _parse_timestamp(value: Any, path: str) -> datetime:
    text = _require_non_placeholder_text(value, path, max_length=100)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise EvidenceValidationError(f"{path} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EvidenceValidationError(f"{path} must include a timezone offset")
    return parsed


def _require_revision(value: Any, path: str) -> str:
    text = _require_non_placeholder_text(value, path, max_length=40).lower()
    if REVISION_RE.fullmatch(text) is None:
        raise EvidenceValidationError(f"{path} must be an exact 40-character lowercase Git SHA")
    return text


def _require_sha256(value: Any, path: str) -> str:
    text = _require_non_placeholder_text(value, path, max_length=64).lower()
    if SHA256_RE.fullmatch(text) is None:
        raise EvidenceValidationError(f"{path} must be an exact lowercase SHA-256 digest")
    return text


def _require_https_url(value: Any, path: str) -> str:
    text = _require_non_placeholder_text(value, path, max_length=300)
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.netloc:
        raise EvidenceValidationError(f"{path} must be an absolute HTTPS URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise EvidenceValidationError(
            f"{path} must not contain credentials, query parameters, or fragments"
        )
    return text.rstrip("/")


def _require_absolute_posix_path(value: Any, path: str) -> str:
    text = _require_non_placeholder_text(value, path, max_length=500)
    candidate = PurePosixPath(text)
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise EvidenceValidationError(f"{path} must be an absolute normalized POSIX path")
    return str(candidate)


def _require_restrictive_database_mode(value: Any, path: str) -> str:
    text = _require_non_placeholder_text(value, path, max_length=4)
    if OCTAL_MODE_RE.fullmatch(text) is None:
        raise EvidenceValidationError(f"{path} must be a four-character octal mode such as '0600'")
    mode = int(text, 8)
    if mode & stat.S_IROTH or mode & stat.S_IWOTH or mode & stat.S_IXOTH:
        raise EvidenceValidationError(f"{path} must not grant permissions to other users")
    if not mode & stat.S_IRUSR or not mode & stat.S_IWUSR:
        raise EvidenceValidationError(f"{path} must grant the owner read and write access")
    if mode & stat.S_IXUSR or mode & stat.S_IXGRP:
        raise EvidenceValidationError(f"{path} must not mark the SQLite database executable")
    return text


def _reject_sensitive_keys(value: Any, path: str = "evidence") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if (
                lowered not in SAFE_SENSITIVE_ASSERTION_KEYS
                and any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)
            ):
                raise EvidenceValidationError(f"{path}.{key} is a prohibited sensitive-data field")
            _reject_sensitive_keys(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_sensitive_keys(nested, f"{path}[{index}]")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceValidationError(f"evidence file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceValidationError(f"evidence file is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise EvidenceValidationError("evidence root must be a JSON object")
    return raw


def _load_contract() -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    _require_exact_keys(
        contract,
        {
            "schema_version",
            "contract_kind",
            "state",
            "issue",
            "candidate_contract",
            "snapshot_contract",
            "restore_contract",
            "privacy_contract",
        },
        "contract",
    )
    if contract["schema_version"] != 1:
        raise EvidenceValidationError("source recovery contract schema_version must be 1")
    if contract["contract_kind"] != "goreecloud-notify-target-backup-restore-contract":
        raise EvidenceValidationError("source recovery contract kind is invalid")
    if contract["state"] != "target-evidence-required":
        raise EvidenceValidationError("source recovery contract must remain in target-evidence-required state")
    if contract["issue"] != 23:
        raise EvidenceValidationError("source recovery contract must remain bound to issue #23")
    return contract


def validate_evidence(
    evidence: dict[str, Any],
    expected_revision: str,
    contract: dict[str, Any] | None = None,
) -> None:
    contract = contract or _load_contract()
    expected_revision = _require_revision(expected_revision, "expected_revision")
    _reject_sensitive_keys(evidence)

    _require_exact_keys(
        evidence,
        {
            "schema_version",
            "evidence_kind",
            "sanitized",
            "captured_at",
            "candidate",
            "data_path",
            "backup_repository",
            "backup_policy",
            "backup_monitoring",
            "snapshot",
            "alternate_restore",
            "security_reconciliation",
            "disposition",
            "privacy",
        },
        "evidence",
    )
    if evidence["schema_version"] != 1:
        raise EvidenceValidationError("schema_version must be 1")
    if evidence["evidence_kind"] != EVIDENCE_KIND:
        raise EvidenceValidationError(f"evidence_kind must be {EVIDENCE_KIND!r}")
    _require_bool(evidence["sanitized"], True, "sanitized")
    _parse_timestamp(evidence["captured_at"], "captured_at")

    candidate_contract = contract["candidate_contract"]
    candidate = evidence["candidate"]
    if not isinstance(candidate, dict):
        raise EvidenceValidationError("candidate must be an object")
    _require_exact_keys(
        candidate,
        {
            "service_url",
            "build_revision",
            "release_stage",
            "production_accepted",
            "acceptance_status",
        },
        "candidate",
    )
    _require_https_url(candidate["service_url"], "candidate.service_url")
    candidate_revision = _require_revision(candidate["build_revision"], "candidate.build_revision")
    if candidate_revision != expected_revision:
        raise EvidenceValidationError(
            "candidate.build_revision must match the explicitly expected deployed revision"
        )
    for field in ("release_stage", "production_accepted", "acceptance_status"):
        if candidate[field] != candidate_contract[field]:
            raise EvidenceValidationError(
                f"candidate.{field} must match the source acceptance contract: {candidate_contract[field]!r}"
            )

    data_path = evidence["data_path"]
    if not isinstance(data_path, dict):
        raise EvidenceValidationError("data_path must be an object")
    _require_exact_keys(
        data_path,
        {
            "database_path",
            "owner",
            "group",
            "mode",
            "runtime_read_write_verified",
        },
        "data_path",
    )
    _require_absolute_posix_path(data_path["database_path"], "data_path.database_path")
    _require_non_placeholder_text(data_path["owner"], "data_path.owner", max_length=100)
    _require_non_placeholder_text(data_path["group"], "data_path.group", max_length=100)
    _require_restrictive_database_mode(data_path["mode"], "data_path.mode")
    _require_bool(data_path["runtime_read_write_verified"], True, "data_path.runtime_read_write_verified")

    repository = evidence["backup_repository"]
    if not isinstance(repository, dict):
        raise EvidenceValidationError("backup_repository must be an object")
    _require_exact_keys(
        repository,
        {
            "repository_type",
            "destination_reference",
            "encrypted_or_provider_protected",
            "independent_from_primary_runtime",
            "independent_from_primary_storage",
            "credentials_recoverable_without_primary_host",
            "credential_reference",
            "administrative_recovery_path",
        },
        "backup_repository",
    )
    for field in (
        "repository_type",
        "destination_reference",
        "credential_reference",
        "administrative_recovery_path",
    ):
        _require_non_placeholder_text(repository[field], f"backup_repository.{field}", max_length=500)
    for field in (
        "encrypted_or_provider_protected",
        "independent_from_primary_runtime",
        "independent_from_primary_storage",
        "credentials_recoverable_without_primary_host",
    ):
        _require_bool(repository[field], True, f"backup_repository.{field}")

    policy = evidence["backup_policy"]
    if not isinstance(policy, dict):
        raise EvidenceValidationError("backup_policy must be an object")
    _require_exact_keys(
        policy,
        {
            "backup_frequency_minutes",
            "maximum_rpo_minutes",
            "recovery_point_retention_days",
            "minimum_recovery_point_count",
            "pre_change_recovery_point_required",
        },
        "backup_policy",
    )
    frequency = _require_positive_int(policy["backup_frequency_minutes"], "backup_policy.backup_frequency_minutes")
    rpo = _require_positive_int(policy["maximum_rpo_minutes"], "backup_policy.maximum_rpo_minutes")
    if frequency > rpo:
        raise EvidenceValidationError(
            "backup_policy.backup_frequency_minutes must not exceed maximum_rpo_minutes"
        )
    _require_positive_int(
        policy["recovery_point_retention_days"],
        "backup_policy.recovery_point_retention_days",
    )
    _require_positive_int(
        policy["minimum_recovery_point_count"],
        "backup_policy.minimum_recovery_point_count",
    )
    _require_bool(
        policy["pre_change_recovery_point_required"],
        True,
        "backup_policy.pre_change_recovery_point_required",
    )

    monitoring = evidence["backup_monitoring"]
    if not isinstance(monitoring, dict):
        raise EvidenceValidationError("backup_monitoring must be an object")
    _require_exact_keys(
        monitoring,
        {
            "failed_backup_monitoring_enabled",
            "missed_backup_monitoring_enabled",
            "mechanism",
            "alert_path",
            "separate_failure_domain",
            "depends_on_notify",
            "depends_on_same_runtime_host",
            "controlled_failure_or_missed_backup_tested",
            "approved_administrator_received_alert",
        },
        "backup_monitoring",
    )
    _require_bool(
        monitoring["failed_backup_monitoring_enabled"],
        True,
        "backup_monitoring.failed_backup_monitoring_enabled",
    )
    _require_bool(
        monitoring["missed_backup_monitoring_enabled"],
        True,
        "backup_monitoring.missed_backup_monitoring_enabled",
    )
    _require_non_placeholder_text(monitoring["mechanism"], "backup_monitoring.mechanism", max_length=300)
    _require_non_placeholder_text(monitoring["alert_path"], "backup_monitoring.alert_path", max_length=300)
    _require_bool(monitoring["separate_failure_domain"], True, "backup_monitoring.separate_failure_domain")
    _require_bool(monitoring["depends_on_notify"], False, "backup_monitoring.depends_on_notify")
    _require_bool(
        monitoring["depends_on_same_runtime_host"],
        False,
        "backup_monitoring.depends_on_same_runtime_host",
    )
    _require_bool(
        monitoring["controlled_failure_or_missed_backup_tested"],
        True,
        "backup_monitoring.controlled_failure_or_missed_backup_tested",
    )
    _require_bool(
        monitoring["approved_administrator_received_alert"],
        True,
        "backup_monitoring.approved_administrator_received_alert",
    )

    snapshot_contract = contract["snapshot_contract"]
    snapshot = evidence["snapshot"]
    if not isinstance(snapshot, dict):
        raise EvidenceValidationError("snapshot must be an object")
    _require_exact_keys(
        snapshot,
        {
            "method",
            "captured_at",
            "build_revision",
            "alembic_revision",
            "artifact_sha256",
            "artifact_size_bytes",
            "integrity_check_passed",
            "foreign_key_check_passed",
            "manifest_sanitized",
        },
        "snapshot",
    )
    if snapshot["method"] != snapshot_contract["method"]:
        raise EvidenceValidationError(
            f"snapshot.method must match the source contract: {snapshot_contract['method']!r}"
        )
    snapshot_time = _parse_timestamp(snapshot["captured_at"], "snapshot.captured_at")
    if _require_revision(snapshot["build_revision"], "snapshot.build_revision") != candidate_revision:
        raise EvidenceValidationError("snapshot.build_revision must match candidate.build_revision")
    _require_non_placeholder_text(snapshot["alembic_revision"], "snapshot.alembic_revision", max_length=100)
    snapshot_sha = _require_sha256(snapshot["artifact_sha256"], "snapshot.artifact_sha256")
    _require_positive_int(snapshot["artifact_size_bytes"], "snapshot.artifact_size_bytes")
    _require_bool(snapshot["integrity_check_passed"], True, "snapshot.integrity_check_passed")
    _require_bool(snapshot["foreign_key_check_passed"], True, "snapshot.foreign_key_check_passed")
    _require_bool(snapshot["manifest_sanitized"], True, "snapshot.manifest_sanitized")

    restore_contract = contract["restore_contract"]
    restore = evidence["alternate_restore"]
    if not isinstance(restore, dict):
        raise EvidenceValidationError("alternate_restore must be an object")
    _require_exact_keys(
        restore,
        {
            "alternate_location",
            "production_overwritten",
            "location_reference",
            "started_at",
            "completed_at",
            "observed_recovery_seconds",
            "source_backup_sha256",
            "restored_artifact_sha256",
            "build_revision",
            "alembic_revision_after_restore",
            "alembic_validation_passed",
            "file_ownership_permissions_verified",
            "healthz_passed",
            "human_authentication_passed",
            "expected_application_state_passed",
            "producer_authorization_passed",
            "inbox_isolation_passed",
            "read_ack_state_passed",
        },
        "alternate_restore",
    )
    _require_bool(
        restore["alternate_location"],
        restore_contract["alternate_location_required"],
        "alternate_restore.alternate_location",
    )
    _require_bool(
        restore["production_overwritten"],
        restore_contract["production_overwrite_for_routine_test"],
        "alternate_restore.production_overwritten",
    )
    _require_non_placeholder_text(
        restore["location_reference"],
        "alternate_restore.location_reference",
        max_length=500,
    )
    started_at = _parse_timestamp(restore["started_at"], "alternate_restore.started_at")
    completed_at = _parse_timestamp(restore["completed_at"], "alternate_restore.completed_at")
    if started_at < snapshot_time:
        raise EvidenceValidationError("alternate_restore.started_at must not predate the selected snapshot")
    if completed_at <= started_at:
        raise EvidenceValidationError("alternate_restore.completed_at must be after started_at")
    _require_positive_int(
        restore["observed_recovery_seconds"],
        "alternate_restore.observed_recovery_seconds",
    )
    if _require_sha256(restore["source_backup_sha256"], "alternate_restore.source_backup_sha256") != snapshot_sha:
        raise EvidenceValidationError("alternate_restore.source_backup_sha256 must match snapshot.artifact_sha256")
    if _require_sha256(
        restore["restored_artifact_sha256"],
        "alternate_restore.restored_artifact_sha256",
    ) != snapshot_sha:
        raise EvidenceValidationError(
            "alternate_restore.restored_artifact_sha256 must match the verified source backup"
        )
    if _require_revision(restore["build_revision"], "alternate_restore.build_revision") != candidate_revision:
        raise EvidenceValidationError("alternate_restore.build_revision must match candidate.build_revision")
    _require_non_placeholder_text(
        restore["alembic_revision_after_restore"],
        "alternate_restore.alembic_revision_after_restore",
        max_length=100,
    )
    for field in (
        "alembic_validation_passed",
        "file_ownership_permissions_verified",
        "healthz_passed",
        "human_authentication_passed",
        "expected_application_state_passed",
        "producer_authorization_passed",
        "inbox_isolation_passed",
        "read_ack_state_passed",
    ):
        _require_bool(restore[field], True, f"alternate_restore.{field}")

    reconciliation = evidence["security_reconciliation"]
    if not isinstance(reconciliation, dict):
        raise EvidenceValidationError("security_reconciliation must be an object")
    _require_exact_keys(
        reconciliation,
        {
            "restored_web_sessions_revoked",
            "producer_token_state_reviewed",
            "user_active_state_reviewed",
            "administrator_authority_reviewed",
            "password_reset_state_reviewed",
            "login_security_state_interpreted_as_historical",
            "current_authoritative_identity_records_used",
        },
        "security_reconciliation",
    )
    for field in reconciliation:
        _require_bool(reconciliation[field], True, f"security_reconciliation.{field}")

    disposition = evidence["disposition"]
    if not isinstance(disposition, dict):
        raise EvidenceValidationError("disposition must be an object")
    _require_exact_keys(
        disposition,
        {
            "restore_environment_state",
            "rollback_or_disposition_recorded",
            "production_data_unchanged_by_routine_restore_test",
        },
        "disposition",
    )
    if disposition["restore_environment_state"] not in {"disposed", "retained_controlled"}:
        raise EvidenceValidationError(
            "disposition.restore_environment_state must be 'disposed' or 'retained_controlled'"
        )
    _require_bool(
        disposition["rollback_or_disposition_recorded"],
        True,
        "disposition.rollback_or_disposition_recorded",
    )
    _require_bool(
        disposition["production_data_unchanged_by_routine_restore_test"],
        True,
        "disposition.production_data_unchanged_by_routine_restore_test",
    )

    privacy = evidence["privacy"]
    if not isinstance(privacy, dict):
        raise EvidenceValidationError("privacy must be an object")
    expected_privacy = contract["privacy_contract"]
    _require_exact_keys(privacy, set(expected_privacy), "privacy")
    for field, expected in expected_privacy.items():
        _require_bool(privacy[field], expected, f"privacy.{field}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate sanitized real target backup/restore evidence for GoreeCloud Notify issue #23. "
            "This validator is read-only and does not create backups, restore production data, "
            "configure repositories, or modify production."
        )
    )
    parser.add_argument("evidence", type=Path, help="path to sanitized target recovery evidence JSON")
    parser.add_argument(
        "--expected-revision",
        required=True,
        help="exact 40-character Git SHA of the candidate intentionally under target recovery acceptance",
    )
    args = parser.parse_args(argv)

    try:
        evidence = _load_json(args.evidence)
        validate_evidence(evidence, args.expected_revision)
    except EvidenceValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    print(
        "PASS: GoreeCloud Notify target backup/restore evidence satisfies the source issue #23 acceptance contract"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
