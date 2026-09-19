from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).with_name("notify_monitoring_contract.json")
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


def _fail(message: str) -> None:
    raise EvidenceValidationError(message)


def _exact_keys(value: Any, expected: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{path} must be an object")
    actual = set(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if unexpected:
            details.append(f"unexpected={unexpected}")
        _fail(f"{path} has invalid fields ({', '.join(details)})")
    return value


def _bool(value: Any, expected: bool, path: str) -> None:
    if value is not expected:
        _fail(f"{path} must be {expected!r}")


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str):
        _fail(f"{path} must be a string")
    text = value.strip()
    if not text or text.lower() in PLACEHOLDER_VALUES:
        _fail(f"{path} must contain a concrete recorded value")
    return text


def _revision(value: Any, path: str) -> str:
    text = _text(value, path).lower()
    if REVISION_RE.fullmatch(text) is None:
        _fail(f"{path} must be an exact 40-character lowercase Git SHA")
    return text


def _positive_int(value: Any, path: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(f"{path} must be an integer")
    minimum = 0 if allow_zero else 1
    if value < minimum:
        _fail(f"{path} must be >= {minimum}")
    return value


def _timestamp(value: Any, path: str) -> None:
    text = _text(value, path)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise EvidenceValidationError(f"{path} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        _fail(f"{path} must include a timezone")


def _reject_sensitive_fields(value: Any, path: str = "evidence") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lower = key.lower()
            if any(fragment in lower for fragment in SENSITIVE_KEY_FRAGMENTS):
                _fail(f"{path}.{key} is a prohibited sensitive-data field")
            _reject_sensitive_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive_fields(child, f"{path}[{index}]")


def _source_is_authorized(observed: str, allowlist: list[str]) -> bool:
    try:
        address = ipaddress.ip_address(observed)
    except ValueError:
        return False
    for item in allowlist:
        try:
            network = ipaddress.ip_network(item, strict=False)
        except ValueError:
            continue
        if address in network:
            return True
    return False


def validate_evidence(evidence: dict[str, Any], expected_revision: str) -> None:
    _reject_sensitive_fields(evidence)
    expected_revision = _revision(expected_revision, "expected_revision")

    root = _exact_keys(
        evidence,
        {
            "schema_version",
            "evidence_kind",
            "sanitized",
            "captured_at",
            "candidate",
            "monitor_provider",
            "state_transitions",
            "administrator_receipt",
            "rollback",
            "independent_out_of_band",
        },
        "evidence",
    )
    if root["schema_version"] != 3:
        _fail("schema_version must be 3")
    if root["evidence_kind"] != EVIDENCE_KIND:
        _fail(f"evidence_kind must be {EVIDENCE_KIND!r}")
    _bool(root["sanitized"], True, "sanitized")
    _timestamp(root["captured_at"], "captured_at")

    candidate = _exact_keys(
        root["candidate"],
        {
            "service_url",
            "build_revision",
            "release_stage",
            "production_accepted",
            "acceptance_status",
        },
        "candidate",
    )
    if _text(candidate["service_url"], "candidate.service_url") != "https://notify.goreecloud.com":
        _fail("candidate.service_url must match the final Notify origin")
    if _revision(candidate["build_revision"], "candidate.build_revision") != expected_revision:
        _fail("candidate.build_revision must match the explicitly expected deployed revision")
    if candidate["release_stage"] != "release_candidate":
        _fail("candidate.release_stage must remain release_candidate")
    _bool(candidate["production_accepted"], False, "candidate.production_accepted")
    if candidate["acceptance_status"] != "pending":
        _fail("candidate.acceptance_status must remain pending")

    monitor = _exact_keys(
        root["monitor_provider"],
        {
            "provider",
            "provider_build_revision",
            "provider_production_accepted",
            "monitor_id",
            "monitor_name",
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
            "observed_at_gateway",
            "observed_remote_address",
            "gateway_allowlist_values",
            "final_private_https_route_verified",
            "backend_socket_only",
            "database_aware_health_verified",
        },
        "monitor_provider",
    )
    if monitor["provider"] != "GoreeCloud Monitor":
        _fail("monitor_provider.provider must be GoreeCloud Monitor")
    _revision(monitor["provider_build_revision"], "monitor_provider.provider_build_revision")
    _bool(
        monitor["provider_production_accepted"],
        True,
        "monitor_provider.provider_production_accepted",
    )
    _text(monitor["monitor_id"], "monitor_provider.monitor_id")
    if monitor["monitor_name"] != "GoreeCloud Notify":
        _fail("monitor_provider.monitor_name must be GoreeCloud Notify")
    if monitor["type"] != "http" or monitor["method"] != "GET":
        _fail("monitor_provider must use HTTP GET")
    if monitor["url"] != "https://notify.goreecloud.com/healthz":
        _fail("monitor_provider.url must use the final private HTTPS health route")
    _bool(monitor["active"], True, "monitor_provider.active")
    _positive_int(monitor["interval_seconds"], "monitor_provider.interval_seconds")
    _positive_int(monitor["max_retries"], "monitor_provider.max_retries", allow_zero=True)
    _positive_int(
        monitor["retry_interval_seconds"],
        "monitor_provider.retry_interval_seconds",
    )
    _positive_int(
        monitor["request_timeout_seconds"],
        "monitor_provider.request_timeout_seconds",
    )
    if monitor["accepted_status_codes"] != [200]:
        _fail("monitor_provider.accepted_status_codes must equal [200]")
    _bool(
        monitor["tls_verification_enabled"],
        True,
        "monitor_provider.tls_verification_enabled",
    )
    _bool(monitor["observed_at_gateway"], True, "monitor_provider.observed_at_gateway")
    observed = _text(
        monitor["observed_remote_address"],
        "monitor_provider.observed_remote_address",
    )
    allowlist = monitor["gateway_allowlist_values"]
    if not isinstance(allowlist, list) or not allowlist:
        _fail("monitor_provider.gateway_allowlist_values must be a non-empty list")
    allowlist = [
        _text(value, f"monitor_provider.gateway_allowlist_values[{index}]")
        for index, value in enumerate(allowlist)
    ]
    if not _source_is_authorized(observed, allowlist):
        _fail("monitor_provider.gateway_allowlist_values must authorize the observed source")
    _bool(
        monitor["final_private_https_route_verified"],
        True,
        "monitor_provider.final_private_https_route_verified",
    )
    _bool(monitor["backend_socket_only"], False, "monitor_provider.backend_socket_only")
    _bool(
        monitor["database_aware_health_verified"],
        True,
        "monitor_provider.database_aware_health_verified",
    )

    transitions = _exact_keys(
        root["state_transitions"],
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
    for field in ("healthy_no_false_alert", "down_detected", "recovered_detected"):
        _bool(transitions[field], True, f"state_transitions.{field}")
    _positive_int(
        transitions["down_observed_status_code"],
        "state_transitions.down_observed_status_code",
    )
    if transitions["recovered_observed_status_code"] != 200:
        _fail("state_transitions.recovered_observed_status_code must be 200")
    if transitions["observed_order"] != ["DOWN", "RECOVERED"]:
        _fail("state_transitions.observed_order must equal ['DOWN', 'RECOVERED']")

    receipt = _exact_keys(
        root["administrator_receipt"],
        {
            "recipient_approved",
            "down_received",
            "recovered_received",
            "content_minimized",
        },
        "administrator_receipt",
    )
    for field in receipt:
        _bool(receipt[field], True, f"administrator_receipt.{field}")

    rollback = _exact_keys(
        root["rollback"],
        {
            "procedure_recorded",
            "monitor_disable_or_remove_documented",
            "previous_notify_release_recovery_documented",
            "uptime_kuma_production_restore_required",
        },
        "rollback",
    )
    _bool(rollback["procedure_recorded"], True, "rollback.procedure_recorded")
    _bool(
        rollback["monitor_disable_or_remove_documented"],
        True,
        "rollback.monitor_disable_or_remove_documented",
    )
    _bool(
        rollback["previous_notify_release_recovery_documented"],
        True,
        "rollback.previous_notify_release_recovery_documented",
    )
    _bool(
        rollback["uptime_kuma_production_restore_required"],
        False,
        "rollback.uptime_kuma_production_restore_required",
    )

    independent = _exact_keys(
        root["independent_out_of_band"],
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
    _text(independent["mechanism"], "independent_out_of_band.mechanism")
    _bool(
        independent["separate_failure_domain"],
        True,
        "independent_out_of_band.separate_failure_domain",
    )
    _bool(independent["depends_on_notify"], False, "independent_out_of_band.depends_on_notify")
    _bool(
        independent["depends_on_same_runtime_host"],
        False,
        "independent_out_of_band.depends_on_same_runtime_host",
    )
    _bool(
        independent["controlled_notify_outage_tested"],
        True,
        "independent_out_of_band.controlled_notify_outage_tested",
    )
    _bool(
        independent["approved_administrator_received_down"],
        True,
        "independent_out_of_band.approved_administrator_received_down",
    )


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceValidationError(f"could not read valid JSON evidence: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceValidationError("evidence root must be an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path, help="path to sanitized target evidence JSON")
    parser.add_argument(
        "--expected-revision",
        required=True,
        help="exact 40-character Git SHA of the Notify candidate under monitoring acceptance",
    )
    args = parser.parse_args(argv)

    try:
        evidence = _load_json(args.evidence)
        validate_evidence(evidence, args.expected_revision)
    except EvidenceValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    print("PASS: GoreeCloud Notify monitoring target evidence satisfies the post-retirement acceptance contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
