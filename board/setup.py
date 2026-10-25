#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
"""From received BSP to configured board; a root worker survives SSH account renaming."""
import argparse,fcntl,json,os,platform,pwd,re,shutil,subprocess,sys,time
from pathlib import Path
from lib.common import BOARD,ROOT,STATE,desktop_user,now,profile,require,require_root,run,save_json,sha
from lib.remote import installed
from lib.provision import checked_file,unpack_mesa,session_command,change_password
from lib.identity import account_preflight,rename
from lib.snapshot import Snapshot
VERSION='v0.3.0'
LOGO_URL='https://www.ymbot.com/static/png/logo-CM8nhUEK.png'
LOGO_SHA='c3fb34bb5b182375cbb30c5d9e2cc16808203e5b5b22a0781b7e1fbbaba635b6'
DESKTOP=['gdm3','gnome-shell','ubuntu-session','gnome-control-center','gnome-settings-daemon','gnome-keyring','dbus-x11','xserver-xorg-core','xserver-xorg-input-libinput','x11-xserver-utils','gnome-shell-extension-ubuntu-dock','gnome-shell-extension-appindicator','gnome-shell-extension-desktop-icons-ng','gnome-sound-recorder','gnome-screenshot','python3-nacl','mesa-utils','curl']

def emit(state,phase,**values):
 state.update(phase=phase,updated_at=now(),**values);save_json(Path(state['directory'])/'status.json',state)
 print(phase,flush=True)

def preflight(a):
 device=profile();u=account_preflight(a.source_user,a.target_user)
 require(re.fullmatch('[a-z0-9][a-z0-9-]{0,62}',a.hostname),'Invalid hostname.')
 boot=Path('/boot/firmware/uEnv/uEnv-lubancat-5io.txt');require(boot.exists() and Path('/boot/firmware/ubuntuEnv.txt').resolve()==boot.resolve(),'Unexpected active BSP boot configuration.')
 inputs={}
 if not Path('/opt/mesa-26.2.3/lib/aarch64-linux-gnu/dri/libdril_dri.so').is_file():
  inputs['mesa_bundle']=str(checked_file(a.mesa_bundle,a.mesa_sha256,'Matching BSP Mesa 26.2.3 archive'));inputs['mesa_sha256']=a.mesa_sha256
 if not all(Path('/lib/modules',platform.release(),'build',f).is_file() for f in ('Makefile','Module.symvers','include/generated/autoconf.h')):
  inputs['headers_deb']=str(checked_file(a.headers_deb,a.headers_sha256,'Exact vendor kernel headers .deb'));inputs['headers_sha256']=a.headers_sha256
  require(run('dpkg-deb','-f',inputs['headers_deb'],'Package').strip()=='linux-headers-6.1.172','Wrong kernel headers package.')
 if not installed('nomachine'):
  inputs['nomachine_deb']=str(checked_file(a.nomachine_deb,a.nomachine_sha256,'Licensed NoMachine ARM64 server installer'));inputs['nomachine_sha256']=a.nomachine_sha256
  for field,value in [('Package','nomachine'),('Architecture','arm64')]:require(run('dpkg-deb','-f',inputs['nomachine_deb'],field).strip()==value,'Wrong NoMachine server package.')
 if not installed('chromium'):
  require(a.chromium_package_dir and a.chromium_package_dir.is_dir(),'Native vendor Chromium is missing. Provide --chromium-package-dir with .deb files and SHA256SUMS; Ubuntu chromium-browser is a snap transition and is not substituted.')
  inputs['chromium_package_dir']=str(a.chromium_package_dir.resolve())
  files=list(a.chromium_package_dir.glob('*.deb'));require(files,'Chromium package directory is empty.')
  # Resolve only the named deb files; never allow checksum manifests to read outside the supplied directory.
  manifest={}
  for line in (a.chromium_package_dir/'SHA256SUMS').read_text().splitlines():
   digest,name=line.split('  ',1);require(Path(name).name==name,'Unsafe Chromium manifest filename.');manifest[name]=digest
  names=[]
  for path in files:
   checked_file(path,manifest.get(path.name),'Chromium package')
   package=run('dpkg-deb','-f',path,'Package').strip();arch=run('dpkg-deb','-f',path,'Architecture').strip()
   require(package in ('chromium','chromium-common','chromium-sandbox') and arch in ('arm64','all'),'Unexpected browser package.');names.append(package)
  require('chromium' in names,'Native chromium package missing.')
 if not a.keep_password and installed('todesk'):
  require(run('dpkg-query','-W','-f=${Version}','todesk').strip()=='4.8.5.1','For another ToDesk version use --keep-password and configure its fixed password in the vendor GUI.')
 if a.logo_file:checked_file(a.logo_file,LOGO_SHA,'Official brain logo');inputs['logo_file']=str(a.logo_file.resolve())
 if a.remote_package_dir:inputs['remote_package_dir']=str(a.remote_package_dir.resolve())
 return {'hardware':device,'source_user':a.source_user,'target_user':a.target_user,'hostname':a.hostname,'rs485_2':a.rs485_2,'can_mode':a.can_mode,'reboot':a.reboot,'inputs':inputs,'passwords':'kept' if a.keep_password else 'hidden interactive input; OS PAM + version-specific ToDesk configuration','missing_desktop_packages':[p for p in DESKTOP if not installed(p)],'session_impact':'account/hostname changes close desktop applications and SSH; stop business applications first','validation':'separate verify; setup sends no bus frames'}

