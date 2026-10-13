#!/usr/bin/env bash
# Build the .rpm package (requires rpmbuild, e.g. Fedora/openSUSE).
# Usage: bash packaging/rpm/build-rpm.sh [version]
set -euo pipefail
umask 022

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-$(python3 -c "import re; print(re.search(r'version\s*=\s*\"([^\"]+)\"', open('$ROOT/pyproject.toml').read()).group(1))")}"

if ! command -v rpmbuild >/dev/null; then
  echo "rpmbuild not found (install rpm-build / rpm-build tools first)" >&2
  exit 1
fi

TOPDIR="$(mktemp -d)/rpmbuild"
trap 'rm -rf "$(dirname "$TOPDIR")"' EXIT
mkdir -p "$TOPDIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

TARBALL="$TOPDIR/SOURCES/v$VERSION.tar.gz"
git -C "$ROOT" archive --format=tar.gz --prefix="Athan-Five-Times-$VERSION/" \
  HEAD > "$TARBALL"
cp "$ROOT/packaging/rpm/athan-five-times.spec" "$TOPDIR/SPECS/"

rpmbuild --define "_topdir $TOPDIR" -bb "$TOPDIR/SPECS/athan-five-times.spec"
find "$TOPDIR/RPMS" -name "*.rpm" -exec cp {} "$ROOT/" \;
echo "Built RPM(s) in $ROOT"
