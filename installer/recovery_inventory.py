# SPDX-License-Identifier: GPL-3.0-only
"""Inspect the bundled RAM recovery itself, rather than assuming host tools exist."""
import hashlib,lzma,struct

def verify(path,expected_busybox_sha256):
    image=path.read_bytes()
    if image[:8]!=b'ANDROID!':raise ValueError('Invalid recovery image')
    kernel_size=struct.unpack_from('<I',image,8)[0];ramdisk_size=struct.unpack_from('<I',image,16)[0];page=struct.unpack_from('<I',image,36)[0]
    if page!=2048 or len(image)>16777216:raise ValueError('Unsupported recovery header/size')
    start=page+((kernel_size+page-1)//page)*page
    if start+ramdisk_size>len(image):raise ValueError('Truncated recovery image')
    raw=lzma.decompress(image[start:start+ramdisk_size]);offset=0;files={}
    while offset+110<=len(raw):
        if raw[offset:offset+6]!=b'070701':raise ValueError('Invalid recovery cpio')
        values=[int(raw[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
        name=raw[offset+110:offset+110+values[11]-1].decode().removeprefix('./');offset=(offset+110+values[11]+3)//4*4
        data=raw[offset:offset+values[6]];offset=(offset+values[6]+3)//4*4
        if name=='TRAILER!!!':break
        files[name]=data
    required=['init','bin/busybox','bin/sh','bin/cat','bin/id','bin/blockdev','bin/reboot','usr/bin/adbd','usr/bin/adbd-launch','sbin/reboot-bootloader']
    for name in required:
        if name not in files:raise ValueError('Required recovery file missing: '+name)
    if hashlib.sha256(files['bin/busybox']).hexdigest()!=expected_busybox_sha256:raise ValueError('Recovery BusyBox differs from the binary tested')
    if b'/run/a05bd-ram-recovery' not in files['init']:raise ValueError('Recovery marker not generated')
    return {'entries':len(files),'busybox_sha256':expected_busybox_sha256,'required_files':required}
