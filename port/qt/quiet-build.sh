#!/bin/bash
set -euo pipefail
unit=a05bd-webengine-ion-full-r4-complete.service
systemctl is-active --quiet "$unit"
python3 - <<'PY'
from pathlib import Path
import subprocess,time,json
unit='a05bd-webengine-ion-full-r4-complete.service'
before=subprocess.check_output(['systemctl','show',unit,'--no-pager','-p','CPUQuotaPerSecUSec','-p','CPUQuotaPeriodUSec','-p','ControlGroup'],text=True)
p=Path('/opt/a05bd-webengine/logs/cpu-limit-before-quiet.txt')
if not p.exists():p.write_text(before)
cg=subprocess.check_output(['systemctl','show',unit,'-p','ControlGroup','--value'],text=True).strip()
p=Path('/sys/fs/cgroup'+cg)
def usage():return int(dict(l.split() for l in (p/'cpu.stat').read_text().splitlines())['usage_usec'])
t=time.monotonic();a=usage();time.sleep(3);elapsed=time.monotonic()-t
print('BEFORE',json.dumps({'cpu_core_percent':round((usage()-a)/1e6/elapsed*100,1),'cpu_max':((p/'cpu.max').read_text().strip() if (p/'cpu.max').exists() else 'not enabled; unlimited')}))
subprocess.run(['systemctl','set-property','--runtime',unit,'CPUQuota=100%'],check=True)
t=time.monotonic();a=usage();time.sleep(5);elapsed=time.monotonic()-t
print('AFTER',json.dumps({'cpu_core_percent':round((usage()-a)/1e6/elapsed*100,1),'cpu_max':((p/'cpu.max').read_text().strip() if (p/'cpu.max').exists() else 'not enabled; unlimited')}))
print(subprocess.check_output(['systemctl','show',unit,'--no-pager','-p','ActiveState','-p','CPUQuotaPerSecUSec','-p','CPUQuotaPeriodUSec'],text=True))
PY
