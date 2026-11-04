#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Local, bounded-memory TWRP installer. No ADB writer and no shell dd.

Production entry accepts only /dev/block/mmcblk0, a recovery boot, the exact
A05BD GPT geometry, and payloads pinned by the packaged build manifest.
DiskIO also supports sparse regular files for offline fault-injection tests;
the production entry point never accepts a caller-selected device path.
"""
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import zipfile

from layout import DATA_BYTES, DISK_SECTORS, SYSTEM_BYTES, parse, plan

CHUNK = 4 * 1024**2
DISK_BYTES = DISK_SECTORS * 512
SECONDARY = (DISK_SECTORS - 33) * 512


def sha(data):
    return hashlib.sha256(data).hexdigest()


class DiskIO:
    def __init__(self, fd):
        self.fd = fd
        self.writes = 0

    def read(self, offset, length):
        result = os.pread(self.fd, length, offset)
        if len(result) != length:
            raise ValueError('Short disk read')
        return result

    def write(self, offset, data):
        if offset < 0 or offset + len(data) > DISK_BYTES:
            raise ValueError('Out of disk write')
        v = memoryview(data)
        while v:
            n = os.pwrite(self.fd, v, offset)
            if n <= 0:
                raise OSError('Short disk write')
            offset += n
            self.writes += n
            v = v[n:]

    def sync(self):
        os.fsync(self.fd)

    def digest(self, offset, length):
        h = hashlib.sha256()
        while length:
            n = min(length, CHUNK)
            h.update(self.read(offset, n))
            offset += n
            length -= n
        return h.hexdigest()

    def gpt(self):
        return self.read(0, 17408), self.read(SECONDARY, 16896)

    def copy(self, source, destination, length):
        # This recovery does not attempt overlapping relocation.
        if source < destination + length and destination < source + length:
            raise ValueError('Overlapping relocation')
        original = self.digest(source, length)
        for n in range(0, length, CHUNK):
            self.write(destination + n, self.read(source + n, min(CHUNK, length - n)))
        self.sync()
        if self.digest(destination, length) != original:
            raise ValueError('Relocated partition readback failed')


class Payload:
    def __init__(self, package, trusted):
        self.zip = zipfile.ZipFile(package)
        self.manifest = trusted
        names = self.zip.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP entry')

    def small(self, name):
        spec = self.manifest['files'][name]
        if spec['bytes'] > 2 * 1024**2:
            raise ValueError('Not a small payload')
        data = self.zip.read(name)
        if len(data) != spec['bytes'] or sha(data) != spec['sha256']:
            raise ValueError('Bad payload: ' + name)
        return data

    def image(self, name):
        stream = self.zip.open(name)
        return gzip.GzipFile(fileobj=stream) if name.endswith('.gz') else stream

    def check(self, report):
        # Validate gzip CRC, expanded size/hash and compressed bytes before
        # ANY disk write. Stream in bounded memory, including on sideload FUSE.
        for name, spec in self.manifest['files'].items():
            h = hashlib.sha256()
            count = 0
            with self.zip.open(name) as stream:
                for chunk in iter(lambda: stream.read(CHUNK), b''):
                    h.update(chunk)
                    count += len(chunk)
            if count != spec['bytes'] or h.hexdigest() != spec['sha256']:
                raise ValueError('Compressed/file hash mismatch: ' + name)
        for name, spec in self.manifest['images'].items():
            report('Verifying ' + name + ' before writes')
            h = hashlib.sha256()
            count = 0
            with self.image(name) as stream:
                for chunk in iter(lambda: stream.read(CHUNK), b''):
                    count += len(chunk)
                    if count > spec['bytes']:
                        raise ValueError('Oversized expanded image')
                    h.update(chunk)
            if count != spec['bytes'] or h.hexdigest() != spec['sha256']:
                raise ValueError('Expanded image hash mismatch: ' + name)


def geometry(disk):
    primary, secondary = disk.gpt()
    old, new, np, ns = plan(primary, secondary)
    # Only the original Android layout or the exact prepared Ubuntu layout.
    if old != new and old[27]['bytes'] != 1413480448:
        raise ValueError('Unrecognized Android system size')
    moves = [(old[i], new[i]) for i in range(28, 31) if old[i] != new[i]]
    for before, after in moves:
        for source, _ in moves:
            if after['start'] < source['end'] + 1 and source['start'] < after['end'] + 1:
                raise ValueError('Relocation destination overlaps a live source')
    return old, new, np, ns, moves


def execute(disk, payload, clean, session, report, reread=lambda: None):
    old, new, np, ns, moves = geometry(disk)
    if not clean:
        if old != new:
            raise ValueError('Update ZIP requires the Ubuntu 6GiB system layout')
        sb = disk.read(old[31]['start'] * 512 + 1024, 1024)
        if sb[56:58] != b'\x53\xef' or sb[120:136].rstrip(b'\0') != b'UTdata':
            raise ValueError('Update ZIP requires existing UTdata ext4')
    vbmeta = old[26]
    if disk.digest(vbmeta['start'] * 512, vbmeta['bytes']) != payload.manifest['vbmeta_sha256']:
        raise ValueError('Unsupported vbmeta firmware')
    for name, index in [('payload/system.img.gz', 27), ('payload/userdata-empty.img.gz', 31)]:
        if payload.manifest['images'][name]['bytes'] != new[index]['bytes']:
            raise ValueError('Image/partition length mismatch before writes')
    boot_spec = payload.manifest['files']['payload/boot.img']
    if not 16384 <= boot_spec['bytes'] <= old[13]['bytes']:
        raise ValueError('Invalid BOOT size')
    # Validate the migration footer before copying even the first vendor byte.
    tail = payload.small('payload/system-avb-tail.bin')
    if len(tail) != 1048576 or tail[-64:-60] != b'AVBf':
        raise ValueError('Invalid AVB footer')
    payload.check(report)
    original_gpt = disk.gpt()
    # Verify nothing changed while checking the large image.
    if geometry(disk)[:4] != (old, new, np, ns):
        raise ValueError('GPT changed during preflight')
    protected = [(p, disk.digest(p['start'] * 512, p['bytes']))
                 for p in old[:27] if p['index'] != 14]
    # A RAM-only journal is diagnostic, not a full backup or automatic resume.
    session.mkdir(mode=0o700, parents=True, exist_ok=False)
    (session / 'gpt-primary.bin').write_bytes(original_gpt[0])
    (session / 'gpt-secondary.bin').write_bytes(original_gpt[1])
    (session / 'boot-before.img').write_bytes(disk.read(old[13]['start'] * 512, old[13]['bytes']))
    (session / 'state.json').write_text(json.dumps({'phase': 'writes starting', 'clean': clean,
        'automatic_retry': False, 'full_backup': False}) + '\n')
    for before, after in moves:
        report('Keeping this device\'s ' + after['name'])
        disk.copy(before['start'] * 512, after['start'] * 512, before['bytes'])
    if old != new:
        # Child AVB footer must be valid at the new system boundary before GPT.
        offset = new[27]['start'] * 512 + SYSTEM_BYTES - len(tail)
        disk.write(offset, tail)
        disk.sync()
        if disk.digest(offset, len(tail)) != sha(tail):
            raise ValueError('AVB bootstrap readback failed')
        disk.write(SECONDARY, ns)
        disk.sync()
        disk.write(0, np)
        disk.sync()
        if disk.gpt() != (np, ns):
            raise ValueError('GPT readback failed')
        reread()
    for name, part in [('payload/system.img.gz', new[27])] + (
            [('payload/userdata-empty.img.gz', new[31])] if clean else []):
        spec = payload.manifest['images'][name]
        if spec['bytes'] != part['bytes']:
            raise ValueError('Image/partition length mismatch')
        report('Writing ' + part['name'])
        count = 0
        last_report = 0
        with payload.image(name) as stream:
            for chunk in iter(lambda: stream.read(CHUNK), b''):
                if count + len(chunk) > part['bytes']:
                    raise ValueError('Oversized image during write')
                disk.write(part['start'] * 512 + count, chunk)
                count += len(chunk)
                if count - last_report >= 32 * 1024**2:
                    disk.sync()
                    last_report = count
                if count % (512 * 1024**2) == 0:
                    report(part['name'] + ': ' + str(count // 1024**2) + ' MiB')
        disk.sync()
        if count != spec['bytes'] or disk.digest(part['start'] * 512, part['bytes']) != spec['sha256']:
            raise ValueError('Written image readback failed: ' + name)
    for p, digest in protected:
        if disk.digest(p['start'] * 512, p['bytes']) != digest:
            raise ValueError('Protected firmware changed: ' + p['name'])
    # BOOT is committed last. Recovery, LK, preloader and device calibration
    # are never updated by this ZIP. Keep the installed TWRP recovery intact.
    name = 'payload/boot.img'
    spec = payload.manifest['files'][name]
    if spec['bytes'] > old[13]['bytes']:
        raise ValueError('BOOT too large')
    with payload.image(name) as stream:
        count = 0
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            if count + len(chunk) > spec['bytes'] or count + len(chunk) > old[13]['bytes']:
                raise ValueError('BOOT stream exceeds its verified image/partition boundary')
            disk.write(old[13]['start'] * 512 + count, chunk)
            count += len(chunk)
    disk.sync()
    if count != spec['bytes'] or disk.digest(old[13]['start'] * 512, count) != spec['sha256']:
        raise ValueError('BOOT readback failed')
    (session / 'state.json').write_text(json.dumps({'phase': 'ALL_WRITTEN_IMAGES_READBACK_VERIFIED',
        'clean': clean, 'full_backup': False}) + '\n')
    report('Verified. Use Reboot > System when ready.')


def production_preflight(package):
    if os.geteuid() != 0 or not Path('/sbin/recovery').is_file():
        raise ValueError('Run only inside TWRP recovery')
    compat = Path('/proc/device-tree/compatible').read_bytes()
    if b'mt8168' not in compat:
        raise ValueError('Wrong SoC')
    if int(Path('/sys/class/block/mmcblk0/size').read_text()) != DISK_SECTORS:
        raise ValueError('Wrong eMMC capacity')
    # Reject any mounted internal partition, including package storage. TWRP
    # must run from RAM and the ZIP must be on external SD or sideload FUSE.
    internal = set()
    for node in Path('/sys/class/block').glob('mmcblk0*'):
        internal.add(node.joinpath('dev').read_text().strip())
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        if line.split()[2] in internal:
            raise ValueError('Internal storage is mounted; unmount it and use external SD/sideload')
    info = os.stat('/dev/block/mmcblk0')
    if not stat.S_ISBLK(info.st_mode):
        raise ValueError('Not the eMMC block device')
    if (os.major(info.st_rdev), os.minor(info.st_rdev)) != (179, 0):
        raise ValueError('Unexpected eMMC device number')
    if os.stat(package).st_dev in {os.makedev(*map(int, d.split(':'))) for d in internal}:
        raise ValueError('ZIP must not be on internal storage')
    if int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines()
                if s.startswith('MemAvailable:'))) < 384 * 1024:
        raise ValueError('Not enough free RAM')
    batteries = list(Path('/sys/class/power_supply').glob('*/capacity'))
    if not batteries or min(int(p.read_text()) for p in batteries) < 30:
        raise ValueError('Charge battery to at least 30 percent')


def main():
    if len(sys.argv) != 4:
        raise ValueError('Expected: flash.py OUTFD ZIP MANIFEST')
    out = os.fdopen(os.dup(int(sys.argv[1])), 'w', buffering=1)
    def report(message):
        print('ui_print ' + message.replace('\n', ' '), file=out)
        print('ui_print', file=out)
    try:
        package = sys.argv[2]
        trusted = json.loads(Path(sys.argv[3]).read_text())
        if trusted.get('mode') not in ('clean-install', 'update'):
            raise ValueError('Unknown install mode')
        if trusted['images']['payload/system.img.gz']['bytes'] != SYSTEM_BYTES:
            raise ValueError('Wrong system size')
        if trusted['images']['payload/userdata-empty.img.gz']['bytes'] != DATA_BYTES:
            raise ValueError('Wrong userdata size')
        production_preflight(package)
        clean = trusted['mode'] == 'clean-install'
        report('A05BD RC3: ' + ('CLEAN INSTALL - erases user data' if clean else 'system update - keeps UTdata'))
        payload = Payload(package, trusted)
        # Exclusive process lock is in RAM; it never locks/mounts user data.
        with open('/tmp/a05bd-flash.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Prevent accidental repetition after a partially completed attempt.
            if Path('/tmp/a05bd-install-session').exists():
                raise ValueError('Earlier attempt exists. Keep logs and review; do not retry blindly.')
            fd = os.open('/dev/block/mmcblk0', os.O_RDWR | os.O_CLOEXEC)
            try:
                disk = DiskIO(fd)
                execute(disk, payload, clean, Path('/tmp/a05bd-install-session'), report,
                        lambda: fcntl.ioctl(fd, 0x125f))  # BLKRRPART
            finally:
                os.close(fd)
    except Exception as error:
        report('STOP: ' + str(error))
        report('No automatic retry/reboot. Keep /tmp/recovery.log and /tmp/a05bd-install-session.')
        raise


if __name__ == '__main__':
    main()
