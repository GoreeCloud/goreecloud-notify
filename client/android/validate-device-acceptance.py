#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

REQUIRED_SCENARIOS = {
    "background_delivery",
    "process_termination_delivery",
    "reboot_recovery",
    "doze_battery_behavior",
    "restricted_app_behavior",
    "network_loss_replay_no_duplicates",
    "lock_screen_privacy",
    "sign_out_clears_native_session",
    "representative_producer_delivery",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def fail(message: str) -> None:
    raise SystemExit(f"invalid acceptance evidence: {message}")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] in {"-h", "--help"}:
        print("usage: validate-device-acceptance.py EVIDENCE.json")
        raise SystemExit(0 if len(sys.argv) == 2 else 2)

    path = Path(sys.argv[1])
    if not path.is_file():
        fail(f"file not found: {path}")

    try:
        record = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        fail(str(exc))

    if record.get("schema") != "goreecloud-notify-android-device-acceptance/v1":
        fail("unsupported schema")
    if record.get("classification") != "acceptance-evidence":
        fail("classification must be acceptance-evidence")
    if record.get("authority") != "https://notify.goreecloud.com":
        fail("authority must be final notify.goreecloud.com HTTPS authority")

    source_revision = record.get("source_revision")
    if not isinstance(source_revision, str) or not GIT_SHA.fullmatch(source_revision):
        fail("source_revision must be a full lowercase 40-character Git SHA")

    for field in ("signed_apk_sha256", "signer_certificate_sha256"):
        value = record.get(field)
        if not isinstance(value, str) or not SHA256.fullmatch(value):
            fail(f"{field} must be a lowercase SHA-256 digest")

    device = record.get("device")
    if not isinstance(device, dict):
        fail("device record is missing")
    device_id_hash = device.get("adb_serial_sha256")
    if not isinstance(device_id_hash, str) or not SHA256.fullmatch(device_id_hash):
        fail("device.adb_serial_sha256 must be a SHA-256 digest")
    if "adb_serial" in device:
        fail("raw ADB serial must not be retained")
    for field in ("manufacturer", "model", "android_release", "sdk", "build_fingerprint"):
        if not isinstance(device.get(field), str) or not device[field].strip():
            fail(f"device.{field} is required")

    package = record.get("package")
    if not isinstance(package, dict):
        fail("package record is missing")
    if package.get("name") != "com.goreecloud.goreecloud_notify_client":
        fail("unexpected Android package name")
    for field in ("version_name", "version_code", "notification_permission", "standby_bucket"):
        if not isinstance(package.get(field), str) or not package[field].strip():
            fail(f"package.{field} is required")

    scenarios = record.get("scenarios")
    if not isinstance(scenarios, dict):
        fail("scenarios record is missing")
    if set(scenarios) != REQUIRED_SCENARIOS:
        missing = sorted(REQUIRED_SCENARIOS - set(scenarios))
        extra = sorted(set(scenarios) - REQUIRED_SCENARIOS)
        fail(f"scenario set mismatch; missing={missing}, extra={extra}")
    incomplete = sorted(name for name, status in scenarios.items() if status != "accepted")
    if incomplete:
        fail(f"all scenarios must be accepted; incomplete={incomplete}")

    if record.get("accepted") is not True:
        fail("accepted must be true")

    notes = record.get("notes")
    if not isinstance(notes, list):
        fail("notes must be a list")
    if not notes or any(not isinstance(note, str) or not note.strip() for note in notes):
        fail("notes must contain at least one non-empty review note")

    print(f"valid acceptance evidence: {path}")


if __name__ == "__main__":
    main()
