#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only
"""Queue the port-specific offline userdata reset; never format partitions."""
from pathlib import Path
import hashlib,json,os,secrets,subprocess,sys,stat

def output(args):return subprocess.check_output(args,text=True).strip()
def main():
 # D-Bus service activation omits sbin; use a fixed root tool search path.
 os.environ['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
 if os.geteuid()!=0:raise PermissionError('Factory reset requires root')
 if sys.argv[1:] not in ([],['--check']):raise ValueError('Use no arguments, or --check')
 m=json.loads(Path('/usr/local/share/a05bd-factory-reset/boot.json').read_text())
 assert output(['findmnt','-n','-o','SOURCE','/'])=='/dev/mmcblk0p28'
 assert output(['findmnt','-n','-o','SOURCE','/userdata'])=='/dev/mmcblk0p32'
 assert output(['blkid','-s','LABEL','-o','value','/dev/mmcblk0p32'])=='UTdata'
 data_uuid=output(['blkid','-s','UUID','-o','value','/dev/mmcblk0p32'])
 import re
 assert re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',data_uuid)
 assert m['reset_protocol']=='A05BD_FACTORY_RESET_V2'
 assert Path('/sys/class/block/mmcblk0p32/start').read_text().strip()=='15240192'
 assert Path('/sys/class/block/mmcblk0p32/size').read_text().strip()=='15295455'
 assert Path('/var/lib/lxc/android/android-rootfs.img').is_file()
 with open('/dev/mmcblk0p14','rb',buffering=0) as f:assert hashlib.sha256(f.read(m['bytes'])).hexdigest()==m['sha256'], 'Current boot does not support safe offline reset'
 state=Path('/var/lib/a05bd-reset');assert state.is_dir() and not state.is_symlink()
 assert stat.S_IMODE(state.stat().st_mode)==0o700 and state.stat().st_uid==0
 # State must reside on system, outside the userdata being deleted.
 assert output(['findmnt','-n','-o','SOURCE','-T',str(state)])=='/dev/mmcblk0p28'
 if sys.argv[1:]==['--check']:
  print('A05BD_FACTORY_RESET_READY');return
 req=Path('/userdata/.a05bd-factory-reset.request');pending=state/'pending'
 assert not req.exists() and not req.is_symlink() and not pending.exists() and not pending.is_symlink(), 'Reset already queued'
 data=(m['reset_protocol']+' '+data_uuid+' '+secrets.token_hex(16)+'\n').encode();assert len(data)==93
 oldmask=os.umask(0o077)
 try:
  for p in (pending,req):
   with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.sync()
  subprocess.run(['systemctl','--no-block','reboot'],check=True,timeout=15)
 except BaseException:
  req.unlink(missing_ok=True);pending.unlink(missing_ok=True);os.sync();raise
 finally:os.umask(oldmask)
 print('A05BD_FACTORY_RESET_QUEUED')
if __name__=='__main__':main()
