#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Only READY -> FASTBOOT -> TOOBTSAF -> DISCONNECT; never flash or load payloads."""
import os,glob,time,select,termios,subprocess,plistlib,json
from pathlib import Path
out=Path(os.environ.get('A05BD_FASTBOOT_LOG_DIR','bootloader-connection-log'));events=[];out.mkdir(parents=True,exist_ok=True);start=time.monotonic();fd=None;port=None;sent=False;ack=False;buf=b'';last=None

def event(kind,**kw):
 d={'elapsed_seconds':round(time.monotonic()-start,2),'event':kind,**kw};events.append(d);print(json.dumps(d),flush=True)

def usb_inventory():
 if os.uname().sysname=='Linux':
  found=[]
  for serial_node in Path('/sys/class/tty').glob('ttyACM*'):
   for parent in (serial_node/'device').resolve().parents:
    try:
     vid=int((parent/'idVendor').read_text().strip(),16);pid=int((parent/'idProduct').read_text().strip(),16)
     found.append({'vid':vid,'pid':pid,'product':'USB serial'});break
    except (FileNotFoundError,ValueError):continue
  return found
 r=subprocess.run(['ioreg','-a','-p','IOUSB','-l'],capture_output=True,timeout=5)
 try:tree=plistlib.loads(r.stdout)
 except Exception:return []
 found=[]
 def walk(node):
  if isinstance(node,list):
   for v in node:walk(v)
  elif isinstance(node,dict):
   if 'idVendor' in node and 'idProduct' in node:found.append({'vid':node['idVendor'],'pid':node['idProduct'],'product':node.get('USB Product Name',node.get('IORegistryEntryName',''))})
   for c in node.get('IORegistryEntryChildren',[]):walk(c)
 walk(tree);return found

try:
 while time.monotonic()-start<115:
  ports=glob.glob('/dev/cu.usbmodem*')+glob.glob('/dev/ttyACM*');usb=usb_inventory();pl=[d for d in usb if d['vid']==0xe8d and d['pid']==0x2000]
  state=(tuple(ports),len(pl))
  if state!=last:event('connection_state',serial_ports=ports,preloader_usb_devices=pl);last=state
  if fd is None and len(ports)==1 and len(pl)==1:
   try:
    port=ports[0];fd=os.open(port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK);a=termios.tcgetattr(fd);a[0]=0;a[1]=0;a[2]=termios.CS8|termios.CREAD|termios.CLOCAL;a[3]=0;a[4]=termios.B115200;a[5]=termios.B115200;a[6][termios.VMIN]=0;a[6][termios.VTIME]=0;termios.tcsetattr(fd,termios.TCSANOW,a);event('serial_open',port=port)
   except OSError as e:event('open_error',error=str(e));fd=None
  if fd is not None:
   try:
    if select.select([fd],[],[],0.1)[0]:
     chunk=os.read(fd,4096)
     if chunk:
      buf=(buf+chunk)[-8192:]
      event('rx',ascii=chunk.decode('ascii',errors='backslashreplace'))
      if b'READY' in buf and not sent:
       os.write(fd,b'FASTBOOT');sent=True;event('tx',ascii='FASTBOOT')
      if sent and b'TOOBTSAF' in buf:
       ack=True;os.write(fd,b'DISCONNECT');event('tx',ascii='DISCONNECT');break
      if sent and any(x in buf for x in [b'METASLA',b'forbidden',b'UNKNOWN']):event('unexpected_response_stop');break
   except OSError as e:
    event('serial_error',error=str(e));os.close(fd);fd=None
    if sent:break
  time.sleep(0.1)
finally:
 if fd is not None:os.close(fd)
 fastboot=False
 for n in range(40 if sent else 1):
  r=subprocess.run(['fastboot','devices'],capture_output=True,text=True,timeout=4)
  if r.stdout.strip():fastboot=True;break
  time.sleep(0.5)
 if fastboot:
  for name in ['product','unlocked','secure']:
   r=subprocess.run(['fastboot','getvar',name],capture_output=True,text=True,timeout=5);event('fastboot_getvar',name=name,response=r.stdout+r.stderr)
 result={'events':events,'command_sent':sent,'ack_received':ack,'fastboot_detected':fastboot,'partition_writes':False,'payloads_loaded':False,'seconds':round(time.monotonic()-start,2)}
 (out/'usb-fastboot-attempt-1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='events'}),flush=True)
