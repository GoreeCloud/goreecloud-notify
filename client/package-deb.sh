#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-0.1.0}"
ARCH="${2:-amd64}"
BUNDLE="${3:-build/linux/x64/release/bundle}"
OUT="${4:-dist}"
PKG="goreecloud-notify_${VERSION}_${ARCH}"
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT

if [[ ! -x "$BUNDLE/goreecloud_notify_client" ]]; then
  echo "missing Linux release bundle: $BUNDLE" >&2
  exit 1
fi

install -d "$ROOT/DEBIAN" "$ROOT/usr/lib/goreecloud-notify" "$ROOT/usr/bin" \
  "$ROOT/usr/share/applications" "$ROOT/usr/share/icons/hicolor/scalable/apps"
cp -a "$BUNDLE/." "$ROOT/usr/lib/goreecloud-notify/"
ln -s ../lib/goreecloud-notify/goreecloud_notify_client "$ROOT/usr/bin/goreecloud-notify"

cat > "$ROOT/DEBIAN/control" <<EOF
Package: goreecloud-notify
Version: ${VERSION}
Section: net
Priority: optional
Architecture: ${ARCH}
Maintainer: GoreeCloud
Depends: libgtk-3-0, libsecret-1-0
Description: First-party GoreeCloud Notify client
 Native Linux client for the GoreeCloud Notify notification service.
EOF

cat > "$ROOT/usr/share/applications/goreecloud-notify.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=GoreeCloud Notify
Comment=Private GoreeCloud notifications
Exec=/usr/bin/goreecloud-notify
Icon=goreecloud-notify
Terminal=false
Categories=Network;Utility;
StartupNotify=true
EOF

install -m 0644 ../frontend/public/brand/goreecloud-notify-icon.svg \
  "$ROOT/usr/share/icons/hicolor/scalable/apps/goreecloud-notify.svg"

mkdir -p "$OUT"
dpkg-deb --root-owner-group --build "$ROOT" "$OUT/${PKG}.deb"
dpkg-deb --info "$OUT/${PKG}.deb"
