#!/usr/bin/env python3
import hashlib,json,os,shutil,subprocess,tarfile
from pathlib import Path
base=Path('/run/a05bd-charger-stage');base.mkdir(exist_ok=True)
with tarfile.open('/run/a05bd-charger-payload.tgz') as t:t.extractall(base,filter='data')
assert Path('/sys/class/power_supply/battery/capacity').is_file()
dest=Path('/usr/local/share/a05bd-charger');dest.mkdir(parents=True,exist_ok=True)
meta={}
for name in ['a05bd-android-charger','a05bd-charge-watchdog']:
 p=Path('/usr/local/sbin')/name
 if p.exists():raise ValueError('Destination already exists; inspect first: '+str(p))
 source=base/('charger-a05bd-nosuspend' if name.endswith('android-charger') else name)
 shutil.copyfile(source,p);p.chmod(0o755);meta[str(p)]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'previously_present':False}
res=dest/'res'
assert not res.exists()
shutil.copytree('/android/res',res,symlinks=True)
(res/'values/charger').mkdir(parents=True,exist_ok=True)
shutil.copy2(base/'animation.txt',res/'values/charger/animation.txt')
for name in ['a05bd-charger.target','a05bd-android-charger.service','a05bd-charge-watchdog.service']:
 p=Path('/etc/systemd/system')/name
 assert not p.exists();shutil.copy2(base/name,p);p.chmod(0o644);meta[str(p)]={'previously_present':False}
jd=Path('/etc/systemd/journald.conf.d');jd.mkdir(exist_ok=True)
jc=jd/'90-a05bd-charger-debug.conf';assert not jc.exists()
jc.write_text('[Journal]\nStorage=persistent\nSystemMaxUse=16M\nRuntimeMaxUse=4M\n')
Path('/var/log/journal').mkdir(parents=True,exist_ok=True)
(dest/'install-record.json').write_text(json.dumps(meta,indent=2)+'\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','systemd-journald'],check=True)
subprocess.run(['journalctl','--flush'],check=True)
subprocess.run(['systemd-analyze','verify','/etc/systemd/system/a05bd-charger.target','/etc/systemd/system/a05bd-android-charger.service','/etc/systemd/system/a05bd-charge-watchdog.service'],check=True)
print('STAGED; original charger image and boot/GPT unchanged; generator NOT enabled')
print(json.dumps(meta,indent=2))
