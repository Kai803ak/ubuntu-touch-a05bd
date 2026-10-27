#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
base=/opt/a05bd-release
src=/opt/a05bd-webengine/noble-host/build/qt6-webengine-6.11.2
out=$base/sources/qt6-webengine-6.11.2-a05bd-r5-source.tar.gz
trap 'rc=$?; echo "$rc" > /opt/a05bd-release/qt-source.exit; exit "$rc"' EXIT
test -d "$src/src/3rdparty/chromium"
test ! -e "$out"
tar --sort=name --numeric-owner --owner=0 --group=0 --mtime='2026-10-27 00:00:00 UTC' --exclude='.git' --exclude='__pycache__' -C "$(dirname "$src")" -cf - "$(basename "$src")" | gzip -1 > "$out.partial"
mv "$out.partial" "$out"
sha256sum "$out" > "$out.sha256"
stat -c '%s bytes' "$out"
