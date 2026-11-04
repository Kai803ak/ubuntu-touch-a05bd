#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
base=/opt/a05bd-twrp-r11-20261104
root=/opt/a05bd-twrp-20261104/focal-host
trap 'rc=$?; echo "$rc" > /opt/a05bd-twrp-r11-20261104/build.exit; exit "$rc"' EXIT
python3 - <<'PY'
from pathlib import Path
b=Path('/opt/a05bd-twrp-r11-20261104')
p=Path('/opt/a05bd-twrp-20261104/focal-host/build/twrp/device/sts/a05bd/recovery/root/init.recovery.mt8168.rc')
assert p.read_bytes()==(b/'init.recovery.mt8168.rc.before').read_bytes(),'Unexpected prior source'
p.write_bytes((b/'init.recovery.mt8168.rc').read_bytes())
PY
chroot "$root" /bin/bash -se <<'INNER'
export LC_ALL=C.UTF-8 LANG=C.UTF-8
export ALLOW_MISSING_DEPENDENCIES=true USE_CCACHE=0
export BUILD_NUMBER=A05BD_UT_TWRP_R11_20261104
cd /build/twrp
source build/envsetup.sh
lunch omni_a05bd-eng
make -j2 recoveryimage
out=out/target/product/a05bd/recovery.img
test -s "$out"
test "$(stat -c %s "$out")" -le 16777216
cp "$out" /build/result/recovery-a05bd-ut-r11.img
sha256sum /build/result/recovery-a05bd-ut-r11.img
INNER
