#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Static validation only; never opens a device or writes a partition."""
import hashlib
import json
import lzma
from pathlib import Path
import stat
import struct
import sys

image = Path(sys.argv[1])
out = image.parent
data = image.read_bytes()
assert data[:8] == b'ANDROID!' and 0 < len(data) <= 16777216
klen, rlen, page, version = [struct.unpack_from('<I', data, i)[0] for i in [8,16,36,40]]
assert page == 2048 and version == 1
align = lambda n: (n+page-1)//page*page
k = data[page:page+klen]
rstart = page+align(klen)
r = data[rstart:rstart+rlen]
dlen, doffset = struct.unpack_from('<IQ', data, 1632)
dtbo = data[doffset:doffset+dlen]
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(k) == 'bfb501fe4aba8eb573759403138e90f344970fa55514a35070e1a0f37e10f446'
assert sha(dtbo) == 'e3f6c95f11b31487b749e1314b40da78ab4ec4c1eaf9108d1504803a530007ea'
raw = lzma.decompress(r)
files = {}
offset = 0
while offset+110 <= len(raw):
    assert raw[offset:offset+6] in (b'070701', b'070702')
    f = [int(raw[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
    size, namesize = f[6], f[11]
    name = raw[offset+110:offset+110+namesize-1].decode().removeprefix('./')
    offset = (offset+110+namesize+3)//4*4
    assert offset+size <= len(raw)
    body = raw[offset:offset+size]
    offset = (offset+size+3)//4*4
    if name == 'TRAILER!!!':
        break
    assert name not in files
    files[name] = {'body': body, 'mode': f[1]}
for name in ['init','init.rc','sbin/recovery','sbin/teamwin','sbin/adbd','sbin/sh',
             'sbin/unzip','sbin/tar','sbin/gzip','sbin/a05bd_recovery_watchdog',
             'etc/recovery.fstab','init.recovery.mt8168.rc','init.recovery.usb.rc',
             'twres/languages/en.xml']:
    assert name in files, name
for name in ['sbin/a05bd_recovery_watchdog','sbin/recovery','sbin/adbd']:
    body = files[name]['body']
    assert body[:4] == b'\x7fELF' and struct.unpack_from('<H',body,18)[0] == 183
rc = files['init.rc']['body'].decode()
assert '--root_seclabel=u:r:recovery:s0' in rc and 'seclabel u:r:adbd:s0' not in rc
device = files['init.recovery.mt8168.rc']['body'].decode()
assert 'start a05bd_recovery_watchdog' in device and 'on boot\n' in device and '    restart adbd' in device
assert 'a05bd-recovery-serial' not in device
assert 'mount functionfs' not in rc
assert device.index('mkdir /config/usb_gadget/g1/functions/ffs.adb') < device.index('mount functionfs')
assert device.index('setprop sys.usb.ffs.aio_compat true') < device.index('mount functionfs')
fstab = files['etc/recovery.fstab']['body'].decode()
assert fstab.count('fsflags=ro') == 2 and '/ubuntu-data ext4 /dev/block/mmcblk0p32' in fstab
assert 'forcefde' not in fstab
assert 'sbin/a05bd-recovery-serial.sh' not in files
result = {'image': image.name, 'bytes': len(data), 'sha256': sha(data),
          'partition_bytes': 16777216, 'free_bytes': 16777216-len(data),
          'kernel_sha256': sha(k), 'dtbo_sha256': sha(dtbo), 'ramdisk_entries':len(files),
          'arm64_binaries_checked':['recovery','adbd','a05bd_recovery_watchdog'],
          'scope':'Static R11 validation; device installation results recorded separately',
          'device_tested': False}
(out/'recovery-validation.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'recovery-ramdisk-files.txt').write_text('\n'.join(sorted(files))+'\n')
print(json.dumps(result,indent=2))
