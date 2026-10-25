#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
"""Launch a command using the real GNOME session environment; never log it."""
import argparse,os,pwd,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--user',default=pwd.getpwuid(1000).pw_name);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
if os.geteuid()!=0:raise SystemExit('Run as root to read the session environment.')
pwd.getpwnam(a.user)
pids=subprocess.check_output(['pgrep','-u',a.user,'-x','gnome-shell'],text=True).split()
if len(pids)!=1:raise SystemExit('Expected exactly one active GNOME session for '+a.user)
env=dict(x.decode(errors='surrogateescape').split('=',1) for x in Path('/proc',pids[0],'environ').read_bytes().split(b'\0') if b'=' in x)
for k in ['DISPLAY','XDG_CURRENT_DESKTOP','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR']:
 if not env.get(k):raise SystemExit('Active GNOME session is missing '+k)
command=a.command
if command[:1]==['--']:command=command[1:]
if not command:raise SystemExit('Specify a command after --user USER.')
os.execvpe('runuser',['runuser','-u',a.user,'--','env','-i']+[k+'='+v for k,v in env.items()]+command,os.environ)
