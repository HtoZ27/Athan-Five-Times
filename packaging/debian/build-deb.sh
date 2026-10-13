#!/usr/bin/env bash
# Build the .deb package (requires dpkg-deb).
# Usage: bash packaging/debian/build-deb.sh [version]  (default: pyproject version)
set -euo pipefail
umask 022

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-$(python3 -c "import re; print(re.search(r'version\s*=\s*\"([^\"]+)\"', open('$ROOT/pyproject.toml').read()).group(1))")}"
PKGDIR="$(mktemp -d)/athan-five-times_${VERSION}_all"
trap 'rm -rf "$(dirname "$PKGDIR")"' EXIT

APP="$PKGDIR/usr/share/athan-five-times"
mkdir -p "$APP" "$PKGDIR/usr/bin" \
         "$PKGDIR/usr/share/applications" \
         "$PKGDIR/usr/share/icons/hicolor/scalable/apps" \
         "$PKGDIR/usr/share/doc/athan-five-times" \
         "$PKGDIR/DEBIAN"

cp -a "$ROOT/backend" "$ROOT/qml" "$ROOT/assets" "$APP/"
find "$APP" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
cp "$ROOT/packaging/common/athan-five-times" "$PKGDIR/usr/bin/"
cp "$ROOT/packaging/common/com.azanprayer.app.desktop" \
   "$PKGDIR/usr/share/applications/"
cp "$ROOT/assets/kaaba.svg" \
   "$PKGDIR/usr/share/icons/hicolor/scalable/apps/com.azanprayer.app.svg"
chmod 755 "$PKGDIR/usr/bin/athan-five-times"
find "$PKGDIR/usr" -type d -exec chmod 755 {} +
find "$APP" "$PKGDIR/usr/share/doc" -type f -exec chmod 644 {} +
chmod 755 "$PKGDIR/usr/bin/athan-five-times"
mkdir -p "$PKGDIR/usr/share/man/man1"
cat > "$PKGDIR/usr/share/man/man1/athan-five-times.1" <<'MAN'
.TH ATHAN-FIVE-TIMES 1 "2026" "0.3.0" "User Commands"
.SH NAME
athan-five-times \- Islamic prayer times with azan audio and adhkar
.SH SYNOPSIS
.B athan-five-times
.RI [ options ]
.SH DESCRIPTION
Desktop prayer-times application (PySide6/Qt6): prayer calculation,
streaming azan audio, structured adhkar library, system tray and
do-not-disturb automation.
.SH OPTIONS
The application is configured through its settings dialog; no command-line
options are currently defined.
.SH FILES
.I ~/.config/athan-five-times/settings.json
.SH AUTHOR
H.Z.Tun
MAN
gzip -9 "$PKGDIR/usr/share/man/man1/athan-five-times.1"
cp "$ROOT/LICENSE" "$PKGDIR/usr/share/doc/athan-five-times/copyright"
{ echo "athan-five-times ($VERSION) unstable; urgency=medium"; echo;
  git -C "$ROOT" log --oneline -5 2>/dev/null | cut -c1-75 | sed 's/^/  * /';
  echo; echo " -- H.Z.Tun <htoz27@users.noreply.github.com>  $(date -R)"; } \
  | gzip -9 > "$PKGDIR/usr/share/doc/athan-five-times/changelog.gz"

cat > "$PKGDIR/DEBIAN/control" <<EOF
Package: athan-five-times
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Maintainer: H.Z.Tun <htoz27@users.noreply.github.com>
Depends: python3 (>= 3.10), python3-pyside6.qtcore, python3-pyside6.qtgui, python3-pyside6.qtwidgets, python3-pyside6.qtqml, python3-pyside6.qtquick, python3-pyside6.qtquickcontrols2, python3-pyside6.qtsvg
Recommends: libnotify-bin
Description: Islamic prayer times with azan audio and adhkar
 Desktop prayer-times application with streaming azan audio, a structured
 adhkar library, system-tray integration, do-not-disturb automation and
 17 interface languages. Built with PySide6/Qt6.
 .
 Prayer calculation (adhan) and audio decoding (miniaudio) come from PyPI:
     pip install adhan miniaudio
EOF

dpkg-deb --root-owner-group --build "$PKGDIR" "$ROOT/athan-five-times_${VERSION}_all.deb"
echo "Built: $ROOT/athan-five-times_${VERSION}_all.deb"
