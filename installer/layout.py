# SPDX-License-Identifier: GPL-3.0-only
"""A05BD GPT parser/planner. Preserves each device's GUIDs and p1-p27."""
import struct,zlib
DISK_SECTORS=30535680
SYSTEM_BYTES=6442450944
DATA_BYTES=7831272960

def header(data):
    if len(data)!=512 or data[:8]!=b'EFI PART':raise ValueError('Invalid GPT header')
    size,checksum=struct.unpack_from('<II',data,12)
    if not 92<=size<=512:raise ValueError('Invalid GPT header size')
    copy=bytearray(data[:size]);copy[16:20]=b'\0'*4
    if zlib.crc32(copy)!=checksum:raise ValueError('GPT header CRC mismatch')
    current,backup,first,last=struct.unpack_from('<QQQQ',data,24)
    lba,count,entry_size,crc=struct.unpack_from('<QIII',data,72)
    if count!=128 or entry_size!=128:raise ValueError('Unsupported GPT table geometry')
    return dict(current=current,backup=backup,first=first,last=last,lba=lba,count=count,entry_size=entry_size,crc=crc)

def parse(primary,secondary,allow_stale_backup=False):
    if len(primary)!=17408 or len(secondary)!=16896:raise ValueError('Incorrect GPT byte counts')
    a=header(primary[512:1024]);b=header(secondary[-512:]);entries=primary[1024:]
    if (a['current'],a['backup'],a['lba'],b['current'],b['backup'],b['lba'])!=(1,DISK_SECTORS-1,2,DISK_SECTORS-1,1,DISK_SECTORS-33):raise ValueError('Unsupported GPT placement')
    if zlib.crc32(entries)!=a['crc'] or zlib.crc32(secondary[:-512])!=b['crc']:raise ValueError('GPT entry CRC mismatch')
    if entries!=secondary[:-512]:
        if not allow_stale_backup:raise ValueError('Valid primary/secondary GPT disagree. Review backup and explicitly select --use-primary-gpt if appropriate.')
        if entries[:27*128]!=secondary[:27*128]:raise ValueError('Primary/secondary protected p1-p27 disagree')
    if primary[568:584]!=secondary[-456:-440]:raise ValueError('GPT disk GUID disagreement')
    parts=[]
    for i in range(128):
        e=entries[i*128:(i+1)*128]
        if e[:16]==b'\0'*16:continue
        start,end=struct.unpack_from('<QQ',e,32)
        if start>end or start<a['first'] or end>a['last']:raise ValueError('Out of bounds partition')
        parts.append(dict(index=i+1,name=e[56:128].decode('utf-16le').rstrip('\0'),start=start,end=end,bytes=(end-start+1)*512))
    if len(parts)!=32 or [p['index'] for p in parts]!=list(range(1,33)):raise ValueError('Expected 32 A05BD partitions')
    for p,q in zip(parts,parts[1:]):
        if p['end']>=q['start']:raise ValueError('Overlapping partitions')
    if [p['name'] for p in parts[27:]]!=['system','vendor','factory','cache','userdata']:raise ValueError('Wrong partition names/order')
    if parts[13]['name']!='boot' or parts[14]['name']!='recovery' or parts[26]['name']!='vbmeta':raise ValueError('Wrong boot partition indices')
    if [parts[i]['bytes'] for i in [13,14,26]]!=[16777216,16777216,11796480]:raise ValueError('Unsupported boot/recovery/vbmeta sizes')
    if parts[27]['start']!=576512 or [p['bytes'] for p in parts[28:31]]!=[891289600,16777216,157286400]:raise ValueError('Unsupported A05BD geometry')
    if parts[-1]['end']!=30535646:raise ValueError('Unexpected userdata boundary')
    return parts

def plan(primary,secondary,allow_stale_backup=False):
    old=parse(primary,secondary,allow_stale_backup);new=[dict(p) for p in old];cursor=old[27]['start']
    for p in new[27:]:
        length=SYSTEM_BYTES//512 if p['name']=='system' else (old[-1]['end']-cursor+1 if p['name']=='userdata' else p['bytes']//512)
        p.update(start=cursor,end=cursor+length-1,bytes=length*512);cursor+=length
    if new[-1]['bytes']!=DATA_BYTES:raise ValueError('Target userdata geometry differs')
    entries=bytearray(primary[1024:])
    for p in new[27:]:struct.pack_into('<QQ',entries,(p['index']-1)*128+32,p['start'],p['end'])
    def patch(h):
        h=bytearray(h);struct.pack_into('<I',h,88,zlib.crc32(entries));h[16:20]=b'\0'*4
        struct.pack_into('<I',h,16,zlib.crc32(h[:struct.unpack_from('<I',h,12)[0]]));header(h);return bytes(h)
    p=primary[:512]+patch(primary[512:1024])+bytes(entries);s=bytes(entries)+patch(secondary[-512:])
    assert p[:512]==primary[:512] and p[568:584]==primary[568:584] and p[1024:1024+27*128]==primary[1024:1024+27*128]
    assert parse(p,s)==new
    return old,new,p,s
