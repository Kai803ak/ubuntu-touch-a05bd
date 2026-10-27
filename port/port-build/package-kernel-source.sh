#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
base=/opt/a05bd-release
src=/opt/a05bd-webengine/noble-host/opt/a05bd-camera
mkdir -p "$base/sources" "$base/logs" "$base/kernel-build-inputs"
trap 'rc=$?; echo "$rc" > /opt/a05bd-release/kernel-source.exit; exit "$rc"' EXIT
cp "$src/out/.config" "$base/kernel-build-inputs/kernel.config"
cp "$src/build.sh" "$base/kernel-build-inputs/build-original-paths.sh"
cp "$src/out/include/generated/compile.h" "$base/kernel-build-inputs/compile.h"
sha256sum "$src/out/arch/arm64/boot/Image.gz" > "$base/kernel-build-inputs/Image.gz.sha256"
chroot /opt/a05bd-webengine/noble-host aarch64-linux-gnu-gcc-9 --version | head -n 1 > "$base/kernel-build-inputs/compiler.txt"
# The explicit source tree and build inputs contain no userdata tree. Preserve
# source license notices and configuration, excluding generated object/private
# signing-key artifacts. No original file is deleted or changed.
test ! -e "$base/sources/kernel-4.14.87-a05bd-6-source.tar.gz"
tar --sort=name --numeric-owner --owner=0 --group=0 --mtime='2026-10-21 00:00Z' \
 --exclude=.git --exclude='._*' --exclude='*.o' --exclude='*.a' --exclude='*.ko' \
 --exclude='*.cmd' --exclude='*.mod.c' --exclude='*.before-whitelist.c' \
 --exclude='certs/signing_key.pem' \
 -czf "$base/sources/kernel-4.14.87-a05bd-6-source.tar.gz.partial" \
 -C "$src" kernel-4.14 -C "$base" kernel-build-inputs
mv "$base/sources/kernel-4.14.87-a05bd-6-source.tar.gz.partial" "$base/sources/kernel-4.14.87-a05bd-6-source.tar.gz"
sha256sum "$base/sources/kernel-4.14.87-a05bd-6-source.tar.gz" > "$base/sources/kernel-source.SHA256SUMS"
stat -c '%s %n' "$base/sources/kernel-4.14.87-a05bd-6-source.tar.gz"
