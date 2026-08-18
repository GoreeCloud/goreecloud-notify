from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).with_name("notify_uptime_kuma_monitor.json")
EVIDENCE_KIND = "goreecloud-notify-monitoring-target-acceptance"
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
SENSITIVE_KEY_FRAGMENTS = (
    "authorization",
    "cookie",
    "csrf",
    "database_url",
    "password",
    "private_key",
    "recovery_code",
    "secret",
    "session",
    "token",
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


def _require_non_placeholder_text(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise EvidenceValidationError(f"{path} must be a string")
    normalized = value.strip()
    if not normalized:
        raise EvidenceValidationError(f"{path} must not be empty")
    if normalized.lower() in PLACEHOLDER_VALUES:
        raise EvidenceValidationError(f"{path} must contain a concrete recorded value")
    return normalized


def _require_revision(value: Any, path: str) -> str:
    text = _require_non_placeholder_text(value, path).lower()
    if REVISION_RE.fullmatch(text) is None:
        raise EvidenceValidationError(f"{path} must be an exact 40-character lowercase Git SHA")
    return text


def _require_positive_int(value: Any, path: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvidenceValidationError(f"{path} must be an integer")
    minimum = 0 if allow_zero else 1
    if value < minimum:
        raise EvidenceValidationError(f"{path} must be >= {minimum}")
    return value


def _require_timestamp(value: Any, path: str) -> None:
    text = _require_non_placeholder_text(value, path)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise EvidenceValidationError(f"{path} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EvidenceValidationError(f"{path} must include a timezone offset")


def _require_ip(value: Any, path: str) -> ipaddress._BaseAddress:
    text = _require_non_placeholder_text(value, path)
    try:
        return ipaddress.ip_address(text)
    except ValueError as exc:
        raise EvidenceValidationError(f"{path} must be a valid IPv4 or IPv6 address") from exc


def _require_allowlist_contains(values: Any, observed: ipaddress._BaseAddress) -> None:
    if not isinstance(values, list) or not values:
        raise EvidenceValidationError("source_path.caddy_allowlist_values must be a non-empty list")
    networks: list[ipaddress._BaseNetwork] = []
    for index, item in enumerate(values):
        text = _require_non_placeholder_text(item, f"source_path.caddy_allowlist_values[{index}]")
        try:
            network = ipaddress.ip_network(text, strict=False)
        except ValueError as exc:
            raise EvidenceValidationError(
                f"source_path.caddy_allowlist_values[{index}] must be an IP address or CIDR"
            ) from exc
        networks.append(network)
    if not any(observed.version == network.version and observed in network for network in networks):
        raise EvidenceValidationError(
            "source_path.caddy_allowlist_values must authorize the observed Uptime Kuma source"
        )


def _reject_sensitive_keys(value: Any, path: str = "evidence") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
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
    if contract.get("schema_version") != 2:
        raise EvidenceValidationError("source monitoring contract schema_version must be 2")
    if contract.get("state") != "proposed-not-provisioned":
        raise EvidenceValidationError("source monitoring contract is not in proposed-not-provisioned state")
    target_evidence = contract.get("target_acceptance_evidence")
    if not isinstance(target_evidence, dict) or target_evidence.get("evidence_schema_version") != 2:
        raise EvidenceValidationError("source monitoring target evidence contract must require schema version 2")
    if target_evidence.get("exact_candidate_revision_required") is not True:
        raise EvidenceValidationError("source monitoring contract must require exact candidate revision evidence")
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
            "notify_monitor",
            "source_path",
            "state_transitions",
            "administrator_receipt",
            "ntfy_preservation",
            "rollback",
            "independent_out_of_band",
        },
        "evidence",
    )
    if evidence["schema_version"] != 2:
        raise EvidenceValidationError("schema_version must be 2")
    if evidence["evidence_kind"] != EVIDENCE_KIND:
        raise EvidenceValidationError(f"evidence_kind must be {EVIDENCE_KIND!r}")
    _require_bool(evidence["sanitized"], True, "sanitized")
    _require_timestamp(evidence["captured_at"], "captured_at")

    expected_candidate = contract["candidate_contract"]
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
    for field in ("service_url", "release_stage", "production_accepted", "acceptance_status"):
        if candidate[field] != expected_candidate[field]:
            raise EvidenceValidationError(
                f"candidate.{field} must match the source contract: {expected_candidate[field]!r}"
            )
    candidate_revision = _require_revision(candidate["build_revision"], "candidate.build_revision")
    if candidate_revision != expected_revision:
        raise EvidenceValidationError(
            "candidate.build_revision must match the explicitly expected deployed revision"
        )

    expected_monitor = contract["monitor"]
    monitor = evidence["notify_monitor"]
    if not isinstance(monitor, dict):
        raise EvidenceValidationError("notify_monitor must be an object")
    _require_exact_keys(
        monitor,
        {
            "id",
            "name",
            "type",
            "url",
            "method",
            "active",
            "interval_seconds",
            "max_retries",
            "retry_interval_seconds",
            "request_timeout_seconds",
            "accepted_status_codes",
            "tls_verification_enabled",
            "notification_assignment_identifiers",
        },
        "notify_monitor",
    )
    _require_positive_int(monitor["id"], "notify_monitor.id")
    for field in ("name", "type", "url", "method", "interval_seconds", "accepted_status_codes"):
        if monitor[field] != expected_monitor[field]:
            raise EvidenceValidationError(
                f"notify_monitor.{field} must match the source contract: {expected_monitor[field]!r}"
            )
    _require_bool(monitor["active"], True, "notify_monitor.active")
    _require_positive_int(monitor["max_retries"], "notify_monitor.max_retries", allow_zero=True)
    _require_positive_int(monitor["retry_interval_seconds"], "notify_monitor.retry_interval_seconds")
    _require_positive_int(monitor["request_timeout_seconds"], "notify_monitor.request_timeout_seconds")
    _require_bool(monitor["tls_verification_enabled"], True, "notify_monitor.tls_verification_enabled")
    assignments = monitor["notification_assignment_identifiers"]
    if not isinstance(assignments, list) or not assignments:
        raise EvidenceValidationError(
            "notify_monitor.notification_assignment_identifiers must record at least one live assignment"
        )
    for index, assignment in enumerate(assignments):
        if isinstance(assignment, bool) or not isinstance(assignment, (str, int)):
            raise EvidenceValidationError(
                f"notify_monitor.notification_assignment_identifiers[{index}] must be a string or integer"
            )
        if isinstance(assignment, int):
            _require_positive_int(assignment, f"notify_monitor.notification_assignment_identifiers[{index}]")
        else:
            _require_non_placeholder_text(
                assignment,
                f"notify_monitor.notification_assignment_identifiers[{index}]",
            )

    source = evidence["source_path"]
    if not isinstance(source, dict):
        raise EvidenceValidationError("source_path must be an object")
    _require_exact_keys(
        source,
        {
            "observed_at_caddy",
            "observed_remote_address",
            "caddy_allowlist_values",
            "final_private_https_route_verified",
            "backend_socket_only",
            "database_aware_health_verified",
        },
        "source_path",
    )
    _require_bool(source["observed_at_caddy"], True, "source_path.observed_at_caddy")
    observed_ip = _require_ip(source["observed_remote_address"], "source_path.observed_remote_address")
    _require_allowlist_contains(source["caddy_allowlist_values"], observed_ip)
    _require_bool(
        source["final_private_https_route_verified"],
        True,
        "source_path.final_private_https_route_verified",
    )
    _require_bool(source["backend_socket_only"], False, "source_path.backend_socket_only")
    _require_bool(
        source["database_aware_health_verified"],
        True,
        "source_path.database_aware_health_verified",
    )

    transitions = evidence["state_transitions"]
    if not isinstance(transitions, dict):
        raise EvidenceValidationError("state_transitions must be an object")
    _require_exact_keys(
        transitions,
        {
            "healthy_no_false_alert",
            "down_detected",
            "down_observed_status_code",
            "recovered_detected",
            "recovered_observed_status_code",
            "observed_order",
        },
        "state_transitions",
    )
    _require_bool(
        transitions["healthy_no_false_alert"],
        True,
        "state_transitions.healthy_no_false_alert",
    )
    _require_bool(transitions["down_detected"], True, "state_transitions.down_detected")
    down_status = _require_positive_int(
        transitions["down_observed_status_code"],
        "state_transitions.down_observed_status_code",
    )
    if down_status < 400:
        raise EvidenceValidationError("state_transitions.down_observed_status_code must be an HTTP failure")
    _require_bool(transitions["recovered_detected"], True, "state_transitions.recovered_detected")
    if transitions["recovered_observed_status_code"] != 200:
        raise EvidenceValidationError("state_transitions.recovered_observed_status_code must be 200")
    if transitions["observed_order"] != ["DOWN", "RECOVERED"]:
        raise EvidenceValidationError("state_transitions.observed_order must be exactly ['DOWN', 'RECOVERED']")

    receipt = evidence["administrator_receipt"]
    if not isinstance(receipt, dict):
        raise EvidenceValidationError("administrator_receipt must be an object")
    _require_exact_keys(
        receipt,
        {
            "recipient_approved",
            "down_received",
            "recovered_received",
            "content_minimized",
        },
        "administrator_receipt",
    )
    for field in ("recipient_approved", "down_received", "recovered_received", "content_minimized"):
        _require_bool(receipt[field], True, f"administrator_receipt.{field}")

    expected_ntfy = contract["documented_ntfy_monitor_baseline_to_reverify_before_cutover"]
    ntfy = evidence["ntfy_preservation"]
    if not isinstance(ntfy, dict):
        raise EvidenceValidationError("ntfy_preservation must be an object")
    _require_exact_keys(
        ntfy,
        {
            "monitor_present",
            "monitor_active",
            "name",
            "type",
            "url",
            "interval_seconds",
            "max_retries",
            "retry_interval_seconds",
            "request_timeout_seconds",
            "notification_assignment_present",
        },
        "ntfy_preservation",
    )
    _require_bool(ntfy["monitor_present"], True, "ntfy_preservation.monitor_present")
    _require_bool(ntfy["monitor_active"], True, "ntfy_preservation.monitor_active")
    for field in (
        "name",
        "type",
        "url",
        "interval_seconds",
        "max_retries",
        "retry_interval_seconds",
        "request_timeout_seconds",
    ):
        if ntfy[field] != expected_ntfy[field]:
            raise EvidenceValidationError(
                f"ntfy_preservation.{field} does not match the documented baseline: {expected_ntfy[field]!r}"
            )
    _require_bool(
        ntfy["notification_assignment_present"],
        True,
        "ntfy_preservation.notification_assignment_present",
    )

    rollback = evidence["rollback"]
    if not isinstance(rollback, dict):
        raise EvidenceValidationError("rollback must be an object")
    _require_exact_keys(
        rollback,
        {
            "procedure_recorded",
            "ntfy_monitor_state_preserved",
            "notify_monitor_removal_or_disable_documented",
            "ntfy_route_restore_documented",
        },
        "rollback",
    )
    for field in rollback:
        _require_bool(rollback[field], True, f"rollback.{field}")

    independent = evidence["independent_out_of_band"]
    if not isinstance(independent, dict):
        raise EvidenceValidationError("independent_out_of_band must be an object")
    _require_exact_keys(
        independent,
        {
            "mechanism",
            "separate_failure_domain",
            "depends_on_notify",
            "depends_on_same_runtime_host",
            "controlled_notify_outage_tested",
            "approved_administrator_received_down",
        },
        "independent_out_of_band",
    )
    _require_non_placeholder_text(independent["mechanism"], "independent_out_of_band.mechanism")
    _require_bool(
        independent["separate_failure_domain"],
        True,
        "independent_out_of_band.separate_failure_domain",
    )
    _require_bool(independent["depends_on_notify"], False, "independent_out_of_band.depends_on_notify")
    _require_bool(
        independent["depends_on_same_runtime_host"],
        False,
        "independent_out_of_band.depends_on_same_runtime_host",
    )
    _require_bool(
        independent["controlled_notify_outage_tested"],
        True,
        "independent_out_of_band.controlled_notify_outage_tested",
    )
    _require_bool(
        independent["approved_administrator_received_down"],
        True,
        "independent_out_of_band.approved_administrator_received_down",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate sanitized target-environment Uptime Kuma/Caddy/alert evidence for "
            "GoreeCloud Notify issue #24. The validator does not activate or modify production."
        )
    )
    parser.add_argument("evidence", type=Path, help="path to sanitized target evidence JSON")
    parser.add_argument(
        "--expected-revision",
        required=True,
        help="exact 40-character Git SHA of the candidate intentionally under monitoring acceptance",
    )
    args = parser.parse_args(argv)

    try:
        evidence = _load_json(args.evidence)
        validate_evidence(evidence, args.expected_revision)
    except EvidenceValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    print("PASS: GoreeCloud Notify monitoring target evidence satisfies the source acceptance contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
