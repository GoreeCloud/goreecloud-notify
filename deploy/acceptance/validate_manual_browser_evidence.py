from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CONTRACT_PATH = Path(__file__).with_name("manual_browser_os_acceptance.json")
EVIDENCE_KIND = "goreecloud-notify-manual-browser-os-acceptance"
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
DEFECT_ISSUE_RE = re.compile(
    r"^https://github\.com/GoreeCloud/goreecloud-notify/issues/[1-9][0-9]*$"
)
SENSITIVE_KEY_FRAGMENTS = (
    "authorization",
    "cookie",
    "csrf",
    "password",
    "private_key",
    "recovery_code",
    "secret",
    "token",
)
SAFE_SENSITIVE_ASSERTION_KEYS = {"reusable_secrets_recorded"}
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


def _require_optional_text(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _require_non_placeholder_text(value, path, max_length=200)


def _require_positive_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise EvidenceValidationError(f"{path} must be a positive integer")
    return value


def _require_timestamp(value: Any, path: str) -> None:
    text = _require_non_placeholder_text(value, path, max_length=100)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise EvidenceValidationError(f"{path} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EvidenceValidationError(f"{path} must include a timezone offset")


def _require_revision(value: Any, path: str) -> str:
    text = _require_non_placeholder_text(value, path, max_length=40).lower()
    if REVISION_RE.fullmatch(text) is None:
        raise EvidenceValidationError(f"{path} must be an exact 40-character lowercase Git SHA")
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


def _require_defect_issue_url(value: Any, path: str, *, required: bool) -> str | None:
    if value is None:
        if required:
            raise EvidenceValidationError(f"{path} must link the failed check to a dedicated issue")
        return None
    text = _require_non_placeholder_text(value, path, max_length=200)
    if DEFECT_ISSUE_RE.fullmatch(text) is None:
        raise EvidenceValidationError(
            f"{path} must be a GoreeCloud/goreecloud-notify GitHub issue URL"
        )
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
            "required_checks",
            "privacy_contract",
        },
        "contract",
    )
    if contract["schema_version"] != 1:
        raise EvidenceValidationError("source manual-acceptance contract schema_version must be 1")
    if contract["contract_kind"] != "goreecloud-notify-manual-browser-os-acceptance-contract":
        raise EvidenceValidationError("source manual-acceptance contract kind is invalid")
    if contract["state"] != "manual-evidence-required":
        raise EvidenceValidationError("source manual-acceptance contract is not in manual-evidence-required state")
    if contract["issue"] != 55:
        raise EvidenceValidationError("source manual-acceptance contract must remain bound to issue #55")

    checks = contract["required_checks"]
    if not isinstance(checks, list) or not checks:
        raise EvidenceValidationError("source manual-acceptance contract must define required checks")
    ids: list[str] = []
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise EvidenceValidationError(f"contract.required_checks[{index}] must be an object")
        _require_exact_keys(check, {"id", "category"}, f"contract.required_checks[{index}]")
        ids.append(_require_non_placeholder_text(check["id"], f"contract.required_checks[{index}].id"))
        _require_non_placeholder_text(check["category"], f"contract.required_checks[{index}].category")
    if len(ids) != len(set(ids)):
        raise EvidenceValidationError("source manual-acceptance contract contains duplicate check IDs")
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
            "sessions",
            "checks",
            "privacy",
        },
        "evidence",
    )
    if evidence["schema_version"] != 1:
        raise EvidenceValidationError("schema_version must be 1")
    if evidence["evidence_kind"] != EVIDENCE_KIND:
        raise EvidenceValidationError(f"evidence_kind must be {EVIDENCE_KIND!r}")
    _require_bool(evidence["sanitized"], True, "sanitized")
    _require_timestamp(evidence["captured_at"], "captured_at")

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
    candidate_url = _require_https_url(candidate["service_url"], "candidate.service_url")
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

    sessions = evidence["sessions"]
    if not isinstance(sessions, list) or not sessions:
        raise EvidenceValidationError("sessions must be a non-empty list of real manual acceptance sessions")
    session_by_id: dict[str, dict[str, Any]] = {}
    for index, session in enumerate(sessions):
        path = f"sessions[{index}]"
        if not isinstance(session, dict):
            raise EvidenceValidationError(f"{path} must be an object")
        _require_exact_keys(
            session,
            {
                "id",
                "captured_at",
                "browser_name",
                "browser_version",
                "operating_system",
                "operating_system_version",
                "device_class",
                "viewport_css_pixels",
                "screen_reader",
                "service_url",
                "build_revision",
            },
            path,
        )
        session_id = _require_non_placeholder_text(session["id"], f"{path}.id", max_length=100)
        if session_id in session_by_id:
            raise EvidenceValidationError(f"{path}.id must be unique")
        _require_timestamp(session["captured_at"], f"{path}.captured_at")
        for field in (
            "browser_name",
            "browser_version",
            "operating_system",
            "operating_system_version",
            "device_class",
        ):
            _require_non_placeholder_text(session[field], f"{path}.{field}", max_length=200)

        viewport = session["viewport_css_pixels"]
        if not isinstance(viewport, dict):
            raise EvidenceValidationError(f"{path}.viewport_css_pixels must be an object")
        _require_exact_keys(viewport, {"width", "height"}, f"{path}.viewport_css_pixels")
        _require_positive_int(viewport["width"], f"{path}.viewport_css_pixels.width")
        _require_positive_int(viewport["height"], f"{path}.viewport_css_pixels.height")

        screen_reader = session["screen_reader"]
        if not isinstance(screen_reader, dict):
            raise EvidenceValidationError(f"{path}.screen_reader must be an object")
        _require_exact_keys(screen_reader, {"name", "version"}, f"{path}.screen_reader")
        screen_reader_name = _require_optional_text(screen_reader["name"], f"{path}.screen_reader.name")
        screen_reader_version = _require_optional_text(
            screen_reader["version"], f"{path}.screen_reader.version"
        )
        if (screen_reader_name is None) != (screen_reader_version is None):
            raise EvidenceValidationError(
                f"{path}.screen_reader name and version must both be recorded or both be null"
            )

        session_url = _require_https_url(session["service_url"], f"{path}.service_url")
        if session_url != candidate_url:
            raise EvidenceValidationError(f"{path}.service_url must match candidate.service_url")
        session_revision = _require_revision(session["build_revision"], f"{path}.build_revision")
        if session_revision != candidate_revision:
            raise EvidenceValidationError(f"{path}.build_revision must match candidate.build_revision")
        session_by_id[session_id] = session

    required_ids = [check["id"] for check in contract["required_checks"]]
    required_id_set = set(required_ids)
    results = evidence["checks"]
    if not isinstance(results, list) or not results:
        raise EvidenceValidationError("checks must be a non-empty list")

    seen_ids: set[str] = set()
    failed_ids: list[str] = []
    for index, result in enumerate(results):
        path = f"checks[{index}]"
        if not isinstance(result, dict):
            raise EvidenceValidationError(f"{path} must be an object")
        _require_exact_keys(
            result,
            {"id", "session_id", "status", "evidence", "defect_issue_url"},
            path,
        )
        check_id = _require_non_placeholder_text(result["id"], f"{path}.id", max_length=120)
        if check_id not in required_id_set:
            raise EvidenceValidationError(f"{path}.id is not a required issue #55 check")
        if check_id in seen_ids:
            raise EvidenceValidationError(f"{path}.id is duplicated")
        seen_ids.add(check_id)

        session_id = _require_non_placeholder_text(
            result["session_id"], f"{path}.session_id", max_length=100
        )
        if session_id not in session_by_id:
            raise EvidenceValidationError(f"{path}.session_id does not identify a recorded session")
        if check_id.startswith("screen_reader."):
            screen_reader = session_by_id[session_id]["screen_reader"]
            if screen_reader["name"] is None or screen_reader["version"] is None:
                raise EvidenceValidationError(
                    f"{path} must reference a session with an actual screen reader and version"
                )

        status = result["status"]
        if status not in {"pass", "fail"}:
            raise EvidenceValidationError(f"{path}.status must be exactly 'pass' or 'fail'")
        _require_non_placeholder_text(result["evidence"], f"{path}.evidence", max_length=1000)
        if status == "fail":
            _require_defect_issue_url(
                result["defect_issue_url"], f"{path}.defect_issue_url", required=True
            )
            failed_ids.append(check_id)
        else:
            _require_defect_issue_url(
                result["defect_issue_url"], f"{path}.defect_issue_url", required=False
            )

    missing_ids = [check_id for check_id in required_ids if check_id not in seen_ids]
    if missing_ids:
        raise EvidenceValidationError(f"manual acceptance evidence is incomplete; missing checks={missing_ids}")
    if failed_ids:
        raise EvidenceValidationError(
            f"manual acceptance has failed checks linked to defects; failed checks={failed_ids}"
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
            "Validate sanitized real human/browser/OS acceptance evidence for GoreeCloud Notify "
            "issue #55. This validator checks evidence completeness and integrity; it does not "
            "perform or simulate the manual acceptance itself."
        )
    )
    parser.add_argument("evidence", type=Path, help="path to sanitized manual acceptance evidence JSON")
    parser.add_argument(
        "--expected-revision",
        required=True,
        help="exact 40-character Git SHA of the deployed candidate intentionally under acceptance",
    )
    args = parser.parse_args(argv)

    try:
        evidence = _load_json(args.evidence)
        validate_evidence(evidence, args.expected_revision)
    except EvidenceValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    print(
        "PASS: GoreeCloud Notify manual browser/OS evidence satisfies the source issue #55 acceptance contract"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
