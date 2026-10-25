#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
import argparse,json,os,shutil
from pathlib import Path
from lib.common import require_root,run,require,sha,save_json,now,BOARD,STATE
p=argparse.ArgumentParser(description='Restore a local optimization backup; installed packages are retained.');p.add_argument('backup');p.add_argument('--dry-run',action='store_true');a=p.parse_args();require_root()
b=Path(a.backup).resolve();require(b.is_relative_to(Path('/var/backups/rk3588-board-kit')),'Backup must be under /var/backups/rk3588-board-kit')
m=json.loads((b/'manifest.json').read_text())
for e in m['files']:
 if e['exists'] and 'symlink' not in e:require(sha(b/'files'/e['path'].lstrip('/'))==e['sha256'],'Backup checksum mismatch: '+e['path'])
for entry in m.get('branding_diversions',[]):
 p=Path(entry['path'])
 require(str(p) in ['/usr/share/pixmaps/ubuntu-logo-icon.png','/usr/share/pixmaps/ubuntu-logo-dark.png','/usr/share/plymouth/themes/spinner/watermark.png','/usr/share/plymouth/themes/spinner/bgrt-fallback.png'],'Unexpected logo diversion in backup.')
 require(entry['divert']==str(p)+'.ymbot-vendor','Unexpected logo diversion target.')
 require(run('dpkg-divert','--truename',p).strip()==entry['divert'],'Logo diversion changed since backup; inspect manually.')
if a.dry_run:print(json.dumps({'backup':str(b),'files':len(m['files']),'services':m['services'],'mode':'dry-run'}));raise SystemExit(0)
for entry in m.get('branding_diversions',[]):
 p=Path(entry['path'])
 if p.exists() or p.is_symlink():p.unlink()
 run('dpkg-divert','--local','--remove','--rename','--divert',entry['divert'],p)
if m.get('diversion_added'):
 driver=Path('/usr/lib/aarch64-linux-gnu/dri/rockchip_dri.so')
 if driver.is_symlink():driver.unlink()
 run('dpkg-divert','--local','--remove','--rename','--divert',str(driver)+'.distrib',str(driver))
for e in reversed(m['files']):
 p=Path(e['path'])
 if p.is_symlink() or p.exists():p.unlink()
 if e['exists']:
  p.parent.mkdir(parents=True,exist_ok=True)
  if 'symlink' in e:p.symlink_to(e['symlink']);os.lchown(p,e['uid'],e['gid'])
  else:shutil.copyfile(b/'files'/str(p).lstrip('/'),p);p.chmod(e['mode']);os.chown(p,e['uid'],e['gid'])
if m.get('branding_diversions') and not any(e['path']==str(STATE/'last-branding.json') for e in m['files']):
 (STATE/'last-branding.json').unlink(missing_ok=True)
for unit,old in m['services'].items():
 if old in ['enabled','disabled']:run('systemctl','enable' if old=='enabled' else 'disable',unit)
for uuid,old in m.get('wifi',{}).items():run('nmcli','connection','modify',uuid,'802-11-wireless.powersave',old)
for key,value in m.get('gsettings',{}).items():
 schema,name=key.split('/',1);run('python3',BOARD/'assets/session-run.py','--user',m['user'],'gsettings','set',schema,name,value,check=False)
run('ldconfig');run('depmod','-a');run('systemctl','daemon-reload');run('udevadm','control','--reload-rules')
save_json(b/'restored.json',{'at':now(),'reboot_required':True})
print('Configuration restored. Installed packages and private application credentials are retained. Reboot to apply: sudo reboot')
