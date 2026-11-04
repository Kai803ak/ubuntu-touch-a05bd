#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Repackage hash-pinned RC3 images for TWRP without unpacking them to RAM."""
import hashlib
import io
import json
from pathlib import Path
import posixpath
import shutil
import tarfile
import zipfile

BASE = Path(__file__).resolve().parents[1] / 'twrp-20261104'
CHARGE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = ROOT / 'release/twrp-rc4-20261104'
ORIGINAL_SHA = '808854c2fc2ee3f412bd66bd8a444e7774e5b69c817da148da7151151b67856a'
FILES = ['boot.img', 'system.img.gz', 'userdata-empty.img.gz', 'system-avb-tail.bin']


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def runtime_tar(mode, manifest):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode='w:gz', compresslevel=6) as out:
        with tarfile.open(BASE / 'runtime-root.tar.gz', 'r:gz') as source:
            for member in source:
                name = member.name.removeprefix('./').strip('/')
                if name in ('', '.'):
                    continue
                if '..' in name.split('/'):
                    raise ValueError('Unexpected runtime path')
                member.name = 'runtime/' + name
                if member.issym() and member.linkname.startswith('/'):
                    member.linkname = posixpath.relpath('runtime/' + member.linkname.lstrip('/'), posixpath.dirname(member.name))
                elif member.islnk():
                    member.linkname = 'runtime/' + member.linkname.removeprefix('./').lstrip('/')
                member.uid = member.gid = 0
                member.uname = member.gname = 'root'
                out.addfile(member, source.extractfile(member) if member.isfile() else None)
        manifest = dict(manifest, mode=mode)
        for name, content in [(n, (BASE/n).read_bytes()) for n in ['flash.py', 'layout.py']] + [
                ('payload-manifest.json', (json.dumps(manifest, indent=2)+'\n').encode())]:
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            entry.mode = 0o644
            entry.mtime = 1793660400
            out.addfile(entry, io.BytesIO(content))
    return result.getvalue()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    original = ROOT / 'release/a05bd-ubuntu-touch-24.04-20261027-rc3.zip'
    if digest(original) != ORIGINAL_SHA:
        raise ValueError('Original RC3 ZIP differs')
    outputs = []
    with zipfile.ZipFile(original) as source:
        prefix = 'a05bd-ubuntu-touch-24.04-20261027-rc3/'
        rc3 = json.loads(source.read(prefix + 'manifest.json'))
        licenses = source.read(prefix + 'LICENSES.txt')
        licenses += b'\n\n===== TWRP / 2026-11-04 additions =====\n'
        licenses += (BASE/'TWRP-NOTICE').read_bytes()
        licenses += b'\nInstaller/build scripts: GPL-3.0-only. Device/watchdog: individual Apache-2.0 SPDX.\n'
        licenses += b'\nARM64 Python runtime package versions:\n' + (BASE/'runtime-packages.tsv').read_bytes()
        with tarfile.open(BASE/'runtime-root.tar.gz', 'r:gz') as t:
            for entry in t:
                if entry.isfile() and entry.name.endswith('/copyright'):
                    licenses += ('\n\n===== '+entry.name+' =====\n').encode() + t.extractfile(entry).read()
        licenses += b'\n\n===== A05BD charging RC4 =====\n' + (CHARGE/'CHARGER-NOTICE.txt').read_bytes()
        (OUT/'LICENSES.txt').write_bytes(licenses)
        manifest = {'release': rc3['version'], 'vbmeta_sha256': rc3['requirements']['vbmeta_sha256'],
                    'files': {'payload/'+n: rc3['files'][n] for n in FILES},
                    'images': {'payload/'+n: spec for n, spec in rc3['images'].items()}}
        proof = json.loads((ROOT/'outputs/twrp-install-20261104/rc4-image.json').read_text())
        manifest['release'] = 'a05bd-ubuntu-touch-24.04-20261104-rc4'
        manifest['files']['payload/system.img.gz'] = {'bytes': proof['gzip_bytes'], 'sha256': proof['gzip_sha256']}
        manifest['images']['payload/system.img.gz'] = dict(manifest['images']['payload/system.img.gz'], bytes=proof['system_bytes'], sha256=proof['system_sha256'])
        for mode in ['clean-install', 'update']:
            target = OUT / ('a05bd-ubuntu-touch-rc4-twrp-' + mode + '-20261104.zip')
            if target.exists() or target.with_suffix('.zip.partial').exists():
                raise ValueError('Output already exists: ' + str(target))
            rt = runtime_tar(mode, manifest)
            with zipfile.ZipFile(target.with_suffix('.zip.partial'), 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as out:
                info = zipfile.ZipInfo('META-INF/com/google/android/update-binary', (2026,11,4,0,0,0))
                info.create_system = 3
                info.external_attr = (0o100755 << 16)
                out.writestr(info, (BASE/'update-binary').read_bytes())
                out.writestr('installer-runtime.tar.gz', rt)
                out.writestr('INSTALL-TWRP.md', (CHARGE/'INSTALL-TWRP-RC4.md').read_bytes())
                out.writestr('LICENSES.txt', licenses, compress_type=zipfile.ZIP_DEFLATED)
                out.writestr('runtime-packages.tsv', (BASE/'runtime-packages.tsv').read_bytes())
                out.writestr('runtime-debs.SHA256SUMS', (BASE/'runtime-debs.SHA256SUMS').read_bytes())
                out.writestr('charging-sources.tar.gz', (CHARGE/'charging-sources.tar.gz').read_bytes())
                out.writestr('CHARGING-RC4.md', (CHARGE/'CHARGER-NOTICE.txt').read_bytes())
                for name in ['SOURCES.md', 'KNOWN-ISSUES.md', 'packages.tsv']:
                    out.writestr(name, source.read(prefix + name), compress_type=zipfile.ZIP_DEFLATED)
                for name in FILES:
                    h = hashlib.sha256()
                    count = 0
                    # Every entry and the whole ZIP fit below 2GiB. Avoid
                    # optional ZIP64 local headers for older recovery tools.
                    with ((CHARGE/'rc4-system.img.gz').open('rb') if name == 'system.img.gz' else source.open(prefix+name)) as f, out.open('payload/'+name, 'w') as dest:
                        for data in iter(lambda: f.read(4*1024**2), b''):
                            dest.write(data)
                            h.update(data)
                            count += len(data)
                    if count != manifest['files']['payload/'+name]['bytes'] or h.hexdigest() != manifest['files']['payload/'+name]['sha256']:
                        raise ValueError('RC3 payload mismatch: ' + name)
                    print(mode, name, count, flush=True)
            target.with_suffix('.zip.partial').rename(target)
            outputs.append({'name': target.name, 'bytes': target.stat().st_size, 'sha256': digest(target),
                            'mode': mode, 'device_tested': False})
            print('READY_NOT_DEVICE_TESTED', target, flush=True)
    (OUT/'package-results.json').write_text(json.dumps(outputs, indent=2)+'\n')
    (OUT/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in outputs))
    shutil.copy2(BASE/'runtime-corresponding-sources.tar.gz', OUT/'python-runtime-corresponding-sources.tar.gz')


if __name__ == '__main__':
    main()