def brand(user,snap,inputs):
 cache=STATE/'downloads';cache.mkdir(parents=True,exist_ok=True);source=Path(inputs.get('logo_file',cache/'ymbot-brain.png'))
 if not source.exists():
  run('curl','--fail','--location','--proto','=https','--proto-redir','=https','--retry','2','--max-time','60','-o',str(source)+'.part',LOGO_URL,timeout=70)
  require(sha(str(source)+'.part')==LOGO_SHA,'Official logo checksum mismatch.');os.replace(str(source)+'.part',source)
 require(sha(source)==LOGO_SHA,'Official logo checksum mismatch.')
 target=Path('/usr/share/backgrounds/ymbot/brain-logo.png');target.parent.mkdir(parents=True,exist_ok=True);target.parent.chmod(0o755);snap.write(target,source.read_bytes());u=pwd.getpwnam(user)
 face=Path(u.pw_dir)/'.face';snap.write(face,source.read_bytes());os.chown(face,u.pw_uid,u.pw_gid)
 from lib.profile import section
 account=Path('/var/lib/AccountsService/users')/user
 snap.write(account,section(account.read_text() if account.exists() else '', 'User',{'Icon':str(face)}),0o600)
 prefs={'org.gnome.desktop.background':{'picture-uri':target.as_uri(),'picture-uri-dark':target.as_uri(),'picture-options':'centered','primary-color':'#000000','secondary-color':'#000000','color-shading-type':'solid'},'org.gnome.desktop.screensaver':{'picture-uri':target.as_uri()}}
 snap.data['user']=user
 for schema,values in prefs.items():
  for key,value in values.items():
   snap.data['gsettings'][schema+'/'+key]=session_command(user,'gsettings','get',schema,key).strip();snap.flush()
   session_command(user,'gsettings','set',schema,key,value)
 return {'official_logo_sha256':LOGO_SHA,'wallpaper':target.as_uri(),'recorder':'gnome-sound-recorder installed; no microphone capture performed'}

