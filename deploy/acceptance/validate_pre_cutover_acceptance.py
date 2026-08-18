from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CONTRACT_PATH = Path(__file__).with_name("pre_cutover_acceptance_contract.json")
ROOT = Path(__file__).resolve().parents[2]
MANIFEST_KIND = "goreecloud-notify-pre-cutover-acceptance"
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDERS = {"example", "pending", "placeholder", "replace-me", "tbd", "todo", "unknown", "unset"}
SAFE_ASSERTIONS = {"authorization_validation_passed", "reusable_secrets_recorded"}
SENSITIVE_FRAGMENTS = (
    "authorization", "cookie", "csrf", "password", "private_key", "recovery_code", "secret", "token_value"
)


class AcceptanceValidationError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AcceptanceValidationError(f"file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AcceptanceValidationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AcceptanceValidationError(f"JSON root must be an object: {path}")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise AcceptanceValidationError(f"{path} fields mismatch; missing={missing}, unexpected={unexpected}")


def _text(value: Any, path: str, *, max_length: int = 1000) -> str:
    if not isinstance(value, str):
        raise AcceptanceValidationError(f"{path} must be a string")
    text = value.strip()
    if not text or text.lower() in PLACEHOLDERS:
        raise AcceptanceValidationError(f"{path} must contain a concrete recorded value")
    if len(text) > max_length:
        raise AcceptanceValidationError(f"{path} must be <= {max_length} characters")
    return text


def _bool(value: Any, expected: bool, path: str) -> None:
    if value is not expected:
        raise AcceptanceValidationError(f"{path} must be {expected!r}")


def _timestamp(value: Any, path: str) -> None:
    text = _text(value, path, max_length=100)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise AcceptanceValidationError(f"{path} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise AcceptanceValidationError(f"{path} must include a timezone offset")


def _revision(value: Any, path: str) -> str:
    text = _text(value, path, max_length=40).lower()
    if REVISION_RE.fullmatch(text) is None:
        raise AcceptanceValidationError(f"{path} must be an exact 40-character lowercase Git SHA")
    return text


def _sha256_text(value: Any, path: str) -> str:
    text = _text(value, path, max_length=64).lower()
    if SHA256_RE.fullmatch(text) is None:
        raise AcceptanceValidationError(f"{path} must be a lowercase SHA-256 digest")
    return text


def _https_url(value: Any, path: str) -> str:
    text = _text(value, path, max_length=300)
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AcceptanceValidationError(f"{path} must be an absolute HTTPS URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AcceptanceValidationError(f"{path} must not contain credentials, query parameters, or fragments")
    return text.rstrip("/")


def _reject_sensitive_fields(value: Any, path: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if lowered not in SAFE_ASSERTIONS and any(fragment in lowered for fragment in SENSITIVE_FRAGMENTS):
                raise AcceptanceValidationError(f"{path}.{key} is a prohibited sensitive-data field")
            _reject_sensitive_fields(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_sensitive_fields(nested, f"{path}[{index}]")


def _artifact_path(manifest_path: Path, value: Any, path: str) -> Path:
    text = _text(value, path, max_length=500)
    relative = Path(text)
    if relative.is_absolute() or ".." in relative.parts:
        raise AcceptanceValidationError(f"{path} must be a relative path contained beside the manifest")
    base = manifest_path.resolve().parent
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise AcceptanceValidationError(f"{path} must resolve within the manifest evidence directory") from exc
    if not resolved.is_file():
        raise AcceptanceValidationError(f"{path} does not identify an existing regular file")
    return resolved


def _verify_digest(path: Path, expected: Any, field: str) -> None:
    expected_digest = _sha256_text(expected, field)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected_digest:
        raise AcceptanceValidationError(f"{field} does not match the referenced evidence file")


def _load_validator(relative_path: str, module_name: str) -> Any:
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AcceptanceValidationError(f"unable to load source validator {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_subordinate(
    artifact: Path,
    expected_kind: str,
    expected_revision: str,
    candidate_url: str,
    validator_path: str,
    module_name: str,
) -> None:
    evidence = _load_json(artifact)
    if evidence.get("evidence_kind") != expected_kind:
        raise AcceptanceValidationError(f"{artifact.name} has the wrong evidence_kind")
    candidate = evidence.get("candidate")
    if not isinstance(candidate, dict):
        raise AcceptanceValidationError(f"{artifact.name} must contain candidate identity")
    if candidate.get("build_revision") != expected_revision:
        raise AcceptanceValidationError(f"{artifact.name} candidate revision does not match aggregate candidate")
    if str(candidate.get("service_url", "")).rstrip("/") != candidate_url:
        raise AcceptanceValidationError(f"{artifact.name} candidate URL does not match aggregate candidate")
    module = _load_validator(validator_path, module_name)
    try:
        module.validate_evidence(evidence, expected_revision)
    except Exception as exc:
        raise AcceptanceValidationError(f"{artifact.name} failed its source validator: {exc}") from exc


def _validate_preflight(report: dict[str, Any], revision: str, base_url: str, contract: dict[str, Any]) -> None:
    _exact_keys(
        report,
        {"schema", "generated_at", "scope", "base_url", "expected_revision", "container", "data_dir", "env_file", "result", "checks", "limitations"},
        "target_preflight",
    )
    expected = contract["required_evidence"]["target_preflight"]
    if report["schema"] != expected["schema"]:
        raise AcceptanceValidationError("target_preflight.schema does not match the source contract")
    if report["scope"] != expected["scope"]:
        raise AcceptanceValidationError("target_preflight.scope must be 'all'")
    if report["result"] != expected["result"]:
        raise AcceptanceValidationError("target_preflight.result must be 'pass'")
    if str(report["base_url"]).rstrip("/") != base_url:
        raise AcceptanceValidationError("target_preflight.base_url does not match aggregate candidate")
    if report["expected_revision"] != revision:
        raise AcceptanceValidationError("target_preflight.expected_revision does not match aggregate candidate")
    _timestamp(report["generated_at"], "target_preflight.generated_at")
    checks = report["checks"]
    if not isinstance(checks, list) or not checks:
        raise AcceptanceValidationError("target_preflight.checks must contain the completed all-scope checks")
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise AcceptanceValidationError(f"target_preflight.checks[{index}] must be an object")
        _exact_keys(check, {"name", "status", "detail"}, f"target_preflight.checks[{index}]")
        _text(check["name"], f"target_preflight.checks[{index}].name", max_length=200)
        _text(check["detail"], f"target_preflight.checks[{index}].detail", max_length=2000)
        if check["status"] != "pass":
            raise AcceptanceValidationError(f"target_preflight.checks[{index}] is not pass")
    if not isinstance(report["limitations"], list):
        raise AcceptanceValidationError("target_preflight.limitations must be a list")


def validate_manifest(manifest: dict[str, Any], manifest_path: Path, expected_revision: str) -> None:
    contract = _load_json(CONTRACT_PATH)
    if contract.get("schema_version") != 1 or contract.get("state") != "evidence-required":
        raise AcceptanceValidationError("source pre-cutover acceptance contract is invalid")
    expected_revision = _revision(expected_revision, "expected_revision")
    _reject_sensitive_fields(manifest)
    _exact_keys(
        manifest,
        {"schema_version", "manifest_kind", "sanitized", "captured_at", "candidate", "evidence_files", "migration_rollback", "privacy"},
        "manifest",
    )
    if manifest["schema_version"] != 1:
        raise AcceptanceValidationError("manifest.schema_version must be 1")
    if manifest["manifest_kind"] != MANIFEST_KIND:
        raise AcceptanceValidationError(f"manifest.manifest_kind must be {MANIFEST_KIND!r}")
    _bool(manifest["sanitized"], True, "manifest.sanitized")
    _timestamp(manifest["captured_at"], "manifest.captured_at")

    candidate = manifest["candidate"]
    if not isinstance(candidate, dict):
        raise AcceptanceValidationError("manifest.candidate must be an object")
    _exact_keys(candidate, {"service_url", "build_revision", "release_stage", "production_accepted", "acceptance_status"}, "manifest.candidate")
    candidate_url = _https_url(candidate["service_url"], "manifest.candidate.service_url")
    revision = _revision(candidate["build_revision"], "manifest.candidate.build_revision")
    if revision != expected_revision:
        raise AcceptanceValidationError("manifest candidate revision must match --expected-revision")
    candidate_contract = contract["candidate_contract"]
    for field in ("release_stage", "production_accepted", "acceptance_status"):
        if candidate[field] != candidate_contract[field]:
            raise AcceptanceValidationError(f"manifest.candidate.{field} must match source contract")

    evidence_files = manifest["evidence_files"]
    if not isinstance(evidence_files, dict):
        raise AcceptanceValidationError("manifest.evidence_files must be an object")
    expected_names = {"backup_restore", "monitoring", "target_preflight", "manual_browser_os"}
    _exact_keys(evidence_files, expected_names, "manifest.evidence_files")
    artifacts: dict[str, Path] = {}
    for name in sorted(expected_names):
        reference = evidence_files[name]
        if not isinstance(reference, dict):
            raise AcceptanceValidationError(f"manifest.evidence_files.{name} must be an object")
        _exact_keys(reference, {"path", "sha256"}, f"manifest.evidence_files.{name}")
        artifact = _artifact_path(manifest_path, reference["path"], f"manifest.evidence_files.{name}.path")
        _verify_digest(artifact, reference["sha256"], f"manifest.evidence_files.{name}.sha256")
        artifacts[name] = artifact
    if len({path.resolve() for path in artifacts.values()}) != len(artifacts):
        raise AcceptanceValidationError("each acceptance gate must reference a distinct evidence artifact")

    required = contract["required_evidence"]
    _validate_subordinate(artifacts["backup_restore"], required["backup_restore"]["evidence_kind"], revision, candidate_url, required["backup_restore"]["validator"], "aggregate_backup_validator")
    _validate_subordinate(artifacts["monitoring"], required["monitoring"]["evidence_kind"], revision, candidate_url, required["monitoring"]["validator"], "aggregate_monitoring_validator")
    _validate_subordinate(artifacts["manual_browser_os"], required["manual_browser_os"]["evidence_kind"], revision, candidate_url, required["manual_browser_os"]["validator"], "aggregate_manual_validator")
    _validate_preflight(_load_json(artifacts["target_preflight"]), revision, candidate_url, contract)

    migration = manifest["migration_rollback"]
    if not isinstance(migration, dict):
        raise AcceptanceValidationError("manifest.migration_rollback must be an object")
    _exact_keys(
        migration,
        {"phase", "recorded_at", "ntfy_active", "ntfy_retired", "parallel_producer_validation_passed", "parallel_consumer_validation_passed", "authorization_validation_passed", "rollback_exercised", "rollback_procedure_recorded", "cutover_performed", "evidence_summary"},
        "manifest.migration_rollback",
    )
    migration_contract = contract["migration_rollback_contract"]
    if migration["phase"] != migration_contract["phase"]:
        raise AcceptanceValidationError("migration_rollback.phase must be pre_cutover_ready")
    _timestamp(migration["recorded_at"], "manifest.migration_rollback.recorded_at")
    _bool(migration["ntfy_active"], True, "manifest.migration_rollback.ntfy_active")
    _bool(migration["ntfy_retired"], False, "manifest.migration_rollback.ntfy_retired")
    for field in (
        "parallel_producer_validation_passed",
        "parallel_consumer_validation_passed",
        "authorization_validation_passed",
        "rollback_exercised",
        "rollback_procedure_recorded",
    ):
        _bool(migration[field], True, f"manifest.migration_rollback.{field}")
    _bool(migration["cutover_performed"], False, "manifest.migration_rollback.cutover_performed")
    _text(migration["evidence_summary"], "manifest.migration_rollback.evidence_summary", max_length=2000)

    privacy = manifest["privacy"]
    if not isinstance(privacy, dict):
        raise AcceptanceValidationError("manifest.privacy must be an object")
    expected_privacy = contract["privacy_contract"]
    _exact_keys(privacy, set(expected_privacy), "manifest.privacy")
    for field, expected in expected_privacy.items():
        _bool(privacy[field], expected, f"manifest.privacy.{field}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one coherent GoreeCloud Notify pre-cutover acceptance set. A PASS proves "
            "evidence convergence for one candidate; it does not promote Stable, perform cutover, or retire ntfy."
        )
    )
    parser.add_argument("manifest", type=Path, help="path to the sanitized pre-cutover acceptance manifest")
    parser.add_argument("--expected-revision", required=True, help="exact 40-character Git SHA intentionally under acceptance")
    args = parser.parse_args(argv)
    try:
        manifest = _load_json(args.manifest)
        validate_manifest(manifest, args.manifest, args.expected_revision)
    except AcceptanceValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print("PASS: GoreeCloud Notify pre-cutover acceptance evidence is coherent for one exact candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
