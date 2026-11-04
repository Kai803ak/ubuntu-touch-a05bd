#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Real pwrite/readback tests on one 15.6GB sparse REGULAR file, never devices."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import time
import uuid
import zipfile
import zlib

import flash


def fixture_gpt():
    entries = bytearray(16384)
    cursor = 2048
    for i in range(32):
        name = 'fixture' + str(i + 1)
        sectors = 32
        if i in (13, 14):
            name = ['boot', 'recovery'][i - 13]
            sectors = 32768
        if i == 26:
            name = 'vbmeta'
            sectors = 23040
        if i >= 27:
            name, start, end = [
                ('system', 576512, 3337215), ('vendor', 3337216, 5078015),
                ('factory', 5078016, 5110783), ('cache', 5110784, 5417983),
                ('userdata', 5417984, 30535646)][i - 27]
            cursor, sectors = start, end - start + 1
        o = i * 128
        entries[o:o+16] = uuid.UUID(int=i + 1).bytes_le
        entries[o+16:o+32] = uuid.UUID(int=100 + i).bytes_le
        struct.pack_into('<QQ', entries, o + 32, cursor, cursor + sectors - 1)
        n = name.encode('utf-16le')
        entries[o+56:o+56+len(n)] = n
        cursor += sectors
    def header(current, backup, table):
        h = bytearray(512)
        h[:8] = b'EFI PART'
        struct.pack_into('<IIIIQQQQ', h, 8, 0x10000, 92, 0, 0,
                         current, backup, 34, flash.DISK_SECTORS - 34)
        h[56:72] = uuid.UUID(int=999).bytes_le
        struct.pack_into('<QIII', h, 72, table, 128, 128, zlib.crc32(entries))
        struct.pack_into('<I', h, 16, zlib.crc32(h[:92]))
        return bytes(h)
    mbr = bytearray(512)
    mbr[510:512] = b'\x55\xaa'
    return bytes(mbr) + header(1, flash.DISK_SECTORS-1, 2) + entries, bytes(entries) + header(flash.DISK_SECTORS-1, 1, flash.DISK_SECTORS-33)


