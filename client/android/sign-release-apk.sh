#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  sign-release-apk.sh INPUT_UNSIGNED_APK OUTPUT_SIGNED_APK KEYSTORE KEY_ALIAS

Required environment variables:
  GOREECLOUD_ANDROID_KEYSTORE_PASSWORD
  GOREECLOUD_ANDROID_KEY_PASSWORD

The keystore and passwords must be supplied outside the repository. The script refuses
in-place signing, refuses to overwrite an existing output, verifies the final APK signature,
and emits SHA-256 plus signer-certificate evidence for acceptance records.
EOF
}

if [[ ${1:-} == "--help" || ${1:-} == "-h" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 4 ]]; then
  usage >&2
  exit 2
fi

input_apk=$1
output_apk=$2
keystore=$3
key_alias=$4

: "${GOREECLOUD_ANDROID_KEYSTORE_PASSWORD:?GOREECLOUD_ANDROID_KEYSTORE_PASSWORD is required}"
: "${GOREECLOUD_ANDROID_KEY_PASSWORD:?GOREECLOUD_ANDROID_KEY_PASSWORD is required}"

[[ -f "$input_apk" ]] || { echo "Input APK not found: $input_apk" >&2; exit 1; }
[[ -f "$keystore" ]] || { echo "Keystore not found: $keystore" >&2; exit 1; }
[[ "$input_apk" != "$output_apk" ]] || { echo "Refusing in-place signing." >&2; exit 1; }
[[ ! -e "$output_apk" ]] || { echo "Refusing to overwrite existing output: $output_apk" >&2; exit 1; }

if [[ -n ${ANDROID_HOME:-} ]]; then
  apksigner=$(find "$ANDROID_HOME/build-tools" -type f -name apksigner -print 2>/dev/null | sort -V | tail -n 1)
else
  apksigner=$(command -v apksigner || true)
fi

[[ -n "$apksigner" && -x "$apksigner" ]] || { echo "Android apksigner was not found." >&2; exit 1; }

if "$apksigner" verify "$input_apk" >/dev/null 2>&1; then
  echo "Input APK is already signed; expected an unsigned release acceptance artifact." >&2
  exit 1
fi

cp -- "$input_apk" "$output_apk"

"$apksigner" sign \
  --ks "$keystore" \
  --ks-key-alias "$key_alias" \
  --ks-pass env:GOREECLOUD_ANDROID_KEYSTORE_PASSWORD \
  --key-pass env:GOREECLOUD_ANDROID_KEY_PASSWORD \
  "$output_apk"

"$apksigner" verify --verbose --print-certs "$output_apk"
sha256sum "$input_apk" "$output_apk"
