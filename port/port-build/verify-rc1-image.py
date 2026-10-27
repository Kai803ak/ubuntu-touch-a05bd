#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import hashlib,json,os,stat,struct,subprocess
from pathlib import Path
base=Path('/opt/a05bd-release');r=base/'rootfs-rc1';image=base/'rc1-images/system.img';out=base/'rc1-image-verification';out.mkdir(exist_ok=False)
m=json.loads((base/'input-rc1/port-payload-manifest.json').read_text());names=[f['path'] for f in m['files']]
names+=['/usr/share/glib-2.0/schemas/gschemas.compiled','/usr/local/bin/a05bd-morph-browser','/usr/local/lib/a05bd-gst-pts/libgsta05bdiondec.so','/etc/systemd/system/a05bd-usb.service','/etc/systemd/system/a05bd-usb-console.service']
commands=[]
for i,n in enumerate(names):commands.append('dump -p '+n+' '+str(out/str(i)))
cmd=out/'debugfs.commands';cmd.write_text('\n'.join(commands)+'\n')
p=subprocess.run(['debugfs','-f',str(cmd),str(image)],capture_output=True,text=True,check=True)
(out/'debugfs.log').write_text(p.stdout+p.stderr)
for i,n in enumerate(names):
    actual=(out/str(i)).read_bytes();expected=(r/n.lstrip('/')).read_bytes()
    assert actual==expected,n
# Filesystem ends before the AVB tail; the footer is at the partition end.
with image.open('rb') as f:
    f.seek(1024);sb=f.read(1024);assert struct.unpack_from('<H',sb,56)[0]==0xef53
    blocks=struct.unpack_from('<I',sb,4)[0];blocksize=1024<<struct.unpack_from('<I',sb,24)[0]
    assert blocks*blocksize==6442450944-1048576
    f.seek(-64,2);assert f.read(4)==b'AVBf'
# Known private paths and the obsolete per-device UUID must not remain.
secret_names={'authorized_keys','known_hosts','id_rsa','id_ed25519','id_ecdsa','.bash_history','.zsh_history','.wget-hsts'}
private_paths=[];old_uuid_files=[]
for directory,dirs,files in os.walk(r,followlinks=False):
    dirs[:]=[d for d in dirs if not (Path(directory)/d).is_symlink()]
    for name in files:
        path=Path(directory)/name;rel=str(path.relative_to(r));st=path.lstat()
        if not stat.S_ISREG(st.st_mode):continue
        if name in secret_names and not rel.startswith(('usr/share/','usr/lib/')):private_paths.append(rel)
        if st.st_size<4*1024**2 and rel.startswith(('etc/','usr/local/','var/lib/')):
            if b'c5ecd62c-ee0e-47a5-9644-a2637ac4ae3b' in path.read_bytes():old_uuid_files.append(rel)
assert not private_paths,private_paths
assert not old_uuid_files,old_uuid_files
assert (r/'etc/machine-id').stat().st_size==0
assert not list((r/'etc/NetworkManager/system-connections').glob('*'))
assert not (r/'var/backups/a05bd-port').exists()
assert not list((r/'root').iterdir())
assert (r/'home/phablet').stat().st_uid==32011
result={'exact_files_verified':len(names),'filesystem_bytes':blocks*blocksize,'avb_reserved_bytes':1048576,'avb_footer_present':True,'root_console_units_in_image':True,'known_private_paths_found':private_paths,'obsolete_device_uuid_found':old_uuid_files,'empty_machine_id':True,'empty_network_profiles':True,'old_port_backups_absent':True,'home_owner_uid':32011,'scope':'known-path and UUID audit, not a proof that every proprietary blob is redistributable','actual_device_writes':False}
(base/'rc1-images/image-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
