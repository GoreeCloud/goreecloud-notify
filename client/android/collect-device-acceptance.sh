#!/usr/bin/env bash
set -euo pipefail

package_name=${GOREECLOUD_NOTIFY_ANDROID_PACKAGE:-com.goreecloud.goreecloud_notify_client}
output=${1:-goreecloud-notify-android-device-acceptance.json}

command -v adb >/dev/null 2>&1 || { echo "adb is required." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required." >&2; exit 1; }

serial=$(adb get-serialno)
[[ -n "$serial" && "$serial" != "unknown" ]] || { echo "No authorized Android device detected." >&2; exit 1; }

model=$(adb shell getprop ro.product.model | tr -d '\r')
manufacturer=$(adb shell getprop ro.product.manufacturer | tr -d '\r')
android_release=$(adb shell getprop ro.build.version.release | tr -d '\r')
sdk=$(adb shell getprop ro.build.version.sdk | tr -d '\r')
build_fingerprint=$(adb shell getprop ro.build.fingerprint | tr -d '\r')
package_dump=$(adb shell dumpsys package "$package_name" 2>/dev/null | tr -d '\r' || true)
[[ -n "$package_dump" ]] || { echo "Package is not installed: $package_name" >&2; exit 1; }

version_name=$(printf '%s\n' "$package_dump" | sed -n 's/.*versionName=//p' | head -n 1 | xargs)
version_code=$(printf '%s\n' "$package_dump" | sed -n 's/.*versionCode=\([0-9][0-9]*\).*/\1/p' | head -n 1)
first_install=$(printf '%s\n' "$package_dump" | sed -n 's/.*firstInstallTime=//p' | head -n 1 | xargs)
last_update=$(printf '%s\n' "$package_dump" | sed -n 's/.*lastUpdateTime=//p' | head -n 1 | xargs)

signer=$(printf '%s\n' "$package_dump" | sed -n 's/.*signatures=\[\(.*\)\].*/\1/p' | head -n 1)
notification_permission=$(adb shell cmd appops get "$package_name" POST_NOTIFICATION 2>/dev/null | tr -d '\r' || true)
battery_state=$(adb shell dumpsys deviceidle 2>/dev/null | grep -E 'mState=|mLightState=|mScreenOn=|mCharging=' | tr -d '\r' || true)
standby_bucket=$(adb shell am get-standby-bucket "$package_name" 2>/dev/null | tr -d '\r' || true)

export GC_SERIAL="$serial" GC_MODEL="$model" GC_MANUFACTURER="$manufacturer" GC_ANDROID_RELEASE="$android_release" GC_SDK="$sdk" GC_BUILD_FINGERPRINT="$build_fingerprint" GC_PACKAGE="$package_name" GC_VERSION_NAME="$version_name" GC_VERSION_CODE="$version_code" GC_FIRST_INSTALL="$first_install" GC_LAST_UPDATE="$last_update" GC_SIGNER="$signer" GC_NOTIFICATION_PERMISSION="$notification_permission" GC_BATTERY_STATE="$battery_state" GC_STANDBY_BUCKET="$standby_bucket" GC_OUTPUT="$output"

python3 - <<'PY'
import json
import os
from pathlib import Path

record = {
    "schema": "goreecloud-notify-android-device-acceptance/v1",
    "classification": "acceptance-evidence-template",
    "source_revision": None,
    "signed_apk_sha256": None,
    "signer_certificate_sha256": None,
    "device": {
        "adb_serial": os.environ["GC_SERIAL"],
        "manufacturer": os.environ["GC_MANUFACTURER"],
        "model": os.environ["GC_MODEL"],
        "android_release": os.environ["GC_ANDROID_RELEASE"],
        "sdk": os.environ["GC_SDK"],
        "build_fingerprint": os.environ["GC_BUILD_FINGERPRINT"],
    },
    "package": {
        "name": os.environ["GC_PACKAGE"],
        "version_name": os.environ["GC_VERSION_NAME"],
        "version_code": os.environ["GC_VERSION_CODE"],
        "first_install_time": os.environ["GC_FIRST_INSTALL"],
        "last_update_time": os.environ["GC_LAST_UPDATE"],
        "dumpsys_signer_summary": os.environ["GC_SIGNER"],
        "notification_permission": os.environ["GC_NOTIFICATION_PERMISSION"],
        "standby_bucket": os.environ["GC_STANDBY_BUCKET"],
    },
    "device_idle_snapshot": os.environ["GC_BATTERY_STATE"].splitlines(),
    "authority": "https://notify.goreecloud.com",
    "scenarios": {
        "background_delivery": "pending",
        "process_termination_delivery": "pending",
        "reboot_recovery": "pending",
        "doze_battery_behavior": "pending",
        "restricted_app_behavior": "pending",
        "network_loss_replay_no_duplicates": "pending",
        "lock_screen_privacy": "pending",
        "sign_out_clears_native_session": "pending",
        "representative_producer_delivery": "pending",
    },
    "notes": [],
    "accepted": False,
}

path = Path(os.environ["GC_OUTPUT"])
if path.exists():
    raise SystemExit(f"Refusing to overwrite existing evidence file: {path}")
path.write_text(json.dumps(record, indent=2) + "\n")
print(path)
PY
