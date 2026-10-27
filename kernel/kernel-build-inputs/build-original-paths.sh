#!/bin/bash
set -euo pipefail
base=/opt/a05bd-camera
trap 'printf "%s\n" "$?" > /opt/a05bd-camera/build.exit' EXIT
export KBUILD_BUILD_USER=ut-builder KBUILD_BUILD_HOST=proxmox104
export KBUILD_BUILD_VERSION=6 KBUILD_BUILD_TIMESTAMP='Wed Oct 21 00:00:00 UTC 2026'
cd "$base/kernel-4.14"
args=(O="$base/out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CROSS_COMPILE_ARM32= CC=aarch64-linux-gnu-gcc-9 HOSTCC=gcc-9)
make "${args[@]}" olddefconfig
make "${args[@]}" KCFLAGS="-Wno-error=array-bounds -Wno-error=address-of-packed-member -Wno-error=stringop-truncation -Wno-error=stringop-overflow -Wno-error=missing-attributes -Wno-error=attribute-alias -Wno-error=restrict" -j4 Image.gz
sha256sum "$base/out/arch/arm64/boot/Image.gz" "$base/out/Module.symvers"
printf 'CAMERA_CROSS_BUILD_COMPLETE\n'
