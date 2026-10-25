#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
import argparse,json
from pathlib import Path
from lib.common import STATE,now,profile,require_root,save_json
from lib.snapshot import Snapshot
from lib.branding import LOGO_TARGETS,boot_audit,apply_logos
p=argparse.ArgumentParser(description='Replace GNOME About and inactive Plymouth logo files. Does not restart desktop, enable splash, rebuild initramfs or flash U-Boot.')
p.add_argument('--logo-file',type=Path,default=Path('/usr/share/backgrounds/ymbot/brain-logo.png'));p.add_argument('--apply',action='store_true');a=p.parse_args();require_root();profile()
try:
 if not a.apply:print(json.dumps({'mode':'dry-run','existing_logo_targets':[x for x in LOGO_TARGETS if Path(x).is_file()],'boot':boot_audit()},ensure_ascii=False,indent=2))
 else:
  snap=Snapshot();snap.remember(STATE/'last-branding.json');r=apply_logos(a.logo_file,snap);r.update(at=now(),backup=str(snap.path));save_json(STATE/'last-branding.json',r);print(json.dumps(r,ensure_ascii=False,indent=2))
except Exception as e:
 if 'snap' in globals():print('Backup: '+str(snap.path))
 p.exit(1,str(e)+'\n')
