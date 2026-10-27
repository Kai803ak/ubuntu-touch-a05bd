#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Explicit A05BD installer. No writes without --execute. Python3/macOS/Linux."""
import argparse,gzip,hashlib,json,os,shutil,subprocess,sys,time
from contextlib import contextmanager
from pathlib import Path
sys.dont_write_bytecode=True
from layout import DISK_SECTORS,SYSTEM_BYTES,DATA_BYTES,parse,plan
from ram_tools import read_command,write_command,hash_command,hash_output,is_utdata_superblock,relocation_commands
from recovery_inventory import verify as verify_recovery_inventory
ROOT=Path(__file__).resolve().parent.parent
A=['adb','-s','a05bd-ut','shell','-T']
DISK_BYTES=DISK_SECTORS*512
TRANSFER_CHUNK_BYTES=32*1024**2

@contextmanager
def keep_host_awake():
    """Prevent macOS idle sleep for this command, without changing settings."""
    guard=None
    if sys.platform=='darwin':
        guard=subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(os.getpid())],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:yield
    finally:
        if guard is not None:
            guard.terminate();guard.wait(timeout=10)

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(command,timeout=120,binary=False):
    r=subprocess.run(A+[command],capture_output=True,timeout=timeout);r.check_returncode()
    return r.stdout if binary else r.stdout.decode().strip()
def ready():
    run('test -f /run/a05bd-ram-recovery && test -x /bin/busybox')
    run('/bin/busybox dd if=/dev/null count=0 2>/dev/null')
    probe=run('printf A05BD_RAM_TOOL_CHECK | /bin/busybox sha256sum')
    if hash_output(probe)!=hashlib.sha256(b'A05BD_RAM_TOOL_CHECK').hexdigest():raise ValueError('RAM SHA256 self-test failed')
    if run('id -u')!='0' or run('cat /sys/class/block/mmcblk0/size')!=str(DISK_SECTORS):raise ValueError('Wrong device/recovery')
    if 'mmcblk' in run('cat /proc/mounts'):raise ValueError('Internal filesystems must all be unmounted')
    return run('cat /sys/class/block/mmcblk0/device/cid')
def read_gpt():
    p=run(read_command('/dev/mmcblk0',0,17408),binary=True)
    s=run(read_command('/dev/mmcblk0',30535647*512,16896),binary=True)
    parse(p,s,allow_stale_backup=True);return p,s
def verify():
    m=json.loads((ROOT/'manifest.json').read_text())
    for n,f in m['files'].items():
        p=ROOT/n
        if p.stat().st_size!=f['bytes'] or sha(p)!=f['sha256']:raise ValueError('Package checksum mismatch: '+n)
    verify_recovery_inventory(ROOT/'recovery-ram.img',m['requirements']['ram_busybox_sha256'])
    for n,f in m['images'].items():
        h=hashlib.sha256();size=0
        with gzip.open(ROOT/n,'rb') as stream:
            for b in iter(lambda:stream.read(4*1024**2),b''):size+=len(b);h.update(b)
        if size!=f['bytes'] or h.hexdigest()!=f['sha256']:raise ValueError('Expanded image mismatch: '+n)
    return m
def backup_dir(path):
    d=Path(path).resolve();d.mkdir(mode=0o700,parents=True,exist_ok=True);d.chmod(0o700);return d
def stream_to_device(stream,command,timeout=3600):
    p=subprocess.Popen(A+[command],stdin=subprocess.PIPE)
    try:
        shutil.copyfileobj(stream,p.stdin,4*1024**2);p.stdin.close()
        if p.wait(timeout=timeout):raise RuntimeError('Device write failed')
    except BaseException:
        p.kill();p.wait();raise
def ram_memory():
    text=run('cat /proc/meminfo; for p in $(/bin/busybox pidof adbd); do cat /proc/$p/status; done')
    values={line.split(':',1)[0]:int(line.split()[1]) for line in text.splitlines() if line.startswith(('MemAvailable:','VmRSS:'))}
    if not {'MemAvailable','VmRSS'}<=values.keys() or values['MemAvailable']<384*1024 or values['VmRSS']>512*1024:
        raise ValueError('RAM transfer memory limit reached; no further chunks sent')
    return values
