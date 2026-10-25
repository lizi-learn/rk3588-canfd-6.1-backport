# SPDX-License-Identifier: GPL-2.0-only
"""Provisioning helpers; no embedded machine, network or account credentials."""
import getpass,os,pty,pwd,re,select,shlex,subprocess,tarfile,time
from pathlib import Path
from .common import require,run,sha,BOARD

def checked_file(path,digest,label):
 require(path and Path(path).is_file(),label+' is required.')
 require(digest and re.fullmatch('[a-fA-F0-9]{64}',digest),label+' requires its SHA256 from a trusted source.')
 require(sha(path)==digest.lower(),label+' checksum mismatch.')
 return Path(path).resolve()

def unpack_mesa(archive,dest):
 # Extract only one contained directory; reject special files and escaping link targets.
 import posixpath
 dest=Path(dest)
 with tarfile.open(archive,'r:*') as t:
  members=t.getmembers();require(sum(m.size for m in members)<3*1024**3,'Mesa archive too large.')
  for m in members:
   require('..' not in Path(m.name).parts,'Parent traversal archive member rejected.')
   name=posixpath.normpath(m.name)
   require(not m.name.startswith('/') and (name=='mesa-26.2.3' or name.startswith('mesa-26.2.3/')),'Unexpected archive path.')
   require(m.isdir() or m.isfile() or m.issym(),'Special/hardlink archive member rejected.')
   if m.issym():
    target=posixpath.normpath(posixpath.join(posixpath.dirname(name),m.linkname))
    require(not m.linkname.startswith('/') and target.startswith('mesa-26.2.3/'),'Escaping archive symlink.')
  # No later member may write through a symlink directory, even if lexically contained.
  links={posixpath.normpath(m.name) for m in members if m.issym()}
  for m in members:
   require(not any(str(parent) in links for parent in Path(posixpath.normpath(m.name)).parents),'Archive writes through a symlink.')
  for m in members:
   m.uid=m.gid=0;m.uname=m.gname='root';m.mode=0o755 if m.isdir() or m.mode&0o111 else 0o644
  t.extractall(dest,members=members)
  for m in members:
   if m.issym():require((dest/m.name).resolve().is_relative_to((dest/'mesa-26.2.3').resolve()),'Resolved symlink escapes bundle.')
 result=dest/'mesa-26.2.3'
 require((result/'lib/aarch64-linux-gnu/dri/libdril_dri.so').is_file(),'Mesa DRI library missing.')
 return result

def session_command(user,*cmd,check=True):
 if run('pgrep','-u',user,'-x','gnome-shell',check=False).returncode==0:
  return run('python3',BOARD/'assets/session-run.py','--user',user,'--',*cmd,check=check)
 # Offline per-user dconf initialization; does not require a first graphical login.
 return run('runuser','-u',user,'--','dbus-run-session','--',*cmd,check=check)

def change_password(user):
 """Invoke the user's PAM passwd path with old/new tokens; updates existing login keyring."""
 old=getpass.getpass('Current system password (hidden, for PAM/keyring): ')
 new=getpass.getpass('New system password (hidden): ')
 require(new==getpass.getpass('Repeat new system password (hidden): '),'Passwords differ.')
 require('\n' not in new and '\r' not in new and len(new)>=8,'Password must be at least 8 characters, without line breaks.')
 # A real controlling TTY avoids passwd's stdin/PAM ambiguities. Never print its transcript.
 pid,fd=pty.fork()
 if pid==0:
  os.environ['LC_ALL']='C';os.execvp('runuser',['runuser','-u',user,'--','passwd'])
 prompts=[('Current password:',old),('New password:',new),('Retype new password:',new)];stage=0;buf='';deadline=time.monotonic()+45;status=None
 try:
  while time.monotonic()<deadline:
   ready,_,_=select.select([fd],[],[],.1)
   if ready:
    try:data=os.read(fd,8192)
    except OSError:break
    if not data:break
    buf+=data.decode(errors='replace')
    if stage<len(prompts) and prompts[stage][0] in buf:
     os.write(fd,(prompts[stage][1]+'\n').encode());stage+=1;buf=''
   done,status=os.waitpid(pid,os.WNOHANG)
   if done:break
  else:os.kill(pid,15)
 finally:
  os.close(fd)
  try:_,status=os.waitpid(pid,0)
  except ChildProcessError:pass
 require(status==0 and stage==3,'PAM password change failed; transcript withheld.')
 del old,buf
 return new
