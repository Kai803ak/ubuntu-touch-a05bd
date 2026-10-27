#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Reassemble the checked RC3 ZIP from GitHub Release parts; Python 3.11+."""
import argparse,hashlib,json,os
from pathlib import Path
NAME='a05bd-ubuntu-touch-24.04-20261027-rc3.zip'
SHA='808854c2fc2ee3f412bd66bd8a444e7774e5b69c817da148da7151151b67856a'
SIZE=2904897818
def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parts-dir',type=Path,default=Path('.'));p.add_argument('--output',type=Path,default=Path(NAME));a=p.parse_args()
 m=json.loads((a.parts_dir/'rc3-download.json').read_text())
 if (m['zip_name'],m['zip_sha256'],m['zip_bytes'])!=(NAME,SHA,SIZE):raise ValueError('Unexpected release metadata')
 if len(m['parts'])!=3:raise ValueError('Expected three RC3 parts')
 if a.output.exists():
  if a.output.stat().st_size==SIZE and digest(a.output)==SHA:print('Existing RC3 ZIP verified:',a.output);return
  raise FileExistsError('Output already exists and differs; it was not modified')
 temp=a.output.with_name(a.output.name+'.partial');whole=hashlib.sha256();total=0
 # Exclusive creation avoids overwriting an earlier attempt or another file.
 with temp.open('xb') as target:
  try:
   for i,part in enumerate(m['parts'],1):
    if part['name']!=NAME+f'.part{i:02d}':raise ValueError('Unexpected part filename')
    source=a.parts_dir/part['name']
    if source.stat().st_size!=part['bytes']:raise ValueError('Part length mismatch: '+part['name'])
    h=hashlib.sha256()
    with source.open('rb') as f:
     for b in iter(lambda:f.read(4194304),b''):target.write(b);h.update(b);whole.update(b);total+=len(b)
    if h.hexdigest()!=part['sha256']:raise ValueError('Part checksum mismatch: '+part['name'])
    print('Verified',part['name'],flush=True)
   if total!=SIZE or whole.hexdigest()!=SHA:raise ValueError('Combined ZIP checksum mismatch')
   target.flush();os.fsync(target.fileno())
  except BaseException:
   temp.unlink(missing_ok=True);raise
 temp.rename(a.output);print('RC3 ZIP verified:',a.output);print(SHA)
if __name__=='__main__':main()
