#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Create a private release-candidate clone; never modify the baseline/device."""
import hashlib,json,os,shutil,stat,subprocess,tarfile
from pathlib import Path
base=Path('/opt/a05bd-release');src=base/'rootfs-candidate-20261027';r=base/'rootfs-rc1';inp=base/'input-rc1'
assert src.is_dir() and not r.exists()
subprocess.run(['cp','-a','--reflink=auto',str(src),str(r)],check=True)
manifest=json.loads((inp/'port-payload-manifest.json').read_text());archive=inp/'port-payload-20261026.tgz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['payload_sha256']
changes=[]
def safe(path):
    parts=Path(path.lstrip('/')).parts
    assert '..' not in parts
    current=r
    for part in parts[:-1]:
        current=current/part
        assert not current.is_symlink(),str(current)
    return r.joinpath(*parts)
def put(path,data,mode=0o644):
    p=safe(path);assert not p.is_symlink(),path
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(mode)
    changes.append({'path':path,'sha256':hashlib.sha256(data).hexdigest(),'mode':oct(mode)})
with tarfile.open(archive) as t:
    for f in manifest['files']:
        path=f['path'].lstrip('/');m=t.getmember(path);assert m.isfile()
        data=t.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==f['sha256']
        put('/'+path,data,int(f['mode'],8))
put('/usr/local/sbin/a05bd-request-factory-reset',(inp/'request-reset.py').read_bytes(),0o755)
put('/usr/local/share/a05bd-factory-reset/boot.json',(inp/'boot.json').read_bytes())
state=safe('var/lib/a05bd-reset');state.mkdir(mode=0o700,exist_ok=False);state.chmod(0o700)
# Clean disposable data only in the NEW clone. Keep original/baseline backups.
clean=['root','home/phablet','var/log','var/backups/a05bd-port','var/cache/apt/archives','var/lib/apt/lists','var/lib/AccountsService/users','var/lib/AccountsService/icons','var/lib/NetworkManager','var/lib/bluetooth','var/lib/dhcp','var/lib/systemd/random-seed','var/lib/dbus/machine-id']
cleaned=[]
for path in clean:
    p=safe(path)
    if p.is_symlink() or p.is_file():p.unlink()
    elif p.is_dir():shutil.rmtree(p)
    cleaned.append(path)
for path,mode in [('root',0o700),('home/phablet',0o755),('var/log',0o755),('var/backups',0o755),('var/cache/apt/archives/partial',0o755),('var/lib/apt/lists/partial',0o755),('var/lib/AccountsService/users',0o700),('var/lib/AccountsService/icons',0o775),('var/lib/NetworkManager',0o700),('var/lib/bluetooth',0o700),('var/lib/dbus',0o755)]:
    p=safe(path);p.mkdir(parents=True,exist_ok=True);p.chmod(mode)
# Standard shell defaults only, no previous user's hidden files.
for name in ['.bashrc','.profile','.bash_logout']:
    p=r/'etc/skel'/name
    if p.is_file() and not p.is_symlink():shutil.copy2(p,r/'home/phablet'/name)
for path in ['var/cache/apt/pkgcache.bin','var/cache/apt/srcpkgcache.bin','etc/machine-id','etc/writable/machine-id']:
    p=safe(path)
    if p.is_file() and not p.is_symlink():p.write_bytes(b'')
# The DBus alias must point to the future device's newly generated identity.
(r/'var/lib/dbus/machine-id').symlink_to('/etc/machine-id')
for p in (r/'etc/ssh').glob('ssh_host_*'):
    if p.is_file() or p.is_symlink():p.unlink()
profiles=safe('etc/NetworkManager/system-connections')
if profiles.is_dir():
    for p in profiles.iterdir():
        assert p.is_file() or p.is_symlink();p.unlink()
# Disable diagnostic USB and unsolicited SSH even when old wants links exist.
for name in ['a05bd-usb.service','a05bd-usb-console.service','ssh.service','ssh.socket']:
    p=safe('etc/systemd/system/'+name)
    if p.exists() or p.is_symlink():p.unlink()
    p.symlink_to('/dev/null')
for name,target in [('zram-touch.service','/usr/local/lib/systemd/system/zram-touch.service'),('a05bd-initrd-log-cleanup.service','/usr/local/lib/systemd/system/a05bd-initrd-log-cleanup.service')]:
    p=safe('etc/systemd/system/multi-user.target.wants/'+name)
    if p.exists() or p.is_symlink():p.unlink()
    p.parent.mkdir(parents=True,exist_ok=True);p.symlink_to(target)
# Turn off verbose TRACE without modifying functional LXC hooks.
p=r/'var/lib/lxc/android/config';s=p.read_text();assert 'lxc.log.level = TRACE' in s
s=s.replace('lxc.log.level = TRACE','lxc.log.level = WARN');put('/var/lib/lxc/android/config',s.encode())
for name in ['config.bak','config.before-wifi','mount.sh.a05bd-before-fix']:
    p=r/'var/lib/lxc/android'/name
    if p.is_file() and not p.is_symlink():p.unlink()
# Complete the requested root-console configuration and compile schemas inside Noble.
subprocess.run(['python3',str(inp/'finish-rc1.py')],check=True)
