#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Patch a verified public RC3 regular-file image. Never opens a device."""
from pathlib import Path
import gzip,hashlib,json,os,shutil,subprocess,tarfile,tempfile
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
IMAGE=BASE/'rc4-system.img'
OUT=ROOT/'outputs/twrp-install-20261104';OUT.mkdir(parents=True,exist_ok=True)
DEBUG='/opt/homebrew/opt/e2fsprogs/sbin/debugfs'
def digest(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert IMAGE.is_file() and IMAGE.stat().st_size==6442450944
assert digest(IMAGE)=='da70752d95eb266081e63b65796ec5f14839e88b919f6749209727d2bb2e6f3f'
with IMAGE.open('rb') as f:f.seek(-1048576,2);tail=f.read()
assert tail[-64:-60]==b'AVBf'
resources=BASE/'rc4-resources';assert not resources.exists();resources.mkdir()
with tarfile.open(BASE/'charger-resources.tgz') as t:t.extractall(resources,filter='data')
files={}
overlay=ROOT/'publication/repository/port/rootfs-overlay'
for name in ['a05bd-charger.target','a05bd-android-charger.service','a05bd-charge-watchdog.service']:
 files['/etc/systemd/system/'+name]=(BASE/name,0o100644)
files['/etc/systemd/system-generators/lxc-android-config-charger-generator']=(BASE/'lxc-android-config-charger-generator',0o100755)
files['/usr/local/sbin/a05bd-android-charger']=(BASE/'charger-a05bd-nosuspend',0o100755)
files['/usr/local/sbin/a05bd-charge-watchdog']=(BASE/'a05bd-charge-watchdog',0o100755)
for p in (resources/'res').rglob('*'):
 if p.is_file():
  assert not p.is_symlink()
  files['/usr/local/share/a05bd-charger/'+p.relative_to(resources).as_posix()]=(p,0o100644)
assert digest(files['/usr/local/sbin/a05bd-android-charger'][0])=='944bff591872210e8a3efa6fcfd836b851ab3890baef4bdf416a315debc976df'
assert (resources/'res/values/charger/animation.txt').read_bytes()==(BASE/'animation.txt').read_bytes()
# Keep the small bounded persistent boot journal used in hardware testing.
cfg=BASE/'90-a05bd-charger-debug.conf';cfg.write_text('[Journal]\nStorage=persistent\nSystemMaxUse=16M\nRuntimeMaxUse=4M\n')
files['/etc/systemd/journald.conf.d/90-a05bd-charger-debug.conf']=(cfg,0o100644)
def stat(path):return subprocess.run([DEBUG,'-R','stat '+path,str(IMAGE)],capture_output=True,text=True).stdout
commands=[];dirs=set()
for target in files:
 assert 'Inode:' not in stat(target),'Base already contains charger override: '+target
 parent=Path(target).parent
 while str(parent)!='/':dirs.add(str(parent));parent=parent.parent
for d in sorted(dirs,key=lambda x:(x.count('/'),x)):
 if 'Inode:' not in stat(d):commands += ['mkdir '+d,'set_inode_field '+d+' mode 040755','set_inode_field '+d+' uid 0','set_inode_field '+d+' gid 0']
for target,(source,mode) in sorted(files.items()):
 commands += [f'write "{source}" {target}',f'set_inode_field {target} mode {mode:07o}',f'set_inode_field {target} uid 0',f'set_inode_field {target} gid 0']
batch=OUT/'debugfs-rc4.commands';batch.write_text('\n'.join(commands)+'\n')
with (OUT/'debugfs-rc4.log').open('w') as log:subprocess.run([DEBUG,'-w','-f',str(batch),str(IMAGE)],stdout=log,stderr=subprocess.STDOUT,check=True)
checks=[]
with tempfile.TemporaryDirectory(prefix='a05bd-image-readback-') as td:
 for i,(target,(source,mode)) in enumerate(sorted(files.items())):
  dest=Path(td)/str(i)
  subprocess.run([DEBUG,'-R',f'dump {target} {dest}',str(IMAGE)],capture_output=True,check=True)
  assert digest(dest)==digest(source),target
  info=stat(target);assert f'Mode:  0{mode&0o7777:o}' in info,info
  assert 'User:     0   Group:     0' in info,info
  checks.append({'path':target,'sha256':digest(source),'mode':oct(mode&0o7777)})
with IMAGE.open('rb') as f:f.seek(-1048576,2);assert f.read()==tail
with (OUT/'e2fsck-rc4.log').open('w') as log:
 result=subprocess.run(['/opt/homebrew/opt/e2fsprogs/sbin/e2fsck','-fn',str(IMAGE)],stdout=log,stderr=subprocess.STDOUT)
assert result.returncode==0,'Filesystem check failed; inspect log'
raw_sha=digest(IMAGE)
gz=BASE/'rc4-system.img.gz';assert not gz.exists()
with IMAGE.open('rb') as src,gz.open('xb') as target:
 with gzip.GzipFile(fileobj=target,mode='wb',compresslevel=6,mtime=0) as dst:shutil.copyfileobj(src,dst,4*1024**2)
proof={'base':'public RC3 SHA-verified image; no live rootfs or user data copied','files_readback_verified':checks,'system_bytes':IMAGE.stat().st_size,'system_sha256':raw_sha,'gzip_bytes':gz.stat().st_size,'gzip_sha256':digest(gz),'avb_tail_unchanged':True,'e2fsck_exit':result.returncode}
(OUT/'rc4-image.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k!='files_readback_verified'},indent=2),flush=True)