def worker(planpath):
 os.umask(0o077);plan=json.loads(Path(planpath).read_text());directory=Path(planpath).parent
 state={'directory':str(directory),'started_at':now(),'pass':False,'version':VERSION};emit(state,'preparing-packages')
 lock=open('/run/lbm5-setup.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  profile();account_preflight(plan['source_user'],plan['target_user']);inputs=plan['inputs']
  # Recheck supplied inputs after copying them into the root-owned transaction.
  for key in ('mesa_bundle','headers_deb','nomachine_deb'):
   if key in inputs:checked_file(inputs[key],inputs[key.replace('_bundle','_sha256').replace('_deb','_sha256')],key)
  if plan['missing_desktop_packages']:
   run('apt-get','update',timeout=300)
   subprocess.run(['debconf-set-selections'],input='gdm3 shared/default-x-display-manager select gdm3\n',text=True,check=True)
   env=os.environ.copy();env['DEBIAN_FRONTEND']='noninteractive'
   r=subprocess.run(['apt-get','install','-y',*plan['missing_desktop_packages']],env=env,timeout=900)
   require(r.returncode==0,'Desktop package installation failed.')
  if 'headers_deb' in inputs:run('apt-get','install','-y',inputs['headers_deb'],timeout=300)
  require(all(Path('/lib/modules',platform.release(),'build',f).is_file() for f in ('Makefile','Module.symvers','include/generated/autoconf.h')),'Exact matching vendor headers/config/Module.symvers are required.')
  if 'mesa_bundle' in inputs:
   staging=directory/'mesa-staging';staging.mkdir();mesa=unpack_mesa(inputs['mesa_bundle'],staging)
   require(not Path('/opt/mesa-26.2.3').exists(),'Refusing to overwrite an existing partial Mesa bundle.');shutil.move(str(mesa),'/opt/mesa-26.2.3')
  if 'chromium_package_dir' in inputs:
   run('apt-get','install','-y',*sorted(Path(inputs['chromium_package_dir']).glob('*.deb')),timeout=300)
  emit(state,'optimizing-board')
  cmd=['python3',str(BOARD/'optimize.py'),'--carrier','lbm5-diban-v01a','--user',plan['source_user'],'--rs485-2',plan['rs485_2'],'--can-mode',plan['can_mode']]
  for key in ('nomachine_deb','remote_package_dir'):
   if key in inputs:cmd += ['--'+key.replace('_','-'),inputs[key]]
  subprocess.run(cmd,check=True,timeout=1200)
  state['optimization_backup']=json.loads((STATE/'last-optimize.json').read_text())['backup']
  snap=Snapshot();state['branding_backup']=str(snap.path);emit(state,'branding-desktop')
  state['branding']=brand(plan['source_user'],snap,inputs)
  if 'todesk_payload' in plan:
   run('systemctl','start','todeskd.service')
   import configparser
   for attempt in range(30):
    cfg=configparser.ConfigParser(interpolation=None);cfg.read('/opt/todesk/config/config.ini')
    if cfg.get('configinfo','clientid',fallback=''):break
    time.sleep(1)
   from lib.todesk_password import apply
   state['todesk']=apply(plan['todesk_payload'],plan['source_user'],snap)
   # Remove the transient encrypted credential after application; local root backup retains previous config.
   del plan['todesk_payload'];save_json(planpath,plan)
  identity=Snapshot();state['identity_backup']=str(identity.path);emit(state,'renaming-account')
  state['identity']=rename(plan['source_user'],plan['target_user'],plan['hostname'],identity)
  emit(state,'configured-reboot-required',configuration_complete=True,hardware_acceptance='not run',verification='run board/verify.sh after reboot')
  if plan['reboot']:run('shutdown','-r','+1','Board setup complete; reconnect as '+plan['target_user'])
 except BaseException as e:
  # Exceptions must never dump the private plan (which may contain a new encrypted ToDesk credential).
  emit(state,'failed',error=type(e).__name__+': '+str(e));raise

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--worker',type=Path,help=argparse.SUPPRESS);p.add_argument('--status',action='store_true')
 p.add_argument('--carrier',choices=['lbm5-diban-v01a']);p.add_argument('--source-user',default=desktop_user());p.add_argument('--target-user',default='ymbot');p.add_argument('--hostname',default='ymbot')
 p.add_argument('--rs485-2',choices=['on','off'],default='on');p.add_argument('--can-mode',choices=['classic','fd5m'],default='classic')
 p.add_argument('--dry-run',action='store_true');p.add_argument('--keep-password',action='store_true',help='Keep existing system and ToDesk passwords. Default prompts securely for new credentials.')
 p.add_argument('--reboot',action='store_true',help='Schedule reboot one minute after successful configuration.')
 for name in ('nomachine-deb','mesa-bundle','headers-deb','chromium-package-dir','remote-package-dir','logo-file'):p.add_argument('--'+name,type=Path)
 for name in ('nomachine','mesa','headers'):p.add_argument('--'+name+'-sha256')
 a=p.parse_args();require_root()
 if a.worker:return worker(a.worker)
 if a.status:
  pointer=STATE/'latest-setup';require(pointer.is_symlink(),'No setup transaction exists.');print((pointer/'status.json').read_text());return
 require(a.carrier=='lbm5-diban-v01a','Explicitly select --carrier lbm5-diban-v01a.')
 run('python3',ROOT/'scripts/check_source.py')
 plan=preflight(a);print(json.dumps(plan,ensure_ascii=False,indent=2),flush=True)
 if a.dry_run:return
 # Do not begin a second worker while the first one is installing packages or renaming the account.
 lock=open('/run/lbm5-setup.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if not a.keep_password:
  if not installed('python3-nacl'):
   run('apt-get','update',timeout=300);run('apt-get','install','-y','python3-nacl',timeout=300)
  from lib.todesk_password import encode
  import getpass
  fixed=getpass.getpass('New ToDesk fixed password (8–16 ASCII letters/digits, hidden): ');plan['todesk_payload']=encode(fixed);del fixed
  password=change_password(a.source_user);del password
 # Copy all input files and source before a service terminates the old account/SSH session.
 directory=STATE/('setup-'+now().replace(':',''));directory.mkdir(parents=True,mode=0o700);directory.chmod(0o700)
 inputdir=directory/'inputs';inputdir.mkdir(mode=0o700)
 for key,value in list(plan['inputs'].items()):
  if key.endswith('_sha256'):continue
  src=Path(value);dest=inputdir/(key if src.is_dir() else key+''.join(src.suffixes))
  if src.is_dir():shutil.copytree(src,dest)
  else:shutil.copyfile(src,dest);dest.chmod(0o600)
  plan['inputs'][key]=str(dest)
 code=directory/'source';shutil.copytree(ROOT,code,ignore=shutil.ignore_patterns('.git','__pycache__','build','*.ko','*.o','*.mod*','.tmp_versions'))
 save_json(directory/'plan.json',plan);save_json(directory/'status.json',{'directory':str(directory),'phase':'queued','configuration_complete':False})
 pointer=STATE/'latest-setup'
 if pointer.is_symlink():pointer.unlink()
 require(not pointer.exists(),'Unexpected latest-setup path.');pointer.symlink_to(directory,target_is_directory=True)
 unit='rk3588-setup-'+str(time.time_ns());lock.close()
 run('systemd-run','--unit',unit,'--collect','--property=Type=exec','/usr/bin/python3',code/'board/setup.py','--worker',directory/'plan.json')
 print('Root worker started: '+unit+'\nStatus: sudo ./board/setup.sh --status\nLogs: sudo journalctl -fu '+unit+'\nThe SSH session will close during account rename; reconnect as '+a.target_user+'.\nReboot required after configuration; verification remains a separate command.')
if __name__=='__main__':
 try:main()
 except Exception as e:print(str(e),file=sys.stderr);raise SystemExit(1)