def stream_partition(stream,path,offset=0):
    """Bound ADB's pending input; wait for each 32MiB write+fsync to finish."""
    import io
    written=0;last=0;peak=0
    ram_memory()
    while True:
        data=stream.read(TRANSFER_CHUNK_BYTES)
        if not data:break
        stream_to_device(io.BytesIO(data),write_command(path,offset+written))
        written+=len(data);memory=ram_memory();peak=max(peak,memory['VmRSS'])
        if written-last>=256*1024**2:
            print('TRANSFER_BYTES',path,written,'ADBD_RSS_KIB',memory['VmRSS'],flush=True);last=written
    print('TRANSFER_DONE',path,written,'ADBD_POST_CHUNK_MAX_RSS_KIB',peak,flush=True)
    return written
def bytes_to_device(data,command):
    import io
    stream_to_device(io.BytesIO(data),command)
def device_sha(path,timeout=1200):return hash_output(run(hash_command(path),timeout))
def require_execute(args):
    if not args.execute:raise ValueError('No write performed. Add --execute after reviewing INSTALL.md.')
def load_backup(path,check_full=True):
    d=Path(path).resolve();m=json.loads((d/'backup.json').read_text())
    if m['cid']!=ready():raise ValueError('Backup belongs to a different eMMC device')
    if check_full and (sha(d/'emmc.img')!=m['sha256'] or (d/'emmc.img').stat().st_size!=DISK_BYTES):raise ValueError('Backup damaged')
    if sha(d/'original-boot.img')!=m['original_boot_sha256']:raise ValueError('Original boot backup damaged')
    if (d/'original-boot.img').stat().st_size!=16777216:raise ValueError('Original boot backup has wrong size')
    with (d/'emmc.img').open('rb') as f:
        if f.read(17408)!=(d/'gpt-primary.bin').read_bytes():raise ValueError('Primary GPT backup does not match whole-disk backup')
        f.seek(-16896,2)
        if f.read(16896)!=(d/'gpt-secondary.bin').read_bytes():raise ValueError('Secondary GPT backup does not match whole-disk backup')
    return d,m

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='phase',required=True)
    sub.add_parser('verify')
    q=sub.add_parser('bootstrap');q.add_argument('--original-boot',required=True);q.add_argument('--backup-dir',required=True);q.add_argument('--execute',action='store_true')
    q=sub.add_parser('backup');q.add_argument('--backup-dir',required=True)
    q=sub.add_parser('prepare-no-backup');q.add_argument('--backup-dir',required=True);q.add_argument('--accept-data-loss',action='store_true');q.add_argument('--use-primary-gpt',action='store_true')
    q=sub.add_parser('plan');q.add_argument('--backup-dir',required=True);q.add_argument('--use-primary-gpt',action='store_true')
    q=sub.add_parser('install');q.add_argument('--backup-dir',required=True);q.add_argument('--execute',action='store_true');q.add_argument('--erase-userdata',action='store_true');q.add_argument('--preserve-userdata',action='store_true');q.add_argument('--use-primary-gpt',action='store_true');q.add_argument('--without-full-backup',action='store_true');q.add_argument('--accept-data-loss',action='store_true')
    q=sub.add_parser('restore');q.add_argument('--backup-dir',required=True);q.add_argument('--execute',action='store_true')
    args=p.parse_args()
    if args.phase=='verify':verify();print('PACKAGE_VERIFIED; no device writes');return
    if args.phase=='bootstrap':
        require_execute(args);verify();original=Path(args.original_boot).resolve()
        if original.stat().st_size!=16777216 or original.read_bytes()[:8]!=b'ANDROID!':raise ValueError('Supply your OWN complete 16MiB boot partition backup')
        listing=subprocess.check_output(['fastboot','devices'],text=True).strip().splitlines()
        if len(listing)!=1:raise ValueError('Exactly one fastboot device is required')
        for key,value in [('product','a05bd'),('unlocked','yes'),('partition-size:boot','1000000')]:
            r=subprocess.run(['fastboot','getvar',key],capture_output=True,text=True,check=True)
            if key+': '+value not in r.stdout+r.stderr:raise ValueError('Fastboot guard failed: '+key)
        d=backup_dir(args.backup_dir);dest=d/'original-boot.img'
        if dest.exists() and sha(dest)!=sha(original):raise ValueError('Existing boot backup differs')
        if dest!=original:shutil.copy2(original,dest)
        dest.chmod(0o600)
        subprocess.run(['fastboot','flash','boot',str(ROOT/'recovery-ram.img')],check=True)
        subprocess.run(['fastboot','reboot'],check=True)
        print('RAM recovery started. Next: backup. System/data/GPT untouched.');return
    if args.phase=='backup':
        cid=ready();primary,secondary=read_gpt();d=backup_dir(args.backup_dir)
        original=d/'original-boot.img'
        if not original.is_file() or original.stat().st_size!=16777216:raise ValueError('Original boot backup is required before full backup')
        if (d/'emmc.img').exists() or (d/'emmc.img.partial').exists():raise ValueError('Backup already exists; do not overwrite')
        if shutil.disk_usage(d).free<DISK_BYTES+1024**3:raise ValueError('At least 16.7GB free space is required')
        h=hashlib.sha256();size=0;last=time.monotonic()
        with (d/'emmc.img.partial').open('xb') as f:
            os.chmod(f.name,0o600)
            command=A+[read_command('/dev/mmcblk0')]
            child=subprocess.Popen(command,stdout=subprocess.PIPE)
            for b in iter(lambda:child.stdout.read(4*1024**2),b''):
                f.write(b);h.update(b);size+=len(b)
                if time.monotonic()-last>30:print('Backup bytes:',size,flush=True);last=time.monotonic()
            if child.wait()!=0 or size!=DISK_BYTES:raise RuntimeError('Incomplete backup')
        expected=device_sha('/dev/mmcblk0')
        if expected!=h.hexdigest():raise ValueError('Backup readback hash mismatch')
        (d/'emmc.img.partial').rename(d/'emmc.img')
        (d/'gpt-primary.bin').write_bytes(primary);(d/'gpt-secondary.bin').write_bytes(secondary)
        (d/'backup.json').write_text(json.dumps({'cid':cid,'bytes':size,'sha256':expected,'original_boot_sha256':sha(original),'boot_in_full_dump':'temporary RAM recovery; original-boot.img is restored separately'},indent=2)+'\n')
        print('FULL_BACKUP_VERIFIED. Keep this directory private.');return
    if args.phase=='prepare-no-backup':
        if not args.accept_data_loss:raise ValueError('Explicit --accept-data-loss is required; no whole-disk restore will be created')
        cid=ready();primary,secondary=read_gpt();old,new,_,_=plan(primary,secondary,args.use_primary_gpt)
        relocation_commands(old,new)
        d=backup_dir(args.backup_dir);original=d/'original-boot.img'
        if not original.is_file() or original.stat().st_size!=16777216 or original.read_bytes()[:8]!=b'ANDROID!':raise ValueError('Original BOOT file required')
        if any((d/n).exists() for n in ['backup.json','no-full-backup.json','install-started.json']):raise ValueError('Use a new session directory')
        start=old[0]['start']*512;length=(old[26]['end']+1)*512-start
        meta={'cid':cid,'no_full_backup':True,'data_loss_accepted':True,'original_boot_sha256':sha(original),'protected_sha256':hash_output(run(hash_command('/dev/mmcblk0',start,length),1200)),'primary_sha256':hashlib.sha256(primary).hexdigest(),'secondary_sha256':hashlib.sha256(secondary).hexdigest()}
        (d/'gpt-primary.bin').write_bytes(primary);(d/'gpt-secondary.bin').write_bytes(secondary)
        (d/'no-full-backup.json').write_text(json.dumps(meta,indent=2)+'\n')
        print('SESSION_PREPARED_WITHOUT_FULL_BACKUP. No partition writes. User data cannot be restored from this session.');return
    if args.phase=='plan':
        d=Path(args.backup_dir);old,new,_,_=plan((d/'gpt-primary.bin').read_bytes(),(d/'gpt-secondary.bin').read_bytes(),args.use_primary_gpt)
        print(json.dumps({'before':old[27:],'after':new[27:],'p1_to_p27_unchanged':True,'device_writes':False},indent=2));return
    require_execute(args)
    unbacked=args.phase=='install' and args.without_full_backup
    if unbacked:
        if not args.accept_data_loss or not args.erase_userdata or args.preserve_userdata:raise ValueError('No-backup installation requires --accept-data-loss --erase-userdata')
        d=Path(args.backup_dir).resolve();b=json.loads((d/'no-full-backup.json').read_text())
        if b.get('no_full_backup') is not True or b.get('data_loss_accepted') is not True or b['cid']!=ready():raise ValueError('Wrong no-backup session/device')
        if (d/'original-boot.img').stat().st_size!=16777216 or sha(d/'original-boot.img')!=b['original_boot_sha256']:raise ValueError('Original BOOT file damaged')
        for name in ['primary','secondary']:
            if sha(d/f'gpt-{name}.bin')!=b[name+'_sha256']:raise ValueError('Session GPT file damaged')
    else:d,b=load_backup(args.backup_dir)
    primary=(d/'gpt-primary.bin').read_bytes();secondary=(d/'gpt-secondary.bin').read_bytes();old,new,np,ns=plan(primary,secondary,allow_stale_backup=(args.phase=='restore' or args.use_primary_gpt))
    if args.phase=='restore':
        # CID and full-backup integrity are authoritative even if an interrupted
        # GPT write left the current table corrupt. Do not require a healthy GPT.
        with (d/'emmc.img').open('rb') as f:stream_partition(f,'/dev/mmcblk0')
        if device_sha('/dev/mmcblk0')!=b['sha256']:raise ValueError('Restore whole-disk readback mismatch')
        run('blockdev --rereadpt /dev/mmcblk0')
        with (d/'original-boot.img').open('rb') as f:stream_partition(f,'/dev/mmcblk0p14')
        if device_sha('/dev/mmcblk0p14')!=b['original_boot_sha256']:raise ValueError('Restore boot mismatch')
        print('ORIGINAL_DISK_AND_BOOT_RESTORED');run('(sleep 1; reboot -f) >/dev/null 2>&1 </dev/null &');return
    current=read_gpt()
    if current not in [(primary,secondary),(np,ns)]:raise ValueError('Current GPT differs from this device backup/plan; restore instead')
    m=verify()
    if args.erase_userdata==args.preserve_userdata:raise ValueError('Choose exactly one: --erase-userdata or --preserve-userdata')
    if args.preserve_userdata and (old!=new or current!=(np,ns) or not is_utdata_superblock(run(read_command('/dev/mmcblk0p32',1024,1024),binary=True))):raise ValueError('Data preservation requires the existing exact Ubuntu layout and UTdata label')
    if device_sha('/dev/mmcblk0p27')!=m['requirements']['vbmeta_sha256']:raise ValueError('Unsupported base firmware vbmeta; no install writes started')
    if (d/'install-started.json').exists():raise ValueError('Earlier installation already started; use restore or review that session before retrying')
    # Validate p1-p27 before ANY system/GPT writes. No LK/preloader/NVRAM writes.
    protected_start=old[0]['start']*512;protected_end=(old[26]['end']+1)*512
    if unbacked:
        expected_protected=b['protected_sha256'];moves=relocation_commands(old,new)
        if current!=(primary,secondary):raise ValueError('No-backup session requires original unchanged GPT')
    else:
        with (d/'emmc.img').open('rb') as f:
            f.seek(protected_start);left=protected_end-protected_start;h=hashlib.sha256()
            while left:
                chunk=f.read(min(left,4*1024**2));h.update(chunk);left-=len(chunk)
        expected_protected=h.hexdigest()
    command=hash_command('/dev/mmcblk0',protected_start,protected_end-protected_start)
    if hash_output(run(command,1200))!=expected_protected:raise ValueError('Protected partitions differ from session/backup')
    (d/'install-started.json').write_text(json.dumps({'package':m['version'],'without_full_backup':unbacked,'phase':'writes starting; inspect session on interruption; do not automatically retry'},indent=2)+'\n')
    if current!=(np,ns):
        if unbacked:
            # Copy recipient vendor/calibration/cache before changing GPT or
            # overwriting their old locations. No host/RAM image backup needed.
            for before,after,copy_command in moves:
                expected=hash_output(run(hash_command('/dev/mmcblk0',before['start']*512,before['bytes']),1200))
                run(copy_command,1200)
                if hash_output(run(hash_command('/dev/mmcblk0',after['start']*512,after['bytes']),1200))!=expected:raise ValueError('On-device relocation readback mismatch')
                print('RELOCATED_AND_VERIFIED',after['name'],flush=True)
        # Preserve a valid child AVB footer at the FUTURE system end before GPT
        # changes, so the bootloader can still load RAM recovery after power loss.
        tail=(ROOT/'system-avb-tail.bin').read_bytes()
        if len(tail)!=1048576 or tail[-64:-60]!=b'AVBf':raise ValueError('Invalid AVB tail')
        offset=new[27]['start']*512+SYSTEM_BYTES-len(tail)
        bytes_to_device(tail,write_command('/dev/mmcblk0',offset))
        actual=hash_output(run(hash_command('/dev/mmcblk0',offset,1048576)))
        if actual!=hashlib.sha256(tail).hexdigest():raise ValueError('Bootstrap AVB tail readback mismatch')
        bytes_to_device(ns,write_command('/dev/mmcblk0',30535647*512))
        bytes_to_device(np,write_command('/dev/mmcblk0'))
        run('blockdev --rereadpt /dev/mmcblk0')
        if read_gpt()!=(np,ns):raise ValueError('GPT readback mismatch')
        for part in new[27:]:
            node='/sys/class/block/mmcblk0p'+str(part['index'])
            if int(run('cat '+node+'/start'))!=part['start'] or int(run('cat '+node+'/size'))!=part['bytes']//512:raise ValueError('Kernel partition map mismatch')
        # Move this recipient device's vendor/factory/cache from THEIR backup.
        for part in ([] if unbacked else new[28:31]):
            before=old[part['index']-1];offset=before['start']*512
            temp=d/(part['name']+'-move.img');h=hashlib.sha256()
            with (d/'emmc.img').open('rb') as f,temp.open('wb') as target:
                f.seek(offset);left=before['bytes']
                while left:
                    chunk=f.read(min(left,4*1024**2));target.write(chunk);h.update(chunk);left-=len(chunk)
            temp.chmod(0o600)
            with temp.open('rb') as f:stream_partition(f,'/dev/mmcblk0p'+str(part['index']))
            if device_sha('/dev/mmcblk0p'+str(part['index']))!=h.hexdigest():raise ValueError('Moved partition mismatch')
    for key,index in [('system.img.gz',28)]+([('userdata-empty.img.gz',32)] if args.erase_userdata else []):
        print('WRITE',key,flush=True)
        with gzip.open(ROOT/key,'rb') as f:stream_partition(f,'/dev/mmcblk0p'+str(index))
        if device_sha('/dev/mmcblk0p'+str(index))!=m['images'][key]['sha256']:raise ValueError('Image readback mismatch: '+key)
    if hash_output(run(command,1200))!=expected_protected:raise ValueError('Protected partitions changed during installation')
    with (ROOT/'boot.img').open('rb') as f:stream_partition(f,'/dev/mmcblk0p14')
    # Image is shorter than its partition; verify exactly the image length.
    count=m['files']['boot.img']['bytes']
    if hash_output(run(hash_command('/dev/mmcblk0p14',0,count),120))!=m['files']['boot.img']['sha256']:raise ValueError('Boot readback mismatch')
    (d/'install-result.json').write_text(json.dumps({'result':'ALL_WRITTEN_IMAGES_READBACK_VERIFIED','erase_userdata':args.erase_userdata,'without_full_backup':unbacked,'package':m['version']},indent=2)+'\n')
    print('INSTALL_READBACK_VERIFIED. Rebooting.',flush=True);run('(sleep 1; reboot -f) >/dev/null 2>&1 </dev/null &')
if __name__=='__main__':
    try:
        with keep_host_awake():main()
    except Exception as e:
        print('STOP:',str(e),file=sys.stderr);print('No automatic retry. Keep the session and any existing backup. See RESTORE.md; no-backup sessions cannot restore the whole disk.',file=sys.stderr);sys.exit(1)
