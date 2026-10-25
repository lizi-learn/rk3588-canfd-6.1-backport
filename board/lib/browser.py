# SPDX-License-Identifier: GPL-2.0-only
"""Conservative recovery of local Chromium singleton symlinks after a rename."""
import json,os,socket,subprocess,time
from pathlib import Path
NAMES=('SingletonLock','SingletonCookie','SingletonSocket')
def browser_running(uid,proc=Path('/proc')):
 for p in proc.iterdir():
  if not p.name.isdigit():continue
  try:
   if p.stat().st_uid==uid and (p/'comm').read_text().strip() in ('chromium','chrome','chromium-browse'):return True
  except (FileNotFoundError,ProcessLookupError,PermissionError):continue
 return False

def repair(profile,uid,*,apply=False,previous_hostname=None):
 profile=Path(profile)
 if not profile.is_dir():return {'status':'no profile','removed':[]}
 if profile.stat().st_uid!=uid:raise RuntimeError('Profile is not owned by selected account.')
 if browser_running(uid):raise RuntimeError('Chromium/Chrome is running; close it normally first.')
 fs=subprocess.check_output(['findmnt','-n','-o','FSTYPE','-T',str(profile)],text=True).strip()
 if fs not in ('ext4','ext3','ext2','btrfs','xfs','f2fs'):raise RuntimeError('Refusing to unlock a shared or unknown filesystem: '+fs)
 links={}
 for n in NAMES:
  p=profile/n
  if p.is_symlink():links[n]=os.readlink(p)
  elif p.exists():raise RuntimeError('Unexpected non-symlink singleton: '+n)
 if not links:return {'status':'no singleton links','removed':[]}
 lock=links.get('SingletonLock','');host,sep,pid=lock.rpartition('-')
 if not sep or not pid.isdigit():raise RuntimeError('Unrecognized singleton lock; inspect manually.')
 if previous_hostname and host!=previous_hostname:raise RuntimeError('Singleton belongs to an unexpected previous host.')
 target=links.get('SingletonSocket')
 if not target:raise RuntimeError('Missing socket link; cannot prove stale ownership.')
 if not target.startswith(('/tmp/','/run/user/'+str(uid)+'/')):raise RuntimeError('Unexpected singleton socket path.')
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(1)
  try:s.connect(target)
  except (FileNotFoundError,ConnectionRefusedError):pass
  else:raise RuntimeError('Singleton socket is live; profile remains locked.')
 if not apply:return {'status':'stale links, dry run','old_hostname':host,'removed':[],'links':list(links)}
 # Recheck both processes and exact links immediately before unlinking; no automatic launcher hook.
 if browser_running(uid) or any(not (profile/n).is_symlink() or os.readlink(profile/n)!=v for n,v in links.items()):raise RuntimeError('Profile changed during inspection; retry after closing the browser.')
 parent=profile.parent/'chromium-singleton-backups'
 if parent.is_symlink():raise RuntimeError('Unexpected backup symlink.')
 backup=parent/str(time.time_ns());backup.mkdir(parents=True,mode=0o700)
 record=backup/'links.json';record.write_text(json.dumps(links,indent=2)+'\n');record.chmod(0o600)
 os.chown(backup.parent,uid,-1);os.chown(backup,uid,-1);os.chown(record,uid,-1)
 for n in links:(profile/n).unlink()
 return {'status':'stale links archived and removed','old_hostname':host,'removed':list(links),'backup':str(record),'profile_data_preserved':True}
