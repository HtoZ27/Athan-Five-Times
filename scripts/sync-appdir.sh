#!/usr/bin/env bash
# sync-appdir.sh — single-source sync from repo root into AppDir.
# Usage: bash scripts/sync-appdir.sh [--check-only]
# Eliminates the manual-copy drift that once shipped a broken AppImage:
# root qml/ backend/ assets/ are the ONLY source of truth.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/AppDir/usr/share/prayer_app"
CHECK_ONLY=0
if [ "${1:-}" = "--check-only" ]; then CHECK_ONLY=1; fi

fail() { echo "DRIFT: $1" >&2; exit 1; }

if [ "$CHECK_ONLY" -eq 1 ]; then
    leftovers=$(diff -rq "$ROOT/qml" "$DEST/qml" || true)
    [ -z "$leftovers" ] || fail "qml/ differs: $leftovers"
    leftovers=$(diff -rq --exclude=__pycache__ "$ROOT/backend" "$DEST/backend" || true)
    [ -z "$leftovers" ] || fail "backend/ differs: $leftovers"
    leftovers=$(diff -rq "$ROOT/assets" "$DEST/assets" || true)
    [ -z "$leftovers" ] || fail "assets/ differ: $leftovers"
    [ -f "$DEST/qml/PrayerIcon.qml" ] || fail "PrayerIcon.qml missing in AppDir"
    n=$(ls "$DEST/assets/prayer_icons/"*_{active,inactive}.png 2>/dev/null | wc -l)
    [ "$n" -eq 14 ] || fail "prayer_icons incomplete in AppDir ($n/14)"
    echo "AppDir in sync (modulo known orphans)"
    exit 0
fi

rm -rf "$DEST/qml" "$DEST/backend" "$DEST/assets"
mkdir -p "$DEST"
cp -a "$ROOT/qml" "$DEST/qml"
cp -a "$ROOT/backend" "$DEST/backend"
cp -a "$ROOT/assets" "$DEST/assets"
# Never ship dev-only / stale files:
rm -rf "$DEST/backend/__pycache__" "$DEST/backend/translations/__pycache__" \
       "$DEST/backend/requirements.txt" "$DEST/backend/test2.txt" \
       "$DEST/backend/athkar.py" "$DEST/qml/Palette.qml"
# Re-create the blessed assets symlink (cp -a would copy the target):
rm -rf "$DEST/backend/assets" && ln -s ../assets "$DEST/backend/assets"
echo "Synced root -> AppDir, orphans pruned"
bash "$0" --check-only
