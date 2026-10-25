#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
import argparse,json,pwd
from pathlib import Path
from lib.common import desktop_user,require_root
from lib.browser import repair
p=argparse.ArgumentParser(description='Recover stale Chromium locks on a local home; never deletes profile data. Close Chromium first.')
p.add_argument('--user',default=desktop_user());p.add_argument('--apply',action='store_true');a=p.parse_args();require_root();u=pwd.getpwnam(a.user)
try:print(json.dumps(repair(Path(u.pw_dir)/'.config/chromium',u.pw_uid,apply=a.apply),ensure_ascii=False,indent=2))
except Exception as e:p.exit(1,str(e)+'\n')
