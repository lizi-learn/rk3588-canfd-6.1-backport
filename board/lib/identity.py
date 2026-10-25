# SPDX-License-Identifier: GPL-2.0-only
"""Root-worker account migration preserving numeric ownership and the selected password."""
import grp,os,pwd,re,shutil,spwd,time
from pathlib import Path
from .common import require,run,save_json
from .profile import section
from .browser import repair
STOP_UNITS=('lightdm.service','sddm.service','gdm3.service','nxserver.service','todeskd.service')
START_UNITS=('gdm3.service','nxserver.service','todeskd.service')
def account_preflight(source,target):
 require(re.fullmatch('[a-z_][a-z0-9_-]{0,30}',target),'Invalid target username.')
 u=pwd.getpwnam(source);require(u.pw_uid==1000 and Path(u.pw_dir)==Path('/home')/source,'Expected the BSP desktop account UID1000 with conventional home.')
 if source!=target:
  try:pwd.getpwnam(target)
  except KeyError:pass
  else:raise RuntimeError('Target account already exists; refusing to merge accounts.')
  require(not (Path('/home')/target).exists(),'Target home already exists.')
  require(not Path(u.pw_dir).is_mount(),'A separately mounted home requires a manual migration.')
  require(grp.getgrnam(source).gr_gid==u.pw_gid,'Expected matching primary group.')
  try:grp.getgrnam(target)
  except KeyError:pass
  else:raise RuntimeError('Target group already exists.')
  effective=run('/usr/sbin/sshd','-T')
  require(not any(l.startswith(('allowusers ','denyusers ','allowgroups ','denygroups ')) for l in effective.splitlines()),'SSH identity allow/deny rules need manual review before renaming.')
 return u

def rename(source,target,hostname,snap):
 u=account_preflight(source,target);oldhome=Path(u.pw_dir);newhome=Path('/home')/target
 oldhostname=run('hostname').strip();groups=sorted(os.getgrouplist(source,u.pw_gid));password_hash=spwd.getspnam(source).sp_pwdp
 meta={'source_user':source,'target_user':target,'old_hostname':oldhostname,'hostname':hostname,'uid':u.pw_uid,'gid':u.pw_gid,'groups':groups,'original_gecos':u.pw_gecos,'phase':'prepared'}
 for f in ('/etc/hostname','/etc/hosts','/etc/gdm3/custom.conf','/etc/subuid','/etc/subgid','/opt/todesk/config/config.ini','/var/lib/AccountsService/users/'+source,'/var/lib/AccountsService/users/'+target):
  if Path(f).exists():snap.remember(f)
 save_json(snap.path/'identity.json',meta)
 stopped=False
 try:
  if source!=target or oldhostname!=hostname:
   for unit in STOP_UNITS:run('systemctl','stop',unit,check=False,timeout=40)
   stopped=True;run('loginctl','terminate-user',str(u.pw_uid),check=False)
   for sig in ('TERM','KILL'):
    run('pkill','-'+sig,'-u',str(u.pw_uid),check=False);time.sleep(2)
    if run('pgrep','-u',str(u.pw_uid),check=False).returncode:break
   require(run('pgrep','-u',str(u.pw_uid),check=False).returncode!=0,'Desktop processes are still running; refusing usermod.')
   # Local stale browser locks must be checked after stopping every user process.
   p=oldhome/'.config/chromium'
   if (p/'SingletonLock').is_symlink():repair(p,u.pw_uid,apply=True)
  if source!=target:
   run('usermod','-l',target,'-d',newhome,'-m','-c',target,source)
   run('groupmod','-n',target,source)
   # Preserve recorded test-script/desktop paths without preserving the old login.
   oldhome.symlink_to(newhome,target_is_directory=True)
   for f in ('/etc/subuid','/etc/subgid'):
    p=Path(f)
    if p.exists():snap.write(p,re.sub(r'(?m)^'+re.escape(source)+':',target+':',p.read_text()),p.stat().st_mode&0o777)
   for directory in ('/var/spool/cron/crontabs','/var/mail'):
    old=Path(directory)/source;new=Path(directory)/target
    if old.exists():require(not new.exists(),'Target per-user spool exists.');old.rename(new)
   old=Path('/var/lib/AccountsService/users')/source;new=old.with_name(target)
   if old.exists():snap.write(new,old.read_text().replace(str(oldhome),str(newhome)),0o600);snap.remove(old)
   p=Path('/opt/todesk/config/config.ini')
   if p.exists():snap.write(p,p.read_text().replace(str(oldhome)+'/',str(newhome)+'/'),0o660);os.chown(p,0,u.pw_gid)
  run('usermod','-c',target,target)
  p=Path('/etc/gdm3/custom.conf');snap.write(p,section(p.read_text(),'daemon',{'AutomaticLogin':target}))
  run('hostnamectl','set-hostname',hostname)
  p=Path('/etc/hosts');snap.write(p,re.sub(r'(?m)^127\.0\.1\.1\s+.*\n?','',p.read_text()).rstrip()+'\n127.0.1.1\t'+hostname+'\n')
  require(pwd.getpwnam(target).pw_uid==u.pw_uid and sorted(os.getgrouplist(target,u.pw_gid))==groups,'Numeric account memberships changed.')
  require(spwd.getspnam(target).sp_pwdp==password_hash,'Password unexpectedly changed during rename.')
  run('/usr/sbin/sshd','-t');meta['phase']='complete-reboot-required';save_json(snap.path/'identity.json',meta)
 except BaseException:
  # Fail back to the original login/home; never restore a stale copy of /etc/shadow.
  try:
   if source!=target:
    if oldhome.is_symlink():oldhome.unlink()
    try:current=pwd.getpwnam(target)
    except KeyError:current=None
    if current:run('usermod','-l',source,'-d',oldhome,'-m',target)
    try:
     if grp.getgrnam(target).gr_gid==u.pw_gid:run('groupmod','-n',source,target)
    except KeyError:pass
    for directory in ('/var/spool/cron/crontabs','/var/mail'):
     a=Path(directory)/target;b=Path(directory)/source
     if a.exists() and not b.exists():a.rename(b)
   for entry in reversed(snap.data['files']):
    p=Path(entry['path'])
    # Only restore configuration entries captured for this transaction.
    if p.is_symlink() or p.exists():p.unlink()
    if entry['exists']:
     if 'symlink' in entry:p.symlink_to(entry['symlink'])
     else:shutil.copyfile(snap.path/'files'/str(p).lstrip('/'),p);p.chmod(entry['mode']);os.chown(p,entry['uid'],entry['gid'])
   run('usermod','-c',u.pw_gecos,source)
   run('hostnamectl','set-hostname',oldhostname);meta['phase']='rolled-back';save_json(snap.path/'identity.json',meta)
  except BaseException:meta['phase']='rollback-incomplete';save_json(snap.path/'identity.json',meta)
  raise
 finally:
  if stopped:
   run('systemctl','restart','accounts-daemon.service',check=False)
   for unit in START_UNITS:run('systemctl','start',unit,check=False,timeout=40)
 return {'user':target,'hostname':hostname,'uid_preserved':True,'groups_preserved':True,'password_preserved':True,'reboot_required':source!=target or oldhostname!=hostname,'backup':str(snap.path)}
