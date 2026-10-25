#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
"""Configure the tested carrier. Does not send bus traffic or reboot."""
import argparse,fcntl,json,os,platform,pwd,re,shutil,sys,tempfile
from pathlib import Path
from lib.common import BOARD,ROOT,STATE,now,profile,require,require_root,run,save_json
from lib.profile import boot_config,section,FD_OVERLAY
from lib.snapshot import Snapshot
from lib.remote import installed,install_remote

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--carrier',required=True,choices=['lbm5-diban-v01a'])
 p.add_argument('--user',default='cat');p.add_argument('--can-mode',choices=['classic','fd5m'],default='classic')
 p.add_argument('--rs485-2',choices=['on','off'],default='on');p.add_argument('--dry-run',action='store_true')
 p.add_argument('--nomachine-deb',type=Path,help='Locally obtained, licensed NoMachine ARM64 server installer if not already installed.')
 p.add_argument('--remote-package-dir',type=Path,help='Optional local directory containing the pinned ToDesk installer.')
 a=p.parse_args();require_root();device=profile();u=pwd.getpwnam(a.user);require(u.pw_uid>=1000,'Use a normal desktop account.')
 lock=open('/run/lbm5-interface-test.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 boot=Path('/boot/firmware/uEnv/uEnv-lubancat-5io.txt');require(boot.exists(),'Active 5IO board boot configuration is required.')
 require(Path('/boot/firmware/ubuntuEnv.txt').resolve()==boot.resolve(),'Unexpected U-Boot config symlink; inspect the active boot path manually.')
 mesa=Path('/opt/mesa-26.2.3');require((mesa/'lib/aarch64-linux-gnu/dri/libdril_dri.so').is_file(),'Tested BSP Mesa 26.2.3 bundle is missing; this kit does not install a GPU stack.')
 for package in ['gdm3','gnome-shell']:require(installed(package),'Tested GNOME BSP prerequisite missing: '+package)
 if not installed('nomachine'):
  require(a.nomachine_deb and a.nomachine_deb.is_file(),'NoMachine server is absent. Obtain a licensed ARM64 server .deb from the vendor and pass --nomachine-deb. Do not install the client-only package.')
  require(run('dpkg-deb','-f',a.nomachine_deb,'Package').strip()=='nomachine' and run('dpkg-deb','-f',a.nomachine_deb,'Architecture').strip()=='arm64','Wrong NoMachine server package/architecture.')
 candidate=boot_config(boot.read_text(),True,a.rs485_2=='on')
 require(Path('/lib/modules',platform.release(),'build/Makefile').exists(),'CAN build requires exact matching vendor kernel headers/config/symbol versions.')
 plan={'profile':a.carrier,'can_mode':a.can_mode,'rs485_2':a.rs485_2,'desktop':'GNOME X11 autologin, 1080p headless, no idle suspend','audio_forwarding':'disabled','remote':'retain installed versions and credentials; install missing approved packages','reboot':'manual, after successful configuration','validation':'separate verify.sh; no bus frames sent by optimize.sh'}
 if a.can_mode=='fd5m':plan['fd_stability']='EXPERIMENTAL: reboot repetition added bus errors; not qualified for reliable 5M use.'
 print(json.dumps(plan,indent=2),flush=True)
 if a.dry_run:return 0
 missing=[x for x in ['device-tree-compiler','python3-serial','iproute2','can-utils','ethtool','mesa-utils','curl'] if not installed(x)]
 missing += [x for x in ['build-essential','gcc-aarch64-linux-gnu'] if not installed(x)]
 if missing:run('apt-get','update',timeout=180);run('apt-get','install','-y',*missing,timeout=360)
 if not installed('nomachine'):run('apt-get','install','-y',a.nomachine_deb.resolve(),timeout=300)
 remote=install_remote(a.remote_package_dir)
 snap=Snapshot();snap.data['user']=a.user;snap.flush();print('Backup: '+str(snap.path),flush=True)
 try:
  # Both modes use the RK3588-specific RX FIFO/errata handling.
  print('Building against running vendor kernel headers; modpost must pass.',flush=True)
  run('make','-C',ROOT,'modules',timeout=240);run('make','-C',ROOT,'overlay',timeout=30)
  module=ROOT/'driver/lbm5_canfd.ko';require(run('modinfo','-F','vermagic',module).split()[0]==platform.release(),'Module vermagic mismatch.')
  snap.write(Path('/lib/modules',platform.release(),'extra/lbm5_canfd.ko'),module.read_bytes())
  snap.write(Path('/boot/firmware')/FD_OVERLAY.lstrip('/'),(ROOT/'build/rk3588-lbm5-canfd-overlay.dtbo').read_bytes())
  snap.write('/etc/modules-load.d/lbm5-canfd.conf','lbm5_canfd\n')
  # Validate ALL enabled overlays in combination before changing the boot file.
  base=Path('/boot/firmware/dtb/rk3588-lubancat-5io.dtb')
  if not base.exists():
   candidates=list(Path('/boot/firmware').rglob('rk3588-lubancat-5io.dtb'));require(len(candidates)==1,'Expected one matching BSP base DTB.');base=candidates[0]
  require(base.is_file(),'Base DTB missing.')
  overlays=[Path('/boot/firmware')/l.split('=',1)[1].lstrip('/') for l in candidate.splitlines() if l.startswith('dtoverlay=')]
  require(all(x.is_file() for x in overlays),'An enabled device-tree overlay is missing.')
  merged=snap.path/'merged.dtb';run('fdtoverlay','-i',base,'-o',merged,*overlays)
  nodes=['/can@fea60000','/can@fea70000','/serial@feb70000']+(['/serial@feba0000'] if a.rs485_2=='on' else [])
  for node in nodes:require(run('fdtget','-t','s',merged,node,'status').strip()=='okay','Disabled hardware node: '+node)
  snap.write(boot,candidate)
  def asset(name,target,mode=0o644):snap.write(target,(BOARD/'assets'/name).read_bytes(),mode)
  asset('lbm5-interfaces','/usr/local/sbin/lbm5-interfaces',0o755)
  asset('70-lbm5-interfaces.rules','/etc/udev/rules.d/70-lbm5-interfaces.rules')
  asset('session-run.py','/usr/local/bin/lbm5-session-run',0o755)
  config=(BOARD/'assets/interfaces.conf').read_text().replace('CAN_FD=0','CAN_FD='+str(int(a.can_mode=='fd5m'))).replace('RS485_2_ENABLED=1','RS485_2_ENABLED='+str(int(a.rs485_2=='on')))
  snap.write('/etc/default/lbm5-interfaces',config)
  devices='sys-subsystem-net-devices-can0.device sys-subsystem-net-devices-can1.device dev-ttyS4.device'+(' dev-ttyS7.device' if a.rs485_2=='on' else '')
  snap.write('/etc/systemd/system/lbm5-can.service',f'[Unit]\nDescription=LBM5 CAN and AutoDirection RS485 configuration\nRequires={devices}\nAfter={devices}\n\n[Service]\nType=oneshot\nEnvironmentFile=/etc/default/lbm5-interfaces\nExecStart=/usr/local/sbin/lbm5-interfaces start\nExecStop=/usr/local/sbin/lbm5-interfaces stop\nRemainAfterExit=yes\nTimeoutStartSec=15\n\n[Install]\nWantedBy=multi-user.target\n')
  gdm=Path('/etc/gdm3/custom.conf');snap.write(gdm,section(gdm.read_text(),'daemon',{'WaylandEnable':'false','AutomaticLoginEnable':'true','AutomaticLogin':a.user,'DefaultSession':'ubuntu-xorg.desktop'}))
  account=Path('/var/lib/AccountsService/users')/a.user;snap.write(account,section(account.read_text() if account.exists() else '', 'User',{'Session':'ubuntu-xorg','XSession':'ubuntu-xorg'}),0o600)
  dmrc=Path(u.pw_dir)/'.dmrc';snap.write(dmrc,'[Desktop]\nSession=ubuntu-xorg\n');os.chown(dmrc,u.pw_uid,u.pw_gid)
  asset('20-modesetting.conf','/etc/X11/xorg.conf.d/20-modesetting.conf')
  asset('zz-session-platform','/etc/chromium.d/zz-session-platform')
  lib=mesa/'lib/aarch64-linux-gnu';snap.write('/etc/ld.so.conf.d/00-mesa-26.2.3.conf',str(lib)+'\n')
  env={'LD_LIBRARY_PATH':lib,'LIBGL_DRIVERS_PATH':lib/'dri','GBM_BACKENDS_PATH':lib/'gbm','__EGL_VENDOR_LIBRARY_FILENAMES':mesa/'share/glvnd/egl_vendor.d/50_mesa.json','VK_ICD_FILENAMES':mesa/'share/vulkan/icd.d/panfrost_icd.aarch64.json','VK_DRIVER_FILES':mesa/'share/vulkan/icd.d/panfrost_icd.aarch64.json','LIBGL_DRIRC_PATH':mesa/'share/drirc.d'}
  # Existing BSP repair uses this drop-in name. Avoid conflicting duplicate overrides.
  snap.write('/etc/systemd/system/gdm3.service.d/mesa-26.2.3.conf','[Service]\n'+''.join(f'Environment="{k}={v}"\n' for k,v in env.items()))
  dri=Path('/usr/lib/aarch64-linux-gnu/dri/rockchip_dri.so');target=lib/'dri/libdril_dri.so'
  if not dri.is_symlink() or dri.resolve()!=target.resolve():
   diverted=run('dpkg-divert','--list',str(dri)).strip()
   if not diverted:
    snap.remember(dri)
    run('dpkg-divert','--local','--add','--rename','--divert',str(dri)+'.distrib',dri);snap.data['diversion_added']=True;snap.flush()
   snap.link(dri,target)
  node=Path('/usr/NX/etc/node.cfg');text=node.read_text()
  for k,v in {'EnableAudio':'0','AudioInterface':'disabled'}.items():text=re.sub(r'(?m)^\s*#?\s*'+k+r'\s+.*\n?','',text).rstrip()+'\n'+k+' '+v+'\n'
  snap.write(node,text,node.stat().st_mode&0o777)
  cfg=Path('/opt/todesk/config/config.ini')
  if cfg.exists():snap.remember(cfg);os.chown(cfg,0,u.pw_gid);cfg.chmod(0o660)
  autostart=Path(u.pw_dir)/'.config/autostart/todesk.desktop';snap.write(autostart,'[Desktop Entry]\nType=Application\nName=ToDesk\nExec=/opt/todesk/bin/ToDesk\nX-GNOME-Autostart-enabled=true\n');os.chown(autostart,u.pw_uid,u.pw_gid)
  run('usermod','-aG','dialout',a.user)
  # Apply desktop preferences through the existing session; no partial DISPLAY-only environment.
  prefs={'org.gnome.desktop.session/idle-delay':'uint32 0','org.gnome.desktop.screensaver/lock-enabled':'false','org.gnome.settings-daemon.plugins.power/sleep-inactive-ac-type':"'nothing'",'org.gnome.settings-daemon.plugins.power/sleep-inactive-battery-type':"'nothing'"}
  session=BOARD/'assets/session-run.py'
  if run('pgrep','-u',a.user,'-x','gnome-shell',check=False).returncode==0:
   for key,value in prefs.items():
    schema,name=key.split('/',1);old=run('python3',session,'--user',a.user,'gsettings','get',schema,name).strip();snap.data['gsettings'][key]=old;snap.flush()
    run('python3',session,'--user',a.user,'gsettings','set',schema,name,value)
  else:raise RuntimeError('No active GNOME session: log in once before running the desktop profile.')
  # Only remove the local network-online boot wait when no remote filesystem depends on it.
  fstab=Path('/etc/fstab').read_text()
  remote_mount=any(re.search(r'\b(nfs|nfs4|cifs)\b|_netdev',l) for l in fstab.splitlines() if l.strip() and not l.lstrip().startswith('#'))
  if not remote_mount:snap.service('NetworkManager-wait-online.service',False)
  else:print('Retaining network-online wait: a network filesystem is configured.',flush=True)
  for uuid in run('nmcli','-g','UUID','connection','show','--active').splitlines():
   if run('nmcli','-g','connection.type','connection','show',uuid).strip()=='802-11-wireless':
    old=run('nmcli','-g','802-11-wireless.powersave','connection','show',uuid).split()[0];snap.data['wifi'][uuid]=old;snap.flush();run('nmcli','connection','modify',uuid,'802-11-wireless.powersave','2')
  run('ldconfig');run('depmod','-a');run('udevadm','control','--reload-rules');run('systemctl','daemon-reload')
  for unit in ['lbm5-can.service','nxserver.service','todeskd.service']:snap.service(unit,True)
  result={'at':now(),'profile':plan,'backup':str(snap.path),'changed_files':snap.changed,'remote':remote,'overlay_merge':'pass','reboot_required':True,'verification':'not run by optimizer'}
  save_json(STATE/'last-optimize.json',result);print(json.dumps(result,ensure_ascii=False,indent=2));print('Configuration complete. Apply with sudo reboot, then run board/verify.sh separately.')
  return 0
 except Exception:
  print('Configuration incomplete. Backup: '+str(snap.path)+'; rollback: sudo ./board/rollback.sh '+str(snap.path),file=sys.stderr);raise
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as e:print(str(e),file=sys.stderr);raise SystemExit(1)
