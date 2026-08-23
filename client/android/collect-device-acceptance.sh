#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  collect-device-acceptance.sh SOURCE_REVISION SIGNED_APK [OUTPUT_JSON]

The collector records non-secret physical-device acceptance context for the exact signed APK
under test. It hashes the ADB serial rather than storing the raw device identifier.
EOF
}

if [[ ${1:-} == "--help" || ${1:-} == "-h" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 2 || $# -gt 3 ]]; then
  usage >&2
  exit 2
fi

source_revision=$1
signed_apk=$2
output=${3:-goreecloud-notify-android-device-acceptance.json}
package_name=${GOREECLOUD_NOTIFY_ANDROID_PACKAGE:-com.goreecloud.goreecloud_notify_client}

[[ "$source_revision" =~ ^[0-9a-fA-F]{40}$ ]] || { echo "SOURCE_REVISION must be a full 40-character Git SHA." >&2; exit 1; }
[[ -f "$signed_apk" ]] || { echo "Signed APK not found: $signed_apk" >&2; exit 1; }
[[ ! -e "$output" ]] || { echo "Refusing to overwrite existing evidence file: $output" >&2; exit 1; }

command -v adb >/dev/null 2>&1 || { echo "adb is required." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required." >&2; exit 1; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required." >&2; exit 1; }

if [[ -n ${ANDROID_HOME:-} ]]; then
  apksigner=$(find "$ANDROID_HOME/build-tools" -type f -name apksigner -print 2>/dev/null | sort -V | tail -n 1)
else
  apksigner=$(command -v apksigner || true)
fi
[[ -n "$apksigner" && -x "$apksigner" ]] || { echo "Android apksigner was not found." >&2; exit 1; }
"$apksigner" verify --verbose --print-certs "$signed_apk" >/dev/null

serial=$(adb get-serialno)
[[ -n "$serial" && "$serial" != "unknown" ]] || { echo "No authorized Android device detected." >&2; exit 1; }
serial_hash=$(printf '%s' "$serial" | sha256sum | awk '{print $1}')
signed_apk_sha256=$(sha256sum "$signed_apk" | awk '{print $1}')
signer_certificate_sha256=$("$apksigner" verify --print-certs "$signed_apk" 2>/dev/null | sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -n 1 | tr -d '[:space:]')
[[ "$signer_certificate_sha256" =~ ^[0-9a-fA-F]{64}$ ]] || { echo "Unable to determine signer certificate SHA-256 digest." >&2; exit 1; }

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
notification_permission=$(adb shell cmd appops get "$package_name" POST_NOTIFICATION 2>/dev/null | tr -d '\r' || true)
battery_state=$(adb shell dumpsys deviceidle 2>/dev/null | grep -E 'mState=|mLightState=|mScreenOn=|mCharging=' | tr -d '\r' || true)
standby_bucket=$(adb shell am get-standby-bucket "$package_name" 2>/dev/null | tr -d '\r' || true)

export GC_SOURCE_REVISION="$source_revision" GC_SIGNED_APK_SHA256="$signed_apk_sha256" GC_SIGNER_CERT_SHA256="$signer_certificate_sha256" GC_SERIAL_HASH="$serial_hash" GC_MODEL="$model" GC_MANUFACTURER="$manufacturer" GC_ANDROID_RELEASE="$android_release" GC_SDK="$sdk" GC_BUILD_FINGERPRINT="$build_fingerprint" GC_PACKAGE="$package_name" GC_VERSION_NAME="$version_name" GC_VERSION_CODE="$version_code" GC_FIRST_INSTALL="$first_install" GC_LAST_UPDATE="$last_update" GC_NOTIFICATION_PERMISSION="$notification_permission" GC_BATTERY_STATE="$battery_state" GC_STANDBY_BUCKET="$standby_bucket" GC_OUTPUT="$output"

python3 - <<'PY'
import json
import os
from pathlib import Path

record = {
    "schema": "goreecloud-notify-android-device-acceptance/v2",
    "classification": "acceptance-evidence-template",
    "source_revision": os.environ["GC_SOURCE_REVISION"].lower(),
    "signed_apk_sha256": os.environ["GC_SIGNED_APK_SHA256"].lower(),
    "signer_certificate_sha256": os.environ["GC_SIGNER_CERT_SHA256"].lower(),
    "device": {
        "adb_serial_sha256": os.environ["GC_SERIAL_HASH"].lower(),
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
path.write_text(json.dumps(record, indent=2) + "\n")
print(path)
PY
