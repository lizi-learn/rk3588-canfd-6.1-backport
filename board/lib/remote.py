# SPDX-License-Identifier: GPL-2.0-only
from pathlib import Path
import json,os
from .common import BOARD,STATE,require,run,save_json,sha

def installed(package):
 r=run('dpkg-query','-W','-f=${db:Status-Status}',package,check=False)
 return r.returncode==0 and r.stdout=='installed'

def install_remote(local_dir=None):
 manifest=json.loads((BOARD/'assets/remote-packages.json').read_text());result={}
 cache=STATE/'downloads';cache.mkdir(parents=True,exist_ok=True)
 for package,entry in manifest.items():
  if installed(package):result[package]='kept installed version';continue
  path=Path(local_dir)/entry['filename'] if local_dir else cache/entry['filename']
  if not path.exists():
   print('Downloading '+package+' from '+entry['source_label'],flush=True)
   # curl follows HTTPS only, keeps TLS validation, and rejects HTML masquerading as a deb.
   run('curl','--fail','--location','--proto','=https','--proto-redir','=https','--retry','2','--connect-timeout','15','--max-time','240','--output',str(path)+'.part',entry['url'],timeout=260)
   os.replace(str(path)+'.part',path)
  require(sha(path)==entry['sha256'],'Package checksum mismatch: '+package)
  for field,value in [('Package',package),('Architecture','arm64'),('Version',entry['version'])]:
   require(run('dpkg-deb','-f',path,field).strip()==value,'Package '+field+' mismatch: '+package)
  run('apt-get','install','-y',path,timeout=300);result[package]='installed '+entry['version']
 return result
