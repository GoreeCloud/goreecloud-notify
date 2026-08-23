# Android release signing and real-device acceptance

GoreeCloud Notify Android production signing remains an external acceptance operation. GitHub Actions must build an **unsigned** release APK and must not receive the production keystore, private key, keystore password, key password, or reusable signing credential.

## CI artifacts

The Native client build workflow produces two Android artifacts from the exact pull-request revision:

- `goreecloud-notify-android-apk`: debug acceptance APK for source/runtime troubleshooting;
- `goreecloud-notify-android-release-unsigned`: unsigned release acceptance APK for controlled external signing.

The workflow verifies that the release acceptance APK is unsigned before upload and records SHA-256 checksums for both APKs.

## External signing

Use `client/android/sign-release-apk.sh` only on an approved administrative system with the approved GoreeCloud Android signing keystore available outside the repository.

Required runtime environment variables:

- `GOREECLOUD_ANDROID_KEYSTORE_PASSWORD`
- `GOREECLOUD_ANDROID_KEY_PASSWORD`

Example:

```bash
export GOREECLOUD_ANDROID_KEYSTORE_PASSWORD='...'
export GOREECLOUD_ANDROID_KEY_PASSWORD='...'
client/android/sign-release-apk.sh \
  goreecloud-notify-android-release-unsigned.apk \
  goreecloud-notify-android-release-signed.apk \
  /approved/private/path/goreecloud-android-release.jks \
  goreecloud-notify
```

Do not place the keystore or passwords in Git, GitHub Actions secrets, issue comments, pull-request comments, Google Drive project documentation, shell history, or acceptance evidence. Record only public signer-certificate evidence, APK hashes, exact source revision, device/build information, and scenario outcomes.

## Acceptance evidence initialization

After installing the exact externally signed APK on the physical device, initialize a new evidence record before running acceptance scenarios:

```bash
bash client/android/collect-device-acceptance.sh \
  <40-character-source-revision> \
  goreecloud-notify-android-release-signed.apk \
  goreecloud-notify-android-device-acceptance.json
```

The collector fails closed unless the source revision is a full Git SHA, the supplied APK exists and has a valid Android signature, the signer certificate SHA-256 can be extracted, the package is installed, and an authorized ADB device is present. It records the signed APK SHA-256 and signer-certificate SHA-256 directly at collection time so those values cannot be silently omitted later. The raw ADB device serial is not stored; only a one-way SHA-256 identifier is retained for evidence correlation.

The generated JSON is only an evidence template. Every scenario remains `pending` and `accepted` remains `false` until the physical-device results are explicitly reviewed and recorded.

## Required real-device gate

A signed APK is not sufficient to close issue #81. Acceptance must be performed on representative physical Android hardware and must remain tied to the exact source revision and signed APK hash.

The acceptance session must cover:

1. install or upgrade the externally signed release APK and verify the expected signer certificate;
2. authenticate against the final `https://notify.goreecloud.com` authority and explicitly enable system alerts;
3. confirm delivery while the app is backgrounded;
4. terminate the Flutter process/application task and confirm a later notification is delivered by the native service without reopening the app;
5. reboot the device and confirm the user-enabled delivery service recovers and later delivers an alert;
6. exercise Doze/battery-optimization and restricted-app behavior, recording any Android-imposed limitations rather than hiding them;
7. disconnect the network, generate representative notifications, reconnect, and verify replay without duplicate user alerts;
8. verify privacy-safe lock-screen presentation and that private message content is not exposed by default;
9. verify sign-out disables native delivery and clears its stored authenticated session state;
10. send representative notifications from the documented GoreeCloud producers through the final production authority and confirm expected mobile delivery.

## Evidence validation before closure

After all physical-device scenarios have been reviewed, update each scenario status to `accepted`, set the top-level classification to `acceptance-evidence`, set `accepted` to `true`, and add at least one non-empty review note describing the acceptance review or relevant device limitation. Then run:

```bash
python3 client/android/validate-device-acceptance.py \
  goreecloud-notify-android-device-acceptance.json
```

The validator rejects unsupported schemas, non-final authorities, missing or malformed source/APK/signer digests, raw ADB serial retention, incomplete package/device metadata, missing or extra acceptance scenarios, any scenario not explicitly marked `accepted`, a false/missing top-level acceptance result, and empty/missing review notes. A validator pass is necessary evidence-integrity confirmation; it does not replace human review of the physical-device test results.

## Acceptance classification

Until every required real-device scenario is accepted and the completed evidence record passes `validate-device-acceptance.py`, PR #85 must remain a source/CI candidate and issue #81 must remain open. GoreeCloud Notify must not be described as ntfy-equivalent for Android background delivery, and issue #83 must not authorize ntfy retirement based on source or emulator evidence alone.
