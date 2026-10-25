# SPDX-License-Identifier: GPL-2.0-only
from pathlib import Path
import os,shutil,subprocess
from .common import now,run,save_json,sha
class Snapshot:
 def __init__(self):
  self.path=Path('/var/backups/rk3588-board-kit')/now().replace(':','').replace('+','_')
  self.path.mkdir(parents=True,mode=0o700);self.data={'created_at':now(),'files':[],'services':{},'gsettings':{},'wifi':{},'diversion_added':False};self.changed=[];self.flush()
 def flush(self):save_json(self.path/'manifest.json',self.data)
 def remember(self,name):
  p=Path(name)
  if any(e['path']==str(p) for e in self.data['files']):return
  e={'path':str(p),'exists':p.exists() or p.is_symlink()}
  if e['exists']:
   st=p.lstat();e.update(mode=st.st_mode&0o777,uid=st.st_uid,gid=st.st_gid)
   if p.is_symlink():e['symlink']=os.readlink(p)
   else:
    dest=self.path/'files'/str(p).lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);e['sha256']=sha(p)
  self.data['files'].append(e);self.flush()
 def write(self,name,data,mode=0o644):
  p=Path(name);self.remember(p);data=data.encode() if isinstance(data,str) else data
  if not p.is_symlink() and p.exists() and p.read_bytes()==data:return
  p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.rk-kit');tmp.write_bytes(data);tmp.chmod(mode);os.replace(tmp,p);self.changed.append(str(p))
 def remove(self,name):
  p=Path(name);self.remember(p)
  if p.exists() or p.is_symlink():p.unlink();self.changed.append(str(p))
 def link(self,name,target):
  p=Path(name);self.remember(p)
  if p.is_symlink() and os.readlink(p)==str(target):return
  p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists() or p.is_symlink():p.unlink()
  p.symlink_to(target);self.changed.append(str(p))
 def service(self,name,enabled):
  self.data['services'].setdefault(name,run('systemctl','is-enabled',name,check=False).stdout.strip());self.flush()
  run('systemctl','enable' if enabled else 'disable',name)
