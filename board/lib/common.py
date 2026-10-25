# SPDX-License-Identifier: GPL-2.0-only
from pathlib import Path
import datetime,hashlib,json,os,platform,pwd,subprocess
ROOT=Path(__file__).resolve().parents[2]
BOARD=ROOT/'board'
STATE=Path('/var/lib/rk3588-board-kit')
def now():return datetime.datetime.now().astimezone().isoformat()
def run(*args,check=True,timeout=40):
 r=subprocess.run(list(map(str,args)),text=True,capture_output=True,timeout=timeout)
 if check and r.returncode:raise RuntimeError(f'{args[0]} exited {r.returncode}: '+r.stderr.strip()[-1500:])
 return r.stdout if check else r
def require(condition,message):
 if not condition:raise RuntimeError(message)
def require_root():require(os.geteuid()==0,'Run with sudo on the target board.')
def profile():
 require(platform.machine()=='aarch64','This profile is for ARM64 only.')
 compat=Path('/proc/device-tree/compatible').read_bytes().split(b'\0')
 require(b'rockchip,rk3588' in compat,'Expected Rockchip RK3588.')
 model=Path('/proc/device-tree/model').read_text().rstrip('\0')
 require('LubanCat-5IO' in model,'Expected LubanCat-5IO/5IOB BSP; carrier must be LBM5-DIBAN-V01A.')
 release=dict(l.split('=',1) for l in Path('/etc/os-release').read_text().splitlines() if '=' in l)
 require(release.get('VERSION_ID','').strip('"')=='22.04','Only the tested Ubuntu 22.04 BSP profile is supported.')
 require(platform.release()=='6.1.172','Only the tested 6.1.172 BSP is supported; rebuild/review other kernels explicitly.')
 return {'model':model,'kernel':platform.uname()._asdict(),'os':release.get('PRETTY_NAME','').strip('"')}
def save_json(path,data,mode=0o600):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.new');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.chmod(mode);os.replace(tmp,p)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def configuration(path='/etc/default/lbm5-interfaces'):
 d={}
 for l in Path(path).read_text().splitlines():
  if l and not l.lstrip().startswith('#') and '=' in l:
   k,v=l.split('=',1);d[k.strip()]=v.strip().strip('"\'')
 return d

def desktop_user():
 for name in (os.environ.get('SUDO_USER'), 'ymbot'):
  if name and name!='root':
   try:
    if pwd.getpwnam(name).pw_uid>=1000:return name
   except KeyError:pass
 try:return pwd.getpwuid(1000).pw_name
 except KeyError:return 'cat'
