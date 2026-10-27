#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
base=/opt/a05bd-release
rootfs=$base/rootfs-rc1
out=$base/rc1-images
trap 'rc=$?; echo "$rc" > /opt/a05bd-release/images-rc1.exit; exit "$rc"' EXIT
test "$(cat "$base/finish-rc1.exit")" = 0
mkdir "$out"
# Exactly 1MiB is kept outside ext4 for the bootloader's original AVB metadata.
truncate -s 6441402368 "$out/system.img"
mke2fs -F -t ext4 -b 4096 -I 256 -m 1 -L UTsystem -O ^orphan_file,^metadata_csum_seed -E lazy_itable_init=0,lazy_journal_init=0 -d "$rootfs" "$out/system.img"
e2fsck -fn "$out/system.img" > "$out/system-fsck.log" 2>&1
python3 - <<'PY'
import hashlib,struct
from pathlib import Path
base=Path('/opt/a05bd-system-migration');p=Path('/opt/a05bd-release/rc1-images/system.img');size=6442450944;end=size-1048576
meta=(base/'original-system-child-vbmeta.bin').read_bytes();assert hashlib.sha256(meta).hexdigest()=='f56990c67bdb68be645bec29f99e3ff1edf17fefc9c74d3143408b398313ec93'
footer=bytearray((base/'original-system-avb-footer.bin').read_bytes());assert footer[:4]==b'AVBf';struct.pack_into('>QQQ',footer,12,end,end,len(meta))
assert p.stat().st_size==end
with p.open('r+b') as f:
 f.truncate(size);f.seek(end);f.write(meta);f.seek(size-64);f.write(footer)
PY
e2fsck -fn "$out/system.img" > "$out/system-avb-fsck.log" 2>&1
truncate -s 7831272960 "$out/userdata-empty.img"
mke2fs -F -t ext4 -b 4096 -I 256 -m 0 -L UTdata -O ^orphan_file,^metadata_csum_seed -E lazy_itable_init=0,lazy_journal_init=0 "$out/userdata-empty.img"
e2fsck -fn "$out/userdata-empty.img" > "$out/userdata-fsck.log" 2>&1
for name in system.img userdata-empty.img; do
 gzip -1 -c "$out/$name" > "$out/$name.gz.partial"
 mv "$out/$name.gz.partial" "$out/$name.gz"
done
python3 - <<'PY'
from pathlib import Path
import hashlib,json
p=Path('/opt/a05bd-release/rc1-images');m={}
for n in ['system.img','system.img.gz','userdata-empty.img','userdata-empty.img.gz']:
 f=p/n
 with f.open('rb') as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
 m[n]={'bytes':f.stat().st_size,'sha256':h}
(p/'images.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
PY
