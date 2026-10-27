#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Derive release boot from known kernel/initrd; retain requested USB root console."""
import gzip,hashlib,json,subprocess
from pathlib import Path
out=Path('outputs/release-20261027');out.mkdir(exist_ok=True)
raw=gzip.decompress(Path('outputs/factory-reset-20261024/initrd-factory-reset.img').read_bytes());o=0;entries=[];changed=[];removed=[]
while o<len(raw):
 assert raw[o:o+6]==b'070701'
 f=[int(raw[o+6+i*8:o+14+i*8],16) for i in range(13)];name=raw[o+110:o+110+f[11]-1].decode();n=name.removeprefix('./');o=(o+110+f[11]+3)//4*4;d=raw[o:o+f[6]];o=(o+f[6]+3)//4*4
 if n=='init':
  start=d.index(b'# Initial A05BD bring-up diagnostics, before mounting internal storage.');end=d.index(b'# Export the dpkg architecture',start)
  d=d[:start]+b'# User-requested USB root diagnostic console; no recurring log streamer.\n/bin/a05bd-usb\n\n'+d[end:]
  old=b'kill "$(cat /run/a05bd-log.pid 2>/dev/null)" 2>/dev/null || true\n';assert old in d;d=d.replace(old,b'');changed.append(n)
 if n=='scripts/a05bd-factory-reset':d=Path('work/release/rc1/offline-reset.sh').read_bytes();changed.append(n)
 entries.append((name,f,d))
 if n=='TRAILER!!!':break
assert not removed
parts=[]
for name,f,d in entries:
 b=name.encode()+b'\0';f=f.copy();f[6]=len(d);f[11]=len(b);f[12]=0
 c=b'070701'+b''.join(f'{x:08x}'.encode() for x in f)+b;c+=b'\0'*(-len(c)%4);c+=d;c+=b'\0'*(-len(c)%4);parts.append(c)
c=b''.join(parts);c+=b'\0'*(-len(c)%512);ram=out/'initrd.img';ram.write_bytes(gzip.compress(c,mtime=0))
k=Path('outputs/camera-rotation-20261021/boot-package/verify/kernel');kh=hashlib.sha256(k.read_bytes()).hexdigest();assert kh=='bfb501fe4aba8eb573759403138e90f344970fa55514a35070e1a0f37e10f446'
base=json.loads(Path('outputs/factory-reset-20261024/boot-build.json').read_text());boot=out/'boot.img';assert not boot.exists()
subprocess.run(['python3','work/mkbootimg/mkbootimg.py','--kernel',str(k),'--ramdisk',str(ram),'--header_version','1','--base','0','--kernel_offset','0x40080000','--ramdisk_offset','0x55000000','--second_offset','0','--tags_offset','0x54000000','--pagesize','2048','--os_version','9.0.0','--os_patch_level','2020-07','--cmdline',base['cmdline'],'--output',str(boot)],check=True)
m={'bytes':boot.stat().st_size,'sha256':hashlib.sha256(boot.read_bytes()).hexdigest(),'kernel_sha256':kh,'reset_protocol':'A05BD_FACTORY_RESET_V2','cmdline':base['cmdline'],'usb_root_debug':True,'changed_initrd_entries':changed,'removed_initrd_entries':removed,'status':'BUILT_NOT_DEVICE_TESTED'}
assert m['bytes']<=16777216
(out/'boot.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
