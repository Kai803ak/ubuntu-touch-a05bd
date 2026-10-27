from pathlib import Path
import stat,lzma,gzip,hashlib,json,subprocess,shutil
base=Path('work/system-migration');r=base/'recovery-root';out=Path('outputs/system-migration-20261024')
for n in ['bin','sbin','usr/bin','usr/libexec','etc','proc','sys','dev','run','tmp','data','home/phablet','var/log']:(r/n).mkdir(parents=True,exist_ok=True)
shutil.copyfile(base/'busybox',r/'bin/busybox');(r/'bin/busybox').chmod(0o755)
# Busybox is static. Only applets needed by the RAM recovery are exposed.
for n in 'sh ash cat chmod chown cp dd echo env grep head id kill ln ls mkdir mknod mount mv od ps pwd readlink rm sed sha256sum sleep stat stty sync tail tar touch umount uname wc dmesg blockdev fdisk losetup reboot'.split():
 p=r/'bin'/n
 if not p.exists():p.symlink_to('busybox')
shutil.copyfile(base/'adbd-launch',r/'usr/bin/adbd-launch');(r/'usr/bin/adbd-launch').chmod(0o4755)
p=r/'usr/libexec/adbd-pam-session'
if not p.is_symlink():p.symlink_to('/usr/bin/adbd-launch')
shutil.copyfile('work/suspend-resume/offline-check/tool/reboot-bootloader',r/'sbin/reboot-bootloader');(r/'sbin/reboot-bootloader').chmod(0o755)
(r/'usr/bin/adbd').chmod(0o755);(r/'lib/ld-linux-aarch64.so.1').chmod(0o755)
(r/'etc/passwd').write_text('root:x:0:0:root:/root:/bin/sh\nphablet:x:32011:32011:Recovery:/home/phablet:/bin/sh\n')
(r/'etc/group').write_text('root:x:0:\nphablet:x:32011:\n')
(r/'etc/nsswitch.conf').write_text('passwd: files\ngroup: files\nhosts: files\n')
shutil.copyfile(base/'recovery-init.sh',r/'init');(r/'init').chmod(0o755)
parts=[]
for i,p in enumerate([r]+sorted(r.rglob('*')),1):
 n='.' if p==r else str(p.relative_to(r));m=p.lstat().st_mode
 d=p.readlink().as_posix().encode() if p.is_symlink() else p.read_bytes() if p.is_file() else b''
 name=n.encode()+b'\0';v=[i,m,0,0,1,0,len(d),0,0,0,0,len(name),0]
 h=b'070701'+b''.join(f'{x:08x}'.encode() for x in v)+name;h+=b'\0'*(-len(h)%4);h+=d;h+=b'\0'*(-len(d)%4);parts.append(h)
n=b'TRAILER!!!\0';v=[0,0,0,0,1,0,0,0,0,0,0,len(n),0];h=b'070701'+b''.join(f'{x:08x}'.encode() for x in v)+n;h+=b'\0'*(-len(h)%4);parts.append(h)
c=b''.join(parts);c+=b'\0'*(-len(c)%512)
ram=out/'initrd-ram-recovery.xz';ram.write_bytes(lzma.compress(c,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC32,preset=6))
k=Path('outputs/camera-rotation-20261021/boot-package/verify/kernel')
assert hashlib.sha256(k.read_bytes()).hexdigest()=='bfb501fe4aba8eb573759403138e90f344970fa55514a35070e1a0f37e10f446'
boot=out/'boot-ram-recovery.img'
subprocess.run(['python3','work/mkbootimg/mkbootimg.py','--kernel',str(k),'--ramdisk',str(ram),'--header_version','1','--base','0','--kernel_offset','0x40080000','--ramdisk_offset','0x55000000','--second_offset','0','--tags_offset','0x54000000','--pagesize','2048','--os_version','9.0.0','--os_patch_level','2020-07','--cmdline','systemd.unified_cgroup_hierarchy=0 androidboot.hardware=mt8168 bootopt=64S3,32N2,64N2','--output',str(boot)],check=True)
assert boot.stat().st_size<=16777216,boot.stat().st_size
meta={str(p):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [ram,k,boot]};(out/'recovery-build.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta,indent=2))
