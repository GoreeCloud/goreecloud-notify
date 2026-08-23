# GoreeCloud Notify Application Identity

GoreeCloud Notify uses one canonical first-party product identity across the web application and the first-party native clients.

## Canonical identity

- Product name: `GoreeCloud Notify`
- Short product label: `Notify`
- Canonical scalable mark: `frontend/public/brand/goreecloud-notify-icon.svg`
- Design language: Glaze UI
- Security identity: Wardveil Security by GoreeCloud
- Privacy identity: GoreeCloud Privacy Shield

The canonical SVG is the source asset for web metadata and for package-specific icon derivatives. Platform packaging must not introduce unrelated or upstream product branding.

## Web contract

The web application reuses the canonical SVG for its favicon, installable web-app manifest, and product-mark surfaces. The manifest presents the product as `GoreeCloud Notify` / `Notify` and uses standalone display behavior.

## Linux contract

Linux delivery is a native Flutter desktop client packaged as an amd64 Debian package:

- package name: `goreecloud-notify`
- executable: `/usr/bin/goreecloud-notify`
- application display name: `GoreeCloud Notify`
- artifact pattern: `goreecloud-notify_<version>_amd64.deb`
- icon source: the canonical GoreeCloud Notify SVG

The Debian package installs the Flutter release bundle under `/usr/lib/goreecloud-notify`, exposes a freedesktop desktop entry, and declares the GTK/libsecret runtime dependencies required by the client.

## Android contract

Android delivery is a first-party Flutter client, not a WebView wrapper. The acceptance artifact uses:

- application identity: `com.goreecloud.goreecloud_notify_client`
- application display name: `GoreeCloud Notify`
- acceptance artifact: `goreecloud-notify-android-acceptance.apk`
- icon source: the canonical GoreeCloud Notify SVG

The GitHub Actions acceptance build is installable for device testing but is intentionally not a production-signed Store release. Production signing keys and other reusable signing material must remain outside source control.

## Native-client privacy and authentication boundary

The native client authenticates against the existing human-session API. It stores only the opaque session cookie and CSRF token through the platform secure-storage provider; it does not retain the user's password after login. Native operating-system notification previews are redacted so private notification content is not exposed on a lock screen by default.

## Android background-delivery gate

The initial Android client maintains the realtime SSE stream while its process remains running. That behavior is not sufficient to claim ntfy-equivalent persistent mobile delivery. GoreeCloud Notify may retire ntfy as the phone's independent alert path only after persistent Android delivery has been implemented and independently accepted across backgrounding, process termination, device reboot, Doze/battery restrictions, and the approved production-signing path.

## Acceptance rule

A generated `.deb` or APK is an acceptance artifact, not proof of production readiness. Production claims require the repository's normal release, security, runtime, client, and migration gates to pass for the exact candidate revision.