def run(base):
    results = []
    diskfile = base / 'fixture-emmc-regular-file'
    with diskfile.open('xb') as f:
        f.truncate(flash.DISK_BYTES)
    fd = os.open(diskfile, os.O_RDWR)
    disk = flash.DiskIO(fd)
    primary, secondary = fixture_gpt()
    disk.write(0, primary)
    disk.write(flash.SECONDARY, secondary)
    old, new, _, _, moves = flash.geometry(disk)
    assert len(moves) == 3
    for p in old:
        disk.write(p['start'] * 512, (p['name'] + ':own-device').encode())
    # BOOT is deliberately a complete partition whose trailing bytes must stay.
    disk.write(old[13]['start'] * 512, b'B' * old[13]['bytes'])
    boot = b'ANDROID!' + b'N' * (16384 - 8)
    tail = bytearray(1048576)
    tail[-64:-60] = b'AVBf'
    spec = {'mode': 'clean-install', 'files': {}, 'images': {}}
    package = base / 'fixture.zip'
    payloadfiles = {'payload/boot.img': boot, 'payload/system-avb-tail.bin': bytes(tail)}
    for name, data in payloadfiles.items():
        spec['files'][name] = {'bytes': len(data), 'sha256': flash.sha(data)}
    for name, size in [('system.img.gz', flash.SYSTEM_BYTES), ('userdata-empty.img.gz', flash.DATA_BYTES)]:
        path = base / name
        print('Creating compressed sparse-image fixture', name, flush=True)
        h = hashlib.sha256()
        zeros = bytes(flash.CHUNK)
        with gzip.GzipFile(filename=str(path), mode='wb', compresslevel=1, mtime=0) as gz:
            left = size
            while left:
                chunk = zeros[:min(len(zeros), left)]
                gz.write(chunk)
                h.update(chunk)
                left -= len(chunk)
        key = 'payload/' + name
        spec['images'][key] = {'bytes': size, 'sha256': h.hexdigest()}
        spec['files'][key] = {'bytes': path.stat().st_size, 'sha256': flash.sha(path.read_bytes())}
    spec['vbmeta_sha256'] = disk.digest(old[26]['start'] * 512, old[26]['bytes'])
    with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_STORED) as z:
        for name, data in payloadfiles.items():
            z.writestr(name, data)
        for name in spec['images']:
            z.write(base / name.split('/')[-1], name)
    payload = flash.Payload(package, spec)
    def log(s):
        print(s, flush=True)
    before = disk.writes
    try:
        flash.execute(disk, payload, False, base / 'wrong-update', log)
        raise AssertionError('Android update accepted')
    except ValueError as error:
        assert '6GiB' in str(error) and disk.writes == before
    results.append('update on Android layout rejected with zero writes')
    damaged = dict(spec, vbmeta_sha256='0' * 64)
    try:
        flash.execute(disk, flash.Payload(package, damaged), True, base / 'bad-vbmeta', log)
        raise AssertionError('Unknown firmware accepted')
    except ValueError as error:
        assert 'vbmeta' in str(error) and disk.writes == before
    results.append('wrong vbmeta rejected with zero writes')
    badspec = json.loads(json.dumps(spec))
    badspec['files']['payload/boot.img']['sha256'] = '0' * 64
    try:
        flash.execute(disk, flash.Payload(package, badspec), True, base / 'bad-payload', log)
        raise AssertionError('Damaged payload accepted')
    except ValueError as error:
        assert 'hash mismatch' in str(error) and disk.writes == before
    results.append('payload damage rejected before relocation/GPT/image writes')
    badspec = json.loads(json.dumps(spec))
    badspec['images']['payload/system.img.gz']['bytes'] -= 512
    try:
        flash.execute(disk, flash.Payload(package, badspec), True, base / 'bad-size', log)
        raise AssertionError('Wrong image geometry accepted')
    except ValueError as error:
        assert 'length mismatch before writes' in str(error) and disk.writes == before
    results.append('wrong expanded partition size rejected with zero writes')
    badspec = json.loads(json.dumps(spec))
    badspec['files']['payload/system-avb-tail.bin']['sha256'] = '0' * 64
    try:
        flash.execute(disk, flash.Payload(package, badspec), True, base / 'bad-footer', log)
        raise AssertionError('Damaged bootstrap footer accepted')
    except ValueError as error:
        assert 'Bad payload' in str(error) and disk.writes == before
    results.append('bad bootstrap footer rejected before the first vendor relocation')
    expected = [(p, disk.digest(p['start'] * 512, p['bytes'])) for p in old[:27] if p['index'] != 14]
    flash.execute(disk, payload, True, base / 'clean-session', log)
    assert flash.geometry(disk)[0] == new
    for p in new[28:31]:
        assert disk.read(p['start'] * 512, len((p['name'] + ':own-device').encode())) == (p['name'] + ':own-device').encode()
    for p, digest in expected:
        assert disk.digest(p['start'] * 512, p['bytes']) == digest
    assert disk.read(old[13]['start'] * 512 + len(boot), 1024) == b'B' * 1024
    results.append('full Android-to-Ubuntu GPT migration with own vendor/factory/cache preserved')
    results.append('full 6GiB system / 7831272960B userdata writes and SHA256 readback')
    results.append('p1-p27 except final BOOT unchanged; BOOT prefix committed last, trailing bytes preserved')
    # Update fixture: label and a personal canary must survive.
    sb = bytearray(1024)
    sb[56:58] = b'\x53\xef'
    sb[120:126] = b'UTdata'
    disk.write(new[31]['start'] * 512 + 1024, sb)
    disk.write(new[31]['start'] * 512 + 8192, b'KEEP-MY-DATA')
    datahash = disk.digest(new[31]['start'] * 512, new[31]['bytes'])
    flash.execute(disk, payload, False, base / 'update-session', log)
    assert disk.digest(new[31]['start'] * 512, new[31]['bytes']) == datahash
    results.append('system update preserved every byte of UTdata, GPT and factory firmware')
    os.close(fd)
    return results


if __name__ == '__main__':
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='a05bd-twrp-fixture-') as td:
        results = run(Path(td))
    result = {'tests_passed': results, 'elapsed_seconds': round(time.monotonic()-start, 2),
              'real_block_devices_written': False, 'uses_real_pread_pwrite_fsync': True,
              'flash_source_sha256': flash.sha(Path(flash.__file__).read_bytes()),
              'scope': 'PC regular-file fixtures; not proof of TWRP UI/USB/real-device boot'}
    Path(__file__).with_name('fixture-results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
