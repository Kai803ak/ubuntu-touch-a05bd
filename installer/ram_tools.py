# SPDX-License-Identifier: GPL-3.0-only
"""Commands supported by the BusyBox actually shipped in A05BD RAM recovery."""
import re
BUSYBOX='/bin/busybox'
def device_path(path):
    if not re.fullmatch(r'/dev/mmcblk0(?:p[1-9][0-9]*)?',path):raise ValueError('Unexpected target device path')
    return path
def block_size(*values):
    if any(n<0 for n in values):raise ValueError('Negative byte range')
    for size in [4194304,524288,4096,2048,512,1]:
        if all(n%size==0 for n in values):return size
def read_command(path,offset=0,length=None):
    path=device_path(path)
    if length is not None and length<=0:raise ValueError('Empty/negative byte range')
    bs=block_size(offset,*([length] if length is not None else []))
    cmd=f'{BUSYBOX} dd if={path} bs={bs}'
    if offset:cmd+=f' skip={offset//bs}'
    if length is not None:cmd+=f' count={length//bs}'
    # BusyBox 1.22 has no status=none. Keep stderr out of binary ADB streams.
    return cmd+' 2>/dev/null'
def write_command(path,offset=0):
    path=device_path(path);bs=block_size(offset)
    cmd=f'{BUSYBOX} dd of={path} bs={bs}'
    if offset:cmd+=f' seek={offset//bs}'
    return cmd+' conv=notrunc,fsync'
def hash_command(path,offset=0,length=None):
    if offset==0 and length is None:return f'{BUSYBOX} sha256sum {device_path(path)}'
    return 'set -o pipefail; '+read_command(path,offset,length)+f' | {BUSYBOX} sha256sum'
def hash_output(text):
    fields=text.split()
    if not fields or not re.fullmatch('[0-9a-f]{64}',fields[0]):raise ValueError('Unexpected SHA256 result')
    return fields[0]

def is_utdata_superblock(data):
    return len(data)==1024 and data[56:58]==b'\x53\xef' and data[120:136].rstrip(b'\0')==b'UTdata'

def relocation_commands(old,new):
    """Plan bounded on-device copies; reject any destination/source overlap."""
    moves=[(old[p['index']-1],p) for p in new[28:31]]
    result=[]
    for source,target in moves:
        a=source['start']*512;b=target['start']*512;n=source['bytes']
        if n!=target['bytes'] or min(a,b)<new[27]['start']*512 or max(a+n,b+n)>new[-1]['end']*512+512:
            raise ValueError('Unsafe relocation geometry')
        if a==b:continue
        for other,_ in moves:
            c=other['start']*512
            if b<c+other['bytes'] and c<b+n:raise ValueError('Relocation overlaps a source')
        bs=block_size(a,b,n)
        if bs<512:raise ValueError('Unaligned relocation')
        cmd=f'{BUSYBOX} dd if=/dev/mmcblk0 of=/dev/mmcblk0 bs={bs} skip={a//bs} seek={b//bs} count={n//bs} conv=notrunc,fsync'
        result.append((source,target,cmd))
    return result
