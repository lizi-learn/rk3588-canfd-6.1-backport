#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
import argparse,getpass,json,sys
from lib.common import desktop_user,require_root
from lib.snapshot import Snapshot
from lib.todesk_password import encode,apply
p=argparse.ArgumentParser(description='Set the tested ToDesk fixed password locally; no credentials in argv or stdout.')
p.add_argument('--user',default=desktop_user());p.add_argument('--password-stdin',action='store_true',help='Read password from stdin, for a trusted local runner.');a=p.parse_args();require_root()
try:
 password=sys.stdin.read().rstrip('\n') if a.password_stdin else getpass.getpass('New ToDesk fixed password (hidden): ')
 payload=encode(password);del password;snap=Snapshot();result=apply(payload,a.user,snap);result['backup']=str(snap.path);print(json.dumps(result,indent=2))
except Exception as e:p.exit(1,str(e)+'\n')
