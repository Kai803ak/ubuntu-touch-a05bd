#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
base=/opt/a05bd-charging-20261104
root=/opt/a05bd-twrp-20261104/focal-host
mkdir -p "$base"
trap 'rc=$?; echo "$rc" > /opt/a05bd-charging-20261104/build.exit; exit "$rc"' EXIT
python3 - <<'PY'
from pathlib import Path
import hashlib
p=Path('/opt/a05bd-twrp-20261104/focal-host/build/twrp/system/core/healthd/healthd_draw.cpp')
old=p.read_text();needle='void HealthdDraw::blank_screen(bool blank) { gr_fb_blank(blank); }'
assert old.count(needle)==1, 'Inspect existing source changes before rebuilding'
Path('/opt/a05bd-charging-20261104/healthd_draw.before.cpp').write_text(old)
patched=old.replace(needle,'''// A05BD: panel DPMS and system suspend are separate from LCD backlight.
// Keep scanning the framebuffer; blank only the backlight for reliable wake.
void HealthdDraw::blank_screen(bool blank) {
  const char* value = blank ? "0\\n" : "102\\n";
  int fd = open("/sys/class/leds/lcd-backlight/brightness", O_WRONLY | O_CLOEXEC);
  if (fd < 0) { LOGE("A05BD: cannot open LCD backlight\\n"); return; }
  size_t length = strlen(value);
  if (write(fd, value, length) != static_cast<ssize_t>(length))
    LOGE("A05BD: cannot set LCD backlight\\n");
  close(fd);
}''')
patched='#include <fcntl.h>\n#include <unistd.h>\n#include <string.h>\n'+patched
p.write_text(patched)
print('Patched healthd_draw source SHA256',hashlib.sha256(patched.encode()).hexdigest())
PY
chroot "$root" /bin/bash -se <<'INNER'
export LC_ALL=C.UTF-8 LANG=C.UTF-8
export ALLOW_MISSING_DEPENDENCIES=true USE_CCACHE=0
export BUILD_NUMBER=A05BD_CHARGER_20261104
cd /build/twrp
source build/envsetup.sh
lunch omni_a05bd-eng
make -j2 charger BOARD_CHARGER_ENABLE_SUSPEND=false
test -s out/target/product/a05bd/root/sbin/charger
cp out/target/product/a05bd/root/sbin/charger /build/result/charger-a05bd-nosuspend
sha256sum /build/result/charger-a05bd-nosuspend
git -C system/core diff -- healthd/healthd_draw.cpp > /build/result/a05bd-charger-backlight.patch
INNER
