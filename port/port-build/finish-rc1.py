#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import hashlib,json,os,shutil,subprocess
from pathlib import Path
base=Path('/opt/a05bd-release');r=base/'rootfs-rc1';src=base/'rootfs-candidate-20261027';inp=base/'input-rc1'
assert r.is_dir() and (r/'var/lib/a05bd-reset').is_dir()
# User explicitly requested that the physical USB root console be retained.
for name in ['a05bd-usb.service','a05bd-usb-console.service']:
 p=r/'etc/systemd/system'/name;assert p.is_symlink() and os.readlink(p)=='/dev/null';p.unlink();shutil.copy2(src/'etc/systemd/system'/name,p)
for p in [r/'home/phablet',*(r/'home/phablet').rglob('*')]:os.chown(p,32011,32011,follow_symlinks=False)
shutil.copy2(inp/'boot.json',r/'usr/local/share/a05bd-factory-reset/boot.json')
# Execute the amd64 schema compiler inside its existing Ubuntu build chroot.
chroot=Path('/opt/a05bd-webengine/noble-host');tmp=chroot/'run/a05bd-release-schemas-rc1';assert not tmp.exists()
shutil.copytree(r/'usr/share/glib-2.0/schemas',tmp,symlinks=True)
subprocess.run(['chroot',str(chroot),'/usr/bin/glib-compile-schemas','--strict','/run/a05bd-release-schemas-rc1'],check=True)
shutil.copy2(tmp/'gschemas.compiled',r/'usr/share/glib-2.0/schemas/gschemas.compiled')
assert (r/'usr/local/lib/a05bd-webengine-candidate-r5').is_dir()
assert (r/'var/lib/lxc/android/android-rootfs.img').stat().st_size>500*1024**2
assert not (r/'var/backups/a05bd-port').exists()
assert (r/'etc/machine-id').stat().st_size==0
m={'status':'EXPERIMENTAL_RC_NOT_DEVICE_TESTED','source_baseline_preserved':True,'latest_payload_files':28,'usb_root_debug':True,'usb_root_debug_requested_by_user':True,'factory_reset_protocol':'A05BD_FACTORY_RESET_V2','home_owner_uid_gid':[32011,32011],'glib_schema_compiled':True,'vendor_redistribution_review':'unconfirmed','device_written':False}
(base/'rc1-prepare.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
