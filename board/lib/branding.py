# SPDX-License-Identifier: GPL-2.0-only
"""Replace supported userspace logos, and audit boot branding without flashing firmware."""
from pathlib import Path
import os,re
from .common import run,require,sha
LOGO_SHA='c3fb34bb5b182375cbb30c5d9e2cc16808203e5b5b22a0781b7e1fbbaba635b6'
LOGO_TARGETS=(
 '/usr/share/pixmaps/ubuntu-logo-icon.png',
 '/usr/share/pixmaps/ubuntu-logo-dark.png',
 '/usr/share/plymouth/themes/spinner/watermark.png',
 '/usr/share/plymouth/themes/spinner/bgrt-fallback.png',
)
def boot_audit():
 cmdline=Path('/proc/cmdline').read_text().strip();args=cmdline.split()
 config=Path('/boot/config-'+os.uname().release)
 if not config.is_file():config=Path('/usr/src/linux-headers-'+os.uname().release+'/.config')
 text=config.read_text() if config.is_file() else ''
 files=[str(p) for base in ['/boot','/boot/firmware'] for p in Path(base).glob('*') if p.name in ('logo.bmp','logo_kernel.bmp','resource.img')]
 return {'kernel_config_source':str(config),'plymouth_disabled':'plymouth.enable=0' in args,'splash_argument':'splash' in args,'kernel_logo_config':'disabled' if '# CONFIG_LOGO is not set' in text else ('enabled' if re.search(r'^CONFIG_LOGO=y$',text,re.M) else 'unknown'),
  'filesystem_boot_logo_resources':files,'firmware_stage':'Not visually tested; never infer U-Boot logo absence from Linux/Plymouth settings.',
  'boot_arguments_changed':False,'bootloader_flashed':False,'initramfs_rebuilt':False,
  'note':'Root-filesystem Plymouth artwork is replaced as an inactive fallback. The already-built initramfs is not changed; there is no active Plymouth splash in this profile.'}

def apply_logos(source,snap):
 source=Path(source);require(source.is_file() and sha(source)==LOGO_SHA,'Official brain logo checksum mismatch.')
 replaced=[]
 for name in LOGO_TARGETS:
  p=Path(name)
  if not p.is_file():continue
  require(not p.is_symlink(),'Unexpected logo symlink: '+name)
  snap.remember(p)
  destination=str(p)+'.ymbot-vendor'
  diversion=run('dpkg-divert','--list',p).strip()
  if diversion:
   require(run('dpkg-divert','--truename',p).strip()==destination,'Logo already has an unrelated package diversion: '+name)
  else:
   run('dpkg-divert','--local','--add','--rename','--divert',destination,p)
   snap.data.setdefault('branding_diversions',[]).append({'path':str(p),'divert':destination});snap.flush()
  snap.write(p,source.read_bytes(),0o644);p.chmod(0o644)
  replaced.append({'path':str(p),'sha256':sha(p)})
 require(any(e['path']=='/usr/share/pixmaps/ubuntu-logo-icon.png' for e in replaced),'GNOME About logo asset not found in the supported BSP.')
 return {'logos':replaced,'package_upgrades':'local dpkg diversions preserve branding; vendor files retained beside overrides','boot':boot_audit()}
